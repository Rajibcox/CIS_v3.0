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
    Strategy, StrategyRule, Signal, Position
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
        """Load an active strategy and its canonical JSON rule groups."""
        if not strategy.is_active:
            self._strategy_cache.pop(strategy.id, None)
            self._rule_cache.pop(strategy.id, None)
            return

        rules = db.query(StrategyRule).filter(
            StrategyRule.strategy_id == strategy.id,
            StrategyRule.is_active.is_(True)
        ).all()
        # Validate persisted configuration before making it eligible for evaluation.
        for rule in rules:
            self._validate_rule_group(rule.rule_config)
        self._strategy_cache[strategy.id] = strategy
        self._rule_cache[strategy.id] = rules

    def load_active_strategies(self, db: Session) -> int:
        """Refresh the in-memory cache from persisted active strategies."""
        self._strategy_cache.clear()
        self._rule_cache.clear()
        strategies = db.query(Strategy).filter(Strategy.is_active.is_(True)).all()
        for strategy in strategies:
            self.load_strategy(strategy, db)
        return len(strategies)

    @staticmethod
    def _indicator_key(indicator: Any) -> str:
        """Map supported visual-builder indicators to scanner scalar keys."""
        if not isinstance(indicator, dict):
            raise ValueError("indicator must be an object")
        name = str(indicator.get("name", "")).upper()
        params = indicator.get("params") or {}
        source = indicator.get("source", "close")
        if source != "close":
            raise ValueError(f"Unsupported indicator source: {source}")

        fixed = {
            "RSI": ("rsi", {"period": 14}),
            "MACD": ("macd", {"fast": 12, "slow": 26, "signal": 9}),
            "ATR": ("atr", {"period": 14}),
            "ADX": ("adx", {"period": 14}),
            "VWAP": ("vwap", {"reset_period": "daily"}),
        }
        if name == "EMA":
            period = params.get("period", 9)
            if period not in (9, 21, 50):
                raise ValueError(f"EMA period {period} is not available from scanner data")
            expected = {"period": period}
            key = f"ema_{period}"
        elif name in fixed:
            key, expected = fixed[name]
        else:
            raise ValueError(f"Unsupported scanner indicator: {name or '<missing>'}")

        if params and params != expected:
            raise ValueError(f"Unsupported parameters for {name}: {params}")
        return key

    @classmethod
    def _validate_rule_group(cls, group: Any, depth: int = 0) -> None:
        """Reject malformed or unsupported rules before persistence/evaluation."""
        if depth > 12:
            raise ValueError("Rule groups exceed maximum nesting depth")
        if not isinstance(group, dict):
            raise ValueError("Rule group must be an object")
        operator = group.get("operator", "AND")
        if hasattr(operator, "value"):
            operator = operator.value
        if operator not in ("AND", "OR"):
            raise ValueError(f"Unsupported logical operator: {operator}")
        conditions = group.get("conditions") or []
        groups = group.get("groups") or []
        if not isinstance(conditions, list) or not isinstance(groups, list):
            raise ValueError("conditions and groups must be arrays")
        if not conditions and not groups:
            raise ValueError("Rule group cannot be empty")
        for condition in conditions:
            if not isinstance(condition, dict):
                raise ValueError("Rule condition must be an object")
            # Only the scanner-backed indicator-vs-number contract is executable.
            if set(condition) - {"indicator", "operator", "threshold"}:
                raise ValueError("Unsupported rule condition fields")
            cls._indicator_key(condition.get("indicator"))
            comparison = condition.get("operator")
            if hasattr(comparison, "value"):
                comparison = comparison.value
            if comparison not in (">", "<", ">=", "<=", "=="):
                raise ValueError(f"Unsupported comparison operator: {comparison}")
            threshold = condition.get("threshold")
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
                raise ValueError("Rule threshold must be numeric")
        for child in groups:
            cls._validate_rule_group(child, depth + 1)

    @staticmethod
    def _group_matches(group: Dict, indicators: Dict[str, float], timeframe: str) -> bool:
        """Evaluate nested AND/OR groups without treating missing data as a match."""
        results = []
        for condition in group.get("conditions") or []:
            indicator = condition["indicator"]
            key = StrategyEngine._indicator_key(indicator)
            timeframe_key = f"{key}_{timeframe}"
            # MarketScanner currently calculates its scalar indicator set from 1h candles.
            if timeframe_key in indicators:
                value = indicators[timeframe_key]
            elif timeframe == "1h" and key in indicators:
                value = indicators[key]
            else:
                value = None

            threshold = float(condition["threshold"])
            operator = condition["operator"]
            if value is None:
                matched = False
            elif operator == ">":
                matched = value > threshold
            elif operator == "<":
                matched = value < threshold
            elif operator == ">=":
                matched = value >= threshold
            elif operator == "<=":
                matched = value <= threshold
            else:
                matched = abs(value - threshold) < 0.0001
            results.append(matched)

        for child in group.get("groups") or []:
            results.append(StrategyEngine._group_matches(child, indicators, timeframe))

        if not results:
            return False
        operator = group.get("operator", "AND")
        return all(results) if operator == "AND" else any(results)

    def evaluate_entry(
        self,
        strategy_id: int,
        indicators: Dict[str, float],
        timeframe: str,
        direction: str = "BOTH"
    ) -> tuple:
        """Evaluate persisted entry rules; missing rules/data never qualify."""
        strategy = self._strategy_cache.get(strategy_id)
        rules = self._rule_cache.get(strategy_id, [])
        if strategy is None or not strategy.is_active:
            return False, {}
        entry_rules = [rule for rule in rules if rule.rule_type == "entry"]
        if not entry_rules:
            return False, {}

        groups = [rule.rule_config for rule in entry_rules]
        if direction.upper() == "LONG":
            groups.extend(rule.rule_config for rule in rules if rule.rule_type == "long")
        elif direction.upper() == "SHORT":
            groups.extend(rule.rule_config for rule in rules if rule.rule_type == "short")
        if not all(self._group_matches(group, indicators, timeframe) for group in groups):
            return False, {}
        return True, {"matched_rule_types": ["entry"] + ([direction.lower()] if direction.upper() in ("LONG", "SHORT") else [])}

    def evaluate_exit(
        self,
        strategy_id: int,
        indicators: Dict[str, float],
        position: Any,
        timeframe: str
    ) -> tuple:
        """Evaluate persisted exit rules."""
        rules = self._rule_cache.get(strategy_id, [])
        exit_rules = [rule for rule in rules if rule.rule_type == "exit"]
        if not exit_rules:
            return False, ""
        matched = all(
            self._group_matches(rule.rule_config, indicators, timeframe)
            for rule in exit_rules
        )
        return matched, "strategy_exit" if matched else ""



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

    @staticmethod
    def _plain_rule_set(rule_set: Any) -> Dict:
        if hasattr(rule_set, "model_dump"):
            return rule_set.model_dump(mode="json", exclude_none=True)
        if hasattr(rule_set, "dict"):
            return rule_set.dict(exclude_none=True)
        if not isinstance(rule_set, dict):
            raise ValueError("rule_set must be an object")
        return rule_set

    @classmethod
    def _normalize_rule_set(cls, rule_set: Any) -> Dict[str, Dict]:
        """Normalize API *_rules keys to persisted rule_type values."""
        data = cls._plain_rule_set(rule_set)
        aliases = {
            "entry_rules": "entry", "exit_rules": "exit",
            "long_rules": "long", "short_rules": "short",
            # Accept the service's original internal names for compatibility.
            "entry": "entry", "exit": "exit", "long": "long", "short": "short",
        }
        normalized = {}
        for key, value in data.items():
            if key not in aliases:
                raise ValueError(f"Unsupported rule set key: {key}")
            if value is None:
                continue
            StrategyEngine._validate_rule_group(value)
            rule_type = aliases[key]
            if rule_type in normalized:
                raise ValueError(f"Duplicate rule set for {rule_type}")
            normalized[rule_type] = value
        if "entry" not in normalized:
            raise ValueError("An entry rule group is required")
        return normalized

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
        """Persist strategy metadata and canonical nested rule JSON atomically."""
        normalized_rules = self._normalize_rule_set(rule_set)
        strategy = Strategy(
            name=name, description=description, version=version,
            direction=direction.lower(), weight=weight,
            risk_multiplier=risk_multiplier, timeframes=timeframes,
            symbols=symbols, min_signal_score=min_signal_score,
            is_active=True, created_by=created_by,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        try:
            db.add(strategy)
            db.flush()
            for rule_type, rule_config in normalized_rules.items():
                db.add(StrategyRule(
                    strategy_id=strategy.id,
                    rule_type=rule_type,
                    rule_config=rule_config,
                    is_active=True
                ))
            db.commit()
            db.refresh(strategy)
        except Exception:
            db.rollback()
            raise
        self.engine.load_strategy(strategy, db)
        return strategy.id

    async def update_strategy(
        self,
        db: Session,
        strategy_id: int,
        updates: Dict
    ) -> bool:
        """Update strategy metadata and replace rule JSON in one transaction."""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False
        allowed = {
            "name", "description", "version", "is_active", "direction",
            "weight", "risk_multiplier", "timeframes", "symbols",
            "min_signal_score"
        }
        unknown = set(updates) - allowed - {"rule_set"}
        if unknown:
            raise ValueError(f"Unsupported strategy fields: {sorted(unknown)}")
        normalized_rules = None
        if "rule_set" in updates:
            normalized_rules = self._normalize_rule_set(updates["rule_set"])
        try:
            for key, value in updates.items():
                if key == "rule_set":
                    continue
                if key == "direction" and isinstance(value, str):
                    value = value.lower()
                setattr(strategy, key, value)
            if normalized_rules is not None:
                db.query(StrategyRule).filter(
                    StrategyRule.strategy_id == strategy_id
                ).delete(synchronize_session=False)
                for rule_type, rule_config in normalized_rules.items():
                    db.add(StrategyRule(
                        strategy_id=strategy_id,
                        rule_type=rule_type,
                        rule_config=rule_config,
                        is_active=True
                    ))
            strategy.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(strategy)
        except Exception:
            db.rollback()
            raise
        if strategy.is_active:
            self.engine.load_strategy(strategy, db)
        else:
            self.engine._strategy_cache.pop(strategy_id, None)
            self.engine._rule_cache.pop(strategy_id, None)
        return True

    async def delete_strategy(self, db: Session, strategy_id: int) -> bool:
        """Delete (deactivate) strategy"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False

        strategy.is_active = False
        strategy.updated_at = datetime.utcnow()
        db.commit()
        self.engine._strategy_cache.pop(strategy_id, None)
        self.engine._rule_cache.pop(strategy_id, None)
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
        rule_sets = db.query(StrategyRule).filter(
            StrategyRule.strategy_id == strategy_id
        ).all()

        for rs in rule_sets:
            new_rs = StrategyRule(
                strategy_id=new_strategy.id,
                rule_type=rs.rule_type,
                rule_config=rs.rule_config,
                weight=rs.weight,
                is_active=rs.is_active
            )
            db.add(new_rs)

        db.commit()
        return new_strategy.id

    async def get_strategy(self, db: Session, strategy_id: int) -> Optional[Dict]:
        """Get strategy with rules"""
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None

        rule_sets = db.query(StrategyRule).filter(
            StrategyRule.strategy_id == strategy_id
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
                'symbols': s.symbols,
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


