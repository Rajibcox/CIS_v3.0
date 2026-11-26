# QUANTUM TRADER V1 - Risk Model Documentation

## Risk Model Overview

The risk model is the core safety system that governs all trading decisions. It operates on a **risk-first** principle: position size is determined by risk budget first, then leverage is calculated to fit the position within available margin.

## Core Risk Parameters

### Portfolio-Level Limits

| Parameter | Default | Configurable | Description |
|-----------|---------|--------------|-------------|
| Initial Equity | 100 USDT | Yes | Starting paper trading capital |
| Risk Per Trade | 0.5% | Yes | Maximum loss per trade as % of equity |
| Max Simultaneous Positions | 2 | Yes | Maximum open positions across all exchanges |
| Max Leverage | 3x | Yes | Maximum leverage for any position |
| Daily Loss Limit | 1.5% | Yes | Maximum realized loss per day |
| Drawdown Warning | 5% | Yes | Alert threshold for portfolio drawdown |
| Emergency Drawdown | 8% | Yes | Automatic trading halt threshold |

### Per-Trade Risk Calculation

```
1. max_risk_amount = current_equity × risk_per_trade
2. stop_distance_usd = |entry_price - stop_loss| × quantity
3. position_size = max_risk_amount / stop_distance_usd
4. required_margin = position_size × entry_price / leverage
5. if required_margin ≤ available_margin: proceed
   else: reject trade
```

## Dynamic Leverage Calculation

### Leverage Decision Process

The leverage is **never** used to increase position size. It is calculated *after* position size is determined from risk parameters.

```
Input: position_size, entry_price, available_margin, exchange_constraints

1. notional_value = position_size × entry_price
2. min_leverage = notional_value / available_margin
3. max_leverage_allowed = min(exchange_max, portfolio_max_leverage)
4. selected_leverage = clamp(min_leverage, 1, max_leverage_allowed)
5. Verify: selected_leverage × maintenance_margin < 1.0 (liquidation buffer)
```

### Liquidation Safety Buffer

```
maintenance_margin_rate = exchange_specific (e.g., 0.005 for Binance 3x)
liquidation_price_long = entry_price × (1 - 1/leverage + maintenance_margin_rate)
liquidation_price_short = entry_price × (1 + 1/leverage - maintenance_margin_rate)

safety_buffer = 20% of (liquidation_price - entry_price)
effective_stop = max(user_stop, liquidation_price + safety_buffer)
```

### Leverage Rejection Criteria

Trade is rejected if:
1. `min_leverage > max_leverage_allowed`
2. `position_size < exchange_min_lot_size`
3. `notional_value < exchange_min_notional`
3. `stop_distance` would require leverage > `max_leverage_allowed`
4. Liquidation price is within 5% of stop loss

## Position Sizing

### Quantity Calculation

```
raw_quantity = max_risk_amount / (entry_price - stop_loss)
adjusted_quantity = floor(raw_quantity / lot_size) × lot_size
final_quantity = max(adjusted_quantity, min_lot_size)

if final_quantity × entry_price < min_notional:
    reject trade
```

### Rounding and Precision

- All quantities rounded **down** to exchange lot size
- Prices rounded to exchange tick size
- Never round up (prevents oversizing)
- Residual quantity tracked for reconciliation

## Portfolio Risk Management

### Exposure Tracking

```
total_exposure = Σ (position_quantity × current_price) for all open positions
total_margin_used = Σ (position_notional / position_leverage)
available_margin = equity - total_margin_used + unrealized_pnl
```

### Correlation Risk

- Symbols with >0.7 correlation treated as single exposure
- BTC correlation factored into all altcoin positions
- Maximum correlated exposure: 50% of equity

### Drawdown Controls

```
current_drawdown = (peak_equity - current_equity) / peak_equity

if current_drawdown ≥ drawdown_warning:
    - Reduce position sizes by 50%
    - Alert user
    - Log event

if current_drawdown ≥ emergency_drawdown:
    - Halt all new entries
    - Close all positions at market
    - Alert user
    - Enter emergency state
```

### Daily Loss Limit

```
daily_realized_pnl = Σ (closed_trade_pnl) for today

if daily_realized_pnl ≤ -daily_loss_limit × equity:
    - Halt all new entries for remainder of day
    - Alert user
    - Allow existing positions to run (with TP/SL active)
    - Reset at 00:00 UTC
```

## Trade-Level Risk Controls

### Entry Validation

Before any trade entry:
1. ✓ Signal score ≥ minimum threshold
2. ✓ Risk/reward ≥ 2:1 (configurable)
3. ✓ Stop distance ≥ minimum (2× ATR or 1%)
4. ✓ Notional ≥ exchange minimum
5. ✓ Quantity ≥ exchange minimum lot
6. ✓ Margin available after entry
7. ✓ Portfolio exposure limits not exceeded
7. ✓ Correlation limits not exceeded
8. ✓ Not in drawdown emergency state
9. ✓ Daily loss limit not exceeded

### Position Monitoring

Continuous monitoring of open positions:
- Unrealized PnL vs risk budget
- Mark price vs liquidation price
- Funding rate impact
- Correlation changes
- Market regime changes

### Emergency Procedures

1. **Margin Call Risk**: If position approaches liquidation
   - Alert immediately
   - Attempt to reduce position
   - If unable, force close at market

2. **Exchange Failure**: If API unavailable
   - Preserve existing protective orders
   - Alert user
   - Block new entries
   - Enter degraded mode

3. **System Failure**: Application crash/restart
   - On restart: reconcile all positions
   - Verify all TP/SL orders active
   - Alert if discrepancies found

## Risk Reports

### Daily Risk Report

- Current equity and drawdown
- Open positions with risk metrics
- Daily realized PnL vs limit
- Available margin
- Correlation exposure
- Leverage distribution

### Per-Trade Risk Report

- Selected leverage and reason
- Position quantity and notional
- Required margin
- Maximum planned loss
- Stop distance
- Estimated liquidation price
- Liquidation buffer
- Rejected alternatives

## Configuration Validation

All risk parameters validated on change:
- `risk_per_trade`: (0, 0.1] - max 10%
- `max_leverage`: [1, 100]
- `daily_loss_limit`: (0, 0.5] - max 50%
- `drawdown_warning`: (0, 0.5] - max 50%
- `emergency_drawdown`: > `drawdown_warning`, ≤ 1.0
- `tp_allocation`: Must sum to 1.0

## Testing Requirements

Unit tests for:
- Position sizing calculations
- Leverage selection logic
- Liquidation price accuracy
- Drawdown triggering
- Daily loss limit enforcement
- Correlation limit enforcement
- Emergency procedures