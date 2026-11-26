"""
Trading API Routes for QUANTUM TRADER V1
Paper trading, positions, orders, trade history, TP/SL management
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


# Enums
class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"
    FORCE_CLOSED = "force_closed"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TPSLStageType(str, Enum):
    TP = "TP"
    SL = "SL"


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


# Models
class Position(BaseModel):
    id: int
    signal_id: Optional[int] = None
    exchange: str
    symbol: str
    direction: TradeDirection
    entry_price: float
    current_price: float
    quantity: float
    notional_value: float
    margin_used: float
    leverage: float
    unrealized_pnl: float
    realized_pnl: float
    status: PositionStatus
    tp_stage: int = 0  # 0=initial, 1=TP1 hit, 2=TP2 hit, 3=TP3 hit, 4=runner
    open_time: datetime
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    stop_loss: float
    liquidation_price: Optional[float] = None
    liquidation_buffer_pct: Optional[float] = None
    runner_trailing_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class Order(BaseModel):
    id: int
    position_id: Optional[int] = None
    exchange: str
    symbol: str
    exchange_order_id: Optional[str] = None
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    fees: float = 0.0
    reduce_only: bool = False
    created_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime] = None


class TPSLStage(BaseModel):
    id: int
    position_id: int
    stage_type: TPSLStageType
    stage_number: int  # 0=initial SL, 1=TP1, 2=TP2, 3=TP3, 4=runner
    target_price: float
    quantity: float
    status: str  # pending, triggered, filled, cancelled, failed
    exchange_order_id: Optional[str] = None
    triggered_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    created_at: datetime


class PaperTradeRequest(BaseModel):
    signal_id: Optional[int] = None
    symbol: str
    exchange: str
    direction: TradeDirection
    entry_price: Optional[float] = None  # None = market
    quantity: Optional[float] = None  # Auto-calculated if None
    leverage: Optional[float] = None  # Auto-calculated if None
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    runner_pct: float = 0.1
    execution_mode: ExecutionMode = ExecutionMode.PAPER


class PaperTradeResponse(BaseModel):
    success: bool
    message: str
    position_id: Optional[int] = None
    order_id: Optional[int] = None
    entry_price: Optional[float] = None
    quantity: Optional[float] = None
    leverage: Optional[float] = None
    required_margin: Optional[float] = None
    tp_sl_stages: List[TPSLStage] = []


class ClosePositionRequest(BaseModel):
    position_id: int
    quantity: Optional[float] = None  # None = full close
    order_type: OrderType = OrderType.MARKET


class TradeHistoryEntry(BaseModel):
    id: int
    position_id: int
    symbol: str
    exchange: str
    direction: TradeDirection
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    r_multiple: float
    hold_time_hours: float
    exit_reason: str  # TP1, TP2, TP3, RUNNER, SL, MANUAL
    tp_stage_reached: int
    opened_at: datetime
    closed_at: datetime


class PaperAccountStatus(BaseModel):
    mode: ExecutionMode
    equity: float
    available_balance: float
    allocated_margin: float
    unrealized_pnl: float
    realized_pnl_today: float
    open_positions: int
    max_positions: int
    daily_loss_limit: float
    daily_loss_used_pct: float
    is_paused: bool
    last_reset: datetime


# Mock data
MOCK_POSITIONS = []
MOCK_ORDERS = []
MOCK_TRADES = []
MOCK_TPSL_STAGES = []


def generate_mock_data():
    """Generate mock trading data"""
    global MOCK_POSITIONS, MOCK_ORDERS, MOCK_TRADES, MOCK_TPSL_STAGES

    # Mock position
    MOCK_POSITIONS = [
        Position(
            id=1,
            signal_id=1,
            exchange="binance",
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=45100.0,
            current_price=45800.0,
            quantity=0.01,
            notional_value=458.0,
            margin_used=152.7,
            leverage=3.0,
            unrealized_pnl=7.0,
            realized_pnl=0.0,
            status=PositionStatus.OPEN,
            tp_stage=1,  # TP1 hit
            open_time=datetime.utcnow() - timedelta(hours=2),
            tp1_price=46000.0,
            tp2_price=47000.0,
            tp3_price=48500.0,
            stop_loss=45100.0,  # Moved to break-even after TP1
            liquidation_price=43500.0,
            liquidation_buffer_pct=3.5,
            runner_trailing_price=None,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(minutes=30)
        )
    ]

    # Mock orders
    MOCK_ORDERS = [
        Order(
            id=1,
            position_id=1,
            exchange="binance",
            symbol="BTCUSDT",
            exchange_order_id="binance_12345",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.01,
            price=None,
            stop_price=None,
            status=OrderStatus.FILLED,
            filled_quantity=0.01,
            average_fill_price=45100.0,
            fees=0.45,
            reduce_only=False,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=2),
            filled_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Order(
            id=2,
            position_id=1,
            exchange="binance",
            symbol="BTCUSDT",
            exchange_order_id="binance_12346",
            order_type=OrderType.STOP_MARKET,
            side=OrderSide.SELL,
            quantity=0.006,  # TP1 - 40% of 0.015 (adjusted for precision)
            price=None,
            stop_price=46000.0,
            status=OrderStatus.FILLED,
            filled_quantity=0.006,
            average_fill_price=46000.0,
            fees=0.28,
            reduce_only=True,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(minutes=30),
            filled_at=datetime.utcnow() - timedelta(minutes=30)
        ),
        Order(
            id=3,
            position_id=1,
            exchange="binance",
            symbol="BTCUSDT",
            exchange_order_id="binance_12347",
            order_type=OrderType.STOP_MARKET,
            side=OrderSide.SELL,
            quantity=0.004,  # Remaining SL at break-even
            price=None,
            stop_price=45100.0,
            status=OrderStatus.PENDING,
            filled_quantity=0.0,
            average_fill_price=None,
            fees=0.0,
            reduce_only=True,
            created_at=datetime.utcnow() - timedelta(minutes=30),
            updated_at=datetime.utcnow() - timedelta(minutes=30),
            filled_at=None
        )
    ]

    # Mock TP/SL stages
    MOCK_TPSL_STAGES = [
        TPSLStage(
            id=1,
            position_id=1,
            stage_type=TPSLStageType.SL,
            stage_number=0,
            target_price=44200.0,  # Initial SL
            quantity=0.01,
            status="cancelled",
            exchange_order_id="binance_12345_sl",
            triggered_at=None,
            filled_at=None,
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        TPSLStage(
            id=2,
            position_id=1,
            stage_type=TPSLStageType.TP,
            stage_number=1,
            target_price=46000.0,
            quantity=0.004,
            status="filled",
            exchange_order_id="binance_12346",
            triggered_at=datetime.utcnow() - timedelta(minutes=30),
            filled_at=datetime.utcnow() - timedelta(minutes=30),
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        TPSLStage(
            id=3,
            position_id=1,
            stage_type=TPSLStageType.SL,
            stage_number=1,
            target_price=45100.0,  # Break-even after TP1
            quantity=0.006,
            status="pending",
            exchange_order_id="binance_12347",
            triggered_at=None,
            filled_at=None,
            created_at=datetime.utcnow() - timedelta(minutes=30)
        ),
        TPSLStage(
            id=4,
            position_id=1,
            stage_type=TPSLStageType.TP,
            stage_number=2,
            target_price=47000.0,
            quantity=0.003,
            status="pending",
            exchange_order_id=None,
            triggered_at=None,
            filled_at=None,
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        TPSLStage(
            id=5,
            position_id=1,
            stage_type=TPSLStageType.TP,
            stage_number=3,
            target_price=48500.0,
            quantity=0.002,
            status="pending",
            exchange_order_id=None,
            triggered_at=None,
            filled_at=None,
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        TPSLStage(
            id=6,
            position_id=1,
            stage_type=TPSLStageType.TP,
            stage_number=4,  # Runner
            target_price=0,  # Trailing
            quantity=0.001,
            status="pending",
            exchange_order_id=None,
            triggered_at=None,
            filled_at=None,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
    ]

    # Mock completed trades
    MOCK_TRADES = [
        TradeHistoryEntry(
            id=1,
            position_id=0,
            symbol="BTCUSDT",
            exchange="binance",
            direction=TradeDirection.LONG,
            entry_price=44000.0,
            exit_price=45500.0,
            quantity=0.01,
            gross_pnl=15.0,
            fees=0.90,
            funding=0.12,
            net_pnl=13.98,
            r_multiple=2.8,
            hold_time_hours=4.5,
            exit_reason="TP2",
            tp_stage_reached=2,
            opened_at=datetime.utcnow() - timedelta(days=1),
            closed_at=datetime.utcnow() - timedelta(days=1, hours=-4)
        ),
        TradeHistoryEntry(
            id=2,
            position_id=0,
            symbol="ETHUSDT",
            exchange="binance",
            direction=TradeDirection.SHORT,
            entry_price=3100.0,
            exit_price=3050.0,
            quantity=0.1,
            gross_pnl=5.0,
            fees=0.62,
            funding=0.05,
            net_pnl=4.33,
            r_multiple=1.5,
            hold_time_hours=2.0,
            exit_reason="TP1",
            tp_stage_reached=1,
            opened_at=datetime.utcnow() - timedelta(days=2),
            closed_at=datetime.utcnow() - timedelta(days=2, hours=-2)
        )
    ]


generate_mock_data()


# Routes
@router.get("/paper/status", response_model=PaperAccountStatus)
async def get_paper_status():
    """Get paper trading account status"""
    return PaperAccountStatus(
        mode=ExecutionMode.PAPER,
        equity=100.0 + sum(p.unrealized_pnl for p in MOCK_POSITIONS) + sum(t.net_pnl for t in MOCK_TRADES),
        available_balance=100.0 - sum(p.margin_used for p in MOCK_POSITIONS),
        allocated_margin=sum(p.margin_used for p in MOCK_POSITIONS),
        unrealized_pnl=sum(p.unrealized_pnl for p in MOCK_POSITIONS),
        realized_pnl_today=sum(t.net_pnl for t in MOCK_TRADES if t.closed_at.date() == datetime.utcnow().date()),
        open_positions=len(MOCK_POSITIONS),
        max_positions=2,
        daily_loss_limit=1.5,
        daily_loss_used_pct=0.0,
        is_paused=False,
        last_reset=datetime.utcnow() - timedelta(days=30)
    )


@router.get("/positions", response_model=List[Position])
async def get_positions(
    status: Optional[PositionStatus] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
):
    """Get all positions"""
    positions = MOCK_POSITIONS

    if status:
        positions = [p for p in positions if p.status == status]
    if exchange:
        positions = [p for p in positions if p.exchange == exchange.lower()]
    if symbol:
        positions = [p for p in positions if p.symbol == symbol.upper()]

    return positions


@router.get("/positions/{position_id}", response_model=Position)
async def get_position(position_id: int):
    """Get position by ID"""
    position = next((p for p in MOCK_POSITIONS if p.id == position_id), None)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


@router.get("/positions/{position_id}/tp-sl", response_model=List[TPSLStage])
async def get_position_tp_sl(position_id: int):
    """Get TP/SL stages for position"""
    position = next((p for p in MOCK_POSITIONS if p.id == position_id), None)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    stages = [s for s in MOCK_TPSL_STAGES if s.position_id == position_id]
    stages.sort(key=lambda x: (x.stage_type == TPSLStageType.SL, x.stage_number))
    return stages


@router.post("/paper-trade", response_model=PaperTradeResponse)
async def place_paper_trade(trade: PaperTradeRequest):
    """Place a paper trade"""
    # Validate
    if trade.direction == TradeDirection.LONG:
        if trade.stop_loss >= trade.entry_price if trade.entry_price else False:
            raise HTTPException(status_code=400, detail="Stop loss must be below entry for LONG")
        if trade.tp1 <= trade.entry_price if trade.entry_price else False:
            raise HTTPException(status_code=400, detail="TP1 must be above entry for LONG")
    else:
        if trade.stop_loss <= trade.entry_price if trade.entry_price else False:
            raise HTTPException(status_code=400, detail="Stop loss must be above entry for SHORT")
        if trade.tp1 >= trade.entry_price if trade.entry_price else False:
            raise HTTPException(status_code=400, detail="TP1 must be below entry for SHORT")

    # Mock execution - in reality calls execution service
    new_position_id = len(MOCK_POSITIONS) + 1
    new_order_id = len(MOCK_ORDERS) + 1

    # Calculate position size if not provided
    quantity = trade.quantity or 0.01
    leverage = trade.leverage or 3.0
    entry_price = trade.entry_price or 45000.0

    return PaperTradeResponse(
        success=True,
        message="Paper trade executed",
        position_id=new_position_id,
        order_id=new_order_id,
        entry_price=entry_price,
        quantity=quantity,
        leverage=leverage,
        required_margin=entry_price * quantity / leverage,
        tp_sl_stages=[
            TPSLStage(
                id=1,
                position_id=new_position_id,
                stage_type=TPSLStageType.SL,
                stage_number=0,
                target_price=trade.stop_loss,
                quantity=quantity,
                status="pending",
                created_at=datetime.utcnow()
            ),
            TPSLStage(
                id=2,
                position_id=new_position_id,
                stage_type=TPSLStageType.TP,
                stage_number=1,
                target_price=trade.tp1,
                quantity=quantity * 0.4,
                status="pending",
                created_at=datetime.utcnow()
            ),
            TPSLStage(
                id=3,
                position_id=new_position_id,
                stage_type=TPSLStageType.TP,
                stage_number=2,
                target_price=trade.tp2,
                quantity=quantity * 0.3,
                status="pending",
                created_at=datetime.utcnow()
            ),
            TPSLStage(
                id=4,
                position_id=new_position_id,
                stage_type=TPSLStageType.TP,
                stage_number=3,
                target_price=trade.tp3,
                quantity=quantity * 0.2,
                status="pending",
                created_at=datetime.utcnow()
            ),
            TPSLStage(
                id=5,
                position_id=new_position_id,
                stage_type=TPSLStageType.TP,
                stage_number=4,
                target_price=0,  # Trailing
                quantity=quantity * trade.runner_pct,
                status="pending",
                created_at=datetime.utcnow()
            )
        ]
    )


@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, request: ClosePositionRequest):
    """Close a position (fully or partially)"""
    position = next((p for p in MOCK_POSITIONS if p.id == position_id), None)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.status != PositionStatus.OPEN:
        raise HTTPException(status_code=400, detail="Position not open")

    # Mock close
    return {
        "success": True,
        "message": "Close order placed",
        "order_id": len(MOCK_ORDERS) + 1,
        "quantity": request.quantity or position.quantity,
        "order_type": request.order_type
    }


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: int):
    """Cancel an open order"""
    order = next((o for o in MOCK_ORDERS if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")

    return {"success": True, "message": "Order cancelled"}


@router.get("/orders", response_model=List[Order])
async def get_orders(
    position_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
):
    """Get orders"""
    orders = MOCK_ORDERS

    if position_id:
        orders = [o for o in orders if o.position_id == position_id]
    if status:
        orders = [o for o in orders if o.status == status]
    if exchange:
        orders = [o for o in orders if o.exchange == exchange.lower()]
    if symbol:
        orders = [o for o in orders if o.symbol == symbol.upper()]

    return orders


@router.get("/history", response_model=List[TradeHistoryEntry])
async def get_trade_history(
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    direction: Optional[TradeDirection] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    exit_reason: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get trade history"""
    trades = MOCK_TRADES

    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]
    if exchange:
        trades = [t for t in trades if t.exchange == exchange.lower()]
    if direction:
        trades = [t for t in trades if t.direction == direction]
    if start_date:
        trades = [t for t in trades if t.closed_at >= start_date]
    if end_date:
        trades = [t for t in trades if t.closed_at <= end_date]
    if exit_reason:
        trades = [t for t in trades if t.exit_reason == exit_reason]

    trades.sort(key=lambda x: x.closed_at, reverse=True)
    return trades[:limit]


