"""Persistence and evaluator contract tests for nested strategy rules."""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.models.database import Base, Strategy, StrategyRule
from src.backend.services.strategy_service import StrategyEngine, StrategyService


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


def _group(operator="AND", conditions=None, groups=None):
    return {
        "operator": operator,
        "conditions": conditions or [],
        "groups": groups or [],
    }


def _rsi(operator, threshold):
    return {
        "indicator": {"name": "RSI", "params": {"period": 14}, "source": "close"},
        "operator": operator,
        "threshold": threshold,
    }


def test_create_strategy_persists_api_rule_keys_and_loads_engine(db_session):
    service = StrategyService(config=None)
    strategy_id = asyncio.run(service.create_strategy(
        db=db_session,
        name="Persisted RSI",
        description="Contract test",
        version="1.0.0",
        direction="BOTH",
        weight=1.0,
        risk_multiplier=1.0,
        timeframes=["1h"],
        symbols=[],
        min_signal_score=70.0,
        rule_set={
            "entry_rules": _group(conditions=[_rsi("<", 30)]),
            "exit_rules": _group(conditions=[_rsi(">", 70)]),
        },
    ))

    strategy = db_session.query(Strategy).filter_by(id=strategy_id).one()
    rules = db_session.query(StrategyRule).filter_by(strategy_id=strategy_id).all()
    assert {rule.rule_type for rule in rules} == {"entry", "exit"}
    assert rules[0].rule_config["conditions"][0]["indicator"]["name"] == "RSI"
    assert service.engine.evaluate_entry(
        strategy_id, {"rsi": 25.0}, "1h", "LONG"
    )[0] is True
    assert service.engine.evaluate_entry(
        strategy_id, {"rsi": 35.0}, "1h", "LONG"
    )[0] is False


def _trade_plan():
    return {
                "schema_version": 1,
                "entry": "strategy_rule_match",
                "stop_loss": {"method": "swing_structure", "parameters": {"lookback_candles": 20, "buffer_mode": "none"}},
                "take_profit": {
                    "targets": {
                        "tp1": {"method": "strategy_defined_tp1", "parameters": {}},
                        "tp2": {"method": "strategy_defined_tp2", "parameters": {}},
                        "tp3": {"method": "strategy_defined_tp3", "parameters": {}}
                    },
                    "allocation": {"tp1": 40, "tp2": 30, "tp3": 20, "runner": 10}
                },
                "runner": {"method": "strategy_defined_runner", "parameters": {}}
            }


def test_trade_plan_is_persisted_and_not_evaluated_as_an_entry_rule(db_session):
    service = StrategyService(config=None)
    strategy_id = asyncio.run(service.create_strategy(
        db=db_session,
        name="Trade plan contract",
        description="Persistence-only contract test",
        version="1.0.0",
        direction="BOTH",
        weight=1.0,
        risk_multiplier=1.0,
        timeframes=["1h"],
        symbols=[],
        min_signal_score=70.0,
        rule_set={
            "entry_rules": _group(conditions=[_rsi("<", 30)]),
            "exit_rules": _group(conditions=[_rsi(">", 70)]),
            "trade_plan": _trade_plan(),
        },
    ))

    stored = db_session.query(StrategyRule).filter_by(
        strategy_id=strategy_id, rule_type="trade_plan"
    ).one()
    assert stored.rule_config["schema_version"] == 1
    assert stored.rule_config["take_profit"]["allocation"] == {
        "tp1": 40.0, "tp2": 30.0, "tp3": 20.0, "runner": 10.0
    }
    # Loading succeeds, but only the entry rule participates in evaluation.
    assert service.engine.evaluate_entry(
        strategy_id, {"rsi": 25.0}, "1h", "LONG"
    ) == (True, {"matched_rule_types": ["entry"]})


def test_trade_plan_rejects_invalid_version_allocation_and_missing_target(db_session):
    service = StrategyService(config=None)
    invalid_plans = []
    wrong_version = _trade_plan()
    wrong_version["schema_version"] = 2
    invalid_plans.append(wrong_version)
    bad_allocation = _trade_plan()
    bad_allocation["take_profit"]["allocation"]["runner"] = 15
    invalid_plans.append(bad_allocation)
    missing_target = _trade_plan()
    del missing_target["take_profit"]["targets"]["tp3"]
    invalid_plans.append(missing_target)

    for plan in invalid_plans:
        with pytest.raises(ValueError, match="Invalid trade_plan"):
            service._normalize_rule_set({
                "entry_rules": _group(conditions=[_rsi("<", 30)]),
                "trade_plan": plan,
            })


