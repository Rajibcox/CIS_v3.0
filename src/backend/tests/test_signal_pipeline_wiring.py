"""Tests for scanner snapshot exposure and signal-service dependency wiring."""

import asyncio

from src.backend import services
from src.backend.services.market_scanner import MarketScanner
from src.backend.utils.config import Config


def test_scanner_exposes_unfiltered_snapshots_from_last_successful_scan():
    scanner = MarketScanner(Config(), None, None)
    snapshot = object()
    snapshots = {"binance:BTC/USDT": snapshot}

    async def get_symbols():
        return ["BTC/USDT"]

    async def build_snapshots():
        return snapshots

    scanner._get_eligible_symbols = get_symbols
    scanner._build_market_snapshots = build_snapshots
    scanner._run_filters = lambda received: []

    results = asyncio.run(scanner.run_scan())

    assert results == []
    assert scanner.latest_snapshots == snapshots
    assert scanner.latest_snapshots["binance:BTC/USDT"] is snapshot

    # Consumers cannot mutate the scanner's stored mapping.
    exposed = scanner.latest_snapshots
    exposed.clear()
    assert scanner.latest_snapshots == snapshots


def test_service_container_passes_scanner_and_session_factory_to_signal_service(monkeypatch):
    class StubService:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def initialize(self):
            return None

        async def start(self):
            return None

        async def stop(self):
            return None

        async def shutdown(self):
            return None

    for name in (
        "MarketDataService",
        "HistoricalDataService",
        "MarketRegimeService",
        "MarketScanner",
        "StrategyService",
        "RiskService",
        "ExecutionService",
        "TPSLService",
        "PnLService",
        "SignalService",
        "WebSocketManager",
    ):
        monkeypatch.setattr(services, name, StubService)

    session_factory = object()
    container = services.ServiceContainer(Config(), session_factory=session_factory)
    asyncio.run(container.initialize_all())

    assert container.signal_service.kwargs["market_scanner"] is container.market_scanner
    assert container.signal_service.kwargs["session_factory"] is session_factory


def test_initialize_services_forwards_session_factory(monkeypatch):
    captured = {}

    class StubContainer:
        async def initialize_all(self):
            return None

    def get_container(config=None, session_factory=None):
        captured["config"] = config
        captured["session_factory"] = session_factory
        return StubContainer()

    monkeypatch.setattr(services, "get_service_container", get_container)
    config = Config()
    session_factory = object()

    asyncio.run(services.initialize_services(config, session_factory))

    assert captured["config"] is config
    assert captured["session_factory"] is session_factory
