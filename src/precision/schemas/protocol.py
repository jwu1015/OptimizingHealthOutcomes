"""The protocol the engine drafts and the physician signs (04 · What a candidate protocol must show).

The thesis rules are enforced here as validation, so a protocol that breaks them
cannot be constructed at all.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import model_validator

from .common import Model, Provenance, Quantity, SourceRef
from .evidence import EvidenceClaim


class ItemKind(StrEnum):
    RX = "rx"
    NON_RX = "non_rx"  # training, sleep, nutrition


class Dose(Model):
    amount: Quantity
    route: str
    frequency: str
    timing: str | None = None
    titration: str | None = None


class DoseBasis(Model):
    """The label text the dose comes from."""

    source: SourceRef
    quote: str


class RuledOut(Model):
    option: str
    reason: str
    rule_id: str | None = None
    source: SourceRef | None = None


class MonitoringOrder(Model):
    loinc: str
    display: str
    at_weeks: list[float]
    reason: str  # every ordered lab states why it's drawn
    action_threshold: str | None = None


class TrajectoryPoint(Model):
    at_weeks: float
    mean: float
    low: float
    high: float


class PredictedTrajectory(Model):
    loinc: str
    unit: str
    points: list[TrajectoryPoint]
    provenance: Provenance = Provenance.MODELED

    @model_validator(mode="after")
    def _never_measured(self) -> PredictedTrajectory:
        if self.provenance in (Provenance.MEASURED, Provenance.CURATED):
            raise ValueError("a predicted trajectory is modeled, never measured")
        return self


class ProtocolItem(Model):
    item_id: str
    kind: ItemKind
    name: str
    rxcui: str | None = None
    addresses_targets: list[str]
    rationale: str
    primary_evidence: list[EvidenceClaim]
    supporting_evidence: list[EvidenceClaim] = []
    dose: Dose | None = None
    dose_basis: DoseBasis | None = None
    ruled_out: list[RuledOut] = []
    pgx_note: str | None = None
    monitoring: list[MonitoringOrder] = []
    predicted: list[PredictedTrajectory] = []

    @model_validator(mode="after")
    def _thesis_rules(self) -> ProtocolItem:
        if not self.addresses_targets:
            raise ValueError(f"{self.item_id}: must address at least one confirmed target")
        if not self.primary_evidence:
            raise ValueError(f"{self.item_id}: needs primary evidence")
        weak = [c.claim_id for c in self.primary_evidence if not c.grade.can_justify_item]
        if weak:
            raise ValueError(f"{self.item_id}: primary evidence must be grade A or B, got {weak}")
        unverified = [c.claim_id for c in self.primary_evidence if not c.verified]
        if unverified:
            raise ValueError(f"{self.item_id}: primary evidence failed or skipped the quote gates: {unverified}")
        if self.kind is ItemKind.RX:
            if self.dose is None or self.dose_basis is None:
                raise ValueError(f"{self.item_id}: prescription items need a dose and its label basis")
            if not any(m.action_threshold for m in self.monitoring):
                raise ValueError(f"{self.item_id}: prescription items need a monitored marker with an action threshold")
        return self


class InteractionResult(StrEnum):
    NONE = "none"
    MONITOR = "monitor"
    ADJUST = "adjust"
    AVOID = "avoid"


class InteractionCheck(Model):
    item: str
    against: str  # another item, a current medication, a condition or a genotype
    result: InteractionResult
    note: str | None = None
    source: SourceRef | None = None


class ProtocolStatus(StrEnum):
    DRAFT = "draft"
    SIGNED = "signed"
    SUPERSEDED = "superseded"


class Protocol(Model):
    protocol_id: str
    patient_id: str
    created_at: datetime
    engine_version: str
    status: ProtocolStatus = ProtocolStatus.DRAFT
    items: list[ProtocolItem]
    interactions: list[InteractionCheck] = []
    signed_by: str | None = None
    signed_at: datetime | None = None

    @model_validator(mode="after")
    def _signature(self) -> Protocol:
        if self.status is ProtocolStatus.SIGNED and not (self.signed_by and self.signed_at):
            raise ValueError("a signed protocol needs signed_by and signed_at")
        return self
