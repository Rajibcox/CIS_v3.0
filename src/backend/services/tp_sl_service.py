"""
Paper-first TP/SL management for QUANTUM TRADER.
TP/SL triggers are evaluated from market data and closed through the paper
ExecutionService. No exchange-native conditional orders are submitted.
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session, object_session

from src.backend.models.database import (
    OrderStatus, OrderType as DBOrderType, PositionStatus, TP_SL_Stage,
    TPStageStatus, TPStageType,
)
from src.backend.services.execution_service import (
    ExecutionService, OrderParams, OrderSide, OrderType,
)
from src.backend.services.risk_service import RiskService
from src.backend.services.market_data_service import MarketDataService
from src.backend.utils.config import Config


logger = logging.getLogger(__name__)


class TPStage:
    INITIAL_SL = 0
    TP1 = 1
    TP2 = 2
    TP3 = 3
    RUNNER = 4


class TPStatus:
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TPOrder:
    def __init__(self, stage: int, target_price: Decimal, quantity: Decimal):
        self.stage = stage
        self.target_price = target_price
        self.quantity = quantity
        self.order_id = None
        self.exchange_order_id = None
        self.status = TPStatus.PENDING
        self.triggered_at = None
        self.filled_at = None
        self.db_stage_id = None


class TPSLManager:
    """Manages one open position using paper-market close orders."""

    def __init__(self, position: Any, config: Config,
                 execution_service: ExecutionService,
                 market_data_service: MarketDataService):
        self.position = position
        self.config = config
        self.execution_service = execution_service
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(f"tp_sl.{position.symbol.symbol if getattr(position, 'symbol', None) else position.id}")
        self.db: Optional[Session] = object_session(position)
        self.mode = "paper"
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._sl_closing = False
        self.state = self._initialize_state()

    @staticmethod
    def _decimal(value: Any, label: str) -> Decimal:
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"{label} must be a valid decimal number")
        if not result.is_finite():
            raise ValueError(f"{label} must be finite")
        return result

    def _initialize_state(self) -> Dict[str, Any]:
        signal = getattr(self.position, "signal", None)
        if signal is None:
            raise ValueError("Position must reference a signal containing TP/SL targets")

        direction = getattr(self.position.direction, "value", self.position.direction)
        direction = str(direction).upper()
        if direction not in ("LONG", "SHORT"):
            raise ValueError("Position direction must be LONG or SHORT")

        entry = self._decimal(self.position.entry_price, "entry_price")
        quantity = self._decimal(self.position.quantity, "position quantity")
        stop = self._decimal(signal.stop_loss, "stop_loss")
        targets = [
            self._decimal(signal.tp1, "tp1"),
            self._decimal(signal.tp2, "tp2"),
            self._decimal(signal.tp3, "tp3"),
        ]
        if entry <= 0 or quantity <= 0 or stop <= 0 or any(x <= 0 for x in targets):
            raise ValueError("Entry, quantity, stop-loss and take-profit prices must be positive")
        if direction == "LONG":
            valid = stop < entry and targets[0] > entry and targets[0] < targets[1] < targets[2]
        else:
            valid = stop > entry and targets[0] < entry and targets[0] > targets[1] > targets[2]
        if not valid:
            raise ValueError(f"Invalid {direction} TP/SL price ordering")

        allocation = self.config.settings.tp_allocation
        keys = ("tp1", "tp2", "tp3", "runner")
        try:
            fractions = {key: self._decimal(allocation[key], f"tp_allocation.{key}") for key in keys}
        except (KeyError, TypeError):
            raise ValueError("TP allocation must define tp1, tp2, tp3 and runner")
        if any(value <= 0 or value >= 1 for value in fractions.values()):
            raise ValueError("Each TP allocation must be greater than 0 and less than 1")
        if sum(fractions.values(), Decimal("0")) != Decimal("1"):
            raise ValueError("TP allocations must sum exactly to 1")

        exchange = getattr(self.position, "exchange", None)
        exchange_name = getattr(exchange, "name", None)
        if not exchange_name:
            raise ValueError("Position must have a valid exchange relationship")
        symbol_obj = getattr(self.position, "symbol", None)
        symbol = getattr(symbol_obj, "symbol", None)
        if not symbol:
            raise ValueError("Position must have a valid symbol relationship")

        tp_orders = {
            stage: TPOrder(stage, targets[stage - 1], quantity * fractions[f"tp{stage}"])
            for stage in (1, 2, 3)
        }
        tp_orders[4] = TPOrder(4, Decimal("0"), quantity * fractions["runner"])
        return {
            "position_id": self.position.id,
            "symbol": symbol,
            "exchange": exchange_name,
            "direction": direction,
            "entry_price": entry,
            "quantity": quantity,
            "original_quantity": quantity,
            "current_stage": 0,
            "stop_loss": stop,
            "tp1": targets[0],
            "tp2": targets[1],
            "tp3": targets[2],
            "tp_orders": tp_orders,
            "runner_trailing_price": None,
            "runner_high": None,
            "runner_low": None,
            "updated_at": datetime.utcnow(),
            "db_stages": {},
        }

    async def start(self, mode: str = "paper"):
        if mode != "paper" or not self.config.settings.mock_exchange or not self.config.settings.paper_trading:
            raise RuntimeError("TP/SL service requires mock_exchange=True and paper_trading=True")
        if self._running:
            return
        await self._place_initial_orders(mode)
        self.mode = "paper"
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Started paper TP/SL monitoring for %s", self.state["symbol"])

    async def stop(self):
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._monitor_task = None

    def _persist_stage(self, stage_number: int, target: Optional[Decimal],
                       quantity: Decimal, status: str = TPStatus.PENDING,
                       triggered_at=None, filled_at=None, exchange_order_id=None):
        if self.db is None:
            return
        row = self.state["db_stages"].get(stage_number)
        db_status = TPStageStatus(status) if status in TPStageStatus._value2member_map_ else TPStageStatus.PENDING
        if row is None:
            row = TP_SL_Stage(
                position_id=self.position.id,
                stage_type=TPStageType.SL if stage_number == 0 else TPStageType.TP,
                stage_number=stage_number,
                target_price=float(target) if target is not None else None,
                quantity=float(quantity),
                status=db_status,
            )
            self.db.add(row)
            self.state["db_stages"][stage_number] = row
        else:
            row.stage_type = TPStageType.SL if stage_number == 0 else TPStageType.TP
            row.status = db_status
            row.target_price = float(target) if target is not None else None
            row.quantity = float(quantity)
        row.triggered_at = triggered_at
        row.filled_at = filled_at
        row.exchange_order_id = exchange_order_id
        self.db.flush()

    async def _place_initial_orders(self, mode: str):
        # Paper mode uses the ticker monitor as the trigger source. Persist the
        # initial SL (stage 0), TP1-TP3 and runner (stage 4); do not submit
        # exchange-native conditional orders.
        self._persist_stage(0, self.state["stop_loss"], self.state["original_quantity"])
        for stage, order in self.state["tp_orders"].items():
            self._persist_stage(stage, order.target_price if stage != 4 else None, order.quantity)

    async def _monitor_loop(self):
        while self._running:
            try:
                await asyncio.sleep(5)
                if self._running:
                    await self._check_and_update()
            except asyncio.CancelledError:
                break
            except Exception:
                self.logger.exception("TP/SL monitoring error for %s", self.state["symbol"])
                await asyncio.sleep(5)

    async def _check_and_update(self):
        ticker = await self.market_data_service.get_ticker(
            self.state["symbol"], self.state["exchange"]
        )
        raw_price = ticker.get("price") if isinstance(ticker, dict) else getattr(ticker, "price", None)
        if raw_price is None:
            return
        current_price = self._decimal(raw_price, "market price")
        if current_price <= 0:
            return

        for stage in (1, 2, 3):
            order = self.state["tp_orders"][stage]
            if order.status == TPStatus.PENDING and self._is_tp_triggered(stage, order.target_price, current_price):
                await self._handle_tp_trigger(stage)
        if self.state["current_stage"] >= 4:
            await self._update_runner_trailing(current_price)
        if self._is_sl_triggered(current_price):
            await self._handle_sl_trigger()

    def _is_tp_triggered(self, stage: int, target_price: Decimal, current_price: Decimal) -> bool:
        return current_price >= target_price if self.state["direction"] == "LONG" else current_price <= target_price

    def _is_sl_triggered(self, current_price: Decimal) -> bool:
        stop = self.state["stop_loss"]
        return current_price <= stop if self.state["direction"] == "LONG" else current_price >= stop

    def _close_side(self):
        return OrderSide.SELL if self.state["direction"] == "LONG" else OrderSide.BUY

    async def _submit_close(self, quantity: Decimal):
        return await self.execution_service.place_order(
            OrderParams(
                symbol=self.state["symbol"],
                exchange=self.state["exchange"],
                side=self._close_side(),
                order_type=OrderType.MARKET,
                quantity=quantity,
                reduce_only=True,
                position_side=self.state["direction"],
            ),
            mode="paper",
            db=self.db,
            position_id=self.position.id,
        )

    def _update_position_after_fill(
        self, quantity: Decimal, fill_price: Decimal, fees: Decimal = Decimal("0")
    ):
        """Book net realized PnL for a partial or full closing fill.

        Long: (exit - entry) * quantity.
        Short: (entry - exit) * quantity.
        Paper execution reports the closing fee separately, so deduct it once
        from the realized result.
        """
        remaining = max(Decimal("0"), self.state["quantity"] - quantity)
        entry = self.state["entry_price"]
        fees = self._decimal(fees, "closing fees")
        if fees < 0:
            raise ValueError("Closing fees cannot be negative")
        pnl = (fill_price - entry) * quantity
        if self.state["direction"] == "SHORT":
            pnl = -pnl
        net_pnl = pnl - fees
        self.position.realized_pnl = float(
            Decimal(str(self.position.realized_pnl or 0)) + net_pnl
        )
        self.state["quantity"] = remaining
        self.position.quantity = float(remaining)
        if remaining == 0:
            self.position.status = PositionStatus.CLOSED
            self.position.close_time = datetime.utcnow()
        self.state["updated_at"] = datetime.utcnow()
        if self.db is not None:
            self.db.flush()

    async def _handle_tp_trigger(self, stage: int):
        order = self.state["tp_orders"][stage]
        if order.status == TPStatus.FILLED or order.quantity <= 0:
            return
        result = await self._submit_close(min(order.quantity, self.state["quantity"]))
        if result.status != OrderStatus.FILLED:
            self.logger.error("TP%s close rejected for %s: %s", stage, self.state["symbol"], result.error or result.status.value)
            return

        now = datetime.utcnow()
        filled_qty = min(order.quantity, self.state["quantity"])
        order.status = TPStatus.FILLED
        order.triggered_at = now
        order.filled_at = now
        order.order_id = result.order_id
        order.exchange_order_id = result.exchange_order_id
        self._update_position_after_fill(filled_qty, result.average_fill_price, result.fees)
        self.state["current_stage"] = stage
        self._persist_stage(stage, order.target_price, order.quantity, TPStatus.FILLED,
                            now, now, result.exchange_order_id)

        if stage == 1:
            new_sl = self._calculate_breakeven()
            await self._update_stop_loss(new_sl)
        elif stage == 2:
            await self._update_stop_loss(self.state["tp1"])
        elif stage == 3:
            await self._update_stop_loss(self.state["tp2"])
            self.state["current_stage"] = 4
            self.state["runner_trailing_price"] = self.state["tp2"]

    def _calculate_breakeven(self) -> Decimal:
        entry = self.state["entry_price"]
        fee_rate = Decimal(str(self.config.settings.paper_fees))
        funding_rate = Decimal(str(self.config.settings.paper_funding_rate))
        cost_per_unit = entry * (fee_rate + funding_rate * Decimal("3"))
        return entry + cost_per_unit if self.state["direction"] == "LONG" else entry - cost_per_unit

    async def _update_stop_loss(self, new_sl: Decimal):
        new_sl = self._decimal(new_sl, "new stop_loss")
        if new_sl <= 0:
            raise ValueError("Stop-loss price must be positive")
        old = self.state["stop_loss"]
        if self.state["direction"] == "LONG" and new_sl < old:
            return
        if self.state["direction"] == "SHORT" and new_sl > old:
            return
        self.state["stop_loss"] = new_sl
        self.state["updated_at"] = datetime.utcnow()
        self._persist_stage(0, new_sl, self.state["original_quantity"])

    async def _get_atr(self) -> Decimal:
        candles = await self.market_data_service.get_candles(
            self.state["symbol"], "15m", limit=15, exchange=self.state["exchange"]
        )
        if not candles or len(candles) < 2:
            return self.state["entry_price"] * Decimal(str(self.config.settings.min_trailing_distance))
        ranges = []
        previous_close = None
        for candle in candles[-14:]:
            high = Decimal(str(candle["high"]))
            low = Decimal(str(candle["low"]))
            close = Decimal(str(candle["close"]))
            true_range = high - low
            if previous_close is not None:
                true_range = max(true_range, abs(high - previous_close), abs(low - previous_close))
            ranges.append(true_range)
            previous_close = close
        return sum(ranges, Decimal("0")) / Decimal(len(ranges))

    async def _update_runner_trailing(self, current_price: Decimal):
        multiplier = Decimal(str(self.config.settings.trailing_atr_multiplier))
        distance = await self._get_atr() * multiplier
        if self.state["direction"] == "LONG":
            high = self.state["runner_high"]
            self.state["runner_high"] = current_price if high is None else max(high, current_price)
            candidate = self.state["runner_high"] - distance
            if candidate > self.state["stop_loss"]:
                await self._update_stop_loss(candidate)
                self.state["runner_trailing_price"] = candidate
        else:
            low = self.state["runner_low"]
            self.state["runner_low"] = current_price if low is None else min(low, current_price)
            candidate = self.state["runner_low"] + distance
            if candidate < self.state["stop_loss"]:
                await self._update_stop_loss(candidate)
                self.state["runner_trailing_price"] = candidate

    async def _handle_sl_trigger(self):
        if self._sl_closing or self.state["quantity"] <= 0:
            return
        self._sl_closing = True
        try:
            remaining = self.state["quantity"]
            result = await self._submit_close(remaining)
            if result.status != OrderStatus.FILLED:
                self.logger.error("Stop-loss close rejected for %s: %s", self.state["symbol"], result.error or result.status.value)
                return
            now = datetime.utcnow()
            self._persist_stage(0, self.state["stop_loss"], self.state["original_quantity"],
                                TPStatus.FILLED, now, now, result.exchange_order_id)
            self._update_position_after_fill(remaining, result.average_fill_price, result.fees)
            self._running = False
        finally:
            self._sl_closing = False


class TPSLService:
    """Coordinates TP/SL managers for open positions."""

    def __init__(self, config: Config, execution_service: ExecutionService,
                 market_data_service: MarketDataService, risk_service: RiskService):
        self.config = config
        self.execution_service = execution_service
        self.market_data_service = market_data_service
        self.risk_service = risk_service
        self.logger = logging.getLogger(__name__)
        self.managers: Dict[int, TPSLManager] = {}
        self._running = False

    async def initialize(self):
        if not self.config.settings.mock_exchange or not self.config.settings.paper_trading:
            raise RuntimeError("TP/SL service requires mock_exchange=True and paper_trading=True")
        self._running = True
        self.logger.info("TP/SL Service initialized in paper mode")

    async def shutdown(self):
        self._running = False
        for manager in list(self.managers.values()):
            await manager.stop()
        self.logger.info("TP/SL Service shut down")

    async def add_position(self, position: Any, mode: str = "paper"):
        if not self._running:
            raise RuntimeError("TP/SL service is not initialized")
        if mode != "paper":
            raise RuntimeError("Only paper TP/SL management is permitted")
        manager = TPSLManager(position, self.config, self.execution_service, self.market_data_service)
        await manager.start(mode)
        self.managers[position.id] = manager
        self.logger.info("Added position %s to TP/SL management", position.id)

    async def remove_position(self, position_id: int):
        manager = self.managers.pop(position_id, None)
        if manager:
            await manager.stop()

    async def update_position_stage(self, position_id: int, new_stage: int):
        if new_stage not in (0, 1, 2, 3, 4):
            raise ValueError("TP stage must be between 0 and 4")
        manager = self.managers.get(position_id)
        if manager:
            manager.state["current_stage"] = new_stage
            manager.state["updated_at"] = datetime.utcnow()

    async def update_stop_loss(self, position_id: int, new_sl: Decimal):
        manager = self.managers.get(position_id)
        if manager:
            await manager._update_stop_loss(new_sl)

    async def get_position_state(self, position_id: int) -> Optional[Dict]:
        manager = self.managers.get(position_id)
        return manager.state if manager else None

    async def get_all_states(self) -> Dict[int, Dict]:
        return {pid: manager.state for pid, manager in self.managers.items()}
