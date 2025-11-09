from __future__ import annotations

from datetime import datetime
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    groups = db.relationship("ChartGroup", backref="user", lazy=True)
    tasks = db.relationship("ChartTask", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


class ChartGroup(db.Model):
    __tablename__ = "chart_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship("ChartTask", backref="group", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


class ChartTask(db.Model):
    __tablename__ = "chart_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="pending")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("chart_groups.id"), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    data_points = db.Column(db.JSON, nullable=True)
    table_data = db.Column(db.JSON, nullable=True)
    generated_code = db.Column(db.Text, nullable=True)
    custom_code = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        from flask import url_for

        image_url = (
            url_for("charts.serve_upload", filename=self.image_path, _external=True)
            if self.image_path
            else None
        )
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "group_id": self.group_id,
            "image_path": self.image_path,
            "image_url": image_url,
            "summary": self.summary,
            "description": self.description,
            "data_points": self.data_points or [],
            "table_data": self.table_data or [],
            "generated_code": self.generated_code,
            "custom_code": self.custom_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
