"""Command-line entry points: `precision <command>`."""

from __future__ import annotations

import argparse
from pathlib import Path

from precision.knowledge import cpic, dailymed
from precision.knowledge.panels import load_panel
from precision.rules import pgx
from precision.schemas import Case

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LOCK_PATH = ROOT / "config" / "labels.lock.json"
CPIC_LOCK_PATH = ROOT / "config" / "cpic.lock.json"


def _ingest_labels(args: argparse.Namespace) -> None:
    notes = dailymed.ingest_panel(Path(args.panel), DATA_DIR, LOCK_PATH)
    for note in notes:
        print(note)
    print(f"done; labels in {DATA_DIR / 'labels'}, lock at {LOCK_PATH}")


def _show_label(args: argparse.Namespace) -> None:
    label = dailymed.load_label(DATA_DIR, args.slug)
    if args.section is None:
        print(f"{label.title}\nsetid {label.setid} v{label.version} ({label.effective_date})\n")
        for s in label.sections:
            if s.title:
                print(f"{'  ' * (len(s.path) - 1)}{s.title}")
        return
    section = label.section(args.section) or next(iter(label.find(args.section)), None)
    if section is None:
        raise SystemExit(f"no section {args.section!r} in {args.slug}")
    print(" > ".join(section.path))
    print(section.text)


def _ingest_cpic(args: argparse.Namespace) -> None:
    snapshot, notes = cpic.ingest_panel(Path(args.panel), DATA_DIR, CPIC_LOCK_PATH)
    for note in notes:
        print(note)
    counts, needs_review = pgx.classification_report(snapshot)
    print("recommendation text classified as:")
    for action, n in counts.most_common():
        print(f"  {action}: {n}")
    for rec in needs_review:
        print(f"  NEEDS REVIEW [{rec.drug} {rec.lookup}]: {rec.text}")


def _pgx(args: argparse.Namespace) -> None:
    case = Case.model_validate_json(Path(args.case).read_text())
    panel = load_panel(Path(args.panel))
    snapshot = cpic.load_snapshot(DATA_DIR, panel.panel)
    tested = ", ".join(f"{p.gene} {p.diplotype} ({p.phenotype})" for p in case.patient.pgx) or "none"
    print(f"{case.patient.patient_id}: PGx results {tested}\n")
    for drug in panel.drugs:
        findings = pgx.evaluate(snapshot, case.patient, drug.slug)
        if not findings:
            print(f"{drug.slug}: no CPIC guideline\n")
            continue
        for f in findings:
            parsed = f.parsed
            limits = [
                f"start ≤{parsed.max_starting_dose_mg:g} mg" if parsed.max_starting_dose_mg else "",
                f"if used, {'<' if parsed.daily_dose_limit_exclusive else '≤'}{parsed.daily_dose_limit_mg:g} mg/day"
                if parsed.daily_dose_limit_mg
                else "",
            ]
            detail = ", ".join(x for x in limits if x)
            print(f"{drug.slug}: {parsed.action}" + (f" ({detail})" if detail else ""))
            print(f"  lookup {f.lookup}  [{f.classification}]")
            if f.not_tested:
                print(f"  not tested: {', '.join(f.not_tested)}")
            print(f"  CPIC: {f.recommendation or f.note}\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="precision")
    sub = parser.add_subparsers(required=True)

    ingest = sub.add_parser("ingest-labels", help="fetch and parse the pinned DailyMed labels for a drug panel")
    ingest.add_argument("panel", help="path to a panel config, e.g. config/panels/lipids.json")
    ingest.set_defaults(func=_ingest_labels)

    show = sub.add_parser("show-label", help="print a parsed label's outline or one section")
    show.add_argument("slug")
    show.add_argument("section", nargs="?", help='section number ("2.2") or title text ("pharmacogenomics")')
    show.set_defaults(func=_show_label)

    ingest_cpic = sub.add_parser("ingest-cpic", help="fetch and pin the CPIC recommendations for a drug panel")
    ingest_cpic.add_argument("panel", help="path to a panel config, e.g. config/panels/lipids.json")
    ingest_cpic.set_defaults(func=_ingest_cpic)

    pgx_cmd = sub.add_parser("pgx", help="CPIC findings for every drug in a panel, for one case")
    pgx_cmd.add_argument("case", help="path to a case file, e.g. fixtures/cases/synthetic-lipid-001.json")
    pgx_cmd.add_argument("panel", help="path to a panel config")
    pgx_cmd.set_defaults(func=_pgx)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
