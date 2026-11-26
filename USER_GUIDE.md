# QUANTUM TRADER V1 - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Configuration Center](#configuration-center)
4. [Market Intelligence](#market-intelligence)
5. [Strategy Center](#strategy-center)
6. [Signal Center](#signal-center)
7. [Paper Trading](#paper-trading)
8. [Portfolio & PnL Analytics](#portfolio--pnl-analytics)
9. [Backtesting](#backtesting)
10. [Telegram Bot](#telegram-bot)
11. [Risk Management](#risk-management)
12. [Live Trading Authorization](#live-trading-authorization)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation
1. Connect your portable SSD to Windows 11 computer
2. Navigate to the QUANTUM_TRADER_V1 folder
3. Run `INSTALL_QUANTUM_TRADER.bat` (run as Administrator recommended)
4. Wait for installation to complete

### First Launch
1. Run `START_QUANTUM_TRADER.bat`
2. Open browser to `http://localhost:8000`
3. You'll see the QUANTUM TRADER dashboard

### Initial Configuration
Before trading, configure these essential settings:

1. **Exchange Connections** (Configuration → Exchange Connections)
   - Add Binance API credentials (read + trade permissions)
   - Add Bitget API credentials (read + trade permissions)
   - Enable IP whitelist on exchange for your IP

2. **Risk Settings** (Configuration → Risk Management)
   - Starting equity: 100 USDT (paper)
   - Risk per trade: 0.5%
   - Max positions: 2
   - Max leverage: 3x
   - Daily loss limit: 1.5%

3. **Telegram** (Configuration → Telegram)
   - Add bot token from @BotFather
   - Add your user ID (get from @userinfobot)
   - Test with `/start` command

---

## Dashboard Overview

The dashboard is organized into functional pages accessible via the sidebar navigation.

### Main Sections

| Section | Pages | Purpose |
|---------|-------|---------|
| **Overview** | Dashboard | Portfolio summary, key metrics |
| **Market** | Intelligence, Scanner, LONG/Short Opportunities | Market analysis |
| **Signals** | Signal Center, Signal History | Signal management |
| **Strategies** | Strategy Center, Visual Builder, Indicators | Strategy configuration |
| **Risk** | Leverage, Position Sizing, TP/SL, Profit Protection | Risk controls |
| **Trading** | Paper Trading, Portfolio, Positions, Orders, History | Trade execution |
| **Analytics** | PnL, Performance, Backtesting, Walk-Forward, Monte Carlo | Analysis |
| **System** | Exchanges, Telegram, Notifications, Health, Settings | Administration |

### Key Dashboard Elements

**Header Bar**:
- Current equity (paper/live)
- Daily PnL
- Open positions count
- System status indicator
- Live trading status badge

**Sidebar**:
- Collapsible navigation
- Page groups by function
- Active page highlighted

**Real-time Updates**:
- WebSocket connection status
- Auto-refreshing data
- Live price feeds

---

## Configuration Center

All settings are managed through the web UI - no file editing required.

### Exchange Connections
- **Add Exchange**: Select Binance or Bitget
- **API Credentials**: Enter API key, secret, passphrase (Bitget)
- **Permissions**: Verify read + trade, NO withdrawal
- **IP Whitelist**: Add your current IP on exchange
- **Test Connection**: Validates credentials before saving

### Market Selection
- **Exchanges**: Enable/disable Binance, Bitget
- **Quote Asset**: USDT-M perpetuals only
- **Min Volume**: Filter low-liquidity symbols
- **Max Spread**: Filter wide-spread markets
- **Min History**: Minimum candle history required

### Scanner Filters
- **Timeframes**: 3m, 5m, 15m, 1h, 4h, 1d
- **Volume**: Minimum 24h volume
- **Volatility**: ATR percentile range
- **Trend**: ADX threshold
- **Regime**: Trending/ranging/volatile filters

### Strategy Parameters
Per-strategy configuration:
- **Enable/Disable**: Toggle strategies
- **Weight**: Signal combination weight
- **Timeframes**: Which timeframes to analyze
- **Symbols**: Specific symbols or all eligible
- **Risk Multiplier**: Adjust position size per strategy

### Signal Scoring
- **Minimum Score**: Threshold for qualified signals
- **Component Weights**: Trend, momentum, volume, volatility
- **Regime Bonuses**: Extra points for favorable regimes
- **Penalties**: Deductions for adverse conditions

### TP/SL Configuration
- **Allocation**: TP1 40%, TP2 30%, TP3 20%, Runner 10%
- **Trailing**: ATR multiplier, minimum distance
- **Break-even**: Fee-aware calculation
- **Runner Management**: Hybrid trailing parameters

### Leverage Policy
- **Max Leverage**: Hard ceiling (default 3x)
- **Risk-First**: Position size from risk, then leverage
- **Liquidation Buffer**: Safety margin above liquidation
- **Per-Symbol Overrides**: Different limits per symbol

### Risk Limits
- **Portfolio**: Max drawdown, daily loss, correlation
- **Per-Trade**: Max risk, min R:R, min stop distance
- **Emergency**: Auto-close thresholds, halt conditions

### Telegram Setup
- **Bot Token**: From @BotFather
- **Allowed Users**: User IDs who can control bot
- **Commands Enabled**: Select command categories
- **Notifications**: Select alert types

### Backup & Storage
- **Auto Backup**: Daily at specified time
- **Retention**: Number of backups to keep
- **Location**: On SSD (data/backups/)
- **Manual Backup**: Button for immediate backup

---

## Market Intelligence

### Market Intelligence Page
Real-time market overview:
- **BTC Dominance**: Market structure indicator
- **Fear & Greed**: Sentiment index
- **Global Volume**: 24h futures volume
- **Top Movers**: Gainers/losers by %
- **Funding Rates**: Aggregate funding picture
- **Open Interest**: Total OI changes
- **Liquidations**: Recent liquidation data

### Market Scanner
Automated opportunity detection:
- **Scan Now**: Manual trigger
- **Auto-Scan**: Every 5 minutes (configurable)
- **Results Table**: Ranked opportunities
- **Filters**: Apply custom filters to results
- **Export**: CSV export of scan results

### LONG Opportunities
Bullish setups meeting criteria:
- **Signal Score**: Quality rating (0-100)
- **Strategy**: Which strategy generated it
- **Entry Zone**: Suggested entry range
- **Stop Loss**: Initial protective stop
- **TP Targets**: TP1/TP2/TP3 levels
- **Risk/Reward**: Calculated ratio
- **Regime**: Market regime context
- **BTC Alignment**: Correlation with BTC

### SHORT Opportunities
Bearish setups (inverse of LONG):
- Same columns as LONG
- Entry above current price
- Stop above entry
- TP below entry

---

## Strategy Center

### Strategy List
All configured strategies with:
- **Status**: Active/Inactive
- **Performance**: Win rate, profit factor, expectancy
- **Signals Today**: Count generated
- **Last Signal**: Timestamp
- **Actions**: Edit, Clone, Disable, Backtest

### Visual Strategy Builder
No-code strategy creation:
1. **Select Direction**: LONG, SHORT, or BOTH
2. **Add Conditions**: Drag-and-drop rule builder
3. **Condition Types**:
   - Indicator vs Value (RSI < 30)
   - Indicator vs Indicator (EMA9 > EMA21)
   - Price Action (Close > VWAP)
   - Volume (Volume > 2x Average)
   - Trend (ADX > 25)
   - Regime (Market = Trending)
4. **Logic Groups**: AND/OR combinations
5. **Entry Rules**: When to generate signal
6. **Exit Rules**: When to close position
7. **Save as Version**: Versioned strategy storage

### Indicator Configuration
Manage technical indicators:
- **Built-in**: RSI, MACD, EMA, SMA, Bollinger, ATR, ADX, VWAP, OBV, MFI
- **Parameters**: Period, source, offsets
- **Custom**: Add Pine Script indicators (future)
- **Validation**: Check for repainting, lookahead

### Strategy Comparison
Compare strategy versions:
- Side-by-side parameters
- Backtest results comparison
- Performance metrics table
- Equity curves overlay

---

## Signal Center

### Signal Lifecycle
```
CANDIDATE → QUALIFIED → ACTIVE → TRIGGERED → EXECUTED
                ↓           ↓          ↓
            EXPIRED    INVALIDATED  REJECTED
```

### Active Signals
Currently valid trading opportunities:
- **Time Remaining**: Until expiration
- **Distance to Entry**: % from current price
- **Quality Indicators**: Score breakdown
- **One-Click Paper Trade**: Execute in paper mode

### Signal History
Complete signal archive:
- **Filters**: Date, strategy, symbol, outcome
- **Executed**: Became positions
- **Expired**: Time ran out
- **Invalidated**: Market moved against setup
- **Rejected**: Failed validation

### Signal Details
Click any signal for full analysis:
- **Chart**: Multi-timeframe with indicators
- **Entry Logic**: Why signal generated
- **Risk Calculation**: Position size, leverage, margin
- **TP/SL Plan**: Complete exit strategy
- **Market Context**: Regime, BTC, correlations
- **Invalidation**: What would kill the setup

---

## Paper Trading

### Paper Trading Page
Simulated trading environment:
- **Virtual Balance**: 100 USDT starting equity
- **Open Positions**: Current paper positions
- **Order Book**: Pending paper orders
- **Trade History**: All completed paper trades
- **PnL Summary**: Real-time performance

### Paper Trading Controls
- **Start/Pause/Resume**: Control paper engine
- **Reset**: Back to 100 USDT, clear history
- **Settings**: Fees, slippage, funding assumptions
- **Speed**: Real-time or accelerated (backtest mode)

### Placing Paper Trades
1. From Signal Center: Click "Paper Trade"
2. Manual: Paper Trading → New Order
3. Review: Position size, leverage, TP/SL
4. Confirm: Places simulated order

### Paper Order Types
- **Market**: Fill at current mark price
- **Limit**: Fill when price reaches level
- **Stop Market**: Trigger at mark price
- **Reduce Only**: TP/SL orders

### Paper Trading Realism
Simulated factors:
- **Fees**: 0.1% per side (configurable)
- **Slippage**: 0.05% adverse (configurable)
- **Funding**: 8-hour intervals, realistic rates
- **Partial Fills**: Random partial fill simulation
- **Latency**: Simulated network delay
- **Liquidation**: Realistic liquidation engine

---

## Portfolio & PnL Analytics

### Portfolio Page
Unified view across exchanges:
- **Total Equity**: Paper + unrealized PnL
- **Available Balance**: Free margin
- **Allocated Margin**: Used for positions
- **Daily PnL**: Realized today
- **Drawdown**: From peak equity
- **Positions Table**: All open positions

### PnL Analytics
Deep performance analysis:

#### Overview Tab
- **Equity Curve**: Time series of equity
- **Drawdown Chart**: Underwater plot
- **Monthly Returns**: Calendar heatmap
- **Key Metrics**: Win rate, PF, expectancy, Sharpe

#### Trade Analysis Tab
- **Win/Loss Distribution**: Histogram
- **R-Multiple Distribution**: Risk-adjusted outcomes
- **Holding Time**: Duration analysis
- **MAE/MFE**: Adverse/favorable excursion

#### Breakdown Tabs
- **By Strategy**: Performance per strategy
- **By Symbol**: Best/worst symbols
- **By Direction**: LONG vs SHORT
- **By Timeframe**: Which TF works best
- **By Regime**: Trending vs ranging
- **By Session**: Asian/European/US
- **By TP Stage**: TP1/TP2/TP3/Runner contribution

#### TP Analytics
- **TP Hit Rates**: % reaching each target
- **Profit Captured**: At each stage
- **Giveback After TP3**: Runner performance
- **Stop Out After TP**: Protection effectiveness

---

## Backtesting

### Backtest Configuration
1. **Select Strategy**: Choose strategy version
2. **Select Symbols**: Single, watchlist, or all
3. **Date Range**: Start/end dates
4. **Timeframes**: Primary + context TFs
5. **Initial Capital**: Starting equity
6. **Costs**: Fees, slippage, funding
7. **Risk Settings**: Same as live/paper

### Running Backtest
- **Start**: Begin simulation
- **Progress**: Real-time progress bar
- **Cancel**: Stop early if needed
- **Results**: Auto-display when complete

### Backtest Results
- **Equity Curve**: vs Buy & Hold
- **Trade List**: Every simulated trade
- **Metrics Table**: Complete statistics
- **Monthly Returns**: Calendar view
- **Drawdown Periods**: Recovery analysis
- **Parameter Sensitivity**: If optimized

### Walk-Forward Analysis
Robustness testing:
- **In-Sample**: Training period
- **Out-of-Sample**: Testing period
- **Rolling Windows**: Multiple IS/OOS cycles
- **Stability Metric**: IS vs OOS correlation

### Monte Carlo Analysis
Statistical validation:
- **Simulations**: 1000+ random trade sequences
- **Confidence Intervals**: 5th/50th/95th percentile
- **Ruination Risk**: Probability of blowing up
- **Expected Drawdown**: Distribution

---

## Telegram Bot

### Authorization
1. Start bot: `/start`
2. Bot replies with your user ID
3. Add user ID to Configuration → Telegram → Allowed Users
4. Admin users get full command access

### Command Categories

#### General
| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Command list |
| `/menu` | Interactive menu |
| `/status` | System status |
| `/health` | Health check |
| `/version` | Version info |
| `/uptime` | Running time |
| `/connections` | Exchange status |

#### Market
| Command | Description |
|---------|-------------|
| `/market` | Market overview |
| `/btc` | BTC analysis |
| `/regime` | Market regime |
| `/volatility` | Volatility scan |
| `/funding` | Funding rates |
| `/top_gainers` | Top 24h gainers |
| `/top_losers` | Top 24h losers |

#### Scanner
| Command | Description |
|---------|-------------|
| `/scanner` | Run scan |
| `/opportunities` | Current setups |
| `/long_candidates` | LONG setups |
| `/short_candidates` | SHORT setups |
| `/watchlist` | Your watchlist |

#### Signals
| Command | Description |
|---------|-------------|
| `/signals` | Active signals |
| `/best_signals` | Top scored |
| `/signal_history` | Recent signals |
| `/signal_stats` | Signal statistics |

#### Paper Trading
| Command | Description |
|---------|-------------|
| `/paper` | Paper status |
| `/paper_balance` | Virtual balance |
| `/paper_positions` | Open positions |
| `/paper_pnl` | PnL summary |
| `/paper_reset` | Reset to 100 USDT |

#### Strategies
| Command | Description |
|---------|-------------|
| `/strategies` | List strategies |
| `/strategy_stats` | Performance |
| `/strategy_compare` | Compare versions |

#### Risk
| Command | Description |
|---------|-------------|
| `/risk` | Risk summary |
| `/risk_limits` | Current limits |
| `/drawdown` | Current drawdown |
| `/emergency_stop` | Halt all trading |

#### Portfolio
| Command | Description |
|---------|-------------|
| `/portfolio` | Portfolio summary |
| `/equity` | Current equity |
| `/pnl` | PnL breakdown |
| `/daily_report` | Today's report |

#### System
| Command | Description |
|---------|-------------|
| `/pause` | Pause all activity |
| `/resume` | Resume activity |
| `/logs` | Recent logs |
| `/backup` | Create backup |
| `/diagnostics` | System check |

#### Live Trading Safety
| Command | Description |
|---------|-------------|
| `/live_status` | Live mode status |
| `/live_eligibility` | Check eligibility |
| `/arm_live` | Arm live mode |
| `/confirm_live` | Confirm activation |
| `/disarm_live` | Disable live mode |

### Notifications
Automatic alerts for:
- New qualified signals
- TP/SL triggers
- Position opens/closes
- Risk limit breaches
- System errors
- Daily/weekly reports

---

## Risk Management

### Risk Dashboard
Real-time risk monitoring:
- **Current Drawdown**: % from peak
- **Daily PnL**: vs daily limit
- **Open Risk**: Sum of position risks
- **Available Margin**: Free collateral
- **Leverage Distribution**: Across positions
- **Correlation Exposure**: Concentrated risk

### Risk Limits Enforcement
Hard limits that cannot be overridden from UI:
- **Max Leverage**: 3x (configurable, but hardcoded max 10x)
- **Risk Per Trade**: 0.5% (max 5% in UI)
- **Daily Loss**: 1.5% (max 10% in UI)
- **Max Positions**: 2 (max 10 in UI)
- **Emergency Drawdown**: 8% (triggers auto-close)

### Position Sizing Logic
```
1. Risk Budget = Equity × Risk Per Trade
2. Stop Distance = |Entry - Stop| × Quantity
3. Position Size = Risk Budget / Stop Distance
4. Leverage = Notional / Available Margin
5. Validate: Leverage ≤ Max, Notional ≥ Min, Qty ≥ Lot
```

### Leverage Intelligence
Per-trade leverage calculation:
- **Risk-First**: Size from risk, then leverage
- **Exchange Constraints**: Tiers, maintenance margin
- **Liquidation Buffer**: 20% above liquidation price
- **Report**: Full decision audit trail

### Emergency Procedures
- **Emergency Stop**: `/emergency_stop` or dashboard button
- **Close All**: Market close all positions
- **Cancel Orders**: Cancel all open orders
- **Halt New Entries**: Block new signals
- **Alert**: Telegram + dashboard notification

---

## Live Trading Authorization

### Safety Philosophy
Live trading requires explicit, multi-step authorization. The system defaults to **PAPER MODE** and will never trade live without deliberate user action.

### Authorization States
```
PAPER MODE → LIVE ELIGIBLE → LIVE ARMED → LIVE ACTIVE
                ↓              ↓            ↓
            (not met)     (not confirmed) (emergency)
```

### Eligibility Criteria (All Must Pass)
1. ✅ **100+ Paper Trades**: Minimum sample size
2. ✅ **30+ Days Forward Test**: Out-of-sample validation
3. ✅ **Positive Expectancy**: Net profit after costs
4. ✅ **Profit Factor > 1.2**: Minimum threshold
4. ✅ **Max Drawdown < 10%**: Acceptable risk
5. ✅ **No Critical Bugs**: All P0/P1 tests passing
6. ✅ **TP/SL Verified**: Protective orders tested
7. ✅ **Recovery Tested**: Crash/restart recovery works

### Arming Live Mode
1. **Check Eligibility**: Dashboard → Live Trading Eligibility
2. **Separate Credentials**: Live API keys (different from paper)
3. **Arm Command**: `/arm_live` in Telegram
4. **Confirm**: `/confirm_live` with explicit confirmation
5. **Activation**: System enters LIVE ACTIVE state

### Live Trading Safeguards
- **Different Credentials**: Paper and live keys separate
- **Position Limits**: Exchange-level limits enforced
- **Daily Loss Limit**: Hard stop at exchange level
- **Kill Switch**: Instant disable from Telegram/dashboard
- **Audit Trail**: Every live action logged
- **No Auto-Activation**: Never automatic

### Disarming
- `/disarm_live` - Immediate return to paper
- Emergency stop also disarms
- All live positions managed to completion or closed

---

## Troubleshooting

### Common Issues

#### "Application won't start"
1. Run `DIAGNOSTICS_QUANTUM_TRADER.bat`
2. Check `data/logs/quantum_trader_error.log`
3. Verify Python in `runtime/venv`
4. Re-run `INSTALL_QUANTUM_TRADER.bat`

#### "Dashboard not loading"
1. Check `START_QUANTUM_TRADER.bat` running
2. Verify port 8000 not in use: `netstat -an | findstr 8000`
3. Check firewall allows localhost:8000
4. Try `http://127.0.0.1:8000`

#### "Exchange connection failed"
1. Verify API credentials in Configuration
2. Check IP whitelist on exchange
3. Test internet: `ping fapi.binance.com`
4. Check rate limits not exceeded
5. Verify exchange not in maintenance

#### "Paper trading not working"
1. Check Paper Trading page - is it running?
2. Verify paper trading enabled in Settings
3. Check for sufficient virtual balance
4. Review paper trade logs

#### "Signals not generating"
1. Check scanner running (Market → Scanner)
2. Verify strategies enabled (Strategy Center)
3. Check market hours (crypto 24/7)
4. Review signal score threshold
5. Check eligible symbols list

#### "TP/SL not triggering"
1. Verify TP/SL service running
2. Check exchange has stop orders
3. Review stop order parameters
4. Check mark price vs trigger price
5. Verify reduce-only flag set

#### "PnL seems wrong"
1. Check fees and funding included
2. Verify realized vs unrealized
3. Run PnL recalculation (admin)
4. Compare with exchange history

#### "Telegram bot not responding"
1. Verify bot token in Configuration
2. Check your user ID in Allowed Users
3. Test with `/start` command
4. Check bot not blocked
5. Review Telegram command logs

#### "Database errors"
1. Run `DIAGNOSTICS_QUANTUM_TRADER.bat`
2. Try `RECOVERY_QUANTUM_TRADER.bat`
3. Check disk space
4. Verify database file not corrupted

### Log Files
Location: `data/logs/`
- `quantum_trader.log` - General application log
- `quantum_trader_error.log` - Errors only
- Rotated daily, 5 files retained

### Getting Help
1. Check this guide
2. Run diagnostics
3. Review logs
4. Check GitHub Issues
5. Create new issue with:
   - Error message
   - Log excerpt
   - Steps to reproduce
   - System info (diagnostics output)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Refresh current page |
| `Ctrl+Shift+R` | Hard refresh (clear cache) |
| `Esc` | Close modal/dropdown |
| `?` | Show help overlay |
| `Alt+1-9` | Navigate to page group |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-11-26 | Initial user guide |

---

*QUANTUM TRADER V1 - Professional Quantitative Futures Trading Platform*
*Built for serious traders who demand accuracy, safety, and reliability.*