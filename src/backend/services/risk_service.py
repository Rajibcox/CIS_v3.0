"""
Risk Service for QUANTUM TRADER V1
Implements risk management, position sizing, and leverage intelligence
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional, Any, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session

from src.backend.models.database import Position, Signal, Exchange, Symbol
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


class LeverageDecision(NamedTuple):
    """Result of leverage decision"""
    selected_leverage: int
    position_quantity: Decimal
    notional: Decimal
    required_margin: Decimal
    max_planned_loss: Decimal
    stop_distance: Decimal
    liquidation_price: Optional[Decimal]
    liquidation_buffer: Decimal
    estimated_fees: Decimal
    funding_assumption: Decimal
    net_tp1_profit: Decimal
    net_tp2_profit: Decimal
    net_tp3_profit: Decimal
    rejected_alternatives: List[Dict]
    reason: str


class RiskLimits(Enum):
    """Risk limit types"""
    DAILY_LOSS = "daily_loss"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_POSITIONS = "max_positions"
    MAX_LEVERAGE = "max_leverage"
    MAX_CORRELATED = "max_correlated"


@dataclass
class RiskBudget:
    """Available risk budget for new trades"""
    total_equity: Decimal
    available_margin: Decimal
    used_margin: Decimal
    daily_realized_pnl: Decimal
    current_drawdown: Decimal
    remaining_daily_risk: Decimal
    remaining_drawdown_risk: Decimal
    max_new_positions: int
    correlated_exposure: Decimal


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    quantity: Decimal
    notional: Decimal
    required_margin: Decimal
    leverage: int
    max_loss: Decimal
    stop_distance: Decimal
    liquidation_price: Optional[Decimal]
    liquidation_buffer_pct: Decimal
    rejected: bool
    rejection_reason: Optional[str]


class RiskEngine:
    """Core risk calculation engine"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def calculate_risk_budget(self, db: Session, equity: Decimal) -> RiskBudget:
        """Calculate available risk budget"""
        # Get open positions
        open_positions = db.query(Position).filter(Position.status == 'open').all()

        used_margin = sum(p.margin_used for p in open_positions)
        available_margin = equity - used_margin

        # Daily realized PnL (simplified - would query actual trades)
        daily_realized_pnl = Decimal('0')

        # Current drawdown
        peak_equity = equity  # Would track actual peak
        current_drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else Decimal('0')

        # Remaining daily risk
        daily_limit = equity * Decimal(str(self.config.settings.daily_loss_limit))
        remaining_daily_risk = max(Decimal('0'), daily_limit + daily_realized_pnl)

        # Remaining drawdown risk
        drawdown_limit = equity * Decimal(str(self.config.settings.emergency_drawdown))
        remaining_drawdown_risk = max(Decimal('0'), drawdown_limit - (peak_equity - equity))

        # Correlated exposure (simplified)
        correlated_exposure = self._calculate_correlated_exposure(open_positions)

        return RiskBudget(
            total_equity=equity,
            available_margin=available_margin,
            used_margin=used_margin,
            daily_realized_pnl=daily_realized_pnl,
            current_drawdown=current_drawdown,
            remaining_daily_risk=remaining_daily_risk,
            remaining_drawdown_risk=remaining_drawdown_risk,
            max_new_positions=self.config.settings.max_simultaneous_positions - len([p for p in open_positions if p.status == 'open']),
            correlated_exposure=correlated_exposure
        )

    def _calculate_correlated_exposure(self, positions: List) -> Decimal:
        """Calculate exposure to correlated assets"""
        # Simplified - would check actual correlations
        total = Decimal('0')
        for p in positions:
            total += p.notional_value
        return total

    def calculate_position_size(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        equity: Decimal,
        risk_per_trade: Decimal,
        exchange_info: Dict,
        max_leverage: int
    ) -> PositionSizeResult:
        """Calculate position size from risk parameters"""
        # 1. Calculate stop distance
        stop_distance = abs(entry_price - stop_loss)

        # 2. Calculate max risk amount
        max_risk = self._quantize(Decimal(str(equity)) * risk_per_trade)

        # 3. Calculate raw position size
        raw_quantity = max_risk / stop_distance

        # 4. Apply exchange constraints
        lot_size = Decimal(str(exchange_info.get('lot_size', '0.001')))
        min_notional = Decimal(str(exchange_info.get('min_notional', '5')))
        max_qty = Decimal(str(exchange_info.get('max_qty', '1000000')))

        # Round down to lot size
        quantity = (raw_quantity / lot_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * lot_size
        quantity = min(quantity, max_qty)

        # Check minimum notional
        notional = quantity * entry_price
        if notional < min_notional:
            return PositionSizeResult(
                quantity=Decimal('0'),
                notional=Decimal('0'),
                required_margin=Decimal('0'),
                leverage=0,
                max_loss=Decimal('0'),
                stop_distance=stop_distance,
                liquidation_price=None,
                liquidation_buffer_pct=Decimal('0'),
                rejected=True,
                rejection_reason=f"Notional {notional} below minimum {min_notional}"
            )

        # 5. Calculate required margin and leverage
        notional = quantity * entry_price
        required_margin = notional / max_leverage

        # Check available margin (would be passed in)
        # For now, assume sufficient

        # 6. Calculate liquidation price
        maint_margin_rate = Decimal('0.005')  # 0.5% default
        leverage_decimal = Decimal(str(max_leverage))
        if notional > 0:
            liquidation_price = entry_price * (
                Decimal('1') - (Decimal('1') / leverage_decimal) + maint_margin_rate
            )
            liquidation_buffer = (
                (entry_price - liquidation_price) / entry_price * Decimal('100')
            )
        else:
            liquidation_price = None
            liquidation_buffer = Decimal('0')

        return PositionSizeResult(
            quantity=quantity,
            notional=notional,
            required_margin=required_margin,
            leverage=max_leverage,
            max_loss=max_risk,
            stop_distance=stop_distance,
            liquidation_price=liquidation_price,
            liquidation_buffer_pct=liquidation_buffer,
            rejected=False,
            rejection_reason=None
        )

    def _quantize(self, value: Decimal) -> Decimal:
        """Quantize to 8 decimal places"""
        return value.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)


