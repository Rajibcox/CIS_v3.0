# QUANTUM TRADER V1 - Architecture Documentation

## System Architecture

### High-Level Overview

QUANTUM TRADER V1 is a microservices-based architecture with the following core components:

1. **Web Dashboard** - React/Vue frontend providing the user interface
2. **Backend API** - FastAPI-based REST and WebSocket services
3. **Market Data Service** - Real-time and historical data management
4. **Strategy Engine** - Strategy execution and signal generation
5. **Risk Engine** - Dynamic leverage and position sizing
6. **Execution Engine** - Order management and trade execution
7. **TP/SL Management** - Advanced profit protection system
8. **PnL Analytics** - Performance tracking and analysis
9. **Telegram Bot** - Command center and notifications
10. **Database Layer** - PostgreSQL for persistent storage

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Overview      │  │   Strategy     │  │   Settings  │ │
│  │   Market Intel  │  │   Builder      │  │   Config    │ │
│  │   Scanner       │  │   Performance  │  │   Security  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Backend API (FastAPI)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Market        │  │   Strategy     │  │   Risk      │ │
│  │   Service       │  │   Service      │  │   Service   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Order         │  │   TP/SL        │  │   PnL       │ │
│  │   Service       │  │   Service      │  │   Service   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   External Systems                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Binance   │  │   Bitget    │  │   Telegram  │       │
│  │   Futures   │  │   Futures   │  │   Bot       │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                   Data Layer                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL Database                   │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │ │
│  │  │ Market  │ │ Signals │ │ Trades  │ │ Config      │  │ │
│  │  │ Data    │ │         │ │         │ │             │  │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Service Architecture

#### 1. Web Dashboard
- **Technology**: React/Vue.js with TypeScript
- **Port**: 80 (HTTP) / 443 (HTTPS)
- **Features**:
  - Real-time dashboard updates via WebSocket
  - Strategy visual builder
  - Configuration management
  - PnL analytics visualization
  - Trade history and position management

#### 2. Backend API
- **Technology**: FastAPI with Python 3.11
- **Port**: 8000
- **Features**:
  - RESTful API for all operations
  - WebSocket for real-time updates
  - Authentication and authorization
  - Request validation and rate limiting
  - Health monitoring endpoints

#### 3. Market Data Service
- **Technology**: Python with asyncio
- **Features**:
  - Real-time candle data streaming
  - Historical data management
  - Market regime detection
  - Volume and volatility analysis
  - Order book snapshots

#### 4. Strategy Engine
- **Technology**: Python with asyncio
- **Features**:
  - Strategy execution framework
  - Signal generation and scoring
  - Multi-timeframe analysis
  - Strategy versioning
  - Performance tracking

#### 5. Risk Engine
- **Technology**: Python with asyncio
- **Features**:
  - Dynamic leverage calculation
  - Position sizing based on risk
  - Portfolio exposure management
  - Correlation analysis
  - Risk limit enforcement

#### 6. Execution Engine
- **Technology**: Python with asyncio
- **Features**:
  - Order placement and management
  - Exchange integration abstraction
  - Fills and execution tracking
  - Order state management
  - Error handling and retries

#### 7. TP/SL Management
- **Technology**: Python with asyncio
- **Features**:
  - TP/SL stage management
  - Trailing stop implementation
  - Break-even calculation
  - Order safety checks
  - Recovery procedures

#### 8. PnL Analytics
- **Technology**: Python with pandas
- **Features**:
  - Trade-level accounting
  - Performance metrics calculation
  - PnL ledger management
  - Backtesting framework
  - Monte Carlo analysis

#### 9. Telegram Bot
- **Technology**: Python with aiogram
- **Features**:
  - Command processing
  - Real-time notifications
  - Trade reporting
  - Status updates
  - Safety confirmations

#### 10. Database Layer
- **Technology**: PostgreSQL 14+
- **Features**:
  - ACID-compliant transactions
  - JSONB for configuration storage
  - Time-series data optimization
  - Backup and recovery
  - Connection pooling

### Data Flow

1. **Market Data Flow**:
   - Exchange APIs → Market Data Service → Database → WebSocket → Dashboard

2. **Strategy Flow**:
   - Market Data → Strategy Engine → Signal Generation → Risk Engine → Execution Engine

3. **Trade Management Flow**:
   - Execution → Position Tracking → TP/SL Management → PnL Ledger → Analytics

4. **User Interaction Flow**:
   - Dashboard → Backend API → Services → Database → Dashboard Updates

### Exchange Integration

The platform uses CCXT for exchange abstraction with custom adapters for:

- **Binance USDT-M Futures**
  - Rate limiting: 1200/min raw, 600/min polling
  - Mark price for stop triggers
  - Reduce-only order semantics
  - Isolated margin support

- **Bitget USDT-M Futures**
  - Rate limiting: 300/min private, 1200/min public
  - Mark price for stop triggers
  - Reduce-only order semantics
  - Isolated margin support

### Security Architecture

1. **Authentication**:
   - JWT-based web authentication
   - Telegram bot user whitelisting
   - API key rotation support

2. **Data Protection**:
   - AES-256-GCM encryption for credentials
   - PostgreSQL encryption at rest
   - Secure password hashing (bcrypt)

3. **Network Security**:
   - Default localhost-only access
   - HTTPS with TLS 1.3
   - Rate limiting on all endpoints
   - IP whitelisting for exchanges

### Deployment Architecture

The application is designed for Windows portable deployment:

1. **Self-contained**: All dependencies bundled with the application
2. **Portable Python**: Embedded Python runtime
3. **Relative Paths**: All paths resolved relative to application directory
4. **Windows Services**: Background services as Windows services
5. **Registry Integration**: File associations and startup entries

### Monitoring and Logging

1. **Structured Logging**:
   - JSON-formatted logs
   - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Rotating file handlers
   - Centralized log collection

2. **Health Monitoring**:
   - Service health checks
   - Database connectivity monitoring
   - Exchange API status
   - Memory and CPU usage tracking

3. **Audit Logging**:
   - All user actions logged
   - Configuration changes tracked
   - Order execution audited
   - Security events recorded