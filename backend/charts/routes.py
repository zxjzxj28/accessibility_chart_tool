from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

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
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    ChartTask,
    ChartTaskResult,
    CodeTemplate,
    TaskStatus,
    TaskType,
)
from ..tasks import TaskPayload, worker
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
    except (TypeError, ValueError):  # pragma: no cover - defensive
        abort(401, description="Invalid authentication token.")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _ensure_template_access(template: CodeTemplate, user_id: int) -> bool:
    if template.is_system:
        return not template.is_deleted
    return template.user_id == user_id and not template.is_deleted


@bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


def _save_upload(file_storage) -> str:
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename or "chart.png")
    ext = Path(filename).suffix or ".png"
    target = upload_folder / f"{uuid.uuid4().hex}{ext}"
    file_storage.save(target)
    return target.name


def _resolve_template(user_id: int, template_id: str | None) -> CodeTemplate | None:
    if not template_id:
        return None
    try:
        template_int = int(template_id)
    except (TypeError, ValueError):
        raise ValueError("模板不可用") from None
    template = CodeTemplate.query.get(template_int)
    if not template or not _ensure_template_access(template, user_id):
        raise ValueError("模板不可用")
    return template


@bp.get("/tasks")
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    keyword = (request.args.get("keyword") or "").strip()
    task_name = (request.args.get("task_name") or "").strip()
    status_raw = request.args.get("status")
    created_from = _parse_datetime(request.args.get("created_from"))
    created_to = _parse_datetime(request.args.get("created_to"))
    updated_from = _parse_datetime(request.args.get("updated_from"))
    updated_to = _parse_datetime(request.args.get("updated_to"))
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 12)), 50)

    query = (
        ChartTask.query.options(
            joinedload(ChartTask.template),
            joinedload(ChartTask.result),
        )
        .filter_by(user_id=user_id, is_deleted=False)
        .order_by(ChartTask.created_at.desc())
    )

    if status_raw not in {None, ""}:
        try:
            status_value = int(status_raw)
        except (TypeError, ValueError):
            return jsonify({"message": "无效的状态筛选"}), 400
        query = query.filter(ChartTask.status == status_value)
    if task_name:
        query = query.filter(ChartTask.name.ilike(f"%{task_name}%"))
    if created_from:
        query = query.filter(ChartTask.created_at >= created_from)
    if created_to:
        query = query.filter(ChartTask.created_at <= created_to)
    if updated_from:
        query = query.filter(ChartTask.updated_at >= updated_from)
    if updated_to:
        query = query.filter(ChartTask.updated_at <= updated_to)
    if keyword:
        like = f"%{keyword}%"
        query = query.outerjoin(ChartTaskResult).filter(
            or_(ChartTask.name.ilike(like), ChartTaskResult.summary.ilike(like))
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = [task.to_dict() for task in pagination.items]

    return jsonify(
        {
            "items": items,
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@bp.post("/tasks")
@jwt_required()
def create_task():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    creation_mode = payload.get("mode")

    if creation_mode == "metadata":
        name = (payload.get("name") or payload.get("title") or "").strip()
        if not name:
            return jsonify({"message": "任务名称不能为空"}), 400

        summary = (payload.get("summary") or "").strip()
        if not summary:
            return jsonify({"message": "请填写摘要内容"}), 400

        template_id = payload.get("template_id")

        try:
            template = _resolve_template(user_id, template_id)
        except ValueError as exc:
            return jsonify({"message": str(exc)}), 400

        task = ChartTask(
            name=name,
            type=TaskType.METADATA.value,
            status=TaskStatus.COMPLETED.value,
            user_id=user_id,
            template=template,
        )
        db.session.add(task)
        db.session.flush()

        result = ChartTaskResult(
            task=task,
            is_success=True,
            summary=summary,
            data_points=payload.get("data_points") or [],
            table_data=payload.get("table_data") or [],
            error_message=None,
        )
        db.session.add(result)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    if "file" not in request.files:
        return jsonify({"message": "请上传图表图片或提供图表元数据"}), 400

    file_storage = request.files["file"]
    if file_storage.filename == "":
        return jsonify({"message": "请选择有效的图片文件"}), 400

    name = (request.form.get("name") or request.form.get("title") or "").strip()
    if not name:
        return jsonify({"message": "任务名称不能为空"}), 400

    template_id = request.form.get("template_id")

    try:
        template = _resolve_template(user_id, template_id)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    filename = _save_upload(file_storage)
    public_url = url_for("charts.serve_upload", filename=filename, _external=True)

    task = ChartTask(
        name=name,
        type=TaskType.UPLOAD.value,
        status=TaskStatus.QUEUED.value,
        user_id=user_id,
        template=template,
    )
    db.session.add(task)
    db.session.commit()

    worker.enqueue(
        TaskPayload(
            task_id=task.id,
            image_path=str(Path(current_app.config["UPLOAD_FOLDER"]) / filename),
            public_image_url=public_url,
        )
    )

    return jsonify(task.to_dict()), 201


def _load_task(task_id: int, user_id: int) -> ChartTask:
    task = (
        ChartTask.query.options(
            joinedload(ChartTask.template),
            joinedload(ChartTask.result),
        )
        .filter_by(id=task_id, user_id=user_id)
        .first()
    )
    if not task or task.is_deleted:
        abort(404, description="任务不存在")
    return task


@bp.get("/tasks/<int:task_id>")
@jwt_required()
def get_task(task_id: int):
    user_id = _current_user_id()
    task = _load_task(task_id, user_id)
    return jsonify(task.to_dict())


@bp.patch("/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id: int):
    user_id = _current_user_id()
    task = _load_task(task_id, user_id)
    payload = request.get_json() or {}

    name = payload.get("name") or payload.get("title")
    if name is not None:
        name = str(name).strip()
        if not name:
            return jsonify({"message": "任务名称不能为空"}), 400
        task.name = name

    template_id = payload.get("template_id")

    try:
        if template_id is not None:
            task.template = _resolve_template(user_id, template_id)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    db.session.commit()
    return jsonify(task.to_dict())


@bp.post("/tasks/<int:task_id>/cancel")
@jwt_required()
def cancel_task(task_id: int):
    user_id = _current_user_id()
    task = _load_task(task_id, user_id)
    if task.status not in {TaskStatus.QUEUED, TaskStatus.PROCESSING}:
        return jsonify({"message": "当前状态无法取消"}), 400
    task.status = TaskStatus.CANCELLED
    db.session.commit()
    return jsonify({"message": "任务已取消"})


@bp.delete("/tasks/<int:task_id>")
@jwt_required()
def delete_task(task_id: int):
    user_id = _current_user_id()
    task = _load_task(task_id, user_id)
    task.is_deleted = True
    db.session.commit()
    return jsonify({"message": "任务已删除"})


@bp.get("/tasks/<int:task_id>/download")
@jwt_required()
def download_task_bundle(task_id: int):
    user_id = _current_user_id()
    task = _load_task(task_id, user_id)
    if not task.result or not task.result.is_success:
        return jsonify({"message": "任务尚未完成"}), 400

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w") as archive:
        archive.writestr("summary.txt", (task.result.summary or "").encode("utf-8"))
        archive.writestr(
            "table_data.json",
            (json.dumps(task.result.table_data or [], ensure_ascii=False)).encode("utf-8"),
        )
        archive.writestr(
            "data_points.json",
            (json.dumps(task.result.data_points or [], ensure_ascii=False)).encode("utf-8"),
        )

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"task-{task.id}-bundle.zip",
    )


@bp.get("/tasks/<int:task_id>/render-template")
@jwt_required()
def render_template_view(task_id: int):
    user_id = _current_user_id()
    template_id = request.args.get("template_id")
    if not template_id:
        return jsonify({"message": "缺少模板标识"}), 400

    task = _load_task(task_id, user_id)
    template = CodeTemplate.query.get(template_id)
    if not template or not _ensure_template_access(template, user_id):
        return jsonify({"message": "模板不可用"}), 404

    try:
        rendered = render_template_for_task(template, task)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    return jsonify({"content": rendered, "language": template.language})


@bp.get("/templates")
@jwt_required()
def list_templates():
    user_id = _current_user_id()
    templates = (
        CodeTemplate.query.filter(
            (CodeTemplate.is_system == True) | (CodeTemplate.user_id == user_id)  # noqa: E712
        )
        .filter_by(is_deleted=False)
        .order_by(CodeTemplate.is_system.desc(), CodeTemplate.created_at.asc())
        .all()
    )
    return jsonify([template.to_dict() for template in templates])


@bp.post("/templates")
@jwt_required()
def create_template():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    language = (payload.get("language") or "").strip()
    content = payload.get("content") or ""
    template_type = payload.get("type", 0)

    if not name:
        return jsonify({"message": "模板名称不能为空"}), 400
    if not language:
        return jsonify({"message": "模板语言不能为空"}), 400

    missing = validate_template_content(content)
    if missing:
        return (
            jsonify({"message": "模板缺少必需占位符", "missing": missing}),
            400,
        )

    parsed_type: int
    try:
        parsed_type = int(template_type)
    except (TypeError, ValueError):
        parsed_type = 0

    template = CodeTemplate(
        name=name,
        language=language,
        content=content,
        user_id=user_id,
        type=parsed_type,
    )
    db.session.add(template)
    db.session.commit()

    return jsonify(template.to_dict()), 201


@bp.patch("/templates/<int:template_id>")
@jwt_required()
def update_template(template_id: int):
    user_id = _current_user_id()
    template = CodeTemplate.query.get_or_404(template_id)
    if not _ensure_template_access(template, user_id):
        return jsonify({"message": "无权访问该模板"}), 404
    if template.is_system:
        return jsonify({"message": "系统模板不支持直接修改"}), 400

    payload = request.get_json() or {}
    name = payload.get("name")
    language = payload.get("language")
    content = payload.get("content")
    template_type = payload.get("type")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "模板名称不能为空"}), 400
        template.name = name

    if language is not None:
        language = language.strip()
        if not language:
            return jsonify({"message": "模板语言不能为空"}), 400
        template.language = language

    if template_type is not None:
        try:
            template.type = int(template_type)
        except (TypeError, ValueError):
            return jsonify({"message": "模板类型必须为数字"}), 400

    if content is not None:
        missing = validate_template_content(content)
        if missing:
            return (
                jsonify({"message": "模板缺少必需占位符", "missing": missing}),
                400,
            )
        template.content = content

    db.session.commit()
    return jsonify(template.to_dict())


@bp.delete("/templates/<int:template_id>")
@jwt_required()
def delete_template(template_id: int):
    user_id = _current_user_id()
    template = CodeTemplate.query.get_or_404(template_id)
    if template.is_system:
        return jsonify({"message": "系统模板不可删除"}), 400
    if template.user_id != user_id:
        return jsonify({"message": "未找到模板"}), 404

    template.is_deleted = True
    db.session.commit()
    return jsonify({"message": "模板已删除"})


@bp.post("/templates/validate")
@jwt_required()
def validate_template():
    payload = request.get_json() or {}
    content = payload.get("content") or ""
    missing = validate_template_content(content)
    return jsonify({"missing": missing, "required": sorted(REQUIRED_TEMPLATE_PLACEHOLDERS)})

