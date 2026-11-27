"""Stage 5 TP/SL runtime contract tests.

All tests force mock exchange + paper trading. No exchange adapter is
initialized and all close orders pass through the paper executor.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.backend.models.database import (
    Exchange, Order, Position, PositionStatus, Signal, SignalDirection,
    Strategy, Symbol, TP_SL_Stage, TPStageStatus,
)
from src.backend.services.execution_service import ExecutionService
from src.backend.services.tp_sl_service import TPSLService


class FakeMarketData:
    def __init__(self, price=Decimal("50000")):
        self.price = price
        self.ticker_calls = []

    async def get_ticker(self, symbol, exchange):
        self.ticker_calls.append((symbol, exchange))
        return None if self.price is None else {"price": self.price}

    async def get_candles(self, symbol, timeframe, limit=15, exchange=None):
        return [
            {"high": Decimal("50100"), "low": Decimal("49900"), "close": Decimal("50000")}
            for _ in range(15)
        ]


class ForbiddenLiveExecutor:
    def __init__(self):
        self.called = False

    async def place_order(self, params):
        self.called = True
        raise AssertionError("Live executor must never be called in paper mode")


@pytest.fixture
def tp_context(config, db_session):
    config.settings.mock_exchange = True
    config.settings.paper_trading = True
    config.settings.tp_allocation = {
        "tp1": 0.4, "tp2": 0.3, "tp3": 0.2, "runner": 0.1
    }
    exchange = Exchange(name="binance", base_url="https://example.invalid", api_version="test")
    db_session.add(exchange)
    db_session.flush()
    symbol = Symbol(
        exchange_id=exchange.id, symbol="BTCUSDT", base_asset="BTC",
        quote_asset="USDT", is_active=True, is_eligible=True,
    )
    db_session.add(symbol)
    db_session.flush()
    strategy = Strategy(name="TP/SL test", version="1.0")
    db_session.add(strategy)
    db_session.flush()
    signal = Signal(
        symbol_id=symbol.id, strategy_id=strategy.id,
        direction=SignalDirection.LONG, entry_price=50000,
        stop_loss=49000, tp1=51000, tp2=52000, tp3=53000,
    )
    db_session.add(signal)
    db_session.flush()
    position = Position(
        signal_id=signal.id, exchange_id=exchange.id, symbol_id=symbol.id,
        direction=SignalDirection.LONG, entry_price=50000, quantity=0.01,
        notional_value=500, margin_used=250, leverage_used=2,
        status=PositionStatus.OPEN,
    )
    db_session.add(position)
    db_session.flush()

    market_data = FakeMarketData()
    execution = ExecutionService(config, risk_service=object(), market_data_service=market_data)
    forbidden = ForbiddenLiveExecutor()
    execution.executors["binance"] = forbidden
    service = TPSLService(config, execution, market_data, risk_service=object())
    return service, position, signal, market_data, forbidden, db_session


@pytest.mark.asyncio
async def test_tp_sl_service_initializes_and_shuts_down(tp_context):
    service, *_ = tp_context
    await service.initialize()
    assert service._running is True
    await service.shutdown()
    assert service._running is False


@pytest.mark.asyncio
async def test_initial_stop_loss_and_take_profit_targets_are_persisted(tp_context):
    service, position, *_rest, db = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        rows = db.query(TP_SL_Stage).filter_by(position_id=position.id).order_by(TP_SL_Stage.stage_number).all()
        assert [row.stage_number for row in rows] == [0, 1, 2, 3, 4]
        assert rows[0].target_price == pytest.approx(49000)
        assert [rows[i].target_price for i in (1, 2, 3)] == [51000, 52000, 53000]
        assert [rows[i].quantity for i in (1, 2, 3, 4)] == pytest.approx([0.004, 0.003, 0.002, 0.001])
        assert all(row.status == TPStageStatus.PENDING for row in rows)
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_tp_trigger_executes_paper_close_and_updates_position_and_database(tp_context):
    service, position, *_rest, db = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        manager = service.managers[position.id]
        await manager._handle_tp_trigger(1)
        assert manager.state["tp_orders"][1].status == "filled"
        assert position.quantity == pytest.approx(0.006)
        assert position.status == PositionStatus.OPEN
        assert position.realized_pnl > 0
        stage = db.query(TP_SL_Stage).filter_by(position_id=position.id, stage_number=1).one()
        assert stage.status == TPStageStatus.FILLED
        order = db.query(Order).filter_by(position_id=position.id).one()
        assert order.status.value == "filled"
        assert order.quantity == pytest.approx(0.004)
        assert manager.state["stop_loss"] > Decimal("50000")
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_multi_stage_take_profit_activates_runner_and_preserves_remaining_quantity(tp_context):
    service, position, *_rest, db = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        manager = service.managers[position.id]
        for stage in (1, 2, 3):
            await manager._handle_tp_trigger(stage)
        assert manager.state["current_stage"] == 4
        assert manager.state["quantity"] == Decimal("0.0010")
        assert position.quantity == pytest.approx(0.001)
        assert position.status == PositionStatus.OPEN
        assert manager.state["runner_trailing_price"] == Decimal("52000")
        assert db.query(Order).filter_by(position_id=position.id).count() == 3
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_stop_loss_trigger_closes_remaining_position_and_persists_order(tp_context):
    service, position, *_rest, db = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        manager = service.managers[position.id]
        await manager._handle_sl_trigger()
        assert manager.state["quantity"] == 0
        assert position.quantity == pytest.approx(0)
        assert position.status == PositionStatus.CLOSED
        assert position.close_time is not None
        stage = db.query(TP_SL_Stage).filter_by(position_id=position.id, stage_number=0).one()
        assert stage.status == TPStageStatus.FILLED
        assert db.query(Order).filter_by(position_id=position.id).count() == 1
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_invalid_tp_sl_configuration_is_rejected_without_registration(tp_context):
    service, position, signal, *_rest = tp_context
    signal.tp2 = 50500  # TP2 must be above TP1 for a long position.
    await service.initialize()
    with pytest.raises(ValueError, match="Invalid LONG TP/SL"):
        await service.add_position(position)
    assert position.id not in service.managers
    await service.shutdown()


@pytest.mark.asyncio
async def test_paper_mode_never_calls_live_executor(tp_context):
    service, position, *_rest, forbidden, db = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        await service.managers[position.id]._handle_tp_trigger(1)
        assert forbidden.called is False
    finally:
        await service.shutdown()


@pytest.mark.asyncio
async def test_live_tp_sl_mode_is_rejected(tp_context):
    service, position, *_rest = tp_context
    await service.initialize()
    with pytest.raises(RuntimeError, match="Only paper"):
        await service.add_position(position, mode="live")
    assert position.id not in service.managers
    await service.shutdown()


@pytest.mark.asyncio
async def test_rejected_paper_close_does_not_reduce_position(tp_context):
    service, position, _signal, market_data, *_rest = tp_context
    await service.initialize()
    await service.add_position(position)
    try:
        market_data.price = None
        manager = service.managers[position.id]
        await manager._handle_tp_trigger(1)
        assert manager.state["tp_orders"][1].status == "pending"
        assert position.quantity == pytest.approx(0.01)
        assert position.status == PositionStatus.OPEN
    finally:
        await service.shutdown()
