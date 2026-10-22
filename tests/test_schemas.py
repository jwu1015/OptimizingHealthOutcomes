from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from precision.schemas import (
    Case,
    Dose,
    DoseBasis,
    EvidenceClaim,
    EvidenceGrade,
    ItemKind,
    MonitoringOrder,
    PredictedTrajectory,
    Protocol,
    ProtocolItem,
    ProtocolStatus,
    Provenance,
    Quantity,
    SourceKind,
    SourceRef,
    StudyDesign,
    Target,
)

ROOT = Path(__file__).resolve().parents[1]
LABEL = SourceRef(kind=SourceKind.DAILYMED_SPL, id="setid", version="19", section="2.2")


def claim(grade=EvidenceGrade.A, verified=True):
    return EvidenceClaim(
        claim_id="c1",
        subject="rosuvastatin",
        outcome="LDL-C",
        statement="lowers LDL-C",
        quote="lowers LDL-C",
        source=LABEL,
        design=StudyDesign.LABEL,
        grade=grade,
        verified=verified,
    )


def rx_item(**overrides):
    fields = dict(
        item_id="i1",
        kind=ItemKind.RX,
        name="rosuvastatin",
        addresses_targets=["T1"],
        rationale="ApoB above confirmed target",
        primary_evidence=[claim()],
        dose=Dose(amount=Quantity(value=5, unit="mg"), route="oral", frequency="once daily"),
        dose_basis=DoseBasis(source=LABEL, quote="5 mg to 40 mg orally once daily"),
        monitoring=[
            MonitoringOrder(
                loinc="1884-6",
                display="ApoB",
                at_weeks=[6],
                reason="response",
                action_threshold="no fall after 6 weeks -> review",
            )
        ],
    )
    fields.update(overrides)
    return ProtocolItem(**fields)


def test_synthetic_case_fixture_loads():
    case = Case.model_validate_json((ROOT / "fixtures/cases/synthetic-lipid-001.json").read_text())
    assert case.unconfirmed() == []
    assert case.patient.latest("1884-6").value.value == 128


def test_valid_rx_item():
    assert rx_item().name == "rosuvastatin"


@pytest.mark.parametrize("grade", [EvidenceGrade.C, EvidenceGrade.D, EvidenceGrade.E])
def test_primary_evidence_must_be_grade_a_or_b(grade):
    with pytest.raises(ValidationError, match="grade A or B"):
        rx_item(primary_evidence=[claim(grade=grade)])


def test_primary_evidence_must_pass_gates():
    with pytest.raises(ValidationError, match="quote gates"):
        rx_item(primary_evidence=[claim(verified=False)])


def test_rx_needs_dose_basis():
    with pytest.raises(ValidationError, match="label basis"):
        rx_item(dose_basis=None)


def test_rx_needs_action_threshold():
    with pytest.raises(ValidationError, match="action threshold"):
        rx_item(monitoring=[])


def test_predicted_trajectory_cannot_claim_measured():
    with pytest.raises(ValidationError, match="never measured"):
        PredictedTrajectory(loinc="1884-6", unit="mg/dL", points=[], provenance=Provenance.MEASURED)


def test_target_bounds_must_match_direction():
    with pytest.raises(ValidationError, match="needs bound"):
        Target(target_id="T1", problem_id="P1", loinc="1884-6", display="ApoB", direction="lower")


def test_signed_protocol_needs_signature():
    with pytest.raises(ValidationError, match="signed_by"):
        Protocol(
            protocol_id="p1",
            patient_id="x",
            created_at=datetime(2026, 10, 22),
            engine_version="0.1.0",
            status=ProtocolStatus.SIGNED,
            items=[rx_item()],
        )
