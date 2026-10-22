# OptimizingHealthOutcomes

The software for **Precision Clinic**: the protocol engine, data pipelines, backend and frontend. The concept, patient journey, data spec and engine design live in Notion (Precision Clinic, pages 01–06); this repo implements them.

## Current scope

We're building the Protocol Engine end to end for **one clinical area, ApoB / lipids**, to produce protocols for the blind 10-case comparison (06 · Open Questions, #4). The clinic platform (patient app, physician queue, HIPAA hosting) waits on the practice-structure decisions.

| Piece | Status |
| --- | --- |
| Schemas: patient record, problem/target lists, evidence claims, protocol | done (`src/precision/schemas`) |
| Evidence gates: verbatim quote + number checks | done (`src/precision/evidence/gates.py`) |
| DailyMed label pipeline for the lipid panel | done (`src/precision/knowledge/dailymed.py`) |
| CPIC pipeline + PGx rules (genotype → standard / max starting dose / prefer alternative) | done (`src/precision/knowledge/cpic.py`, `src/precision/rules/pgx.py`) |
| Structured extraction from labels (dose ranges, contraindications, interactions) | next |
| Drugs@FDA, DrugCentral | next |
| Literature pipeline (PubMed, PubTator3, ClinicalTrials.gov) + grading | later |
| Engine core: targets → candidates → filters → dose → monitoring → protocol | later |
| Blind comparison UI (`frontend/`) | later |

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Commands

```sh
precision ingest-labels config/panels/lipids.json   # fetch + parse the pinned DailyMed labels
precision show-label rosuvastatin                   # outline of a parsed label
precision show-label rosuvastatin 2.2               # one section by number
precision show-label rosuvastatin pharmacogenomics  # or by title

precision ingest-cpic config/panels/lipids.json     # fetch + pin CPIC recommendations for the panel
precision pgx fixtures/cases/synthetic-lipid-001.json config/panels/lipids.json  # PGx findings per drug
```

Downloaded and parsed data goes to `data/` (gitignored, regenerable). `config/labels.lock.json` and `config/cpic.lock.json` record the version and checksum of every label and CPIC guideline we've ingested. If either changes upstream, the ingest prints `CHANGED` and the lock file diff shows it in review.

### How PGx rules work

1. Each gene in the CPIC guideline is looked up from the patient's **tier-A** results. A gene with no result is looked up as CPIC's own `"No Result"`. An untested gene is never treated as normal.
2. The matching CPIC recommendation is classified into an action: `standard`, `standard_with_caution`, `max_starting_dose` (with the mg cap), `prefer_alternative` (with any daily limit), or `no_recommendation`.
3. Anything that doesn't match, whether unrecognised wording, a genotype with no CPIC row, or an unfamiliar phenotype term, becomes `needs_review`. The physician then sees the CPIC text verbatim. Nothing is guessed. `ingest-cpic` reports how every row classified.

## Layout

```
config/panels/       pinned drug panels (one DailyMed setid per drug, originator label)
config/labels.lock.json
fixtures/cases/      synthetic patient cases (never real patient data)
src/precision/
  schemas/           typed data contracts, FHIR-shaped
  evidence/gates.py  deterministic quote + number gates
  knowledge/         drug knowledge pipelines (DailyMed labels, CPIC guidelines)
  rules/             deterministic rules over knowledge + patient (PGx first)
  cli.py
tests/
frontend/            not started
```

## Rules the code enforces

These come from 01 · Thesis and 04 · Protocol Engine. They are schema validation, so a protocol that breaks them can't be constructed:

- A protocol item's primary evidence must be **grade A or B** and must have **passed the quote gates**.
- A prescription item needs a **dose with its label basis** and **a monitored marker with an action threshold**.
- Predicted trajectories are always labelled **modeled**.
- Targets come from the physician-confirmed list. The engine plans against them and never sets them.
- A signed protocol must record who signed it and when.

## Patient data

**No real patient data in this repo or on dev machines.** Use synthetic cases in `fixtures/cases/`. Real cases for the blind test need de-identification or HIPAA-covered infrastructure first.
