"""Regression tests for the API's restricted CORS policy."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.backend.api.server import create_app
from src.backend.utils.config import Settings


def make_client():
    settings = Settings(
        _env_file=None,
        secret_key="test-only-signing-key-with-at-least-32-characters",
        algorithm="HS256",
        access_token_expire_minutes=30,
        admin_username="test-admin",
        admin_password_hash="$argon2id$test-hash-not-used-by-these-tests",
        database_url="sqlite:///:memory:",
    )
    return TestClient(create_app(SimpleNamespace(settings=settings)))


def test_cors_allows_only_the_configured_local_frontend_origin():
    with make_client() as client:
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_cors_rejects_unlisted_origins():
    with make_client() as client:
        response = client.get(
            "/health",
            headers={"Origin": "https://untrusted.example"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_frontend_preflight_for_authorized_api_methods():
    with make_client() as client:
        response = client.options(
            "/api/v1/overview/quick-stats",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


def test_cors_preflight_rejects_unapproved_methods():
    with make_client() as client:
        response = client.options(
            "/api/v1/overview/quick-stats",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PATCH",
            },
        )

    assert response.status_code == 400
