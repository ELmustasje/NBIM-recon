"""High-level orchestration for the reconciliation MVP."""
from __future__ import annotations

from pathlib import Path

from .checks import evaluate_matches
from .matching import match_records
from .normalization import load_sources
from .report import generate_markdown_summary, write_csv, write_json, write_markdown


def run_reconciliation(
    *,
    nbim_path: Path,
    custodian_path: Path,
    out_dir: Path,
    tolerance: float,
) -> None:
    nbim_records, custodian_records = load_sources(nbim_path, custodian_path)
    matches = match_records(nbim_records, custodian_records)
    breaks = evaluate_matches(matches.items(), tolerance=tolerance)

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "recon_breaks.csv"
    json_path = out_dir / "recon_breaks.json"
    report_path = out_dir / "recon_report.md"

    write_csv(csv_path, breaks)
    write_json(json_path, breaks)
    markdown = generate_markdown_summary(
        breaks,
        nbim_total=len(nbim_records),
        custodian_total=len(custodian_records),
    )
    write_markdown(report_path, markdown)
