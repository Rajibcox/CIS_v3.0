"""Contract tests for the Stage 2A signal-generation entry point."""

import asyncio
from types import SimpleNamespace

from src.backend.services.signal_service import SignalService


def test_generate_signals_now_returns_empty_list_without_loaded_rules():
    strategy_service = SimpleNamespace(
        engine=SimpleNamespace(_rule_cache={})
    )
    service = SignalService(
        config=None,
        market_data_service=None,
        market_regime_service=None,
        strategy_service=strategy_service,
    )

    result = asyncio.run(service.generate_signals_now())

    assert result == []
    assert isinstance(result, list)