@router.post("/paper/pause")
async def pause_paper_trading():
    """Pause paper trading"""
    return {"success": True, "message": "Paper trading paused"}


@router.post("/paper/resume")
async def resume_paper_trading():
    """Resume paper trading"""
    return {"success": True, "message": "Paper trading resumed"}


@router.post("/paper/reset")
async def reset_paper_trading():
    """Reset paper trading account to initial state"""
    global MOCK_POSITIONS, MOCK_ORDERS, MOCK_TRADES, MOCK_TPSL_STAGES
    MOCK_POSITIONS = []
    MOCK_ORDERS = []
    MOCK_TRADES = []
    MOCK_TPSL_STAGES = []

    return {
        "success": True,
        "message": "Paper trading reset to 100 USDT",
        "new_equity": 100.0,
        "reset_time": datetime.utcnow()
    }


@router.get("/pnl/summary")
async def get_pnl_summary(days: int = Query(30, ge=1, le=365)):
    """Get PnL summary"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_trades = [t for t in MOCK_TRADES if t.closed_at >= cutoff]

    if not recent_trades:
        return {
            "period_days": days,
            "total_trades": 0,
            "gross_pnl": 0.0,
            "total_fees": 0.0,
            "total_funding": 0.0,
            "net_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_r_multiple": 0.0,
            "max_drawdown": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0
        }

    wins = [t for t in recent_trades if t.net_pnl > 0]
    losses = [t for t in recent_trades if t.net_pnl <= 0]

    gross_profit = sum(t.net_pnl for t in wins)
    gross_loss = abs(sum(t.net_pnl for t in losses))

    return {
        "period_days": days,
        "total_trades": len(recent_trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "gross_pnl": sum(t.gross_pnl for t in recent_trades),
        "total_fees": sum(t.fees for t in recent_trades),
        "total_funding": sum(t.funding for t in recent_trades),
        "net_pnl": sum(t.net_pnl for t in recent_trades),
        "win_rate": len(wins) / len(recent_trades) * 100,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0,
        "expectancy": sum(t.net_pnl for t in recent_trades) / len(recent_trades),
        "avg_r_multiple": sum(t.r_multiple for t in recent_trades) / len(recent_trades),
        "max_drawdown": 0.0,  # Would calculate from equity curve
        "best_trade": max(t.net_pnl for t in recent_trades),
        "worst_trade": min(t.net_pnl for t in recent_trades),
        "avg_hold_time_hours": sum(t.hold_time_hours for t in recent_trades) / len(recent_trades),
        "by_exit_reason": {
            reason: len([t for t in recent_trades if t.exit_reason == reason])
            for reason in set(t.exit_reason for t in recent_trades)
        },
        "by_tp_stage": {
            stage: len([t for t in recent_trades if t.tp_stage_reached == stage])
            for stage in set(t.tp_stage_reached for t in recent_trades)
        }
    }