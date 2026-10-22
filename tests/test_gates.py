from precision.evidence.gates import numbers_in_quote, quote_in_source, run_gates

SOURCE = "The dosage range is 5 mg to 40 mg orally once daily.\nInitiate at 10 mg in Asian patients — see 8.8."


def test_quote_found_across_line_breaks_and_typography():
    assert quote_in_source("once daily. Initiate at 10 mg in Asian patients - see 8.8", SOURCE).passed


def test_quote_not_in_source_fails():
    result = quote_in_source("The dosage range is 5 mg to 80 mg", SOURCE)
    assert not result.passed


def test_quote_is_case_sensitive():
    assert not quote_in_source("the dosage range", SOURCE).passed


def test_number_not_in_quote_fails():
    result = numbers_in_quote("Maximum dose is 80 mg", "The dosage range is 5 mg to 40 mg")
    assert not result.passed
    assert "80" in result.reasons[0]


def test_numbers_compare_by_value():
    assert numbers_in_quote("dose 1,000 mg or 40.0 mg", "1000 mg ... 40 mg").passed


def test_run_gates_reports_every_failure():
    result = run_gates("Maximum dose is 80 mg", "not in the label 5 mg", SOURCE)
    assert not result.passed
    assert len(result.reasons) == 2
