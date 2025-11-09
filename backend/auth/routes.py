from __future__ import annotations

from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from ..extensions import db
from ..models import User
from . import bp


@bp.post("/register")
def register():
    payload = request.get_json() or {}
    name = payload.get("name")
    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password")

    if not all([name, email, password]):
        return jsonify({"message": "Missing required fields."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered."}), 400

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registration successful."}), 201


@bp.post("/login")
def login():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not password or not user.check_password(password):
        return jsonify({"message": "Invalid credentials."}), 401

    token = create_access_token(identity=user.id)
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.post("/change-password")
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    payload = request.get_json() or {}
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")

    if not all([current_password, new_password]):
        return jsonify({"message": "Missing required fields."}), 400

    user = User.query.get(user_id)
    if not user or not user.check_password(current_password):
        return jsonify({"message": "Current password is incorrect."}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password updated."})
