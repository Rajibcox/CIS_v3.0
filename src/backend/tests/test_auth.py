"""Security tests for local administrator REST authentication."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from jose import jwt

from src.backend.api.server import create_app
from src.backend.api.auth import validate_auth_settings
from src.backend.utils.config import Settings


@pytest.fixture
def auth_config():
    settings = Settings(
        _env_file=None,
        secret_key="test-only-signing-key-with-at-least-32-characters",
        algorithm="HS256",
        access_token_expire_minutes=30,
        admin_username="test-admin",
        admin_password_hash=PasswordHasher().hash("test-password-long-enough"),
        database_url="sqlite:///:memory:",
    )
    return SimpleNamespace(settings=settings)


@pytest.fixture
def client(auth_config):
    app = create_app(auth_config)
    return TestClient(app)


def test_protected_rest_route_rejects_missing_token(client):
    response = client.get("/api/v1/overview/quick-stats")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("token", ["not-a-jwt", "a.b.c", ""])
def test_protected_rest_route_rejects_malformed_token(client, token):
    response = client.get(
        "/api/v1/overview/quick-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_login_returns_signed_access_token_and_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "test-password-long-enough"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["user"] == {
        "id": "test-admin",
        "username": "test-admin",
        "role": "admin",
    }
    assert body["access_token"]
    assert "password" not in body
    assert "secret_key" not in body


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_rejects_wrong_username(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "another-user", "password": "test-password-long-enough"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_valid_token_authorizes_route_and_me(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "test-admin", "password": "test-password-long-enough"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_response = client.get("/api/v1/auth/me", headers=headers)
    protected_response = client.get("/api/v1/overview/quick-stats", headers=headers)

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "test-admin"
    assert protected_response.status_code == 200


def test_expired_token_is_rejected(client, auth_config):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "test-admin",
            "username": "test-admin",
            "role": "admin",
            "token_type": "access",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        auth_config.settings.secret_key,
        algorithm="HS256",
    )
    response = client.get(
        "/api/v1/overview/quick-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_invalid_signature_is_rejected(client):
    token = jwt.encode(
        {
            "sub": "test-admin",
            "username": "test-admin",
            "role": "admin",
            "token_type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "different-signing-key-that-is-also-long-enough",
        algorithm="HS256",
    )
    response = client.get(
        "/api/v1/overview/quick-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_health_and_api_info_remain_public(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api-info").status_code == 200


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "change-me"},
        {"secret_key": "short"},
        {"admin_username": ""},
        {"admin_password_hash": "plaintext-password"},
    ],
)
def test_auth_configuration_fails_closed(auth_config, overrides):
    for name, value in overrides.items():
        setattr(auth_config.settings, name, value)
    with pytest.raises(ValueError):
        validate_auth_settings(auth_config.settings)
