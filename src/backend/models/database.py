"""
Database Models for QUANTUM TRADER V1
SQLAlchemy ORM models for all persistent data
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, JSON, Text,
    ForeignKey, CheckConstraint, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class SignalStatus(str, enum.Enum):
    """Signal lifecycle states"""
    CANDIDATE = "candidate"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    REJECTED = "rejected"
    EXECUTED = "executed"


class SignalDirection(str, enum.Enum):
    """Signal direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, enum.Enum):
    """Position status"""
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"
    FORCE_CLOSED = "force_closed"


class OrderStatus(str, enum.Enum):
    """Order status"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, enum.Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class TPStageStatus(str, enum.Enum):
    """TP/SL stage status"""
    PENDING = "pending"
    TRIGGERED = "triggered"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Exchange(str, enum.Enum):
    """Supported exchanges"""
    BINANCE = "binance"
    BITGET = "bitget"


class MarketRegime(str, enum.Enum):
    """Market regime types"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    SIDECAR = "sideways"


class Exchange(Base):
    """Exchange configuration"""

    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    base_url = Column(String(255), nullable=False)
    api_version = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    symbols = relationship("Symbol", back_populates="exchange", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="exchange")
    credentials = relationship("ExchangeCredential", back_populates="exchange", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exchange(name={self.name!r}, active={self.is_active})>"


class ExchangeCredential(Base):
    """Encrypted exchange credentials"""

    __tablename__ = "exchange_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)
    passphrase = Column(String(255), nullable=True)
    permissions = Column(String(50), default="read")
    ip_whitelist = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)

    exchange = relationship("Exchange", back_populates="credentials")

    def __repr__(self):
        return f"<ExchangeCredential(exchange_id={self.exchange_id}, enabled={self.is_enabled})>"


class Symbol(Base):
    """Trading symbol configuration"""

    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    symbol = Column(String(50), nullable=False)
    base_asset = Column(String(20), nullable=False)
    quote_asset = Column(String(20), nullable=False)
    contract_size = Column(Float, nullable=True)
    tick_size = Column(Float, nullable=True)
    lot_size = Column(Float, nullable=True)
    min_notional = Column(Float, nullable=True)
    max_leverage = Column(Integer, nullable=True)
    maintenance_margin_rate = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    is_eligible = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    exchange = relationship("Exchange", back_populates="symbols")
    market_candles = relationship("MarketCandle", back_populates="symbol", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="symbol")
    positions = relationship("Position", back_populates="symbol")
    orders = relationship("Order", back_populates="symbol")

    def __repr__(self):
        return f"<Symbol(symbol={self.symbol!r}, exchange_id={self.exchange_id})>"


class MarketCandle(Base):
    """Market candle data"""

    __tablename__ = "market_candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    timeframe = Column(String(10), nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quote_volume = Column(Float, nullable=True)
    trades = Column(Integer, nullable=True)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    symbol = relationship("Symbol", back_populates="market_candles")

    def __repr__(self):
        return f"<MarketCandle(symbol_id={self.symbol_id}, timeframe={self.timeframe!r}, open_time={self.open_time})>"


class Strategy(Base):
    """Trading strategy configuration"""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rules = relationship("StrategyRule", back_populates="strategy", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="strategy")

    def __repr__(self):
        return f"<Strategy(name={self.name!r}, version={self.version!r})>"


class StrategyRule(Base):
    """Strategy rule configuration"""

    __tablename__ = "strategy_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_config = Column(JSON, nullable=False)
    weight = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    strategy = relationship("Strategy", back_populates="rules")

    def __repr__(self):
        return f"<StrategyRule(strategy_id={self.strategy_id}, type={self.rule_type!r})>"


class Signal(Base):
    """Trading signal"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    direction = Column(SQLEnum(SignalDirection), nullable=False)
    signal_score = Column(Float, nullable=True)
    market_regime = Column(SQLEnum(MarketRegime), nullable=True)
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    tp1 = Column(Float, nullable=True)
    tp2 = Column(Float, nullable=True)
    tp3 = Column(Float, nullable=True)
    runner_quantity = Column(Float, nullable=True)
    status = Column(SQLEnum(SignalStatus), default=SignalStatus.CANDIDATE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    symbol = relationship("Symbol", back_populates="signals")
    strategy = relationship("Strategy", back_populates="signals")
    positions = relationship("Position", back_populates="signal")

    def __repr__(self):
        return f"<Signal(id={self.id}, symbol_id={self.symbol_id}, direction={self.direction!r})>"


class Position(Base):
    """Trading position"""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    direction = Column(SQLEnum(SignalDirection), nullable=False)
    entry_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    notional_value = Column(Float, nullable=True)
    margin_used = Column(Float, nullable=True)
    leverage_used = Column(Float, nullable=True)
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN)
    pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    open_time = Column(DateTime(timezone=True), nullable=True)
    close_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    exchange = relationship("Exchange", back_populates="positions")
    symbol = relationship("Symbol", back_populates="positions")
    signal = relationship("Signal", back_populates="positions")
    orders = relationship("Order", back_populates="position", cascade="all, delete-orphan")
    tp_sl_stages = relationship("TP_SL_Stage", back_populates="position", cascade="all, delete-orphan")
    pnl_entries = relationship("PnL_Entry", back_populates="position", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Position(id={self.id}, symbol_id={self.symbol_id}, direction={self.direction!r})>"


class Order(Base):
    """Order record"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    exchange_id = Column(Integer, ForeignKey("exchanges.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    exchange_order_id = Column(String(100), nullable=True)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True), nullable=True)

    exchange = relationship("Exchange")
    symbol = relationship("Symbol", back_populates="orders")
    position = relationship("Position", back_populates="orders")

    def __repr__(self):
        return f"<Order(id={self.id}, symbol_id={self.symbol_id}, type={self.order_type!r})>"


class TP_SL_Stage(Base):
    """TP/SL stage management"""

    __tablename__ = "tp_sl_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    stage_type = Column(SQLEnum(TPStageStatus), nullable=False)
    stage_number = Column(Integer, nullable=False)
    target_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    status = Column(SQLEnum(TPStageStatus), default=TPStageStatus.PENDING)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    exchange_order_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    position = relationship("Position", back_populates="tp_sl_stages")

    def __repr__(self):
        return f"<TP_SL_Stage(position_id={self.position_id}, type={self.stage_type!r}, number={self.stage_number})>"


class PnL_Entry(Base):
    """PnL ledger entry"""

    __tablename__ = "pnl_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    trade_id = Column(Integer, nullable=True)
    pnl_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    running_balance = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    position = relationship("Position", back_populates="pnl_entries")

    def __repr__(self):
        return f"<PnL_Entry(position_id={self.position_id}, type={self.pnl_type!r}, amount={self.amount})>"


class Configuration(Base):
    """Application configuration"""

    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    version = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Configuration(key={self.config_key!r}, value={self.config_value!r})>"


class AuditLog(Base):
    """Audit trail for all operations"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(action={self.action!r}, user_id={self.user_id!r})>"


class SystemEvent(Base):
    """System health and event tracking"""

    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SystemEvent(type={self.event_type!r}, severity={self.severity!r})>"


class TelegramUser(Base):
    """Telegram user authorization"""

    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TelegramUser(user_id={self.user_id}, username={self.username!r})>"
