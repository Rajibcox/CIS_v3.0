"""
Signal Service for QUANTUM TRADER V1
Manages signal generation, lifecycle, and scoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session

from src.backend.models.database import (
    Signal, SignalStatus, SignalDirection, MarketRegime, Strategy, StrategyRule
)
from src.backend.services.market_data_service import MarketDataService
from src.backend.services.market_regime_service import MarketRegimeService, RegimeType
from src.backend.services.strategy_service import StrategyService
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger, log_service_event


logger = logging.getLogger(__name__)


class SignalEventType(Enum):
    """Signal lifecycle events"""
    CREATED = "created"
    QUALIFIED = "qualified"
    ACTIVATED = "activated"
    TRIGGERED = "triggered"
    EXECUTED = "executed"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    REJECTED = "rejected"


@dataclass
class SignalCandidate:
    """A potential signal before validation"""
    symbol: str
    exchange: str
    direction: SignalDirection
    strategy: str
    timeframe: str
    regime: str
    entry_price: Decimal
    stop_loss: Decimal
    tp1: Decimal
    tp2: Decimal
    tp3: Decimal
    runner_quantity: Decimal
    risk_reward: float
    signal_score: float
    confidence: float
    supporting_evidence: List[str]
    invalidating_conditions: List[str]
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    market_structure: Dict
    indicators: Dict
    higher_timeframe_context: Dict
    btc_correlation: float
    estimated_fees: Decimal
    estimated_funding: Decimal
    net_pnl_tp1: Decimal
    net_pnl_tp2: Decimal
    net_pnl_tp3: Decimal
    net_pnl_runner: Decimal
    suggested_leverage: int
    position_quantity: Decimal
    notional: Decimal
    required_margin: Decimal
    leverage_decision: Dict


@dataclass
class SignalEvent:
    """Signal lifecycle event"""
    signal_id: int
    event_type: SignalEventType
    timestamp: datetime
    details: Dict
    price: Optional[Decimal] = None


@dataclass(frozen=True)
class StrategyMatch:
    """A real entry-rule match; not an actionable or executable signal."""
    strategy_id: int
    strategy_name: str
    strategy_version: str
    symbol: str
    exchange: str
    direction: str
    timeframe: str
    regime: str
    current_price: Optional[Decimal]
    matched_rule_types: List[str]
    indicators: Dict[str, float]


class SignalScorer:
    """Scores and validates signal candidates"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def score_candidate(self, candidate: SignalCandidate, regime_state: Any) -> float:
        """Score a signal candidate (0-100)"""
        score = 0.0
        max_score = 0.0

        # 1. Trend alignment (20 points)
        max_score += 20
        if candidate.higher_timeframe_context.get('trend_alignment', False):
            score += 20
        elif candidate.higher_timeframe_context.get('trend_neutral', False):
            score += 10

        # 2. BTC correlation (15 points)
        max_score += 15
        btc_corr = candidate.btc_correlation
        if candidate.direction == SignalDirection.LONG and btc_corr > 0.3:
            score += 15
        elif candidate.direction == SignalDirection.SHORT and btc_corr < -0.3:
            score += 15
        elif abs(btc_corr) < 0.2:
            score += 10

        # 3. Regime match (15 points)
        max_score += 15
        if regime and candidate.regime in ['trending', 'breakout']:
            score += 15
        elif candidate.regime in ['ranging', 'volatile']:
            score += 10

        # 4. Volume confirmation (10 points)
        max_score += 10
        if candidate.indicators.get('volume_ratio', 1) > 1.2:
            score += 10
        elif candidate.indicators.get('volume_ratio', 1) > 1.0:
            score += 5

        # 5. Risk/Reward ratio (15 points)
        max_score += 15
        rr = candidate.risk_reward
        if rr >= 3.0:
            score += 15
        elif rr >= 2.5:
            score += 12
        elif rr >= 2.0:
            score += 10
        elif rr >= 1.5:
            score += 5

        # 6. Entry quality (10 points)
        max_score += 10
        entry_quality = self._calculate_entry_quality(candidate)
        score += entry_quality * 10

        # 2. Momentum alignment (10 points)
        max_score += 10
        if self._check_momentum_alignment(candidate):
            score += 10

        # Normalize to 0-100
        final_score = (score / max_score * 100) if max_score > 0 else 0
        return min(100, max(0, final_score))

    def _calculate_entry_quality(self, candidate: SignalCandidate) -> float:
        """Calculate entry quality (0-1)"""
        quality = 0.5  # Base

        # Distance from entry zone
        price = candidate.indicators.get('current_price', candidate.entry_price)
        entry_mid = (candidate.entry_zone_low + candidate.entry_zone_high) / 2
        distance_pct = abs(float(price) - float(entry_mid)) / float(entry_mid)

        if distance_pct < 0.002:  # Within 0.2%
            quality += 0.3
        elif distance_pct < 0.005:  # Within 0.5%
            quality += 0.2
        elif distance_pct < 0.01:  # Within 1%
            quality += 0.1

        # RSI alignment
        rsi = candidate.indicators.get('rsi', 50)
        if candidate.direction == SignalDirection.LONG and rsi < 40:
            quality += 0.2
        elif candidate.direction == SignalDirection.SHORT and rsi > 60:
            quality += 0.2

        return min(1.0, quality)

    def _check_momentum_alignment(self, candidate: SignalCandidate) -> bool:
        """Check if momentum aligns with signal direction"""
        macd = candidate.indicators.get('macd', 0)
        macd_signal = candidate.indicators.get('macd_signal', 0)

        if candidate.direction == SignalDirection.LONG:
            return macd > macd_signal
        else:
            return macd < macd_signal

    def validate_candidate(self, candidate: SignalCandidate) -> tuple:
        """Validate candidate meets minimum requirements"""
        errors = []

        # Risk/Reward minimum
        if candidate.risk_reward < 1.5:
            errors.append(f"Risk/Reward too low: {candidate.risk_reward:.2f} < 1.5")

        # Minimum stop distance
        stop_dist_pct = abs(float(candidate.entry_price) - float(candidate.stop_loss)) / float(candidate.entry_price)
        if stop_dist_pct < 0.005:  # 0.5%
            errors.append(f"Stop distance too small: {stop_dist_pct*100:.2f}% < 0.5%")

        # Entry price validation
        if candidate.direction == SignalDirection.LONG:
            if candidate.stop_loss >= candidate.entry_price:
                errors.append("Stop loss must be below entry for LONG")
            if candidate.tp1 <= candidate.entry_price:
                errors.append("TP1 must be above entry for LONG")
        else:
            if candidate.stop_loss <= candidate.entry_price:
                errors.append("Stop loss must be above entry for SHORT")
            if candidate.tp1 >= candidate.entry_price:
                errors.append("TP1 must be below entry for SHORT")

        # TP ordering
        if candidate.direction == SignalDirection.LONG:
            if not (candidate.entry_price < candidate.tp1 < candidate.tp2 < candidate.tp3):
                errors.append("TP levels must be in ascending order for LONG")
        else:
            if not (candidate.entry_price > candidate.tp1 > candidate.tp2 > candidate.tp3):
                errors.append("TP levels must be in descending order for SHORT")

        return len(errors) == 0, errors


