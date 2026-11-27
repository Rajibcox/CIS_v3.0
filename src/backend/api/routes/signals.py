"""
Signals API Routes for QUANTUM TRADER V1
Signal center, history, details, statistics
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
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



# Signal API availability
_SIGNAL_READ_UNAVAILABLE = (
    "Persisted signal records are not currently exposed by the API. "
    "Strategy-rule matches are not actionable signals and must not be presented as trades."
)


def _raise_signal_read_unavailable() -> None:
    raise HTTPException(status_code=503, detail=_SIGNAL_READ_UNAVAILABLE)


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
    page_size: int = Query(20, ge=1, le=100),
):
    """Signal history is unavailable until complete persisted signal records exist."""
    _raise_signal_read_unavailable()


@router.get("/active", response_model=List[SignalResponse])
async def get_active_signals():
    """Return active persisted signals only when the signal read model is implemented."""
    _raise_signal_read_unavailable()


@router.get("/best", response_model=List[SignalResponse])
async def get_best_signals(limit: int = Query(10, ge=1, le=50)):
    """Return ranked persisted signals only when real qualification data exists."""
    _raise_signal_read_unavailable()


@router.get("/stats/summary", response_model=SignalStats)
async def get_signal_stats(days: int = Query(30, ge=1, le=365)):
    """Signal performance statistics are unavailable without persisted outcome data."""
    _raise_signal_read_unavailable()


@router.get("/{signal_id}", response_model=SignalDetail)
async def get_signal_detail(signal_id: int):
    """Signal detail is unavailable until complete persisted trade-plan data exists."""
    _raise_signal_read_unavailable()


@router.post("/{signal_id}/paper-trade")
async def execute_paper_trade(signal_id: int):
    """Fail closed: signal-to-paper-execution wiring is not implemented."""
    raise HTTPException(
        status_code=409,
        detail=(
            "Paper trading from signals is disabled. The signal pipeline does not "
            "yet persist fully qualified trade plans or connect them to paper execution."
        ),
    )


@router.post("/scan-now")
async def trigger_scan(request: Request):
    """Run genuine strategy-rule matching without claiming actionable signals were created."""
    services = getattr(request.app.state, "services", None)
    signal_service = getattr(services, "signal_service", None)
    if signal_service is None:
        raise HTTPException(
            status_code=503,
            detail="Signal service is not initialized; no scan was run.",
        )

    try:
        await signal_service.generate_signals_now()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Signal scan failed; no actionable signals were created.",
        ) from None

    matches = signal_service.latest_strategy_matches
    return {
        "status": "completed",
        "strategy_matches": len(matches),
        "actionable_signals_created": 0,
        "message": (
            "Strategy-rule matching completed. Trade-plan qualification and "
            "signal persistence are not implemented; no paper trades were created."
        ),
    }
