from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path

from flask import abort, current_app, jsonify, request, send_file, send_from_directory, url_for
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ChartGroup, ChartTask
from ..tasks import TaskPayload, worker
from ..utils.chart_processing import build_accessible_code
from . import bp


def _current_user_id() -> int:
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        abort(401, description="Invalid authentication token.")


def _ensure_owner(task: ChartTask, user_id: int):
    if task.user_id != user_id:
        return jsonify({"message": "Not found."}), 404
    return None


def _build_group_tree(groups: list[ChartGroup]) -> list[dict[str, object]]:
    nodes: dict[int, dict[str, object]] = {}
    for group in groups:
        node = group.to_dict()
        node["children"] = []
        nodes[group.id] = node

    roots: list[dict[str, object]] = []
    for group in groups:
        node = nodes[group.id]
        parent_id = group.parent_id
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def _collect_descendant_ids(group: ChartGroup) -> set[int]:
    ids = {group.id}
    for child in group.children:
        ids.update(_collect_descendant_ids(child))
    return ids


def _load_custom_code(task: ChartTask) -> dict[str, str]:
    if not task.custom_code:
        return {}
    try:
        data = json.loads(task.custom_code)
        if isinstance(data, dict):
            return {str(key): str(value) for key, value in data.items()}
    except (TypeError, json.JSONDecodeError):
        return {"legacy": task.custom_code}
    return {}


@bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


@bp.get("/groups")
@jwt_required()
def list_groups():
    user_id = _current_user_id()
    groups = (
        ChartGroup.query.filter_by(user_id=user_id)
        .order_by(ChartGroup.created_at.desc())
        .all()
    )
    return jsonify(_build_group_tree(groups))


@bp.post("/groups")
@jwt_required()
def create_group():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    parent_id = payload.get("parent_id")
    if not name:
        return jsonify({"message": "Group name is required."}), 400
    parent = None
    if parent_id is not None:
        parent = ChartGroup.query.get(parent_id)
        if not parent or parent.user_id != user_id:
            return jsonify({"message": "Parent group not found."}), 400
    group = ChartGroup(name=name, user_id=user_id, parent=parent)
    db.session.add(group)
    db.session.commit()
    data = group.to_dict()
    data["children"] = []
    return jsonify(data), 201


@bp.patch("/groups/<int:group_id>")
@jwt_required()
def update_group(group_id: int):
    user_id = _current_user_id()
    group = ChartGroup.query.get_or_404(group_id)
    if group.user_id != user_id:
        return jsonify({"message": "Not found."}), 404

    payload = request.get_json() or {}
    name = payload.get("name")
    parent_id = payload.get("parent_id")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "Group name is required."}), 400
        group.name = name

    if parent_id is not None:
        if parent_id == group.id:
            return jsonify({"message": "Group cannot be its own parent."}), 400
        if parent_id:
            parent = ChartGroup.query.get(parent_id)
            if not parent or parent.user_id != user_id:
                return jsonify({"message": "Parent group not found."}), 400
            ancestor = parent
            while ancestor:
                if ancestor.id == group.id:
                    return jsonify({"message": "Cannot move group under its descendant."}), 400
                ancestor = ancestor.parent
            group.parent = parent
        else:
            group.parent = None

    db.session.commit()
    data = group.to_dict()
    data["children"] = [child.to_dict() for child in group.children]
    return jsonify(data)


@bp.delete("/groups/<int:group_id>")
@jwt_required()
def delete_group(group_id: int):
    user_id = _current_user_id()
    group = ChartGroup.query.get_or_404(group_id)
    if group.user_id != user_id:
        return jsonify({"message": "Not found."}), 404
    if group.tasks:
        return jsonify({"message": "Cannot delete a group with tasks."}), 400
    if group.children:
        return jsonify({"message": "Cannot delete a group with subgroups."}), 400
    db.session.delete(group)
    db.session.commit()
    return jsonify({"message": "Group deleted."})


