"""The problem and target lists the physician confirms at the initial consult (02 · stage 2).

The engine never sets a target; it only plans against confirmed ones.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from .common import Model, Quantity
from .patient import PatientRecord


class Problem(Model):
    problem_id: str
    description: str
    supporting_loincs: list[str] = []
    confirmed_by: str | None = None


class TargetDirection(StrEnum):
    LOWER = "lower"
    RAISE = "raise"
    WITHIN = "within"


class Target(Model):
    target_id: str
    problem_id: str
    loinc: str
    display: str
    direction: TargetDirection
    low: Quantity | None = None
    high: Quantity | None = None
    confirmed_by: str | None = None

    @model_validator(mode="after")
    def _bounds_match_direction(self) -> Target:
        needed = {
            TargetDirection.LOWER: ("high",),
            TargetDirection.RAISE: ("low",),
            TargetDirection.WITHIN: ("low", "high"),
        }[self.direction]
        missing = [b for b in needed if getattr(self, b) is None]
        if missing:
            raise ValueError(f"target {self.target_id} ({self.direction}) needs bound(s): {missing}")
        return self


class Case(Model):
    """Everything the engine takes as input for one patient."""

    patient: PatientRecord
    problems: list[Problem]
    targets: list[Target]

    def unconfirmed(self) -> list[str]:
        ids = [p.problem_id for p in self.problems if not p.confirmed_by]
        ids += [t.target_id for t in self.targets if not t.confirmed_by]
        return ids
