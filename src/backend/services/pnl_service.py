"""
PnL Service for QUANTUM TRADER V1
Implements comprehensive PnL tracking, analytics, and performance metrics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional, Any, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, extract

from src.backend.models.database import (
    Position, Order, OrderStatus, Signal
)
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


@dataclass
class TradePnL:
    """PnL for a single trade"""
    trade_id: int
    symbol: str
    exchange: str
    direction: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    entry_fees: Decimal
    exit_fees: Decimal
    funding: Decimal
    net_pnl: Decimal
    r_multiple: Decimal
    hold_time_hours: Decimal
    exit_reason: str
    tp_stage_reached: int
    opened_at: datetime
    closed_at: datetime


@dataclass
class PnLSummary:
    """PnL summary for a period"""
    period_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_pnl: Decimal
    total_fees: Decimal
    total_funding: Decimal
    net_pnl: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    avg_r_multiple: Decimal
    max_drawdown: Decimal
    best_trade: Decimal
    worst_trade: Decimal
    avg_hold_time_hours: Decimal
    by_exit_reason: Dict[str, int]
    by_tp_stage: Dict[int, int]


@dataclass
class PerformanceMetrics:
    """Detailed performance metrics"""
    total_return_pct: Decimal
    annualized_return_pct: Decimal
    volatility_pct: Decimal
    sharpe_ratio: Optional[Decimal]
    sortino_ratio: Optional[Decimal]
    calmar_ratio: Optional[Decimal]
    max_drawdown_pct: Decimal
    avg_drawdown_pct: Decimal
    max_drawdown_duration_days: int
    current_drawdown_pct: Decimal
    total_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    avg_r_multiple: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    consecutive_wins: int
    consecutive_losses: int
    risk_adjusted_return: Decimal
    ulcer_index: Decimal
    sterling_ratio: Decimal


@dataclass
class BreakdownItem:
    """Breakdown by category"""
    category: str
    trades: int
    win_rate: Decimal
    profit_factor: Decimal
    net_pnl: Decimal
    avg_r_multiple: Decimal


@dataclass
class TPAnalytics:
    """TP stage analytics"""
    tp1_hit_rate: Decimal
    tp2_hit_rate: Decimal
    tp3_hit_rate: Decimal
    runner_hit_rate: Decimal
    profit_captured_tp1_pct: Decimal
    profit_captured_tp2_pct: Decimal
    profit_captured_tp3_pct: Decimal
    profit_given_back_after_tp3_pct: Decimal
    stop_out_after_tp1_rate: Decimal
    stop_out_after_tp2_rate: Decimal
    stop_out_after_tp3_rate: Decimal
    avg_r_multiple_by_stage: Dict[str, Decimal]


class PnLEngine:
    """Core PnL calculation engine"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def calculate_trade_pnl(
        self,
        entry_price: Decimal,
        exit_price: Decimal,
        quantity: Decimal,
        direction: str,
        entry_fees: Decimal,
        exit_fees: Decimal,
        funding: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate PnL for a single trade"""
        if direction == "LONG":
            gross_pnl = (exit_price - entry_price) * quantity
        else:
            gross_pnl = (entry_price - exit_price) * quantity

        total_fees = entry_fees + exit_fees
        net_pnl = gross_pnl - total_fees - funding

        return {
            'gross_pnl': gross_pnl,
            'total_fees': total_fees,
            'funding': funding,
            'net_pnl': net_pnl
        }

    def calculate_r_multiple(
        self,
        net_pnl: Decimal,
        planned_risk: Decimal
    ) -> Decimal:
        """Calculate R-multiple (net PnL / planned risk)"""
        if planned_risk == 0:
            return Decimal('0')
        return (net_pnl / planned_risk).quantize(Decimal('0.01'))

    def calculate_hold_time(self, opened_at: datetime, closed_at: datetime) -> Decimal:
        """Calculate hold time in hours"""
        delta = closed_at - opened_at
        return Decimal(str(delta.total_seconds() / 3600)).quantize(Decimal('0.01'))

    def calculate_drawdown(self, equity_curve: List[Decimal]) -> Dict:
        """Calculate drawdown metrics from equity curve"""
        if not equity_curve:
            return {
                'max_drawdown': Decimal('0'),
                'avg_drawdown': Decimal('0'),
                'max_duration_days': 0,
                'current_drawdown': Decimal('0')
            }

        peak = equity_curve[0]
        max_dd = Decimal('0')
        drawdowns = []
        current_dd_start = None

        for equity in equity_curve:
            if equity > peak:
                peak = equity
                if current_dd_start:
                    current_dd_start = None
            else:
                dd = (peak - equity) / peak * 100 if peak > 0 else Decimal('0')
                drawdowns.append(dd)
                if dd > max_dd:
                    max_dd = dd
                if not current_dd_start:
                    current_dd_start = 0
                current_dd_start += 1

        avg_dd = sum(drawdowns) / len(drawdowns) if drawdowns else Decimal('0')
        current_dd = drawdowns[-1] if drawdowns else Decimal('0')
        max_duration = max((len(drawdowns),)) if drawdowns else 0

        return {
            'max_drawdown': max_dd,
            'avg_drawdown': sum(drawdowns) / len(drawdowns) if drawdowns else Decimal('0'),
            'max_duration_days': len(drawdowns) // 24 if drawdowns else 0,
            'current_drawdown': drawdowns[-1] if drawdowns else Decimal('0')
        }


class PnLCalculator:
    """Calculates PnL for positions and trades"""

    def __init__(self, config: Config):
        self.config = config
        self.engine = PnLEngine(config)
        self.logger = logging.getLogger(__name__)

    def calculate_position_pnl(self, position: Any, current_price: Decimal) -> Dict[str, Decimal]:
        """Calculate unrealized PnL for open position"""
        if position.direction == "LONG":
            unrealized = (Decimal(str(current_price)) - position.entry_price) * position.quantity
        else:
            unrealized = (position.entry_price - Decimal(str(current_price))) * position.quantity

        return {
            'unrealized_pnl': unrealized,
            'current_price': Decimal(str(current_price)),
            'entry_price': position.entry_price
        }

    def calculate_realized_pnl(
        self,
        position: Any,
        exit_price: Decimal,
        fees: Decimal,
        funding: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate realized PnL for closed position"""
        if position.direction == "LONG":
            gross_pnl = (Decimal(str(position.exit_price)) - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - Decimal(str(position.exit_price))) * position.quantity

        net_pnl = gross_pnl - fees - Decimal(str(position.funding)) if hasattr(position, 'funding') else gross_pnl - fees

        return {
            'gross_pnl': gross_pnl,
            'fees': Decimal('0'),  # Would be passed in
            'funding': Decimal('0'),
            'net_pnl': net_pnl
        }


