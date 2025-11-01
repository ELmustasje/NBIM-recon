from decimal import Decimal
from pathlib import Path

import pytest

from recon import normalization
from recon.models import DividendRecord


def test_parse_date_handles_multiple_formats():
    assert normalization.parse_date("2024-03-29").isoformat() == "2024-03-29"
    assert normalization.parse_date("29/03/2024").isoformat() == "2024-03-29"


def test_parse_amount_quantises_to_cents():
    amount = normalization.parse_amount("1,234.567")
    assert amount == Decimal("1234.57")


def test_load_file_round_trips_sample(tmp_path: Path):
    content = """trade_id,isin,pay_date,account,amount,currency,status\nT1,US1,2024-03-29,ACC,100.1,USD,Settled\n"""
    path = tmp_path / "sample.csv"
    path.write_text(content)

    records = normalization.load_file(path, source="TEST")
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, DividendRecord)
    assert record.source == "TEST"
    assert record.amount == Decimal("100.10")
    assert record.status == "SETTLED"


def test_load_file_requires_expected_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("trade_id,isin\n1,US1\n")

    with pytest.raises(normalization.NormalizationError):
        normalization.load_file(path, source="TEST")
