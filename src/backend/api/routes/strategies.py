"""
Strategy API Routes for QUANTUM TRADER V1
Strategy management, visual builder, performance, versions
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


# Enums
class RuleType(str, Enum):
    INDICATOR_VS_VALUE = "indicator_vs_value"
    INDICATOR_VS_INDICATOR = "indicator_vs_indicator"
    PRICE_ACTION = "price_action"
    VOLUME = "volume"
    TREND = "trend"
    REGIME = "regime"
    TIME_BASED = "time_based"


class ComparisonOperator(str, Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"


# Models
class IndicatorConfig(BaseModel):
    name: str
    params: Dict[str, Any] = {}
    source: str = "close"  # close, open, high, low, hl2, hlc3, ohlc4


class RuleCondition(BaseModel):
    # Indicator vs Value
    indicator: Optional[IndicatorConfig] = None
    operator: Optional[ComparisonOperator] = None
    threshold: Optional[float] = None

    # Indicator vs Indicator
    indicator_a: Optional[IndicatorConfig] = None
    indicator_b: Optional[IndicatorConfig] = None

    # Price Action
    price_relation: Optional[str] = None  # above_vwap, below_vwap, breakout_high, etc.

    # Volume
    volume_condition: Optional[str] = None  # volume_spike, volume_dry_up, etc.
    volume_multiplier: Optional[float] = None

    # Trend
    trend_condition: Optional[str] = None  # strong_uptrend, weak_downtrend, etc.
    adx_threshold: Optional[float] = None

    # Regime
    regime: Optional[str] = None  # trending, ranging, volatile, etc.

    # Time
    session: Optional[str] = None  # asian, european, us
    time_range: Optional[str] = None  # "08:00-16:00"


class RuleGroup(BaseModel):
    operator: LogicalOperator = LogicalOperator.AND
    conditions: List[RuleCondition] = []
    groups: List["RuleGroup"] = []


class StrategyRuleSet(BaseModel):
    entry_rules: RuleGroup
    exit_rules: RuleGroup
    long_rules: Optional[RuleGroup] = None
    short_rules: Optional[RuleGroup] = None


class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    is_active: bool = True
    direction: str = "BOTH"  # LONG, SHORT, BOTH
    weight: float = 1.0
    risk_multiplier: float = 1.0
    timeframes: List[str] = ["15m", "1h"]
    symbols: List[str] = []  # Empty = all eligible
    min_signal_score: float = 70.0


class StrategyCreate(StrategyBase):
    rule_set: StrategyRuleSet


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    weight: Optional[float] = None
    risk_multiplier: Optional[float] = None
    timeframes: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    min_signal_score: Optional[float] = None
    rule_set: Optional[StrategyRuleSet] = None


class StrategyResponse(StrategyBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    signal_count_24h: int = 0
    win_rate_30d: float = 0.0
    profit_factor_30d: float = 0.0
    expectancy_30d: float = 0.0


class StrategyPerformance(BaseModel):
    strategy_id: int
    strategy_name: str
    version: str
    period_days: int
    total_signals: int
    executed_signals: int
    win_rate: float
    loss_rate: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    avg_r_multiple: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    by_symbol: Dict[str, Dict[str, float]]
    by_timeframe: Dict[str, Dict[str, float]]
    by_direction: Dict[str, Dict[str, float]]
    by_regime: Dict[str, Dict[str, float]]
    equity_curve: List[Dict[str, Any]]


class StrategyVersion(BaseModel):
    version: str
    description: str
    created_at: datetime
    performance: Optional[StrategyPerformance] = None
    is_current: bool


class IndicatorInfo(BaseModel):
    name: str
    display_name: str
    category: str  # trend, momentum, volatility, volume, other
    description: str
    default_params: Dict[str, Any]
    param_schema: Dict[str, Any]
    supports_timeframes: List[str]
    repainting_risk: str  # none, low, medium, high
    lookahead_risk: bool


# Mock data
MOCK_STRATEGIES = [
    {
        "id": 1,
        "name": "Trend Following",
        "description": "Long-only trend following strategy using EMA alignment and ADX",
        "version": "1.2.0",
        "is_active": True,
        "direction": "BOTH",
        "weight": 1.0,
        "risk_multiplier": 1.0,
        "timeframes": ["15m", "1h", "4h"],
        "symbols": [],
        "min_signal_score": 70.0,
        "created_by": "admin",
        "created_at": datetime(2026, 1, 15),
        "updated_at": datetime(2026, 11, 20),
        "signal_count_24h": 3,
        "win_rate_30d": 58.5,
        "profit_factor_30d": 1.45,
        "expectancy_30d": 0.32
    },
    {
        "id": 2,
        "name": "Mean Reversion",
        "description": "Short-term mean reversion using RSI and Bollinger Bands",
        "version": "1.0.0",
        "is_active": True,
        "direction": "BOTH",
        "weight": 0.8,
        "risk_multiplier": 0.8,
        "timeframes": ["5m", "15m"],
        "symbols": [],
        "min_signal_score": 65.0,
        "created_by": "admin",
        "created_at": datetime(2026, 2, 1),
        "updated_at": datetime(2026, 11, 15),
        "signal_count_24h": 5,
        "win_rate_30d": 62.0,
        "profit_factor_30d": 1.28,
        "expectancy_30d": 0.18
    },
    {
        "id": 3,
        "name": "Breakout",
        "description": "Breakout and retest strategy with volume confirmation",
        "version": "1.1.0",
        "is_active": False,
        "direction": "LONG",
        "weight": 1.2,
        "risk_multiplier": 1.1,
        "timeframes": ["1h", "4h"],
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "min_signal_score": 75.0,
        "created_by": "admin",
        "created_at": datetime(2026, 3, 10),
        "updated_at": datetime(2026, 11, 10),
        "signal_count_24h": 0,
        "win_rate_30d": 52.0,
        "profit_factor_30d": 1.65,
        "expectancy_30d": 0.45
    },
]


MOCK_INDICATORS = [
    IndicatorInfo(
        name="RSI",
        display_name="Relative Strength Index",
        category="momentum",
        description="Momentum oscillator measuring speed and change of price movements",
        default_params={"period": 14},
        param_schema={"period": {"type": "integer", "min": 2, "max": 50, "default": 14}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="MACD",
        display_name="Moving Average Convergence Divergence",
        category="trend",
        description="Trend-following momentum indicator showing relationship between two EMAs",
        default_params={"fast": 12, "slow": 26, "signal": 9},
        param_schema={
            "fast": {"type": "integer", "min": 5, "max": 20, "default": 12},
            "slow": {"type": "integer", "min": 20, "max": 50, "default": 26},
            "signal": {"type": "integer", "min": 5, "max": 20, "default": 9}
        },
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="EMA",
        display_name="Exponential Moving Average",
        category="trend",
        description="Exponentially weighted moving average giving more weight to recent prices",
        default_params={"period": 9},
        param_schema={"period": {"type": "integer", "min": 2, "max": 200, "default": 9}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="SMA",
        display_name="Simple Moving Average",
        category="trend",
        description="Arithmetic mean of prices over specified period",
        default_params={"period": 20},
        param_schema={"period": {"type": "integer", "min": 2, "max": 200, "default": 20}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="BOLLINGER_BANDS",
        display_name="Bollinger Bands",
        category="volatility",
        description="Volatility bands placed above and below a moving average",
        default_params={"period": 20, "std_dev": 2.0},
        param_schema={
            "period": {"type": "integer", "min": 5, "max": 50, "default": 20},
            "std_dev": {"type": "number", "min": 1.0, "max": 3.0, "default": 2.0}
        },
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="low",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="ATR",
        display_name="Average True Range",
        category="volatility",
        description="Measures market volatility by decomposing the entire range of an asset price",
        default_params={"period": 14},
        param_schema={"period": {"type": "integer", "min": 2, "max": 50, "default": 14}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="ADX",
        display_name="Average Directional Index",
        category="trend",
        description="Measures trend strength regardless of direction",
        default_params={"period": 14},
        param_schema={"period": {"type": "integer", "min": 2, "max": 50, "default": 14}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="VWAP",
        display_name="Volume Weighted Average Price",
        category="volume",
        description="Average price weighted by volume, typically reset daily",
        default_params={"reset_period": "daily"},
        param_schema={"reset_period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h"],
        repainting_risk="low",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="OBV",
        display_name="On-Balance Volume",
        category="volume",
        description="Cumulative volume indicator relating volume to price change",
        default_params={},
        param_schema={},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
    IndicatorInfo(
        name="MFI",
        display_name="Money Flow Index",
        category="volume",
        description="Volume-weighted RSI - volume-weighted momentum indicator",
        default_params={"period": 14},
        param_schema={"period": {"type": "integer", "min": 2, "max": 50, "default": 14}},
        supports_timeframes=["1m", "3m", "5m", "15m", "1h", "4h", "1d"],
        repainting_risk="none",
        lookahead_risk=False
    ),
]


# Routes
@router.get("", response_model=List[StrategyResponse])
async def get_strategies(
    active_only: bool = Query(False),
    include_performance: bool = Query(False)
):
    """Get all strategies"""
    strategies = MOCK_STRATEGIES
    if active_only:
        strategies = [s for s in strategies if s["is_active"]]
    return [StrategyResponse(**s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Get strategy by ID"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyResponse(**strategy)


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(strategy: StrategyCreate):
    """Create new strategy"""
    new_id = max(s["id"] for s in MOCK_STRATEGIES) + 1
    new_strategy = {
        "id": new_id,
        **strategy.dict(),
        "created_by": "user",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "signal_count_24h": 0,
        "win_rate_30d": 0.0,
        "profit_factor_30d": 0.0,
        "expectancy_30d": 0.0
    }
    MOCK_STRATEGIES.append(new_strategy)
    return StrategyResponse(**new_strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(strategy_id: int, update: StrategyUpdate):
    """Update strategy"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    update_data = update.dict(exclude_unset=True)
    strategy.update(update_data)
    strategy["updated_at"] = datetime.utcnow()

    return StrategyResponse(**strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int):
    """Delete strategy (soft delete - mark inactive)"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy["is_active"] = False
    strategy["updated_at"] = datetime.utcnow()

    return {"success": True, "message": "Strategy deactivated"}


@router.post("/{strategy_id}/clone", response_model=StrategyResponse)
async def clone_strategy(strategy_id: int, new_name: str):
    """Clone strategy with new name"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    new_id = max(s["id"] for s in MOCK_STRATEGIES) + 1
    new_strategy = {
        "id": new_id,
        "name": new_name,
        "description": strategy["description"],
        "version": "1.0.0",
        "is_active": False,
        "direction": strategy["direction"],
        "weight": strategy["weight"],
        "risk_multiplier": strategy["risk_multiplier"],
        "timeframes": strategy["timeframes"],
        "symbols": strategy["symbols"],
        "min_signal_score": strategy["min_signal_score"],
        "created_by": "user",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "signal_count_24h": 0,
        "win_rate_30d": 0.0,
        "profit_factor_30d": 0.0,
        "expectancy_30d": 0.0
    }
    MOCK_STRATEGIES.append(new_strategy)
    return StrategyResponse(**new_strategy)


