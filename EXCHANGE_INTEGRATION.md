# QUANTUM TRADER V1 - Exchange Integration Documentation

## Exchange Integration Overview

This document details the integration with Binance USDT-M Futures and Bitget USDT-M Futures exchanges. The platform uses CCXT as the base abstraction layer with custom adapters for exchange-specific behavior.

## Supported Exchanges

### Binance USDT-M Futures
- **API Base**: `https://fapi.binance.com`
- **WebSocket**: `wss://fstream.binance.com`
- **Rate Limits**: 1200/min raw, 600/min polling
- **Position Mode**: One-way (default), Hedge mode supported
- **Margin Mode**: Isolated (default), Cross supported
- **Contract Type**: USDT-M Perpetual

### Bitget USDT-M Futures
- **API Base**: `https://api.bitget.com`
- **WebSocket**: `wss://ws.bitget.com`
- **Rate Limits**: 300/min private, 1200/min public
- **Position Mode**: One-way (default), Hedge mode supported
- **Margin Mode**: Isolated (default), Cross supported
- **Contract Type**: USDT-M Perpetual

## Exchange Abstraction Layer

### Base Adapter Interface

```python
class ExchangeAdapter:
    """Base interface for exchange operations"""
    
    # Market Data
    async def get_symbols(self) -> List[SymbolInfo]
    async def get_candles(self, symbol: str, timeframe: str, limit: int) -> List[Candle]
    async def get_ticker(self, symbol: str) -> Ticker
    async def get_orderbook(self, symbol: str, depth: int) -> OrderBook
    
    # Account
    async def get_balance(self) -> Dict[str, Balance]
    async def get_positions(self) -> List[Position]
    async def get_open_orders(self, symbol: str = None) -> List[Order]
    
    # Trading
    async def place_order(self, params: OrderParams) -> OrderResult
    async def cancel_order(self, order_id: str, symbol: str) -> bool
    async def modify_order(self, order_id: str, params: OrderParams) -> OrderResult
    
    # TP/SL
    async def place_stop_order(self, params: StopOrderParams) -> OrderResult
    
    # Utilities
    async def get_funding_rate(self, symbol: str) -> FundingRate
    async def get_leverage_tiers(self, symbol: str) -> List[LeverageTier]
    async def sync_time(self) -> int
```

### Exchange-Specific Differences Handled

| Feature | Binance | Bitget | Abstraction |
|---------|---------|--------|-------------|
| Symbol Format | BTCUSDT | BTCUSDT | Normalized |
| Timeframe | 1m, 3m, 5m... | 1m, 5m, 15m... | Mapped |
| Order ID | Numeric | Alphanumeric | String |
| Stop Order | STOP_MARKET | planOrder | Unified |
| Reduce-Only | reduceOnly flag | reduceOnly flag | Unified |
| Position Mode | positionSide param | holdSide param | Unified |
| Funding Interval | 8h | 8h | Same |
| Mark Price | markPrice | markPrice | Same |

## Symbol Specifications

### Binance USDT-M Futures

```
Key Parameters:
- Contract Size: 1 unit of base asset
- Tick Size: Variable (e.g., 0.01 for BTC, 0.0001 for small caps)
- Lot Size: Variable (e.g., 0.001 for BTC, 1 for small caps)
- Min Notional: 5 USDT
- Max Leverage: Up to 125x (varies by symbol)
- Maintenance Margin: Tiered by position size
```

### Bitget USDT-M Futures

```
Key Parameters:
- Contract Size: 1 unit of base asset
- Tick Size: Variable
- Lot Size: Variable
- Min Notional: 5 USDT (varies)
- Max Leverage: Up to 125x (varies by symbol)
- Maintenance Margin: Tiered by position size
```

## API Integration Details

### Authentication

```python
# Binance
api_key = "your_api_key"
api_secret = "your_api_secret"
# Headers: X-MBX-APIKEY, signature in query params

# Bitget
api_key = "your_api_key"
api_secret = "your_api_secret"
passphrase = "your_passphrase"
# Headers: ACCESS-KEY, ACCESS-SIGN, ACCESS-TIMESTAMP, ACCESS-PASSPHRASE
```

### Rate Limit Handling

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.rate = requests_per_minute
        self.tokens = requests_per_minute
        self.last_update = time.time()
    
    async def acquire(self):
        while self.tokens < 1:
            await asyncio.sleep(0.1)
            self.refill()
        self.tokens -= 1
    
    def refill(self):
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate / 60)
        self.last_update = now
