from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TaskStatus(IntEnum):
    QUEUED = 0
    PROCESSING = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4


class TaskType(IntEnum):
    UPLOAD = 0
    METADATA = 1


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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


class ChartTask(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False, default=TaskType.UPLOAD.value)
    status = db.Column(db.SmallInteger, nullable=False, default=TaskStatus.QUEUED.value)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    template_id = db.Column(db.BigInteger, db.ForeignKey("templates.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    result = db.relationship(
        "ChartTaskResult",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy=True,
        uselist=False,
    )

    def to_dict(self) -> dict[str, Any]:
        result_payload = self.result.to_dict() if self.result else None
        result_data: dict[str, Any] = result_payload or {}

        return {
            "id": self.id,
            "name": self.name,
            "type": int(self.type),
            "status": int(self.status),
            "user_id": self.user_id,
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


class ChartTaskResult(db.Model):
    __tablename__ = "task_results"

    id = db.Column(db.BigInteger, primary_key=True)
    task_id = db.Column(
        db.BigInteger, db.ForeignKey("tasks.id"), nullable=False, unique=True
    )
    is_success = db.Column(db.Boolean, default=False, nullable=False)
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
    __tablename__ = "templates"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False, default=0)
    language = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    tasks = db.relationship("ChartTask", backref="template", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": int(self.type),
            "language": self.language,
            "content": self.content,
            "is_system": self.is_system,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
