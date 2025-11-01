from datetime import date
from decimal import Decimal

from recon.checks import evaluate_matches, evaluate_pair
from recon.models import DividendRecord, MatchKey


def make_record(amount: str, *, currency: str = "USD", status: str = "SETTLED") -> DividendRecord:
    return DividendRecord(
        source="SRC",
        trade_id="T1",
        isin="US1",
        account="ACC",
        pay_date=date(2024, 3, 29),
        amount=Decimal(amount),
        currency=currency,
        status=status,
    )


def test_evaluate_pair_identifies_amount_break():
    key = MatchKey("US1", "ACC", date(2024, 3, 29))
    nbim = make_record("100.00")
    cust = make_record("101.00")

    detail = evaluate_pair(key, nbim, cust, tolerance=0.5)
    assert detail is not None
    assert detail.reason_code == "AMOUNT_DIFFERENCE"
    assert "Amounts differ" in detail.explanation


def test_evaluate_pair_accepts_within_tolerance():
    key = MatchKey("US1", "ACC", date(2024, 3, 29))
    nbim = make_record("100.00")
    cust = make_record("100.20")

    detail = evaluate_pair(key, nbim, cust, tolerance=0.5)
    assert detail is None


def test_evaluate_matches_collects_multiple_breaks():
    key = MatchKey("US1", "ACC", date(2024, 3, 29))
    nbim = make_record("100.00")
    breaks = evaluate_matches([(key, (nbim, None))], tolerance=0.5)
    assert len(breaks) == 1
    assert breaks[0].reason_code == "MISSING_IN_CUSTODIAN"
