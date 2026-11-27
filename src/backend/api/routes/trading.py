"""
Trading API routes for QUANTUM TRADER V1.

The current build exposes paper-only execution services, but this API does not
yet have a complete persistence/read-model contract for every response. Until
that integration exists, it must fail closed rather than manufacture trades,
positions, orders, PnL, or successful execution acknowledgements.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


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
    tp_stage: int = 0
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
    stage_number: int
    target_price: float
    quantity: float
    status: str
    exchange_order_id: Optional[str] = None
    triggered_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    created_at: datetime


class PaperTradeRequest(BaseModel):
    signal_id: Optional[int] = None
    symbol: str
    exchange: str
    direction: TradeDirection
    entry_price: Optional[float] = None
    quantity: Optional[float] = None
    leverage: Optional[float] = None
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
    tp_sl_stages: List[TPSLStage] = Field(default_factory=list)


class ClosePositionRequest(BaseModel):
    position_id: int
    quantity: Optional[float] = None
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
    exit_reason: str
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


def _data_unavailable(resource: str):
    raise HTTPException(
        status_code=503,
        detail=(
            f"{resource} is unavailable: the trading API is not yet connected "
            "to an authoritative persisted read model. No simulated data is returned."
        ),
    )


def _operation_disabled(operation: str):
    raise HTTPException(
        status_code=409,
        detail=(
            f"{operation} is disabled: this API operation is not yet wired to "
            "the paper execution and persistence services. No order or state change occurred."
        ),
    )


@router.get("/paper/status", response_model=PaperAccountStatus)
async def get_paper_status():
    _data_unavailable("Paper account status")


@router.get("/positions", response_model=List[Position])
async def get_positions(
    status: Optional[PositionStatus] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
):
    _data_unavailable("Positions")


@router.get("/positions/{position_id}", response_model=Position)
async def get_position(position_id: int):
    _data_unavailable(f"Position {position_id}")


@router.get("/positions/{position_id}/tp-sl", response_model=List[TPSLStage])
async def get_position_tp_sl(position_id: int):
    _data_unavailable(f"TP/SL stages for position {position_id}")


@router.post("/paper-trade", response_model=PaperTradeResponse)
async def place_paper_trade(trade: PaperTradeRequest):
    _operation_disabled("Paper trade submission")


@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, request: ClosePositionRequest):
    _operation_disabled("Position close")


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: int):
    _operation_disabled("Order cancellation")


@router.get("/orders", response_model=List[Order])
async def get_orders(
    position_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None,
):
    _data_unavailable("Orders")


@router.get("/history", response_model=List[TradeHistoryEntry])
async def get_trade_history(
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    direction: Optional[TradeDirection] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    exit_reason: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    _data_unavailable("Trade history")


@router.post("/paper/pause")
async def pause_paper_trading():
    _operation_disabled("Paper trading pause")


@router.post("/paper/resume")
async def resume_paper_trading():
    _operation_disabled("Paper trading resume")


@router.post("/paper/reset")
async def reset_paper_trading():
    _operation_disabled("Paper account reset")


@router.get("/pnl/summary")
async def get_pnl_summary(days: int = Query(30, ge=1, le=365)):
    _data_unavailable("PnL summary")
