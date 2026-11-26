"""
Strategy Service for QUANTUM TRADER V1
Manages trading strategies, rule sets, and performance tracking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.backend.models.database import (
    Strategy, StrategyRule, StrategyRuleSet, Signal, Position
)
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


@dataclass
class RuleCondition:
    """A single rule condition"""
    indicator: str
    timeframe: str
    operator: str  # >, <, >=, <=, ==, crosses_above, crosses_below
    threshold: float
    lookback: int = 1


@dataclass
class RuleGroup:
    """A group of conditions combined with AND/OR"""
    operator: str = "AND"  # AND, OR
    conditions: List[RuleCondition] = field(default_factory=list)
    groups: List["RuleGroup"] = field(default_factory=list)


@dataclass
class StrategyRuleSet:
    """Complete rule set for a strategy"""
    entry_rules: RuleGroup
    exit_rules: RuleGroup
    long_rules: Optional[RuleGroup] = None
    short_rules: Optional[RuleGroup] = None


@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_id: int
    strategy_name: str
    period_days: int
    total_signals: int
    executed_signals: int
    win_rate: float
    loss_rate: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    avg_r_multiple: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    by_symbol: Dict[str, Dict] = field(default_factory=dict)
    by_timeframe: Dict[str, Dict] = field(default_factory=dict)
    by_direction: Dict[str, Dict] = field(default_factory=dict)
    by_regime: Dict[str, Dict] = field(default_factory=dict)
    equity_curve: List[Dict] = field(default_factory=list)


class StrategyEngine:
    """Core strategy evaluation engine"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._strategy_cache: Dict[int, Strategy] = {}
        self._rule_cache: Dict[int, List[StrategyRule]] = {}

    def load_strategy(self, strategy: Strategy, db: Session):
        """Load strategy into cache"""
        self._strategy_cache[strategy.id] = strategy
        rules = db.query(StrategyRule).filter(
            StrategyRule.strategy_id == strategy.id,
            StrategyRule.is_active == True
        ).all()
        self._rule_cache[strategy.id] = rules

    def evaluate_entry(
        self,
        strategy_id: int,
        indicators: Dict[str, float],
        timeframe: str,
        direction: str = "BOTH"
    ) -> tuple:
        """
        Evaluate entry conditions for a strategy
        Returns: (should_enter: bool, signal_data: dict)
        """
        if strategy_id not in self._rule_cache:
            return False, {}

        rules = self._rule_cache[strategy_id]
        entry_rules = [r for r in rules if r.rule_type == 'entry']

        if not entry_rules:
            return False, {}

        # Evaluate rule groups
        should_enter, signal_data = self._evaluate_rules(
            entry_rules, indicators, timeframe, direction
        )

        return should_enter, signal_data

    def evaluate_exit(
        self,
        strategy_id: int,
        indicators: Dict[str, float],
        position: Any,
        timeframe: str
    ) -> tuple:
        """
        Evaluate exit conditions for a strategy
        Returns: (should_exit: bool, exit_reason: str)
        """
        if strategy_id not in self._rule_cache:
            return False, ""

        rules = self._rule_cache[strategy_id]
        exit_rules = [r for r in rules if r.rule_type == 'exit']

        if not exit_rules:
            return False, ""

        should_exit, exit_reason = self._evaluate_rules(
            exit_rules, indicators, timeframe, position.direction
        )

        return should_exit, exit_reason

    def _evaluate_rules(
        self,
        rules: List,
        indicators: Dict[str, float],
        timeframe: str,
        direction: str
    ) -> tuple:
        """Evaluate a list of rules"""
        # Group rules by group_id
        groups = {}
        for rule in rules:
            if rule.group_id not in groups:
                groups[rule.group_id] = []
            groups[rule.group_id].append(rule)

        # Each group is OR'd together, groups are AND'd
        group_results = []
        for group_id, group_rules in groups.items():
            group_result = False
            for rule in group_rules:
                if self._evaluate_condition(rule, indicators, timeframe):
                    group_result = True
                    break  # OR within group
            group_results.append(group_result)

        # All groups must pass (AND)
        should_enter = all(group_results)

        return should_enter, {}

    def _evaluate_condition(self, rule: StrategyRule, indicators: Dict[str, float], timeframe: str) -> bool:
        """Evaluate a single rule condition"""
        indicator_key = f"{rule.indicator}_{timeframe}"

        if indicator_key not in indicators:
            # Try without timeframe
            if rule.indicator not in indicators:
                return False
            indicator_key = rule.indicator

        value = indicators[indicator_key]
        threshold = rule.threshold

        if rule.operator == '>':
            return value > threshold
        elif rule.operator == '<':
            return value < threshold
        elif rule.operator == '>=':
            return value >= threshold
        elif rule.operator == '<=':
            return value <= threshold
        elif rule.operator == '==':
            return abs(value - threshold) < 0.0001
        elif rule.operator == 'crosses_above':
            # Would need previous value
            return False
        elif rule.operator == 'crosses_below':
            return False

        return False


