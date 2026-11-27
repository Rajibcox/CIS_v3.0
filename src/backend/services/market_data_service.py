"""
Market Data Service for QUANTUM TRADER V1
Handles real-time and historical market data from Binance and Bitget
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import ccxt.async_support as ccxt
from sqlalchemy.orm import Session

from src.backend.models.database import (
    Exchange, Symbol, MarketCandle, MarketRegime
)
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger, log_service_event


logger = get_logger(__name__)


@dataclass
class CandleData:
    """Normalized candle data"""
    symbol: str
    exchange: str
    timeframe: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Optional[Decimal] = None
    trades: Optional[int] = None
    is_closed: bool = False


@dataclass
class TickerData:
    """Real-time ticker data"""
    symbol: str
    exchange: str
    price: Decimal
    bid: Decimal
    ask: Decimal
    bid_volume: Decimal
    ask_volume: Decimal
    volume_24h: Decimal
    change_24h_pct: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime
    spread_bps: Decimal = Decimal('0')
    spread_pct: Decimal = Decimal('0')


@dataclass
class OrderBookSnapshot:
    """Order book snapshot"""
    symbol: str
    exchange: str
    bids: List[tuple]  # (price, volume)
    asks: List[tuple]  # (price, volume)
    timestamp: datetime


class ExchangeAdapter:
    """Wrapper for CCXT exchange with QUANTUM TRADER specific logic"""

    def __init__(self, exchange_name: str, config: Config):
        self.exchange_name = exchange_name
        self.config = config
        self.exchange = None
        self.logger = get_logger(f"exchange.{exchange_name}")
        self._symbol_map = {}  # Internal symbol -> Exchange symbol
        self._symbol_info_cache = {}
        self._ws_connections: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize CCXT exchange"""
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange_config = self.config.get_exchange_config(self.exchange_name)
        self.exchange = exchange_class(exchange_config)

        # Load markets
        await self.exchange.load_markets()
        self._build_symbol_map()
        self.logger.info(f"Initialized {self.exchange_name} adapter with {len(self.exchange.markets)} markets")

    def _build_symbol_map(self):
        """Build mapping from internal symbol format to exchange format"""
        for market_id, market in self.exchange.markets.items():
            if market.get('quote') == 'USDT' and market.get('type') in ['future', 'swap']:
                internal_symbol = market['base'] + market['quote']
                self._symbol_map[internal_symbol] = market_id

    async def close(self):
        """Close exchange connections"""
        if self.exchange:
            await self.exchange.close()
        for ws in self._ws_connections.values():
            try:
                await ws.close()
            except:
                pass

    def get_exchange_symbol(self, internal_symbol: str) -> Optional[str]:
        """Get exchange-specific symbol format"""
        return self._symbol_map.get(internal_symbol)

    def get_all_symbols(self) -> List[str]:
        """Get all available symbols"""
        return list(self._symbol_map.keys())

    async def get_symbol_info(self, internal_symbol: str) -> Optional[Dict]:
        """Get symbol specifications"""
        if internal_symbol in self._symbol_info_cache:
            return self._symbol_info_cache[internal_symbol]

        exchange_symbol = self.get_exchange_symbol(internal_symbol)
        if not exchange_symbol:
            return None

        market = self.exchange.market(exchange_symbol)
        info = {
            'symbol': internal_symbol,
            'exchange_symbol': exchange_symbol,
            'base_asset': market['base'],
            'quote_asset': market['quote'],
            'tick_size': Decimal(str(market['precision']['price'])) if market['precision']['price'] else Decimal('0.01'),
            'lot_size': Decimal(str(market['precision']['amount'])) if market['precision']['amount'] else Decimal('0.001'),
            'min_notional': Decimal(str(market['limits']['cost']['min'])) if market['limits']['cost']['min'] else Decimal('5'),
            'max_leverage': market.get('leverage', 125),
            'contract_size': Decimal(str(market.get('contractSize', 1))),
        }
        self._symbol_info_cache[internal_symbol] = info
        return info

    async def fetch_candles(
        self,
        internal_symbol: str,
        timeframe: str,
        limit: int = 1000,
        since: Optional[int] = None
    ) -> List[Dict]:
        """Fetch OHLCV candles"""
        exchange_symbol = self.get_exchange_symbol(internal_symbol)
        if not exchange_symbol:
            raise ValueError(f"Symbol {internal_symbol} not found on {self.exchange_name}")

        ccxt_timeframe = self._map_timeframe(timeframe)

        try:
            candles = await self.exchange.fetch_ohlcv(
                exchange_symbol,
                timeframe=ccxt_timeframe,
                limit=limit,
                since=since
            )

            result = []
            for c in candles:
                result.append({
                    'symbol': internal_symbol,
                    'exchange': self.exchange_name,
                    'timeframe': timeframe,
                    'open_time': datetime.fromtimestamp(c[0] / 1000),
                    'open': Decimal(str(c[1])),
                    'high': Decimal(str(c[2])),
                    'low': Decimal(str(c[3])),
                    'close': Decimal(str(c[4])),
                    'volume': Decimal(str(c[5])),
                    'is_closed': True
                })
            return result

        except Exception as e:
            self.logger.error(f"Failed to fetch candles for {internal_symbol}: {e}")
            raise

    async def fetch_ticker(self, internal_symbol: str) -> Dict:
        """Fetch real-time ticker"""
        exchange_symbol = self.get_exchange_symbol(internal_symbol)
        if not exchange_symbol:
            raise ValueError(f"Symbol {internal_symbol} not found on {self.exchange_name}")

        ticker = await self.exchange.fetch_ticker(exchange_symbol)

        bid = Decimal(str(ticker['bid'])) if ticker['bid'] else Decimal('0')
        ask = Decimal(str(ticker['ask'])) if ticker['ask'] else Decimal('0')
        spread = ask - bid if bid > 0 and ask > 0 else Decimal('0')
        spread_bps = (spread / ask * 10000) if ask > 0 else Decimal('0')

        return {
            'symbol': internal_symbol,
            'exchange': self.exchange_name,
            'price': Decimal(str(ticker['last'])) if ticker['last'] else Decimal('0'),
            'bid': bid,
            'ask': ask,
            'bid_volume': Decimal(str(ticker['bidVolume'])) if ticker.get('bidVolume') else Decimal('0'),
            'ask_volume': Decimal(str(ticker['askVolume'])) if ticker.get('askVolume') else Decimal('0'),
            'volume_24h': Decimal(str(ticker['baseVolume'])) if ticker.get('baseVolume') else Decimal('0'),
            'change_24h_pct': Decimal(str(ticker['percentage'])) if ticker.get('percentage') else Decimal('0'),
            'high_24h': Decimal(str(ticker['high'])) if ticker.get('high') else Decimal('0'),
            'low_24h': Decimal(str(ticker['low'])) if ticker.get('low') else Decimal('0'),
            'timestamp': datetime.utcnow(),
            'spread_bps': spread_bps,
            'spread_pct': (spread_bps / 100) if spread_bps > 0 else Decimal('0')
        }

    async def fetch_orderbook(self, internal_symbol: str, depth: int = 20) -> Dict:
        """Fetch order book snapshot"""
        exchange_symbol = self.get_exchange_symbol(internal_symbol)
        if not exchange_symbol:
            raise ValueError(f"Symbol {internal_symbol} not found on {self.exchange_name}")

        ob = await self.exchange.fetch_order_book(exchange_symbol, limit=depth)
        return {
            'symbol': internal_symbol,
            'exchange': self.exchange_name,
            'bids': [(Decimal(str(p)), Decimal(str(v))) for p, v in ob['bids'][:depth]],
            'asks': [(Decimal(str(p)), Decimal(str(v))) for p, v in ob['asks'][:depth]],
            'timestamp': datetime.utcnow()
        }

    async def fetch_funding_rate(self, internal_symbol: str) -> Optional[Dict]:
        """Fetch current funding rate"""
        exchange_symbol = self.get_exchange_symbol(internal_symbol)
        if not exchange_symbol:
            return None

        try:
            if self.exchange_name == 'binance':
                funding = await self.exchange.fetch_funding_rate(exchange_symbol)
                return {
                    'symbol': internal_symbol,
                    'rate': Decimal(str(funding['fundingRate'])),
                    'next_funding_time': datetime.fromtimestamp(funding['nextFundingTimestamp'] / 1000)
                }
            elif self.exchange_name == 'bitget':
                funding = await self.exchange.fetch_funding_rate(exchange_symbol)
                return {
                    'symbol': internal_symbol,
                    'rate': Decimal(str(funding['fundingRate'])),
                    'next_funding_time': datetime.fromtimestamp(funding['nextFundingTime'] / 1000)
                }
        except Exception as e:
            self.logger.warning(f"Failed to fetch funding rate for {internal_symbol}: {e}")
        return None

    async def start_websocket_streams(self, symbols: List[str], timeframes: List[str], callback: Callable):
        """Start WebSocket streams for real-time data"""
        # This would connect to exchange WebSocket APIs
        # Placeholder for WebSocket implementation
        pass

    def _map_timeframe(self, timeframe: str) -> str:
        """Map internal timeframe to CCXT format"""
        mapping = {
            '3m': '3m', '5m': '5m', '15m': '15m',
            '1h': '1h', '4h': '4h', '1d': '1d'
        }
        return mapping.get(timeframe, timeframe)


