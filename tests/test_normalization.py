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


def test_load_file_transforms_nbim_schema(tmp_path: Path):
    content = (
        "COAC_EVENT_KEY;ISIN;PAYMENT_DATE;BANK_ACCOUNT;NET_AMOUNT_SETTLEMENT;SETTLEMENT_CURRENCY\n"
        "N1;US1111111111;07.02.2025;12345;1234.56;USD\n"
    )
    path = tmp_path / "nbim.csv"
    path.write_text("\ufeff" + content, encoding="utf-8")

    records = normalization.load_file(path, source="NBIM")
    assert len(records) == 1
    record = records[0]
    assert record.trade_id == "N1"
    assert record.isin == "US1111111111"
    assert record.account == "12345"
    assert record.amount == Decimal("1234.56")
    assert record.currency == "USD"
    assert record.pay_date.isoformat() == "2025-02-07"
    assert record.status == ""


def test_load_file_transforms_custodian_schema(tmp_path: Path):
    content = (
        "COAC_EVENT_KEY;ISIN;PAY_DATE;BANK_ACCOUNTS;NET_AMOUNT_SC;SETTLED_CURRENCY;EVENT_TYPE\n"
        "C1;US2222222222;08.02.2025;54321;2000;EUR;SETTLED\n"
    )
    path = tmp_path / "cust.csv"
    path.write_text(content)

    records = normalization.load_file(path, source="CUSTODIAN")
    assert len(records) == 1
    record = records[0]
    assert record.trade_id == "C1"
    assert record.isin == "US2222222222"
    assert record.account == "54321"
    assert record.amount == Decimal("2000.00")
    assert record.currency == "EUR"
    assert record.pay_date.isoformat() == "2025-02-08"
    assert record.status == "SETTLED"
