"""HTTP acceptance tests for persistent strategy CRUD routes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.api.dependencies import get_db, get_strategy_service
from src.backend.api.routes.strategies import router
from src.backend.models.database import Base, StrategyRule
from src.backend.services.strategy_service import StrategyService


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    service = StrategyService(config=None)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_strategy_service] = lambda: service
    with TestClient(app) as client:
        yield client, factory, service
    Base.metadata.drop_all(engine)
    engine.dispose()


def _payload(name="API persisted strategy"):
    group = {
        "operator": "AND",
        "conditions": [{
            "indicator": {"name": "RSI", "params": {"period": 14}, "source": "close"},
            "operator": "<",
            "threshold": 30,
        }],
        "groups": [],
    }
    return {
        "name": name,
        "description": "HTTP persistence test",
        "version": "1.0.0",
        "is_active": True,
        "direction": "BOTH",
        "weight": 1.0,
        "risk_multiplier": 1.0,
        "timeframes": ["1h"],
        "symbols": [],
        "min_signal_score": 70.0,
        "rule_set": {"entry_rules": group, "exit_rules": group},
    }


def test_strategy_api_create_read_and_list_persist_across_requests(api_client):
    client, factory, _ = api_client
    created = client.post("/api/v1/strategies", json=_payload())
    assert created.status_code == 201, created.text
    strategy_id = created.json()["id"]

    fetched = client.get(f"/api/v1/strategies/{strategy_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "API persisted strategy"

    listed = client.get("/api/v1/strategies")
    assert listed.status_code == 200
    assert any(item["id"] == strategy_id for item in listed.json())

    with factory() as db:
        rules = db.query(StrategyRule).filter_by(strategy_id=strategy_id).all()
        assert {rule.rule_type for rule in rules} == {"entry", "exit"}


def _trade_plan():
    return {
                "schema_version": 1,
                "entry": "strategy_rule_match",
                "stop_loss": {"method": "strategy_defined_sl", "parameters": {"source": "configured_rule"}},
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


def test_strategy_api_persists_returns_updates_and_clones_trade_plan(api_client):
    client, factory, _ = api_client
    payload = _payload()
    payload["rule_set"]["trade_plan"] = _trade_plan()

    created = client.post("/api/v1/strategies", json=payload)
    assert created.status_code == 201, created.text
    strategy_id = created.json()["id"]

    fetched = client.get(f"/api/v1/strategies/{strategy_id}")
    assert fetched.status_code == 200
    assert fetched.json()["trade_plan"]["schema_version"] == 1

    updated_plan = _trade_plan()
    updated_plan["runner"]["parameters"] = {"trail_mode": "configured"}
    updated = client.put(
        f"/api/v1/strategies/{strategy_id}",
        json={"rule_set": {**payload["rule_set"], "trade_plan": updated_plan}},
    )
    assert updated.status_code == 200, updated.text

    cloned = client.post(
        f"/api/v1/strategies/{strategy_id}/clone",
        params={"new_name": "Trade plan clone"},
    )
    assert cloned.status_code == 201, cloned.text
    clone_id = cloned.json()["id"]
    assert cloned.json()["is_active"] is False
    assert cloned.json()["trade_plan"]["runner"]["parameters"] == {
        "trail_mode": "configured"
    }

    with factory() as db:
        source_plan = db.query(StrategyRule).filter_by(
            strategy_id=strategy_id, rule_type="trade_plan"
        ).one()
        clone_plan = db.query(StrategyRule).filter_by(
            strategy_id=clone_id, rule_type="trade_plan"
        ).one()
        assert source_plan.rule_config == clone_plan.rule_config


def test_strategy_api_rejects_invalid_trade_plan_without_persisting(api_client):
    client, factory, _ = api_client
    payload = _payload()
    payload["rule_set"]["trade_plan"] = _trade_plan()
    payload["rule_set"]["trade_plan"]["take_profit"]["allocation"]["runner"] = 20

    response = client.post("/api/v1/strategies", json=payload)
    assert response.status_code == 422, response.text
    with factory() as db:
        from src.backend.models.database import Strategy
        assert db.query(Strategy).count() == 0


def test_strategy_api_update_and_deactivate(api_client):
    client, _, _ = api_client
    created = client.post("/api/v1/strategies", json=_payload())
    strategy_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/strategies/{strategy_id}",
        json={"name": "Updated strategy", "weight": 0.75},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated strategy"
    assert updated.json()["weight"] == 0.75

    deactivated = client.delete(f"/api/v1/strategies/{strategy_id}")
    assert deactivated.status_code == 200
    assert client.get(
        "/api/v1/strategies", params={"active_only": "true"}
    ).json() == []


def test_strategy_api_clone_copies_persisted_rules(api_client):
    client, factory, _ = api_client
    created = client.post("/api/v1/strategies", json=_payload())
    source_id = created.json()["id"]

    cloned = client.post(
        f"/api/v1/strategies/{source_id}/clone",
        params={"new_name": "Cloned strategy"},
    )
    assert cloned.status_code == 201, cloned.text
    clone_id = cloned.json()["id"]
    assert cloned.json()["name"] == "Cloned strategy"
    assert cloned.json()["is_active"] is False

    with factory() as db:
        rules = db.query(StrategyRule).filter_by(strategy_id=clone_id).all()
        assert {rule.rule_type for rule in rules} == {"entry", "exit"}


def test_strategy_api_rejects_unsupported_rules_without_persisting(api_client):
    client, factory, _ = api_client
    payload = _payload()
    payload["rule_set"]["entry_rules"]["conditions"][0]["operator"] = "crosses_above"

    response = client.post("/api/v1/strategies", json=payload)
    assert response.status_code == 422
    with factory() as db:
        from src.backend.models.database import Strategy
        assert db.query(Strategy).count() == 0
