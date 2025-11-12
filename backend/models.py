from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import url_for

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship("ChartApplication", backref="user", lazy=True)
    tasks = db.relationship("ChartTask", backref="user", lazy=True)
    templates = db.relationship("CodeTemplate", backref="owner", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
        }


class ChartApplication(db.Model):
    __tablename__ = "chart_applications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_chart_app_user_name"),
    )

    groups = db.relationship(
        "ChartGroup",
        backref="application",
        cascade="all, delete-orphan",
        lazy=True,
    )
    tasks = db.relationship(
        "ChartTask",
        backref="application",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
        }


class ChartGroup(db.Model):
    __tablename__ = "chart_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey("chart_applications.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("chart_groups.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, default=False)

    children = db.relationship(
        "ChartGroup",
        cascade="all, delete-orphan",
        backref=db.backref("parent", remote_side=[id]),
        lazy=True,
    )
    tasks = db.relationship(
        "ChartTask", backref="group", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "app_id": self.app_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
        }


class ChartTask(db.Model):
    __tablename__ = "chart_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="queued")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey("chart_applications.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("chart_groups.id"), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey("code_templates.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    result = db.relationship(
        "ChartTaskResult",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy=True,
        uselist=False,
    )

    def to_dict(self) -> dict[str, Any]:
        image_url = None
        if self.image_path:
            try:
                image_url = url_for(
                    "charts.serve_upload",
                    filename=self.image_path,
                    _external=True,
                )
            except RuntimeError:  # pragma: no cover - outside request context
                image_url = f"/api/uploads/{self.image_path}"

        result_payload = self.result.to_dict() if self.result else None
        result_data: dict[str, Any] = result_payload or {}

        data: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "user_id": self.user_id,
            "app_id": self.app_id,
            "group_id": self.group_id,
            "application": self.application.to_dict() if self.application else None,
            "group": self.group.to_dict() if self.group else None,
            "image_path": self.image_path,
            "image_url": image_url,
            "template_id": self.template_id,
            "template": self.template.to_dict() if self.template else None,
            "result": result_payload,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "summary": result_data.get("summary"),
            "data_points": result_data.get("data_points", []),
            "table_data": result_data.get("table_data", []),
            "error_message": result_data.get("error_message"),
        }
        return data


class ChartTaskResult(db.Model):
    __tablename__ = "chart_task_results"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("chart_tasks.id"), nullable=False, unique=True)
    is_success = db.Column(db.Boolean, default=False)
    summary = db.Column(db.Text, nullable=True)
    data_points = db.Column(db.JSON, nullable=True)
    table_data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    task = db.relationship("ChartTask", back_populates="result", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "is_success": bool(self.is_success),
            "summary": self.summary,
            "data_points": self.data_points or [],
            "table_data": self.table_data or [],
            "error_message": self.error_message,
        }


class CodeTemplate(db.Model):
    __tablename__ = "code_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    language = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_system = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.CheckConstraint(
            "language IN ('java', 'kotlin')",
            name="ck_code_templates_language",
        ),
    )

    tasks = db.relationship("ChartTask", backref="template", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "content": self.content,
            "is_system": self.is_system,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
