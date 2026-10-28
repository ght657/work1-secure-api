"""Application configuration. Secrets come from environment variables."""
import os


class Config:
    # SECRET_KEY signs the JWT tokens. Always override via the environment in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-do-not-use-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_MINUTES = 60

    # SQLite database (works out of the box; switch to PostgreSQL URL in production).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # bcrypt cost factor: 12 rounds (~100 ms per hash on modern hardware).
    BCRYPT_ROUNDS = 12
