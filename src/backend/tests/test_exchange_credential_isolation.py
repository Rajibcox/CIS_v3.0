"""Regression tests for exchange credential isolation in paper-only mode."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from jose import jwt

from src.backend.api.server import create_app
from src.backend.utils.config import Settings


@pytest.fixture
def exchange_client():
    settings = Settings(
        _env_file=None,
        secret_key="test-only-signing-key-with-at-least-32-characters",
        algorithm="HS256",
        access_token_expire_minutes=30,
        admin_username="test-admin",
        admin_password_hash=PasswordHasher().hash("test-password-long-enough"),
        database_url="sqlite:///:memory:",
    )
    app = create_app(SimpleNamespace(settings=settings))
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "test-admin",
            "username": "test-admin",
            "role": "admin",
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    return TestClient(app), {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "credential_payload",
    [
        {"api_key": "sentinel-api-key"},
        {"api_secret": "sentinel-api-secret"},
        {"passphrase": "sentinel-passphrase"},
        {
            "api_key": "sentinel-api-key",
            "api_secret": "sentinel-api-secret",
            "passphrase": "sentinel-passphrase",
        },
    ],
)
def test_exchange_config_rejects_credentials_without_echoing_or_retaining_them(
    exchange_client, credential_payload
):
    client, headers = exchange_client
    payload = {
        "name": "binance",
        "enabled": True,
        "testnet": True,
        "margin_mode": "isolated",
        "position_mode": "one_way",
        "rate_limit_buffer": 0.8,
        "recv_window": 5000,
        **credential_payload,
    }

    response = client.put(
        "/api/v1/config/exchanges/binance", json=payload, headers=headers
    )

    assert response.status_code == 400
    assert "sentinel" not in response.text
    assert "api_secret" not in response.text

    exchange_response = client.get("/api/v1/config/exchanges", headers=headers)
    assert exchange_response.status_code == 200
    binance = next(item for item in exchange_response.json() if item["name"] == "binance")
    assert binance["has_credentials"] is False
    assert binance["connection_status"] == "not_configured"


def test_exchange_config_get_never_exposes_credential_fields(exchange_client):
    client, headers = exchange_client

    response = client.get("/api/v1/config", headers=headers)

    assert response.status_code == 200
    for exchange in response.json()["exchanges"].values():
        assert "api_key" not in exchange
        assert "api_secret" not in exchange
        assert "passphrase" not in exchange


def test_non_secret_exchange_settings_can_be_updated(exchange_client):
    client, headers = exchange_client
    payload = {
        "name": "binance",
        "enabled": False,
        "testnet": True,
        "margin_mode": "isolated",
        "position_mode": "one_way",
        "rate_limit_buffer": 0.75,
        "recv_window": 6000,
    }

    response = client.put(
        "/api/v1/config/exchanges/binance", json=payload, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_exchange_connection_test_does_not_claim_mock_success(exchange_client):
    client, headers = exchange_client

    response = client.post(
        "/api/v1/config/exchanges/binance/test", headers=headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Exchange connectivity testing is unavailable in paper-only mode."
    )
