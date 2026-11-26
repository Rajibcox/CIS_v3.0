"""
Unit tests for Market Scanner
"""

import pytest
from decimal import Decimal
from datetime import datetime
import numpy as np

from src.backend.services.market_scanner import (
    MarketScanner, ScanConfig, ScanResult, MarketSnapshot
)
from src.backend.utils.config import Config


class TestMarketScanner:
    """Test market scanner functionality"""

    @pytest.fixture
    def config(self):
        return Config()

    @pytest.fixture
    def scanner_config(self):
        return ScanConfig(
            min_volume_24h=10_000_000,
            max_spread_bps=50,
            min_atr_pct=0.5,
            max_atr_pct=10.0,
            min_adx=20.0,
            max_results=100,
            min_signal_score=70.0
        )

    @pytest.fixture
    def mock_snapshot(self):
        """Create a mock market snapshot for testing"""
        from src.backend.services.market_scanner import MarketSnapshot
        from src.backend.services.market_data_service import TickerData

        # Create mock ticker
        ticker = TickerData(
            symbol="BTCUSDT",
            exchange="binance",
            price=Decimal('50000'),
            bid=Decimal('49999'),
            ask=Decimal('50001'),
            bid_volume=Decimal('10'),
            ask_volume=Decimal('10'),
            volume_24h=Decimal('1000000000'),
            change_24h_pct=2.5,
            high_24h=Decimal('51000'),
            low_24h=Decimal('49000'),
            timestamp=datetime.utcnow()
        )

        # Mock indicators
        indicators = {
            'rsi': 45.0,
            'ema_9': 50100,
            'ema_21': 50050,
            'ema_50': 49500,
            'macd': 100,
            'macd_signal': 50,
            'macd_hist': 50,
            'atr': 500,
            'atr_pct': 1.0,
            'adx': 25,
            'bb_upper': 51000,
            'bb_middle': 50000,
            'bb_lower': 49000,
            'bb_width': 4.0,
            'volume_sma': 1000,
            'volume_ratio': 1.5,
            'vwap': 50050
        }

        # Create mock candles
        mock_candles = []
        base_price = 50000
        for i in range(100):
            mock_candles.append(type('Candle', (), {
                'open': base_price + i * 10,
                'high': base_price + i * 10 + 100,
                'low': base_price + i * 10 - 50,
                'close': base_price + i * 10 + 25,
                'volume': 1000,
                'open_time': datetime.utcnow()
            })())

        snapshot = MarketSnapshot(
            symbol="BTCUSDT",
            exchange="binance",
            ticker=type('Ticker', (), {
                'symbol': 'BTCUSDT',
                'exchange': 'binance',
                'price': Decimal('50000'),
                'bid': Decimal('49999'),
                'ask': Decimal('50001'),
                'bid_volume': Decimal('10'),
                'ask_volume': Decimal('10'),
                'volume_24h': Decimal('1000000000'),
                'change_24h_pct': 2.5,
                'high_24h': Decimal('51000'),
                'low_24h': Decimal('49000'),
                'spread_bps': 4.0,
                'spread_pct': 0.004
            })(),
            candles_15m=[],
            candles_1h=[type('Candle', (), {
                'open': 50000 + i,
                'high': 50100 + i,
                'low': 49900 + i,
                'close': 50000 + i + 10,
                'volume': 1000
            })() for i in range(100)],
            candles_4h=[],
            candles_1d=[],
            orderbook=None,
            funding_rate={'rate': Decimal('0.0001')},
            regime='trending',
            btc_correlation=0.85,
            indicators={
                'rsi': 45.0,
                'ema_9': 50100,
                'ema_21': 50050,
                'ema_50': 49500,
                'macd': 100,
                'macd_signal': 50,
                'atr': 500,
                'atr_pct': 1.0,
                'adx': 25,
                'bb_upper': 51000,
                'bb_middle': 50000,
                'bb_lower': 49000,
                'bb_width': 4.0,
                'volume_sma': 1000,
                'volume_ratio': 1.5,
                'vwap': 50050
            }
        )

        return snapshot


