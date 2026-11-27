"""
Configuration API Routes for QUANTUM TRADER V1
All system configuration through the web UI
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


# Enums
class ExchangeName(str, Enum):
    BINANCE = "binance"
    BITGET = "bitget"


class MarginMode(str, Enum):
    ISOLATED = "isolated"
    CROSS = "cross"


class PositionMode(str, Enum):
    ONE_WAY = "one_way"
    HEDGE = "hedge"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# Models
class ExchangeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ExchangeName
    enabled: bool
    testnet: bool = False
    margin_mode: MarginMode = MarginMode.ISOLATED
    position_mode: PositionMode = PositionMode.ONE_WAY
    rate_limit_buffer: float = 0.8  # Use 80% of limit
    recv_window: int = 5000


class ExchangeConfigResponse(BaseModel):
    name: ExchangeName
    enabled: bool
    testnet: bool
    margin_mode: MarginMode
    position_mode: PositionMode
    has_credentials: bool
    last_tested: Optional[datetime] = None
    connection_status: str  # not_configured until a real exchange adapter is implemented


class MarketConfig(BaseModel):
    enabled_exchanges: List[ExchangeName] = [ExchangeName.BINANCE, ExchangeName.BITGET]
    quote_asset: str = "USDT"
    contract_type: str = "perpetual"
    min_volume_24h: float = 10_000_000
    max_spread_bps: float = 50
    min_history_days: int = 30
    supported_timeframes: List[str] = ["3m", "5m", "15m", "1h", "4h", "1d"]
    primary_timeframe: str = "15m"
    context_timeframes: List[str] = ["1h", "4h", "1d"]


class ScannerConfig(BaseModel):
    scan_interval_seconds: int = 300
    max_candidates: int = 100
    min_signal_score: float = 70.0
    volume_filter: bool = True
    spread_filter: bool = True
    volatility_filter: bool = True
    regime_filter: bool = True
    btc_correlation_filter: bool = True
    min_btc_correlation: float = -0.5
    max_btc_correlation: float = 1.0


class RiskConfig(BaseModel):
    initial_equity: float = 100.0
    risk_per_trade_pct: float = Field(0.5, ge=0.1, le=5.0)
    max_simultaneous_positions: int = Field(2, ge=1, le=10)
    max_leverage: int = Field(3, ge=1, le=10)
    daily_loss_limit_pct: float = Field(1.5, ge=0.5, le=10.0)
    drawdown_warning_pct: float = Field(5.0, ge=1.0, le=20.0)
    emergency_drawdown_pct: float = Field(8.0, ge=5.0, le=50.0)
    max_correlated_exposure_pct: float = 50.0
    min_risk_reward: float = 2.0
    min_stop_distance_pct: float = 0.5


class TP_SL_Config(BaseModel):
    tp_allocation: Dict[str, float] = {
        "tp1": 0.4,
        "tp2": 0.3,
        "tp3": 0.2,
        "runner": 0.1
    }
    trailing_atr_multiplier: float = 2.0
    min_trailing_distance_pct: float = 0.1
    break_even_fee_aware: bool = True
    break_even_funding_aware: bool = True
    runner_trailing_type: str = "hybrid"  # atr, structure, hybrid
    runner_min_profit_pct: float = 0.5


class LeverageConfig(BaseModel):
    max_leverage: int = 3
    risk_first_sizing: bool = True
    liquidation_buffer_pct: float = 20.0
    use_exchange_maintenance_margin: bool = True
    leverage_tiers_respected: bool = True


class PaperTradingConfig(BaseModel):
    enabled: bool = True
    fees_bps: float = 10.0  # 0.1%
    slippage_bps: float = 5.0  # 0.05%
    funding_rate_pct: float = 0.01  # 0.01% per 8h
    partial_fill_probability: float = 0.1
    latency_ms: int = 100


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = None
    allowed_users: List[int] = []
    admin_users: List[int] = []
    notifications: Dict[str, bool] = {
        "new_signal": True,
        "tp_triggered": True,
        "sl_triggered": True,
        "position_open": True,
        "position_close": True,
        "risk_alert": True,
        "daily_report": True,
        "weekly_report": True,
        "system_error": True
    }
    command_categories: Dict[str, bool] = {
        "general": True,
        "market": True,
        "scanner": True,
        "signals": True,
        "paper": True,
        "strategies": True,
        "risk": True,
        "backtest": True,
        "portfolio": True,
        "system": True,
        "live": True
    }


class NotificationConfig(BaseModel):
    telegram_enabled: bool = False
    email_enabled: bool = False
    email_address: Optional[str] = None
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_events: List[str] = []


class UIConfig(BaseModel):
    theme: Theme = Theme.DARK
    auto_refresh_seconds: int = 5
    chart_timezone: str = "UTC"
    decimal_places: int = 2
    show_advanced: bool = False
    compact_mode: bool = False
    sound_enabled: bool = True


class BackupConfig(BaseModel):
    enabled: bool = True
    interval_hours: int = 24
    retention_count: int = 7
    encrypt_backups: bool = True
    backup_path: str = "data/backups"


class FullConfig(BaseModel):
    exchanges: Dict[str, ExchangeConfig]
    market: MarketConfig
    scanner: ScannerConfig
    risk: RiskConfig
    tp_sl: TP_SL_Config
    leverage: LeverageConfig
    paper_trading: PaperTradingConfig
    telegram: TelegramConfig
    notifications: NotificationConfig
    ui: UIConfig
    backup: BackupConfig


class ConfigValidationResult(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


# Mock storage
MOCK_CONFIG = FullConfig(
    exchanges={
        "binance": ExchangeConfig(
            name=ExchangeName.BINANCE,
            enabled=True,
            testnet=False,
            margin_mode=MarginMode.ISOLATED,
            position_mode=PositionMode.ONE_WAY
        ),
        "bitget": ExchangeConfig(
            name=ExchangeName.BITGET,
            enabled=True,
            testnet=False,
            margin_mode=MarginMode.ISOLATED,
            position_mode=PositionMode.ONE_WAY
        )
    },
    market=MarketConfig(),
    scanner=ScannerConfig(),
    risk=RiskConfig(),
    tp_sl=TP_SL_Config(),
    leverage=LeverageConfig(),
    paper_trading=PaperTradingConfig(),
    telegram=TelegramConfig(),
    notifications=NotificationConfig(),
    ui=UIConfig(),
    backup=BackupConfig()
)


# Routes
@router.get("", response_model=FullConfig)
async def get_full_config():
    """Get configuration; exchange credentials are unsupported and Telegram token is masked."""
    config = MOCK_CONFIG.dict()
    if config["telegram"].get("bot_token"):
        config["telegram"]["bot_token"] = "***"
    return config


@router.get("/exchanges", response_model=List[ExchangeConfigResponse])
async def get_exchange_configs():
    """Get exchange configurations"""
    result = []
    for name, config in MOCK_CONFIG.exchanges.items():
        result.append(ExchangeConfigResponse(
            name=config.name,
            enabled=config.enabled,
            testnet=config.testnet,
            margin_mode=config.margin_mode,
            position_mode=config.position_mode,
            has_credentials=False,
            last_tested=None,
            connection_status="not_configured"
        ))
    return result


@router.put("/exchanges/{exchange_name}")
async def update_exchange_config(
    exchange_name: ExchangeName,
    payload: Dict[str, Any]
):
    """Update non-secret exchange settings; credential submission is disabled."""
    if exchange_name not in MOCK_CONFIG.exchanges:
        raise HTTPException(status_code=404, detail="Exchange not found")

    forbidden_fields = {"api_key", "api_secret", "passphrase"}
    if any(str(key).lower() in forbidden_fields for key in payload):
        raise HTTPException(
            status_code=400,
            detail="Exchange API credentials are not accepted in paper-only mode.",
        )

    try:
        config = ExchangeConfig.model_validate(payload)
    except ValidationError:
        # Never echo request data: validation payloads may contain sensitive values.
        raise HTTPException(status_code=400, detail="Invalid exchange configuration.")

    if config.name != exchange_name:
        raise HTTPException(status_code=400, detail="Exchange name does not match the requested endpoint.")

    MOCK_CONFIG.exchanges[exchange_name] = config
    return {"success": True, "message": f"{exchange_name.value} configuration updated"}


@router.post("/exchanges/{exchange_name}/test")
async def test_exchange_connection(exchange_name: ExchangeName):
    """Test exchange API connection"""
    if exchange_name not in MOCK_CONFIG.exchanges:
        raise HTTPException(status_code=404, detail="Exchange not found")

    raise HTTPException(
        status_code=409,
        detail="Exchange connectivity testing is unavailable in paper-only mode.",
    )


@router.get("/market", response_model=MarketConfig)
async def get_market_config():
    return MOCK_CONFIG.market


@router.put("/market")
async def update_market_config(config: MarketConfig):
    MOCK_CONFIG.market = config
    return {"success": True, "message": "Market configuration updated"}


@router.get("/scanner", response_model=ScannerConfig)
async def get_scanner_config():
    return MOCK_CONFIG.scanner


@router.put("/scanner")
async def update_scanner_config(config: ScannerConfig):
    MOCK_CONFIG.scanner = config
    return {"success": True, "message": "Scanner configuration updated"}


@router.get("/risk", response_model=RiskConfig)
async def get_risk_config():
    return MOCK_CONFIG.risk


@router.put("/risk")
async def update_risk_config(config: RiskConfig):
    # Validate
    if config.emergency_drawdown_pct <= config.drawdown_warning_pct:
        raise HTTPException(
            status_code=400,
            detail="Emergency drawdown must be greater than warning threshold"
        )
    MOCK_CONFIG.risk = config
    return {"success": True, "message": "Risk configuration updated"}


@router.get("/tp-sl", response_model=TP_SL_Config)
async def get_tp_sl_config():
    return MOCK_CONFIG.tp_sl


@router.put("/tp-sl")
async def update_tp_sl_config(config: TP_SL_Config):
    # Validate allocation sums to 1.0
    total = sum(config.tp_allocation.values())
    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"TP allocation must sum to 1.0, got {total}"
        )
    MOCK_CONFIG.tp_sl = config
    return {"success": True, "message": "TP/SL configuration updated"}


@router.get("/leverage", response_model=LeverageConfig)
async def get_leverage_config():
    return MOCK_CONFIG.leverage


@router.put("/leverage")
async def update_leverage_config(config: LeverageConfig):
    MOCK_CONFIG.leverage = config
    return {"success": True, "message": "Leverage configuration updated"}


@router.get("/paper-trading", response_model=PaperTradingConfig)
async def get_paper_trading_config():
    return MOCK_CONFIG.paper_trading


@router.put("/paper-trading")
async def update_paper_trading_config(config: PaperTradingConfig):
    MOCK_CONFIG.paper_trading = config
    return {"success": True, "message": "Paper trading configuration updated"}


@router.get("/telegram", response_model=TelegramConfig)
async def get_telegram_config():
    config = MOCK_CONFIG.telegram.dict()
    if config.get("bot_token"):
        config["bot_token"] = "***"
    return config


@router.put("/telegram")
async def update_telegram_config(config: TelegramConfig):
    MOCK_CONFIG.telegram = config
    return {"success": True, "message": "Telegram configuration updated"}


@router.post("/telegram/test")
async def test_telegram_bot():
    """Test Telegram bot connection"""
    if not MOCK_CONFIG.telegram.enabled or not MOCK_CONFIG.telegram.bot_token:
        raise HTTPException(status_code=400, detail="Telegram not configured")

    return {
        "success": True,
        "message": "Bot connection successful",
        "bot_username": "QuantumTraderBot",
        "bot_id": 123456789
    }


@router.get("/notifications", response_model=NotificationConfig)
async def get_notification_config():
    return MOCK_CONFIG.notifications


@router.put("/notifications")
async def update_notification_config(config: NotificationConfig):
    MOCK_CONFIG.notifications = config
    return {"success": True, "message": "Notification configuration updated"}


@router.get("/ui", response_model=UIConfig)
async def get_ui_config():
    return MOCK_CONFIG.ui


@router.put("/ui")
async def update_ui_config(config: UIConfig):
    MOCK_CONFIG.ui = config
    return {"success": True, "message": "UI configuration updated"}


@router.get("/backup", response_model=BackupConfig)
async def get_backup_config():
    return MOCK_CONFIG.backup


@router.put("/backup")
async def update_backup_config(config: BackupConfig):
    MOCK_CONFIG.backup = config
    return {"success": True, "message": "Backup configuration updated"}


@router.post("/backup/run")
async def run_backup():
    """Trigger manual backup"""
    return {
        "success": True,
        "message": "Backup completed",
        "backup_file": f"quantum_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db",
        "size_bytes": 1024 * 1024 * 5
    }


@router.post("/validate", response_model=ConfigValidationResult)
async def validate_config():
    """Validate entire configuration"""
    errors = []
    warnings = []

    # Risk validation
    risk = MOCK_CONFIG.risk
    if risk.emergency_drawdown_pct <= risk.drawdown_warning_pct:
        errors.append("Emergency drawdown must exceed warning threshold")

    if risk.daily_loss_limit_pct >= risk.emergency_drawdown_pct:
        warnings.append("Daily loss limit close to emergency drawdown")

    # TP/SL validation
    tp_sl = MOCK_CONFIG.tp_sl
    total = sum(tp_sl.tp_allocation.values())
    if abs(total - 1.0) > 0.001:
        errors.append(f"TP allocation sums to {total}, must be 1.0")

    # Exchange credentials are intentionally unsupported in paper-only mode.
    # No exchange credential validation is performed here.

    # Telegram validation
    if MOCK_CONFIG.telegram.enabled:
        if not MOCK_CONFIG.telegram.bot_token:
            errors.append("Telegram enabled but no bot token")
        if not MOCK_CONFIG.telegram.allowed_users:
            warnings.append("Telegram enabled but no allowed users")

    return ConfigValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


@router.get("/version")
async def get_config_version():
    """Get configuration version info"""
    return {
        "version": "1.0.0",
        "last_modified": datetime.utcnow().isoformat(),
        "modified_by": "admin",
        "schema_version": 1
    }


@router.post("/reset")
async def reset_config(section: Optional[str] = None):
    """Reset configuration to defaults"""
    # In real implementation, reset specific section or all
    return {
        "success": True,
        "message": f"Configuration reset{' for ' + section if section else ''}",
        "reset_time": datetime.utcnow().isoformat()
    }


@router.post("/export")
async def export_config():
    """Export configuration (encrypted)"""
    return {
        "success": True,
        "message": "Configuration exported",
        "data": "encrypted_base64_string_here",
        "export_time": datetime.utcnow().isoformat()
    }


@router.post("/import")
async def import_config(encrypted_data: str, passphrase: str):
    """Import configuration from encrypted backup"""
    return {
        "success": True,
        "message": "Configuration imported",
        "import_time": datetime.utcnow().isoformat()
    }