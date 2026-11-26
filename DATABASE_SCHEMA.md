# QUANTUM TRADER V1 - Database Schema Documentation

## Overview

This document describes the complete database schema for QUANTUM TRADER V1. The database uses PostgreSQL with JSONB columns for flexible configuration storage.

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Exchange   │───────│   Symbol    │───────│MarketCandle │
└─────────────┘       └─────────────┘       └─────────────┘
       │                     │                     │
       │                     ▼                     │
       │              ┌─────────────┐              │
       │              │   Signal    │◄─────────────┘
       │              └─────────────┘
       │                     │
       │                     ▼
       │              ┌─────────────┐       ┌─────────────┐
       └──────────────│  Position   │───────│    Order    │
                      └─────────────┘       └─────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
             ┌─────────────┐    ┌─────────────┐
             │ TP_SL_Stage │    │  PnL_Entry  │
             └─────────────┘    └─────────────┘

Other tables: Strategy, StrategyRule, Configuration, AuditLog, 
SystemEvent, TelegramUser, ExchangeCredential
```

## Table Definitions

### 1. exchanges
**Purpose**: Exchange configuration and metadata

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| name | VARCHAR(50) | UNIQUE, NOT NULL | Exchange name (binance, bitget) |
| base_url | VARCHAR(255) | NOT NULL | API base URL |
| api_version | VARCHAR(20) | | API version |
| is_active | BOOLEAN | DEFAULT true | Whether exchange is enabled |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

### 2. exchange_credentials
**Purpose**: Encrypted API credentials for exchanges

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| exchange_id | INTEGER | FK → exchanges.id, NOT NULL | Exchange reference |
| api_key | VARCHAR(255) | NOT NULL | Encrypted API key |
| api_secret | VARCHAR(255) | NOT NULL | Encrypted API secret |
| passphrase | VARCHAR(255) | | Encrypted passphrase (Bitget) |
| permissions | VARCHAR(50) | DEFAULT 'read' | read, trade, withdraw |
| ip_whitelist | JSONB | | Allowed IP addresses |
| is_enabled | BOOLEAN | DEFAULT true | Credential status |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| last_used | TIMESTAMPTZ | | Last usage timestamp |

### 3. symbols
**Purpose**: Trading symbol specifications per exchange

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| exchange_id | INTEGER | FK → exchanges.id, NOT NULL | Exchange reference |
| symbol | VARCHAR(50) | NOT NULL | Trading symbol (e.g., BTCUSDT) |
| base_asset | VARCHAR(20) | NOT NULL | Base asset (e.g., BTC) |
| quote_asset | VARCHAR(20) | NOT NULL | Quote asset (e.g., USDT) |
| contract_size | DECIMAL(18,8) | | Contract size for futures |
| tick_size | DECIMAL(18,8) | | Minimum price increment |
| lot_size | DECIMAL(18,8) | | Minimum quantity |
| min_notional | DECIMAL(18,8) | | Minimum order value |
| max_leverage | INTEGER | | Maximum leverage |
| maintenance_margin_rate | DECIMAL(5,4) | | Maintenance margin rate |
| is_active | BOOLEAN | DEFAULT true | Symbol active status |
| is_eligible | BOOLEAN | DEFAULT true | Eligible for scanning |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

**Indexes**:
- UNIQUE(exchange_id, symbol)

### 4. market_candles
**Purpose**: OHLCV candle data storage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PRIMARY KEY | Unique identifier |
| symbol_id | INTEGER | FK → symbols.id, NOT NULL | Symbol reference |
| timeframe | VARCHAR(10) | NOT NULL | Timeframe (3m, 5m, 15m, 1h, 4h, 1d) |
| open_time | TIMESTAMPTZ | NOT NULL | Candle open timestamp |
| open | DECIMAL(18,8) | NOT NULL | Open price |
| high | DECIMAL(18,8) | NOT NULL | High price |
| low | DECIMAL(18,8) | NOT NULL | Low price |
| close | DECIMAL(18,8) | NOT NULL | Close price |
| volume | DECIMAL(18,8) | NOT NULL | Base asset volume |
| quote_volume | DECIMAL(18,8) | | Quote asset volume |
| trades | INTEGER | | Number of trades |
| is_closed | BOOLEAN | DEFAULT false | Whether candle is closed |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |

**Indexes**:
- UNIQUE(symbol_id, timeframe, open_time)
- INDEX(symbol_id, timeframe, open_time DESC)
- INDEX(is_closed) WHERE is_closed = false

**Partitioning**: By timeframe (recommended for production)

### 5. strategies
**Purpose**: Trading strategy definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| name | VARCHAR(100) | NOT NULL | Strategy name |
| description | TEXT | | Strategy description |
| version | VARCHAR(20) | NOT NULL | Version string |
| is_active | BOOLEAN | DEFAULT true | Strategy status |
| created_by | VARCHAR(100) | | Creator identifier |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

### 6. strategy_rules
**Purpose**: Individual rules within a strategy

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| strategy_id | INTEGER | FK → strategies.id, NOT NULL | Strategy reference |
| rule_type | VARCHAR(50) | NOT NULL | Rule type identifier |
| rule_config | JSONB | NOT NULL | Rule configuration |
| weight | DECIMAL(5,2) | | Rule weight in scoring |
| is_active | BOOLEAN | DEFAULT true | Rule status |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |

### 7. signals
**Purpose**: Generated trading signals

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| symbol_id | INTEGER | FK → symbols.id, NOT NULL | Symbol reference |
| strategy_id | INTEGER | FK → strategies.id, NOT NULL | Strategy reference |
| direction | ENUM | NOT NULL | LONG or SHORT |
| signal_score | DECIMAL(5,2) | | Signal quality score (0-100) |
| market_regime | ENUM | | Market regime at signal time |
| entry_price | DECIMAL(18,8) | | Suggested entry price |
| stop_loss | DECIMAL(18,8) | | Initial stop loss |
| tp1 | DECIMAL(18,8) | | Take profit 1 |
| tp2 | DECIMAL(18,8) | | Take profit 2 |
| tp3 | DECIMAL(18,8) | | Take profit 3 |
| runner_quantity | DECIMAL(18,8) | | Runner position size |
| status | ENUM | DEFAULT 'candidate' | Signal lifecycle status |
| created_at | TIMESTAMPTZ | DEFAULT now() | Signal generation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |
| expires_at | TIMESTAMPTZ | | Signal expiration time |

**Signal Statuses**: candidate, qualified, active, triggered, expired, invalidated, rejected, executed

### 8. positions
**Purpose**: Open and closed trading positions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| signal_id | INTEGER | FK → signals.id | Originating signal |
| exchange_id | INTEGER | FK → exchanges.id, NOT NULL | Exchange reference |
| symbol_id | INTEGER | FK → symbols.id, NOT NULL | Symbol reference |
| direction | ENUM | NOT NULL | LONG or SHORT |
| entry_price | DECIMAL(18,8) | | Average entry price |
| quantity | DECIMAL(18,8) | | Position size |
| notional_value | DECIMAL(18,8) | | Position notional |
| margin_used | DECIMAL(18,8) | | Margin allocated |
| leverage_used | DECIMAL(5,2) | | Leverage used |
| status | ENUM | DEFAULT 'open' | Position status |
| pnl | DECIMAL(18,8) | DEFAULT 0 | Unrealized PnL |
| realized_pnl | DECIMAL(18,8) | DEFAULT 0 | Realized PnL |
| open_time | TIMESTAMPTZ | | Position open time |
| close_time | TIMESTAMPTZ | | Position close time |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

**Position Statuses**: open, closed, liquidated, force_closed

### 9. orders
**Purpose**: Order execution records

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| position_id | INTEGER | FK → positions.id | Associated position |
| exchange_id | INTEGER | FK → exchanges.id, NOT NULL | Exchange reference |
| symbol_id | INTEGER | FK → symbols.id, NOT NULL | Symbol reference |
| exchange_order_id | VARCHAR(100) | | Exchange order ID |
| order_type | ENUM | NOT NULL | market, limit, stop_market, stop_limit |
| side | VARCHAR(10) | NOT NULL | BUY or SELL |
| quantity | DECIMAL(18,8) | | Order quantity |
| price | DECIMAL(18,8) | | Limit price |
| stop_price | DECIMAL(18,8) | | Stop trigger price |
| status | ENUM | DEFAULT 'pending' | Order status |
| filled_quantity | DECIMAL(18,8) | DEFAULT 0 | Filled quantity |
| average_fill_price | DECIMAL(18,8) | | Average fill price |
| fees | DECIMAL(18,8) | DEFAULT 0 | Fees paid |
| created_at | TIMESTAMPTZ | DEFAULT now() | Order creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |
| filled_at | TIMESTAMPTZ | | Fill timestamp |

**Order Statuses**: pending, partially_filled, filled, cancelled, rejected, expired

### 10. tp_sl_stages
**Purpose**: TP/SL stage tracking per position

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| position_id | INTEGER | FK → positions.id, NOT NULL | Position reference |
| stage_type | ENUM | NOT NULL | TP or SL |
| stage_number | INTEGER | NOT NULL | 0=initial SL, 1-3=TP, 4=runner |
| target_price | DECIMAL(18,8) | | Target trigger price |
| quantity | DECIMAL(18,8) | | Quantity for this stage |
| status | ENUM | DEFAULT 'pending' | Stage status |
| triggered_at | TIMESTAMPTZ | | Trigger timestamp |
| filled_at | TIMESTAMPTZ | | Fill timestamp |
| exchange_order_id | VARCHAR(100) | | Exchange order ID |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

**Stage Statuses**: pending, triggered, filled, cancelled, failed

### 11. pnl_entries
**Purpose**: Detailed PnL ledger

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| position_id | INTEGER | FK → positions.id, NOT NULL | Position reference |
| trade_id | INTEGER | | Trade group identifier |
| pnl_type | VARCHAR(20) | NOT NULL | realized, unrealized, fee, funding |
| amount | DECIMAL(18,8) | NOT NULL | PnL amount |
| running_balance | DECIMAL(18,8) | NOT NULL | Running equity balance |
| description | TEXT | | Description |
| created_at | TIMESTAMPTZ | DEFAULT now() | Entry timestamp |

### 12. configurations
**Purpose**: Application configuration with versioning

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| config_key | VARCHAR(100) | UNIQUE, NOT NULL | Configuration key |
| config_value | JSONB | NOT NULL | Configuration value |
| version | INTEGER | DEFAULT 1 | Configuration version |
| description | TEXT | | Description |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Last update time |

### 13. audit_logs
**Purpose**: Security and operational audit trail

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PRIMARY KEY | Unique identifier |
| user_id | VARCHAR(100) | | User identifier |
| action | VARCHAR(100) | NOT NULL | Action performed |
| resource_type | VARCHAR(50) | | Resource type |
| resource_id | VARCHAR(100) | | Resource identifier |
| old_values | JSONB | | Previous values |
| new_values | JSONB | | New values |
| ip_address | INET | | Client IP |
| user_agent | TEXT | | Client user agent |
| success | BOOLEAN | DEFAULT true | Whether action succeeded |
| error_message | TEXT | | Error if failed |
| created_at | TIMESTAMPTZ | DEFAULT now() | Event timestamp |

**Indexes**:
- INDEX(user_id, created_at)
- INDEX(resource_type, resource_id)
- INDEX(created_at)

### 14. system_events
**Purpose**: System health and operational events

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_type | VARCHAR(50) | NOT NULL | Event category |
| severity | VARCHAR(20) | NOT NULL | INFO, WARNING, ERROR, CRITICAL |
| message | TEXT | NOT NULL | Event description |
| details | JSONB | | Additional details |
| is_resolved | BOOLEAN | DEFAULT false | Resolution status |
| resolved_at | TIMESTAMPTZ | | Resolution timestamp |
| created_at | TIMESTAMPTZ | DEFAULT now() | Event timestamp |

**Indexes**:
- INDEX(event_type, severity)
- INDEX(is_resolved)
- INDEX(created_at)

### 15. telegram_users
**Purpose**: Authorized Telegram users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | BIGINT | UNIQUE, NOT NULL | Telegram user ID |
| username | VARCHAR(100) | | Telegram username |
| is_admin | BOOLEAN | DEFAULT false | Admin privileges |
| is_active | BOOLEAN | DEFAULT true | User status |
| created_at | TIMESTAMPTZ | DEFAULT now() | Authorization time |

## JSONB Schema Examples

### signal_config (strategy_rules.rule_config)
```json
{
  "indicator": "RSI",
  "timeframe": "15m",
  "condition": "below",
  "threshold": 30,
  "lookback": 14
}
```

### tp_sl_config (configurations.config_value)
```json
{
  "allocation": {
    "tp1": 0.4,
    "tp2": 0.3,
    "tp3": 0.2,
    "runner": 0.1
  },
  "trailing": {
    "atr_multiplier": 2.0,
    "min_distance_pct": 0.1
  }
}
```

### exchange_symbol_info (symbols - stored as columns, not JSON)
```json
{
  "binance": {
    "BTCUSDT": {
      "tickSize": "0.01",
      "stepSize": "0.001",
      "minNotional": "5.0",
      "maxLeverage": 125,
      "maintenanceMarginRate": "0.005"
    }
  }
}
```

## Migration Strategy

### Version 1.0 (Initial)
- All tables created with base schema
- Default exchanges inserted
- Default strategies inserted
- Default configurations inserted

### Future Migrations
- Add partitioning to market_candles
- Add materialized views for analytics
- Add strategy versioning table
- Add backtest results tables

## Performance Considerations

### Indexing Strategy
- Primary keys on all tables
- Foreign key indexes on all FK columns
- Composite indexes for common query patterns
- Partial indexes for status columns
- BRIN indexes for time-series tables (market_candles)

### Partitioning
```sql
-- Recommended partitioning for market_candles
CREATE TABLE market_candles_3m PARTITION OF market_candles
FOR VALUES IN ('3m');

