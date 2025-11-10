from __future__ import annotations

import uuid
from pathlib import Path

from flask import abort, current_app, jsonify, request, send_from_directory, url_for
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


@bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


@bp.get("/groups")
@jwt_required()
def list_groups():
    user_id = _current_user_id()
    groups = ChartGroup.query.filter_by(user_id=user_id).order_by(ChartGroup.created_at.desc()).all()
    return jsonify([group.to_dict() for group in groups])


@bp.post("/groups")
@jwt_required()
def create_group():
    user_id = _current_user_id()
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"message": "Group name is required."}), 400
    group = ChartGroup(name=name, user_id=user_id)
    db.session.add(group)
    db.session.commit()
    return jsonify(group.to_dict()), 201


@bp.delete("/groups/<int:group_id>")
@jwt_required()
def delete_group(group_id: int):
    user_id = _current_user_id()
    group = ChartGroup.query.get_or_404(group_id)
    if group.user_id != user_id:
        return jsonify({"message": "Not found."}), 404
    if group.tasks:
        return jsonify({"message": "Cannot delete a group with tasks."}), 400
    db.session.delete(group)
    db.session.commit()
    return jsonify({"message": "Group deleted."})


@bp.get("/tasks")
@jwt_required()
def list_tasks():
    user_id = _current_user_id()
    group_id = request.args.get("group_id")
    query = ChartTask.query.filter_by(user_id=user_id)
    if group_id:
        query = query.filter_by(group_id=int(group_id))
    tasks = query.order_by(ChartTask.created_at.desc()).all()
    return jsonify([task.to_dict() for task in tasks])


@bp.post("/tasks")
@jwt_required()
def create_task():
    user_id = _current_user_id()
    if "image" not in request.files:
        return jsonify({"message": "Image file is required."}), 400

    image_file = request.files["image"]
    title = request.form.get("title") or Path(image_file.filename or "chart").stem
    group_id = request.form.get("group_id")

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

    task = ChartTask(
        title=title,
        user_id=user_id,
        group_id=int(group_id) if group_id else None,
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
    custom_code = payload.get("custom_code")
    task.custom_code = custom_code
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

    public_url = url_for("charts.serve_upload", filename=task.image_path, _external=True)
    regenerated = build_accessible_code(public_url, task.summary, task.data_points)
    task.generated_code = regenerated
    db.session.commit()
    return jsonify(task.to_dict())
