from pathlib import Path

import pytest

from precision.knowledge.cpic import CpicGuideline, CpicRecommendation, CpicSnapshot, LookupMethod
from precision.rules.pgx import PGxAction, classify, evaluate
from precision.schemas import Case, PatientRecord, PGxResult

ROOT = Path(__file__).resolve().parents[1]
# Real CPIC rows (statin guideline v72), trimmed to the cases under test.
SNAPSHOT = CpicSnapshot.model_validate_json((ROOT / "tests/fixtures/cpic_snapshot.json").read_text())
CASE = Case.model_validate_json((ROOT / "fixtures/cases/synthetic-lipid-001.json").read_text())


def patient_with(*results: PGxResult) -> PatientRecord:
    return CASE.patient.model_copy(update={"pgx": list(results)})


def slco1b1(phenotype: str) -> PGxResult:
    return PGxResult(
        gene="SLCO1B1", diplotype="*1/*1", phenotype=phenotype, tier="A", callers=["PharmCAT"], guideline_version="test"
    )


@pytest.mark.parametrize(
    ("text", "action", "start", "limit", "exclusive"),
    [
        ("Prescribe desired starting dose and adjust doses based on disease-specific guidelines.", PGxAction.STANDARD, None, None, False),
        (
            "Prescribe desired starting dose and adjust doses. Prescriber should be aware of possible increased risk for myopathy especially for doses >20mg.",
            PGxAction.STANDARD_WITH_CAUTION, None, None, False,
        ),
        ("Prescribe ≤20mg as a starting dose and adjust doses of atorvastatin.", PGxAction.MAX_STARTING_DOSE, 20, None, False),
        ("Prescribe ≤ 40mg as a starting dose and adjust doses of pravastatin.", PGxAction.MAX_STARTING_DOSE, 40, None, False),
        ("Based on SLCO1B1 status, prescribe ≤20mg as a starting dose.", PGxAction.MAX_STARTING_DOSE, 20, None, False),
        (
            "Prescribe an alternative statin depending on the desired potency. If simvastatin therapy is warranted, limit dose to <20mg/day.",
            PGxAction.PREFER_ALTERNATIVE, None, 20, True,
        ),
        ("Prescribe an alternative statin depending on the desired potency.", PGxAction.PREFER_ALTERNATIVE, None, None, False),
        ("No recommendation", PGxAction.NO_RECOMMENDATION, None, None, False),
        ("n/a", PGxAction.NO_RECOMMENDATION, None, None, False),
        ("Consider therapeutic drug monitoring.", PGxAction.NEEDS_REVIEW, None, None, False),
    ],
)
def test_classify(text, action, start, limit, exclusive):
    parsed = classify(text)
    assert parsed.action is action
    assert parsed.max_starting_dose_mg == start
    assert parsed.daily_dose_limit_mg == limit
    assert parsed.daily_dose_limit_exclusive is exclusive


def test_synthetic_case_rosuvastatin_caps_starting_dose():
    [finding] = evaluate(SNAPSHOT, CASE.patient, "rosuvastatin")
    assert finding.lookup == {"ABCG2": "No Result", "SLCO1B1": "Poor Function"}
    assert finding.not_tested == ["ABCG2"]
    assert finding.parsed.action is PGxAction.MAX_STARTING_DOSE
    assert finding.parsed.max_starting_dose_mg == 20
    assert finding.source.version == "72"


def test_synthetic_case_simvastatin_prefers_alternative():
    [finding] = evaluate(SNAPSHOT, CASE.patient, "simvastatin")
    assert finding.parsed.action is PGxAction.PREFER_ALTERNATIVE
    assert finding.classification == "Strong"


def test_dose_limit_carried_through():
    [finding] = evaluate(SNAPSHOT, patient_with(slco1b1("Possible Decreased Function")), "simvastatin")
    assert finding.parsed.action is PGxAction.PREFER_ALTERNATIVE
    assert (finding.parsed.daily_dose_limit_mg, finding.parsed.daily_dose_limit_exclusive) == (20, True)


def test_untested_gene_is_no_result_not_normal():
    [finding] = evaluate(SNAPSHOT, patient_with(), "rosuvastatin")
    assert finding.lookup == {"ABCG2": "No Result", "SLCO1B1": "No Result"}
    # CPIC has no row for neither gene tested, so this must go to a human, not default to standard dosing.
    assert finding.parsed.action is PGxAction.NEEDS_REVIEW


def test_untested_gene_without_cpic_row_needs_review():
    [finding] = evaluate(SNAPSHOT, patient_with(), "simvastatin")
    assert finding.lookup == {"SLCO1B1": "No Result"}
    assert finding.parsed.action is PGxAction.NEEDS_REVIEW
    assert "no CPIC row" in finding.note


def test_unknown_phenotype_term_needs_review():
    [finding] = evaluate(SNAPSHOT, patient_with(slco1b1("Poor metaboliser")), "simvastatin")
    assert finding.parsed.action is PGxAction.NEEDS_REVIEW


def test_tier_b_results_are_ignored():
    tier_b = slco1b1("Poor Function").model_copy(update={"tier": "B"})
    [finding] = evaluate(SNAPSHOT, patient_with(tier_b), "simvastatin")
    assert finding.lookup == {"SLCO1B1": "No Result"}


def test_drug_without_cpic_guideline_has_no_findings():
    assert evaluate(SNAPSHOT, CASE.patient, "ezetimibe") == []


def test_activity_score_lookup_uses_cpic_format():
    snapshot = CpicSnapshot(
        panel="t",
        drugs={},
        not_in_cpic=[],
        guidelines={
            1: CpicGuideline(
                id=1, name="g", url=None, version=1, genes=["CYP2C9"], lookup_methods={"CYP2C9": LookupMethod.ACTIVITY_SCORE}
            )
        },
        recommendations=[
            CpicRecommendation(
                id=1, guideline_id=1, drug="fluvastatin", lookup={"CYP2C9": "1.0"}, phenotypes={}, implications={},
                text="Prescribe ≤40mg as a starting dose.", classification="Moderate", comments=None,
                population="general", version=1,
            )
        ],
    )
    cyp2c9 = PGxResult(
        gene="CYP2C9", diplotype="*1/*3", phenotype="Intermediate Metabolizer", activity_score=1,
        tier="A", callers=["PharmCAT"], guideline_version="test",
    )
    [finding] = evaluate(snapshot, patient_with(cyp2c9), "fluvastatin")
    assert finding.lookup == {"CYP2C9": "1.0"}
    assert finding.parsed.max_starting_dose_mg == 40