@bp.get("/tasks")
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    group_id = request.args.get("group_id")
    page = max(int(request.args.get("page", 1) or 1), 1)
    page_size = int(request.args.get("page_size", 10) or 10)
    page_size = max(1, min(page_size, 50))

    query = ChartTask.query.filter_by(user_id=user_id)
    if group_id:
        group = ChartGroup.query.filter_by(id=int(group_id), user_id=user_id).first()
        if not group:
            return jsonify({"message": "Group not found."}), 404
        ids = _collect_descendant_ids(group)
        query = query.filter(ChartTask.group_id.in_(ids))

    pagination = query.order_by(ChartTask.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return jsonify(
        {
            "items": [task.to_dict() for task in pagination.items],
            "page": pagination.page,
            "page_size": page_size,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@bp.post("/tasks")
@jwt_required()
def create_task():
    user_id = _current_user_id()
    if "image" not in request.files:
        return jsonify({"message": "Image file is required."}), 400

    image_file = request.files["image"]
    title = request.form.get("title") or Path(image_file.filename or "chart").stem
    group_id = request.form.get("group_id")
    language = (request.form.get("language") or "java").lower()
    if language not in {"java", "kotlin"}:
        return jsonify({"message": "Unsupported language."}), 400

    if not image_file.filename:
        return jsonify({"message": "Invalid file."}), 400

    filename = secure_filename(image_file.filename)
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"]) / str(user_id)
    upload_folder.mkdir(parents=True, exist_ok=True)
    file_path = upload_folder / unique_name
    image_file.save(file_path)

    relative_path = str(Path(str(user_id)) / unique_name)
    public_url = url_for("charts.serve_upload", filename=relative_path, _external=True)

    target_group = None
    if group_id:
        target_group = ChartGroup.query.filter_by(id=int(group_id), user_id=user_id).first()
        if not target_group:
            return jsonify({"message": "Group not found."}), 404

    task = ChartTask(
        title=title,
        user_id=user_id,
        group_id=target_group.id if target_group else None,
        language=language,
        image_path=str(relative_path),
        status="pending",
    )
    db.session.add(task)
    db.session.commit()

    worker.enqueue(TaskPayload(task_id=task.id, image_path=str(file_path), public_image_url=public_url))

    return jsonify(task.to_dict()), 201


@bp.get("/tasks/<int:task_id>")
@jwt_required()
def get_task(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response
    return jsonify(task.to_dict())


@bp.patch("/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    payload = request.get_json() or {}

    title = payload.get("title")
    if title is not None:
        title = title.strip()
        if not title:
            return jsonify({"message": "Task title is required."}), 400
        task.title = title

    group_id = payload.get("group_id")
    if group_id is not None:
        if group_id == "":
            group_id = None
        if group_id is None:
            task.group_id = None
        else:
            group = ChartGroup.query.filter_by(id=int(group_id), user_id=user_id).first()
            if not group:
                return jsonify({"message": "Group not found."}), 404
            task.group_id = group.id

    language = payload.get("language")
    if language is not None:
        language = language.lower()
        if language not in {"java", "kotlin"}:
            return jsonify({"message": "Unsupported language."}), 400
        task.language = language
        if language == "java" and task.java_code:
            task.generated_code = task.java_code
        if language == "kotlin" and task.kotlin_code:
            task.generated_code = task.kotlin_code

    db.session.commit()
    return jsonify(task.to_dict())


@bp.delete("/tasks/<int:task_id>")
@jwt_required()
def delete_task(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    if task.image_path:
        file_path = Path(current_app.config["UPLOAD_FOLDER"]) / task.image_path
        if file_path.exists():
            file_path.unlink()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted."})


@bp.post("/tasks/<int:task_id>/cancel")
@jwt_required()
def cancel_task(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    if task.status in {"completed", "failed"}:
        return jsonify({"message": "Task already finished."}), 400

    task.status = "cancelled"
    db.session.commit()
    return jsonify({"message": "Task cancelled."})


@bp.post("/tasks/<int:task_id>/custom-code")
@jwt_required()
def update_custom_code(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    payload = request.get_json() or {}
    language = (payload.get("language") or task.language or "java").lower()
    if language not in {"java", "kotlin"}:
        return jsonify({"message": "Unsupported language."}), 400
    code = payload.get("code")
    existing = _load_custom_code(task)
    if code:
        existing[language] = code
    else:
        existing.pop(language, None)
    task.custom_code = json.dumps(existing) if existing else None
    db.session.commit()
    return jsonify(task.to_dict())


@bp.post("/tasks/<int:task_id>/regenerate-code")
@jwt_required()
def regenerate_code(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    if not task.summary or not task.data_points:
        return jsonify({"message": "Task data not ready."}), 400
    language = (request.args.get("language") or task.language or "java").lower()
    payload = request.get_json(silent=True) or {}
    language = (payload.get("language") or language).lower()
    if language not in {"java", "kotlin"}:
        return jsonify({"message": "Unsupported language."}), 400

    public_url = url_for("charts.serve_upload", filename=task.image_path, _external=True)
    regenerated_bundle = build_accessible_code(public_url, task.summary, task.data_points)
    if language == "java":
        task.java_code = regenerated_bundle.get("java")
    else:
        task.kotlin_code = regenerated_bundle.get("kotlin")

    if task.language == language:
        task.generated_code = regenerated_bundle.get(language)
    task.integration_doc = regenerated_bundle.get("integration") or task.integration_doc
    db.session.commit()
    return jsonify(task.to_dict())


@bp.get("/tasks/<int:task_id>/download")
@jwt_required()
def download_code_archive(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    if not task.java_code and not task.kotlin_code:
        return jsonify({"message": "Task code not ready."}), 400

    custom = _load_custom_code(task)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        summary_lines = [
            "# 无障碍图表任务打包说明",
            "",
            f"任务标题：{task.title}",
            f"当前状态：{task.status}",
            "",
            "该压缩包包含 Java 与 Kotlin 两种语言的示例代码，以及集成步骤说明。",
        ]
        if task.summary:
            summary_lines.append("")
            summary_lines.append("图表摘要：")
            summary_lines.append(task.summary)
        archive.writestr("README.md", "\n".join(summary_lines))

        java_source = custom.get("java") or task.java_code or ""
        kotlin_source = custom.get("kotlin") or task.kotlin_code or ""

        if java_source:
            archive.writestr("java/AccessibleChartActivity.java", java_source)
        if kotlin_source:
            archive.writestr("kotlin/AccessibleChartActivity.kt", kotlin_source)

        integration = task.integration_doc or {}
        java_steps = integration.get("java") or []
        kotlin_steps = integration.get("kotlin") or []
        archive.writestr(
            "docs/java_integration.txt",
            "\n".join(str(step) for step in java_steps) or "暂无集成说明。",
        )
        archive.writestr(
            "docs/kotlin_integration.txt",
            "\n".join(str(step) for step in kotlin_steps) or "暂无集成说明。",
        )

    buffer.seek(0)
    filename = f"chart_task_{task.id}.zip"
    return send_file(buffer, download_name=filename, as_attachment=True, mimetype="application/zip")