class StrategyService:
    """Main strategy management service"""

    def __init__(self, config: Config, market_data_service: Any = None):
        self.config = config
        self.market_data_service = market_data_service
        self.engine = StrategyEngine(config)
        self.logger = logging.getLogger(__name__)
        self._running = False

    async def initialize(self):
        """Initialize strategy service"""
        self.logger.info("Initializing Strategy Service...")
        self._running = True
        self.logger.info("Strategy Service initialized")

    async def shutdown(self):
        """Shutdown strategy service"""
        self.logger.info("Shutting down Strategy Service...")
        self._running = False

    async def create_strategy(
        self,
        db: Session,
        name: str,
        description: str,
        version: str,
        direction: str,
        weight: float,
        risk_multiplier: float,
        timeframes: List[str],
        symbols: List[str],
        min_signal_score: float,
        rule_set: Dict,
        created_by: str = "system"
    ) -> int:
        """Create a new strategy"""
        strategy = Strategy(
            name=name,
            description=description,
            version=version,
            direction=direction,
            weight=weight,
            risk_multiplier=risk_multiplier,
            timeframes=timeframes,
            symbols=symbols,
            min_signal_score=min_signal_score,
            is_active=True,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(strategy)
        db.flush()

        # Create rule sets
        rule_sets = [
            ('entry', 'entry'),
            ('exit', 'exit'),
            ('long', 'long'),
            ('short', 'short')
        ]

        for key, rule_type in rule_sets:
            if key in rule_set and rule_set[key]:
                rule_set_obj = StrategyRuleSet(
                    strategy_id=strategy.id,
                    rule_type=rule_type,
                    rules=rule_set[key]
                )
                db.add(rule_set_obj)

        db.commit()
        return strategy.id

    async def update_strategy(
        self,
        db: Session,
        strategy_id: int,
        updates: Dict
    ) -> bool:
        """Update strategy"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False

        for key, value in updates.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)

        strategy.updated_at = datetime.utcnow()
        db.commit()
        return True

    async def delete_strategy(self, db: Session, strategy_id: int) -> bool:
        """Delete (deactivate) strategy"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False

        strategy.is_active = False
        strategy.updated_at = datetime.utcnow()
        db.commit()
        return True

    async def clone_strategy(self, db: Session, strategy_id: int, new_name: str) -> int:
        """Clone an existing strategy"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return 0

        new_strategy = Strategy(
            name=new_name,
            description=strategy.description,
            version="1.0.0",
            direction=strategy.direction,
            weight=strategy.weight,
            risk_multiplier=strategy.risk_multiplier,
            timeframes=strategy.timeframes,
            symbols=strategy.symbols,
            min_signal_score=strategy.min_signal_score,
            is_active=False,
            created_by="user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_strategy)
        db.flush()

        # Copy rule sets
        rule_sets = db.query(StrategyRuleSet).filter(
            StrategyRuleSet.strategy_id == strategy_id
        ).all()

        for rs in rule_sets:
            new_rs = StrategyRuleSet(
                strategy_id=new_strategy.id,
                rule_type=rs.rule_type,
                rules=rs.rules
            )
            db.add(new_rs)

        db.commit()
        return new_strategy.id

    async def get_strategy(self, db: Session, strategy_id: int) -> Optional[Dict]:
        """Get strategy with rules"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None

        rule_sets = db.query(StrategyRuleSet).filter(
            StrategyRuleSet.strategy_id == strategy_id
        ).all()

        return {
            'strategy': strategy,
            'rule_sets': rule_sets
        }

    async def list_strategies(
        self,
        db: Session,
        active_only: bool = False,
        include_performance: bool = False
    ) -> List[Dict]:
        """List all strategies"""
        query = db.query(Strategy)
        if active_only:
            query = query.filter(Strategy.is_active == True)

        strategies = query.all()
        results = []

        for s in strategies:
            result = {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'version': s.version,
                'is_active': s.is_active,
                'direction': s.direction,
                'weight': s.weight,
                'risk_multiplier': s.risk_multiplier,
                'timeframes': s.timeframes,
                'min_signal_score': s.min_signal_score,
                'created_by': s.created_by,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            }

            if include_performance:
                # Would calculate performance metrics
                result['performance'] = await self._get_performance_summary(s.id)

            results.append(result)

        return results

    async def get_performance(
        self,
        db: Session,
        strategy_id: int,
        days: int = 30
    ) -> StrategyPerformance:
        """Get strategy performance metrics"""
        # This would calculate actual performance from signals/positions
        # Placeholder implementation
        return StrategyPerformance(
            strategy_id=strategy_id,
            strategy_name="Strategy",
            version="1.0.0",
            period_days=days,
            total_signals=0,
            executed_signals=0,
            win_rate=0.0,
            loss_rate=0.0,
            profit_factor=0.0,
            expectancy=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            avg_r_multiple=0.0,
            max_drawdown=0.0
        )

    async def compare_strategies(
        self,
        db: Session,
        strategy_ids: List[int],
        days: int = 30
    ) -> List[StrategyPerformance]:
        """Compare multiple strategies"""
        results = []
        for sid in strategy_ids:
            perf = await self.get_performance(db, sid, days)
            results.append(perf)
        return results

    async def run_backtest(
        self,
        db: Session,
        strategy_id: int,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframes: List[str],
        initial_capital: float = 100.0,
        fees_bps: float = 10.0,
        slippage_bps: float = 5.0
    ) -> Dict:
        """Run backtest for a strategy"""
        # This would run a full backtest
        # Placeholder implementation
        return {
            'backtest_id': f"bt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'strategy_id': strategy_id,
            'status': 'completed',
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'symbols': symbols,
            'initial_capital': initial_capital,
            'final_equity': initial_capital * 1.1,
            'total_return_pct': 10.0,
            'metrics': {}
        }

    async def _get_performance_summary(self, strategy_id: int) -> Dict:
        """Get performance summary for a strategy"""
        return {
            'win_rate_30d': 0.0,
            'profit_factor_30d': 0.0,
            'expectancy_30d': 0.0,
            'signal_count_24h': 0
        }

    async def shutdown(self):
        """Shutdown strategy service"""
        pass


