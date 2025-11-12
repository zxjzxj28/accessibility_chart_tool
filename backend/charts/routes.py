from __future__ import annotations

import io
import json
import uuid
import zipfile
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
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    ChartApplication,
    ChartGroup,
    ChartTask,
    ChartTaskResult,
    CodeTemplate,
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


def _application_payload(app: ChartApplication) -> dict[str, Any]:
    groups = [group for group in app.groups if not group.is_deleted]
    nodes: dict[int, dict[str, Any]] = {}
    ordered = sorted(groups, key=lambda g: (g.parent_id or 0, g.created_at))
    for group in ordered:
        payload = group.to_dict()
        payload["children"] = []
        nodes[group.id] = payload

    roots: list[dict[str, Any]] = []
    for group in ordered:
        parent_id = group.parent_id
        node = nodes[group.id]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    payload = app.to_dict()
    payload["groups"] = roots
    return payload


def _ensure_template_access(template: CodeTemplate, user_id: int) -> bool:
    if template.is_system:
        return not template.is_deleted
    return template.user_id == user_id and not template.is_deleted


@bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


@bp.get("/applications")
@jwt_required()
def list_applications():
    user_id = _current_user_id()
    apps = (
        ChartApplication.query.filter_by(user_id=user_id, is_deleted=False)
        .options(joinedload(ChartApplication.groups))
        .order_by(ChartApplication.created_at.asc())
        .all()
    )
    return jsonify([_application_payload(app) for app in apps])


@bp.post("/groups")
@jwt_required()
def create_group():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    app_id = payload.get("app_id")
    parent_id = payload.get("parent_id")

    if not name:
        return jsonify({"message": "分组名称不能为空"}), 400
    if not app_id:
        return jsonify({"message": "缺少应用标识"}), 400

    application = ChartApplication.query.filter_by(
        id=int(app_id), user_id=user_id, is_deleted=False
    ).first()
    if not application:
        return jsonify({"message": "应用不存在"}), 404

    parent = None
    if parent_id:
        parent = ChartGroup.query.get(parent_id)
        if not parent or parent.is_deleted or parent.application != application:
            return jsonify({"message": "父分组无效"}), 400

    group = ChartGroup(name=name, application=application, parent=parent)
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
    if group.is_deleted or group.application.user_id != user_id:
        return jsonify({"message": "未找到分组"}), 404

    payload = request.get_json() or {}
    name = payload.get("name")
    parent_id = payload.get("parent_id")
    application_id = payload.get("application_id")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "分组名称不能为空"}), 400
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
            return jsonify({"message": "不能将分组设为自己的子级"}), 400
        if parent_id:
            parent = ChartGroup.query.get(parent_id)
            if not parent or parent.is_deleted or parent.application != group.application:
                return jsonify({"message": "父分组无效"}), 400
            ancestor = parent
            while ancestor:
                if ancestor.id == group.id:
                    return jsonify({"message": "不能出现循环嵌套"}), 400
                ancestor = ancestor.parent
            group.parent = parent
        else:
            group.parent = None

    db.session.commit()
    data = group.to_dict()
    data["children"] = [child.to_dict() for child in group.children if not child.is_deleted]
    return jsonify(data)


def _soft_delete_group(group: ChartGroup) -> None:
    group.is_deleted = True
    for task in group.tasks:
        task.is_deleted = True
    for child in group.children:
        if not child.is_deleted:
            _soft_delete_group(child)


@bp.delete("/groups/<int:group_id>")
@jwt_required()
def delete_group(group_id: int):
    user_id = _current_user_id()
    group = ChartGroup.query.get_or_404(group_id)
    if group.is_deleted or group.application.user_id != user_id:
        return jsonify({"message": "未找到分组"}), 404

    _soft_delete_group(group)
    db.session.commit()
    return jsonify({"message": "分组已删除"})


def _ensure_default_application(user_id: int) -> ChartApplication:
    default_app = (
        ChartApplication.query.filter_by(
            user_id=user_id, name="默认应用"
        )
        .order_by(ChartApplication.created_at.asc())
        .first()
    )
    if default_app:
        if default_app.is_deleted:
            default_app.is_deleted = False
            db.session.commit()
        return default_app

    default_app = ChartApplication(name="默认应用", user_id=user_id)
    db.session.add(default_app)
    db.session.commit()
    return default_app


def _resolve_application(user_id: int, name: str | None, app_id: str | None) -> ChartApplication:
    if app_id:
        try:
            app_int = int(app_id)
        except (TypeError, ValueError):
            raise ValueError("应用不存在") from None
        application = ChartApplication.query.filter_by(
            id=app_int, user_id=user_id
        ).first()
        if not application:
            raise ValueError("应用不存在")
        if application.is_deleted:
            application.is_deleted = False
            db.session.commit()
        return application

    if name:
        match = (
            ChartApplication.query.filter(
                ChartApplication.user_id == user_id,
                func.lower(ChartApplication.name) == name.lower(),
            )
            .order_by(ChartApplication.created_at.asc())
            .first()
        )
        if match:
            if match.is_deleted:
                match.is_deleted = False
                db.session.commit()
            return match
        application = ChartApplication(name=name, user_id=user_id)
        db.session.add(application)
        db.session.commit()
        return application

    return _ensure_default_application(user_id)


