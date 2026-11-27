"""Typed, versioned strategy trade-plan configuration.

These models define and validate persisted configuration only. They do not
implement price calculations, qualify signals, or authorize order execution.
"""
from math import isclose, isfinite
from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator


class TradePlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TradePlanMethod(TradePlanModel):
    """Opaque method identifier and its method-specific parameters."""

    method: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TradePlanAllocation(TradePlanModel):
    """Original QUANTUM TRADER partial-exit allocation."""

    tp1: float = Field(default=40.0, gt=0.0, le=100.0)
    tp2: float = Field(default=30.0, gt=0.0, le=100.0)
    tp3: float = Field(default=20.0, gt=0.0, le=100.0)
    runner: float = Field(default=10.0, gt=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_total_allocation(self):
        values = (self.tp1, self.tp2, self.tp3, self.runner)
        if not all(isfinite(value) for value in values):
            raise ValueError("Trade-plan allocations must be finite numbers")
        if not isclose(sum(values), 100.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("Trade-plan allocations must total exactly 100%")
        return self


class SwingStructureStopLossParameters(TradePlanModel):
    """Strategy-owned parameters for confirmed swing-structure stops."""

    lookback_candles: int = Field(..., ge=2, le=500)
    buffer_mode: Literal["none", "atr"] = "none"
    atr_period: Optional[int] = Field(default=None, ge=2, le=200)
    atr_multiplier: Optional[float] = Field(default=None, gt=0.0, le=10.0)

    @model_validator(mode="after")
    def validate_buffer_parameters(self):
        if self.buffer_mode == "none":
            if self.atr_period is not None or self.atr_multiplier is not None:
                raise ValueError("ATR parameters must be omitted when buffer_mode is 'none'")
        elif self.atr_period is None or self.atr_multiplier is None:
            raise ValueError("ATR buffer requires both atr_period and atr_multiplier")
        if self.atr_multiplier is not None and not isfinite(self.atr_multiplier):
            raise ValueError("atr_multiplier must be finite")
        return self


class TradePlanStopLoss(TradePlanModel):
    """Only the implemented, validated initial stop method is accepted."""

    method: Literal["swing_structure"]
    parameters: SwingStructureStopLossParameters


class RiskRewardTakeProfitParameters(TradePlanModel):
    """Target distance expressed as a multiple of initial stop risk."""

    r_multiple: StrictFloat = Field(..., gt=0.0, le=50.0)

    @model_validator(mode="after")
    def validate_finite_multiple(self):
        if not isfinite(self.r_multiple):
            raise ValueError("r_multiple must be finite")
        return self


class ATRMultipleTakeProfitParameters(TradePlanModel):
    """Target distance expressed as a strategy-configured ATR multiple."""

    atr_period: StrictInt = Field(..., ge=2, le=200)
    atr_multiplier: StrictFloat = Field(..., gt=0.0, le=50.0)

    @model_validator(mode="after")
    def validate_finite_multiplier(self):
        if not isfinite(self.atr_multiplier):
            raise ValueError("atr_multiplier must be finite")
        return self


class FixedPercentageTakeProfitParameters(TradePlanModel):
    """Target distance expressed as an explicit percentage from entry."""

    percentage: StrictFloat = Field(..., gt=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_finite_percentage(self):
        if not isfinite(self.percentage):
            raise ValueError("percentage must be finite")
        return self


class RiskRewardTakeProfitTarget(TradePlanModel):
    method: Literal["risk_reward"]
    parameters: RiskRewardTakeProfitParameters


class ATRMultipleTakeProfitTarget(TradePlanModel):
    method: Literal["atr_multiple"]
    parameters: ATRMultipleTakeProfitParameters


class FixedPercentageTakeProfitTarget(TradePlanModel):
    method: Literal["fixed_percentage"]
    parameters: FixedPercentageTakeProfitParameters


TakeProfitTarget = Annotated[
    Union[
        RiskRewardTakeProfitTarget,
        ATRMultipleTakeProfitTarget,
        FixedPercentageTakeProfitTarget,
    ],
    Field(discriminator="method"),
]


class TradePlanTakeProfit(TradePlanModel):
    targets: Dict[str, TakeProfitTarget]
    allocation: TradePlanAllocation = Field(default_factory=TradePlanAllocation)

    @model_validator(mode="after")
    def require_three_targets(self):
        expected = {"tp1", "tp2", "tp3"}
        if set(self.targets) != expected:
            raise ValueError("Take-profit targets must define exactly tp1, tp2, and tp3")
        return self


class TradePlanConfig(TradePlanModel):
    """Persistable plan contract; deliberately not an executable trade plan."""

    schema_version: Literal[1]
    entry: Literal["strategy_rule_match"] = "strategy_rule_match"
    stop_loss: TradePlanStopLoss
    take_profit: TradePlanTakeProfit
    runner: TradePlanMethod
