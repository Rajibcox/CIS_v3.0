"""Caller-owned transaction contract tests for paper entry persistence.

These tests use an isolated in-memory SQLite database. They do not touch the
user's local trading database or connect to an exchange.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.backend.models.database import Order, Position
from src.backend.services.execution_service import ExecutionService


def _signal():
    return SimpleNamespace(
        symbol="BTCUSDT",
        exchange="binance",
        direction="LONG",
        id=None,
    )


def _leverage():
    return SimpleNamespace(
        position_quantity=Decimal("0.01"),
        selected_leverage=2,
    )


@pytest.mark.asyncio
async def test_entry_persistence_is_one_linked_order_inside_caller_transaction(
    execution_context, db_session, exchange_symbol
):
    service, _market_data = execution_context

    result = await service.place_entry_order(
        _signal(), _leverage(), mode="paper", db=db_session
    )

    assert result.status.value == "filled"
    position = db_session.query(Position).one()
    orders = db_session.query(Order).all()

    assert len(orders) == 1
    assert orders[0].position_id == position.id
    assert orders[0].status.value == "filled"
    assert db_session.in_transaction() is True

    # The service must flush, not commit: the caller retains transaction control.
    db_session.rollback()
    assert db_session.query(Position).count() == 0
    assert db_session.query(Order).count() == 0


@pytest.mark.asyncio
async def test_entry_validates_exchange_and_symbol_before_simulating_fill(
    execution_context, db_session
):
    service, market_data = execution_context

    with pytest.raises(ValueError, match="Cannot create paper position"):
        await service.place_entry_order(
            _signal(), _leverage(), mode="paper", db=db_session
        )

    assert market_data.calls == []
    assert service.paper_executor.orders == {}
    assert db_session.query(Position).count() == 0
    assert db_session.query(Order).count() == 0


@pytest.mark.asyncio
async def test_entry_persistence_failure_propagates_for_caller_rollback(
    execution_context, db_session, exchange_symbol, monkeypatch
):
    service, _market_data = execution_context
    original_flush = db_session.flush
    flush_calls = 0

    def fail_order_flush(*args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise RuntimeError("simulated order persistence failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", fail_order_flush)

    with pytest.raises(RuntimeError, match="simulated order persistence failure"):
        await service.place_entry_order(
            _signal(), _leverage(), mode="paper", db=db_session
        )

    # The service does not commit or swallow persistence errors. The caller
    # must roll back the failed SQLAlchemy transaction.
    db_session.rollback()
    assert db_session.query(Position).count() == 0
    assert db_session.query(Order).count() == 0
