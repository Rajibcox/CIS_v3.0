"""
Service Factory for QUANTUM TRADER V1
Centralized service creation, dependency injection, and lifecycle management.
"""

import logging
from typing import Optional, Any

from src.backend.utils.config import Config
from src.backend.services.market_data_service import MarketDataService
from src.backend.services.historical_data_service import HistoricalDataService
from src.backend.services.market_regime_service import MarketRegimeService
from src.backend.services.market_scanner import MarketScanner
from src.backend.services.signal_service import SignalService
from src.backend.services.strategy_service import StrategyService
from src.backend.services.risk_service import RiskService
from src.backend.services.execution_service import ExecutionService
from src.backend.services.tp_sl_service import TPSLService
from src.backend.services.pnl_service import PnLService
from src.backend.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Owns application services and their dependency-aware lifecycle."""

    def __init__(self, config: Config, session_factory: Any = None):
        self.config = config
        self.session_factory = session_factory
        self.market_data: Optional[MarketDataService] = None
        self.historical_data: Optional[HistoricalDataService] = None
        self.market_regime: Optional[MarketRegimeService] = None
        self.market_scanner: Optional[MarketScanner] = None
        self.signal_service: Optional[SignalService] = None
        self.strategy_service: Optional[StrategyService] = None
        self.risk_service: Optional[RiskService] = None
        self.execution_service: Optional[ExecutionService] = None
        self.tp_sl_service: Optional[TPSLService] = None
        self.pnl_service: Optional[PnLService] = None
        self.websocket_manager: Optional[WebSocketManager] = None
        self._initialized = False

    async def initialize_all(self):
        """Initialize services in dependency order."""
        if self._initialized:
            logger.warning("Service container is already initialized; skipping.")
            return

        self.market_data = MarketDataService(self.config)
        await self.market_data.initialize()

        self.historical_data = HistoricalDataService(self.config, self.market_data)
        await self.historical_data.initialize()

        self.market_regime = MarketRegimeService(self.config, self.market_data)
        await self.market_regime.initialize()

        self.market_scanner = MarketScanner(
            self.config, self.market_data, self.historical_data
        )
        await self.market_scanner.start()

        self.strategy_service = StrategyService(
            self.config, self.market_data, session_factory=self.session_factory
        )
        await self.strategy_service.initialize()

        self.risk_service = RiskService(self.config)
        await self.risk_service.initialize()

        self.execution_service = ExecutionService(
            self.config,
            self.risk_service,
            self.market_data,
            session_factory=self.session_factory,
        )
        await self.execution_service.initialize()

        self.tp_sl_service = TPSLService(
            self.config,
            self.execution_service,
            self.market_data,
            self.risk_service,
            session_factory=self.session_factory,
        )
        await self.tp_sl_service.initialize()

        self.pnl_service = PnLService(
            self.config, session_factory=self.session_factory
        )
        await self.pnl_service.initialize()

        self.signal_service = SignalService(
            self.config,
            self.market_data,
            self.market_regime,
            self.strategy_service,
            market_scanner=self.market_scanner,
            session_factory=self.session_factory,
        )
        await self.signal_service.initialize()

        self.websocket_manager = WebSocketManager(
            self.config,
            market_data_service=self.market_data,
            tp_sl_service=self.tp_sl_service,
            signal_service=self.signal_service,
            execution_service=self.execution_service,
            pnl_service=self.pnl_service,
        )
        await self.websocket_manager.initialize()

        self._initialized = True
        logger.info("All services initialized successfully.")

    async def shutdown_all(self):
        """Shut down every initialized service, even if one cleanup fails."""
        shutdown_steps = (
            ("websocket_manager", "shutdown"),
            ("signal_service", "shutdown"),
            ("pnl_service", "shutdown"),
            ("tp_sl_service", "shutdown"),
            ("execution_service", "shutdown"),
            ("risk_service", "shutdown"),
            ("strategy_service", "shutdown"),
            ("market_scanner", "stop"),
            ("market_regime", "shutdown"),
            ("historical_data", "shutdown"),
            ("market_data", "shutdown"),
        )

        for attribute, method_name in shutdown_steps:
            service = getattr(self, attribute, None)
            if service is None:
                continue
            method = getattr(service, method_name, None)
            if method is None:
                continue
            try:
                await method()
            except Exception:
                logger.exception(
                    "Error shutting down service %s", attribute
                )

        self._initialized = False


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container(
    config: Optional[Config] = None,
    session_factory: Any = None,
) -> ServiceContainer:
    """Get or create the global service container."""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer(config or Config(), session_factory)
    elif config is not None and _service_container.config is not config:
        if _service_container._initialized:
            raise RuntimeError(
                "Cannot replace the service container while it is initialized."
            )
        _service_container = ServiceContainer(config, session_factory)
    elif session_factory is not None:
        if (
            _service_container._initialized
            and _service_container.session_factory is not session_factory
        ):
            raise RuntimeError(
                "Cannot replace the session factory while services are initialized."
            )
        _service_container.session_factory = session_factory
    return _service_container


async def initialize_services(
    config: Optional[Config] = None,
    session_factory: Any = None,
) -> ServiceContainer:
    """Create and initialize all application services."""
    container = get_service_container(config, session_factory)
    await container.initialize_all()
    return container


async def shutdown_services():
    """Shut down and release the global service container."""
    global _service_container
    container = _service_container
    if container is None:
        return

    try:
        await container.shutdown_all()
    finally:
        _service_container = None
