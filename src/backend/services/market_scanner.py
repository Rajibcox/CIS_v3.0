"""
Market Scanner Service for QUANTUM TRADER V1
Scans markets for trading opportunities using configurable filters
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import ccxt.async_support as ccxt
import numpy as np
from sqlalchemy.orm import Session

from src.backend.models.database import (
    Exchange, Symbol, MarketCandle, MarketRegime
)
from src.backend.services.market_data_service import MarketDataService, TickerData, CandleData
from src.backend.services.historical_data_service import HistoricalDataService
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger, log_service_event


logger = get_logger(__name__)


class ScanFilter(Enum):
    """Available scan filters"""
    VOLUME = "volume"
    SPREAD = "spread"
    VOLATILITY = "volatility"
    TREND = "trend"
    REGIME = "regime"
    BTC_CORRELATION = "btc_correlation"
    MOMENTUM = "momentum"
    LIQUIDITY = "liquidity"
    FUNDING = "funding"
    OPEN_INTEREST = "open_interest"


@dataclass
class ScanConfig:
    """Configuration for market scan"""
    # Exchange filters
    exchanges: List[str] = field(default_factory=lambda: ["binance", "bitget"])

    # Symbol filters
    min_volume_24h: float = 10_000_000  # $10M
    max_spread_bps: float = 50  # 0.5%
    min_history_days: int = 30

    # Volatility filters
    min_atr_pct: float = 0.5  # 0.5%
    max_atr_pct: float = 10.0  # 10%

    # Trend filters
    min_adx: float = 20.0
    trend_lookback: int = 100

    # Regime filters
    allowed_regimes: List[str] = field(default_factory=lambda: ["trending", "breakout", "ranging"])

    # BTC correlation filters
    min_btc_correlation: float = -0.5
    max_btc_correlation: float = 1.0

    # Momentum filters
    min_momentum_score: float = 0.0

    # Volume filters
    min_volume_ratio: float = 1.0  # vs 20-period average

    # Funding rate filters
    max_funding_rate: float = 0.01  # 1%

    # Open interest filters
    min_oi_change_24h: float = -50.0  # %

    # Output limits
    max_results: int = 100
    min_signal_score: float = 0.7


@dataclass
class ScanResult:
    """Result of a market scan"""
    symbol: str
    exchange: str
    price: Decimal
    change_24h_pct: float
    volume_24h: Decimal
    volume_change_24h_pct: float
    spread_bps: float
    atr_pct: float
    adx: float
    rsi: float
    volume_ratio: float
    trend_strength: float
    btc_correlation: float
    funding_rate: float
    oi_change_24h_pct: float
    regime: str
    signal_score: float
    signal_direction: str  # LONG or SHORT
    strategy_match: str
    timestamp: datetime
    filters_passed: Dict[str, bool]


@dataclass
class MarketSnapshot:
    """Complete market snapshot for a symbol"""
    symbol: str
    exchange: str
    ticker: Any  # TickerData
    candles_15m: List
    candles_1h: List
    candles_4h: List
    candles_1d: List
    orderbook: Any
    funding_rate: Optional[Dict]
    regime: str
    btc_correlation: float
    indicators: Dict[str, float]


class MarketScanner:
    """Main market scanner for finding trading opportunities"""

    def __init__(
        self,
        config: Config,
        market_data_service: "MarketDataService",
        historical_data_service: "HistoricalDataService"
    ):
        self.config = config
        self.market_data_service = market_data_service
        self.historical_data_service = historical_data_service
        self.logger = logging.getLogger(__name__)
        self.scan_config = ScanConfig()
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._last_scan_results: List[ScanResult] = []
        self._scan_callbacks: List[Callable] = []

    def configure(self, scan_config: ScanConfig):
        """Update scan configuration"""
        self.scan_config = scan_config

    def register_callback(self, callback: Callable):
        """Register callback for scan completion"""
        self._scan_callbacks.append(callback)

    async def start(self):
        """Start periodic scanning"""
        if self._running:
            return
        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info("Market Scanner started")

    async def stop(self):
        """Stop periodic scanning"""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        logger.info("Market Scanner stopped")

    async def _scan_loop(self):
        """Main scanning loop"""
        while True:
            try:
                await asyncio.sleep(self.config.settings.market_data_interval)
                if not self._running:
                    break
                await self.run_scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def run_scan(self, config: Optional[ScanConfig] = None) -> List[ScanResult]:
        """Run a single market scan"""
        if config:
            self.scan_config = config

        logger.info("Starting market scan...")
        start_time = datetime.utcnow()

        try:
            # Get all eligible symbols
            symbols = await self._get_eligible_symbols()

            # Build market snapshots
            snapshots = await self._build_market_snapshots()

            # Run filters
            results = await self._run_filters(snapshots)

            # Sort by signal score
            results.sort(key=lambda x: x.signal_score, reverse=True)

            # Limit results
            results = results[:self.scan_config.max_results]

            self._last_scan_results = results
            scan_duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(f"Scan completed in {scan_duration:.1f}s: {len(results)} opportunities found")

            # Notify callbacks
            for callback in self._scan_callbacks:
                try:
                    await callback(results)
                except Exception as e:
                    logger.error(f"Error in scan callback: {e}")

            return results

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return []

    async def _get_eligible_symbols(self) -> List[str]:
        """Get list of symbols eligible for scanning"""
        symbols = set()

        for exchange_name in self.scan_config.exchanges:
            adapter = self.market_data_service.adapters.get(exchange_name)
            if not adapter:
                continue

            for symbol, info in adapter._symbol_info_cache.items():
                # Check basic filters
                if info.get('min_notional', 0) > self.scan_config.min_volume_24h:
                    continue
                symbols.add(symbol)

        # Also get from market data service
        eligible = await self.market_data_service.get_eligible_symbols()
        symbols.update(eligible)

        return list(symbols)

    async def _build_market_snapshots(self) -> Dict[str, MarketSnapshot]:
        """Build comprehensive market snapshots for all symbols"""
        snapshots = {}

        for exchange_name in self.scan_config.exchanges:
            adapter = self.market_data_service.adapters.get(exchange_name)
            if not adapter:
                continue

            for symbol in adapter._symbol_map.keys():
                try:
                    # Normalize adapter dictionaries into the dataclasses
                    # consumed by the scanner's indicator and filter pipeline.
                    ticker_data = await adapter.fetch_ticker(symbol)
                    if not ticker_data:
                        continue
                    ticker = (
                        TickerData(**ticker_data)
                        if isinstance(ticker_data, dict)
                        else ticker_data
                    )

                    # Get candles for multiple timeframes and normalize them.
                    candles_15m = await adapter.fetch_candles(symbol, '15m', limit=200)
                    candles_1h = await adapter.fetch_candles(symbol, '1h', limit=200)
                    candles_4h = await adapter.fetch_candles(symbol, '4h', limit=200)
                    candles_1d = await adapter.fetch_candles(symbol, '1d', limit=200)
                    candles_15m = [
                        CandleData(**c) if isinstance(c, dict) else c for c in candles_15m
                    ]
                    candles_1h = [
                        CandleData(**c) if isinstance(c, dict) else c for c in candles_1h
                    ]
                    candles_4h = [
                        CandleData(**c) if isinstance(c, dict) else c for c in candles_4h
                    ]
                    candles_1d = [
                        CandleData(**c) if isinstance(c, dict) else c for c in candles_1d
                    ]

                    # Get orderbook
                    orderbook = await adapter.fetch_orderbook(symbol, depth=20)

                    # Get funding rate
                    funding = await adapter.fetch_funding_rate(symbol)

                    # Calculate indicators
                    indicators = self._calculate_indicators(
                        candles_15m, candles_1h, candles_4h, candles_1d
                    )

                    # Determine regime
                    regime = self._detect_regime(candles_1h, candles_4h)

                    # Get BTC correlation
                    btc_correlation = await self._calculate_btc_correlation(symbol)

                    snapshot = MarketSnapshot(
                        symbol=symbol,
                        exchange=exchange_name,
                        ticker=ticker,
                        candles_15m=candles_15m,
                        candles_1h=candles_1h,
                        candles_4h=candles_4h,
                        candles_1d=candles_1d,
                        orderbook=orderbook,
                        funding_rate=funding,
                        regime=regime,
                        btc_correlation=btc_correlation,
                        indicators=indicators
                    )

                    snapshots[f"{exchange_name}:{symbol}"] = snapshot

                except Exception as e:
                    logger.warning(f"Failed to build snapshot for {symbol} on {exchange_name}: {e}")

        return snapshots

    def _calculate_indicators(
        self,
        candles_15m: List,
        candles_1h: List,
        candles_4h: List,
        candles_1d: List
    ) -> Dict[str, float]:
        """Calculate technical indicators from candle data"""
        indicators = {}

        # Use 1h candles as primary
        if len(candles_1h) < 50:
            return indicators

        closes = [float(c.close) for c in candles_1h]
        highs = [float(c.high) for c in candles_1h]
        lows = [float(c.low) for c in candles_1h]
        volumes = [float(c.volume) for c in candles_1h]

        # RSI
        indicators['rsi'] = self._calculate_rsi(closes, 14)

        # EMA
        indicators['ema_9'] = self._calculate_ema(closes, 9)[-1]
        indicators['ema_21'] = self._calculate_ema(closes, 21)[-1]
        indicators['ema_50'] = self._calculate_ema(closes, 50)[-1] if len(closes) >= 50 else 0

        # MACD
        macd, signal, hist = self._calculate_macd(closes)
        indicators['macd'] = macd
        indicators['macd_signal'] = signal
        indicators['macd_hist'] = hist

        # ATR
        indicators['atr'] = self._calculate_atr(highs, lows, closes, 14)
        indicators['atr_pct'] = indicators['atr'] / closes[-1] * 100

        # ADX
        indicators['adx'] = self._calculate_adx(highs, lows, closes, 14)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger(closes, 20, 2)
        indicators['bb_upper'] = bb_upper
        indicators['bb_middle'] = bb_middle
        indicators['bb_lower'] = bb_lower
        indicators['bb_width'] = (bb_upper - bb_lower) / bb_middle * 100

        # Volume indicators
        indicators['volume_sma'] = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
        indicators['volume_ratio'] = volumes[-1] / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1.0

        # VWAP
        indicators['vwap'] = self._calculate_vwap(closes, volumes)

        return indicators

    def _detect_regime(self, candles_1h: List, candles_4h: List) -> str:
        """Detect market regime"""
        if len(candles_1h) < 50 or len(candles_4h) < 20:
            return "unknown"

        closes_1h = [float(c.close) for c in candles_1h]
        closes_4h = [float(c.close) for c in candles_4h]

        # Calculate trend
        ema_50_1h = self._calculate_ema(closes_1h, 50)[-1]
        ema_200_1h = self._calculate_ema(closes_1h, 200)[-1] if len(closes_1h) >= 200 else closes_1h[-1]

        ema_50_4h = self._calculate_ema(closes_4h, 50)[-1] if len(closes_4h) >= 50 else closes_4h[-1]

        current_price = closes_1h[-1]

        # Trend detection
        trend_1h = "up" if current_price > ema_50_1h else "down"
        trend_4h = "up" if current_price > ema_50_4h else "down"

        # ADX for trend strength
        highs = [float(c.high) for c in candles_1h[-14:]]
        lows = [float(c.low) for c in candles_1h[-14:]]
        closes = [float(c.close) for c in candles_1h[-14:]]
        adx = self._calculate_adx(highs, lows, closes, 14)

        # Regime classification
        if adx > 25:
            if trend_1h == trend_4h:
                return "trending"
            else:
                return "breakout"
        elif adx < 15:
            return "ranging"
        else:
            return "volatile"

    async def _calculate_btc_correlation(self, symbol: str) -> float:
        """Calculate correlation with BTC"""
        if symbol == "BTCUSDT":
            return 1.0

        try:
            # Get BTC and symbol candles
            btc_candles = await self.market_data_service.get_candles("BTCUSDT", "1h", limit=100)
            sym_candles = await self.market_data_service.get_candles(symbol, "1h", limit=100)

            if not btc_candles or not sym_candles or len(btc_candles) < 20 or len(sym_candles) < 20:
                return 0.0

            btc_returns = np.diff([
                float(c.get("close") if isinstance(c, dict) else c.close)
                for c in btc_candles[-20:]
            ])
            sym_returns = np.diff([
                float(c.get("close") if isinstance(c, dict) else c.close)
                for c in sym_candles[-20:]
            ])

            if len(btc_returns) > 10 and len(sym_returns) > 10:
                correlation = np.corrcoef(btc_returns, sym_returns)[0, 1]
                return float(correlation) if not np.isnan(correlation) else 0.0

        except Exception as e:
            logger.warning(f"Failed to calculate BTC correlation for {symbol}: {e}")

        return 0.0

    def _run_filters(self, snapshots: Dict[str, MarketSnapshot]) -> List[ScanResult]:
        """Run all configured filters on snapshots"""
        results = []

        for key, snapshot in snapshots.items():
            try:
                # Run each filter
                filters_passed = {}

                # Volume filter
                filters_passed['volume'] = snapshot.ticker.volume_24h >= self.scan_config.min_volume_24h

                # Spread filter
                filters_passed['spread'] = snapshot.ticker.spread_bps <= self.scan_config.max_spread_bps

                # Volatility filter
                atr_pct = snapshot.indicators.get('atr_pct', 0)
                filters_passed['volatility'] = (
                    self.scan_config.min_atr_pct <= atr_pct <= self.scan_config.max_atr_pct
                )

                # Trend filter
                adx = snapshot.indicators.get('adx', 0)
                filters_passed['trend'] = adx >= self.scan_config.min_adx

                # Regime filter
                filters_passed['regime'] = snapshot.regime in self.scan_config.allowed_regimes

                # BTC correlation filter
                btc_corr = snapshot.btc_correlation
                filters_passed['btc_correlation'] = (
                    self.scan_config.min_btc_correlation <= btc_corr <= self.scan_config.max_btc_correlation
                )

                # Momentum filter
                rsi = snapshot.indicators.get('rsi', 50)
                macd = snapshot.indicators.get('macd', 0)
                macd_signal = snapshot.indicators.get('macd_signal', 0)
                momentum_score = (rsi - 50) / 50 + (1 if macd > macd_signal else -1)
                filters_passed['momentum'] = momentum_score >= self.scan_config.min_momentum_score

                # Volume filter
                volume_ratio = snapshot.indicators.get('volume_ratio', 1.0)
                filters_passed['volume_ratio'] = volume_ratio >= self.scan_config.min_volume_ratio

                # Funding filter
                funding = snapshot.funding_rate.get('rate', 0) if snapshot.funding_rate else 0
                filters_passed['funding'] = abs(funding) <= self.scan_config.max_funding_rate

                # Calculate signal score
                signal_score = sum(filters_passed.values()) / len(filters_passed) * 100

                # Determine direction
                direction = "LONG" if snapshot.ticker.price > snapshot.indicators.get('vwap', 0) else "SHORT"
                if snapshot.indicators.get('macd', 0) < snapshot.indicators.get('macd_signal', 0):
                    direction = "SHORT"

                # Strategy match
                strategy_match = self._identify_strategy(snapshot)

                if signal_score >= self.scan_config.min_signal_score:
                    result = ScanResult(
                        symbol=snapshot.symbol,
                        exchange=snapshot.exchange,
                        price=snapshot.ticker.price,
                        change_24h_pct=snapshot.ticker.change_24h_pct,
                        volume_24h=snapshot.ticker.volume_24h,
                        volume_change_24h_pct=snapshot.ticker.volume_change_24h_pct,
                        spread_bps=snapshot.ticker.spread_bps,
                        atr_pct=snapshot.indicators.get('atr_pct', 0),
                        adx=snapshot.indicators.get('adx', 0),
                        rsi=snapshot.indicators.get('rsi', 50),
                        volume_ratio=snapshot.indicators.get('volume_ratio', 1.0),
                        trend_strength=snapshot.indicators.get('adx', 0),
                        btc_correlation=snapshot.btc_correlation,
                        funding_rate=snapshot.funding_rate.get('rate', 0) if snapshot.funding_rate else 0,
                        oi_change_24h_pct=0,  # Would need OI data
                        regime=snapshot.regime,
                        signal_score=signal_score,
                        signal_direction=direction,
                        strategy_match=strategy_match,
                        timestamp=datetime.utcnow(),
                        filters_passed=filters_passed
                    )
                    yield result

            except Exception as e:
                logger.warning(f"Error filtering {snapshot.symbol}: {e}")

    def _identify_strategy(self, snapshot: MarketSnapshot) -> str:
        """Identify which strategy matches this snapshot"""
        rsi = snapshot.indicators.get('rsi', 50)
        adx = snapshot.indicators.get('adx', 0)
        macd = snapshot.indicators.get('macd', 0)
        macd_signal = snapshot.indicators.get('macd_signal', 0)

        if adx > 25 and snapshot.regime == "trending":
            return "Trend Following"
        elif adx < 15 and snapshot.regime == "ranging":
            return "Mean Reversion"
        elif snapshot.regime == "breakout" and snapshot.indicators.get('volume_ratio', 1) > 1.5:
            return "Breakout"
        elif rsi < 30 or rsi > 70:
            return "Mean Reversion"
        elif macd > macd_signal and snapshot.indicators.get('ema_9', 0) > snapshot.indicators.get('ema_21', 0):
            return "Momentum Scalping"
        else:
            return "Volume Expansion"

    # Technical indicator calculations
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_ema(self, values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return values

        ema = []
        multiplier = 2 / (period + 1)
        ema.append(values[0])

        for i in range(1, len(values)):
            ema.append((values[i] - ema[-1]) * multiplier + ema[-1])

        return ema

    def _calculate_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        if len(closes) < slow:
            return 0.0, 0.0, 0.0

        ema_fast = self._calculate_ema(closes, fast)[-1]
        ema_slow = self._calculate_ema(closes, slow)[-1]
        macd = ema_fast - ema_slow

        # Signal line would need historical MACD values
        return macd, 0.0, 0.0

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(highs) < period + 1:
            return 0.0

        tr_values = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)

        return np.mean(tr_values[-period:])

    def _calculate_adx(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(highs) < period + 1:
            return 0.0

        plus_dm = []
        minus_dm = []
        tr_values = []

        for i in range(1, len(highs)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]

            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)

            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)

        if len(tr_values) < period:
            return 0.0

        atr = np.mean(tr_values[-period:])
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr if atr > 0 else 0

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return dx

    def _calculate_bollinger(self, closes: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1]

        recent = closes[-period:]
        middle = np.mean(recent)
        std = np.std(recent)
        upper = middle + std_dev * std
        lower = middle - std_dev * std

        return upper, middle, lower

    def _calculate_vwap(self, closes: List[float], volumes: List[float]) -> float:
        if len(closes) != len(volumes) or len(closes) == 0:
            return closes[-1] if closes else 0.0

        total_pv = sum(c * v for c, v in zip(closes, volumes))
        total_v = sum(volumes)

        return total_pv / total_v if total_v > 0 else closes[-1]


# Factory function
async def create_market_scanner(
    config: Config,
    market_data_service: MarketDataService,
    historical_data_service: HistoricalDataService
) -> MarketScanner:
    """Create and initialize market scanner"""
    scanner = MarketScanner(config, market_data_service, historical_data_service)
    await scanner.start()
    return scanner