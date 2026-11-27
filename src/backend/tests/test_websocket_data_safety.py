"""WebSocket handlers must not emit fabricated market or trading state."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.services.websocket_manager import WebSocketManager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_name", "message", "expected_resource"),
    [
        ("_handle_get_ticker", {"symbol": "BTCUSDT", "request_id": "r1"}, "Ticker data"),
        ("_handle_get_orderbook", {"symbol": "BTCUSDT", "request_id": "r2"}, "Order book data"),
        ("_handle_get_position", {"position_id": 7, "request_id": "r3"}, "Position data"),
        ("_handle_get_signal", {"signal_id": 8, "request_id": "r4"}, "Signal data"),
        ("_handle_get_pnl", {"period": "30d", "request_id": "r5"}, "PnL data"),
    ],
)
async def test_request_handlers_return_unavailable_instead_of_fabricated_data(
    handler_name, message, expected_resource
):
    manager = WebSocketManager(config=SimpleNamespace())
    manager.connection_manager.send_personal = AsyncMock()

    await getattr(manager, handler_name)("client-1", message)

    manager.connection_manager.send_personal.assert_awaited_once()
    client_id, response = manager.connection_manager.send_personal.await_args.args
    assert client_id == "client-1"
    assert response.type == "error"
    assert response.data["error"] == "data_unavailable"
    assert response.data["resource"] == expected_resource
    assert "authoritative data source" in response.data["message"]
    assert response.request_id == message["request_id"]
    assert "price" not in response.data
    assert "net_pnl" not in response.data
    assert "entry_price" not in response.data


@pytest.mark.asyncio
async def test_initialize_does_not_start_placeholder_periodic_status_broadcast():
    manager = WebSocketManager(config=SimpleNamespace())

    await manager.initialize()

    assert manager._update_task is None
    assert manager._running is True

    await manager.shutdown()
