"""Deterministic checks that classify breaks and request LLM annotations."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List

from .llm import annotate_break
from .models import BreakDetail, DividendRecord, MatchKey


def evaluate_pair(
    key: MatchKey,
    nbim: DividendRecord | None,
    custodian: DividendRecord | None,
    *,
    tolerance: float,
) -> BreakDetail | None:
    if nbim and not custodian:
        reason = "MISSING_IN_CUSTODIAN"
    elif custodian and not nbim:
        reason = "MISSING_IN_NBIM"
    elif nbim and custodian:
        if nbim.currency != custodian.currency:
            reason = "CURRENCY_MISMATCH"
        elif (nbim.amount - custodian.amount).copy_abs() > Decimal(str(tolerance)):
            reason = "AMOUNT_DIFFERENCE"
        elif nbim.status != custodian.status:
            reason = "STATUS_MISMATCH"
        else:
            return None
    else:  # pragma: no cover - defensive guard
        return None

    annotation = annotate_break(reason, nbim, custodian)
    return BreakDetail(
        key=key,
        nbim=nbim,
        custodian=custodian,
        reason_code=reason,
        explanation=annotation.explanation,
        severity=annotation.severity,
        actions=annotation.actions,
        confidence=annotation.confidence,
        needs_escalation=annotation.needs_escalation,
        llm_source=annotation.source,
        raw_annotation=annotation.raw_response,
    )


def evaluate_matches(pairs: Iterable[tuple[MatchKey, tuple[DividendRecord | None, DividendRecord | None]]], *, tolerance: float) -> list[BreakDetail]:
    breaks: List[BreakDetail] = []
    for key, (nbim, custodian) in pairs:
        detail = evaluate_pair(key, nbim, custodian, tolerance=tolerance)
        if detail:
            breaks.append(detail)
    return breaks