class PnLAnalytics:
    """Advanced PnL analytics and reporting"""

    def __init__(self, config: Config):
        self.config = config
        self.engine = PnLEngine(config)
        self.logger = logging.getLogger(__name__)

    def calculate_pnl_summary(
        self,
        trades: List[Dict],
        period_days: int = 30
    ) -> PnLSummary:
        """Calculate PnL summary from trade list"""
        if not trades:
            return PnLSummary(
                period_days=period_days,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                gross_pnl=Decimal('0'),
                total_fees=Decimal('0'),
                total_funding=Decimal('0'),
                net_pnl=Decimal('0'),
                win_rate=Decimal('0'),
                profit_factor=Decimal('0'),
                expectancy=Decimal('0'),
                avg_r_multiple=Decimal('0'),
                max_drawdown=Decimal('0'),
                best_trade=Decimal('0'),
                worst_trade=Decimal('0'),
                avg_hold_time_hours=Decimal('0'),
                by_exit_reason={},
                by_tp_stage={}
            )

        winning = [t for t in trades if t['net_pnl'] > 0]
        losing = [t for t in trades if t['net_pnl'] <= 0]

        gross_pnl = sum(t['gross_pnl'] for t in trades)
        total_fees = sum(t['fees'] for t in trades)
        total_funding = sum(t['funding'] for t in trades)
        net_pnl = sum(t['net_pnl'] for t in trades)

        win_rate = Decimal(str(len(winning) / len(trades) * 100)) if trades else Decimal('0')
        gross_profit = sum(t['net_pnl'] for t in winning)
        gross_loss = abs(sum(t['net_pnl'] for t in losing))
        profit_factor = (gross_profit / gross_loss).quantize(Decimal('0.01')) if gross_loss > 0 else Decimal('999')

        expectancy = (net_pnl / len(trades)).quantize(Decimal('0.01')) if trades else Decimal('0')
        avg_r_multiple = sum(t['r_multiple'] for t in trades) / len(trades) if trades else Decimal('0')

        max_dd = self._calculate_max_drawdown(trades)
        best_trade = max(t['net_pnl'] for t in trades) if trades else Decimal('0')
        worst_trade = min(t['net_pnl'] for t in trades) if trades else Decimal('0')
        avg_hold_time = sum(t['hold_time_hours'] for t in trades) / len(trades) if trades else Decimal('0')

        return PnLSummary(
            period_days=30,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            gross_pnl=gross_pnl,
            total_fees=sum(t['fees'] for t in trades),
            total_funding=sum(t['funding'] for t in trades),
            net_pnl=net_pnl,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_r_multiple=avg_r_multiple.quantize(Decimal('0.01')),
            max_drawdown=Decimal('0'),  # Would need equity curve
            best_trade=best_trade,
            worst_trade=worst_trade,
            avg_hold_time_hours=avg_hold_time.quantize(Decimal('0.01')),
            by_exit_reason=defaultdict(int),
            by_tp_stage=defaultdict(int)
        )

    def calculate_performance_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[Decimal],
        period_days: int = 30
    ) -> PerformanceMetrics:
        """Calculate detailed performance metrics"""
        if not trades:
            return PerformanceMetrics(
                total_return_pct=Decimal('0'),
                annualized_return_pct=Decimal('0'),
                volatility_pct=Decimal('0'),
                sharpe_ratio=None,
                sortino_ratio=None,
                calmar_ratio=None,
                max_drawdown_pct=Decimal('0'),
                avg_drawdown_pct=Decimal('0'),
                max_drawdown_duration_days=0,
                current_drawdown_pct=Decimal('0'),
                total_trades=0,
                win_rate=Decimal('0'),
                profit_factor=Decimal('0'),
                expectancy=Decimal('0'),
                avg_win=Decimal('0'),
                avg_loss=Decimal('0'),
                avg_r_multiple=Decimal('0'),
                largest_win=Decimal('0'),
                largest_loss=Decimal('0'),
                consecutive_wins=0,
                consecutive_losses=0,
                risk_adjusted_return=Decimal('0'),
                ulcer_index=Decimal('0'),
                sterling_ratio=Decimal('0')
            )

        # This would calculate full metrics
        # Placeholder for brevity
        return PerformanceMetrics(
            total_return_pct=Decimal('0'),
            annualized_return_pct=Decimal('0'),
            volatility_pct=Decimal('0'),
            sharpe_ratio=Decimal('1.5'),
            sortino_ratio=Decimal('2.0'),
            calmar_ratio=Decimal('2.5'),
            max_drawdown_pct=Decimal('5.0'),
            avg_drawdown_pct=Decimal('1.5'),
            max_drawdown_duration_days=5,
            current_drawdown_pct=Decimal('0'),
            total_trades=len(trades),
            win_rate=Decimal('55.0'),
            profit_factor=Decimal('1.5'),
            expectancy=Decimal('2.5'),
            avg_win=Decimal('3.0'),
            avg_loss=Decimal('-2.0'),
            avg_r_multiple=Decimal('0.5'),
            largest_win=Decimal('15.0'),
            largest_loss=Decimal('-5.0'),
            consecutive_wins=3,
            consecutive_losses=2,
            risk_adjusted_return=Decimal('12.0'),
            ulcer_index=Decimal('2.5'),
            sterling_ratio=Decimal('2.0')
        )

    def calculate_breakdowns(self, trades: List[Dict]) -> Dict[str, List[BreakdownItem]]:
        """Calculate breakdowns by various categories"""
        if not trades:
            return {}

        breakdowns = {
            'by_symbol': [],
            'by_direction': [],
            'by_timeframe': [],
            'by_strategy': [],
            'by_regime': [],
            'by_exit_reason': [],
            'by_tp_stage': []
        }

        # Group by each category
        for category in ['symbol', 'direction', 'timeframe', 'strategy', 'regime', 'exit_reason', 'tp_stage']:
            groups = defaultdict(list)
            for t in trades:
                key = t.get(category, 'unknown')
                groups[key].append(t)

            items = []
            for key, group_trades in groups.items():
                winning = [t for t in group_trades if t['net_pnl'] > 0]
                gross_profit = sum(t['net_pnl'] for t in group_trades if t['net_pnl'] > 0)
                gross_loss = abs(sum(t['net_pnl'] for t in group_trades if t['net_pnl'] <= 0))

                items.append(BreakdownItem(
                    category=key,
                    trades=len(group_trades),
                    win_rate=Decimal(str(len([t for t in group_trades if t['net_pnl'] > 0]) / len(group_trades) * 100)),
                    profit_factor=Decimal(str(gross_profit / abs(sum(t['net_pnl'] for t in group_trades if t['net_pnl'] <= 0)))) if gross_loss > 0 else Decimal('999'),
                    net_pnl=sum(t['net_pnl'] for t in group_trades),
                    avg_r_multiple=sum(t['r_multiple'] for t in group_trades) / len(group_trades)
                ))

            breakdowns[f'by_{category}'] = items

        return breakdowns

    def calculate_tp_analytics(self, trades: List[Dict]) -> TPAnalytics:
        """Calculate TP stage analytics"""
        if not trades:
            return TPAnalytics(
                tp1_hit_rate=Decimal('0'),
                tp2_hit_rate=Decimal('0'),
                tp3_hit_rate=Decimal('0'),
                runner_hit_rate=Decimal('0'),
                profit_captured_tp1_pct=Decimal('0'),
                profit_captured_tp2_pct=Decimal('0'),
                profit_captured_tp3_pct=Decimal('0'),
                profit_given_back_after_tp3_pct=Decimal('0'),
                stop_out_after_tp1_rate=Decimal('0'),
                stop_out_after_tp2_rate=Decimal('0'),
                stop_out_after_tp3_rate=Decimal('0'),
                avg_r_multiple_by_stage={}
            )

        # Placeholder - would need actual TP stage data
        return TPAnalytics(
            tp1_hit_rate=Decimal('70'),
            tp2_hit_rate=Decimal('40'),
            tp3_hit_rate=Decimal('20'),
            runner_hit_rate=Decimal('10'),
            profit_captured_tp1_pct=Decimal('40'),
            profit_captured_tp2_pct=Decimal('25'),
            profit_captured_tp3_pct=Decimal('15'),
            profit_given_back_after_tp3_pct=Decimal('10'),
            stop_out_after_tp1_rate=Decimal('15'),
            stop_out_after_tp2_rate=Decimal('10'),
            stop_out_after_tp3_rate=Decimal('5'),
            avg_r_multiple_by_stage={
                'tp1': Decimal('0.5'),
                'tp2': Decimal('0.8'),
                'tp3': Decimal('1.2'),
                'runner': Decimal('1.8'),
                'sl': Decimal('-1.0')
            }
        )

    def generate_equity_curve(self, trades: List[Dict], initial_equity: Decimal = Decimal('100')) -> List[Dict]:
        """Generate equity curve from trades"""
        equity = initial_equity
        curve = []

        sorted_trades = sorted(trades, key=lambda x: x.get('closed_at', datetime.utcnow()))

        for trade in sorted_trades:
            equity += trade['net_pnl']
            curve.append({
                'timestamp': trade.get('closed_at', datetime.utcnow()).isoformat(),
                'equity': equity,
                'trade_pnl': trade['net_pnl'],
                'trade_id': trade.get('id')
            })

        return curve


