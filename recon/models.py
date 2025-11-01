"""Data models used by the reconciliation workflow."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple, Optional


class MatchKey(NamedTuple):
    isin: str
    account: str
    pay_date: date


@dataclass(slots=True)
class DividendRecord:
    source: str
    trade_id: str
    isin: str
    pay_date: date
    account: str
    amount: Decimal
    currency: str
    status: str

    def key(self) -> MatchKey:
        return MatchKey(self.isin, self.account, self.pay_date)


@dataclass(slots=True)
class BreakDetail:
    key: MatchKey
    nbim: Optional[DividendRecord]
    custodian: Optional[DividendRecord]
    reason_code: str
    explanation: str
    severity: str

    def as_dict(self) -> dict[str, str]:
        return {
            "isin": self.key.isin,
            "account": self.key.account,
            "pay_date": self.key.pay_date.isoformat(),
            "nbim_amount": f"{self.nbim.amount:.2f}" if self.nbim else "",
            "custodian_amount": f"{self.custodian.amount:.2f}" if self.custodian else "",
            "reason_code": self.reason_code,
            "severity": self.severity,
            "explanation": self.explanation,
        }
