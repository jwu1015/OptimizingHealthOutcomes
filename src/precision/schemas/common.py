"""Types shared by the patient record, evidence and protocol schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Base for every schema: unknown fields are an error, not silently dropped."""

    model_config = ConfigDict(extra="forbid")


class Provenance(StrEnum):
    """Where a value came from. The label travels with the value into the protocol."""

    MEASURED = "measured"
    CURATED = "curated"
    MODELED = "modeled"
    HYPOTHESIZED = "hypothesized"


class SourceKind(StrEnum):
    DAILYMED_SPL = "dailymed_spl"
    PUBMED = "pubmed"
    CPIC = "cpic"
    CLINICALTRIALS = "clinicaltrials"
    GUIDELINE = "guideline"
    LAB_REPORT = "lab_report"
    PATIENT_REPORTED = "patient_reported"
    PHYSICIAN = "physician"


class SourceRef(Model):
    """A pointer precise enough to re-open the exact text a fact came from."""

    kind: SourceKind
    id: str  # DailyMed setid, PMID, NCT id, guideline slug, ...
    version: str | None = None
    section: str | None = None  # e.g. "2.2" for a label section
    url: str | None = None


class Quantity(Model):
    value: float
    unit: str  # UCUM