class MockExchangeAdapter(ExchangeAdapter):
    """Mock exchange adapter for testing without API keys"""

    def __init__(self, exchange_name: str, config: Config):
        super().__init__(exchange_name, config)
        self.logger = get_logger(f"exchange.mock.{exchange_name}")
        self._mock_tickers = {}
        self._mock_candles = {}
        self._mock_orderbooks = {}
        self._generate_mock_data()

    def _generate_mock_data(self):
        """Generate mock market data for testing"""
        import random
        base_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT']

        for symbol in base_symbols:
            base_price = {
                'BTCUSDT': 45000,
                'ETHUSDT': 3000,
                'SOLUSDT': 145,
                'BNBUSDT': 450,
                'XRPUSDT': 0.65,
                'ADAUSDT': 0.45,
                'DOGEUSDT': 0.08,
                'AVAXUSDT': 35
            }.get(symbol, 100)

            # Generate mock ticker
            price = base_price * (1 + random.uniform(-0.05, 0.05))
            spread = price * 0.0004
            self._mock_tickers[symbol] = {
                'symbol': symbol,
                'exchange': self.exchange_name,
                'price': Decimal(str(price)),
                'bid': Decimal(str(price - base_price * 0.0002)),
                'ask': Decimal(str(price + base_price * 0.0002)),
                'bid_volume': Decimal('10'),
                'ask_volume': Decimal('10'),
                'volume_24h': Decimal(str(base_price * 100000)),
                'change_24h_pct': Decimal(str(random.uniform(-5, 5))),
                'high_24h': Decimal(str(price * 1.02)),
                'low_24h': Decimal(str(price * 0.98)),
                'timestamp': datetime.utcnow(),
                'spread_bps': Decimal('4'),
                'spread_pct': Decimal('0.004')
            }

            # Generate mock candles for each timeframe
            for tf in ['15m', '1h', '4h', '1d']:
                candles = []
                base_time = datetime.utcnow()
                tf_minutes = {'15m': 15, '1h': 60, '4h': 240, '1d': 1440}[tf]

                price = base_price
                for i in range(200):
                    tf_delta = timedelta(minutes=tf_minutes * (199 - i))
                    open_time = base_time - tf_delta
                    change = random.uniform(-0.01, 0.01)
                    open_price = price * (1 + change)
                    close_price = open_price * (1 + random.uniform(-0.005, 0.005))
                    high = max(open_price, close_price) * (1 + random.uniform(0, 0.002))
                    low = min(open_price, close_price) * (1 - random.uniform(0, 0.002))
                    volume = base_price * random.uniform(10, 1000)

                    candles.append({
                        'symbol': symbol,
                        'exchange': self.exchange_name,
                        'timeframe': tf,
                        'open_time': open_time,
                        'open': Decimal(str(open_price)),
                        'high': Decimal(str(high)),
                        'low': Decimal(str(low)),
                        'close': Decimal(str(close_price)),
                        'volume': Decimal(str(volume)),
                        'is_closed': True
                    })
                self._mock_candles[(symbol, tf)] = candles

    async def initialize(self):
        """Initialize mock adapter"""
        self._build_symbol_map()
        self.logger.info(f"Initialized mock {self.exchange_name} adapter")

    def _build_symbol_map(self):
        """Build symbol and cached specification maps for mock markets."""
        base_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT']
        for symbol in base_symbols:
            self._symbol_map[symbol] = symbol
            self._symbol_info_cache[symbol] = {
                'symbol': symbol,
                'exchange_symbol': symbol,
                'base_asset': symbol[:-4],
                'quote_asset': 'USDT',
                'tick_size': Decimal('0.01'),
                'lot_size': Decimal('0.001'),
                'min_notional': Decimal('5'),
                'max_leverage': 125,
                'contract_size': Decimal('1'),
            }

    async def close(self):
        pass

    def get_exchange_symbol(self, internal_symbol: str) -> Optional[str]:
        return internal_symbol if internal_symbol in self._mock_tickers else None

    def get_all_symbols(self) -> List[str]:
        return list(self._mock_tickers.keys())

    async def get_symbol_info(self, internal_symbol: str) -> Optional[Dict]:
        return {
            'symbol': internal_symbol,
            'exchange_symbol': internal_symbol,
            'base_asset': internal_symbol[:-4],
            'quote_asset': 'USDT',
            'tick_size': Decimal('0.01'),
            'lot_size': Decimal('0.001'),
            'min_notional': Decimal('5'),
            'max_leverage': 125,
            'contract_size': Decimal('1')
        }

    async def fetch_candles(
        self,
        internal_symbol: str,
        timeframe: str,
        limit: int = 1000,
        since: Optional[int] = None
    ) -> List[Dict]:
        key = (internal_symbol, timeframe)
        if key in self._mock_candles:
            candles = self._mock_candles[key][-limit:]
            return candles
        return []

    async def fetch_ticker(self, internal_symbol: str) -> Dict:
        if internal_symbol in self._mock_tickers:
            return self._mock_tickers[internal_symbol]
        raise ValueError(
            f"Symbol {internal_symbol} is not available in the mock market data set"
        )

    async def fetch_orderbook(self, internal_symbol: str, depth: int = 20) -> Dict:
        price = Decimal('50000')
        if internal_symbol in self._mock_tickers:
            price = self._mock_tickers[internal_symbol]['price']

        spread = price * Decimal('0.0004')
        return {
            'symbol': internal_symbol,
            'exchange': self.exchange_name,
            'bids': [(price - spread * i, Decimal('1')) for i in range(depth)],
            'asks': [(price + spread * i, Decimal('1')) for i in range(depth)],
            'timestamp': datetime.utcnow()
        }

    async def fetch_funding_rate(self, internal_symbol: str) -> Optional[Dict]:
        return {
            'symbol': internal_symbol,
            'rate': Decimal('0.0001'),
            'next_funding_time': datetime.utcnow() + timedelta(hours=8)
        }

    def _map_timeframe(self, timeframe: str) -> str:
        return timeframe


