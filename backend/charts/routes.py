from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path

from flask import (
    abort,
    current_app,
    jsonify,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ChartApplication, ChartGroup, ChartTask, CodeTemplate
from ..tasks import TaskPayload, worker
from ..utils.chart_processing import build_accessible_code
from ..utils.template_engine import (
    REQUIRED_TEMPLATE_PLACEHOLDERS,
    render_template_for_task,
    validate_template_content,
)
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
    ordered = sorted(groups, key=lambda g: (g.parent_id or 0, g.created_at))
    for group in ordered:
        node = group.to_dict()
        node["children"] = []
        nodes[group.id] = node

    roots: list[dict[str, object]] = []
    for group in ordered:
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


def _application_payload(application: ChartApplication) -> dict[str, object]:
    payload = application.to_dict()
    payload["groups"] = _build_group_tree(application.groups)
    return payload


def _ensure_template_access(template: CodeTemplate, user_id: int) -> bool:
    if template.is_system:
        return True
    return template.user_id == user_id


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


@bp.get("/applications")
@jwt_required()
def list_applications():
    user_id = _current_user_id()
    applications = (
        ChartApplication.query.filter_by(user_id=user_id)
        .order_by(ChartApplication.created_at.asc())
        .all()
    )
    return jsonify([_application_payload(app) for app in applications])


@bp.post("/groups")
@jwt_required()
def create_group():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    parent_id = payload.get("parent_id")
    application_id = payload.get("application_id")
    if not name:
        return jsonify({"message": "Group name is required."}), 400
    if not application_id:
        return jsonify({"message": "Application id is required."}), 400

    application = (
        ChartApplication.query.filter_by(id=int(application_id), user_id=user_id)
        .first()
    )
    if not application:
        return jsonify({"message": "Application not found."}), 404
    parent = None
    if parent_id is not None:
        parent = ChartGroup.query.get(parent_id)
        if not parent or parent.user_id != user_id:
            return jsonify({"message": "Parent group not found."}), 400
        if parent.application_id != application.id:
            return jsonify({"message": "Parent group must belong to the same application."}), 400
    group = ChartGroup(name=name, user_id=user_id, parent=parent, application=application)
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
    application_id = payload.get("application_id")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "Group name is required."}), 400
        group.name = name

    if application_id is not None:
        application = (
            ChartApplication.query.filter_by(id=int(application_id), user_id=user_id)
            .first()
        )
        if not application:
            return jsonify({"message": "Application not found."}), 404
        group.application = application
        if group.parent and group.parent.application_id != group.application_id:
            group.parent = None

    if parent_id is not None:
        if parent_id == group.id:
            return jsonify({"message": "Group cannot be its own parent."}), 400
        if parent_id:
            parent = ChartGroup.query.get(parent_id)
            if not parent or parent.user_id != user_id:
                return jsonify({"message": "Parent group not found."}), 400
            if parent.application_id != group.application_id:
                return jsonify({"message": "Parent group must belong to the same application."}), 400
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
    db.session.delete(group)
    db.session.commit()
    return jsonify({"message": "Group deleted."})


