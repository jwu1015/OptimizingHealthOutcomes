"""Graded, quote-grounded evidence claims (04 · Evidence grading)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .common import Model, SourceRef


class EvidenceGrade(StrEnum):
    A = "A"  # label, clinical guideline, meta-analysis of RCTs
    B = "B"  # human RCT
    C = "C"  # cohort, observational: supporting rationale only
    D = "D"  # case reports, FAERS: safety flags only
    E = "E"  # animal, in vitro, mechanistic: context only

    @property
    def can_justify_item(self) -> bool:
        return self in (EvidenceGrade.A, EvidenceGrade.B)


class StudyDesign(StrEnum):
    LABEL = "label"
    GUIDELINE = "guideline"
    META_ANALYSIS = "meta_analysis"
    RCT = "rct"
    COHORT = "cohort"
    CASE_CONTROL = "case_control"
    CASE_REPORT = "case_report"
    ADVERSE_EVENT_REPORT = "adverse_event_report"
    ANIMAL = "animal"
    IN_VITRO = "in_vitro"
    MECHANISTIC = "mechanistic"


class EvidenceClaim(Model):
    claim_id: str
    subject: str  # the drug or intervention
    outcome: str  # what it affects, e.g. "LDL-C", "myopathy risk"
    statement: str  # the claim in our words; every number in it must appear in `quote`
    quote: str = Field(min_length=1)  # verbatim span from the source
    source: SourceRef
    design: StudyDesign
    grade: EvidenceGrade
    population: str | None = None
    verified: bool = False  # set only by precision.evidence.gates after both gates pass