def test_trade_plan_rejects_unknown_fields_and_malformed_method_ids():
    service = StrategyService(config=None)
    unknown_field = _trade_plan()
    unknown_field["stop_loss"]["unexpected"] = True
    with pytest.raises(ValueError, match="Invalid trade_plan"):
        service._normalize_rule_set({
            "entry_rules": _group(conditions=[_rsi("<", 30)]),
            "trade_plan": unknown_field,
        })

    malformed_method = _trade_plan()
    malformed_method["runner"]["method"] = "ATR trailing"
    with pytest.raises(ValueError, match="Invalid trade_plan"):
        service._normalize_rule_set({
            "entry_rules": _group(conditions=[_rsi("<", 30)]),
            "trade_plan": malformed_method,
        })


def test_nested_and_or_groups_are_evaluated_recursively(db_session):
    strategy = Strategy(name="Nested", version="1.0.0", is_active=True)
    db_session.add(strategy)
    db_session.flush()
    rule = StrategyRule(
        strategy_id=strategy.id,
        rule_type="entry",
        rule_config=_group(
            operator="AND",
            conditions=[_rsi(">", 20)],
            groups=[_group(operator="OR", conditions=[_rsi("<", 30), _rsi(">", 80)])],
        ),
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()

    engine = StrategyEngine(config=None)
    engine.load_strategy(strategy, db_session)
    assert engine.evaluate_entry(strategy.id, {"rsi": 25.0}, "1h")[0] is True
    assert engine.evaluate_entry(strategy.id, {"rsi": 50.0}, "1h")[0] is False


def test_empty_missing_or_unsupported_rules_are_rejected(db_session):
    service = StrategyService(config=None)
    with pytest.raises(ValueError, match="cannot be empty"):
        service._normalize_rule_set({"entry_rules": _group()})
    with pytest.raises(ValueError, match="Unsupported comparison"):
        service._normalize_rule_set({
            "entry_rules": _group(conditions=[_rsi("crosses_above", 30)])
        })
    with pytest.raises(ValueError, match="Unsupported scanner indicator"):
        service._normalize_rule_set({
            "entry_rules": _group(conditions=[{
                "indicator": {"name": "OBV", "params": {}, "source": "close"},
                "operator": ">", "threshold": 0,
            }])
        })
    with pytest.raises(ValueError, match="required"):
        service._normalize_rule_set({"exit_rules": _group(conditions=[_rsi(">", 70)])})


def test_non_one_hour_rule_does_not_reuse_hourly_scanner_value(db_session):
    engine = StrategyEngine(config=None)
    group = _group(conditions=[_rsi("<", 30)])
    assert engine._group_matches(group, {"rsi": 20.0}, "15m") is False



def test_initialize_loads_active_strategies_from_database_and_closes_session(db_session):
    service = StrategyService(config=None, session_factory=lambda: db_session)
    strategy = Strategy(
        name="Startup loaded",
        version="1.0.0",
        is_active=True,
    )
    db_session.add(strategy)
    db_session.flush()
    db_session.add(StrategyRule(
        strategy_id=strategy.id,
        rule_type="entry",
        rule_config=_group(conditions=[_rsi("<", 30)]),
        is_active=True,
    ))
    db_session.commit()

    closed = []
    original_close = db_session.close

    def tracked_close():
        closed.append(True)
        # Keep the fixture-owned session usable for assertions after initialization.
        # SQLAlchemy close is safe here; the fixture closes it again at teardown.
        original_close()

    db_session.close = tracked_close

    asyncio.run(service.initialize())

    assert service._running is True
    assert strategy.id in service.engine._strategy_cache
    assert len(service.engine._rule_cache[strategy.id]) == 1
    assert closed == [True]
    assert service.engine.evaluate_entry(
        strategy.id, {"rsi": 25.0}, "1h", "LONG"
    )[0] is True


def test_initialize_without_session_factory_keeps_cache_empty():
    service = StrategyService(config=None)
    asyncio.run(service.initialize())
    assert service._running is True
    assert service.engine._strategy_cache == {}
    assert service.engine._rule_cache == {}
