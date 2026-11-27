"""Stage 6 PnL service tests. All exchange activity is mock + paper only."""

from decimal import Decimal

import pytest

from src.backend.models.database import (
    Exchange,
    Order,
    OrderStatus,
    OrderType,
    PnL_Entry,
    Position,
    PositionStatus,
    Signal,
    SignalDirection,
    Strategy,
    Symbol,
)
from src.backend.services.execution_service import ExecutionService
from src.backend.services.pnl_service import PnLService
from src.backend.services.tp_sl_service import TPSLService


class FakeMarketData:
    def __init__(self, price=Decimal("50000")):
        self.price = price

    async def get_ticker(self, symbol, exchange):
        return {"price": self.price} if self.price is not None else None

    async def get_candles(self, symbol, timeframe, limit=15, exchange=None):
        return [
            {"high": Decimal("50100"), "low": Decimal("49900"), "close": Decimal("50000")}
            for _ in range(15)
        ]


@pytest.fixture
def pnl_context(config, db_session):
    config.settings.mock_exchange = True
    config.settings.paper_trading = True
    exchange = Exchange(name="binance", base_url="https://example.invalid", api_version="test")
    db_session.add(exchange)
    db_session.flush()
    symbol = Symbol(
        exchange_id=exchange.id, symbol="BTCUSDT", base_asset="BTC",
        quote_asset="USDT", is_active=True, is_eligible=True,
    )
    db_session.add(symbol)
    db_session.flush()
    position = Position(
        exchange_id=exchange.id, symbol_id=symbol.id,
        direction=SignalDirection.LONG, entry_price=50000, quantity=0.01,
        notional_value=500, margin_used=250, leverage_used=2,
        status=PositionStatus.OPEN, realized_pnl=0, pnl=0,
    )
    db_session.add(position)
    db_session.flush()
    service = PnLService(config)
    return service, position, exchange, symbol, db_session


def add_order(db, position, exchange, symbol, *, side, quantity, price, fees, order_id=None):
    order = Order(
        position_id=position.id,
        exchange_id=exchange.id,
        symbol_id=symbol.id,
        exchange_order_id=order_id,
        order_type=OrderType.MARKET,
        side=side,
        quantity=float(quantity),
        filled_quantity=float(quantity),
        average_fill_price=float(price),
        fees=float(fees),
        status=OrderStatus.FILLED,
    )
    db.add(order)
    db.flush()
    return order


@pytest.mark.asyncio
async def test_pnl_service_initializes_and_shuts_down(pnl_context):
    service, *_ = pnl_context
    await service.initialize()
    assert service._running is True
    await service.shutdown()
    assert service._running is False


@pytest.mark.asyncio
async def test_pnl_service_refuses_non_paper_configuration(pnl_context):
    service, *_ = pnl_context
    previous = service.config.settings.paper_trading
    service.config.settings.paper_trading = False
    try:
        with pytest.raises(RuntimeError, match="mock_exchange=True and paper_trading=True"):
            await service.initialize()
    finally:
        service.config.settings.paper_trading = previous


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "direction,entry,current,expected",
    [
        (SignalDirection.LONG, Decimal("50000"), Decimal("51000"), Decimal("10")),
        (SignalDirection.LONG, Decimal("50000"), Decimal("49000"), Decimal("-10")),
        (SignalDirection.SHORT, Decimal("50000"), Decimal("49000"), Decimal("10")),
        (SignalDirection.SHORT, Decimal("50000"), Decimal("51000"), Decimal("-10")),
    ],
)
async def test_unrealized_pnl_handles_long_and_short_and_persists_position_stat(
    pnl_context, direction, entry, current, expected
):
    service, position, *_rest, db = pnl_context
    position.direction = direction
    position.entry_price = float(entry)
    position.quantity = 0.01
    result = await service.calculate_position_pnl(position, current, db=db)
    assert result["unrealized_pnl"] == expected
    assert position.pnl == pytest.approx(float(expected))
    db.refresh(position)
    assert position.pnl == pytest.approx(float(expected))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "direction,exit_price,expected_gross",
    [
        (SignalDirection.LONG, Decimal("51000"), Decimal("10")),
        (SignalDirection.SHORT, Decimal("49000"), Decimal("10")),
    ],
)
async def test_realized_pnl_uses_supplied_exit_price_fees_and_funding(
    pnl_context, direction, exit_price, expected_gross
):
    service, position, *_ = pnl_context
    position.direction = direction
    result = await service.calculate_realized_pnl(
        position, exit_price=exit_price, fees=Decimal("0.50"),
        funding=Decimal("0.10"), quantity=Decimal("0.01"),
    )
    assert result["gross_pnl"] == expected_gross
    assert result["total_fees"] == Decimal("0.50")
    assert result["funding"] == Decimal("0.10")
    assert result["net_pnl"] == Decimal("9.40")


@pytest.mark.asyncio
async def test_partial_close_calculation_uses_only_closed_quantity(pnl_context):
    service, position, *_ = pnl_context
    result = await service.calculate_realized_pnl(
        position, exit_price=Decimal("51000"), fees=Decimal("0.20"),
        funding=Decimal("0.05"), quantity=Decimal("0.004"),
    )
    assert result["gross_pnl"] == Decimal("4")
    assert result["net_pnl"] == Decimal("3.75")


