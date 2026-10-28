"""Entry point: starts the secure REST API on 127.0.0.1:5000."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug is intentionally disabled in production-style runs.
    app.run(host="127.0.0.1", port=5000, debug=False)
