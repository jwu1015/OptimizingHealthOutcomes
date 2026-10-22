"""DailyMed SPL labels: fetch, parse into a numbered section tree, and pin versions.

Labels are the grade-A source for dose ranges, contraindications, interactions and
PGx (04 · What it reads). Each drug is pinned to one setid in config/, and every
ingest records the label version and checksum in a lock file so a label change
shows up as a reviewable diff instead of silently changing the engine's inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from precision.knowledge.panels import load_panel
from precision.schemas.common import Model

API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
_HL7 = "{urn:hl7-org:v3}"
_BLOCK_TAGS = {"paragraph", "item", "tr", "list", "table", "br"}
_CELL_TAGS = {"td", "th"}
_INLINE_SPACED_TAGS = {"caption"}  # list bullets/numbers: keep them on the item's line
_SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\s+")


class LabelSection(Model):
    code: str | None  # LOINC section code; subsections are often the generic 42229-5
    code_name: str | None
    title: str
    number: str | None  # "2.2", "12.5"; parsed from the title
    path: list[str]  # titles from the top-level section down to this one
    text: str  # this section's own text, excluding subsections


class Label(Model):
    setid: str
    version: int
    effective_date: date
    title: str
    sha256: str
    sections: list[LabelSection]

    def section(self, number: str) -> LabelSection | None:
        return next((s for s in self.sections if s.number == number), None)

    def sections_with_code(self, code: str) -> list[LabelSection]:
        return [s for s in self.sections if s.code == code]

    def find(self, title_substring: str) -> list[LabelSection]:
        needle = title_substring.lower()
        return [s for s in self.sections if needle in s.title.lower()]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            walk(child)
            tag = _local(child.tag)
            if tag in _BLOCK_TAGS:
                parts.append("\n")
            elif tag in _CELL_TAGS:
                parts.append(" | ")
            elif tag in _INLINE_SPACED_TAGS:
                parts.append(" ")
            if child.tail:
                parts.append(child.tail)

    walk(el)
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in "".join(parts).split("\n"))
    return "\n".join(line for line in lines if line)


def _walk_sections(el: ET.Element, parent_path: list[str], out: list[LabelSection]) -> None:
    code_el = el.find(f"{_HL7}code")
    title = re.sub(r"\s+", " ", _text_of(el.find(f"{_HL7}title"))).strip()
    match = _SECTION_NUMBER.match(title)
    path = [*parent_path, title] if title else parent_path
    out.append(
        LabelSection(
            code=code_el.get("code") if code_el is not None else None,
            code_name=code_el.get("displayName") if code_el is not None else None,
            title=title,
            number=match.group(1) if match else None,
            path=path,
            text=_text_of(el.find(f"{_HL7}text")),
        )
    )
    for child in el.findall(f"{_HL7}component/{_HL7}section"):
        _walk_sections(child, path, out)


def parse_spl(xml: bytes) -> Label:
    root = ET.fromstring(xml)
    sections: list[LabelSection] = []
    for top in root.findall(f"{_HL7}component/{_HL7}structuredBody/{_HL7}component/{_HL7}section"):
        _walk_sections(top, [], sections)
    return Label(
        setid=root.find(f"{_HL7}setId").get("root"),
        version=int(root.find(f"{_HL7}versionNumber").get("value")),
        effective_date=datetime.strptime(root.find(f"{_HL7}effectiveTime").get("value")[:8], "%Y%m%d").date(),
        title=re.sub(r"\s+", " ", _text_of(root.find(f"{_HL7}title"))).strip(),
        sha256=hashlib.sha256(xml).hexdigest(),
        sections=sections,
    )


def fetch_spl(setid: str, client: httpx.Client) -> bytes:
    response = client.get(f"{API}/spls/{setid}.xml")
    response.raise_for_status()
    return response.content


def ingest_panel(config_path: Path, data_dir: Path, lock_path: Path) -> list[str]:
    """Fetch and parse every pinned label in a panel. Returns human-readable change notes."""
    panel = load_panel(config_path)
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    raw_dir = data_dir / "raw" / "dailymed"
    label_dir = data_dir / "labels"
    raw_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    notes = []
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for drug in panel.drugs:
            xml = fetch_spl(drug.setid, client)
            label = parse_spl(xml)
            (raw_dir / f"{label.setid}_v{label.version}.xml").write_bytes(xml)
            (label_dir / f"{drug.slug}.json").write_text(label.model_dump_json(indent=2))

            previous = lock.get(drug.slug)
            if previous is None:
                notes.append(f"{drug.slug}: pinned v{label.version} ({label.effective_date})")
            elif previous["sha256"] == label.sha256:
                continue
            else:
                notes.append(f"{drug.slug}: CHANGED v{previous['version']} -> v{label.version}; review the diff")
            lock[drug.slug] = {
                "setid": label.setid,
                "version": label.version,
                "effective_date": label.effective_date.isoformat(),
                "sha256": label.sha256,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    return notes


def load_label(data_dir: Path, slug: str) -> Label:
    return Label.model_validate_json((data_dir / "labels" / f"{slug}.json").read_text())
