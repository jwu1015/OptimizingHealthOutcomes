"""Deterministic gates every LLM-extracted claim must pass (04 · How LLMs are used, and bounded).

1. The quote exists verbatim in the source text.
2. Every number in the claim's statement appears in the quote.

Together these catch the common fabrication: a real number attached to
something that didn't produce it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Typographic variants that differ between a source and a faithful copy of it.
_EQUIVALENT_CHARS = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "−": "-",
    }
)
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def normalize(text: str) -> str:
    """Normalize for verbatim comparison: Unicode form, typographic quotes/dashes, whitespace."""
    text = unicodedata.normalize("NFKC", text).translate(_EQUIVALENT_CHARS)
    return re.sub(r"\s+", " ", text).strip()


def numbers_in(text: str) -> set[Decimal]:
    found = set()
    for raw in _NUMBER.findall(normalize(text)):
        try:
            found.add(Decimal(raw.replace(",", "")).normalize())
        except InvalidOperation:
            continue
    return found


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...] = ()


def quote_in_source(quote: str, source_text: str) -> GateResult:
    q = normalize(quote)
    if not q:
        return GateResult(False, ("empty quote",))
    if q not in normalize(source_text):
        return GateResult(False, ("quote not found verbatim in source",))
    return GateResult(True)


def numbers_in_quote(statement: str, quote: str) -> GateResult:
    missing = numbers_in(statement) - numbers_in(quote)
    if missing:
        listed = ", ".join(format(n, "f") for n in sorted(missing))
        return GateResult(False, (f"numbers in statement not in quote: {listed}",))
    return GateResult(True)


def run_gates(statement: str, quote: str, source_text: str) -> GateResult:
    results = (quote_in_source(quote, source_text), numbers_in_quote(statement, quote))
    reasons = tuple(r for result in results for r in result.reasons)
    return GateResult(not reasons, reasons)
