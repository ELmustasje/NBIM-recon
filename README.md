# NBIM Recon

An AI-first reconciliation toolkit that analyses dividend records, explains breaks with
the OpenAI API, and drafts an agentic remediation plan. The system is designed for
operations analysts that need auditable output and structured automation artifacts.

This document provides a full tour of the repository, the LLM integration, and how to
operate or extend the project.

## Table of contents

1. [System overview](#system-overview)
2. [Core modules](#core-modules)
3. [Data products](#data-products)
4. [Configuration](#configuration)
5. [Running the CLI](#running-the-cli)
6. [Development workflow](#development-workflow)

## System overview

The reconciliation pipeline follows four stages:

1. **Normalisation** – Source CSV files from NBIM and the custodian are standardised
   into internal `DividendRecord` objects (`recon/normalization.py`).
2. **Matching** – Records are paired on ISIN, account, and pay date to establish a
   canonical view of the holdings (`recon/matching.py`).
3. **Break detection** – Deterministic checks flag differences between each matched
   pair (`recon/checks.py`). For every break the system asks the OpenAI API to explain
   the issue and recommend actions (`recon/llm.py`).
4. **Reporting and planning** – AI-generated explanations are written to CSV/JSON and a
   Markdown summary (`recon/report.py`). The LLM also produces a structured agent task
   plan that downstream automation can consume (`recon/agents.py`).

The entire workflow is orchestrated via `recon/pipeline.py` and exposed through a CLI in
`recon/cli.py`.

## Core modules

| Module | Key entry points | Description |
| ------ | ---------------- | ----------- |
| `recon/cli.py` | `main()` | Argument parsing for the `python -m recon.cli` entry point. Dispatches to `pipeline.run_reconciliation` with CLI options. |
| `recon/pipeline.py` | `run_reconciliation()` | High-level orchestration: load data, match records, evaluate breaks, and materialise reports. |
| `recon/normalization.py` | `load_sources()` | Reads raw NBIM and custodian CSV files and builds lists of `DividendRecord` instances. |
| `recon/matching.py` | `match_records()` | Correlates dividend records by match key (ISIN, account, pay date) and produces aligned pairs. |
| `recon/checks.py` | `evaluate_pair()`<br>`evaluate_matches()` | Applies deterministic checks (missing record, currency mismatch, amount tolerance, status mismatch). Delegates every detected break to the LLM annotator. |
| `recon/models.py` | `DividendRecord`, `BreakDetail`, `BreakAnnotation` | Typed data containers shared throughout the pipeline. `BreakDetail` structures the final break metadata and is serialisable for reports. |
| `recon/llm.py` | `annotate_break()`<br>`plan_agent_actions()` | Central OpenAI integration. Requests structured JSON responses for both break explanations and the multi-agent remediation plan. Also exposes `set_structured_client_for_testing()` for offline tests. |
| `recon/agents.py` | `build_agent_plan()`<br>`write_agent_plan()` | Converts the LLM task list into numbered `AgentTask` records and writes the resulting JSON payload for orchestration platforms. |
| `recon/report.py` | `generate_markdown_summary()`<br>`write_csv()`<br>`write_json()`<br>`write_markdown()` | Rendering utilities that produce analyst-friendly artefacts in `out/`. |

Support modules include `recon/agents.py` for agent task serialisation and `recon/__init__.py`
for the package export. Tests live under `tests/` and install a stub LLM client so that the
suite can run without network access.

## Data products

Running the pipeline writes four artefacts under the configured output directory:

- `recon_breaks.csv` – Tabular view of every break with explanation, severity, actions,
  and LLM metadata.
- `recon_breaks.json` – Machine-friendly representation (including record details and raw
  annotation payloads).
- `recon_report.md` – Markdown summary that contextualises the run, including totals and
  key findings.
- `recon_agent_plan.json` – Ordered task list emitted by the LLM to drive downstream
  agents or workflow tooling.

## Configuration

All AI features require access to the OpenAI API:

- `NBIM_OPENAI_API_KEY` (preferred) or `OPENAI_API_KEY` must be set before invoking the
  CLI. Requests are issued with the `gpt-4o-mini` model by default.
- Optional environment variables:
  - `NBIM_OPENAI_MODEL` – Override the model name.
  - `NBIM_OPENAI_TEMPERATURE` – Adjust sampling temperature (float).

If the `openai` Python package is missing or an API key is not provided, the
application will raise an error. Tests replace the OpenAI client via
`set_structured_client_for_testing` so the suite remains deterministic.

## Running the CLI

```bash
NBIM_OPENAI_API_KEY="sk-..." \
PYTHONPATH=$(pwd) python -m recon.cli run \
  --nbim data/nbim_sample.csv \
  --custodian data/custodian_sample.csv \
  --out out \
  --tolerance 0.5
```

Adjust the input paths and tolerance as needed. The CLI writes the outputs listed above
and logs progress to stdout.

## Development workflow

- Python 3.12+
- Install tooling: `pip install -r requirements-dev.txt`
- Run the unit tests (which use the stub LLM client): `pytest`
- The custom coverage tracer remains available via `python tools/run_tests_with_trace.py`

See [runbook/README.md](runbook/README.md) for operational guidance, prompt management,
and risk analysis.