```

### Error Handling

Common errors and responses:

| Error Code | Binance | Bitget | Action |
|------------|---------|--------|--------|
| -1003 | Rate limit | - | Exponential backoff |
| -1013 | Filter failure | - | Validate params |
| -1102 | Invalid order | - | Reject order |
| -2010 | Insufficient balance | 40014 | Reject order |
| -2011 | Unknown order | 40006 | Ignore/retry |
| -2015 | Invalid API key | 40001 | Alert user |

### Time Synchronization

```python
async def sync_time(self):
    """Sync local clock with exchange server time"""
    server_time = await self.exchange.fetch_time()
    local_time = int(time.time() * 1000)
    self.time_offset = server_time - local_time
    
    # All timestamps adjusted by offset
    def get_timestamp(self):
        return int(time.time() * 1000) + self.time_offset
```

## Market Data Integration

### WebSocket Streams

```python
class MarketDataStream:
    def __init__(self, exchange: str):
        self.exchange = exchange
        self.subscriptions = {}
        self.callbacks = defaultdict(list)
    
    async def subscribe_candles(self, symbol: str, timeframe: str):
        stream_name = f"{symbol.lower()}@kline_{timeframe}"
        await self.ws.subscribe(stream_name)
    
    async def subscribe_mark_price(self, symbol: str):
        stream_name = f"{symbol.lower()}@markPrice@1s"
        await self.ws.subscribe(stream_name)
    
    async def handle_message(self, msg: dict):
        # Parse and dispatch to callbacks
        for callback in self.callbacks[msg['stream']]:
            await callback(parse_message(msg))
```

### Candle Data Structure

```python
@dataclass
class Candle:
    symbol: str
    timeframe: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades: int
    is_closed: bool
```

### Historical Data Management

- Store in database with timeframe partitioning
- Backfill on startup for configured symbols
- Real-time updates via WebSocket
- Gap detection and filling

## Order Execution

### Order Types Supported

| Type | Binance | Bitget | Use Case |
|------|---------|--------|----------|
| MARKET | ✓ | ✓ | Immediate execution |
| LIMIT | ✓ | ✓ | Specific price entry |
| STOP_MARKET | ✓ | ✓ | Stop loss / TP trigger |
| STOP_LIMIT | ✓ | ✓ | Stop with limit |
| TAKE_PROFIT_MARKET | ✓ | ✓ | TP trigger |
| TAKE_PROFIT_LIMIT | ✓ | ✓ | TP with limit |

### Order Parameters

```python
@dataclass
class OrderParams:
    symbol: str
    side: str  # BUY/SELL
    type: str  # MARKET/LIMIT/STOP_MARKET...
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    reduce_only: bool = False
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    position_side: Optional[str] = None  # LONG/SHORT/BOTH
```

### Order Response

```python
@dataclass
class OrderResult:
    order_id: str
    exchange_order_id: str
    symbol: str
    status: OrderStatus
    filled_quantity: Decimal
    average_price: Decimal
    fees: Decimal
    timestamp: datetime
```

## TP/SL Order Management

### Binance TP/SL

```python
# Stop Loss (STOP_MARKET)
params = {
    "symbol": "BTCUSDT",
    "side": "SELL",  # Opposite of position
    "type": "STOP_MARKET",
    "stopPrice": "45000",
    "quantity": "0.01",
    "reduceOnly": "true",
    "workingType": "MARK_PRICE",
    "positionSide": "LONG"
}

# Take Profit (TAKE_PROFIT_MARKET)
params = {
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "TAKE_PROFIT_MARKET",
    "stopPrice": "50000",
    "quantity": "0.004",  # 40% of position
    "reduceOnly": "true",
    "workingType": "MARK_PRICE",
    "positionSide": "LONG"
}
```

### Bitget TP/SL

```python
# Plan Order (Stop Market)
params = {
    "symbol": "BTCUSDT",
    "marginCoin": "USDT",
    "side": "close_long",
    "orderType": "market",
    "triggerPrice": "45000",
    "size": "0.01",
    "triggerType": "mark_price",
    "planType": "pos_loss"  # pos_loss, pos_profit
}

# Take Profit
params = {
    "symbol": "BTCUSDT",
    "marginCoin": "USDT",
    "side": "close_long",
    "orderType": "market",
    "triggerPrice": "50000",
    "size": "0.004",
    "triggerType": "mark_price",
    "planType": "pos_profit"
}
```

### Order Monitoring

```python
class OrderMonitor:
    async def monitor_order(self, order_id: str, symbol: str):
        while True:
            order = await self.get_order(order_id, symbol)
            if order.status in [FILLED, CANCELLED, REJECTED]:
                await self.handle_completion(order)
                break
            await asyncio.sleep(1)  # Polling interval
    
    async def verify_stop_active(self, position: Position) -> bool:
        """Verify protective stop order exists and is active"""
        open_orders = await self.get_open_orders(position.symbol)
        stop_orders = [o for o in open_orders if o.type in [STOP_MARKET, TAKE_PROFIT_MARKET]]
        return len(stop_orders) > 0
