"""
Signals API Routes for QUANTUM TRADER V1
Signal center, history, details, statistics
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


# Enums
class SignalStatus(str, Enum):
    CANDIDATE = "candidate"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    REJECTED = "rejected"
    EXECUTED = "executed"


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    SIDEWAYS = "sideways"


# Models
class SignalBase(BaseModel):
    symbol: str
    exchange: str
    direction: SignalDirection
    strategy: str
    timeframe: str
    signal_score: float
    regime: MarketRegime
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    runner_quantity: float
    risk_reward: float
    suggested_leverage: float
    position_quantity: float
    notional: float
    required_margin: float
    estimated_fees: float
    estimated_funding: float
    net_pnl_tp1: float
    net_pnl_tp2: float
    net_pnl_tp3: float
    net_pnl_runner: float
    htf_alignment: bool
    btc_alignment: bool
    supporting_evidence: List[str]
    invalidating_conditions: List[str]


class SignalResponse(SignalBase):
    id: int
    status: SignalStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    triggered_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class SignalDetail(SignalResponse):
    # Extended details
    entry_zone_low: float
    entry_zone_high: float
    market_structure: Dict[str, Any]
    indicator_values: Dict[str, float]
    higher_timeframe_context: Dict[str, Any]
    risk_calculation: Dict[str, Any]
    leverage_decision: Dict[str, Any]


class SignalHistoryResponse(BaseModel):
    signals: List[SignalResponse]
    total: int
    page: int
    page_size: int
    filters: Dict[str, Any]


class SignalStats(BaseModel):
    total_signals: int
    by_status: Dict[str, int]
    by_direction: Dict[str, int]
    by_strategy: Dict[str, int]
    avg_score: float
    execution_rate: float
    avg_risk_reward: float
    tp1_hit_rate: float
    tp2_hit_rate: float
    tp3_hit_rate: float
    runner_profit_pct: float


# Mock data
def generate_mock_signals(count: int = 20) -> List[SignalResponse]:
    signals = []
    base_time = datetime.utcnow()
    strategies = ["Trend Following", "Breakout", "Mean Reversion", "Momentum Scalping", "Volume Expansion"]
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
    exchanges = ["binance", "bitget"]
    statuses = list(SignalStatus)
    directions = list(SignalDirection)
    regimes = list(MarketRegime)

    for i in range(count):
        direction = directions[i % 2]
        entry = 45000 + (i * 100) if direction == SignalDirection.LONG else 45000 - (i * 100)
        stop = entry - 500 if direction == SignalDirection.LONG else entry + 500
        tp1 = entry + 800 if direction == SignalDirection.LONG else entry - 800
        tp2 = entry + 1500 if direction == SignalDirection.LONG else entry - 1500
        tp3 = entry + 2500 if direction == SignalDirection.LONG else entry - 2500

        status = statuses[i % len(statuses)]
        created = base_time - timedelta(hours=i * 2)

        signals.append(SignalResponse(
            id=i + 1,
            symbol=symbols[i % len(symbols)],
            exchange=exchanges[i % len(exchanges)],
            direction=direction,
            strategy=strategies[i % len(strategies)],
            timeframe=["15m", "1h", "4h"][i % 3],
            signal_score=70 + (i % 25),
            regime=regimes[i % len(regimes)],
            entry_price=entry,
            stop_loss=stop,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            runner_quantity=0.001,
            risk_reward=2.5 + (i % 3) * 0.5,
            suggested_leverage=3.0,
            position_quantity=0.01,
            notional=450.0,
            required_margin=150.0,
            estimated_fees=0.9,
            estimated_funding=0.05,
            net_pnl_tp1=35.0,
            net_pnl_tp2=65.0,
            net_pnl_tp3=95.0,
            net_pnl_runner=15.0,
            htf_alignment=i % 2 == 0,
            btc_alignment=i % 3 != 0,
            supporting_evidence=["RSI oversold", "Volume spike", "HTF trend alignment"],
            invalidating_conditions=["BTC breaks 42k", "Volume dries up"],
            status=status,
            created_at=created,
            updated_at=created,
            expires_at=created + timedelta(hours=4),
            triggered_at=created + timedelta(hours=1) if status in [SignalStatus.TRIGGERED, SignalStatus.EXECUTED] else None,
            executed_at=created + timedelta(hours=1, minutes=5) if status == SignalStatus.EXECUTED else None,
            rejection_reason="Score below threshold" if status == SignalStatus.REJECTED else None
        ))

    return signals


MOCK_SIGNALS = generate_mock_signals(50)


# Routes
@router.get("", response_model=SignalHistoryResponse)
async def get_signals(
    status: Optional[SignalStatus] = None,
    direction: Optional[SignalDirection] = None,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_score: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get signal history with filters"""
    filtered = MOCK_SIGNALS

    if status:
        filtered = [s for s in filtered if s.status == status]
    if direction:
        filtered = [s for s in filtered if s.direction == direction]
    if strategy:
        filtered = [s for s in filtered if s.strategy == strategy]
    if symbol:
        filtered = [s for s in filtered if s.symbol == symbol.upper()]
    if exchange:
        filtered = [s for s in filtered if s.exchange == exchange.lower()]
    if start_date:
        filtered = [s for s in filtered if s.created_at >= start_date]
    if end_date:
        filtered = [s for s in filtered if s.created_at <= end_date]
    if min_score:
        filtered = [s for s in filtered if s.signal_score >= min_score]

    # Sort by created_at desc
    filtered.sort(key=lambda x: x.created_at, reverse=True)

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size

    return SignalHistoryResponse(
        signals=filtered[start:end],
        total=total,
        page=page,
        page_size=page_size,
        filters={
            "status": status,
            "direction": direction,
            "strategy": strategy,
            "symbol": symbol,
            "exchange": exchange,
            "start_date": start_date,
            "end_date": end_date,
            "min_score": min_score
        }
    )


