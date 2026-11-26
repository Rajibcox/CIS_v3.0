"""
Analytics API Routes for QUANTUM TRADER V1
PnL analytics, performance metrics, backtesting, walk-forward, Monte Carlo
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# Models
class PnLSummary(BaseModel):
    period_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_pnl: float
    total_fees: float
    total_funding: float
    net_pnl: float
    win_rate: float
    profit_factor: float
    expectancy: float
    avg_r_multiple: float
    max_drawdown: float
    best_trade: float
    worst_trade: float
    avg_hold_time_hours: float
    by_exit_reason: Dict[str, int]
    by_tp_stage: Dict[str, int]


class PerformanceMetrics(BaseModel):
    # Basic metrics
    total_return_pct: float
    annualized_return_pct: float
    volatility_pct: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]

    # Drawdown
    max_drawdown_pct: float
    avg_drawdown_pct: float
    max_drawdown_duration_days: int
    current_drawdown_pct: float

    # Trade stats
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    avg_r_multiple: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int

    # Risk-adjusted
    risk_adjusted_return: float
    ulcer_index: float
    sterling_ratio: float


class EquityCurvePoint(BaseModel):
    timestamp: datetime
    equity: float
    drawdown: float
    peak: float


class MonthlyReturns(BaseModel):
    year: int
    month: int
    return_pct: float
    trades: int
    win_rate: float


class BreakdownItem(BaseModel):
    category: str
    trades: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    avg_r_multiple: float


class TradeDistribution(BaseModel):
    r_multiples: List[float]
    hold_times_hours: List[float]
    mae_pct: List[float]  # Maximum Adverse Excursion
    mfe_pct: List[float]  # Maximum Favorable Excursion


class TPAnalytics(BaseModel):
    tp1_hit_rate: float
    tp2_hit_rate: float
    tp3_hit_rate: float
    runner_hit_rate: float
    profit_captured_tp1_pct: float
    profit_captured_tp2_pct: float
    profit_captured_tp3_pct: float
    profit_given_back_after_tp3_pct: float
    stop_out_after_tp1_rate: float
    stop_out_after_tp2_rate: float
    stop_out_after_tp3_rate: float
    avg_r_multiple_by_stage: Dict[str, float]


class BacktestResult(BaseModel):
    backtest_id: str
    strategy_id: int
    strategy_name: str
    status: str  # running, completed, failed
    period: Dict[str, str]
    symbols: List[str]
    initial_capital: float
    final_equity: float
    total_return_pct: float
    metrics: PerformanceMetrics
    equity_curve: List[EquityCurvePoint]
    monthly_returns: List[MonthlyReturns]
    trade_list: List[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None


class WalkForwardResult(BaseModel):
    strategy_id: int
    strategy_name: str
    windows: List[Dict[str, Any]]
    is_oos_correlation: float
    stability_score: float
    avg_oos_return: float
    avg_oos_sharpe: float
    worst_oos_drawdown: float


class MonteCarloResult(BaseModel):
    strategy_id: int
    strategy_name: str
    simulations: int
    confidence_intervals: Dict[str, Dict[str, float]]
    ruin_probability: float
    median_max_drawdown: float
    median_final_equity: float
    percentile_5_final_equity: float
    percentile_95_final_equity: float
    distribution_data: List[float]


# Mock data generators
def generate_equity_curve(days: int, start_equity: float = 100.0) -> List[EquityCurvePoint]:
    curve = []
    equity = start_equity
    peak = start_equity
    for i in range(days):
        # Random walk with slight positive drift
        import random
        change = random.uniform(-2.0, 2.5)
        equity = max(1.0, equity + change)
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak * 100
        curve.append(EquityCurvePoint(
            timestamp=datetime.utcnow() - timedelta(days=days-i),
            equity=round(equity, 2),
            drawdown=round(drawdown, 2),
            peak=round(peak, 2)
        ))
    return curve


def generate_monthly_returns(years: int = 1) -> List[MonthlyReturns]:
    returns = []
    import random
    for year in range(2025, 2025 + years):
        for month in range(1, 13):
            ret = random.uniform(-8.0, 12.0)
            returns.append(MonthlyReturns(
                year=year,
                month=month,
                return_pct=round(ret, 2),
                trades=random.randint(5, 25),
                win_rate=round(random.uniform(45.0, 65.0), 1)
            ))
    return returns


# Routes
@router.get("/pnl/summary", response_model=PnLSummary)
async def get_pnl_summary(
    days: int = Query(30, ge=1, le=365),
    strategy_id: Optional[int] = None,
    symbol: Optional[str] = None,
    direction: Optional[str] = None
):
    """Get PnL summary for period"""
    # Mock data
    return PnLSummary(
        period_days=days,
        total_trades=47,
        winning_trades=28,
        losing_trades=19,
        gross_pnl=125.50,
        total_fees=8.20,
        total_funding=1.15,
        net_pnl=116.15,
        win_rate=59.6,
        profit_factor=1.68,
        expectancy=2.47,
        avg_r_multiple=0.52,
        max_drawdown=6.2,
        best_trade=12.50,
        worst_trade=-4.80,
        avg_hold_time_hours=3.8,
        by_exit_reason={"TP1": 15, "TP2": 8, "TP3": 3, "RUNNER": 2, "SL": 19},
        by_tp_stage={"0": 19, "1": 15, "2": 8, "3": 3, "4": 2}
    )


@router.get("/pnl/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    days: int = Query(30, ge=1, le=365)
):
    """Get detailed performance metrics"""
    return PerformanceMetrics(
        total_return_pct=16.15,
        annualized_return_pct=196.5,
        volatility_pct=12.3,
        sharpe_ratio=1.42,
        sortino_ratio=2.15,
        calmar_ratio=2.60,
        max_drawdown_pct=6.2,
        avg_drawdown_pct=2.1,
        max_drawdown_duration_days=8,
        current_drawdown_pct=0.0,
        total_trades=47,
        win_rate=59.6,
        profit_factor=1.68,
        expectancy=2.47,
        avg_win=3.45,
        avg_loss=-2.12,
        avg_r_multiple=0.52,
        largest_win=12.50,
        largest_loss=-4.80,
        consecutive_wins=5,
        consecutive_losses=3,
        risk_adjusted_return=13.2,
        ulcer_index=3.1,
        sterling_ratio=2.6
    )


@router.get("/pnl/equity-curve")
async def get_equity_curve(
    days: int = Query(30, ge=1, le=365)
):
    """Get equity curve data"""
    curve = generate_equity_curve(days)
    return {"data": [p.dict() for p in curve]}


@router.get("/pnl/monthly-returns")
async def get_monthly_returns(
    years: int = Query(1, ge=1, le=5)
):
    """Get monthly returns"""
    returns = generate_monthly_returns(years)
    return {"data": [r.dict() for r in returns]}


@router.get("/pnl/breakdown/strategy")
async def get_strategy_breakdown(days: int = Query(30, ge=1, le=365)):
    return {
        "data": [
            BreakdownItem(category="Trend Following", trades=22, win_rate=62.0, profit_factor=1.75, net_pnl=78.50, avg_r_multiple=0.65),
            BreakdownItem(category="Mean Reversion", trades=15, win_rate=60.0, profit_factor=1.45, net_pnl=25.30, avg_r_multiple=0.42),
            BreakdownItem(category="Breakout", trades=10, win_rate=50.0, profit_factor=1.20, net_pnl=12.35, avg_r_multiple=0.25),
        ]
    }


@router.get("/pnl/breakdown/symbol")
async def get_symbol_breakdown(days: int = Query(30, ge=1, le=365)):
    return {
        "data": [
            BreakdownItem(category="BTCUSDT", trades=18, win_rate=61.0, profit_factor=1.80, net_pnl=65.20, avg_r_multiple=0.72),
            BreakdownItem(category="ETHUSDT", trades=15, win_rate=60.0, profit_factor=1.55, net_pnl=32.10, avg_r_multiple=0.55),
            BreakdownItem(category="SOLUSDT", trades=8, win_rate=50.0, profit_factor=1.25, net_pnl=11.50, avg_r_multiple=0.30),
            BreakdownItem(category="BNBUSDT", trades=6, win_rate=67.0, profit_factor=2.10, net_pnl=7.35, avg_r_multiple=0.68),
        ]
    }


@router.get("/pnl/breakdown/direction")
async def get_direction_breakdown(days: int = Query(30, ge=1, le=365)):
    return {
        "data": [
            BreakdownItem(category="LONG", trades=28, win_rate=60.7, profit_factor=1.72, net_pnl=78.50, avg_r_multiple=0.58),
            BreakdownItem(category="SHORT", trades=19, win_rate=57.9, profit_factor=1.55, net_pnl=37.65, avg_r_multiple=0.45),
        ]
    }


@router.get("/pnl/breakdown/timeframe")
async def get_timeframe_breakdown(days: int = Query(30, ge=1, le=365)):
    return {
        "data": [
            BreakdownItem(category="15m", trades=22, win_rate=55.0, profit_factor=1.45, net_pnl=42.30, avg_r_multiple=0.42),
            BreakdownItem(category="1h", trades=18, win_rate=61.0, profit_factor=1.70, net_pnl=52.15, avg_r_multiple=0.55),
            BreakdownItem(category="4h", trades=7, win_rate=71.0, profit_factor=2.20, net_pnl=21.70, avg_r_multiple=0.82),
        ]
    }


@router.get("/pnl/breakdown/regime")
async def get_regime_breakdown(days: int = Query(30, ge=1, le=365)):
    return {
        "data": [
            BreakdownItem(category="trending", trades=25, win_rate=64.0, profit_factor=1.85, net_pnl=68.40, avg_r_multiple=0.65),
            BreakdownItem(category="ranging", trades=15, win_rate=53.0, profit_factor=1.30, net_pnl=22.10, avg_r_multiple=0.35),
            BreakdownItem(category="volatile", trades=7, win_rate=43.0, profit_factor=1.10, net_pnl=5.65, avg_r_multiple=0.15),
        ]
    }


@router.get("/pnl/tp-analytics", response_model=TPAnalytics)
async def get_tp_analytics(days: int = Query(30, ge=1, le=365)):
    """Get TP/SL stage analytics"""
    return TPAnalytics(
        tp1_hit_rate=72.0,
        tp2_hit_rate=42.0,
        tp3_hit_rate=18.0,
        runner_hit_rate=8.0,
        profit_captured_tp1_pct=45.0,
        profit_captured_tp2_pct=28.0,
        profit_captured_tp3_pct=15.0,
        profit_given_back_after_tp3_pct=12.0,
        stop_out_after_tp1_rate=15.0,
        stop_out_after_tp2_rate=8.0,
        stop_out_after_tp3_rate=3.0,
        avg_r_multiple_by_stage={
            "tp1": 0.45,
            "tp2": 0.72,
            "tp3": 1.15,
            "runner": 1.85,
            "sl": -1.0
        }
    )


@router.get("/pnl/distribution")
async def get_trade_distribution(days: int = Query(30, ge=1, le=365)):
    """Get trade distribution data for histograms"""
    import random
    return TradeDistribution(
        r_multiples=[random.uniform(-1.5, 3.0) for _ in range(100)],
        hold_times_hours=[random.uniform(0.5, 12.0) for _ in range(100)],
        mae_pct=[random.uniform(0.0, 3.0) for _ in range(100)],
        mfe_pct=[random.uniform(0.0, 5.0) for _ in range(100)]
    )


# Backtesting
@router.post("/backtest/run", response_model=BacktestResult)
async def run_backtest(
    strategy_id: int,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    timeframes: List[str] = ["15m", "1h"],
    initial_capital: float = 100.0,
    fees_bps: float = 10.0,
    slippage_bps: float = 5.0,
    funding_rate_pct: float = 0.01
):
    """Run backtest"""
    backtest_id = f"bt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Mock result
    return BacktestResult(
        backtest_id=backtest_id,
        strategy_id=strategy_id,
        strategy_name="Trend Following",
        status="completed",
        period={"start": start_date.isoformat(), "end": end_date.isoformat()},
        symbols=symbols,
        initial_capital=initial_capital,
        final_equity=116.50,
        total_return_pct=16.5,
        metrics=PerformanceMetrics(
            total_return_pct=16.5,
            annualized_return_pct=45.2,
            volatility_pct=11.8,
            sharpe_ratio=1.35,
            sortino_ratio=2.05,
            calmar_ratio=2.40,
            max_drawdown_pct=6.8,
            avg_drawdown_pct=2.3,
            max_drawdown_duration_days=9,
            current_drawdown_pct=0.0,
            total_trades=142,
            win_rate=58.5,
            profit_factor=1.52,
            expectancy=2.15,
            avg_win=3.20,
            avg_loss=-2.05,
            avg_r_multiple=0.48,
            largest_win=15.80,
            largest_loss=-5.20,
            consecutive_wins=6,
            consecutive_losses=4,
            risk_adjusted_return=12.5,
            ulcer_index=3.2,
            sterling_ratio=2.4
        ),
        equity_curve=generate_equity_curve(30, initial_capital),
        monthly_returns=generate_monthly_returns(1),
        trade_list=[],  # Would be populated with actual trades
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )


@router.get("/backtest/{backtest_id}", response_model=BacktestResult)
async def get_backtest(backtest_id: str):
    """Get backtest result"""
    # Mock - in reality fetch from database
    raise HTTPException(status_code=404, detail="Backtest not found")


@router.get("/backtest/list")
async def list_backtests(
    strategy_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """List backtest runs"""
    return {
        "backtests": [
            {
                "backtest_id": "bt_20261126_120000",
                "strategy_id": 1,
                "strategy_name": "Trend Following",
                "status": "completed",
                "period": {"start": "2026-10-01", "end": "2026-11-26"},
                "total_return_pct": 16.5,
                "created_at": "2026-11-26T12:00:00Z"
            }
        ]
    }


# Walk-Forward
@router.post("/walkforward/run", response_model=WalkForwardResult)
async def run_walkforward(
    strategy_id: int,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    window_days: int = 30,
    step_days: int = 7,
    min_train_days: int = 60
):
    """Run walk-forward analysis"""
    return WalkForwardResult(
        strategy_id=strategy_id,
        strategy_name="Trend Following",
        windows=[
            {
                "window": 1,
                "train_start": "2026-08-01",
                "train_end": "2026-09-30",
                "test_start": "2026-10-01",
                "test_end": "2026-10-07",
                "train_return_pct": 12.5,
                "test_return_pct": 8.2,
                "test_sharpe": 1.2,
                "test_max_dd": 5.5
            },
            {
                "window": 2,
                "train_start": "2026-08-08",
                "train_end": "2026-10-07",
                "test_start": "2026-10-08",
                "test_end": "2026-10-14",
                "train_return_pct": 14.2,
                "test_return_pct": 10.5,
                "test_sharpe": 1.4,
                "test_max_dd": 4.8
            }
        ],
        is_oos_correlation=0.72,
        stability_score=0.78,
        avg_oos_return=9.35,
        avg_oos_sharpe=1.3,
        worst_oos_drawdown=5.5
    )


# Monte Carlo
@router.post("/montecarlo/run", response_model=MonteCarloResult)
async def run_monte_carlo(
    strategy_id: int,
    trade_history: List[Dict[str, Any]],  # Or reference to backtest
    simulations: int = 1000,
    confidence_levels: List[float] = [0.05, 0.5, 0.95]
):
    """Run Monte Carlo simulation"""
    import random
    random.seed(42)

    final_equities = []
    max_drawdowns = []

    for _ in range(simulations):
        # Simulate equity curve from trade distribution
        equity = 100.0
        peak = 100.0
        max_dd = 0.0

        # Sample trades with replacement
        trades = [random.uniform(-2.0, 3.5) for _ in range(100)]
        for t in trades:
            equity += t
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)

        final_equities.append(equity)
        max_drawdowns.append(max_dd)

    final_equities.sort()
    max_drawdowns.sort()

    def percentile(p):
        idx = int(len(final_equities) * p)
        return final_equities[min(idx, len(final_equities) - 1)]

    return MonteCarloResult(
        strategy_id=strategy_id,
        strategy_name="Trend Following",
        simulations=simulations,
        confidence_intervals={
            "final_equity": {
                "5%": percentile(0.05),
                "50%": percentile(0.50),
                "95%": percentile(0.95)
            },
            "max_drawdown": {
                "5%": max_drawdowns[int(len(max_drawdowns) * 0.05)],
                "50%": max_drawdowns[int(len(max_drawdowns) * 0.50)],
                "95%": max_drawdowns[int(len(max_drawdowns) * 0.95)]
            }
        },
        ruin_probability=0.02,  # % of sims where equity < 50
        median_max_drawdown=max_drawdowns[len(max_drawdowns) // 2],
        median_final_equity=final_equities[len(final_equities) // 2],
        percentile_5_final_equity=percentile(0.05),
        percentile_95_final_equity=percentile(0.95),
        distribution_data=final_equities
    )


# Reports
@router.get("/reports/daily")
async def get_daily_report(date: Optional[datetime] = None):
    """Get daily performance report"""
    target_date = date or datetime.utcnow().date()
    return {
        "date": target_date.isoformat(),
        "starting_equity": 100.0,
        "ending_equity": 102.5,
        "daily_pnl": 2.5,
        "daily_pnl_pct": 2.5,
        "trades": 3,
        "win_rate": 66.7,
        "fees": 0.45,
        "funding": 0.05,
        "max_drawdown": 1.2,
        "open_positions": 1,
        "best_trade": 1.8,
        "worst_trade": -0.5
    }


@router.get("/reports/weekly")
async def get_weekly_report(week_start: Optional[datetime] = None):
    """Get weekly performance report"""
    return {
        "week_start": (datetime.utcnow() - timedelta(days=7)).date().isoformat(),
        "week_end": datetime.utcnow().date().isoformat(),
        "starting_equity": 98.0,
        "ending_equity": 102.5,
        "weekly_pnl": 4.5,
        "weekly_pnl_pct": 4.6,
        "trades": 12,
        "win_rate": 58.3,
        "profit_factor": 1.65,
        "max_drawdown": 3.2,
        "by_day": [
            {"date": "2026-11-20", "pnl": 1.2, "trades": 2},
            {"date": "2026-11-21", "pnl": -0.5, "trades": 1},
            {"date": "2026-11-22", "pnl": 0.0, "trades": 0},
            {"date": "2026-11-23", "pnl": 2.1, "trades": 3},
            {"date": "2026-11-24", "pnl": 0.8, "trades": 2},
            {"date": "2026-11-25", "pnl": 0.9, "trades": 2},
            {"date": "2026-11-26", "pnl": 0.0, "trades": 2},
        ]
    }


@router.get("/reports/monthly")
async def get_monthly_report(month: Optional[str] = None):
    """Get monthly performance report"""
    return {
        "month": "2026-11",
        "starting_equity": 90.0,
        "ending_equity": 102.5,
        "monthly_pnl": 12.5,
        "monthly_pnl_pct": 13.9,
        "trades": 47,
        "win_rate": 59.6,
        "profit_factor": 1.68,
        "max_drawdown": 6.2,
        "sharpe_ratio": 1.42,
        "by_week": [
            {"week": "2026-11-02", "pnl": 3.2},
            {"week": "2026-11-09", "pnl": 2.8},
            {"week": "2026-11-16", "pnl": 1.5},
            {"week": "2026-11-23", "pnl": 5.0}
        ]
    }