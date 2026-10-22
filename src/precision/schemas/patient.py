"""The normalized patient record (03 · Data We Collect). Shaped to map onto FHIR R4."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from .common import Model, Provenance, Quantity, SourceRef


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Observation(Model):
    """One lab value or measurement. FHIR Observation, coded with LOINC."""

    loinc: str
    display: str
    value: Quantity | None = None
    value_text: str | None = None  # for results that aren't numbers ("negative", "<0.5")
    effective: datetime
    fasting: bool | None = None
    provenance: Provenance = Provenance.MEASURED
    source: SourceRef | None = None


class MedicationStatement(Model):
    """Anything the patient currently takes, prescription or not (the interaction base case)."""

    name: str
    rxcui: str | None = None
    dose: Quantity | None = None
    route: str | None = None
    frequency: str | None = None
    start: date | None = None
    end: date | None = None
    is_supplement: bool = False


class Condition(Model):
    name: str
    code: str | None = None  # SNOMED CT or ICD-10
    active: bool = True
    note: str | None = None


class Allergy(Model):
    substance: str
    reaction: str | None = None


class PGxTier(StrEnum):
    """03 · Genetics: only tier A may change a drug or dose choice."""

    A_GUIDELINE = "A"
    B_ASSOCIATION = "B"


class PGxResult(Model):
    gene: str
    diplotype: str
    phenotype: str  # CPIC phenotype term, e.g. "Decreased Function"
    activity_score: float | None = None
    tier: PGxTier
    callers: list[str]  # CYP2D6 needs two; disagreements are surfaced, not resolved
    guideline_version: str  # pinned CPIC / ClinPGx data version


class PatientRecord(Model):
    patient_id: str
    sex: Sex
    birth_date: date
    goals: list[str] = []  # patient-stated, before the physician makes them measurable
    observations: list[Observation] = []
    medications: list[MedicationStatement] = []
    conditions: list[Condition] = []
    allergies: list[Allergy] = []
    pgx: list[PGxResult] = []

    def latest(self, loinc: str) -> Observation | None:
        matches = [o for o in self.observations if o.loinc == loinc]
        return max(matches, key=lambda o: o.effective) if matches else None
