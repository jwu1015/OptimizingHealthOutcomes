from datetime import date
from pathlib import Path

from precision.knowledge.dailymed import parse_spl

MINI = (Path(__file__).parent / "fixtures" / "mini_spl.xml").read_bytes()


def test_document_metadata():
    label = parse_spl(MINI)
    assert label.setid == "00000000-0000-0000-0000-000000000001"
    assert label.version == 3
    assert label.effective_date == date(2026, 9, 23)
    assert label.title == "EXAMPLESTATIN tablets"


def test_sections_are_numbered_and_nested():
    label = parse_spl(MINI)
    dosing = label.section("2.2")
    assert dosing is not None
    assert dosing.path == ["2 DOSAGE AND ADMINISTRATION", "2.2 Recommended Dosage in Adult Patients"]
    assert "5 mg to 40 mg orally once daily" in dosing.text


def test_parent_text_excludes_subsections():
    parent = parse_spl(MINI).section("2")
    assert parent.text == "Take with or without food."


def test_table_cells_stay_separated():
    assert "Starting dose | 10 mg" in parse_spl(MINI).section("2.2").text


def test_unclassified_pgx_subsection_is_findable_by_title():
    [pgx] = parse_spl(MINI).find("pharmacogenomics")
    assert pgx.number == "12.5"
    assert pgx.code == "42229-5"
