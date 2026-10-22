"""PGx rules: a patient's tier-A results + a CPIC snapshot -> constraints the engine can act on.

Two deterministic steps:

1. Look up the CPIC recommendation for the patient's genotype. A gene the patient
   has no tier-A result for is looked up as "No Result", CPIC's own term. An
   untested gene is never treated as normal.
2. Classify the recommendation text into an action (standard, max starting dose,
   prefer an alternative, ...). Text that doesn't match a known pattern becomes
   NEEDS_REVIEW and is shown to the physician verbatim. Nothing is guessed.
"""

from __future__ import annotations

import re
from collections import Counter
from enum import StrEnum

from precision.evidence.gates import normalize
from precision.knowledge.cpic import CpicRecommendation, CpicSnapshot, LookupMethod
from precision.schemas.common import Model, SourceKind, SourceRef
from precision.schemas.patient import PatientRecord, PGxResult, PGxTier

NO_RESULT = "No Result"


class PGxAction(StrEnum):
    STANDARD = "standard"
    STANDARD_WITH_CAUTION = "standard_with_caution"
    MAX_STARTING_DOSE = "max_starting_dose"
    PREFER_ALTERNATIVE = "prefer_alternative"
    NO_RECOMMENDATION = "no_recommendation"
    NEEDS_REVIEW = "needs_review"


class ParsedRecommendation(Model):
    action: PGxAction
    max_starting_dose_mg: float | None = None
    daily_dose_limit_mg: float | None = None  # "limit dose to <20mg/day"
    daily_dose_limit_exclusive: bool = False  # True for "<", False for "≤"


_NO_RECOMMENDATION = re.compile(r"^(no recommendation|n/a)\.?$", re.I)
_ALTERNATIVE = re.compile(r"\bprescribe an alternative\b", re.I)
_DAILY_LIMIT = re.compile(r"limit dose to\s*([<≤])\s*(\d+(?:\.\d+)?)\s*mg\s*/\s*day", re.I)
_MAX_START = re.compile(r"\bprescribe\s*≤\s*(\d+(?:\.\d+)?)\s*mg as a starting dose", re.I)
_STANDARD = re.compile(r"\bprescribe desired starting dose\b", re.I)
_CAUTION = re.compile(r"\bshould be aware\b", re.I)


def classify(text: str) -> ParsedRecommendation:
    t = normalize(text)
    if _NO_RECOMMENDATION.match(t):
        return ParsedRecommendation(action=PGxAction.NO_RECOMMENDATION)
    if _ALTERNATIVE.search(t):
        limit = _DAILY_LIMIT.search(t)
        return ParsedRecommendation(
            action=PGxAction.PREFER_ALTERNATIVE,
            daily_dose_limit_mg=float(limit.group(2)) if limit else None,
            daily_dose_limit_exclusive=bool(limit and limit.group(1) == "<"),
        )
    if m := _MAX_START.search(t):
        return ParsedRecommendation(action=PGxAction.MAX_STARTING_DOSE, max_starting_dose_mg=float(m.group(1)))
    if _STANDARD.search(t):
        caution = bool(_CAUTION.search(t))
        return ParsedRecommendation(action=PGxAction.STANDARD_WITH_CAUTION if caution else PGxAction.STANDARD)
    return ParsedRecommendation(action=PGxAction.NEEDS_REVIEW)


class PGxFinding(Model):
    drug: str
    lookup: dict[str, str]  # the genotype key used, gene -> value
    not_tested: list[str]  # genes looked up as "No Result"
    recommendation: str  # CPIC text, verbatim; empty if no row matched
    classification: str
    implications: dict[str, str]
    parsed: ParsedRecommendation
    population: str | None
    source: SourceRef
    note: str | None = None


def _lookup_value(result: PGxResult | None, method: LookupMethod) -> str | None:
    if result is None:
        return None
    if method is LookupMethod.PHENOTYPE:
        return result.phenotype
    if method is LookupMethod.ACTIVITY_SCORE:
        return f"{result.activity_score:.1f}" if result.activity_score is not None else None
    raise ValueError(f"{result.gene}: CPIC lookup by {method} is not supported yet")


def evaluate(snapshot: CpicSnapshot, patient: PatientRecord, drug: str) -> list[PGxFinding]:
    """CPIC findings for one panel drug. Empty if CPIC has no guideline for it."""
    tier_a = {p.gene: p for p in patient.pgx if p.tier is PGxTier.A_GUIDELINE}
    by_guideline: dict[int, list[CpicRecommendation]] = {}
    for rec in snapshot.for_drug(drug):
        by_guideline.setdefault(rec.guideline_id, []).append(rec)

    findings = []
    for gid, recs in sorted(by_guideline.items()):
        guideline = snapshot.guidelines[gid]
        source = SourceRef(kind=SourceKind.CPIC, id=str(gid), version=str(guideline.version), url=guideline.url)
        genes = sorted({gene for rec in recs for gene in rec.lookup})
        lookup, not_tested = {}, []
        for gene in genes:
            value = _lookup_value(tier_a.get(gene), guideline.lookup_methods[gene])
            if value is None:
                value = NO_RESULT
                not_tested.append(gene)
            lookup[gene] = value

        matches = [rec for rec in recs if rec.lookup == lookup]
        if not matches:
            findings.append(
                PGxFinding(
                    drug=drug,
                    lookup=lookup,
                    not_tested=not_tested,
                    recommendation="",
                    classification="n/a",
                    implications={},
                    parsed=ParsedRecommendation(action=PGxAction.NEEDS_REVIEW),
                    population=None,
                    source=source,
                    note=f"no CPIC row for {lookup} in '{guideline.name}'; check the phenotype terms against CPIC's vocabulary",
                )
            )
            continue
        for rec in matches:
            findings.append(
                PGxFinding(
                    drug=drug,
                    lookup=lookup,
                    not_tested=not_tested,
                    recommendation=rec.text,
                    classification=rec.classification,
                    implications=rec.implications,
                    parsed=classify(rec.text),
                    population=rec.population,
                    source=source,
                )
            )
    return findings


def classification_report(snapshot: CpicSnapshot) -> tuple[Counter, list[CpicRecommendation]]:
    """How every row in a snapshot classifies, plus the rows that need a human to read them."""
    counts: Counter = Counter()
    needs_review = []
    for rec in snapshot.recommendations:
        action = classify(rec.text).action
        counts[action] += 1
        if action is PGxAction.NEEDS_REVIEW:
            needs_review.append(rec)
    return counts, needs_review