class SignalGenerator:
    """Generates signal candidates from market data"""

    def __init__(self, config: Config, strategy_service: StrategyService):
        self.config = config
        self.strategy_service = strategy_service
        self.logger = logging.getLogger(__name__)

    async def generate_signals(
        self,
        snapshot: Any,
        regime_state: Any,
        strategy: Strategy
    ) -> List[SignalCandidate]:
        """Generate signal candidates for a snapshot"""
        candidates = []

        for rule_set in strategy.rule_sets:
            if not rule_set.is_active:
                continue

            # Check entry conditions
            if not self._check_entry_conditions(snapshot, rule_set.entry_rules):
                continue

            # Generate candidate
            candidate = self._create_candidate(snapshot, regime_state, strategy)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _check_entry_conditions(self, snapshot: Any, rules: Any) -> bool:
        """Check if entry conditions are met"""
        # This would evaluate the rule set against snapshot indicators
        # Simplified for now
        return True

    def _create_candidate(
        self,
        snapshot: Any,
        regime_state: Any,
        strategy: Strategy
    ) -> Optional[Any]:
        """Create a signal candidate from snapshot"""
        # This would create a full SignalCandidate with all calculations
        # Placeholder for now
        return None


class SignalLifecycleManager:
    """Manages signal lifecycle transitions"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._signal_timers: Dict[int, asyncio.Task] = {}

    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def transition(
        self,
        signal_id: int,
        new_status: str,
        db: Session,
        price: Optional[Decimal] = None,
        details: Optional[Dict] = None
    ) -> bool:
        """Transition signal to new status"""
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return False

        old_status = signal.status
        valid_transitions = self._get_valid_transitions(old_status)

        if new_status not in valid_transitions:
            self.logger.warning(f"Invalid transition: {old_status} -> {new_status}")
            return False

        # Update signal
        signal.status = new_status
        signal.updated_at = datetime.utcnow()

        if new_status == 'triggered':
            signal.triggered_at = datetime.utcnow()
        elif new_status == 'executed':
            signal.executed_at = datetime.utcnow()

        db.commit()

        # Trigger handlers
        await self._trigger_handlers(SignalEventType(new_status), signal, price, details)

        return True

    def _get_valid_transitions(self, status: str) -> List[str]:
        """Get valid status transitions"""
        transitions = {
            'candidate': ['qualified', 'rejected', 'expired'],
            'qualified': ['active', 'rejected', 'expired'],
            'active': ['triggered', 'invalidated', 'expired'],
            'triggered': ['executed', 'invalidated'],
            'executed': [],
            'expired': [],
            'invalidated': [],
            'rejected': []
        }
        return transitions.get(status, [])

    async def _trigger_handlers(
        self,
        event_type: str,
        signal: Any,
        price: Optional[Decimal] = None,
        details: Optional[Dict] = None
    ):
        """Trigger event handlers"""
        event_type_str = event_type.value if hasattr(event_type, 'value') else event_type
        handlers = self._event_handlers.get(event_type_str, [])

        for handler in self._event_handlers.get(event_type_str, []):
            try:
                await handler(signal, price, details)
            except Exception as e:
                logging.getLogger(__name__).error(f"Handler error: {e}")

    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)


class SignalService:
    """Main signal service coordinating generation, scoring, and lifecycle"""

    def __init__(
        self,
        config: Config,
        market_data_service: MarketDataService,
        market_regime_service: Any,
        strategy_service: Any,
        market_scanner: Any = None,
        session_factory: Any = None,
    ):
        self.config = config
        self.market_data_service = market_data_service
        self.market_regime_service = market_regime_service
        self.strategy_service = strategy_service
        self.market_scanner = market_scanner
        self.session_factory = session_factory
        self.logger = logging.getLogger(__name__)

        self.scorer = SignalScorer(config)
        self.generator = SignalGenerator(config, strategy_service)
        self.lifecycle = SignalLifecycleManager(config)

        self._running = False
        self._generation_task: Optional[asyncio.Task] = None
        self._active_signals: Dict[int, Any] = {}
        self._signal_callbacks: List[Callable] = []
        self._last_strategy_matches: List[StrategyMatch] = []

    @property
    def latest_strategy_matches(self) -> List[StrategyMatch]:
        """Return the most recent rule matches without exposing internal list mutation."""
        return list(self._last_strategy_matches)

    async def initialize(self):
        """Initialize signal service"""
        self.logger.info("Initializing Signal Service...")
        self._running = True
        # Retain the task so shutdown can reliably cancel and await it.
        if self._generation_task is None or self._generation_task.done():
            self._generation_task = asyncio.create_task(self._generation_loop())
        self.logger.info("Signal Service initialized")

    async def shutdown(self):
        """Shutdown signal service"""
        self.logger.info("Shutting down Signal Service...")
        self._running = False

    async def _generation_loop(self):
        """Background loop for signal generation"""
        while self._running:
            try:
                await self._generate_signals()
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in generation loop: {e}")
            await asyncio.sleep(300)  # Every 5 minutes

    async def generate_signals_now(self) -> List[Any]:
        """Manually trigger signal generation"""
        return await self._generate_signals()

    def evaluate_strategy_matches(self) -> List[StrategyMatch]:
        """Evaluate active persisted entry rules against the latest raw snapshots.

        This stage deliberately stops at rule matching. It does not construct a
        SignalCandidate, infer stop/target levels, persist a signal, or execute
        an order. Those require the later trade-plan and qualification stages.
        """
        self._last_strategy_matches = []
        scanner = self.market_scanner
        strategy_engine = getattr(self.strategy_service, "engine", None)
        if scanner is None or strategy_engine is None:
            return []

        snapshots = getattr(scanner, "latest_snapshots", None)
        if not isinstance(snapshots, dict) or not snapshots:
            return []

        strategies = getattr(strategy_engine, "_strategy_cache", {})
        rules_by_strategy = getattr(strategy_engine, "_rule_cache", {})
        matches: List[StrategyMatch] = []

        for strategy_id, strategy in strategies.items():
            if not getattr(strategy, "is_active", False):
                continue
            if not rules_by_strategy.get(strategy_id):
                continue

            configured_symbols = getattr(strategy, "symbols", None) or []
            allowed_symbols = {str(symbol).upper() for symbol in configured_symbols}
            configured_timeframes = getattr(strategy, "timeframes", None) or []
            if not isinstance(configured_timeframes, (list, tuple)):
                continue
            timeframes = list(dict.fromkeys(
                str(timeframe).lower() for timeframe in configured_timeframes
                if isinstance(timeframe, str) and timeframe
            ))
            if not timeframes:
                continue

            strategy_direction = str(
                getattr(strategy, "direction", "both") or "both"
            ).lower()
            if strategy_direction == "long":
                directions = ("LONG",)
            elif strategy_direction == "short":
                directions = ("SHORT",)
            elif strategy_direction in ("both", "buy_sell"):
                directions = ("LONG", "SHORT")
            else:
                continue

            for snapshot in snapshots.values():
                symbol = getattr(snapshot, "symbol", None)
                exchange = getattr(snapshot, "exchange", None)
                indicators = getattr(snapshot, "indicators", None)
                if not symbol or not exchange or not isinstance(indicators, dict) or not indicators:
                    continue
                if allowed_symbols and str(symbol).upper() not in allowed_symbols:
                    continue

                for timeframe in timeframes:
                    for direction in directions:
                        matched, evidence = strategy_engine.evaluate_entry(
                            strategy_id, indicators, timeframe, direction
                        )
                        if not matched:
                            continue
                        ticker = getattr(snapshot, "ticker", None)
                        price = getattr(ticker, "price", None) if ticker is not None else None
                        matches.append(StrategyMatch(
                            strategy_id=strategy_id,
                            strategy_name=strategy.name,
                            strategy_version=strategy.version,
                            symbol=str(symbol),
                            exchange=str(exchange),
                            direction=direction,
                            timeframe=timeframe,
                            regime=str(getattr(snapshot, "regime", "unknown")),
                            current_price=price,
                            matched_rule_types=list(evidence.get("matched_rule_types", [])),
                            indicators=dict(indicators),
                        ))

        self._last_strategy_matches = matches
        return list(matches)

    async def _generate_signals(self) -> List[Any]:
        """Run genuine strategy matching without fabricating actionable signals."""
        matches = self.evaluate_strategy_matches()
        if matches:
            self.logger.info(
                "Strategy evaluation completed: %s rule matches; "
                "trade-plan qualification is not yet enabled.",
                len(matches),
            )
        else:
            self.logger.info("Strategy evaluation completed: no qualifying rule matches.")
        # A rule match is not yet a SignalCandidate: strategy-specific entry,
        # stop-loss, targets, costs, and risk checks are still required.
        return []

    def register_callback(self, callback: Callable):
        """Register callback for new signals"""
        self._signal_callbacks.append(callback)

    async def get_signals(
        self,
        db: Session,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        strategy_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Any]:
        """Get signals with filters"""
        query = db.query(Signal)

        # Filters would be applied here
        return query.order_by(Signal.created_at.desc()).limit(50).all()

    async def get_signal_detail(self, db: Session, signal_id: int) -> Optional[Dict]:
        """Get detailed signal information"""
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return None

        # Build detailed response
        return {
            'signal': signal,
            'market_context': {},
            'risk_calculation': {},
            'leverage_decision': {}
        }

    async def execute_paper_trade(self, db: Session, signal_id: int) -> Dict:
        """Execute a paper trade from a signal"""
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return {"success": False, "error": "Signal not found"}

        # This would call execution service
        return {"success": True, "position_id": 123}

    async def shutdown(self):
        """Stop the signal generation loop and wait for it to finish."""
        self._running = False
        if self._generation_task is not None:
            self._generation_task.cancel()
            try:
                await self._generation_task
            except asyncio.CancelledError:
                pass
            finally:
                self._generation_task = None


async def create_signal_service(
    config: Config,
    market_data_service: MarketDataService,
    market_regime_service: Any,
    strategy_service: Any
) -> SignalService:
    """Create and initialize signal service"""
    service = SignalService(
        config, market_data_service, market_regime_service, strategy_service
    )
    await service.initialize()
    return service