class MarketDataService:
    """Main market data service coordinating multiple exchanges"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.adapters: Dict[str, ExchangeAdapter] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._subscribers: Dict[str, List[Callable]] = {}
        self._ticker_cache: Dict[str, Dict] = {}
        self._last_update: Dict[str, datetime] = {}

    async def initialize(self):
        """Initialize market data service"""
        self.logger.info("Initializing Market Data Service...")

        # Initialize exchange adapters
        for exchange_name in ['binance', 'bitget']:
            if self.config.settings.mock_exchange:
                self.logger.info(f"Mock mode: initializing {exchange_name} adapter")
                adapter = MockExchangeAdapter(exchange_name, self.config)
            else:
                adapter = ExchangeAdapter(exchange_name, self.config)

            try:
                await adapter.initialize()
                self.adapters[exchange_name] = adapter
                self.logger.info(f"âœ“ {exchange_name} adapter initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize {exchange_name}: {e}")

        # Start background tasks
        self._running = True
        self._start_background_tasks()

        self.logger.info("Market Data Service initialized successfully")

    def _start_background_tasks(self):
        """Start background data collection tasks"""
        self._tasks.append(asyncio.create_task(self._ticker_update_loop()))
        self._tasks.append(asyncio.create_task(self._candle_update_loop()))
        self._tasks.append(asyncio.create_task(self._funding_update_loop()))

    async def _ticker_update_loop(self):
        """Background loop to update tickers"""
        while self._running:
            try:
                await self._update_all_tickers()
            except Exception as e:
                self.logger.error(f"Error in ticker update loop: {e}")
            await asyncio.sleep(5)  # Update tickers every 5 seconds

    async def _candle_update_loop(self):
        """Background loop to update candles"""
        while self._running:
            try:
                await self._update_all_candles()
            except Exception as e:
                self.logger.error(f"Error in candle update loop: {e}")
            await asyncio.sleep(self.config.settings.market_data_interval)

    async def _funding_update_loop(self):
        """Background loop to update funding rates"""
        while self._running:
            try:
                await self._update_all_funding_rates()
            except Exception as e:
                self.logger.error(f"Error in funding update loop: {e}")
            await asyncio.sleep(3600)  # Update funding rates hourly

    async def _update_all_tickers(self):
        """Update tickers for all active symbols"""
        for exchange_name, adapter in self.adapters.items():
            for symbol in list(adapter._symbol_map.keys())[:100]:  # Limit to top 100
                try:
                    ticker = await adapter.fetch_ticker(symbol)
                    cache_key = f"{adapter.exchange_name}:{symbol}"
                    self._ticker_cache[cache_key] = ticker
                    self._last_update[cache_key] = datetime.utcnow()

                    # Notify subscribers
                    await self._notify_subscribers(f"ticker:{symbol}", ticker)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch ticker for {symbol}: {e}")
            await asyncio.sleep(0.01)  # Small delay between symbols

    async def _update_all_candles(self):
        """Update candles for all active symbols"""
        for exchange_name, adapter in self.adapters.items():
            for symbol in list(adapter._symbol_map.keys())[:50]:
                try:
                    # Update 1h candles
                    candles = await adapter.fetch_candles(symbol, '1h', limit=2)
                    if candles:
                        cache_key = f"{adapter.exchange_name}:{symbol}:1h"
                        self._ticker_cache[cache_key] = candles
                except Exception as e:
                    self.logger.warning(f"Failed to fetch candles for {symbol}: {e}")
            await asyncio.sleep(0.01)

    async def _update_all_funding_rates(self):
        """Update funding rates for all symbols"""
        for adapter in self.adapters.values():
            for symbol in list(adapter._symbol_map.keys())[:50]:
                try:
                    funding = await adapter.fetch_funding_rate(symbol)
                    if funding:
                        await self._notify_subscribers(f"funding:{symbol}", funding)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch funding for {symbol}: {e}")

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to real-time data updates"""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback: Callable):
        """Unsubscribe from real-time data updates"""
        if channel in self._subscribers:
            self._subscribers[channel].remove(callback)

    async def _notify_subscribers(self, channel: str, data: Any):
        """Notify all subscribers of a channel"""
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                try:
                    await callback(data)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber on {channel}: {e}")

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
        exchange: Optional[str] = None
    ) -> List[Dict]:
        """Get candles from exchange"""
        if exchange and exchange in self.adapters:
            return await self.adapters[exchange].fetch_candles(symbol, timeframe, limit)
        elif self.adapters:
            adapter = next(iter(self.adapters.values()))
            return await adapter.fetch_candles(symbol, timeframe, limit)
        return []

    async def get_ticker(self, symbol: str, exchange: Optional[str] = None) -> Optional[Dict]:
        """Get real-time ticker"""
        if exchange and exchange in self.adapters:
            return await self.adapters[exchange].fetch_ticker(symbol)
        elif self.adapters:
            adapter = next(iter(self.adapters.values()))
            return await adapter.fetch_ticker(symbol)
        return None

    async def get_latest_ticker(self, symbol: str, exchange: Optional[str] = None) -> Optional[Dict]:
        """Get cached ticker"""
        if exchange:
            cache_key = f"{exchange}:{symbol}"
            return self._ticker_cache.get(cache_key)

        # Search all exchanges
        for adapter in self.adapters.values():
            cache_key = f"{adapter.exchange_name}:{symbol}"
            if cache_key in self._ticker_cache:
                return self._ticker_cache[cache_key]
        return None

    async def get_orderbook(self, symbol: str, depth: int = 20, exchange: Optional[str] = None) -> Optional[Dict]:
        """Get order book snapshot"""
        if exchange and exchange in self.adapters:
            return await self.adapters[exchange].fetch_orderbook(symbol, depth)
        elif self.adapters:
            adapter = next(iter(self.adapters.values()))
            return await adapter.fetch_orderbook(symbol, depth)
        return None

    async def get_funding_rate(self, symbol: str, exchange: Optional[str] = None) -> Optional[Dict]:
        """Get funding rate"""
        if exchange and exchange in self.adapters:
            return await self.adapters[exchange].fetch_funding_rate(symbol)
        elif self.adapters:
            adapter = next(iter(self.adapters.values()))
            return await adapter.fetch_funding_rate(symbol)
        return None

    async def get_eligible_symbols(self) -> List[str]:
        """Get list of eligible trading symbols"""
        symbols = set()
        for adapter in self.adapters.values():
            for symbol, info in adapter._symbol_info_cache.items():
                info = await adapter.get_symbol_info(symbol)
                if info and info['min_notional'] <= 100:
                    symbols.add(symbol)
        return sorted(symbols)

    async def get_market_overview(self) -> Dict:
        """Get market overview statistics"""
        total_volume = Decimal('0')
        total_oi = Decimal('0')
        funding_sum = Decimal('0')
        funding_count = 0

        for adapter in self.adapters.values():
            for symbol in list(adapter._symbol_map.keys())[:50]:
                try:
                    ticker = await adapter.fetch_ticker(symbol)
                    total_volume += ticker.get('volume_24h', Decimal('0'))

                    funding = await adapter.fetch_funding_rate(symbol)
                    if funding:
                        funding_sum += funding.get('rate', Decimal('0'))
                        funding_count += 1
                except:
                    pass

        return {
            'total_volume_24h': float(total_volume),
            'avg_funding_rate': float(funding_sum / funding_count) if funding_count > 0 else 0,
            'symbols_tracked': sum(len(a._symbol_map) for a in self.adapters.values()),
            'exchanges_connected': list(self.adapters.keys()),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def shutdown(self):
        """Shutdown market data service"""
        self.logger.info("Shutting down Market Data Service...")
        self._running = False

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

        for adapter in self.adapters.values():
            await adapter.close()

        self.logger.info("Market Data Service shut down complete")


async def create_market_data_service(config: Config) -> MarketDataService:
    """Create and initialize market data service"""
    service = MarketDataService(config)
    await service.initialize()
    return service