class DynamicLeverageCalculator:
    """Intelligent leverage selection based on multiple factors"""

    def __init__(self, config: Config, risk_engine: RiskEngine):
        self.config = config
        self.risk_engine = risk_engine
        self.logger = logging.getLogger(__name__)

    def calculate_leverage(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        tp1: Decimal,
        tp2: Decimal,
        tp3: Decimal,
        equity: Decimal,
        available_margin: Decimal,
        exchange_info: Dict,
        signal_score: float,
        strategy_expectancy: float,
        max_leverage: int = 3
    ) -> LeverageDecision:
        """
        Calculate optimal leverage for a trade
        Uses risk-first approach: size from risk, then leverage from margin
        """
        # 1. Calculate position size from risk
        stop_distance = abs(entry_price - stop_loss)
        max_risk = Decimal(str(equity)) * Decimal(str(self.config.settings.risk_per_trade))

        # Position size from risk
        raw_quantity = max_risk / abs(entry_price - stop_loss)

        # Apply exchange constraints
        lot_size = Decimal(str(exchange_info.get('lot_size', '0.001')))
        quantity = (raw_quantity / lot_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * lot_size

        # Notional and required margin at max leverage
        notional = quantity * entry_price
        max_lev = min(max_leverage, exchange_info.get('max_leverage', 125))

        # Try leverage from max down to 1
        best_decision = None
        rejected = []

        available_margin_decimal = Decimal(str(available_margin))

        for lev in range(max_lev, 0, -1):
            required_margin = (quantity * entry_price) / lev

            if required_margin <= available_margin_decimal:
                # Calculate liquidation
                maint_margin = Decimal('0.005')
                liq_price = entry_price * (1 - (1 / Decimal(lev)) + maint_margin)
                liq_buffer = (entry_price - liq_price) / entry_price * 100

                # Check liquidation buffer > 20%
                if (entry_price - liq_price) / entry_price > Decimal('0.2'):
                    # Calculate profits
                    tp1_profit = (tp1 - entry_price) * quantity * Decimal('0.4')
                    tp2_profit = (tp2 - entry_price) * quantity * Decimal('0.3')
                    tp3_profit = (tp3 - entry_price) * quantity * Decimal('0.2')

                    fees = (quantity * entry_price * Decimal('0.0004') * 2)  # Entry + exit
                    funding = entry_price * quantity * Decimal('0.0001') * 3  # 3 funding periods

                    net_tp1 = tp1_profit - fees - funding
                    net_tp2 = tp2_profit - fees - funding
                    net_tp3 = tp3_profit - fees - funding

                    return LeverageDecision(
                        selected_leverage=lev,
                        position_quantity=quantity,
                        notional=quantity * entry_price,
                        required_margin=(quantity * entry_price) / lev,
                        max_planned_loss=abs(entry_price - stop_loss) * quantity,
                        stop_distance=abs(entry_price - stop_loss),
                        liquidation_price=liq_price,
                        liquidation_buffer=((entry_price - liq_price) / entry_price * 100).quantize(Decimal('0.01')),
                        estimated_fees=fees,
                        funding_assumption=funding,
                        net_tp1_profit=net_tp1,
                        net_tp2_profit=net_tp2,
                        net_tp3_profit=net_tp3,
                        rejected_alternatives=rejected,
                        reason=f"Risk-first sizing: {float(max_risk):.2f} USDT risk. Stop distance {float(abs(entry_price - stop_loss)):.2f} -> {float(quantity):.4f} qty. {lev}x leverage fits in margin."
                    )

            rejected.append({"leverage": lev, "reason": "Insufficient margin or liquidation buffer"})

        # No valid leverage found
        return LeverageDecision(
            selected_leverage=0,
            position_quantity=Decimal('0'),
            notional=Decimal('0'),
            required_margin=Decimal('0'),
            max_planned_loss=Decimal('0'),
            stop_distance=abs(entry_price - stop_loss),
            liquidation_price=None,
            liquidation_buffer=Decimal('0'),
            estimated_fees=Decimal('0'),
            funding_assumption=Decimal('0'),
            net_tp1_profit=Decimal('0'),
            net_tp2_profit=Decimal('0'),
            net_tp3_profit=Decimal('0'),
            rejected_alternatives=rejected,
            reason="No valid leverage found - insufficient margin or liquidation risk too high"
        )

    def _get_available_margin(self) -> Decimal:
        """Get available margin (simplified)"""
        return Decimal(str(self.config.settings.initial_equity)) * Decimal('0.5')


class PortfolioRiskManager:
    """Manages portfolio-level risk limits"""

    def __init__(self, config: Config, risk_engine: RiskEngine):
        self.config = config
        self.risk_engine = risk_engine
        self.logger = logging.getLogger(__name__)

    def check_pre_trade_risk(
        self,
        db: Session,
        signal: Any,
        position_size: Any
    ) -> Tuple[bool, List[str]]:
        """Check all pre-trade risk limits"""
        errors = []

        # Get risk budget
        budget = self.risk_engine.calculate_risk_budget(db, Decimal(str(self.config.settings.initial_equity)))

        # 1. Max positions
        if budget.max_new_positions <= 0:
            errors.append(f"Max positions reached ({budget.max_new_positions} remaining)")

        # 2. Daily loss limit
        if budget.remaining_daily_risk <= Decimal('0'):
            errors.append("Daily loss limit reached")

        # 3. Drawdown limit
        if budget.current_drawdown >= Decimal(str(self.config.settings.emergency_drawdown)):
            errors.append("Emergency drawdown limit reached")

        # 4. Margin availability
        # Would check if required_margin <= available_margin

        # 5. Correlated exposure
        # Would check correlation with existing positions

        return len(errors) == 0, errors

    def get_portfolio_risk_metrics(self, db: Session, equity: Decimal) -> Dict:
        """Get current portfolio risk metrics"""
        budget = self.risk_engine.calculate_risk_budget(db, equity)

        return {
            'equity': float(equity),
            'available_margin': float(budget.available_margin),
            'used_margin': float(budget.used_margin),
            'margin_usage_pct': float(budget.used_margin / equity * 100) if equity > 0 else 0,
            'open_positions': self.config.settings.max_simultaneous_positions - budget.max_new_positions,
            'max_positions': self.config.settings.max_simultaneous_positions,
            'daily_pnl': float(budget.daily_realized_pnl),
            'daily_loss_limit': float(self.config.settings.initial_equity * Decimal(str(self.config.settings.daily_loss_limit))),
            'daily_loss_used_pct': float((budget.daily_realized_pnl / budget.remaining_daily_risk * 100) if budget.remaining_daily_risk > 0 else 0),
            'current_drawdown': float(budget.current_drawdown * 100),
            'drawdown_warning': float(self.config.settings.drawdown_warning * 100),
            'emergency_drawdown': float(self.config.settings.emergency_drawdown * 100),
            'correlated_exposure': float(budget.correlated_exposure),
            'max_correlated_exposure': float(self.config.settings.initial_equity * Decimal('0.5'))
        }


class RiskService:
    """Main risk management service"""

    def __init__(self, config: Config):
        self.config = config
        self.risk_engine = RiskEngine(config)
        self.leverage_calculator = DynamicLeverageCalculator(config, self.risk_engine)
        self.portfolio_manager = PortfolioRiskManager(config, self.risk_engine)
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize risk service"""
        logging.getLogger(__name__).info("Risk Service initialized")

    async def shutdown(self):
        pass

    def calculate_position_size(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        equity: Decimal,
        exchange_info: Dict
    ) -> Any:
        """Calculate position size"""
        return self.risk_engine.calculate_position_size(
            entry_price, stop_loss, equity,
            Decimal(str(self.config.settings.risk_per_trade)),
            exchange_info,
            self.config.settings.max_leverage
        )

    def calculate_leverage(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        tp1: Decimal,
        tp2: Decimal,
        tp3: Decimal,
        equity: Decimal,
        available_margin: Decimal,
        exchange_info: Dict,
        signal_score: float,
        strategy_expectancy: float
    ) -> LeverageDecision:
        """Calculate optimal leverage"""
        return self.leverage_calculator.calculate_leverage(
            entry_price, stop_loss, tp1, tp2, tp3,
            equity, available_margin, exchange_info,
            signal_score, 0.0  # strategy_expectancy
        )

    def check_pre_trade_risk(self, db: Session, signal: Any, position_size: Any) -> Tuple[bool, List[str]]:
        """Check all pre-trade risk limits"""
        return self.portfolio_manager.check_pre_trade_risk(None, None, None)

    def get_portfolio_risk(self, equity: Decimal) -> Dict:
        """Get portfolio risk metrics"""
        return self.portfolio_manager.get_portfolio_risk_metrics(None, equity)

    async def initialize(self):
        logging.getLogger(__name__).info("Risk Service initialized")

    async def shutdown(self):
        pass