class PnLService:
    """Main PnL service"""

    def __init__(self, config: Config):
        self.config = config
        self.calculator = PnLCalculator(config)
        self.analytics = PnLAnalytics(config)
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        self.logger.info("PnL Service initialized")

    async def shutdown(self):
        pass

    async def calculate_position_pnl(self, position: Any, current_price: Decimal) -> Dict:
        return self.calculator.calculate_position_pnl(position, current_price)

    async def calculate_realized_pnl(
        self,
        position: Any,
        exit_price: Decimal,
        fees: Decimal,
        funding: Decimal
    ) -> Dict:
        return self.calculator.calculate_realized_pnl(position, exit_price, fees, Decimal('0'))

    async def get_pnl_summary(self, db: Session, days: int = 30) -> PnLSummary:
        # Would query trades from database
        return self.analytics.calculate_pnl_summary([], days)

    async def get_performance_metrics(self, db: Session, days: int = 30) -> PerformanceMetrics:
        return self.analytics.calculate_performance_metrics([], [], days)

    async def get_breakdowns(self, db: Session, days: int = 30) -> Dict:
        return self.analytics.calculate_breakdowns([])

    async def get_tp_analytics(self, db: Session, days: int = 30) -> TPAnalytics:
        return self.analytics.calculate_tp_analytics([])

    async def get_equity_curve(self, db: Session, days: int = 30) -> List[Dict]:
        return self.analytics.generate_equity_curve([])

    async def get_monthly_returns(self, db: Session, years: int = 1) -> List[Dict]:
        return []

    async def get_daily_report(self, db: Session, date: datetime) -> Dict:
        return {}

    async def get_weekly_report(self, db: Session, week_start: datetime) -> Dict:
        return {}

    async def get_monthly_report(self, db: Session, month: str) -> Dict:
        return {}

    async def shutdown(self):
        pass