@router.get("/active", response_model=List[SignalResponse])
async def get_active_signals():
    """Get currently active/qualified signals"""
    active = [s for s in MOCK_SIGNALS if s.status in [SignalStatus.ACTIVE, SignalStatus.QUALIFIED]]
    active.sort(key=lambda x: x.signal_score, reverse=True)
    return active[:20]


@router.get("/best", response_model=List[SignalResponse])
async def get_best_signals(limit: int = Query(10, ge=1, le=50)):
    """Get highest scored signals"""
    qualified = [s for s in MOCK_SIGNALS if s.status in [SignalStatus.QUALIFIED, SignalStatus.ACTIVE]]
    qualified.sort(key=lambda x: x.signal_score, reverse=True)
    return qualified[:limit]


@router.get("/{signal_id}", response_model=SignalDetail)
async def get_signal_detail(signal_id: int):
    """Get detailed signal analysis"""
    signal = next((s for s in MOCK_SIGNALS if s.id == signal_id), None)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Extended detail
    return SignalDetail(
        **signal.dict(),
        entry_zone_low=signal.entry_price * 0.998,
        entry_zone_high=signal.entry_price * 1.002,
        market_structure={
            "trend": "bullish" if signal.direction == SignalDirection.LONG else "bearish",
            "structure": "higher highs, higher lows" if signal.direction == SignalDirection.LONG else "lower highs, lower lows",
            "key_level": signal.tp1,
            "invalidation_level": signal.stop_loss
        },
        indicator_values={
            "RSI_14": 35.0 if signal.direction == SignalDirection.LONG else 65.0,
            "MACD": 120.0,
            "EMA_9": signal.entry_price * 1.001,
            "EMA_21": signal.entry_price * 0.999,
            "VWAP": signal.entry_price * 1.0005,
            "ATR_14": 450.0,
            "ADX_14": 28.0,
            "Volume_Ratio": 1.8
        },
        higher_timeframe_context={
            "4h": {"trend": "bullish", "rsi": 55, "ema_alignment": True},
            "1d": {"trend": "bullish", "rsi": 52, "ema_alignment": True}
        },
        risk_calculation={
            "equity": 100.0,
            "risk_per_trade": 0.5,
            "risk_amount": 0.5,
            "stop_distance": 500.0,
            "stop_distance_pct": 1.11,
            "position_size": 0.01,
            "notional": 450.0,
            "leverage": 3.0,
            "required_margin": 150.0,
            "available_margin": 95.0,
            "liquidation_price": 43500.0 if signal.direction == SignalDirection.LONG else 46500.0,
            "liquidation_buffer_pct": 3.3
        },
        leverage_decision={
            "selected_leverage": 3.0,
            "position_quantity": 0.01,
            "notional": 450.0,
            "required_margin": 150.0,
            "max_planned_loss": 0.5,
            "stop_distance": 500.0,
            "liquidation_price": 43500.0,
            "liquidation_buffer": 1500.0,
            "estimated_fees": 0.9,
            "funding_assumption": 0.05,
            "net_tp1_profit": 35.0,
            "net_tp2_profit": 65.0,
            "net_tp3_profit": 95.0,
            "rejected_alternatives": [
                {"leverage": 5, "reason": "Exceeds max leverage 3x"},
                {"leverage": 1, "reason": "Insufficient margin efficiency"}
            ],
            "reason": "Risk-first sizing: 0.5% risk = 0.5 USDT. Stop distance 500 USDT -> 0.01 qty. 3x leverage fits in available margin."
        }
    )


