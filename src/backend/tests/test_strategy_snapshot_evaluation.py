"""Stage 3A tests for evaluating persisted strategy rules against scanner snapshots.

All market values in this module are controlled test fixtures, not live market data.
"""

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.models.database import Base, Strategy, StrategyRule
from src.backend.services.signal_service import SignalService
from src.backend.services.strategy_service import StrategyEngine


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _condition(indicator, operator, threshold):
    return {
        "indicator": {"name": indicator, "params": {"period": 14}, "source": "close"},
        "operator": operator,
        "threshold": threshold,
    }


def _snapshot(symbol="BTC/USDT", exchange="binance", indicators=None):
    return SimpleNamespace(
        symbol=symbol,
        exchange=exchange,
        ticker=SimpleNamespace(price=100.0),
        indicators=indicators if indicators is not None else {"rsi": 25.0},
        regime="ranging",
    )


def _strategy(
    db_session,
    *,
    name="RSI oversold",
    direction="long",
    timeframes=None,
    symbols=None,
    entry_conditions=None,
):
    strategy = Strategy(
        name=name,
        version="1.0.0",
        is_active=True,
        direction=direction,
        timeframes=timeframes if timeframes is not None else ["1h"],
        symbols=symbols if symbols is not None else [],
    )
    db_session.add(strategy)
    db_session.flush()
    if entry_conditions is not None:
        db_session.add(StrategyRule(
            strategy_id=strategy.id,
            rule_type="entry",
            rule_config={"operator": "AND", "conditions": entry_conditions, "groups": []},
            is_active=True,
        ))
    db_session.commit()
    return strategy


def _service(engine, snapshots):
    strategy_service = SimpleNamespace(engine=engine)
    scanner = SimpleNamespace(latest_snapshots=snapshots)
    return SignalService(
        config=None,
        market_data_service=None,
        market_regime_service=None,
        strategy_service=strategy_service,
        market_scanner=scanner,
    )


def test_evaluates_unfiltered_snapshot_and_returns_real_rule_match(db_session):
    strategy = _strategy(
        db_session,
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {"binance:BTC/USDT": _snapshot()})

    matches = service.evaluate_strategy_matches()

    assert len(matches) == 1
    match = matches[0]
    assert match.strategy_id == strategy.id
    assert match.strategy_name == "RSI oversold"
    assert match.symbol == "BTC/USDT"
    assert match.exchange == "binance"
    assert match.direction == "LONG"
    assert match.timeframe == "1h"
    assert match.matched_rule_types == ["entry"]
    assert match.indicators == {"rsi": 25.0}


def test_strategy_symbol_allowlist_excludes_other_symbols(db_session):
    _strategy(
        db_session,
        symbols=["ETH/USDT"],
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {
        "binance:BTC/USDT": _snapshot("BTC/USDT", indicators={"rsi": 20.0}),
    })

    assert service.evaluate_strategy_matches() == []


def test_strategy_timeframe_restriction_does_not_reuse_hourly_values(db_session):
    _strategy(
        db_session,
        name="Restricted",
        direction="long",
        timeframes=["15m"],
        symbols=["ETH/USDT"],
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {
        "binance:BTC/USDT": _snapshot("BTC/USDT", indicators={"rsi": 20.0}),
        "binance:ETH/USDT": _snapshot("ETH/USDT", indicators={"rsi": 20.0}),
    })

    # Scanner RSI is currently derived from 1h candles. It must not be reused
    # for a configured 15m strategy.
    assert service.evaluate_strategy_matches() == []


def test_direction_configuration_blocks_opposite_direction(db_session):
    _strategy(
        db_session,
        direction="long",
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {"binance:BTC/USDT": _snapshot()})

    matches = service.evaluate_strategy_matches()

    assert [match.direction for match in matches] == ["LONG"]


def test_missing_indicators_and_zero_rule_strategies_never_match(db_session):
    _strategy(
        db_session,
        name="Missing RSI",
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    _strategy(
        db_session,
        name="No entry rules",
        entry_conditions=None,
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {
        "binance:BTC/USDT": _snapshot(indicators={"macd": 1.0}),
    })

    assert service.evaluate_strategy_matches() == []


def test_generate_signals_runs_matching_but_does_not_create_fake_candidates(db_session):
    _strategy(
        db_session,
        entry_conditions=[_condition("RSI", "<", 30)],
    )
    engine = StrategyEngine(config=None)
    engine.load_active_strategies(db_session)
    service = _service(engine, {"binance:BTC/USDT": _snapshot()})

    generated = asyncio.run(service.generate_signals_now())

    assert generated == []
    assert len(service.latest_strategy_matches) == 1
