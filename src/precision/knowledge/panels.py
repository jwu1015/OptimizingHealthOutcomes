"""Drug panels: the pinned set of drugs per clinical area (config/panels/*.json)."""

from __future__ import annotations

from pathlib import Path

from precision.schemas.common import Model


class PinnedDrug(Model):
    slug: str
    ingredient: str
    brand: str | None = None
    labeler: str
    setid: str  # DailyMed label we treat as the reference for this drug


class DrugPanel(Model):
    panel: str
    drugs: list[PinnedDrug]


def load_panel(path: Path) -> DrugPanel:
    return DrugPanel.model_validate_json(path.read_text())
