"""Security tests for authenticated WebSocket handshakes."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from jose import jwt

from src.backend import main
from src.backend.services.websocket_manager import ConnectionManager
from src.backend.utils.config import Settings


class AcceptingWebSocketManager:
    def __init__(self):
        self.called = False

    async def handle_websocket(self, websocket):
        self.called = True
        await websocket.accept(subprotocol="quantum-trader")
        await websocket.send_text('{"type":"welcome","channel":"system","data":{}}')


@pytest.fixture
def websocket_setup(monkeypatch):
    settings = Settings(
        _env_file=None,
        secret_key="test-only-signing-key-with-at-least-32-characters",
        algorithm="HS256",
        access_token_expire_minutes=30,
        admin_username="test-admin",
        admin_password_hash="$argon2id$test-hash-not-used-by-this-test",
        database_url="sqlite:///:memory:",
    )
    config = SimpleNamespace(settings=settings)
    manager = AcceptingWebSocketManager()
    monkeypatch.setattr(main, "config", config)
    monkeypatch.setattr(
        main,
        "get_service_container",
        lambda: SimpleNamespace(websocket_manager=manager),
    )
    app = main.create_app_with_services()
    return TestClient(app), settings, manager


def make_token(settings, *, expires_in=300, username="test-admin"):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "username": username,
            "role": "admin",
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def test_websocket_rejects_missing_authentication(websocket_setup):
    client, _, manager = websocket_setup
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", subprotocols=["quantum-trader"]):
            pass
    assert manager.called is False


@pytest.mark.parametrize("token", ["not-a-jwt", "a.b.c"])
def test_websocket_rejects_malformed_tokens(websocket_setup, token):
    client, _, manager = websocket_setup
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws", subprotocols=["quantum-trader", f"bearer.{token}"]
        ):
            pass
    assert manager.called is False


def test_websocket_rejects_expired_token(websocket_setup):
    client, settings, manager = websocket_setup
    token = make_token(settings, expires_in=-60)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws", subprotocols=["quantum-trader", f"bearer.{token}"]
        ):
            pass
    assert manager.called is False


def test_websocket_rejects_wrong_identity_and_signature(websocket_setup):
    client, settings, manager = websocket_setup
    wrong_identity = make_token(settings, username="another-admin")
    wrong_signature = jwt.encode(
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
    for token in (wrong_identity, wrong_signature):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/ws", subprotocols=["quantum-trader", f"bearer.{token}"]
            ):
                pass
    assert manager.called is False


def test_valid_websocket_token_is_accepted_with_fixed_subprotocol(websocket_setup):
    client, settings, manager = websocket_setup
    token = make_token(settings)
    with client.websocket_connect(
        "/ws", subprotocols=["quantum-trader", f"bearer.{token}"]
    ) as websocket:
        assert websocket.accepted_subprotocol == "quantum-trader"
        message = websocket.receive_json()
        assert message["type"] == "welcome"
    assert manager.called is True


def test_websocket_rejects_duplicate_bearer_protocols(websocket_setup):
    client, settings, manager = websocket_setup
    token = make_token(settings)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws",
            subprotocols=["quantum-trader", f"bearer.{token}", f"bearer.{token}"],
        ):
            pass
    assert manager.called is False



@pytest.mark.asyncio
async def test_connection_manager_negotiates_only_the_fixed_protocol():
    class FakeWebSocket:
        scope = {"subprotocols": ["quantum-trader", "bearer.not-a-real-token"]}
        client = None

        async def accept(self, subprotocol=None):
            self.accepted_subprotocol = subprotocol

        async def send_text(self, message):
            self.last_message = message

    websocket = FakeWebSocket()
    manager = ConnectionManager(SimpleNamespace())
    await manager.connect(websocket)

    assert websocket.accepted_subprotocol == "quantum-trader"
    assert '"type": "welcome"' in websocket.last_message
