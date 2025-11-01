"""Rule-based stand-in for an LLM explanation service."""
from __future__ import annotations

from .models import DividendRecord

REASON_MESSAGES = {
    "MISSING_IN_CUSTODIAN": (
        "Custodian is missing this dividend. Confirm whether the position was reported late.",
        "high",
    ),
    "MISSING_IN_NBIM": (
        "NBIM ledger is missing the custodian event. Check ingestion and booking status.",
        "high",
    ),
    "CURRENCY_MISMATCH": (
        "Currency codes disagree. Validate security static data and FX configuration.",
        "medium",
    ),
    "AMOUNT_DIFFERENCE": (
        "Amounts differ beyond tolerance. Review rate sources and withholding tax setup.",
        "medium",
    ),
    "STATUS_MISMATCH": (
        "Settlement statuses diverge. Follow up with operations for latest instructions.",
        "low",
    ),
}


def annotate_break(reason_code: str, nbim: DividendRecord | None, custodian: DividendRecord | None) -> tuple[str, str]:
    message, severity = REASON_MESSAGES.get(
        reason_code,
        ("Unexpected break detected. Escalate to the reconciliation lead.", "medium"),
    )

    account = (nbim or custodian).account if nbim or custodian else ""
    isin = (nbim or custodian).isin if nbim or custodian else ""
    explanation = f"{message} (ISIN {isin} / account {account})."
    return explanation, severity
