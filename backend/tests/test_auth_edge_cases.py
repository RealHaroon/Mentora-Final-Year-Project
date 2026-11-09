"""
Phase 8 §2.2 — auth edge cases: wrong password, expired token, the
forgot-password round trip, and delete-account actually revoking access.
"""

import time

import jwt

from config import settings
from database.models import User


def _register(client, email):
    return client.post("/auth/register", json={
        "first_name": "Test", "last_name": "Auth", "email": email,
        "password": "testpass123", "confirm_password": "testpass123",
        "university": "Test University", "exam_goal": "sindh_university",
    })


def test_wrong_password_rejected(client):
    _register(client, "auth-wrong-pw@example.com")
    r = client.post("/auth/login", json={"email": "auth-wrong-pw@example.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_duplicate_registration_rejected(client):
    _register(client, "auth-dup@example.com")
    r = _register(client, "auth-dup@example.com")
    assert r.status_code == 409


def test_expired_token_rejected(client):
    reg = _register(client, "auth-expired@example.com")
    token = reg.json()["access_token"]
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

    # Re-sign with an already-past expiry instead of sleeping past the real
    # 7-day expiry — same validation code path (jwt.decode's own exp check),
    # without an unreasonably slow test.
    expired_payload = {**payload, "exp": int(time.time()) - 10}
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    r = client.get("/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401


def test_forgot_password_round_trip(client, db_session):
    _register(client, "auth-forgot@example.com")

    r = client.post("/auth/forgot-password", json={"email": "auth-forgot@example.com"})
    assert r.status_code == 200

    user = db_session.query(User).filter(User.email == "auth-forgot@example.com").first()
    assert user.reset_code is not None

    r = client.post("/auth/reset-password", json={
        "reset_code": user.reset_code, "new_password": "newpass456", "confirm_password": "newpass456",
    })
    assert r.status_code == 200

    old_login = client.post("/auth/login", json={"email": "auth-forgot@example.com", "password": "testpass123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", json={"email": "auth-forgot@example.com", "password": "newpass456"})
    assert new_login.status_code == 200


def test_forgot_password_unknown_email_does_not_leak_existence(client):
    r = client.post("/auth/forgot-password", json={"email": "does-not-exist@example.com"})
    assert r.status_code == 200
    assert "sent" in r.json()["detail"].lower()


def test_delete_account_revokes_access(client):
    reg = _register(client, "auth-delete-me@example.com")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    delete = client.delete("/users/me", headers=headers)
    assert delete.status_code == 204

    login_again = client.post("/auth/login", json={"email": "auth-delete-me@example.com", "password": "testpass123"})
    assert login_again.status_code == 401

    # the OLD token must also stop working, not just a fresh login attempt
    me = client.get("/users/me", headers=headers)
    assert me.status_code == 401
