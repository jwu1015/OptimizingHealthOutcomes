"""CPIC gene–drug guidelines: fetch a pinned snapshot for a drug panel.

CPIC recommendations are the grade-A source for tier-A pharmacogenomics
(03 · Genetics). The API is PostgREST over the CPIC database. Rows are kept
verbatim, and each guideline's version is recorded so a recommendation in a
protocol traces back to the exact guideline data that produced it.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path

import httpx

from precision.knowledge.panels import DrugPanel, load_panel
from precision.schemas.common import Model

API = "https://api.cpicpgx.org/v1"


class LookupMethod(StrEnum):
    """How CPIC keys a gene's recommendations: by phenotype, activity score or allele status."""

    PHENOTYPE = "PHENOTYPE"
    ACTIVITY_SCORE = "ACTIVITY_SCORE"
    ALLELE_STATUS = "ALLELE_STATUS"


class CpicGuideline(Model):
    id: int
    name: str
    url: str | None
    version: int
    genes: list[str]
    lookup_methods: dict[str, LookupMethod]


class CpicDrug(Model):
    name: str
    rxcui: str
    guideline_id: int | None


class CpicRecommendation(Model):
    id: int
    guideline_id: int
    drug: str  # panel slug
    lookup: dict[str, str]  # gene -> phenotype or activity score; "No Result" when untested
    phenotypes: dict[str, str]
    implications: dict[str, str]
    text: str  # CPIC's drugrecommendation, verbatim
    classification: str  # Strong / Moderate / Optional / No Recommendation / n/a
    comments: str | None
    population: str
    version: int


class CpicSnapshot(Model):
    panel: str
    drugs: dict[str, CpicDrug]  # by panel slug
    not_in_cpic: list[str]  # panel slugs CPIC has no entry for
    guidelines: dict[int, CpicGuideline]
    recommendations: list[CpicRecommendation]

    def for_drug(self, slug: str) -> list[CpicRecommendation]:
        return [r for r in self.recommendations if r.drug == slug]

    def sha256(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()


def _get(client: httpx.Client, table: str, **params: str) -> list[dict]:
    response = client.get(f"{API}/{table}", params=params)
    response.raise_for_status()
    return response.json()


def fetch_snapshot(panel: DrugPanel, client: httpx.Client) -> CpicSnapshot:
    drugs: dict[str, CpicDrug] = {}
    not_in_cpic: list[str] = []
    recommendations: list[CpicRecommendation] = []

    for pinned in panel.drugs:
        rows = _get(client, "drug", name=f"eq.{pinned.ingredient}", select="drugid,name,rxnormid,guidelineid")
        if not rows:
            not_in_cpic.append(pinned.slug)
            continue
        row = rows[0]
        drugs[pinned.slug] = CpicDrug(name=row["name"], rxcui=row["rxnormid"], guideline_id=row["guidelineid"])
        for rec in _get(client, "recommendation", drugid=f"eq.{row['drugid']}", select="*", order="id"):
            recommendations.append(
                CpicRecommendation(
                    id=rec["id"],
                    guideline_id=rec["guidelineid"],
                    drug=pinned.slug,
                    lookup=rec["lookupkey"] or {},
                    phenotypes=rec["phenotypes"] or {},
                    implications=rec["implications"] or {},
                    text=rec["drugrecommendation"],
                    classification=rec["classification"],
                    comments=rec["comments"],
                    population=rec["population"],
                    version=rec["version"],
                )
            )

    guideline_ids = {r.guideline_id for r in recommendations}
    guideline_ids |= {d.guideline_id for d in drugs.values() if d.guideline_id is not None}
    guidelines: dict[int, CpicGuideline] = {}
    for gid in sorted(guideline_ids):
        g = _get(client, "guideline", id=f"eq.{gid}")[0]
        methods = _get(client, "gene", symbol=f"in.({','.join(g['genes'])})", select="symbol,lookupmethod")
        guidelines[gid] = CpicGuideline(
            id=g["id"],
            name=g["name"],
            url=g["url"],
            version=g["version"],
            genes=g["genes"],
            lookup_methods={m["symbol"]: m["lookupmethod"] for m in methods},
        )

    return CpicSnapshot(
        panel=panel.panel,
        drugs=drugs,
        not_in_cpic=not_in_cpic,
        guidelines=guidelines,
        recommendations=recommendations,
    )


def snapshot_path(data_dir: Path, panel: str) -> Path:
    return data_dir / "cpic" / f"{panel}.json"


def ingest_panel(config_path: Path, data_dir: Path, lock_path: Path) -> tuple[CpicSnapshot, list[str]]:
    """Fetch the CPIC snapshot for a panel and pin it. Returns the snapshot and change notes."""
    panel = load_panel(config_path)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        snapshot = fetch_snapshot(panel, client)

    path = snapshot_path(data_dir, panel.panel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2))

    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    entry = {
        "sha256": snapshot.sha256(),
        "guidelines": {g.name: g.version for g in snapshot.guidelines.values()},
        "recommendations": len(snapshot.recommendations),
    }
    previous = lock.get(panel.panel)
    notes = []
    if previous is None:
        notes.append(f"{panel.panel}: pinned {entry['recommendations']} recommendations from {entry['guidelines']}")
    elif previous["sha256"] != entry["sha256"]:
        notes.append(f"{panel.panel}: CHANGED guidelines {previous['guidelines']} -> {entry['guidelines']}; review the diff")
    if snapshot.not_in_cpic:
        notes.append(f"{panel.panel}: no CPIC entry for {', '.join(snapshot.not_in_cpic)}")

    if previous is None or previous["sha256"] != entry["sha256"]:
        lock[panel.panel] = entry
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    return snapshot, notes


def load_snapshot(data_dir: Path, panel: str) -> CpicSnapshot:
    return CpicSnapshot.model_validate_json(snapshot_path(data_dir, panel).read_text())
