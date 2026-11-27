from decimal import Decimal

import pytest

from src.backend.services.take_profit_calculator import (
    TakeProfitCalculationError,
    calculate_take_profit_target,
)


def _candles(count=4):
    return [
        {
            "high": str(110 + i),
            "low": str(100 + i),
            "close": str(105 + i),
            "is_closed": True,
        }
        for i in range(count)
    ]


@pytest.mark.parametrize(
    "direction,entry,stop,expected",
    [
        ("LONG", "120", "110", "140"),
        ("SHORT", "100", "110", "80"),
    ],
)
def test_risk_reward_target_uses_initial_stop_distance(
    direction, entry, stop, expected
):
    result = calculate_take_profit_target(
        direction=direction,
        entry_price=entry,
        stop_price=stop,
        target={"method": "risk_reward", "parameters": {"r_multiple": 2.0}},
    )
    assert result.target_price == Decimal(expected)
    assert result.risk_distance == Decimal("10")
    assert result.distance_price == Decimal("20")
    assert result.atr_value is None
    assert result.candles_used == 0


@pytest.mark.parametrize(
    "direction,entry,expected",
    [("LONG", "100", "105"), ("SHORT", "100", "95")],
)
def test_fixed_percentage_target_is_directional(direction, entry, expected):
    result = calculate_take_profit_target(
        direction=direction,
        entry_price=entry,
        target={"method": "fixed_percentage", "parameters": {"percentage": 5.0}},
    )
    assert result.target_price == Decimal(expected)
    assert result.distance_price == Decimal("5")


@pytest.mark.parametrize(
    "direction,entry,expected",
    [("LONG", "120", "125"), ("SHORT", "90", "85")],
)
def test_atr_multiple_target_uses_confirmed_candle_true_ranges(
    direction, entry, expected
):
    result = calculate_take_profit_target(
        direction=direction,
        entry_price=entry,
        candles=_candles(4),
        target={
            "method": "atr_multiple",
            "parameters": {"atr_period": 3, "atr_multiplier": 0.5},
        },
    )
    assert result.atr_value == Decimal("10")
    assert result.distance_price == Decimal("5")
    assert result.target_price == Decimal(expected)
    assert result.candles_used == 4


def test_atr_target_rejects_unconfirmed_candle():
    candles = _candles()
    candles[-1]["is_closed"] = False
    with pytest.raises(TakeProfitCalculationError, match="confirmed closed"):
        calculate_take_profit_target(
            direction="LONG",
            entry_price="120",
            candles=candles,
            target={
                "method": "atr_multiple",
                "parameters": {"atr_period": 3, "atr_multiplier": 1.0},
            },
        )


def test_atr_target_rejects_insufficient_candles():
    with pytest.raises(TakeProfitCalculationError, match="Insufficient candles"):
        calculate_take_profit_target(
            direction="LONG",
            entry_price="120",
            candles=_candles(3),
            target={
                "method": "atr_multiple",
                "parameters": {"atr_period": 3, "atr_multiplier": 1.0},
            },
        )


def test_atr_target_rejects_inconsistent_ohlc():
    candles = _candles()
    candles[0]["low"] = "111"
    with pytest.raises(TakeProfitCalculationError, match="inconsistent OHLC"):
        calculate_take_profit_target(
            direction="LONG",
            entry_price="120",
            candles=candles,
            target={
                "method": "atr_multiple",
                "parameters": {"atr_period": 3, "atr_multiplier": 1.0},
            },
        )


@pytest.mark.parametrize(
    "direction,stop",
    [("LONG", "120"), ("SHORT", "100")],
)
def test_risk_reward_rejects_stop_on_wrong_side(direction, stop):
    with pytest.raises(TakeProfitCalculationError, match="stop_price must be"):
        calculate_take_profit_target(
            direction=direction,
            entry_price="100",
            stop_price=stop,
            target={"method": "risk_reward", "parameters": {"r_multiple": 1.0}},
        )


@pytest.mark.parametrize(
    "target",
    [
        {"method": "unknown", "parameters": {}},
        {"method": "risk_reward", "parameters": {}},
        {"method": "risk_reward", "parameters": {"r_multiple": 1.0, "extra": 1}},
        {"method": "atr_multiple", "parameters": {"atr_period": True, "atr_multiplier": 1.0}},
        {"method": "fixed_percentage", "parameters": {"percentage": 0}},
    ],
)
def test_invalid_target_configuration_is_rejected(target):
    with pytest.raises(TakeProfitCalculationError):
        calculate_take_profit_target(
            direction="LONG",
            entry_price="100",
            stop_price="90",
            candles=_candles(),
            target=target,
        )


@pytest.mark.parametrize(
    "direction,entry,target",
    [
        ("LONG", "NaN", {"method": "fixed_percentage", "parameters": {"percentage": 5.0}}),
        ("LONG", "100", {"method": "fixed_percentage", "parameters": {"percentage": 100.0}}),
    ],
)
def test_invalid_or_nonpositive_target_output_is_rejected(direction, entry, target):
    with pytest.raises(TakeProfitCalculationError):
        calculate_take_profit_target(
            direction=direction, entry_price=entry, target=target
        )