def _resolve_group(app: ChartApplication, group_id: str | None) -> ChartGroup | None:
    if not group_id:
        return None
    try:
        group_int = int(group_id)
    except (TypeError, ValueError):
        raise ValueError("分组不存在") from None
    group = ChartGroup.query.get(group_int)
    if not group or group.is_deleted or group.application != app:
        raise ValueError("分组不存在")
    return group


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


def _save_upload(file_storage) -> str:
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file_storage.filename or "chart.png")
    ext = Path(filename).suffix or ".png"
    target = upload_folder / f"{uuid.uuid4().hex}{ext}"
    file_storage.save(target)
    return target.name


@bp.get("/tasks")
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    keyword = (request.args.get("keyword") or "").strip()
    app_id = request.args.get("app_id")
    group_id = request.args.get("group_id")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 12)), 50)

    query = (
        ChartTask.query.options(
            joinedload(ChartTask.application),
            joinedload(ChartTask.group),
            joinedload(ChartTask.template),
            joinedload(ChartTask.result),
        )
        .filter_by(user_id=user_id, is_deleted=False)
        .order_by(ChartTask.created_at.desc())
    )

    if app_id:
        query = query.filter(ChartTask.app_id == int(app_id))
    if group_id:
        query = query.filter(ChartTask.group_id == int(group_id))
    if keyword:
        like = f"%{keyword}%"
        query = query.outerjoin(ChartTaskResult).filter(
            or_(ChartTask.title.ilike(like), ChartTaskResult.summary.ilike(like))
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
    if "file" not in request.files:
        return jsonify({"message": "请上传图表图片"}), 400

    file_storage = request.files["file"]
    if file_storage.filename == "":
        return jsonify({"message": "请选择有效的图片文件"}), 400

    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify({"message": "任务标题不能为空"}), 400

    application_name = (request.form.get("application_name") or "").strip()
    application_id = request.form.get("application_id")
    group_id = request.form.get("group_id")
    template_id = request.form.get("template_id")

    try:
        application = _resolve_application(user_id, application_name, application_id)
        group = _resolve_group(application, group_id)
        template = _resolve_template(user_id, template_id)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    filename = _save_upload(file_storage)
    public_url = url_for("charts.serve_upload", filename=filename, _external=True)

    task = ChartTask(
        title=title,
        status="queued",
        user_id=user_id,
        application=application,
        group=group,
        image_path=filename,
        template=template,
    )
    db.session.add(task)
    db.session.commit()

    worker.enqueue(TaskPayload(task_id=task.id, image_path=str(Path(current_app.config["UPLOAD_FOLDER"]) / filename), public_image_url=public_url))

    return jsonify(task.to_dict()), 201


def _load_task(task_id: int, user_id: int) -> ChartTask:
    task = (
        ChartTask.query.options(
            joinedload(ChartTask.application),
            joinedload(ChartTask.group),
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

    title = payload.get("title")
    if title is not None:
        title = title.strip()
        if not title:
            return jsonify({"message": "任务标题不能为空"}), 400
        task.title = title

    app_id = payload.get("app_id")
    group_id = payload.get("group_id")
    template_id = payload.get("template_id")

    try:
        application = task.application
        if app_id:
            application = _resolve_application(user_id, None, app_id)
            task.application = application
            task.app_id = application.id
        if group_id is not None:
            group = _resolve_group(application, group_id)
            task.group = group
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
    if task.status not in {"queued", "processing"}:
        return jsonify({"message": "当前状态无法取消"}), 400
    task.status = "cancelled"
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
    language = (payload.get("language") or "").strip().lower()
    content = payload.get("content") or ""

    if not name:
        return jsonify({"message": "模板名称不能为空"}), 400
    if language not in {"java", "kotlin"}:
        return jsonify({"message": "仅支持 Java 或 Kotlin 模板"}), 400

    missing = validate_template_content(content)
    if missing:
        return (
            jsonify({"message": "模板缺少必需占位符", "missing": missing}),
            400,
        )

    template = CodeTemplate(
        name=name,
        language=language,
        content=content,
        user_id=user_id,
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

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"message": "模板名称不能为空"}), 400
        template.name = name

    if language is not None:
        language = language.strip().lower()
        if language not in {"java", "kotlin"}:
            return jsonify({"message": "仅支持 Java 或 Kotlin 模板"}), 400
        template.language = language

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
