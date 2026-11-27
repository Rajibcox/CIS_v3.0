"""Pure strategy-configured take-profit target calculations.

This module calculates one proposed target price. It does not qualify signals,
estimate trading costs, round exchange prices, size positions, persist state,
or submit/manage orders.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional


class TakeProfitCalculationError(ValueError):
    """Raised when a configured take-profit target cannot be calculated safely."""


@dataclass(frozen=True)
class TakeProfitResult:
    direction: str
    method: str
    target_price: Decimal
    distance_price: Decimal
    risk_distance: Optional[Decimal]
    atr_value: Optional[Decimal]
    candles_used: int


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise TakeProfitCalculationError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise TakeProfitCalculationError(f"{label} must be numeric") from None
    if not result.is_finite() or result <= 0:
        raise TakeProfitCalculationError(f"{label} must be finite and positive")
    return result


def _read(candle: Any, key: str) -> Any:
    if isinstance(candle, dict):
        return candle.get(key)
    return getattr(candle, key, None)


def _confirmed_ohlc(candles: Iterable[Any]) -> list[dict[str, Decimal]]:
    bars = []
    for index, candle in enumerate(candles):
        if _read(candle, "is_closed") is not True:
            raise TakeProfitCalculationError(
                f"Candle {index} is not explicitly confirmed closed"
            )
        high = _decimal(_read(candle, "high"), f"candle[{index}].high")
        low = _decimal(_read(candle, "low"), f"candle[{index}].low")
        close = _decimal(_read(candle, "close"), f"candle[{index}].close")
        if low > high or close < low or close > high:
            raise TakeProfitCalculationError(
                f"Candle {index} has inconsistent OHLC values"
            )
        bars.append({"high": high, "low": low, "close": close})
    return bars


def _target_config(target: Any) -> tuple[str, dict]:
    if hasattr(target, "model_dump"):
        target = target.model_dump(mode="python")
    if not isinstance(target, dict) or set(target) != {"method", "parameters"}:
        raise TakeProfitCalculationError("target must contain only method and parameters")

    method = target.get("method")
    parameters = target.get("parameters")
    if not isinstance(method, str) or not isinstance(parameters, dict):
        raise TakeProfitCalculationError("target method and parameters are invalid")

    expected = {
        "risk_reward": {"r_multiple"},
        "atr_multiple": {"atr_period", "atr_multiplier"},
        "fixed_percentage": {"percentage"},
    }
    if method not in expected:
        raise TakeProfitCalculationError(f"Unsupported take-profit method: {method}")
    if set(parameters) != expected[method]:
        raise TakeProfitCalculationError(
            f"{method} requires exactly these parameters: {sorted(expected[method])}"
        )
    return method, parameters


def calculate_take_profit_target(
    *,
    direction: str,
    entry_price: Any,
    target: Any,
    stop_price: Any = None,
    candles: Iterable[Any] = (),
) -> TakeProfitResult:
    """Calculate one configured LONG/SHORT take-profit target.

    ATR uses a simple average of the last atr_period true-range observations,
    which requires atr_period + 1 chronologically ordered, confirmed candles.
    The caller is responsible for supplying candles in chronological order and
    ensuring their timestamps/timeframe/freshness are appropriate.
    """
    if not isinstance(direction, str) or direction.upper() not in {"LONG", "SHORT"}:
        raise TakeProfitCalculationError("direction must be LONG or SHORT")
    direction = direction.upper()
    entry = _decimal(entry_price, "entry_price")
    method, parameters = _target_config(target)

    risk_distance = None
    atr_value = None
    candles_used = 0

    if method == "risk_reward":
        multiple = _decimal(parameters["r_multiple"], "r_multiple")
        if multiple > Decimal("50"):
            raise TakeProfitCalculationError("r_multiple cannot exceed 50")
        stop = _decimal(stop_price, "stop_price")
        if direction == "LONG" and stop >= entry:
            raise TakeProfitCalculationError("LONG stop_price must be below entry_price")
        if direction == "SHORT" and stop <= entry:
            raise TakeProfitCalculationError("SHORT stop_price must be above entry_price")
        risk_distance = abs(entry - stop)
        distance = risk_distance * multiple

    elif method == "fixed_percentage":
        percentage = _decimal(parameters["percentage"], "percentage")
        if percentage > Decimal("100"):
            raise TakeProfitCalculationError("percentage cannot exceed 100")
        distance = entry * percentage / Decimal("100")

    else:
        period = parameters["atr_period"]
        if isinstance(period, bool) or not isinstance(period, int) or not 2 <= period <= 200:
            raise TakeProfitCalculationError("atr_period must be an integer from 2 to 200")
        multiplier = _decimal(parameters["atr_multiplier"], "atr_multiplier")
        if multiplier > Decimal("50"):
            raise TakeProfitCalculationError("atr_multiplier cannot exceed 50")

        raw_candles = list(candles or [])
        required = period + 1
        if len(raw_candles) < required:
            raise TakeProfitCalculationError(
                f"Insufficient candles: need at least {required}, received {len(raw_candles)}"
            )
        bars = _confirmed_ohlc(raw_candles)
        selected = bars[-required:]
        true_ranges = []
        for previous, current in zip(selected, selected[1:]):
            true_ranges.append(max(
                current["high"] - current["low"],
                abs(current["high"] - previous["close"]),
                abs(current["low"] - previous["close"]),
            ))
        atr_value = sum(true_ranges, Decimal("0")) / Decimal(period)
        if not atr_value.is_finite() or atr_value <= 0:
            raise TakeProfitCalculationError("Calculated ATR must be finite and positive")
        distance = atr_value * multiplier
        candles_used = required

    target_price = entry + distance if direction == "LONG" else entry - distance
    if not target_price.is_finite() or target_price <= 0:
        raise TakeProfitCalculationError("Calculated target price must be finite and positive")
    if direction == "LONG" and target_price <= entry:
        raise TakeProfitCalculationError("LONG target must be above entry_price")
    if direction == "SHORT" and target_price >= entry:
        raise TakeProfitCalculationError("SHORT target must be below entry_price")

    return TakeProfitResult(
        direction=direction,
        method=method,
        target_price=target_price,
        distance_price=distance,
        risk_distance=risk_distance,
        atr_value=atr_value,
        candles_used=candles_used,
    )
