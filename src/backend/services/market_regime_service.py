"""
Market Regime Detection Service for QUANTUM TRADER V1
Identifies and classifies market regimes for improved strategy selection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import deque

from src.backend.models.database import MarketRegime
from src.backend.services.market_data_service import MarketDataService, CandleData
from src.backend.services.historical_data_service import HistoricalDataService
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    REVERSAL_UP = "reversal_up"
    REVERSAL_DOWN = "reversal_down"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    UNKNOWN = "unknown"


@dataclass
class RegimeState:
    """Current regime state for a symbol"""
    symbol: str
    regime: RegimeType
    confidence: float  # 0-100
    trend_direction: str  # up, down, sideways
    trend_strength: float  # 0-100
    volatility_level: str  # low, normal, high
    volume_profile: str  # low, normal, high
    momentum: float  # -100 to 100
    timestamp: datetime
    supporting_factors: List[str]


@dataclass
class RegimeTransition:
    """Regime transition event"""
    symbol: str
    from_regime: RegimeType
    to_regime: RegimeType
    confidence: float
    timestamp: datetime
    trigger: str


class RegimeDetector:
    """Detects market regime for a single symbol"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._regime_history: Dict[str, deque] = {}

    def detect_regime(
        self,
        symbol: str,
        candles_15m: List,
        candles_1h: List,
        candles_4h: List,
        candles_1d: List,
        volume_24h: Decimal,
        funding_rate: Optional[Decimal] = None
    ) -> RegimeState:
        """Detect current market regime"""

        # Need sufficient data
        if len(candles_1h) < 50 or len(candles_4h) < 20:
            return RegimeState(
                symbol=symbol,
                regime=RegimeType.UNKNOWN,
                confidence=0,
                trend_direction="unknown",
                trend_strength=0,
                volatility_level="unknown",
                volume_profile="unknown",
                momentum=0,
                timestamp=datetime.utcnow(),
                supporting_factors=["Insufficient data"]
            )

        # Extract price data
        closes_15m = [float(c.close) for c in candles_15m]
        closes_1h = [float(c.close) for c in candles_1h]
        closes_4h = [float(c.close) for c in candles_4h]
        closes_1d = [float(c.close) for c in candles_1d]

        highs_1h = [float(c.high) for c in candles_1h]
        lows_1h = [float(c.low) for c in candles_1h]
        volumes_1h = [float(c.volume) for c in candles_1h]

        current_price = closes_1h[-1]

        # Calculate key metrics
        factors = []

        # 1. Multi-timeframe trend analysis
        trend_15m = self._get_trend(closes_15m[-20:])
        trend_1h = self._get_trend(closes_1h[-50:])
        trend_4h = self._get_trend(closes_4h[-50:])
        trend_1d = self._get_trend(closes_1d[-100:])

        # Trend alignment
        trend_alignment = sum(1 for t in [trend_15m, trend_1h, trend_4h, trend_1d] if t > 0) - \
                         sum(1 for t in [trend_15m, trend_1h, trend_4h, trend_1d] if t < 0)

        # 2. Moving averages
        ema_9 = self._ema(closes_1h, 9)[-1]
        ema_21 = self._ema(closes_1h, 21)[-1]
        ema_50 = self._ema(closes_1h, 50)[-1] if len(closes_1h) >= 50 else current_price
        ema_200 = self._ema(closes_1h, 200)[-1] if len(closes_1h) >= 200 else current_price

        # Price vs MAs
        price_vs_ema9 = (current_price - ema_9) / current_price * 100
        price_vs_ema21 = (current_price - ema_21) / current_price * 100
        price_vs_ema50 = (current_price - ema_50) / current_price * 100

        # MA alignment
        ma_alignment = 0
        if current_price > ema_9 > ema_21 > ema_50 > ema_200:
            ma_alignment = 1  # Strong uptrend
        elif current_price < ema_9 < ema_21 < ema_50 < ema_200:
            ma_alignment = -1  # Strong downtrend

        # 3. ADX for trend strength
        adx = self._calculate_adx(
            [float(c.high) for c in candles_1h[-14:]],
            [float(c.low) for c in candles_1h[-14:]],
            [float(c.close) for c in candles_1h[-14:]],
            14
        )

        # 4. Volatility
        atr = self._atr(
            [float(c.high) for c in candles_1h[-14:]],
            [float(c.low) for c in candles_1h[-14:]],
            [float(c.close) for c in candles_1h[-14:]],
            14
        )
        atr_pct = atr / current_price * 100 if current_price > 0 else 0

        # Volatility percentile
        atr_history = []
        for i in range(14, min(len(candles_1h), 100)):
            atr_val = self._atr(
                [float(c.high) for c in candles_1h[i-14:i]],
                [float(c.low) for c in candles_1h[i-14:i]],
                [float(c.close) for c in candles_1h[i-14:i]],
                14
            )
            # CandleData.close is Decimal while ATR is a float. Keep indicator math
            # consistently in float space to avoid float/Decimal TypeError.
            previous_close = float(candles_1h[i].close)
            atr_history.append(atr_val / previous_close * 100 if previous_close > 0 else 0.0)

        vol_percentile = self._percentile(atr_pct, atr_history) if atr_history else 50

        # 5. Volume analysis
        volume_sma = np.mean([float(c.volume) for c in candles_1h[-20:]]) if len(candles_1h) >= 20 else 0
        current_volume = float(candles_1h[-1].volume) if candles_1h else 0
        volume_ratio = current_volume / volume_sma if volume_sma > 0 else 1

        # 6. RSI
        rsi = self._rsi([float(c.close) for c in candles_1h], 14)

        # 7. MACD
        macd, signal, hist = self._macd([float(c.close) for c in candles_1h])

        # 8. Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._bollinger([float(c.close) for c in candles_1h], 20, 2)
        bb_width = (bb_upper - bb_lower) / bb_middle * 100 if bb_middle > 0 else 0
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

        # 9. Volume profile
        volume_trend = self._volume_trend([float(c.volume) for c in candles_1h[-20:]])

        # 10. Higher timeframe context
        ht_trend = "up" if candles_4h[-1].close > candles_4h[-50].close else "down" if candles_4h[-1].close < candles_4h[-50].close else "sideways"

        # === REGIME CLASSIFICATION ===
        regime = RegimeType.UNKNOWN
        confidence = 0
        factors = []

        # Strong trending conditions
        if adx > 25:
            trend_up = (current_price > self._ema([float(c.close) for c in candles_1h], 21)[-1] >
                       self._ema([float(c.close) for c in candles_1h], 50)[-1] if len(candles_1h) >= 50 else False)

            if trend_up and adx > 30:
                regime = RegimeType.TRENDING_UP
                confidence = min(90, 50 + adx)
                factors.append(f"Strong uptrend (ADX={adx:.1f})")
            elif not trend_up and adx > 30:
                regime = RegimeType.TRENDING_DOWN
                confidence = min(90, 50 + adx)
                factors.append(f"Strong downtrend (ADX={adx:.1f})")
            elif trend_up:
                regime = RegimeType.TRENDING_UP
                confidence = min(80, 40 + adx)
                factors.append(f"Uptrend (ADX={adx:.1f})")
            else:
                regime = RegimeType.TRENDING_DOWN
                confidence = min(80, 40 + adx)
                factors.append(f"Downtrend (ADX={adx:.1f})")

        # Breakout conditions
        elif bb_width < 5 and volume_ratio > 1.5:
            # Squeeze + volume expansion = potential breakout
            if current_price > bb_middle:
                regime = RegimeType.BREAKOUT_UP
                factors.append("Bollinger squeeze + volume expansion (bullish)")
            else:
                regime = RegimeType.BREAKOUT_DOWN
                factors.append("Bollinger squeeze + volume expansion (bearish)")
            confidence = 70

        # Low volatility ranging
        elif adx < 15 and bb_width < 10:
            regime = RegimeType.RANGING
            confidence = 75
            factors.append(f"Low ADX ({adx:.1f}) + narrow Bollinger Bands")

        # High volatility
        elif vol_percentile > 80:
            regime = RegimeType.VOLATILE
            confidence = 65
            factors.append(f"High volatility (percentile={vol_percentile:.0f})")

        # Low volatility
        elif vol_percentile < 20:
            regime = RegimeType.LOW_VOLATILITY
            confidence = 60
            factors.append(f"Low volatility (percentile={vol_percentile:.0f})")

        # Reversal detection
        elif rsi > 75 and macd < signal and current_price > bb_upper:
            regime = RegimeType.REVERSAL_DOWN
            confidence = 65
            factors.append("Overbought + MACD bearish cross + above BB upper")

        elif rsi < 25 and macd > signal and current_price < bb_lower:
            regime = RegimeType.REVERSAL_UP
            confidence = 65
            factors.append("Oversold + MACD bullish cross + below BB lower")

        # Accumulation/Distribution
        elif volume_ratio > 2 and abs(current_price - bb_middle) / bb_middle < 0.02:
            if rsi < 40:
                regime = RegimeType.ACCUMULATION
                factors.append("High volume + near middle BB + oversold")
            elif rsi > 60:
                regime = RegimeType.DISTRIBUTION
                factors.append("High volume + near middle BB + overbought")
            confidence = 60

        else:
            regime = RegimeType.UNKNOWN
            confidence = 30
            factors.append("Mixed signals")

        # Determine trend direction
        if regime in [RegimeType.TRENDING_UP, RegimeType.BREAKOUT_UP, RegimeType.REVERSAL_UP, RegimeType.ACCUMULATION]:
            trend_direction = "up"
        elif regime in [RegimeType.TRENDING_DOWN, RegimeType.BREAKOUT_DOWN, RegimeType.REVERSAL_DOWN, RegimeType.DISTRIBUTION]:
            trend_direction = "down"
        else:
            trend_direction = "sideways"

        # Volatility level
        if vol_percentile > 75:
            volatility_level = "high"
        elif vol_percentile < 25:
            volatility_level = "low"
        else:
            volatility_level = "normal"

        # Volume profile
        if volume_ratio > 1.5:
            volume_profile = "high"
        elif volume_ratio < 0.7:
            volume_profile = "low"
        else:
            volume_profile = "normal"

        # Momentum score
        momentum = (rsi - 50) * 2  # -100 to 100
        if macd > 0:
            momentum += 10
        if macd < 0:
            momentum -= 10
        momentum = max(-100, min(100, momentum))

        # Trend strength
        trend_strength = min(100, adx * 2)

        # Store regime history
        if symbol not in self._regime_history:
            self._regime_history[symbol] = deque(maxlen=100)
        self._regime_history[symbol].append({
            'regime': regime,
            'timestamp': datetime.utcnow(),
            'price': current_price
        })

        return RegimeState(
            symbol=symbol,
            regime=regime,
            confidence=confidence,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            volatility_level=volatility_level,
            volume_profile=volume_profile,
            momentum=momentum,
            timestamp=datetime.utcnow(),
            supporting_factors=factors
        )

    # Technical indicator helpers
    def _ema(self, values: List[float], period: int) -> List[float]:
        if len(values) < period:
            return values
        ema = [values[0]]
        multiplier = 2 / (period + 1)
        for i in range(1, len(values)):
            ema.append((values[i] - ema[-1]) * multiplier + ema[-1])
        return ema

    def _rsi(self, closes: List[float], period: int = 14) -> float:
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

    def _macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        if len(closes) < slow:
            return 0.0, 0.0, 0.0
        ema_fast = self._ema(closes, fast)[-1]
        ema_slow = self._ema(closes, slow)[-1]
        macd = ema_fast - ema_slow
        return macd, 0.0, 0.0

    def _bollinger(self, closes: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1]
        recent = closes[-period:]
        middle = np.mean(recent)
        std = np.std(recent)
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower

    def _atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
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
        plus_di = 100 * np.mean([max(0, highs[i] - highs[i-1]) if highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0 for i in range(1, len(highs))][-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean([max(0, lows[i-1] - lows[i]) if lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0 for i in range(1, len(highs))][-period:]) / atr if atr > 0 else 0
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return dx

    def _percentile(self, value: float, history: List[float]) -> float:
        if not history:
            return 50
        sorted_hist = sorted(history)
        count = sum(1 for h in sorted_hist if h <= value)
        return count / len(sorted_hist) * 100

    def _volume_trend(self, volumes: List[float]) -> str:
        if len(volumes) < 10:
            return "neutral"
        recent = np.mean(volumes[-5:])
        older = np.mean(volumes[-10:-5])
        if recent > older * 1.2:
            return "increasing"
        elif recent < older * 0.8:
            return "decreasing"
        return "stable"

    def _get_trend(self, values: List[float]) -> int:
        if len(values) < 2:
            return 0
        slope = np.polyfit(range(len(values)), values, 1)[0]
        if slope > 0:
            return 1
        elif slope < 0:
            return -1
        return 0

    def get_regime_history(self, symbol: str) -> List[Dict]:
        """Get regime history for a symbol"""
        return list(self._regime_history.get(symbol, []))


class MarketRegimeService:
    """Service for managing market regime detection across all symbols"""

    def __init__(self, config: Config, market_data_service: MarketDataService):
        self.config = config
        self.market_data_service = market_data_service
        self.detector = RegimeDetector(config)
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._regime_cache: Dict[str, RegimeState] = {}
        self._update_task: Optional[asyncio.Task] = None
        self._subscribers: Dict[str, List[callable]] = {}

    async def initialize(self):
        """Initialize regime service"""
        self.logger.info("Initializing Market Regime Service...")
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        self.logger.info("Market Regime Service initialized")

    async def shutdown(self):
        """Shutdown regime service"""
        self.logger.info("Shutting down Market Regime Service...")
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def _update_loop(self):
        """Background loop to update regimes"""
        while self._running:
            try:
                await self._update_all_regimes()
            except Exception as e:
                self.logger.error(f"Error in regime update loop: {e}")
            await asyncio.sleep(300)  # Update every 5 minutes

    async def _update_all_regimes(self):
        """Update regimes for all tracked symbols"""
        for exchange_name, adapter in self.market_data_service.adapters.items():
            for symbol in list(adapter._symbol_map.keys())[:50]:  # Limit to top 50
                try:
                    state = await self.detect_regime(symbol, exchange_name)
                    self._regime_cache[f"{exchange_name}:{symbol}"] = state
                    await self._notify_subscribers(symbol, state)
                except Exception as e:
                    self.logger.warning(f"Failed to detect regime for {symbol}: {e}")

    async def detect_regime(self, symbol: str, exchange: str = "binance") -> Optional[RegimeState]:
        """Detect regime for a specific symbol"""
        adapter = self.market_data_service.adapters.get(exchange)
        if not adapter:
            return None

        try:
            candles_15m = await adapter.fetch_candles(symbol, '15m', limit=200)
            candles_1h = await adapter.fetch_candles(symbol, '1h', limit=200)
            candles_4h = await adapter.fetch_candles(symbol, '4h', limit=200)
            candles_1d = await adapter.fetch_candles(symbol, '1d', limit=200)

            ticker = await adapter.fetch_ticker(symbol)
            funding = await adapter.fetch_funding_rate(symbol)

            # Exchange adapters expose dictionaries; the detector consumes
            # CandleData objects and a Decimal 24h volume.
            candles_15m = [
                CandleData(**candle) if isinstance(candle, dict) else candle
                for candle in candles_15m
            ]
            candles_1h = [
                CandleData(**candle) if isinstance(candle, dict) else candle
                for candle in candles_1h
            ]
            candles_4h = [
                CandleData(**candle) if isinstance(candle, dict) else candle
                for candle in candles_4h
            ]
            candles_1d = [
                CandleData(**candle) if isinstance(candle, dict) else candle
                for candle in candles_1d
            ]

            volume_24h = (
                ticker.get("volume_24h", Decimal("0"))
                if isinstance(ticker, dict)
                else getattr(ticker, "volume_24h", Decimal("0"))
            )

            state = self.detector.detect_regime(
                symbol=symbol,
                candles_15m=candles_15m,
                candles_1h=candles_1h,
                candles_4h=candles_4h,
                candles_1d=candles_1d,
                volume_24h=Decimal(str(volume_24h)),
                funding_rate=funding.get('rate') if funding else None
            )
            return state
        except Exception as e:
            self.logger.error(f"Failed to detect regime for {symbol}: {e}")
            return None

    def get_regime(self, symbol: str, exchange: str = "binance") -> Optional[RegimeState]:
        """Get cached regime state"""
        return self._regime_cache.get(f"{exchange}:{symbol}")

    def get_all_regimes(self) -> Dict[str, RegimeState]:
        """Get all cached regimes"""
        return self._regime_cache.copy()

    def get_btc_regime(self) -> Optional[RegimeState]:
        """Get BTC regime (market leader)"""
        return self.get_regime("BTCUSDT", "binance")

    def get_market_breadth(self) -> Dict[str, Any]:
        """Get overall market breadth statistics"""
        regimes = list(self._regime_cache.values())
        if not regimes:
            return {"total": 0}

        counts = {}
        for r in RegimeType:
            counts[r.value] = sum(1 for s in regimes if s.regime == r)

        trending_up = counts.get('trending_up', 0)
        trending_down = counts.get('trending_down', 0)
        ranging = counts.get('ranging', 0)
        volatile = counts.get('volatile', 0)

        total = len(regimes)
        return {
            "total_symbols": total,
            "regime_distribution": counts,
            "trending_pct": (trending_up + trending_down) / total * 100 if total > 0 else 0,
            "ranging_pct": ranging / total * 100 if total > 0 else 0,
            "volatile_pct": volatile / total * 100 if total > 0 else 0,
            "market_direction": "bullish" if trending_up > trending_down else "bearish" if trending_down > trending_up else "neutral",
            "btc_regime": self.get_btc_regime().regime.value if self.get_btc_regime() else "unknown"
        }

    def subscribe(self, symbol: str, callback: callable):
        """Subscribe to regime updates for a symbol"""
        key = f"regime:{symbol}"
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)

    def unsubscribe(self, symbol: str, callback: callable):
        """Unsubscribe from regime updates"""
        key = f"regime:{symbol}"
        if key in self._subscribers:
            self._subscribers[key].remove(callback)

    async def _notify_subscribers(self, symbol: str, state: RegimeState):
        """Notify subscribers of regime change"""
        key = f"regime:{symbol}"
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    await callback(state)
                except Exception as e:
                    self.logger.error(f"Error notifying regime subscriber for {symbol}: {e}")

    async def shutdown(self):
        """Shutdown regime service"""
        self._running = False
        if hasattr(self, '_update_task'):
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass


async def create_market_regime_service(
    config: Config,
    market_data_service: MarketDataService
) -> MarketRegimeService:
    """Create and initialize market regime service"""
    service = MarketRegimeService(config, market_data_service)
    await service.initialize()
    return service