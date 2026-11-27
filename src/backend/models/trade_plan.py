"""Typed, versioned strategy trade-plan configuration.

These models define and validate persisted configuration only. They do not
implement price calculations, qualify signals, or authorize order execution.
"""
from math import isclose, isfinite
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class TradePlanTakeProfit(TradePlanModel):
    targets: Dict[str, TradePlanMethod]
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
    stop_loss: TradePlanMethod
    take_profit: TradePlanTakeProfit
    runner: TradePlanMethod
