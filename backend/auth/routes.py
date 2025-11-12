from __future__ import annotations

from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from ..extensions import db
from ..models import User
from . import bp


@bp.post("/register")
def register():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").lower().strip()
    username = (payload.get("username") or "").strip()
    password = payload.get("password")

    if not all([email, username, password]):
        return jsonify({"message": "Missing required fields."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already registered."}), 400

    user = User(email=email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registration successful."}), 201


@bp.post("/login")
def login():
    payload = request.get_json() or {}
    identifier = (payload.get("identifier") or "").strip()
    password = payload.get("password")

    user: User | None = None
    if "@" in identifier:
        user = User.query.filter_by(email=identifier.lower()).first()
    else:
        user = User.query.filter_by(username=identifier).first()

    if not user or not password or not user.check_password(password):
        return jsonify({"message": "Invalid credentials."}), 401

    audience = current_app.config.get("JWT_DECODE_AUDIENCE")
    additional_claims = {"aud": audience} if audience else None
    token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.post("/change-password")
@jwt_required()
def change_password():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid authentication token."}), 401
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
