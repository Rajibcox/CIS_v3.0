"""Strategy-specific initial stop-loss calculations.

Only confirmed OHLC candles are accepted. This module calculates a proposed
stop price; it does not qualify signals, size positions, or submit orders.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class StopLossResult:
    direction: str
    method: str
    stop_price: Decimal
    structural_price: Decimal
    buffer_price: Decimal
    atr_value: Optional[Decimal]
    candles_used: int


class StopLossCalculationError(ValueError):
    """Raised when the strategy's configured stop cannot be calculated safely."""


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise StopLossCalculationError(f"{label} must be numeric") from None
    if not result.is_finite() or result <= 0:
        raise StopLossCalculationError(f"{label} must be finite and positive")
    return result


def _read(candle: Any, key: str) -> Any:
    if isinstance(candle, dict):
        return candle.get(key)
    return getattr(candle, key, None)


def _confirmed_ohlc(candles: Iterable[Any]) -> list[dict[str, Decimal]]:
    result = []
    for index, candle in enumerate(candles):
        if _read(candle, "is_closed") is not True:
            raise StopLossCalculationError(
                f"Candle {index} is not explicitly confirmed closed"
            )
        high = _decimal(_read(candle, "high"), f"candle[{index}].high")
        low = _decimal(_read(candle, "low"), f"candle[{index}].low")
        close = _decimal(_read(candle, "close"), f"candle[{index}].close")
        if low > high or close < low or close > high:
            raise StopLossCalculationError(f"Candle {index} has inconsistent OHLC values")
        result.append({"high": high, "low": low, "close": close})
    return result


def calculate_initial_stop_loss(
    *,
    direction: str,
    entry_price: Any,
    candles: Iterable[Any],
    parameters: Any,
) -> StopLossResult:
    """Calculate a configured swing-structure stop using confirmed candles only.

    parameters must contain lookback_candles, buffer_mode, and, when
    buffer_mode='atr', atr_period and atr_multiplier. No defaults are inferred
    for the lookback or ATR settings.
    """
    direction = str(direction).upper()
    if direction not in {"LONG", "SHORT"}:
        raise StopLossCalculationError("direction must be LONG or SHORT")
    entry = _decimal(entry_price, "entry_price")

    if hasattr(parameters, "model_dump"):
        parameters = parameters.model_dump(mode="python")
    if not isinstance(parameters, dict):
        raise StopLossCalculationError("stop-loss parameters must be an object")
    allowed = {"lookback_candles", "buffer_mode", "atr_period", "atr_multiplier"}
    if set(parameters) - allowed:
        raise StopLossCalculationError("Unsupported stop-loss parameter")
    lookback = parameters.get("lookback_candles")
    if isinstance(lookback, bool) or not isinstance(lookback, int) or not 2 <= lookback <= 500:
        raise StopLossCalculationError("lookback_candles must be an integer from 2 to 500")
    buffer_mode = parameters.get("buffer_mode", "none")
    if buffer_mode not in {"none", "atr"}:
        raise StopLossCalculationError("buffer_mode must be 'none' or 'atr'")

    atr_period = parameters.get("atr_period")
    multiplier_raw = parameters.get("atr_multiplier")
    if buffer_mode == "none":
        if atr_period is not None or multiplier_raw is not None:
            raise StopLossCalculationError("ATR parameters are not allowed with buffer_mode='none'")
    else:
        if isinstance(atr_period, bool) or not isinstance(atr_period, int) or not 2 <= atr_period <= 200:
            raise StopLossCalculationError("atr_period must be an integer from 2 to 200")
        multiplier = _decimal(multiplier_raw, "atr_multiplier")
        if multiplier > Decimal("10"):
            raise StopLossCalculationError("atr_multiplier cannot exceed 10")

    raw_candles = list(candles or [])
    required = max(lookback, (atr_period + 1) if buffer_mode == "atr" else 0)
    if len(raw_candles) < required:
        raise StopLossCalculationError(
            f"Insufficient candles: need at least {required}, received {len(raw_candles)}"
        )
    # Validate every supplied candle so an unconfirmed candle cannot be hidden
    # outside the selected structural/ATR window.
    bars = _confirmed_ohlc(raw_candles)
    structure = bars[-lookback:]
    structural_price = (
        min(bar["low"] for bar in structure)
        if direction == "LONG"
        else max(bar["high"] for bar in structure)
    )

    atr_value = None
    buffer_price = Decimal("0")
    if buffer_mode == "atr":
        atr_bars = bars[-(atr_period + 1):]
        true_ranges = []
        for previous, current in zip(atr_bars, atr_bars[1:]):
            true_ranges.append(max(
                current["high"] - current["low"],
                abs(current["high"] - previous["close"]),
                abs(current["low"] - previous["close"]),
            ))
        atr_value = sum(true_ranges, Decimal("0")) / Decimal(atr_period)
        buffer_price = atr_value * multiplier

    stop_price = (
        structural_price - buffer_price
        if direction == "LONG"
        else structural_price + buffer_price
    )
    if stop_price <= 0:
        raise StopLossCalculationError("Calculated stop-loss price must be positive")
    if direction == "LONG" and stop_price >= entry:
        raise StopLossCalculationError("LONG stop-loss must be below entry price")
    if direction == "SHORT" and stop_price <= entry:
        raise StopLossCalculationError("SHORT stop-loss must be above entry price")

    return StopLossResult(
        direction=direction,
        method="swing_structure",
        stop_price=stop_price,
        structural_price=structural_price,
        buffer_price=buffer_price,
        atr_value=atr_value,
        candles_used=required,
    )
