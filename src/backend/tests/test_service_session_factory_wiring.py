"""Service-container database dependency wiring tests."""

import pytest

import src.backend.services as service_module


class _AsyncService:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def initialize(self):
        return None

    async def shutdown(self):
        return None

    async def start(self):
        return None

    async def stop(self):
        return None


@pytest.mark.asyncio
async def test_session_factory_is_injected_into_execution_tp_sl_and_pnl_services(
    config, monkeypatch
):
    session_factory = object()

    class _MarketData(_AsyncService):
        pass

    class _HistoricalData(_AsyncService):
        pass

    class _MarketRegime(_AsyncService):
        pass

    class _MarketScanner(_AsyncService):
        pass

    class _Strategy(_AsyncService):
        pass

    class _Risk(_AsyncService):
        pass

    class _Execution(_AsyncService):
        pass

    class _TPSL(_AsyncService):
        pass

    class _PnL(_AsyncService):
        pass

    class _Signal(_AsyncService):
        pass

    class _WebSocket(_AsyncService):
        pass

    replacements = {
        "MarketDataService": _MarketData,
        "HistoricalDataService": _HistoricalData,
        "MarketRegimeService": _MarketRegime,
        "MarketScanner": _MarketScanner,
        "StrategyService": _Strategy,
        "RiskService": _Risk,
        "ExecutionService": _Execution,
        "TPSLService": _TPSL,
        "PnLService": _PnL,
        "SignalService": _Signal,
        "WebSocketManager": _WebSocket,
    }
    for name, replacement in replacements.items():
        monkeypatch.setattr(service_module, name, replacement)

    container = service_module.ServiceContainer(config, session_factory)
    await container.initialize_all()

    assert container.execution_service.kwargs["session_factory"] is session_factory
    assert container.tp_sl_service.kwargs["session_factory"] is session_factory
    assert container.pnl_service.kwargs["session_factory"] is session_factory

    await container.shutdown_all()
