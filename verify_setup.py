#!/usr/bin/env python3
"""
Verify QUANTUM TRADER V1 Setup
Run this script to verify the backend setup works correctly
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        from src.backend.utils.config import Config
        print("✓ Config")
    except Exception as e:
        print(f"✗ Config: {e}")
        return False

    try:
        from src.backend.utils.logger import setup_logging, get_logger
        print("✓ Logger")
    except Exception as e:
        print(f"✗ Logger: {e}")
        return False

    try:
        from src.backend.models.database import Base, Exchange, Symbol, Signal
        print("✓ Database Models")
    except Exception as e:
        print(f"✗ Database Models: {e}")
        return False

    try:
        from src.backend.api.server import create_app
        print("✓ API Server")
    except Exception as e:
        print(f"✗ API Server: {e}")
        return False

    try:
        from src.backend.services.market_data_service import MarketDataService
        print("✓ Market Data Service")
    except Exception as e:
        print(f"✗ Market Data Service: {e}")
        return False

    try:
        from src.backend.services.historical_data_service import HistoricalDataService
        print("✓ Historical Data Service")
    except Exception as e:
        print(f"✗ Historical Data Service: {e}")
        return False

    try:
        from src.backend.services.market_scanner import MarketScanner
        print("✓ Market Scanner")
    except Exception as e:
        print(f"✗ Market Scanner: {e}")
        return False

    try:
        from src.backend.services.market_regime_service import MarketRegimeService
        print("✓ Market Regime Service")
    except Exception as e:
        print(f"✗ Market Regime Service: {e}")
        return False

    try:
        from src.backend.services.signal_service import SignalService
        print("✓ Signal Service")
    except Exception as e:
        print(f"✗ Signal Service: {e}")
        return False

    try:
        from src.backend.services.strategy_service import StrategyService
        print("✓ Strategy Service")
    except Exception as e:
        print(f"✗ Strategy Service: {e}")
        return False

    try:
        from src.backend.services.risk_service import RiskService
        print("✓ Risk Service")
    except Exception as e:
        print(f"✗ Risk Service: {e}")
        return False

    try:
        from src.backend.services.execution_service import ExecutionService
        print("✓ Execution Service")
    except Exception as e:
        print(f"✗ Execution Service: {e}")
        return False

    try:
        from src.backend.services.tp_sl_service import TPSLService
        print("✓ TP/SL Service")
    except Exception as e:
        print(f"✗ TP/SL Service: {e}")
        return False

    try:
        from src.backend.services.pnl_service import PnLService
        print("✓ PnL Service")
    except Exception as e:
        print(f"✗ PnL Service: {e}")
        return False

    try:
        from src.backend.services import initialize_services, shutdown_services
        print("✓ Service Container")
    except Exception as e:
        print(f"✗ Service Container: {e}")
        return False

    try:
        from src.backend.api.routes.overview import router as overview_router
        from src.backend.api.routes.market import router as market_router
        from src.backend.api.routes.signals import router as signals_router
        from src.backend.api.routes.strategies import router as strategies_router
        from src.backend.api.routes.trading import router as trading_router
        from src.backend.api.routes.config import router as config_router
        from src.backend.api.routes.analytics import router as analytics_router
        from src.backend.api.routes.system import router as system_router
        from src.backend.api.router import api_router
        print("✓ All API Routes")
    except Exception as e:
        print(f"✗ API Routes: {e}")
        return False

    return True


async def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    try:
        from src.backend.utils.config import Config
        config = Config()

        # Test key settings
        assert config.settings.app_name == "QUANTUM TRADER V1"
        assert config.settings.version == "1.0.0"
        assert config.settings.database_url.startswith("sqlite:///")
        assert config.settings.initial_equity == 100.0
        assert config.settings.risk_per_trade == 0.005
        assert config.settings.max_leverage == 3

        print("✓ Configuration loaded correctly")
        print(f"  App: {config.settings.app_name} v{config.settings.version}")
        print(f"  DB: {config.settings.database_url}")
        print(f"  Equity: {config.settings.initial_equity} USDT")
        print(f"  Risk/trade: {config.settings.risk_per_trade*100}%")
        print(f"  Max Leverage: {config.settings.max_leverage}x")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


async def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        from src.backend.database.init_db import DatabaseInitializer
        from src.backend.utils.config import Config

        config = Config()
        # Use in-memory database for testing
        config.settings.database_url = "sqlite:///:memory:"

        initializer = DatabaseInitializer(config.settings.database_url)
        initializer.create_tables()
        initializer.seed_data()

        # Verify tables exist
        from sqlalchemy import inspect, create_engine
        engine = create_engine("sqlite:///:memory:")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'exchanges', 'exchange_credentials', 'symbols', 'market_candles',
            'strategies', 'strategy_rules', 'signals', 'positions',
            'orders', 'tp_sl_stages', 'pnl_entries', 'configurations',
            'audit_logs', 'system_events', 'telegram_users'
        ]

        for table in expected_tables:
            if table not in tables:
                print(f"✗ Missing table: {table}")
                return False

        print(f"✓ Database initialized with {len(tables)} tables")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_risk_engine():
    """Test risk engine calculations"""
    print("\nTesting risk engine...")
    try:
        from src.backend.services.risk_service import RiskEngine, DynamicLeverageCalculator
        from src.backend.utils.config import Config
        from decimal import Decimal

        config = Config()
        risk_engine = RiskEngine(config)

        # Test position sizing
        result = risk_engine.calculate_position_size(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            equity=Decimal('10000'),
            risk_per_trade=Decimal('0.01'),
            exchange_info={
                'lot_size': Decimal('0.001'),
                'min_notional': Decimal('5'),
                'max_qty': Decimal('1000')
            },
            max_leverage=3
        )

        assert not result.rejected
        assert result.quantity > 0
        assert result.max_loss == Decimal('100')  # 1% of 10000

        print("✓ Risk engine calculations work correctly")
        print(f"  Quantity: {result.quantity}")
        print(f"  Notional: {result.notional}")
        print(f"  Required Margin: {result.required_margin}")
        print(f"  Leverage: {result.leverage}")
        print(f"  Max Loss: {result.max_loss}")
        return True
    except Exception as e:
        print(f"✗ Risk engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_technical_indicators():
    """Test technical indicator calculations"""
    print("\nTesting technical indicators...")
    try:
        from src.backend.services.market_scanner import MarketScanner
        from src.backend.utils.config import Config
        import numpy as np

        scanner = MarketScanner(Config(), None, None)

        # Test RSI
        closes = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 109, 111, 112, 110]
        rsi = scanner._calculate_rsi(closes, 14)
        assert 0 <= rsi <= 100
        print(f"✓ RSI: {rsi:.2f}")

        # Test EMA
        values = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        ema = scanner._calculate_ema(values, 3)
        assert len(ema) == len(values)
        print(f"✓ EMA: {ema[-1]:.2f}")

        # Test ATR
        highs = [105, 106, 107, 108, 109]
        lows = [95, 96, 97, 98, 99]
        closes = [100, 101, 102, 103, 104]
        atr = scanner._calculate_atr(highs, lows, closes, 3)
        assert atr > 0
        print(f"✓ ATR: {atr:.2f}")

        # Test Bollinger Bands
        closes = [100] * 20
        upper, middle, lower = scanner._calculate_bollinger(closes, 20, 2)
        assert upper == middle == lower == 100
        print(f"✓ Bollinger Bands: {lower:.2f} / {middle:.2f} / {upper:.2f}")

        print("✓ All technical indicators work correctly")
        return True
    except Exception as e:
        print(f"✗ Technical indicator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_market_data_service():
    """Test market data service with mock adapter"""
    print("\nTesting market data service...")
    try:
        from src.backend.services.market_data_service import MarketDataService, MockExchangeAdapter
        from src.backend.utils.config import Config

        config = Config()
        config.settings.mock_exchange = True

        service = MarketDataService(config)
        await service.initialize()

        # Test getting ticker
        ticker = await service.get_ticker("BTCUSDT")
        assert ticker is not None
        assert 'price' in ticker
        assert ticker['symbol'] == 'BTCUSDT'
        print(f"✓ Ticker for BTCUSDT: ${ticker['price']}")

        # Test getting candles
        candles = await service.get_candles("BTCUSDT", "1h", limit=10)
        assert len(candles) > 0
        print(f"✓ Got {len(candles)} candles for BTCUSDT 1h")

        # Test getting orderbook
        orderbook = await service.get_orderbook("BTCUSDT", depth=10)
        assert orderbook is not None
        assert len(orderbook['bids']) > 0
        assert len(orderbook['asks']) > 0
        print(f"✓ Orderbook: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")

        # Test eligible symbols
        symbols = await service.get_eligible_symbols()
        assert len(symbols) > 0
        print(f"✓ Eligible symbols: {len(symbols)} ({', '.join(symbols[:5])}...)")

        # Test market overview
        overview = await service.get_market_overview()
        assert 'total_volume_24h' in overview
        print(f"✓ Market overview: ${overview['total_volume_24h']:,.0f} volume")

        await service.shutdown()
        print("✓ Market data service works correctly")
        return True
    except Exception as e:
        print(f"✗ Market data service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_risk_engine():
    """Test risk engine calculations"""
    print("\nTesting risk engine...")
    try:
        from src.backend.services.risk_service import RiskEngine, DynamicLeverageCalculator
        from src.backend.utils.config import Config
        from decimal import Decimal

        config = Config()
        risk_engine = RiskEngine(config)

        # Test position sizing
        result = risk_engine.calculate_position_size(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            equity=Decimal('10000'),
            risk_per_trade=Decimal('0.01'),
            exchange_info={
                'lot_size': Decimal('0.001'),
                'min_notional': Decimal('5'),
                'max_qty': Decimal('1000')
            },
            max_leverage=3
        )

        assert not result.rejected
        assert result.quantity > 0
        assert result.max_loss == Decimal('100')  # 1% of 10000

        print("✓ Risk engine calculations work correctly")
        print(f"  Quantity: {result.quantity}")
        print(f"  Notional: {result.notional}")
        print(f"  Required Margin: {result.required_margin}")
        print(f"  Leverage: {result.leverage}")
        print(f"  Max Loss: {result.max_loss}")
        return True
    except Exception as e:
        print(f"✗ Risk engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_technical_indicators():
    """Test technical indicator calculations"""
    print("\nTesting technical indicators...")
    try:
        from src.backend.services.market_scanner import MarketScanner
        from src.backend.utils.config import Config
        import numpy as np

        scanner = MarketScanner(Config(), None, None)

        # Test RSI
        closes = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 109, 111, 112, 110]
        rsi = scanner._calculate_rsi(closes, 14)
        assert 0 <= rsi <= 100
        print(f"✓ RSI: {rsi:.2f}")

        # Test EMA
        values = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        ema = scanner._calculate_ema(values, 3)
        assert len(ema) == len(values)
        print(f"✓ EMA: {ema[-1]:.2f}")

        # Test ATR
        highs = [105, 106, 107, 108, 109]
        lows = [95, 96, 97, 98, 99]
        closes = [100, 101, 102, 103, 104]
        atr = scanner._calculate_atr(highs, lows, closes, 3)
        assert atr > 0
        print(f"✓ ATR: {atr:.2f}")

        # Test Bollinger Bands
        closes = [100] * 20
        upper, middle, lower = scanner._calculate_bollinger(closes, 20, 2)
        assert upper == middle == lower == 100
        print(f"✓ Bollinger Bands: {lower:.2f} / {middle:.2f} / {upper:.2f}")

        print("✓ All technical indicators work correctly")
        return True
    except Exception as e:
        print(f"✗ Technical indicator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_risk_service():
    """Test risk service with dynamic leverage"""
    print("\nTesting risk service...")
    try:
        from src.backend.services.risk_service import RiskService, DynamicLeverageCalculator
        from src.backend.utils.config import Config
        from decimal import Decimal

        config = Config()
        risk_service = RiskService(config)
        await risk_service.initialize()

        # Test leverage calculation
        leverage_decision = risk_service.calculate_leverage(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            tp1=Decimal('51000'),
            tp2=Decimal('52000'),
            tp3=Decimal('53000'),
            equity=Decimal('10000'),
            available_margin=Decimal('5000'),
            exchange_info={'max_leverage': 125, 'lot_size': Decimal('0.001')},
            signal_score=85.0,
            strategy_expectancy=0.5
        )

        assert leverage_decision.selected_leverage >= 1
        assert leverage_decision.position_quantity > 0
        assert leverage_decision.required_margin > 0

        print(f"✓ Leverage decision: {leverage_decision.selected_leverage}x")
        print(f"  Quantity: {leverage_decision.position_quantity}")
        print(f"  Notional: {leverage_decision.notional}")
        print(f"  Required Margin: {leverage_decision.required_margin}")
        print(f"  Liquidation Buffer: {leverage_decision.liquidation_buffer}%")
        print(f"  Reason: {leverage_decision.reason}")

        # Test portfolio risk
        portfolio_risk = risk_service.get_portfolio_risk(Decimal('10000'))
        assert 'equity' in portfolio_risk
        assert 'available_margin' in portfolio_risk
        print(f"✓ Portfolio risk metrics available")

        return True
    except Exception as e:
        print(f"✗ Risk service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification tests"""
    print("=" * 60)
    print("QUANTUM TRADER V1 - Setup Verification")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Risk Engine", test_risk_engine),
        ("Technical Indicators", test_technical_indicators),
        ("Market Data Service", test_market_data_service),
        ("Risk Service", test_risk_service),
    ]

    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed with exception: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n✅ ALL TESTS PASSED - Setup is ready!")
        return 0
    else:
        print(f"\n❌ {len(results) - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))