@pytest.mark.asyncio
async def test_realized_pnl_is_persisted_and_trade_id_is_idempotent(pnl_context):
    service, position, _exchange, _symbol, db = pnl_context
    first = await service.record_realized_pnl(
        position, Decimal("51000"), Decimal("0.004"), Decimal("0.10"),
        Decimal("0.02"), db, trade_id=77, description="TP1 paper fill",
    )
    second = await service.record_realized_pnl(
        position, Decimal("51000"), Decimal("0.004"), Decimal("0.10"),
        Decimal("0.02"), db, trade_id=77, description="TP1 paper fill",
    )
    rows = db.query(PnL_Entry).filter_by(position_id=position.id, trade_id=77).all()
    assert len(rows) == 1
    assert first["net_pnl"] == second["net_pnl"] == Decimal("3.88")
    assert position.realized_pnl == pytest.approx(3.88)
    assert rows[0].running_balance == pytest.approx(3.88)


@pytest.mark.asyncio
async def test_order_reconciliation_allocates_entry_fees_across_partial_closes(pnl_context):
    service, position, exchange, symbol, db = pnl_context
    add_order(
        db, position, exchange, symbol, side="BUY", quantity=Decimal("0.01"),
        price=Decimal("50000"), fees=Decimal("0.50"), order_id="entry-1",
    )
    add_order(
        db, position, exchange, symbol, side="SELL", quantity=Decimal("0.004"),
        price=Decimal("51000"), fees=Decimal("0.204"), order_id="tp1",
    )
    add_order(
        db, position, exchange, symbol, side="SELL", quantity=Decimal("0.003"),
        price=Decimal("52000"), fees=Decimal("0.306"), order_id="tp2",
    )
    position.quantity = 0.003

    result = await service.sync_position_pnl(position, db, current_price=Decimal("50500"))
    assert result["closed_quantity"] == Decimal("0.007")
    assert result["remaining_quantity"] == Decimal("0.003")
    assert result["entry_fees"] == Decimal("0.50")
    assert result["exit_fees"] == Decimal("0.510")
    assert result["realized_pnl"] == Decimal("9.14")
    assert result["unrealized_pnl"] == Decimal("1.500")
    assert position.realized_pnl == pytest.approx(9.14)
    assert position.pnl == pytest.approx(1.5)
    rows = db.query(PnL_Entry).filter_by(position_id=position.id, pnl_type="realized").order_by(PnL_Entry.id).all()
    assert len(rows) == 2
    assert rows[-1].running_balance == pytest.approx(9.14)

    repeated = await service.sync_position_pnl(position, db, current_price=Decimal("50500"))
    assert repeated["realized_pnl"] == result["realized_pnl"]
    assert db.query(PnL_Entry).filter_by(position_id=position.id, pnl_type="realized").count() == 2


async def _run_tp_sl_close(pnl_context, close_price, trigger):
    service, position, exchange, symbol, db = pnl_context
    strategy = Strategy(name="PnL integration strategy", version="1.0")
    db.add(strategy)
    db.flush()
    signal = Signal(
        symbol_id=symbol.id, strategy_id=strategy.id,
        direction=SignalDirection.LONG, entry_price=50000,
        stop_loss=49000, tp1=51000, tp2=52000, tp3=53000,
    )
    db.add(signal)
    db.flush()
    position.signal = signal

    market_data = FakeMarketData(close_price)
    execution = ExecutionService(service.config, risk_service=object(), market_data_service=market_data)
    tp_sl = TPSLService(service.config, execution, market_data, risk_service=object())
    await tp_sl.initialize()
    await tp_sl.add_position(position)
    manager = tp_sl.managers[position.id]
    if trigger == "tp":
        await manager._handle_tp_trigger(1)
    else:
        await manager._handle_sl_trigger()
    result = await service.sync_position_pnl(position, db, current_price=close_price)
    await tp_sl.shutdown()
    return result


@pytest.mark.asyncio
async def test_tp_generated_fill_updates_realized_pnl_ledger(pnl_context):
    service, position, *_ = pnl_context
    result = await _run_tp_sl_close(pnl_context, Decimal("51000"), "tp")
    assert result["trade_count"] == Decimal("1")
    assert result["realized_pnl"] > 0
    assert position.realized_pnl == pytest.approx(float(result["realized_pnl"]))
    assert position.quantity == pytest.approx(0.006)


@pytest.mark.asyncio
async def test_sl_generated_fill_updates_realized_loss_ledger(pnl_context):
    service, position, _exchange, _symbol, db = pnl_context
    result = await _run_tp_sl_close(pnl_context, Decimal("49000"), "sl")
    assert result["trade_count"] == Decimal("1")
    assert result["realized_pnl"] < 0
    assert position.status == PositionStatus.CLOSED
    assert position.realized_pnl == pytest.approx(float(result["realized_pnl"]))
    assert db.query(PnL_Entry).filter_by(position_id=position.id, pnl_type="realized").count() == 1
