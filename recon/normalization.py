"""Utilities for reading and normalising source files."""
from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List

from .models import DividendRecord

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y")

EXPECTED_COLUMNS = {"trade_id", "isin", "pay_date", "account", "amount", "currency"}

NBIM_COLUMNS = {
    "COAC_EVENT_KEY",
    "ISIN",
    "PAYMENT_DATE",
    "BANK_ACCOUNT",
    "NET_AMOUNT_SETTLEMENT",
    "SETTLEMENT_CURRENCY",
}

CUSTODIAN_COLUMNS = {
    "COAC_EVENT_KEY",
    "ISIN",
    "PAY_DATE",
    "BANK_ACCOUNTS",
    "NET_AMOUNT_SC",
    "SETTLED_CURRENCY",
}


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


def _sniff_delimiter(sample: str) -> str:
    """Detect a CSV delimiter, defaulting to comma when uncertain."""

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def _transform_nbim(row: dict[str, str]) -> dict[str, str]:
    return {
        "trade_id": row["COAC_EVENT_KEY"],
        "isin": row["ISIN"],
        "pay_date": row["PAYMENT_DATE"],
        "account": row["BANK_ACCOUNT"],
        "amount": row["NET_AMOUNT_SETTLEMENT"],
        "currency": row["SETTLEMENT_CURRENCY"],
        "status": row.get("STATUS", ""),
    }


def _transform_custodian(row: dict[str, str]) -> dict[str, str]:
    return {
        "trade_id": row["COAC_EVENT_KEY"],
        "isin": row["ISIN"],
        "pay_date": row["PAY_DATE"],
        "account": row["BANK_ACCOUNTS"],
        "amount": row["NET_AMOUNT_SC"],
        "currency": row["SETTLED_CURRENCY"],
        "status": row.get("EVENT_TYPE", ""),
    }


def load_file(path: Path, *, source: str) -> List[DividendRecord]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(1024)
        handle.seek(0)
        delimiter = _sniff_delimiter(sample)
        reader = csv.DictReader(handle, delimiter=delimiter)

        if reader.fieldnames is None:
            raise NormalizationError(f"Missing expected columns in {path}")

        headers = set(reader.fieldnames)
        if EXPECTED_COLUMNS.issubset(headers):
            rows = reader
        elif NBIM_COLUMNS.issubset(headers):
            rows = (_transform_nbim(row) for row in reader)
        elif CUSTODIAN_COLUMNS.issubset(headers):
            rows = (_transform_custodian(row) for row in reader)
        else:
            raise NormalizationError(f"Missing expected columns in {path}")

        records = [normalise_row(row, source=source) for row in rows]
    return records


def load_sources(nbim_path: Path, custodian_path: Path) -> tuple[list[DividendRecord], list[DividendRecord]]:
    nbim = load_file(nbim_path, source="NBIM")
    custodian = load_file(custodian_path, source="CUSTODIAN")
    return nbim, custodian