CREATE TABLE market_candles_1h PARTITION OF market_candles
FOR VALUES IN ('1h');
```

### Retention Policies
- market_candles: 90 days (configurable)
- audit_logs: 365 days
- system_events: 180 days
- pnl_entries: 365 days

## Backup and Recovery

### Backup Strategy
- Daily full backup (pg_dump)
- Hourly WAL archiving
- Point-in-time recovery capability
- Backup encryption for credentials

### Recovery Procedures
1. Restore latest full backup
2. Apply WAL files to target timestamp
3. Verify data integrity
4. Restart services

## Security

### Column-Level Encryption
- exchange_credentials.api_key
- exchange_credentials.api_secret
- exchange_credentials.passphrase
- Use pgcrypto or application-level encryption

### Row-Level Security
```sql
-- Example: Users only see their own audit logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_audit_policy ON audit_logs
USING (user_id = current_setting('app.current_user_id'));
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Tables | snake_case, plural | market_candles |
| Columns | snake_case | open_time |
| Primary Keys | id | id |
| Foreign Keys | {table}_id | symbol_id |
| Indexes | idx_{table}_{columns} | idx_symbols_exchange_symbol |
| Enums | UPPER_SNAKE_CASE | SIGNAL_STATUS |
| JSON Keys | camelCase | signalScore |

## Data Types Reference

| Type | Use Case | Precision |
|------|----------|-----------|
| DECIMAL(18,8) | Prices, quantities, PnL | 18 digits, 8 decimals |
| DECIMAL(5,2) | Percentages, leverage | 5 digits, 2 decimals |
| DECIMAL(5,4) | Rates, margins | 5 digits, 4 decimals |
| TIMESTAMPTZ | All timestamps | Microsecond precision |
| JSONB | Flexible config | Binary JSON |
| ENUM | Fixed value sets | Status, types |
| BIGSERIAL | High-volume IDs | 64-bit auto-increment |