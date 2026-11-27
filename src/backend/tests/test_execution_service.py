"""Stage 4 runtime contract tests for the paper Execution Service.

All tests force mock_exchange=True and paper_trading=True. No real exchange
adapter or credentials are created.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.backend.models.database import (
    Exchange,
    Order,
    OrderStatus as DBOrderStatus,
    Position,
    Symbol,
)
from src.backend.services.execution_service import (
    ExecutionService,
    OrderParams,
    OrderSide,
    OrderType,
)


class FakeMarketData:
    def __init__(self, price=Decimal("50000")):
        self.price = price
        self.calls = []

    async def get_ticker(self, symbol, exchange):
        self.calls.append((symbol, exchange))
        if self.price is None:
            return None
        return {"price": self.price}


class ForbiddenLiveExecutor:
    def __init__(self):
        self.called = False

    async def place_order(self, params):
        self.called = True
        raise AssertionError("Live executor must never be invoked in mock paper mode")


@pytest.fixture
def execution_context(config):
    config.settings.mock_exchange = True
    config.settings.paper_trading = True
    market_data = FakeMarketData()
    service = ExecutionService(config, risk_service=object(), market_data_service=market_data)
    return service, market_data


@pytest.fixture
def exchange_symbol(db_session):
    exchange = Exchange(
        name="binance",
        base_url="https://example.invalid",
        api_version="test",
        is_active=True,
    )
    db_session.add(exchange)
    db_session.flush()
    symbol = Symbol(
        exchange_id=exchange.id,
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        is_active=True,
        is_eligible=True,
    )
    db_session.add(symbol)
    db_session.commit()
    return exchange, symbol


def market_order(quantity=Decimal("0.01"), position_side="LONG"):
    return OrderParams(
        symbol="BTCUSDT",
        exchange="binance",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=quantity,
        position_side=position_side,
    )


@pytest.mark.asyncio
async def test_execution_service_initializes_and_shuts_down(execution_context):
    service, _ = execution_context
    await service.initialize()
    assert service._running is True
    await service.shutdown()
    assert service._running is False


@pytest.mark.asyncio
async def test_paper_market_order_is_created_and_filled(execution_context):
    service, market_data = execution_context
    await service.initialize()
    result = await service.place_order(market_order(), mode="paper")
    assert result.status == DBOrderStatus.FILLED
    assert result.filled_quantity == Decimal("0.01")
    assert result.average_fill_price > 0
    assert result.exchange == "paper"
    assert len(service.paper_executor.orders) == 1
    assert market_data.calls == [("BTCUSDT", "binance")]


@pytest.mark.asyncio
async def test_invalid_quantity_is_rejected_without_order_creation(execution_context):
    service, _ = execution_context
    result = await service.place_order(market_order(quantity=Decimal("-1")), mode="paper")
    assert result.status == DBOrderStatus.REJECTED
    assert result.filled_quantity == Decimal("0")
    assert service.paper_executor.orders == {}


@pytest.mark.asyncio
async def test_pending_limit_order_can_transition_to_cancelled(execution_context):
    service, _ = execution_context
    params = OrderParams(
        symbol="BTCUSDT",
        exchange="binance",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.01"),
        price=Decimal("49000"),
    )
    result = await service.place_order(params, mode="paper")
    assert result.status == DBOrderStatus.PENDING
    assert await service.cancel_order(result.order_id, "BTCUSDT", "binance", mode="paper")
    stored = await service.paper_executor.get_order(result.order_id, "BTCUSDT")
    assert stored["status"] == DBOrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_mock_paper_path_uses_paper_executor_only(execution_context):
    service, _ = execution_context
    forbidden = ForbiddenLiveExecutor()
    service.executors["binance"] = forbidden
    result = await service.place_order(market_order(), mode="paper")
    assert result.status == DBOrderStatus.FILLED
    assert forbidden.called is False


@pytest.mark.asyncio
async def test_live_path_is_blocked_when_mock_and_paper_flags_are_enabled(execution_context):
    service, _ = execution_context
    forbidden = ForbiddenLiveExecutor()
    service.executors["binance"] = forbidden
    result = await service.place_order(market_order(), mode="live")
    assert result.status == DBOrderStatus.REJECTED
    assert forbidden.called is False


@pytest.mark.asyncio
async def test_filled_paper_order_is_persisted(execution_context, db_session, exchange_symbol):
    service, _ = execution_context
    result = await service.place_order(market_order(), mode="paper", db=db_session)
    assert result.status == DBOrderStatus.FILLED
    saved = db_session.query(Order).filter_by(exchange_order_id=result.exchange_order_id).one()
    assert saved.status == DBOrderStatus.FILLED
    assert saved.quantity == pytest.approx(0.01)
    assert saved.filled_quantity == pytest.approx(0.01)


@pytest.mark.asyncio
async def test_executed_entry_order_creates_database_position(
    execution_context, db_session, exchange_symbol
):
    service, _ = execution_context
    signal = SimpleNamespace(symbol="BTCUSDT", exchange="binance", direction="LONG", id=None)
    leverage = SimpleNamespace(position_quantity=Decimal("0.01"), selected_leverage=2)
    result = await service.place_entry_order(signal, leverage, mode="paper", db=db_session)
    assert result.status == DBOrderStatus.FILLED
    position = db_session.query(Position).one()
    assert position.direction.value == "LONG"
    assert position.status.value == "open"
    assert position.quantity == pytest.approx(0.01)
    assert position.entry_price > 0


@pytest.mark.asyncio
async def test_missing_market_data_rejects_order_safely(config):
    config.settings.mock_exchange = True
    config.settings.paper_trading = True
    market_data = FakeMarketData(price=None)
    service = ExecutionService(config, risk_service=object(), market_data_service=market_data)
    result = await service.place_order(market_order(), mode="paper")
    assert result.status == DBOrderStatus.REJECTED
    assert result.order_id == ""
    assert service.paper_executor.orders == {}
