"""
Configuration Management for QUANTUM TRADER V1
Handles application configuration with environment variable support
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Basic application settings
    app_name: str = "QUANTUM TRADER V1"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    # SSL settings
    ssl_enabled: bool = False
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None

    # Database settings
    # Use SQLite by default for portable Windows deployment
    database_url: str = "sqlite:///data/database/quantum.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Security settings
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Exchange API settings
    exchange_timeout: int = 10000  # milliseconds
    exchange_rate_limit: int = 100  # requests per minute
    exchange_retries: int = 3
    exchange_retry_delay: int = 1  # seconds

    # Trading settings
    initial_equity: float = 100.0  # USDT
    risk_per_trade: float = 0.005  # 0.5%
    max_simultaneous_positions: int = 2
    max_leverage: int = 3
    daily_loss_limit: float = 0.015  # 1.5%
    drawdown_warning: float = 0.05  # 5%
    emergency_drawdown: float = 0.08  # 8%

    # Paper trading settings
    paper_trading: bool = True
    paper_fees: float = 0.001  # 0.1%
    paper_slippage: float = 0.0005  # 0.05%
    paper_funding_rate: float = 0.0001  # 0.01%

    # Market data settings
    market_data_interval: int = 60  # seconds
    historical_data_limit: int = 1000  # candles
    supported_timeframes: List[str] = ["3m", "5m", "15m", "1h", "4h", "1d"]

    # Strategy settings
    strategy_scan_interval: int = 300  # seconds (5 minutes)
    max_signals_per_day: int = 10
    signal_min_score: float = 0.7

    # TP/SL settings
    tp_allocation: Dict[str, float] = {
        "tp1": 0.4,
        "tp2": 0.3,
        "tp3": 0.2,
        "runner": 0.1
    }
    trailing_atr_multiplier: float = 2.0
    min_trailing_distance: float = 0.001  # 0.1%

    # Telegram settings
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_allowed_users: List[int] = []
    telegram_commands_interval: int = 60  # seconds

    # Notification settings
    notification_enabled: bool = True
    notification_email: Optional[str] = None
    notification_webhook_url: Optional[str] = None

    # Data retention settings
    log_retention_days: int = 30
    trade_retention_days: int = 365
    market_data_retention_days: int = 90

    # Backup settings
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_count: int = 7

    # Performance monitoring
    performance_metrics_enabled: bool = True
    metrics_interval_seconds: int = 60

    # Development settings
    mock_exchange: bool = True
    mock_data_delay: int = 1000  # milliseconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def project_root(self) -> Path:
        """Get the project root directory"""
        return Path(__file__).parent.parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Get the data directory"""
        return self.project_root / "data"

    @property
    def log_dir(self) -> Path:
        """Get the logs directory"""
        return self.data_dir / "logs"

    @property
    def backup_dir(self) -> Path:
        """Get the backup directory"""
        return self.data_dir / "backups"

    @property
    def database_dir(self) -> Path:
        """Get the database directory"""
        return self.data_dir / "database"

    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.data_dir,
            self.log_dir,
            self.backup_dir,
            self.database_dir,
            self.data_dir / "market_data",
            self.data_dir / "temp"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self):
        """Validate configuration values"""
        errors = []

        if self.risk_per_trade <= 0 or self.risk_per_trade > 0.1:
            errors.append("risk_per_trade must be between 0 and 0.1")

        if self.max_leverage < 1 or self.max_leverage > 100:
            errors.append("max_leverage must be between 1 and 100")

        if self.daily_loss_limit <= 0 or self.daily_loss_limit > 0.1:
            errors.append("daily_loss_limit must be between 0 and 0.1")

        if self.drawdown_warning <= 0 or self.drawdown_warning > 0.5:
            errors.append("drawdown_warning must be between 0 and 0.5")

        if self.emergency_drawdown <= self.drawdown_warning:
            errors.append("emergency_drawdown must be greater than drawdown_warning")

        if sum(self.tp_allocation.values()) != 1.0:
            errors.append("TP allocation percentages must sum to 1.0")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")


class Config:
    """Singleton configuration manager"""
    _instance = None
    _settings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._settings is None:
            self._settings = Settings()
            self._settings.ensure_directories()
            self._settings.validate()

    @property
    def settings(self) -> Settings:
        return self._settings

    def reload(self):
        """Reload configuration from environment"""
        self._settings = Settings()
        self._settings.ensure_directories()
        self._settings.validate()

    def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Get exchange-specific configuration"""
        base_config = {
            "timeout": self.settings.exchange_timeout,
            "rateLimit": self.settings.exchange_rate_limit,
            "retries": self.settings.exchange_retries,
            "retryDelay": self.settings.exchange_retry_delay,
        }

        # Exchange-specific overrides
        if exchange_name.lower() == "binance":
            base_config.update({
                "options": {
                    "defaultType": "future",
                    "adjustForTimeDifference": True,
                }
            })
        elif exchange_name.lower() == "bitget":
            base_config.update({
                "options": {
                    "defaultType": "swap",
                    "adjustForTimeDifference": True,
                }
            })

        return base_config

    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get strategy-specific configuration"""
        return {
            "enabled": True,
            "weight": 1.0,
            "risk_multiplier": 1.0,
            "timeframes": ["15m", "1h"],
            "symbols": [],
        }