"""Security helpers used across the application.

- hash_password / verify_password : bcrypt password hashing (OWASP recommendation).
- generate_token                   : issues a signed JWT after successful login.
- token_required                   : middleware that verifies the JWT on every
                                     protected endpoint (Broken Authentication protection).
"""
import functools
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import current_app, jsonify, request

from . import db
from .models import User


def hash_password(plaintext: str) -> str:
    """Hash a password with bcrypt (salted, slow, adaptive cost)."""
    if not plaintext or len(plaintext) > 72:
        # bcrypt only uses the first 72 bytes; reject longer input explicitly.
        raise ValueError("Password must be 1-72 characters long")
    salt = bcrypt.gensalt(rounds=current_app.config["BCRYPT_ROUNDS"])
    return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Constant-time password verification via bcrypt.checkpw."""
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_token(user: User) -> str:
    """Create a signed JWT with an expiration time (iat/exp claims)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"]),
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def token_required(fn):
    """Decorator: reject requests without a valid Bearer token (401).

    The signature (HS256) guarantees the token was issued by this server and
    has not been tampered with; the `exp` claim is checked automatically.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=[current_app.config["JWT_ALGORITHM"]],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = db.session.get(User, int(payload["sub"]))
        if user is None:
            return jsonify({"error": "Unknown user"}), 401
        return fn(user, *args, **kwargs)

    return wrapper
