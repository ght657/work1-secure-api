"""Application factory."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from .config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from . import models  # noqa: F401  (register models with the extension)
    from .auth import bp as auth_bp
    from .routes import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        _seed_demo_data()

    return app


def _seed_demo_data():
    """Create demo users/posts on first run.

    The plaintext passwords below exist only in this educational seed file;
    the database stores exclusively bcrypt hashes.
    """
    from .models import Post, User
    from .security import hash_password

    if db.session.execute(select(User.id).limit(1)).scalar_one_or_none() is not None:
        return  # already seeded

    admin = User(username="admin", password_hash=hash_password("Admin!23456"), role="admin")
    alice = User(username="alice", password_hash=hash_password("Alice#Strong1"), role="user")
    bob = User(username="bob", password_hash=hash_password("Bob$Secure9"), role="user")
    db.session.add_all([admin, alice, bob])
    db.session.flush()

    db.session.add_all(
        [
            Post(
                title="Welcome to the secure API",
                body="This API is protected with JWT authentication.",
                author_id=alice.id,
            ),
            Post(
                title="Security lab demo",
                body="SQLi and XSS protections are enabled.",
                author_id=bob.id,
            ),
        ]
    )
    db.session.commit()
