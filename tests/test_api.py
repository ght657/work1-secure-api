"""Functional + security tests for the API (pytest)."""
import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _login(client, username="alice", password="Alice#Strong1"):
    r = client.post("/auth/login", json={"login": username, "password": password})
    assert r.status_code == 200
    return r.get_json()["token"]


# --- Authentication (JWT + bcrypt) ----------------------------------------

def test_login_success_issues_token(client):
    r = client.post("/auth/login", json={"login": "alice", "password": "Alice#Strong1"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["token"]
    assert body["user"]["username"] == "alice"


def test_login_wrong_password_rejected(client):
    r = client.post("/auth/login", json={"login": "alice", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user_same_error_as_wrong_password(client):
    r = client.post("/auth/login", json={"login": "nobody", "password": "x"})
    assert r.status_code == 401
    assert r.get_json()["error"] == "Invalid credentials"


def test_passwords_stored_as_bcrypt_hashes(client):
    with client.application.app_context():
        from app.models import User

        for u in User.query.all():
            assert u.password_hash.startswith("$2")  # bcrypt hash format
            assert "Admin!" not in u.password_hash
            assert "Alice#" not in u.password_hash


# --- Broken Authentication protection -------------------------------------

def test_data_endpoint_denied_without_token(client):
    r = client.get("/api/data")
    assert r.status_code == 401


def test_data_endpoint_denied_with_invalid_token(client):
    r = client.get(
        "/api/data", headers={"Authorization": "Bearer not.a.valid.token"}
    )
    assert r.status_code == 401


def test_data_endpoint_works_with_valid_token(client):
    token = _login(client)
    r = client.get("/api/data", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "posts" in r.get_json()


def test_create_post_requires_token(client):
    r = client.post("/api/posts", json={"title": "x", "body": "y"})
    assert r.status_code == 401


# --- SQL injection protection ---------------------------------------------

def test_sqli_payload_treated_as_data(client):
    token = _login(client)
    payload = "' OR '1'='1"
    r = client.get(
        "/api/users/search",
        query_string={"q": payload},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    # The payload is data, not SQL: no rows match a username containing it.
    assert r.get_json()["results"] == []


def test_sqli_union_payload_does_not_dump_table(client):
    token = _login(client)
    payload = "'; DROP TABLE users; --"
    r = client.get(
        "/api/users/search",
        query_string={"q": payload},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.get_json()["results"] == []
    # users table still exists and login still works
    assert _login(client)


# --- XSS protection ---------------------------------------------------------

def test_xss_payload_is_escaped_in_response(client):
    token = _login(client)
    r = client.post(
        "/api/posts",
        json={"title": "<script>alert('xss')</script>", "body": "<img src=x onerror=alert(1)>"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201

    r2 = client.get("/api/data", headers={"Authorization": f"Bearer {token}"})
    raw = r2.get_data(as_text=True)
    # The raw <script> tag must never reach the client.
    assert "<script>" not in raw
    # Escaped form is present instead.
    assert ("&lt;script&gt;" in raw) or ("\\u003cscript\\u003e" in raw)
