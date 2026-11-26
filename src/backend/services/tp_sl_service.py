"""
TP/SL Service for QUANTUM TRADER V1
Implements advanced Take Profit / Stop Loss management with profit protection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session

from src.backend.models.database import (
    Position, Order, OrderStatus, OrderType, OrderSide, TPStage
)
from src.backend.services.execution_service import ExecutionService, OrderParams, OrderSide, OrderType
from src.backend.services.risk_service import RiskService
from src.backend.services.market_data_service import MarketDataService
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


class TPStage(Enum):
    """Take profit stages"""
    INITIAL_SL = 0      # Initial stop loss
    TP1 = 1             # First take profit (40%)
    TP2 = 2             # Second take profit (30%)
    TP3 = 3             # Third take profit (20%)
    RUNNER = 4          # Runner (10%)


class TPStatus(Enum):
    """TP/SL order status"""
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TPOrder:
    """TP/SL order specification"""
    stage: int
    target_price: Decimal
    quantity: Decimal
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    status: TPStatus = TPStatus.PENDING
    triggered_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class PositionTPState:
    """Complete TP/SL state for a position"""
    position_id: int
    symbol: str
    exchange: str
    direction: str  # LONG/SHORT
    entry_price: Decimal
    quantity: Decimal
    current_stage: int  # 0=initial, 1=TP1 hit, 2=TP2 hit, 3=TP3 hit, 4=runner
    stop_loss: Decimal
    tp_orders: Dict[int, TPOrder]  # stage -> TPOrder
    runner_trailing_price: Optional[Decimal] = None
    runner_high: Optional[Decimal] = None
    runner_low: Optional[Decimal] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


class TPSLManager:
    """Manages TP/SL orders for a single position"""

    def __init__(
        self,
        position: Any,
        config: Config,
        execution_service: "ExecutionService",
        market_data_service: "MarketDataService"
    ):
        self.position = position
        self.config = config
        self.execution_service = execution_service
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(f"tp_sl.{position.symbol}")
        self.state = self._initialize_state()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def _initialize_state(self) -> Dict:
        """Initialize TP/SL state from position"""
        return {
            'position_id': self.position.id,
            'symbol': self.position.symbol,
            'exchange': self.position.exchange,
            'direction': self.position.direction,
            'entry_price': self.position.entry_price,
            'quantity': self.position.quantity,
            'current_stage': 0,  # 0 = initial SL
            'stop_loss': self.position.stop_loss,
            'tp1': self.position.tp1,
            'tp2': self.position.tp2,
            'tp3': self.position.tp3,
            'tp_orders': {
                1: TPOrder(stage=1, target_price=self.position.tp1, quantity=self.position.quantity * Decimal('0.4')),
                2: TPOrder(stage=2, target_price=self.position.tp2, quantity=self.position.quantity * Decimal('0.3')),
                3: TPOrder(stage=3, target_price=self.position.tp3, quantity=self.position.quantity * Decimal('0.2')),
                4: TPOrder(stage=4, target_price=Decimal('0'), quantity=self.position.quantity * Decimal('0.1')),  # Runner
            },
            'runner_trailing_price': None,
            'runner_high': None,
            'runner_low': None,
            'updated_at': datetime.utcnow()
        }

    async def start(self, mode: str = "paper"):
        """Start TP/SL monitoring"""
        self._running = True
        # Place initial orders
        await self._place_initial_orders(mode)
        # Start monitoring
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info(f"Started TP/SL monitoring for {self.position.symbol}")

    async def stop(self):
        """Stop TP/SL monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _place_initial_orders(self, mode: str):
        """Place initial TP and SL orders"""
        # This would call execution service to place orders
        # Placeholder - actual implementation would use execution service
        pass

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                if not self._running:
                    break
                await self._check_and_update()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in TP/SL monitor: {e}")
                await asyncio.sleep(10)

    async def _check_and_update(self):
        """Check TP/SL status and update if needed"""
        # Get current market price
        ticker = await self.market_data_service.get_ticker(self.position.symbol)
        if not ticker:
            return

        current_price = ticker.price

        # Check each TP level
        for stage in [1, 2, 3]:
            tp_order = self.state['tp_orders'][stage]
            if tp_order.status == TPStatus.PENDING or tp_order.status == TPStatus.ACTIVE:
                if self._is_tp_triggered(stage, tp_order.target_price):
                    await self._handle_tp_trigger(stage)

        # Check runner trailing stop
        if self.state['current_stage'] >= 3:
            await self._update_runner_trailing()

        # Check stop loss
        if self._is_sl_triggered():
            await self._handle_sl_trigger()

    def _is_tp_triggered(self, stage: int, target_price: Decimal) -> bool:
        """Check if TP is triggered"""
        ticker = self.market_data_service.get_ticker(self.position.symbol)
        if not ticker:
            return False

        current_price = ticker.price

        if self.position.direction == "LONG":
            return current_price >= target_price
        else:
            return current_price <= target_price

    def _is_sl_triggered(self) -> bool:
        """Check if stop loss is triggered"""
        ticker = self.market_data_service.get_ticker(self.position.symbol)
        if not ticker:
            return False

        current_price = ticker.price
        sl = self.state['stop_loss']

        if self.position.direction == "LONG":
            return ticker.price <= sl
        else:
            return ticker.price >= sl

    async def _handle_tp_trigger(self, stage: int):
        """Handle TP trigger"""
        self.logger.info(f"TP{stage} triggered for {self.position.symbol}")

        # Update state
        self.state['current_stage'] = stage
        self.state['tp_orders'][stage].status = TPStatus.TRIGGERED
        self.state['tp_orders'][stage].triggered_at = datetime.utcnow()

        # Move stop loss to next level
        if stage == 1:
            # Move SL to break-even (entry price + fees)
            new_sl = self._calculate_breakeven()
            await self._update_stop_loss(new_sl)
            self.state['stop_loss'] = new_sl

        elif stage == 2:
            # Move SL to TP1
            new_sl = self.state['tp1']
            await self._update_stop_loss(new_sl)
            self.state['stop_loss'] = new_sl

        elif stage == 3:
            # Move SL to TP2, activate runner
            new_sl = self.state['tp2']
            await self._update_stop_loss(new_sl)
            self.state['stop_loss'] = new_sl
            self.state['current_stage'] = 4
            self.state['runner_trailing_price'] = self.state['tp2']

        self.state['updated_at'] = datetime.utcnow()

    def _calculate_breakeven(self) -> Decimal:
        """Calculate break-even price including fees"""
        entry = self.position.entry_price
        fees = self.position.entry_price * self.position.quantity * Decimal('0.0004')  # 0.04% entry fee
        funding = self.position.entry_price * self.position.quantity * Decimal('0.0001') * 3  # 3 funding periods

        total_cost = fees + funding
        breakeven_per_qty = total_cost / self.position.quantity

        if self.position.direction == "LONG":
            return self.position.entry_price + breakeven_per_qty
        else:
            return self.position.entry_price - breakeven_per_qty

    async def _update_stop_loss(self, new_sl: Decimal):
        """Update stop loss order"""
        # Cancel old SL, place new one
        # Would call execution service
        self.logger.info(f"Updated stop loss to {new_sl}")

    async def _update_runner_trailing(self):
        """Update runner trailing stop"""
        ticker = self.market_data_service.get_ticker(self.position.symbol)
        if not ticker:
            return

        current_price = ticker.price

        if self.position.direction == "LONG":
            # Trail up
            if self.state['runner_high'] is None or current_price > self.state['runner_high']:
                self.state['runner_high'] = current_price

            # Calculate trailing stop using ATR
            atr = self._get_atr()
            trailing_distance = atr * Decimal(str(self.config.settings.tp_sl.trailing_atr_multiplier))
            new_sl = self.state['runner_high'] - trailing_distance

            # Only move SL up, never down
            if new_sl > self.state['stop_loss']:
                await self._update_stop_loss(new_sl)
                self.state['runner_trailing_price'] = new_sl

        else:
            # Trail down for SHORT
            if self.state['runner_low'] is None or current_price < self.state['runner_low']:
                self.state['runner_low'] = current_price

            atr = self._get_atr()
            trailing_distance = atr * Decimal(str(self.config.settings.tp_sl.trailing_atr_multiplier))
            new_sl = self.state['runner_low'] + trailing_distance

            if new_sl < self.state['stop_loss']:
                await self._update_stop_loss(new_sl)
                self.state['runner_trailing_price'] = new_sl

    def _get_atr(self) -> Decimal:
        """Get ATR value (placeholder)"""
        return Decimal('100')  # Placeholder

    async def _handle_sl_trigger(self):
        """Handle stop loss trigger"""
        self.logger.info(f"Stop loss triggered for {self.position.symbol}")
        # Would trigger position close
        pass