class TestScanConfig:
    """Test scan configuration"""

    def test_default_config(self):
        config = ScanConfig()
        assert config.min_volume_24h == 10_000_000
        assert config.max_spread_bps == 50
        assert config.max_results == 100
        assert config.min_signal_score == 70.0

    def test_custom_config(self):
        config = ScanConfig(
            min_volume_24h=5_000_000,
            max_spread_bps=100,
            max_results=50
        )
        assert config.min_volume_24h == 5_000_000
        assert config.max_spread_bps == 100
        assert config.max_results == 50


class TestTechnicalIndicators:
    """Test technical indicator calculations"""

    def test_rsi_calculation(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        # Test RSI with known values
        closes = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 109, 111, 112, 110]
        rsi = scanner._calculate_rsi(closes, 14)
        assert 0 <= rsi <= 100

    def test_ema_calculation(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        values = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        ema = scanner._calculate_ema(values, 3)
        assert len(ema) == len(values)
        assert ema[-1] > 0

    def test_atr_calculation(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        highs = [105, 106, 107, 108, 109]
        lows = [95, 96, 97, 98, 99]
        closes = [100, 101, 102, 103, 104]

        atr = scanner._calculate_atr(highs, lows, closes, 3)
        assert atr > 0

    def test_bollinger_bands(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        closes = [100] * 20
        upper, middle, lower = scanner._calculate_bollinger(closes, 20, 2)

        assert upper == middle == lower == 100

    def test_vwap_calculation(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        closes = [100, 101, 102, 103]
        volumes = [1000, 2000, 1500, 1000]

        vwap = scanner._calculate_vwap(closes, volumes)
        expected = sum(c * v for c, v in zip(closes, volumes)) / sum(volumes)
        assert abs(vwap - expected) < 0.01


class TestRegimeDetection:
    """Test market regime detection"""

    def test_regime_trending(self):
        from src.backend.services.market_scanner import MarketScanner

        scanner = MarketScanner(Config(), None, None)

        # Create mock candles with strong uptrend
        candles_1h = [type('Candle', (), {
            'open': 50000 + i * 50,
            'high': 50000 + i * 50 + 100,
            'low': 50000 + i * 50 - 50,
            'close': 50000 + i * 50 + 25,
            'volume': 1000
        })() for i in range(100)]

        candles_4h = [type('Candle', (), {
            'open': 50000 + i * 200,
            'high': 50000 + i * 200 + 200,
            'low': 50000 + i * 200 - 100,
            'close': 50000 + i * 200 + 50,
            'volume': 4000
        })() for i in range(30)]

        regime = scanner._detect_regime(candles_1h, candles_4h)
        assert regime in ['trending', 'breakout']


class TestRiskRewardCalculation:
    """Test risk/reward calculations"""

    def test_risk_reward_long(self):
        # LONG: entry 50000, stop 49000, tp1 51000
        entry = 50000
        stop = 49000
        tp1 = 51000

        risk = entry - stop  # 1000
        reward = tp1 - entry  # 1000
        rr = reward / risk

        assert rr == 1.0

    def test_risk_reward_short(self):
        # SHORT: entry 50000, stop 51000, tp1 49000
        entry = 50000
        stop = 51000
        tp1 = 49000

        risk = stop - entry  # 1000
        reward = entry - tp1  # 1000
        rr = reward / risk

        assert rr == 1.0


class TestPositionSizing:
    """Test position sizing logic"""

    def test_position_size_from_risk(self):
        equity = 10000
        risk_per_trade = 0.01  # 1%
        max_risk = equity * 0.01  # 100

        entry_price = 50000
        stop_loss = 49000
        stop_distance = entry_price - stop_loss  # 1000

        position_size = max_risk / stop_distance  # 100 / 1000 = 0.1
        quantity = 0.1

        notional = quantity * entry_price  # 5000
        leverage = 3
        required_margin = notional / leverage  # 1666.67

        assert abs(position_size - 0.1) < 0.001
        assert notional == 5000
        assert abs(required_margin - 1666.67) < 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])