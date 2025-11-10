from __future__ import annotations

from datetime import datetime
from typing import Any

import json

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
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
            "username": self.username,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


class ChartGroup(db.Model):
    __tablename__ = "chart_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("chart_groups.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship(
        "ChartGroup",
        cascade="all, delete-orphan",
        backref=db.backref("parent", remote_side=[id]),
        lazy=True,
    )
    tasks = db.relationship("ChartTask", backref="group", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
        }


class ChartTask(db.Model):
    __tablename__ = "chart_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="pending")
    language = db.Column(db.String(20), default="java")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("chart_groups.id"), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    data_points = db.Column(db.JSON, nullable=True)
    table_data = db.Column(db.JSON, nullable=True)
    generated_code = db.Column(db.Text, nullable=True)
    java_code = db.Column(db.Text, nullable=True)
    kotlin_code = db.Column(db.Text, nullable=True)
    integration_doc = db.Column(db.JSON, nullable=True)
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

        custom_payload: Any = None
        if self.custom_code:
            try:
                custom_payload = json.loads(self.custom_code)
            except (TypeError, json.JSONDecodeError):
                custom_payload = {"legacy": self.custom_code}

        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "language": self.language,
            "group_id": self.group_id,
            "image_path": self.image_path,
            "image_url": image_url,
            "summary": self.summary,
            "description": self.description,
            "data_points": self.data_points or [],
            "table_data": self.table_data or [],
            "generated_code": self.generated_code,
            "java_code": self.java_code,
            "kotlin_code": self.kotlin_code,
            "integration_doc": self.integration_doc or {},
            "custom_code": custom_payload,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