class TPSLService:
    """Main TP/SL service managing all positions"""

    def __init__(
        self,
        config: Config,
        execution_service: "ExecutionService",
        market_data_service: "MarketDataService",
        risk_service: "RiskService"
    ):
        self.config = config
        self.execution_service = execution_service
        self.market_data_service = market_data_service
        self.risk_service = risk_service
        self.logger = logging.getLogger(__name__)

        self.managers: Dict[int, TPSLManager] = {}
        self._running = False

    async def initialize(self):
        """Initialize TP/SL service"""
        self.logger.info("Initializing TP/SL Service...")
        self._running = True
        self.logger.info("TP/SL Service initialized")

    async def shutdown(self):
        """Shutdown TP/SL service"""
        self._running = False
        for manager in self.managers.values():
            await manager.stop()
        self.logger.info("TP/SL Service shut down")

    async def add_position(self, position: Any, mode: str = "paper"):
        """Add a new position to TP/SL management"""
        manager = TPSLManager(position, self.config, self.execution_service, self.market_data_service)
        self.managers[position.id] = manager
        await manager.start(mode)
        self.logger.info(f"Added position {position.id} to TP/SL management")

    async def remove_position(self, position_id: int):
        """Remove position from TP/SL management"""
        if position_id in self.managers:
            await self.managers[position_id].stop()
            del self.managers[position_id]
            self.logger.info(f"Removed position {position_id} from TP/SL management")

    async def update_position_stage(self, position_id: int, new_stage: int):
        """Manually update position TP stage"""
        if position_id in self.managers:
            manager = self.managers[position_id]
            manager.state['current_stage'] = new_stage
            manager.state['updated_at'] = datetime.utcnow()
            self.logger.info(f"Updated position {position_id} to stage {new_stage}")

    async def update_stop_loss(self, position_id: int, new_sl: Decimal):
        """Manually update stop loss"""
        if position_id in self.managers:
            manager = self.managers[position_id]
            await manager._update_stop_loss(new_sl)
            manager.state['stop_loss'] = new_sl
            manager.state['updated_at'] = datetime.utcnow()
            self.logger.info(f"Updated stop loss for position {position_id} to {new_sl}")

    async def get_position_state(self, position_id: int) -> Optional[Dict]:
        """Get current TP/SL state for a position"""
        if position_id in self.managers:
            return self.managers[position_id].state
        return None

    async def get_all_states(self) -> Dict[int, Dict]:
        """Get all TP/SL states"""
        return {pid: mgr.state for pid, mgr in self.managers.items()}

    async def shutdown(self):
        """Shutdown TP/SL service"""
        for manager in self.managers.values():
            await manager.stop()
        self._running = False
        self.logger.info("TP/SL Service shut down")