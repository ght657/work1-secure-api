"""Protected API endpoints (all /api/* routes require a valid JWT)."""
from flask import Blueprint, jsonify, request
from markupsafe import escape
from sqlalchemy import bindparam, select

from . import db
from .models import Post, User
from .security import token_required

bp = Blueprint("api", __name__)


def _post_to_dict(post):
    """Serialize a post.

    XSS protection: every user-controlled string is HTML-escaped with
    markupsafe.escape() before it is returned to the client, so a stored
    payload like <script>alert(1)</script> is returned as harmless text.
    Flask's jsonify additionally escapes HTML-sensitive characters in JSON.
    """
    return {
        "id": post.id,
        "title": escape(post.title),
        "body": escape(post.body),
        "author": escape(post.author.username),
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


@bp.route("/health", methods=["GET"])
def health():
    """Public health-check endpoint (used for regression testing)."""
    return jsonify({"status": "ok"})


@bp.route("/api/data", methods=["GET"])
@token_required
def get_data(current_user):
    """Return the list of posts. Access is restricted to authenticated users."""
    posts = db.session.execute(select(Post).order_by(Post.id)).scalars().all()
    return jsonify(
        {"user": current_user.username, "posts": [_post_to_dict(p) for p in posts]}
    )


@bp.route("/api/users/search", methods=["GET"])
@token_required
def search_users(current_user):
    """Search users by name (custom endpoint #3).

    SQLi protection in action: the search term is passed as a bound parameter
    (bindparam), so payloads like  ' OR '1'='1  are treated as plain data.
    """
    q = request.args.get("q", "")
    stmt = select(User).where(User.username.like(bindparam("q")))
    users = db.session.execute(stmt, {"q": f"%{q}%"}).scalars().all()
    return jsonify(
        {"results": [{"id": u.id, "username": escape(u.username)} for u in users]}
    )


@bp.route("/api/posts", methods=["POST"])
@token_required
def create_post(current_user):
    """Create a post (authenticated users only)."""
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", ""))[:200]
    body = str(data.get("body", ""))[:5000]
    if not title.strip():
        return jsonify({"error": "title is required"}), 400

    post = Post(title=title, body=body, author_id=current_user.id)
    db.session.add(post)
    db.session.commit()
    return jsonify({"created": _post_to_dict(post)}), 201
