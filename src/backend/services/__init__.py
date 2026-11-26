"""
Service Factory for QUANTUM TRADER V1
Centralized service creation and management
"""

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


class ServiceContainer:
    """Container for all services"""

    def __init__(self, config: Config):
        self.config = config
        self.market_data: Optional[MarketDataService] = None
        self.historical_data: Optional[Any] = None
        self.market_regime: Optional[Any] = None
        self.market_scanner: Optional[Any] = None
        self.signal_service: Optional[Any] = None
        self.strategy_service: Optional[StrategyService] = None
        self.risk_service: Optional[RiskService] = None
        self.execution_service: Optional[ExecutionService] = None
        self.tp_sl_service: Optional[TPSLService] = None
        self.pnl_service: Optional[PnLService] = None
        self.websocket_manager: Optional[WebSocketManager] = None

    async def initialize_all(self):
        """Initialize all services in dependency order"""
        # Core services
        self.market_data = MarketDataService(self.config)
        await self.market_data.initialize()

        from src.backend.services.historical_data_service import HistoricalDataService
        self.historical_data = HistoricalDataService(self.config, self.market_data)
        await self.historical_data.initialize()

        from src.backend.services.market_regime_service import MarketRegimeService
        self.market_regime = MarketRegimeService(self.config, self.market_data)
        await self.market_regime.initialize()

        from src.backend.services.market_scanner import MarketScanner
        self.market_scanner = MarketScanner(
            self.config, self.market_data, None  # historical_data
        )
        await self.market_scanner.start()

        from src.backend.services.strategy_service import StrategyService
        self.strategy_service = StrategyService(self.config, None)
        await self.strategy_service.initialize()

        from src.backend.services.risk_service import RiskService
        self.risk_service = RiskService(self.config)
        await self.risk_service.initialize()

        from src.backend.services.execution_service import ExecutionService
        self.execution_service = ExecutionService(
            self.config, None, None
        )
        await self.execution_service.initialize()

        from src.backend.services.tp_sl_service import TPSLService
        self.tp_sl_service = TPSLService(
            self.config, None, None, None
        )
        await self.tp_sl_service.initialize()

        from src.backend.services.pnl_service import PnLService
        self.pnl_service = PnLService(self.config)
        await self.pnl_service.initialize()

        # WebSocket manager
        from src.backend.services.websocket_manager import WebSocketManager
        self.websocket_manager = WebSocketManager(
            self.config,
            market_data_service=None,  # Will be set after initialization
            tp_sl_service=None,
            signal_service=None,
            execution_service=None,
            pnl_service=None
        )
        await self.websocket_manager.initialize()

        # Connect services after all are initialized
        self._connect_services()

    def _connect_services(self):
        """Connect services together after initialization"""
        # Connect market data to websocket manager
        if self.websocket_manager and self.market_data:
            self.websocket_manager.market_data_service = self.market_data

        # Connect TP/SL service to execution and market data
        if self.tp_sl_service:
            self.tp_sl_service.execution_service = self.execution_service
            self.tp_sl_service.market_data_service = self.market_data

        # Connect websocket manager to services
        if self.websocket_manager:
            self.websocket_manager.tp_sl_service = self.tp_sl_service
            self.websocket_manager.execution_service = self.execution_service
            self.websocket_manager.pnl_service = self.pnl_service

    async def shutdown_all(self):
        """Shutdown all services in reverse order"""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.shutdown()
        if hasattr(self, 'pnl_service') and self.pnl_service:
            await self.pnl_service.shutdown()
        if hasattr(self, 'tp_sl_service') and self.tp_sl_service:
            await self.tp_sl_service.shutdown()
        if hasattr(self, 'execution_service') and self.execution_service:
            await self.execution_service.shutdown()
        if hasattr(self, 'risk_service') and self.risk_service:
            await self.risk_service.shutdown()
        if hasattr(self, 'strategy_service') and self.strategy_service:
            await self.strategy_service.shutdown()
        if hasattr(self, 'market_scanner') and self.market_scanner:
            await self.market_scanner.stop()
        if hasattr(self, 'market_regime') and self.market_regime:
            await self.market_regime.shutdown()
        if hasattr(self, 'historical_data') and self.historical_data:
            await self.historical_data.shutdown()
        if hasattr(self, 'market_data') and self.market_data:
            await self.market_data.shutdown()


# Global service container instance
_service_container = None


def get_service_container(config: Config = None):
    """Get or create global service container"""
    global _service_container
    if _service_container is None:
        if config is None:
            from src.backend.utils.config import Config
            config = Config()
        _service_container = ServiceContainer(config)
    return _service_container


async def initialize_services(config: Config = None):
    """Initialize all services"""
    container = get_service_container(config)
    await container.initialize_all()
    return container


async def shutdown_services():
    """Shutdown all services"""
    global _service_container
    if _service_container:
        await _service_container.shutdown_all()
        _service_container = None