@router.get("/{strategy_id}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(
    strategy_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """Get strategy performance metrics"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Mock performance data
    return StrategyPerformance(
        strategy_id=strategy_id,
        strategy_name=strategy["name"],
        version=strategy["version"],
        period_days=days,
        total_signals=150,
        executed_signals=87,
        win_rate=58.5,
        loss_rate=41.5,
        profit_factor=1.45,
        expectancy=0.32,
        avg_win=1.25,
        avg_loss=-0.85,
        avg_r_multiple=0.42,
        max_drawdown=8.5,
        sharpe_ratio=1.2,
        sortino_ratio=1.8,
        by_symbol={
            "BTCUSDT": {"signals": 45, "win_rate": 60.0, "profit_factor": 1.5},
            "ETHUSDT": {"signals": 38, "win_rate": 58.0, "profit_factor": 1.4},
            "SOLUSDT": {"signals": 22, "win_rate": 55.0, "profit_factor": 1.3},
        },
        by_timeframe={
            "15m": {"signals": 60, "win_rate": 55.0, "profit_factor": 1.3},
            "1h": {"signals": 70, "win_rate": 60.0, "profit_factor": 1.5},
            "4h": {"signals": 20, "win_rate": 65.0, "profit_factor": 1.6},
        },
        by_direction={
            "LONG": {"signals": 95, "win_rate": 60.0, "profit_factor": 1.5},
            "SHORT": {"signals": 55, "win_rate": 55.0, "profit_factor": 1.3},
        },
        by_regime={
            "trending": {"signals": 80, "win_rate": 65.0, "profit_factor": 1.7},
            "ranging": {"signals": 50, "win_rate": 50.0, "profit_factor": 1.1},
            "volatile": {"signals": 20, "win_rate": 45.0, "profit_factor": 1.0},
        },
        equity_curve=[
            {"date": "2026-10-27", "equity": 100.0},
            {"date": "2026-10-28", "equity": 101.2},
            {"date": "2026-10-29", "equity": 100.8},
            {"date": "2026-10-30", "equity": 102.5},
            {"date": "2026-10-31", "equity": 103.1},
        ]
    )


@router.get("/{strategy_id}/versions", response_model=List[StrategyVersion])
async def get_strategy_versions(strategy_id: int):
    """Get strategy version history"""
    return [
        StrategyVersion(
            version="1.2.0",
            description="Added volume filter to entry rules",
            created_at=datetime(2026, 11, 20),
            is_current=True
        ),
        StrategyVersion(
            version="1.1.0",
            description="Adjusted RSI threshold from 30 to 35",
            created_at=datetime(2026, 10, 15),
            is_current=False
        ),
        StrategyVersion(
            version="1.0.0",
            description="Initial version",
            created_at=datetime(2026, 1, 15),
            is_current=False
        ),
    ]


@router.post("/{strategy_id}/versions", response_model=StrategyVersion)
async def create_strategy_version(
    strategy_id: int,
    version: str,
    description: str
):
    """Create new strategy version"""
    return StrategyVersion(
        version=version,
        description=description,
        created_at=datetime.utcnow(),
        is_current=True
    )


@router.get("/indicators/list", response_model=List[IndicatorInfo])
async def get_indicators(
    category: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """Get available indicators for strategy builder"""
    indicators = MOCK_INDICATORS

    if category:
        indicators = [i for i in indicators if i.category == category]
    if timeframe:
        indicators = [i for i in indicators if timeframe in i.supports_timeframes]

    return indicators


@router.get("/indicators/{indicator_name}", response_model=IndicatorInfo)
async def get_indicator(indicator_name: str):
    """Get indicator details"""
    indicator = next((i for i in MOCK_INDICATORS if i.name.lower() == indicator_name.lower()), None)
    if not indicator:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return indicator


def _check_rule(rule: RuleCondition) -> dict:
    """Validate a rule condition (sync logic, reusable from anywhere)"""
    errors = []
    warnings = []

    # Check indicator exists
    if rule.indicator:
        indicator = next((i for i in MOCK_INDICATORS if i.name.lower() == rule.indicator.name.lower()), None)
        if not indicator:
            errors.append(f"Unknown indicator: {rule.indicator.name}")

    if rule.indicator_a:
        indicator = next((i for i in MOCK_INDICATORS if i.name.lower() == rule.indicator_a.name.lower()), None)
        if not indicator:
            errors.append(f"Unknown indicator A: {rule.indicator_a.name}")

    if rule.indicator_b:
        indicator = next((i for i in MOCK_INDICATORS if i.name.lower() == rule.indicator_b.name.lower()), None)
        if not indicator:
            errors.append(f"Unknown indicator B: {rule.indicator_b.name}")

    # Check repainting risk
    if rule.indicator:
        ind = next((i for i in MOCK_INDICATORS if i.name.lower() == rule.indicator.name.lower()), None)
        if ind and ind.repainting_risk != "none":
            warnings.append(f"Indicator {ind.name} has {ind.repainting_risk} repainting risk")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@router.post("/validate-rule")
async def validate_rule(rule: RuleCondition):
    """Validate a rule condition"""
    return _check_rule(rule)


@router.post("/validate-strategy")
async def validate_strategy(rule_set: StrategyRuleSet):
    """Validate complete strategy rule set"""
    all_errors = []
    all_warnings = []

    def validate_group(group: RuleGroup, prefix: str):
        for i, condition in enumerate(group.conditions):
            result = _check_rule(condition)
            if not result["valid"]:
                all_errors.extend([f"{prefix}.conditions[{i}]: {e}" for e in result["errors"]])
            all_warnings.extend([f"{prefix}.conditions[{i}]: {w}" for w in result["warnings"]])

        for i, sub_group in enumerate(group.groups):
            validate_group(sub_group, f"{prefix}.groups[{i}]")

    validate_group(rule_set.entry_rules, "entry_rules")
    validate_group(rule_set.exit_rules, "exit_rules")

    if rule_set.long_rules:
        validate_group(rule_set.long_rules, "long_rules")
    if rule_set.short_rules:
        validate_group(rule_set.short_rules, "short_rules")

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings
    }


@router.post("/backtest")
async def run_backtest(
    strategy_id: int,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    timeframes: List[str] = ["15m", "1h"],
    initial_capital: float = 100.0
):
    """Run backtest for strategy"""
    return {
        "backtest_id": f"bt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "status": "started",
        "message": "Backtest queued for execution",
        "estimated_duration_seconds": 60
    }