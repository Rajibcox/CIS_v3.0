from decimal import Decimal

import pytest

from src.backend.services.stop_loss_calculator import (
    StopLossCalculationError,
    calculate_initial_stop_loss,
)


def _candles(count=5):
    return [
        {
            "high": str(110 + i),
            "low": str(100 + i),
            "close": str(105 + i),
            "is_closed": True,
        }
        for i in range(count)
    ]


def test_long_swing_stop_uses_lowest_confirmed_low():
    result = calculate_initial_stop_loss(
        direction="LONG", entry_price="120",
        candles=_candles(), parameters={"lookback_candles": 3},
    )
    assert result.stop_price == Decimal("102")
    assert result.structural_price == Decimal("102")
    assert result.buffer_price == 0
    assert result.atr_value is None


def test_short_swing_stop_uses_highest_confirmed_high():
    result = calculate_initial_stop_loss(
        direction="SHORT", entry_price="100",
        candles=_candles(), parameters={"lookback_candles": 3},
    )
    assert result.stop_price == Decimal("114")
    assert result.structural_price == Decimal("114")


def test_atr_buffer_is_applied_only_when_strategy_configures_it():
    result = calculate_initial_stop_loss(
        direction="LONG", entry_price="120",
        candles=_candles(6),
        parameters={
            "lookback_candles": 3, "buffer_mode": "atr",
            "atr_period": 3, "atr_multiplier": "0.5",
        },
    )
    assert result.atr_value == Decimal("10")
    assert result.buffer_price == Decimal("5")
    assert result.stop_price == Decimal("98")


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_unconfirmed_candle_is_rejected(direction):
    candles = _candles()
    candles[-1]["is_closed"] = False
    with pytest.raises(StopLossCalculationError, match="confirmed closed"):
        calculate_initial_stop_loss(
            direction=direction, entry_price="120" if direction == "LONG" else "90",
            candles=candles, parameters={"lookback_candles": 3},
        )


def test_insufficient_candles_are_rejected():
    with pytest.raises(StopLossCalculationError, match="Insufficient candles"):
        calculate_initial_stop_loss(
            direction="LONG", entry_price="120", candles=_candles(2),
            parameters={"lookback_candles": 3},
        )


def test_invalid_ohlc_is_rejected():
    candles = _candles()
    candles[0]["low"] = "111"
    with pytest.raises(StopLossCalculationError, match="inconsistent OHLC"):
        calculate_initial_stop_loss(
            direction="LONG", entry_price="120", candles=candles,
            parameters={"lookback_candles": 3},
        )


@pytest.mark.parametrize(
    "direction,entry",
    [("LONG", "100"), ("SHORT", "120")],
)
def test_wrong_side_stop_is_rejected(direction, entry):
    with pytest.raises(StopLossCalculationError, match="must be"):
        calculate_initial_stop_loss(
            direction=direction, entry_price=entry, candles=_candles(),
            parameters={"lookback_candles": 3},
        )


def test_missing_atr_parameters_are_rejected():
    with pytest.raises(StopLossCalculationError, match="atr_period"):
        calculate_initial_stop_loss(
            direction="LONG", entry_price="120", candles=_candles(5),
            parameters={"lookback_candles": 3, "buffer_mode": "atr"},
        )


def test_atr_parameters_are_rejected_when_buffer_disabled():
    with pytest.raises(
        StopLossCalculationError,
        match="ATR parameters are not allowed",
    ):
        calculate_initial_stop_loss(
            direction="LONG", entry_price="120", candles=_candles(),
            parameters={"lookback_candles": 3, "atr_multiplier": 2},
        )
