"""
Unit tests for Risk Engine
"""

import pytest
from decimal import Decimal
from src.backend.services.risk_service import RiskEngine, DynamicLeverageCalculator, RiskEngine as RiskEngineClass


class TestRiskEngine:
    """Test risk engine calculations"""

    @pytest.fixture
    def config(self):
        from src.backend.utils.config import Config
        return Config()

    @pytest.fixture
    def risk_engine(self, config):
        return RiskEngine(config)

    def test_calculate_position_size_basic(self, risk_engine):
        """Test basic position size calculation"""
        result = risk_engine.calculate_position_size(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            equity=Decimal('10000'),
            risk_per_trade=Decimal('0.01'),  # 1%
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
        assert result.stop_distance == Decimal('1000')

    def test_calculate_position_size_rejected_min_notional(self, risk_engine):
        """Test rejection when notional below minimum"""
        result = risk_engine.calculate_position_size(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49900'),  # Very tight stop
            equity=Decimal('100'),
            risk_per_trade=Decimal('0.01'),
            exchange_info={
                'lot_size': Decimal('0.001'),
                'min_notional': Decimal('5'),
                'max_qty': Decimal('1000')
            },
            max_leverage=3
        )

        # A $1 equity with 1% risk and a $100 stop distance
        # rounds below the exchange lot size and must be rejected.
        assert result.rejected
        assert result.quantity == Decimal('0')
        assert result.notional == Decimal('0')
        assert "below minimum" in result.rejection_reason

    def test_calculate_position_size_rejected_stop_too_wide(self, risk_engine):
        """Test rejection when stop requires too much leverage"""
        result = risk_engine.calculate_position_size(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('25000'),  # 50% stop
            equity=Decimal('100'),
            risk_per_trade=Decimal('0.01'),
            exchange_info={
                'lot_size': Decimal('0.001'),
                'min_notional': Decimal('5'),
                'max_qty': Decimal('1000')
            },
            max_leverage=3
        )

        # Stop distance = 25000, max risk = 1 (1% of 100)
        # Quantity = 1/25000 = 0.00004, rounded to lot = 0
        # Should be rejected
        assert result.rejected


class TestDynamicLeverageCalculator:
    """Test dynamic leverage calculator"""

    @pytest.fixture
    def config(self):
        from src.backend.utils.config import Config
        return Config()

    @pytest.fixture
    def risk_engine(self, config):
        return RiskEngine(config)

    @pytest.fixture
    def leverage_calc(self, config, risk_engine):
        from src.backend.services.risk_service import DynamicLeverageCalculator
        return DynamicLeverageCalculator(config, risk_engine)

    def test_calculate_leverage_basic(self, leverage_calc):
        """Test basic leverage calculation"""
        decision = leverage_calc.calculate_leverage(
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            tp1=Decimal('51000'),
            tp2=Decimal('52000'),
            tp3=Decimal('53000'),
            equity=Decimal('10000'),
            available_margin=Decimal('5000'),
            exchange_info={
                'max_leverage': 125,
                'lot_size': Decimal('0.001')
            },
            signal_score=85.0,
            strategy_expectancy=0.5
        )

        # Should select a valid leverage
        assert decision.selected_leverage >= 1
        assert decision.position_quantity > 0
        assert decision.required_margin > 0


class TestPortfolioRiskManager:
    """Test portfolio risk management"""

    @pytest.fixture
    def config(self):
        from src.backend.utils.config import Config
        return Config()

    @pytest.fixture
    def portfolio_manager(self, config):
        from src.backend.services.risk_service import PortfolioRiskManager
        from src.backend.services.risk_service import RiskEngine
        risk_engine = RiskEngine(config)
        return PortfolioRiskManager(config, risk_engine)

    def test_get_portfolio_risk_metrics(self, portfolio_manager):
        """Test portfolio risk metrics calculation"""
        metrics = portfolio_manager.get_portfolio_risk_metrics(None, Decimal('10000'))

        assert 'equity' in metrics
        assert 'available_margin' in metrics
        assert 'used_margin' in metrics
        assert 'margin_usage_pct' in metrics
        assert 'open_positions' in metrics
        assert 'max_positions' in metrics
        assert 'daily_pnl' in metrics
        assert 'daily_loss_limit' in metrics
        assert 'daily_loss_used_pct' in metrics
        assert 'current_drawdown' in metrics
        assert 'drawdown_warning' in metrics
        assert 'emergency_drawdown' in metrics


class TestRiskCalculations:
    """Test core risk calculations"""

    def test_quantize(self):
        from src.backend.services.risk_service import RiskEngine
        from src.backend.utils.config import Config

        config = Config()
        engine = RiskEngine(config)

        # Test quantization to 8 decimal places
        value = Decimal('1.23456789123')
        result = engine._quantize(value)
        assert result == Decimal('1.23456789')

    def test_calculate_risk_budget(self):
        from src.backend.services.risk_service import RiskEngine
        from src.backend.utils.config import Config

        config = Config()
        engine = RiskEngine(config)

        # This would need a database session
        # Just testing the method exists
        assert hasattr(engine, 'calculate_risk_budget')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])