"""Utilities for reading and normalising source files."""
from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List

from .models import DividendRecord

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


class NormalizationError(RuntimeError):
    """Raised when a record cannot be normalised."""


def parse_date(raw: str) -> datetime.date:
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), pattern).date()
        except ValueError:
            continue
    raise NormalizationError(f"Unrecognised date format: {raw}")


def parse_amount(raw: str) -> Decimal:
    normalized = raw.replace(",", "").strip()
    try:
        return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as exc:  # pragma: no cover - Decimal raises multiple subclasses
        raise NormalizationError(f"Invalid amount: {raw}") from exc


def normalise_row(row: dict[str, str], *, source: str) -> DividendRecord:
    return DividendRecord(
        source=source,
        trade_id=row["trade_id"].strip(),
        isin=row["isin"].strip(),
        pay_date=parse_date(row["pay_date"]),
        account=row["account"].strip(),
        amount=parse_amount(row["amount"]),
        currency=row["currency"].strip().upper(),
        status=row.get("status", "").strip().upper(),
    )


def load_file(path: Path, *, source: str) -> List[DividendRecord]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = {"trade_id", "isin", "pay_date",
                    "account", "amount", "currency"}
        if reader.fieldnames is None or not expected.issubset(reader.fieldnames):
            raise NormalizationError(f"Missing expected columns in {path}")

        records = [normalise_row(row, source=source) for row in reader]
    return records


def load_sources(nbim_path: Path, custodian_path: Path) -> tuple[list[DividendRecord], list[DividendRecord]]:
    nbim = load_file(nbim_path, source="NBIM")
    custodian = load_file(custodian_path, source="CUSTODIAN")
    return nbim, custodian
