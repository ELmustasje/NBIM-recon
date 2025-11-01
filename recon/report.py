"""Rendering utilities for machine-readable and human-readable outputs."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import BreakDetail


def write_csv(path: Path, breaks: Iterable[BreakDetail]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "isin",
                "account",
                "pay_date",
                "nbim_amount",
                "custodian_amount",
                "reason_code",
                "severity",
                "explanation",
            ],
        )
        writer.writeheader()
        for detail in breaks:
            writer.writerow(detail.as_dict())


def write_json(path: Path, breaks: Iterable[BreakDetail]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [detail.as_dict() for detail in breaks]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def generate_markdown_summary(
    breaks: list[BreakDetail],
    *,
    nbim_total: int,
    custodian_total: int,
) -> str:
    counter = Counter(detail.reason_code for detail in breaks)
    severities = Counter(detail.severity for detail in breaks)

    lines = ["# Dividend Reconciliation Report", ""]
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- NBIM records processed: **{nbim_total}**")
    lines.append(f"- Custodian records processed: **{custodian_total}**")
    lines.append(f"- Breaks detected: **{len(breaks)}**")
    lines.append("")

    if counter:
        lines.append("## Breaks by reason code")
        lines.append("")
        for reason, count in sorted(counter.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("")

    if severities:
        lines.append("## Severity distribution")
        lines.append("")
        for severity, count in sorted(severities.items()):
            lines.append(f"- {severity.title()}: {count}")
        lines.append("")

    if breaks:
        lines.append("## Detailed explanations")
        lines.append("")
        lines.append(
            "| ISIN | Account | Pay date | Reason | Severity | Explanation |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for detail in breaks:
            lines.append(
                "| {isin} | {account} | {date} | {reason} | {severity} | {explanation} |".format(
                    isin=detail.key.isin,
                    account=detail.key.account,
                    date=detail.key.pay_date.isoformat(),
                    reason=detail.reason_code,
                    severity=detail.severity.title(),
                    explanation=detail.explanation.replace("|", "\\|"),
                )
            )
        lines.append("")
    else:
        lines.append("No breaks detected. All deterministic checks passed.")

    return "\n".join(lines)


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)
