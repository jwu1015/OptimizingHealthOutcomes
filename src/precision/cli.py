"""Command-line entry points: `precision <command>`."""

from __future__ import annotations

import argparse
from pathlib import Path

from precision.knowledge import dailymed

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LOCK_PATH = ROOT / "config" / "labels.lock.json"


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