@bp.get("/tasks")
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    group_id = request.args.get("group_id")
    application_id = request.args.get("application_id")
    search = (request.args.get("q") or "").strip().lower()
    page = max(int(request.args.get("page", 1) or 1), 1)
    page_size = int(request.args.get("page_size", 10) or 10)
    page_size = max(1, min(page_size, 50))

    query = ChartTask.query.filter_by(user_id=user_id)
    if application_id:
        application = (
            ChartApplication.query.filter_by(id=int(application_id), user_id=user_id)
            .first()
        )
        if not application:
            return jsonify({"message": "Application not found."}), 404
        query = query.filter_by(application_id=application.id)
    if group_id:
        group = ChartGroup.query.filter_by(id=int(group_id), user_id=user_id).first()
        if not group:
            return jsonify({"message": "Group not found."}), 404
        ids = _collect_descendant_ids(group)
        query = query.filter(ChartTask.group_id.in_(ids))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            func.lower(ChartTask.title).like(pattern)
            | func.lower(func.coalesce(ChartTask.summary, "")).like(pattern)
            | func.lower(func.coalesce(ChartTask.description, "")).like(pattern)
        )

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
    application_id = request.form.get("application_id")
    application_name = (request.form.get("application_name") or "").strip()
    template_id = request.form.get("template_id")

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

    application: ChartApplication | None = None
    if application_id:
        application = (
            ChartApplication.query.filter_by(id=int(application_id), user_id=user_id)
            .first()
        )
        if not application:
            return jsonify({"message": "Application not found."}), 404
    elif application_name:
        application = (
            ChartApplication.query.filter_by(name=application_name, user_id=user_id)
            .first()
        )
        if not application:
            application = ChartApplication(name=application_name, user_id=user_id)
            db.session.add(application)
            db.session.flush()
    else:
        application = (
            ChartApplication.query.filter_by(user_id=user_id)
            .order_by(ChartApplication.created_at.asc())
            .first()
        )
        if not application:
            application = ChartApplication(name="默认应用", user_id=user_id)
            db.session.add(application)
            db.session.flush()

    target_group = None
    if group_id:
        target_group = ChartGroup.query.filter_by(id=int(group_id), user_id=user_id).first()
        if not target_group:
            return jsonify({"message": "Group not found."}), 404
        if target_group.application_id != application.id:
            return jsonify({"message": "Group does not belong to the selected application."}), 400

    selected_template: CodeTemplate | None = None
    if template_id:
        try:
            template_id_int = int(template_id)
        except (TypeError, ValueError):
            return jsonify({"message": "Template not found."}), 404
        selected_template = CodeTemplate.query.get(template_id_int)
        if not selected_template or not _ensure_template_access(selected_template, user_id):
            return jsonify({"message": "Template not found."}), 404
    else:
        selected_template = (
            CodeTemplate.query.filter_by(is_system=True, language="java")
            .order_by(CodeTemplate.created_at.asc())
            .first()
            or CodeTemplate.query.filter(
                (CodeTemplate.user_id == user_id) | (CodeTemplate.is_system.is_(True)),
                CodeTemplate.language == "java",
            )
            .order_by(CodeTemplate.is_system.desc(), CodeTemplate.created_at.asc())
            .first()
        )

    language = selected_template.language if selected_template else "java"

    task = ChartTask(
        title=title,
        user_id=user_id,
        application_id=application.id,
        group_id=target_group.id if target_group else None,
        language=language,
        image_path=str(relative_path),
        status="pending",
        template=selected_template,
    )
    db.session.add(task)
    db.session.commit()

    worker.enqueue(TaskPayload(task_id=task.id, image_path=str(file_path), public_image_url=public_url))

    return jsonify(task.to_dict()), 201


@bp.get("/templates")
@jwt_required()
def list_templates():
    user_id = _current_user_id()
    language = request.args.get("language")
    include_system = (request.args.get("include_system", "true") or "true").lower()
    include_system_flag = include_system not in {"false", "0"}

    query = CodeTemplate.query
    if language:
        language = language.lower()
        if language not in {"java", "kotlin"}:
            return jsonify({"message": "Unsupported language."}), 400
        query = query.filter_by(language=language)

    if include_system_flag:
        query = query.filter(
            (CodeTemplate.user_id == user_id) | (CodeTemplate.is_system.is_(True))
        )
    else:
        query = query.filter_by(user_id=user_id)

    templates = (
        query.order_by(CodeTemplate.is_system.desc(), CodeTemplate.created_at.asc())
        .all()
    )
    items = []
    for template in templates:
        data = template.to_dict()
        data["editable"] = not template.is_system and template.user_id == user_id
        data["deletable"] = data["editable"]
        items.append(data)
    return jsonify(
        {
            "items": items,
            "required_placeholders": list(REQUIRED_TEMPLATE_PLACEHOLDERS),
        }
    )


@bp.post("/templates")
@jwt_required()
def create_template():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    language = (payload.get("language") or "").strip().lower()
    content = payload.get("content") or ""
    if not name:
        return jsonify({"message": "Template name is required."}), 400
    if language not in {"java", "kotlin"}:
        return jsonify({"message": "Unsupported language."}), 400
    missing = validate_template_content(content)
    if missing:
        return jsonify({"message": "Template missing placeholders.", "missing": missing}), 400

    template = CodeTemplate(
        name=name,
        language=language,
        content=content,
        user_id=user_id,
        is_system=False,
    )
    db.session.add(template)
    db.session.commit()
    data = template.to_dict()
    data["editable"] = True
    data["deletable"] = True
    return jsonify(data), 201


