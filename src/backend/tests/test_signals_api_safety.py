"""Regression tests preventing fabricated signal API responses."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.backend.api.routes import signals


def test_signal_routes_do_not_expose_generated_mock_data():
    assert not hasattr(signals, "MOCK_SIGNALS")
    assert not hasattr(signals, "generate_mock_signals")


@pytest.mark.parametrize(
    ("endpoint", "args"),
    [
        (signals.get_signals, ()),
        (signals.get_active_signals, ()),
        (signals.get_best_signals, ()),
        (signals.get_signal_stats, ()),
        (signals.get_signal_detail, (1,)),
    ],
)
def test_signal_read_endpoints_fail_closed_until_persisted_read_model_exists(endpoint, args):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(endpoint(*args))

    assert exc_info.value.status_code == 503
    assert "Persisted signal records" in exc_info.value.detail or (
        "performance statistics" in exc_info.value.detail
        or "ranked persisted signals" in exc_info.value.detail
        or "complete persisted trade-plan data" in exc_info.value.detail
    )


def test_paper_trade_endpoint_never_claims_fake_execution():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(signals.execute_paper_trade(123))

    assert exc_info.value.status_code == 409
    assert "disabled" in exc_info.value.detail.lower()


def test_scan_endpoint_reports_real_rule_matches_without_claiming_signals_or_trades():
    class FakeSignalService:
        latest_strategy_matches = [object(), object()]

        async def generate_signals_now(self):
            return []

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                services=SimpleNamespace(signal_service=FakeSignalService())
            )
        )
    )

    result = asyncio.run(signals.trigger_scan(request))

    assert result["status"] == "completed"
    assert result["strategy_matches"] == 2
    assert result["actionable_signals_created"] == 0
    assert "no paper trades were created" in result["message"]


def test_scan_endpoint_reports_unavailable_when_signal_service_is_not_initialized():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(services=None)))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(signals.trigger_scan(request))

    assert exc_info.value.status_code == 503
    assert "no scan was run" in exc_info.value.detail
