"""Data models used by the reconciliation workflow."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, NamedTuple, Optional, Tuple


@dataclass(slots=True)
class BreakAnnotation:
    """Structured response produced by the LLM annotator."""

    explanation: str
    severity: str
    actions: Tuple[str, ...] = ()
    confidence: Optional[float] = None
    needs_escalation: bool = False
    source: str = "openai"
    raw_response: Dict[str, object] | None = None


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
    actions: Tuple[str, ...] = ()
    confidence: Optional[float] = None
    needs_escalation: bool = False
    llm_source: str = "openai"
    raw_annotation: Dict[str, object] | None = None

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
            "actions": "; ".join(self.actions),
            "confidence": f"{self.confidence:.0%}" if self.confidence is not None else "",
            "needs_escalation": "Yes" if self.needs_escalation else "No",
            "llm_source": self.llm_source,
        }

    def as_json(self) -> dict[str, object]:
        def serialise_record(record: Optional[DividendRecord]) -> dict[str, object] | None:
            if record is None:
                return None
            return {
                "source": record.source,
                "trade_id": record.trade_id,
                "isin": record.isin,
                "pay_date": record.pay_date.isoformat(),
                "account": record.account,
                "amount": float(record.amount),
                "currency": record.currency,
                "status": record.status,
            }

        return {
            "isin": self.key.isin,
            "account": self.key.account,
            "pay_date": self.key.pay_date.isoformat(),
            "nbim": serialise_record(self.nbim),
            "custodian": serialise_record(self.custodian),
            "reason_code": self.reason_code,
            "severity": self.severity,
            "explanation": self.explanation,
            "actions": list(self.actions),
            "confidence": self.confidence,
            "needs_escalation": self.needs_escalation,
            "llm_source": self.llm_source,
            "llm_payload": self.raw_annotation,
        }