@bp.patch("/templates/<int:template_id>")
@jwt_required()
def update_template(template_id: int):
    user_id = _current_user_id()
    template = CodeTemplate.query.get_or_404(template_id)
    if template.is_system or template.user_id != user_id:
        return jsonify({"message": "Template not found."}), 404

    payload = request.get_json() or {}
    name = payload.get("name")
    language = payload.get("language")
    content = payload.get("content")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "Template name is required."}), 400
        template.name = name

    if language is not None:
        language = language.strip().lower()
        if language not in {"java", "kotlin"}:
            return jsonify({"message": "Unsupported language."}), 400
        template.language = language

    if content is not None:
        missing = validate_template_content(content)
        if missing:
            return jsonify({"message": "Template missing placeholders.", "missing": missing}), 400
        template.content = content

    db.session.commit()
    data = template.to_dict()
    data["editable"] = True
    data["deletable"] = True
    return jsonify(data)


@bp.delete("/templates/<int:template_id>")
@jwt_required()
def delete_template(template_id: int):
    user_id = _current_user_id()
    template = CodeTemplate.query.get_or_404(template_id)
    if template.is_system or template.user_id != user_id:
        return jsonify({"message": "Template not found."}), 404

    affected_tasks = ChartTask.query.filter_by(template_id=template.id).all()
    for task in affected_tasks:
        task.template = None
        if task.status == "completed":
            if task.language == "java" and task.java_code:
                task.generated_code = task.java_code
            elif task.language == "kotlin" and task.kotlin_code:
                task.generated_code = task.kotlin_code
    db.session.delete(template)
    db.session.commit()
    return jsonify({"message": "Template deleted.", "affected_tasks": len(affected_tasks)})


@bp.post("/templates/validate")
@jwt_required()
def validate_template_endpoint():
    payload = request.get_json() or {}
    content = payload.get("content") or ""
    missing = validate_template_content(content)
    return jsonify(
        {
            "valid": not missing,
            "missing": missing,
            "required_placeholders": list(REQUIRED_TEMPLATE_PLACEHOLDERS),
        }
    )


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
    application_id = payload.get("application_id")
    template_id = payload.get("template_id")
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
            task.application_id = group.application_id

    if application_id is not None:
        if application_id == "":
            return jsonify({"message": "Application id is required."}), 400
        application = (
            ChartApplication.query.filter_by(id=int(application_id), user_id=user_id)
            .first()
        )
        if not application:
            return jsonify({"message": "Application not found."}), 404
        task.application_id = application.id
        if task.group and task.group.application_id != task.application_id:
            task.group = None

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

    if template_id is not None:
        if template_id == "":
            task.template = None
        else:
            template = CodeTemplate.query.get(int(template_id))
            if not template or not _ensure_template_access(template, user_id):
                return jsonify({"message": "Template not found."}), 404
            task.template = template
            task.language = template.language
            if task.status == "completed" and (task.java_code or task.kotlin_code):
                try:
                    task.generated_code = _render_template_for_task(template, task)
                except ValueError:
                    pass

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


@bp.post("/tasks/<int:task_id>/render-template")
@jwt_required()
def render_template_endpoint(task_id: int):
    user_id = _current_user_id()
    task = ChartTask.query.get_or_404(task_id)
    response = _ensure_owner(task, user_id)
    if response:
        return response

    payload = request.get_json() or {}
    template_id = payload.get("template_id")
    if template_id in {None, ""}:
        return jsonify({"message": "Template id is required."}), 400
    try:
        template_id_int = int(template_id)
    except (TypeError, ValueError):
        return jsonify({"message": "Template id is required."}), 400
    template = CodeTemplate.query.get(template_id_int)
    if not template or not _ensure_template_access(template, user_id):
        return jsonify({"message": "Template not found."}), 404
    if task.status != "completed":
        return jsonify({"message": "Task code not ready."}), 400
    try:
        rendered = render_template_for_task(template, task)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    return jsonify({"code": rendered, "language": template.language})


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
