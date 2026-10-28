"""POST /auth/login - authenticates the user and issues a JWT."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from . import db
from .models import User
from .security import generate_token, verify_password

bp = Blueprint("auth", __name__)


@bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "login" not in data or "password" not in data:
        return jsonify({"error": "login and password are required"}), 400

    # SQLi protection: the username is bound as a query parameter by SQLAlchemy.
    # Never do: f"... WHERE username = '{data['login']}'"  <-- vulnerable!
    user = db.session.execute(
        select(User).where(User.username == data["login"])
    ).scalar_one_or_none()

    # Same generic error for "user not found" and "wrong password" to avoid
    # user-enumeration attacks (an aspect of Broken Authentication).
    if user is None or not verify_password(data["password"], user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user)
    return (
        jsonify(
            {
                "token": token,
                "user": {"id": user.id, "username": user.username, "role": user.role},
            }
        ),
        200,
    )
