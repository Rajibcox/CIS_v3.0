"""
Overview API Routes for QUANTUM TRADER V1
Dashboard summary, key metrics, system status
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

router = APIRouter(prefix="/api/v1/overview", tags=["overview"])


# Response Models
class EquitySnapshot(BaseModel):
    timestamp: datetime
    equity: float
    unrealized_pnl: float
    realized_pnl: float


class PositionSummary(BaseModel):
    symbol: str
    exchange: str
    direction: str
    entry_price: float
    current_price: float
    quantity: float
    unrealized_pnl: float
    leverage: float
    margin_used: float


class SystemStatus(BaseModel):
    status: str  # healthy, degraded, critical
    uptime_seconds: int
    services: dict
    exchange_connections: dict
    last_market_data_update: Optional[datetime]


class DashboardOverview(BaseModel):
    # Portfolio
    total_equity: float
    available_balance: float
    allocated_margin: float
    daily_pnl: float
    daily_pnl_pct: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    drawdown_pct: float
    peak_equity: float

    # Positions
    open_positions_count: int
    max_positions: int
    positions: List[PositionSummary]

    # Risk
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    max_leverage: int
    current_max_leverage_used: float

    # System
    system_status: SystemStatus
    trading_mode: str  # paper, live_eligible, live_armed, live_active

    # Performance (last 30 days)
    win_rate_30d: float
    profit_factor_30d: float
    expectancy_30d: float
    sharpe_30d: Optional[float]
    max_drawdown_30d: float

    # Timestamp
    timestamp: datetime


# Mock data for development - replace with real service calls
async def get_dashboard_overview() -> DashboardOverview:
    """Get complete dashboard overview"""
    return DashboardOverview(
        # Portfolio
        total_equity=100.0,
        available_balance=95.0,
        allocated_margin=5.0,
        daily_pnl=0.0,
        daily_pnl_pct=0.0,
        total_unrealized_pnl=0.0,
        total_realized_pnl=0.0,
        drawdown_pct=0.0,
        peak_equity=100.0,

        # Positions
        open_positions_count=0,
        max_positions=2,
        positions=[],

        # Risk
        risk_per_trade_pct=0.5,
        daily_loss_limit_pct=1.5,
        max_leverage=3,
        current_max_leverage_used=0.0,

        # System
        system_status=SystemStatus(
            status="healthy",
            uptime_seconds=3600,
            services={
                "market_data": "running",
                "strategy_engine": "running",
                "risk_engine": "running",
                "execution_engine": "running",
                "tp_sl_manager": "running",
                "pnl_analytics": "running",
                "telegram_bot": "stopped"
            },
            exchange_connections={
                "binance": "connected",
                "bitget": "connected"
            },
            last_market_data_update=datetime.utcnow()
        ),
        trading_mode="paper",

        # Performance
        win_rate_30d=0.0,
        profit_factor_30d=0.0,
        expectancy_30d=0.0,
        sharpe_30d=None,
        max_drawdown_30d=0.0,

        timestamp=datetime.utcnow()
    )


@router.get("", response_model=DashboardOverview)
async def get_overview():
    """Get complete dashboard overview"""
    return await get_dashboard_overview()


@router.get("/equity-curve")
async def get_equity_curve(days: int = 30):
    """Get equity curve data for charting"""
    # Mock data - replace with real query
    points = []
    base = 100.0
    for i in range(days):
        points.append({
            "date": (datetime.utcnow() - timedelta(days=days-i)).isoformat(),
            "equity": base + (i * 0.1),
            "drawdown": 0.0
        })
    return {"data": points}


@router.get("/positions", response_model=List[PositionSummary])
async def get_open_positions():
    """Get all open positions"""
    return []


@router.get("/quick-stats")
async def get_quick_stats():
    """Get quick stats for header bar"""
    return {
        "equity": 100.0,
        "daily_pnl": 0.0,
        "daily_pnl_pct": 0.0,
        "open_positions": 0,
        "mode": "paper",
        "status": "healthy"
    }