```

## Position Management

### Position Structure

```python
@dataclass
class Position:
    symbol: str
    side: str  # LONG/SHORT
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: int
    margin: Decimal
    liquidation_price: Decimal
    margin_mode: str  # ISOLATED/CROSS
```

### Position Reconciliation

```python
async def reconcile_positions(self):
    """Reconcile local state with exchange"""
    exchange_positions = await self.get_positions()
    local_positions = await self.db.get_open_positions()
    
    for exch_pos in exchange_positions:
        local = find_matching(local_positions, exch_pos)
        if local:
            # Update local with exchange data
            await self.update_local_position(local, exch_pos)
        else:
            # Orphaned position on exchange
            await self.handle_orphaned_position(exch_pos)
    
    for local_pos in local_positions:
        if not find_matching(exchange_positions, local_pos):
            # Local position not on exchange
            await self.handle_missing_position(local_pos)
```

## Funding Rate Handling

```python
async def fetch_funding_rates(self, symbols: List[str]) -> Dict[str, FundingRate]:
    rates = {}
    for symbol in symbols:
        # Binance: fundingRate endpoint
        # Bitget: fundingTime/fundingRate endpoint
        rate = await self.get_funding_rate(symbol)
        rates[symbol] = FundingRate(
            symbol=symbol,
            rate=rate['fundingRate'],
            next_funding_time=rate['nextFundingTime'],
            interval_hours=8
        )
    return rates
```

## Account Modes

### Position Mode Detection

```python
async def detect_position_mode(self) -> PositionMode:
    """Detect if account is in one-way or hedge mode"""
    # Binance: GET /fapi/v1/positionSide/dual
    # Bitget: GET /api/v2/mix/account/account
    return PositionMode.ONE_WAY  # or HEDGE
```

### Margin Mode

```python
async def set_margin_mode(self, symbol: str, mode: MarginMode):
    """Set margin mode for symbol"""
    # Binance: POST /fapi/v1/marginType
    # Bitget: POST /api/v2/mix/account/set-margin-mode
    pass
```

## Testing Strategy

### Mock Exchange

```python
class MockExchangeAdapter(ExchangeAdapter):
    """Mock exchange for testing without API keys"""
    
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.balances = {"USDT": Decimal("10000")}
    
    async def place_order(self, params):
        # Simulate order execution
        order_id = f"mock_{uuid.uuid4()}"
        return OrderResult(
            order_id=order_id,
            exchange_order_id=order_id,
            symbol=params.symbol,
            status=OrderStatus.FILLED,
            filled_quantity=params.quantity,
            average_price=params.price or await self.get_mark_price(params.symbol),
            fees=params.quantity * params.price * Decimal("0.0004"),
            timestamp=datetime.utcnow()
        )
```

### Integration Tests

1. Symbol info retrieval
2. Candle data accuracy
3. Order placement and cancellation
4. TP/SL order lifecycle
5. Position reconciliation
6. Rate limit handling
7. Error recovery
8. Time synchronization

## Configuration

### Exchange Config File

```yaml
# config/exchanges/binance.yaml
exchange: "binance"
api:
  base_url: "https://fapi.binance.com"
  ws_url: "wss://fstream.binance.com"
  timeout: 10000
  rate_limit: 1200
credentials:
  # Encrypted in database
settings:
  default_margin_mode: "ISOLATED"
  default_position_mode: "ONE_WAY"
  working_type: "MARK_PRICE"
  recv_window: 5000

# config/exchanges/bitget.yaml
exchange: "bitget"
api:
  base_url: "https://api.bitget.com"
  ws_url: "wss://ws.bitget.com"
  timeout: 10000
  rate_limit: 300
credentials:
  # Encrypted in database
settings:
  default_margin_mode: "ISOLATED"
  default_position_mode: "ONE_WAY"
  trigger_type: "mark_price"
```

## Security Considerations

- API keys encrypted at rest (AES-256-GCM)
- Keys only decrypted in memory during API calls
- IP whitelist enforced where supported
- No withdrawal permissions granted
- Separate keys for paper vs live trading
- Key rotation supported
- Audit log of all API calls