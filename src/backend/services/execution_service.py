"""
Execution Service for QUANTUM TRADER V1
Handles order execution, position management, and trade lifecycle
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
    Position, Order, OrderStatus, OrderType, Signal
)
from src.backend.services.risk_service import RiskService, LeverageDecision
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT_MARKET = "take_profit_market"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderParams:
    """Order parameters"""
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    reduce_only: bool = False
    position_side: Optional[str] = None  # LONG, SHORT
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None


@dataclass
class OrderResult:
    """Order execution result"""
    order_id: str
    exchange_order_id: str
    symbol: str
    exchange: str
    status: OrderStatus
    filled_quantity: Decimal
    average_fill_price: Decimal
    fees: Decimal
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class PositionState:
    """Current position state"""
    position_id: int
    symbol: str
    exchange: str
    direction: str  # LONG/SHORT
    entry_price: Decimal
    quantity: Decimal
    notional: Decimal
    margin_used: Decimal
    leverage: int
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    tp_stage: int  # 0=initial, 1=TP1 hit, 2=TP2 hit, 3=TP3 hit, 4=runner
    stop_loss: Decimal
    tp1: Decimal
    tp2: Decimal
    tp3: Decimal
    liquidation_price: Decimal
    updated_at: datetime


class ExchangeExecutor:
    """Executes orders on a specific exchange"""

    def __init__(self, exchange_name: str, config: Config):
        self.exchange_name = exchange_name
        self.config = config
        self.logger = logging.getLogger(f"executor.{exchange_name}")
        self.exchange = None
        self._symbol_map = {}

    async def initialize(self, credentials: Dict):
        """Initialize exchange connection"""
        import ccxt.async_support as ccxt
        exchange_class = getattr(ccxt, self.exchange_name)

        exchange_config = {
            'apiKey': credentials.get('api_key'),
            'secret': credentials.get('api_secret'),
            'password': credentials.get('passphrase'),  # For Bitget
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if self.exchange_name == 'binance' else 'swap',
                'adjustForTimeDifference': True,
            }
        }

        self.exchange = exchange_class(exchange_config)
        await self.exchange.load_markets()
        self._build_symbol_map()
        self.logger.info(f"Initialized {self.exchange_name} executor")

    def _build_symbol_map(self):
        """Build symbol mapping"""
        for market_id, market in self.exchange.markets.items():
            if market.get('quote') == 'USDT' and market.get('type') in ['future', 'swap']:
                internal = market['base'] + market['quote']
                self._symbol_map[internal] = market_id

    def get_exchange_symbol(self, internal_symbol: str) -> Optional[str]:
        return self._symbol_map.get(internal_symbol)

    async def place_order(self, params: OrderParams) -> OrderResult:
        """Place an order on the exchange"""
        exchange_symbol = self.get_exchange_symbol(params.symbol)
        if not exchange_symbol:
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange=self.exchange_name,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal('0'),
                average_fill_price=Decimal('0'),
                fees=Decimal('0'),
                timestamp=datetime.utcnow(),
                error=f"Symbol {params.symbol} not found on {self.exchange_name}"
            )

        try:
            ccxt_params = {
                'symbol': exchange_symbol,
                'type': params.order_type.value,
                'side': params.side.value,
                'amount': float(params.quantity),
            }

            if params.price:
                ccxt_params['price'] = float(params.price)
            if params.stop_price:
                ccxt_params['stopPrice'] = float(params.stop_price)
            if params.reduce_only:
                ccxt_params['reduceOnly'] = True
            if params.position_side:
                ccxt_params['positionSide'] = params.position_side
            if params.time_in_force:
                ccxt_params['timeInForce'] = params.time_in_force
            if params.client_order_id:
                ccxt_params['clientOrderId'] = params.client_order_id

            # Add exchange-specific params
            if self.exchange_name == 'binance':
                ccxt_params['workingType'] = 'MARK_PRICE'
            elif self.exchange_name == 'bitget':
                ccxt_params['triggerType'] = 'mark_price'

            order = await self.exchange.create_order(**ccxt_params)

            return OrderResult(
                order_id=f"{self.exchange_name}_{order['id']}",
                exchange_order_id=str(order['id']),
                symbol=params.symbol,
                exchange=self.exchange_name,
                status=OrderStatus.PENDING if order['status'] == 'open' else OrderStatus.FILLED,
                filled_quantity=Decimal(str(order.get('filled', 0))),
                average_fill_price=Decimal(str(order.get('average', 0))) if order.get('average') else Decimal('0'),
                fees=Decimal(str(order.get('fee', {}).get('cost', 0))) if order.get('fee') else Decimal('0'),
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error(f"Order failed: {e}")
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange=self.exchange_name,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal('0'),
                average_fill_price=Decimal('0'),
                fees=Decimal('0'),
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            exchange_symbol = self.get_exchange_symbol(symbol)
            await self.exchange.cancel_order(order_id, exchange_symbol)
            return True
        except Exception as e:
            self.logger.error(f"Cancel order failed: {e}")
            return False

    async def get_order(self, order_id: str, symbol: str) -> Dict:
        """Get order status"""
        exchange_symbol = self.get_exchange_symbol(symbol)
        return await self.exchange.fetch_order(order_id, exchange_symbol)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """Get all open orders"""
        if symbol:
            exchange_symbol = self.get_exchange_symbol(symbol)
            return await self.exchange.fetch_open_orders(exchange_symbol)
        return await self.exchange.fetch_open_orders()

    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()


class PaperExecutor:
    """Paper trading executor for simulation"""

    def __init__(self, config: Config, market_data_service: Any):
        self.config = config
        self.market_data = market_data_service
        self.logger = logging.getLogger("executor.paper")
        self.orders = {}
        self.positions = {}
        self.order_counter = 0

    async def place_order(self, params: OrderParams) -> OrderResult:
        """Simulate an order without sending anything to an exchange."""
        timestamp = datetime.utcnow()
        ticker = await self.market_data.get_ticker(params.symbol, params.exchange)
        if not ticker:
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange="paper",
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                average_fill_price=Decimal("0"),
                fees=Decimal("0"),
                timestamp=timestamp,
                error="No market data available",
            )

        raw_price = ticker.get("price") if isinstance(ticker, dict) else getattr(ticker, "price", None)
        if raw_price is None:
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange="paper",
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                average_fill_price=Decimal("0"),
                fees=Decimal("0"),
                timestamp=timestamp,
                error="Market data did not contain a price",
            )

        market_price = Decimal(str(raw_price))
        if market_price <= 0 or params.quantity <= 0:
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange="paper",
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                average_fill_price=Decimal("0"),
                fees=Decimal("0"),
                timestamp=timestamp,
                error="Order price and quantity must be positive",
            )

        should_fill = params.order_type == OrderType.MARKET
        if params.order_type == OrderType.LIMIT:
            if params.price is None or params.price <= 0:
                error = "A positive limit price is required"
                should_fill = False
            else:
                should_fill = (
                    market_price <= params.price
                    if params.side == OrderSide.BUY
                    else market_price >= params.price
                )
                error = None
        elif params.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT):
            if params.stop_price is None or params.stop_price <= 0:
                error = "A positive stop price is required"
                should_fill = False
            else:
                should_fill = (
                    market_price >= params.stop_price
                    if params.side == OrderSide.BUY
                    else market_price <= params.stop_price
                )
                error = None
        elif params.order_type in (
            OrderType.TAKE_PROFIT_MARKET,
            OrderType.TAKE_PROFIT_LIMIT,
        ):
            if params.stop_price is None or params.stop_price <= 0:
                error = "A positive take-profit trigger price is required"
                should_fill = False
            else:
                should_fill = (
                    market_price <= params.stop_price
                    if params.side == OrderSide.BUY
                    else market_price >= params.stop_price
                )
                error = None
        elif params.order_type != OrderType.MARKET:
            error = f"Unsupported paper order type: {params.order_type.value}"
            should_fill = False
        else:
            error = None

        self.order_counter += 1
        order_id = f"paper_{self.order_counter}"

        if not should_fill:
            # Keep untriggered limit/conditional orders pending; never report them
            # as filled merely because the paper executor received the request.
            self.orders[order_id] = {
                "id": order_id,
                "symbol": params.symbol,
                "exchange": params.exchange,
                "side": params.side.value,
                "type": params.order_type.value,
                "quantity": params.quantity,
                "filled_quantity": Decimal("0"),
                "price": params.price,
                "stop_price": params.stop_price,
                "status": OrderStatus.PENDING if error is None else OrderStatus.REJECTED,
                "fees": Decimal("0"),
                "timestamp": timestamp,
                "error": error,
            }
            return OrderResult(
                order_id=order_id,
                exchange_order_id=order_id,
                symbol=params.symbol,
                exchange="paper",
                status=OrderStatus.PENDING if error is None else OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                average_fill_price=Decimal("0"),
                fees=Decimal("0"),
                timestamp=timestamp,
                error=error,
            )

        slippage = Decimal(str(self.config.settings.paper_slippage))
        fill_price = market_price * (
            Decimal("1") + slippage
            if params.side == OrderSide.BUY
            else Decimal("1") - slippage
        )
        fees = (
            fill_price
            * params.quantity
            * Decimal(str(self.config.settings.paper_fees))
        )

        self.orders[order_id] = {
            "id": order_id,
            "symbol": params.symbol,
            "exchange": params.exchange,
            "side": params.side.value,
            "type": params.order_type.value,
            "quantity": params.quantity,
            "filled_quantity": params.quantity,
            "price": fill_price,
            "fees": fees,
            "status": OrderStatus.FILLED,
            "timestamp": timestamp,
            "error": None,
        }

        return OrderResult(
            order_id=order_id,
            exchange_order_id=order_id,
            symbol=params.symbol,
            exchange="paper",
            status=OrderStatus.FILLED,
            filled_quantity=params.quantity,
            average_fill_price=fill_price,
            fees=fees,
            timestamp=timestamp,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        if order_id in self.orders and self.orders[order_id]['status'] == OrderStatus.PENDING:
            self.orders[order_id]['status'] = OrderStatus.CANCELLED
            return True
        return False

    async def get_order(self, order_id: str, symbol: str) -> Dict:
        if order_id in self.orders:
            return self.orders[order_id]
        return {}


class ExecutionService:
    """Main execution service coordinating live and paper trading"""

    def __init__(
        self,
        config: Config,
        risk_service: "RiskService",
        market_data_service: Any
    ):
        self.config = config
        self.risk_service = risk_service
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(__name__)

        self.executors: Dict[str, ExchangeExecutor] = {}
        self.paper_executor = PaperExecutor(config, market_data_service)
        self._running = False

    async def initialize(self):
        """Initialize execution service"""
        self.logger.info("Initializing Execution Service...")

        # PaperExecutor is fully initialized by __init__; never await __init__.
        # Initialize live executors (when credentials available)
        self._running = True
        self.logger.info("Execution Service initialized")

    async def shutdown(self):
        """Shutdown execution service"""
        self._running = False
        for executor in self.executors.values():
            await executor.close()

    async def place_order(
        self,
        params: OrderParams,
        mode: str = "paper"
    ) -> OrderResult:
        """Place an order"""
        if mode == "paper":
            return await self.paper_executor.place_order(params)

        executor = self.executors.get(params.exchange)
        if not executor:
            return OrderResult(
                order_id="",
                exchange_order_id="",
                symbol=params.symbol,
                exchange=params.exchange,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal('0'),
                average_fill_price=Decimal('0'),
                fees=Decimal('0'),
                timestamp=datetime.utcnow(),
                error=f"Exchange {params.exchange} not connected"
            )

        return await executor.place_order(params)

    async def place_entry_order(
        self,
        signal: Any,
        leverage_decision: "LeverageDecision",
        mode: str = "paper"
    ) -> OrderResult:
        """Place entry order from signal"""
        # Determine side
        if signal.direction == "LONG":
            side = OrderSide.BUY
        else:
            side = OrderSide.SELL

        # Create order params
        params = OrderParams(
            symbol=signal.symbol,
            exchange=signal.exchange,
            side=side,
            order_type=OrderType.MARKET,
            quantity=leverage_decision.position_quantity,
            reduce_only=False,
            position_side=signal.direction
        )

        return await self.place_order(params, mode)

    async def place_tp_sl_orders(
        self,
        position: Any,
        tp1: Decimal,
        tp2: Decimal,
        tp3: Decimal,
        stop_loss: Decimal,
        mode: str = "paper"
    ) -> List[OrderResult]:
        """Place TP and SL orders for a position"""
        results = []

        # Determine side (opposite of position direction)
        close_side = OrderSide.SELL if position.direction == "LONG" else OrderSide.BUY

        # TP1 - 40%
        tp1_qty = position.quantity * Decimal('0.4')
        tp1_order = OrderParams(
            symbol=position.symbol,
            exchange=position.exchange,
            side=close_side,
            order_type=OrderType.TAKE_PROFIT_MARKET,
            quantity=tp1_qty,
            stop_price=tp1,
            reduce_only=True,
            position_side=position.direction
        )
        results.append(await self.place_order(tp1_order, mode))

        # TP2 - 30%
        tp2_qty = position.quantity * Decimal('0.3')
        tp2_order = OrderParams(
            symbol=position.symbol,
            exchange=position.exchange,
            side=close_side,
            order_type=OrderType.TAKE_PROFIT_MARKET,
            quantity=tp2_qty,
            stop_price=tp2,
            reduce_only=True,
            position_side=position.direction
        )
        results.append(await self.place_order(tp2_order, mode))

        # TP3 - 20%
        tp3_qty = position.quantity * Decimal('0.2')
        tp3_order = OrderParams(
            symbol=position.symbol,
            exchange=position.exchange,
            side=close_side,
            order_type=OrderType.TAKE_PROFIT_MARKET,
            quantity=tp3_qty,
            stop_price=tp3,
            reduce_only=True,
            position_side=position.direction
        )
        results.append(await self.place_order(tp3_order, mode))

        # SL - remaining 10% (runner) + initial
        sl_order = OrderParams(
            symbol=position.symbol,
            exchange=position.exchange,
            side=close_side,
            order_type=OrderType.STOP_MARKET,
            quantity=position.quantity,
            stop_price=stop_loss,
            reduce_only=True,
            position_side=position.direction
        )
        results.append(await self.place_order(sl_order, mode))

        return results

    async def cancel_order(self, order_id: str, symbol: str, exchange: str, mode: str = "paper") -> bool:
        if mode == "paper":
            return await self.paper_executor.cancel_order(order_id, symbol)

        executor = self.executors.get(exchange)
        if executor:
            return await executor.cancel_order(order_id, symbol)
        return False

    async def get_position(self, symbol: str, exchange: str, mode: str = "paper") -> Optional[Dict]:
        """Get current position"""
        if mode == "paper":
            # Would return from paper positions
            return None

        executor = self.executors.get(exchange)
        if executor:
            # Would fetch from exchange
            pass
        return None

    async def get_open_orders(self, symbol: Optional[str] = None, exchange: Optional[str] = None, mode: str = "paper") -> List:
        if mode == "paper":
            return []  # Would return from paper orders

        if exchange:
            executor = self.executors.get(exchange)
            if executor:
                return await executor.get_open_orders(symbol)
        return []

    async def cancel_all_orders(self, symbol: str, exchange: str, mode: str = "paper") -> int:
        """Cancel all open orders for a symbol"""
        cancelled = 0
        orders = await self.get_open_orders(symbol, exchange, mode)
        for order in orders:
            if await self.cancel_order(order['id'], symbol, exchange, mode):
                cancelled += 1
        return cancelled

    async def emergency_close_all(self, mode: str = "paper") -> int:
        """Emergency close all positions"""
        closed = 0
        # Would close all positions
        self.logger.warning("EMERGENCY CLOSE ALL TRIGGERED")
        return closed

    async def initialize(self):
        """Initialize execution service"""
        self.logger.info("Execution Service initialized")

    async def shutdown(self):
        """Shutdown execution service"""
        for executor in self.executors.values():
            await executor.close()