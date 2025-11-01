from datetime import date
from decimal import Decimal

from recon.matching import match_records
from recon.models import DividendRecord


def make_record(source: str, trade_id: str, isin: str, account: str, pay_date: date, amount: str) -> DividendRecord:
    return DividendRecord(
        source=source,
        trade_id=trade_id,
        isin=isin,
        account=account,
        pay_date=pay_date,
        amount=Decimal(amount),
        currency="USD",
        status="SETTLED",
    )


def test_match_records_aligns_on_key():
    nbim = [make_record("NBIM", "N1", "US1", "ACC",
                        date(2024, 3, 29), "100.00")]
    custodian = [make_record("CUST", "C1", "US1", "ACC",
                             date(2024, 3, 29), "100.00")]

    result = match_records(nbim, custodian)
    pairs = list(result.items())
    assert len(pairs) == 1
    key, (nbim_rec, cust_rec) = pairs[0]
    assert key.isin == "US1"
    assert nbim_rec.trade_id == "N1"
    assert cust_rec.trade_id == "C1"


def test_match_records_handles_missing_counterpart():
    nbim = [make_record("NBIM", "N1", "US2", "ACC",
                        date(2024, 3, 29), "100.00")]
    custodian = []

    result = match_records(nbim, custodian)
    pairs = dict(result.items())
    assert len(pairs) == 1
    (nbim_rec, cust_rec) = pairs[next(iter(pairs))]
    assert cust_rec is None
