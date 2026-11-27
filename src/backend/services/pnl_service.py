"""PnL calculation, reconciliation, and persistence for paper positions."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.backend.models.database import (
    Order,
    OrderStatus,
    PnL_Entry,
    Position,
    PositionStatus,
)
from src.backend.utils.config import Config


logger = logging.getLogger(__name__)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value if value is not None else 0))
    except Exception as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _direction(position: Any) -> str:
    value = getattr(position, "direction", None)
    value = getattr(value, "value", value)
    normalized = str(value).upper()
    if normalized not in {"LONG", "SHORT"}:
        raise ValueError(f"Unsupported position direction: {value!r}")
    return normalized


@dataclass
class TradePnL:
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
    category: str
    trades: int
    win_rate: Decimal
    profit_factor: Decimal
    net_pnl: Decimal
    avg_r_multiple: Decimal


@dataclass
class TPAnalytics:
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
    """Pure Decimal PnL arithmetic."""

    def __init__(self, config: Config):
        self.config = config

    def calculate_trade_pnl(
        self,
        entry_price: Decimal,
        exit_price: Decimal,
        quantity: Decimal,
        direction: str,
        entry_fees: Decimal,
        exit_fees: Decimal,
        funding: Decimal,
    ) -> Dict[str, Decimal]:
        entry = _decimal(entry_price, "entry_price")
        exit_ = _decimal(exit_price, "exit_price")
        qty = _decimal(quantity, "quantity")
        entry_fee = _decimal(entry_fees, "entry_fees")
        exit_fee = _decimal(exit_fees, "exit_fees")
        funding_cost = _decimal(funding, "funding")
        side = str(direction).upper()
        if side not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")
        if entry <= 0 or exit_ <= 0 or qty <= 0:
            raise ValueError("prices and quantity must be positive")
        if entry_fee < 0 or exit_fee < 0:
            raise ValueError("fees cannot be negative")

        gross = (exit_ - entry) * qty
        if side == "SHORT":
            gross = -gross
        total_fees = entry_fee + exit_fee
        return {
            "gross_pnl": gross,
            "total_fees": total_fees,
            "funding": funding_cost,
            "net_pnl": gross - total_fees - funding_cost,
        }

    def calculate_r_multiple(self, net_pnl: Decimal, planned_risk: Decimal) -> Decimal:
        risk = _decimal(planned_risk, "planned_risk")
        return Decimal("0") if risk == 0 else (_decimal(net_pnl, "net_pnl") / risk).quantize(Decimal("0.01"))

    def calculate_hold_time(self, opened_at: datetime, closed_at: datetime) -> Decimal:
        return Decimal(str((closed_at - opened_at).total_seconds() / 3600)).quantize(Decimal("0.01"))

    def calculate_drawdown(self, equity_curve: List[Decimal]) -> Dict[str, Decimal]:
        peak = Decimal("0")
        drawdowns = []
        max_drawdown = Decimal("0")
        for raw_equity in equity_curve:
            equity = _decimal(raw_equity, "equity")
            peak = max(peak, equity)
            drawdown = ((peak - equity) / peak * 100) if peak > 0 else Decimal("0")
            drawdowns.append(drawdown)
            max_drawdown = max(max_drawdown, drawdown)
        return {
            "max_drawdown": max_drawdown,
            "avg_drawdown": sum(drawdowns, Decimal("0")) / len(drawdowns) if drawdowns else Decimal("0"),
            "max_duration_days": len(drawdowns) // 24,
            "current_drawdown": drawdowns[-1] if drawdowns else Decimal("0"),
        }


class PnLCalculator:
    """Calculates marked and realized PnL for LONG and SHORT positions."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = PnLEngine(config)

    def calculate_position_pnl(self, position: Any, current_price: Decimal) -> Dict[str, Decimal]:
        entry = _decimal(position.entry_price, "entry_price")
        price = _decimal(current_price, "current_price")
        quantity = _decimal(position.quantity, "quantity")
        if entry <= 0 or price <= 0 or quantity < 0:
            raise ValueError("position prices must be positive and quantity cannot be negative")
        gross = (price - entry) * quantity
        if _direction(position) == "SHORT":
            gross = -gross
        return {
            "unrealized_pnl": gross,
            "current_price": price,
            "entry_price": entry,
            "quantity": quantity,
        }

    def calculate_realized_pnl(
        self,
        position: Any,
        exit_price: Decimal,
        fees: Decimal,
        funding: Decimal,
        quantity: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        qty = _decimal(quantity if quantity is not None else position.quantity, "quantity")
        return self.engine.calculate_trade_pnl(
            entry_price=_decimal(position.entry_price, "entry_price"),
            exit_price=_decimal(exit_price, "exit_price"),
            quantity=qty,
            direction=_direction(position),
            entry_fees=Decimal("0"),
            exit_fees=_decimal(fees, "fees"),
            funding=_decimal(funding, "funding"),
        )


class PnLAnalytics:
    """Compatibility analytics facade over actual persisted trade data."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = PnLEngine(config)

    def calculate_pnl_summary(self, trades: List[Dict], period_days: int = 30) -> PnLSummary:
        values = [_decimal(t.get("net_pnl", 0), "net_pnl") for t in trades]
        wins = [v for v in values if v > 0]
        losses = [v for v in values if v <= 0]
        gross = sum((_decimal(t.get("gross_pnl", t.get("net_pnl", 0)), "gross_pnl") for t in trades), Decimal("0"))
        fees = sum((_decimal(t.get("fees", 0), "fees") for t in trades), Decimal("0"))
        funding = sum((_decimal(t.get("funding", 0), "funding") for t in trades), Decimal("0"))
        net = sum(values, Decimal("0"))
        gross_profit = sum(wins, Decimal("0"))
        gross_loss = abs(sum(losses, Decimal("0")))
        return PnLSummary(
            period_days=period_days, total_trades=len(trades),
            winning_trades=len(wins), losing_trades=len(losses),
            gross_pnl=gross, total_fees=fees, total_funding=funding, net_pnl=net,
            win_rate=Decimal(len(wins)) / Decimal(len(values)) * 100 if values else Decimal("0"),
            profit_factor=gross_profit / gross_loss if gross_loss else (Decimal("999") if gross_profit else Decimal("0")),
            expectancy=net / Decimal(len(values)) if values else Decimal("0"),
            avg_r_multiple=sum((_decimal(t.get("r_multiple", 0), "r_multiple") for t in trades), Decimal("0")) / Decimal(len(values)) if values else Decimal("0"),
            max_drawdown=Decimal("0"), best_trade=max(values) if values else Decimal("0"),
            worst_trade=min(values) if values else Decimal("0"),
            avg_hold_time_hours=sum((_decimal(t.get("hold_time_hours", 0), "hold_time_hours") for t in trades), Decimal("0")) / Decimal(len(values)) if values else Decimal("0"),
            by_exit_reason={}, by_tp_stage={},
        )

    def calculate_performance_metrics(self, trades: List[Dict], equity_curve: List[Decimal], period_days: int = 30) -> PerformanceMetrics:
        summary = self.calculate_pnl_summary(trades, period_days)
        zero = Decimal("0")
        values = [_decimal(t.get("net_pnl", 0), "net_pnl") for t in trades]
        wins = [value for value in values if value > 0]
        losses = [value for value in values if value <= 0]
        drawdown = self.engine.calculate_drawdown(equity_curve)
        return PerformanceMetrics(
            total_return_pct=zero, annualized_return_pct=zero, volatility_pct=zero,
            sharpe_ratio=None, sortino_ratio=None, calmar_ratio=None,
            max_drawdown_pct=drawdown["max_drawdown"],
            avg_drawdown_pct=drawdown["avg_drawdown"],
            max_drawdown_duration_days=drawdown["max_duration_days"],
            current_drawdown_pct=drawdown["current_drawdown"],
            total_trades=summary.total_trades, win_rate=summary.win_rate,
            profit_factor=summary.profit_factor, expectancy=summary.expectancy,
            avg_win=sum(wins, zero) / Decimal(len(wins)) if wins else zero,
            avg_loss=sum(losses, zero) / Decimal(len(losses)) if losses else zero,
            avg_r_multiple=summary.avg_r_multiple,
            largest_win=max(wins) if wins else zero,
            largest_loss=min(losses) if losses else zero,
            consecutive_wins=0, consecutive_losses=0, risk_adjusted_return=zero,
            ulcer_index=zero, sterling_ratio=zero,
        )

    def calculate_breakdowns(self, trades: List[Dict]) -> Dict[str, List[BreakdownItem]]:
        result = {}
        for category in ("symbol", "direction", "timeframe", "strategy", "regime", "exit_reason", "tp_stage"):
            groups = {}
            for trade in trades:
                groups.setdefault(str(trade.get(category, "unknown")), []).append(trade)
            items = []
            for key, group in groups.items():
                summary = self.calculate_pnl_summary(group)
                items.append(BreakdownItem(key, len(group), summary.win_rate, summary.profit_factor, summary.net_pnl, summary.avg_r_multiple))
            result[f"by_{category}"] = items
        return result

    def calculate_tp_analytics(self, trades: List[Dict]) -> TPAnalytics:
        zero = Decimal("0")
        return TPAnalytics(zero, zero, zero, zero, zero, zero, zero, zero, zero, zero, zero, {})

    def generate_equity_curve(self, trades: List[Dict], initial_equity: Decimal = Decimal("100")) -> List[Dict]:
        equity = _decimal(initial_equity, "initial_equity")
        curve = []
        for trade in sorted(trades, key=lambda item: item.get("closed_at") or datetime.min):
            pnl = _decimal(trade.get("net_pnl", 0), "net_pnl")
            equity += pnl
            closed_at = trade.get("closed_at") or datetime.utcnow()
            curve.append({"timestamp": closed_at.isoformat(), "equity": equity, "trade_pnl": pnl, "trade_id": trade.get("id")})
        return curve


class PnLService:
    """Paper-safe PnL service with an idempotent order-to-ledger reconciliation."""

    def __init__(self, config: Config):
        self.config = config
        self.calculator = PnLCalculator(config)
        self.analytics = PnLAnalytics(config)
        self.logger = logging.getLogger(__name__)
        self._running = False

    async def initialize(self):
        if not self.config.settings.mock_exchange or not self.config.settings.paper_trading:
            raise RuntimeError("PnL service requires mock_exchange=True and paper_trading=True")
        self._running = True
        self.logger.info("PnL Service initialized in paper mode")

    async def shutdown(self):
        self._running = False

    async def calculate_position_pnl(
        self, position: Any, current_price: Decimal, db: Optional[Session] = None
    ) -> Dict[str, Decimal]:
        result = self.calculator.calculate_position_pnl(position, current_price)
        position.pnl = float(result["unrealized_pnl"])
        if db is not None:
            db.flush()
        return result

    async def calculate_realized_pnl(
        self,
        position: Any,
        exit_price: Decimal,
        fees: Decimal,
        funding: Decimal,
        quantity: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        return self.calculator.calculate_realized_pnl(
            position, exit_price, fees, funding, quantity=quantity
        )

    async def record_realized_pnl(
        self,
        position: Position,
        exit_price: Decimal,
        quantity: Decimal,
        fees: Decimal,
        funding: Decimal,
        db: Session,
        trade_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Decimal]:
        """Record one realized close fill; repeated trade_id updates rather than duplicates."""
        result = self.calculator.calculate_realized_pnl(
            position, exit_price, fees, funding, quantity=quantity
        )
        existing = None
        if trade_id is not None:
            existing = db.query(PnL_Entry).filter_by(
                position_id=position.id, trade_id=trade_id, pnl_type="realized"
            ).one_or_none()
        entries = db.query(PnL_Entry).filter_by(
            position_id=position.id, pnl_type="realized"
        ).all()
        previous_ledger_total = sum((_decimal(row.amount, "ledger amount") for row in entries), Decimal("0"))
        unledgered_base = _decimal(position.realized_pnl, "position.realized_pnl") - previous_ledger_total
        if existing is None:
            existing = PnL_Entry(
                position_id=position.id,
                trade_id=trade_id,
                pnl_type="realized",
                amount=float(result["net_pnl"]),
                running_balance=0.0,
                description=description or "Realized paper-trade PnL",
            )
            db.add(existing)
        else:
            existing.amount = float(result["net_pnl"])
            if description is not None:
                existing.description = description
        db.flush()
        entries = db.query(PnL_Entry).filter_by(
            position_id=position.id, pnl_type="realized"
        ).order_by(PnL_Entry.id).all()
        running = unledgered_base
        for row in entries:
            running += _decimal(row.amount, "ledger amount")
            row.running_balance = float(running)
        position.realized_pnl = float(running)
        db.flush()
        return result

    async def sync_position_pnl(
        self,
        position: Position,
        db: Session,
        current_price: Optional[Decimal] = None,
    ) -> Dict[str, Decimal]:
        """Rebuild realized PnL from persisted fills and refresh marked PnL.

        Entry fees are allocated pro-rata across closing fills. Each closing
        order has one ledger row keyed by its order id, making sync repeatable.
        """
        orders = db.query(Order).filter_by(
            position_id=position.id, status=OrderStatus.FILLED
        ).order_by(Order.id).all()
        side = _direction(position)
        entry_side = "BUY" if side == "LONG" else "SELL"
        close_side = "SELL" if side == "LONG" else "BUY"
        entry_orders = [o for o in orders if str(o.side).upper() == entry_side]
        close_orders = [o for o in orders if str(o.side).upper() == close_side]

        entry_quantity = sum((_decimal(o.filled_quantity or 0, "filled_quantity") for o in entry_orders), Decimal("0"))
        entry_fees = sum((_decimal(o.fees or 0, "entry fees") for o in entry_orders), Decimal("0"))
        if entry_quantity > 0:
            entry_notional = sum(
                (_decimal(o.average_fill_price, "entry fill price") * _decimal(o.filled_quantity, "filled_quantity") for o in entry_orders),
                Decimal("0"),
            )
            entry_price = entry_notional / entry_quantity
        else:
            entry_price = _decimal(position.entry_price, "entry_price")

        ledger_by_trade = {
            row.trade_id: row
            for row in db.query(PnL_Entry).filter_by(
                position_id=position.id, pnl_type="realized"
            ).all()
            if row.trade_id is not None
        }
        close_results = []
        closed_quantity = Decimal("0")
        exit_fees = Decimal("0")
        for order in close_orders:
            qty = _decimal(order.filled_quantity or 0, "close filled_quantity")
            if qty <= 0:
                continue
            exit_price = _decimal(order.average_fill_price, "exit fill price")
            close_fee = _decimal(order.fees or 0, "exit fees")
            allocated_entry_fee = entry_fees * qty / entry_quantity if entry_quantity > 0 else Decimal("0")
            gross = (exit_price - entry_price) * qty
            if side == "SHORT":
                gross = -gross
            net = gross - close_fee - allocated_entry_fee
            close_results.append((order, qty, gross, close_fee, allocated_entry_fee, net))
            closed_quantity += qty
            exit_fees += close_fee

        running = Decimal("0")
        for order, qty, gross, close_fee, allocated_entry_fee, net in close_results:
            row = ledger_by_trade.get(order.id)
            if row is None:
                row = PnL_Entry(
                    position_id=position.id,
                    trade_id=order.id,
                    pnl_type="realized",
                    amount=float(net),
                    running_balance=0.0,
                    description=f"Paper close order #{order.id}",
                )
                db.add(row)
            row.amount = float(net)
            running += net
            row.running_balance = float(running)

        position.realized_pnl = float(running)
        unrealized = Decimal("0")
        if current_price is not None and _decimal(position.quantity, "position.quantity") > 0:
            marked = self.calculator.calculate_position_pnl(position, current_price)
            unrealized = marked["unrealized_pnl"]
            position.pnl = float(unrealized)
        elif _decimal(position.quantity, "position.quantity") <= 0:
            position.pnl = 0.0
        db.flush()

        return {
            "realized_pnl": running,
            "unrealized_pnl": unrealized,
            "total_pnl": running + unrealized,
            "closed_quantity": closed_quantity,
            "remaining_quantity": _decimal(position.quantity, "position.quantity"),
            "entry_fees": entry_fees,
            "exit_fees": exit_fees,
            "total_fees": entry_fees + exit_fees,
            "trade_count": Decimal(len(close_results)),
        }

    async def get_pnl_summary(self, db: Session, days: int = 30) -> PnLSummary:
        cutoff = datetime.utcnow() - timedelta(days=days)
        positions = db.query(Position).filter(Position.close_time >= cutoff).all()
        values = [_decimal(p.realized_pnl, "realized_pnl") for p in positions]
        winners = [v for v in values if v > 0]
        losers = [v for v in values if v <= 0]
        gross_profit = sum(winners, Decimal("0"))
        gross_loss = abs(sum(losers, Decimal("0")))
        net = sum(values, Decimal("0"))
        fees = sum(
            (_decimal(o.fees or 0, "order fees") for p in positions for o in p.orders),
            Decimal("0"),
        )
        return PnLSummary(
            period_days=days,
            total_trades=len(values),
            winning_trades=len(winners),
            losing_trades=len(losers),
            gross_pnl=net + fees,
            total_fees=fees,
            total_funding=Decimal("0"),
            net_pnl=net,
            win_rate=(Decimal(len(winners)) / Decimal(len(values)) * 100) if values else Decimal("0"),
            profit_factor=(gross_profit / gross_loss) if gross_loss else (Decimal("999") if gross_profit else Decimal("0")),
            expectancy=(net / Decimal(len(values))) if values else Decimal("0"),
            avg_r_multiple=Decimal("0"),
            max_drawdown=Decimal("0"),
            best_trade=max(values) if values else Decimal("0"),
            worst_trade=min(values) if values else Decimal("0"),
            avg_hold_time_hours=Decimal("0"),
            by_exit_reason={},
            by_tp_stage={},
        )

    async def get_performance_metrics(self, db: Session, days: int = 30) -> PerformanceMetrics:
        return PerformanceMetrics(
            total_return_pct=Decimal("0"), annualized_return_pct=Decimal("0"),
            volatility_pct=Decimal("0"), sharpe_ratio=None, sortino_ratio=None,
            calmar_ratio=None, max_drawdown_pct=Decimal("0"), avg_drawdown_pct=Decimal("0"),
            max_drawdown_duration_days=0, current_drawdown_pct=Decimal("0"),
            total_trades=0, win_rate=Decimal("0"), profit_factor=Decimal("0"),
            expectancy=Decimal("0"), avg_win=Decimal("0"), avg_loss=Decimal("0"),
            avg_r_multiple=Decimal("0"), largest_win=Decimal("0"), largest_loss=Decimal("0"),
            consecutive_wins=0, consecutive_losses=0, risk_adjusted_return=Decimal("0"),
            ulcer_index=Decimal("0"), sterling_ratio=Decimal("0"),
        )

    async def get_breakdowns(self, db: Session, days: int = 30) -> Dict:
        return {}

    async def get_tp_analytics(self, db: Session, days: int = 30) -> TPAnalytics:
        zero = Decimal("0")
        return TPAnalytics(zero, zero, zero, zero, zero, zero, zero, zero, zero, zero, zero, {})

    async def get_equity_curve(self, db: Session, days: int = 30) -> List[Dict]:
        positions = db.query(Position).filter(Position.close_time.isnot(None)).order_by(Position.close_time).all()
        equity = _decimal(self.config.settings.initial_equity, "initial_equity")
        curve = []
        for position in positions:
            pnl = _decimal(position.realized_pnl, "realized_pnl")
            equity += pnl
            curve.append({
                "timestamp": position.close_time.isoformat(),
                "equity": equity,
                "trade_pnl": pnl,
                "trade_id": position.id,
            })
        return curve

    async def get_monthly_returns(self, db: Session, years: int = 1) -> List[Dict]:
        return []

    async def get_daily_report(self, db: Session, date: datetime) -> Dict:
        return {}

    async def get_weekly_report(self, db: Session, week_start: datetime) -> Dict:
        return {}

    async def get_monthly_report(self, db: Session, month: str) -> Dict:
        return {}