@router.get("/stats/summary", response_model=SignalStats)
async def get_signal_stats(
    days: int = Query(30, ge=1, le=365)
):
    """Get signal statistics"""
    # Filter by date
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = [s for s in MOCK_SIGNALS if s.created_at >= cutoff]

    if not recent:
        return SignalStats(
            total_signals=0,
            by_status={},
            by_direction={},
            by_strategy={},
            avg_score=0,
            execution_rate=0,
            avg_risk_reward=0,
            tp1_hit_rate=0,
            tp2_hit_rate=0,
            tp3_hit_rate=0,
            runner_profit_pct=0
        )

    by_status = {}
    by_direction = {}
    by_strategy = {}

    for s in recent:
        by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
        by_direction[s.direction.value] = by_direction.get(s.direction.value, 0) + 1
        by_strategy[s.strategy] = by_strategy.get(s.strategy, 0) + 1

    executed = [s for s in recent if s.status == SignalStatus.EXECUTED]
    tp1_hits = len([s for s in executed if s.triggered_at])  # Simplified

    return SignalStats(
        total_signals=len(recent),
        by_status=by_status,
        by_direction=by_direction,
        by_strategy=by_strategy,
        avg_score=sum(s.signal_score for s in recent) / len(recent),
        execution_rate=len(executed) / len(recent) * 100 if recent else 0,
        avg_risk_reward=sum(s.risk_reward for s in recent) / len(recent),
        tp1_hit_rate=75.0,  # Mock
        tp2_hit_rate=45.0,  # Mock
        tp3_hit_rate=25.0,  # Mock
        runner_profit_pct=12.0  # Mock
    )


@router.post("/{signal_id}/paper-trade")
async def execute_paper_trade(signal_id: int):
    """Execute a paper trade from a signal"""
    signal = next((s for s in MOCK_SIGNALS if s.id == signal_id), None)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    if signal.status not in [SignalStatus.QUALIFIED, SignalStatus.ACTIVE]:
        raise HTTPException(status_code=400, detail="Signal not in executable state")

    # In real implementation, this would call the execution service
    return {
        "success": True,
        "message": "Paper trade executed",
        "position_id": 123,
        "signal_id": signal_id,
        "entry_price": signal.entry_price,
        "quantity": signal.position_quantity,
        "leverage": signal.suggested_leverage
    }


@router.post("/scan-now")
async def trigger_scan():
    """Trigger immediate market scan"""
    return {
        "success": True,
        "message": "Scan triggered",
        "scan_id": "scan_20261126_153000",
        "estimated_duration_seconds": 30
    }