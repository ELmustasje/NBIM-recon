"""LLM-backed break annotation utilities."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from .models import BreakDetail, DividendRecord

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BreakInsight:
    """Structured annotation returned by :func:`annotate_break`."""

    explanation: str
    severity: str
    recommendation: str
    tags: tuple[str, ...]
    confidence: float | None
    automation: str


@dataclass(slots=True)
class LLMConfig:
    """Runtime configuration for the OpenAI client."""

    api_key: str | None = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    base_url: str | None = None
    request_timeout: float | None = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        def _float(env_name: str, default: float) -> float:
            try:
                return float(os.getenv(env_name, default))
            except ValueError:
                return default

        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("RECON_LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            temperature=_float("RECON_LLM_TEMPERATURE", 0.1),
            base_url=os.getenv("OPENAI_BASE_URL"),
            request_timeout=_float("RECON_LLM_TIMEOUT", 30.0),
        )


FALLBACK_LIBRARY: dict[str, BreakInsight] = {
    "MISSING_IN_CUSTODIAN": BreakInsight(
        explanation="Custodian is missing this dividend. Confirm whether the position was reported late.",
        severity="high",
        recommendation="Contact the custodian to confirm if the position was reported late and request a catch-up booking.",
        tags=("break-detection", "investigate-custodian"),
        confidence=0.4,
        automation="human-review",
    ),
    "MISSING_IN_NBIM": BreakInsight(
        explanation="NBIM ledger is missing the custodian event. Check ingestion and booking status.",
        severity="high",
        recommendation="Review inbound interfaces for the asset and trigger a manual booking if the feed failed.",
        tags=("booking", "data-ingestion"),
        confidence=0.4,
        automation="human-review",
    ),
    "CURRENCY_MISMATCH": BreakInsight(
        explanation="Currency codes disagree. Validate security static data and FX configuration.",
        severity="medium",
        recommendation="Verify the security master currency and FX override rules, then rebalance the amounts.",
        tags=("static-data", "fx"),
        confidence=0.5,
        automation="assisted",
    ),
    "AMOUNT_DIFFERENCE": BreakInsight(
        explanation="Amounts differ beyond tolerance. Review rate sources and withholding tax setup.",
        severity="medium",
        recommendation="Compare dividend rate sources, withholding settings, and adjust for corporate action fees if required.",
        tags=("rates", "withholding"),
        confidence=0.5,
        automation="assisted",
    ),
    "STATUS_MISMATCH": BreakInsight(
        explanation="Settlement statuses diverge. Follow up with operations for latest instructions.",
        severity="low",
        recommendation="Request latest settlement status from the custodian and update NBIM workflow notes.",
        tags=("settlement", "workflow"),
        confidence=0.6,
        automation="assistive-monitoring",
    ),
}

DEFAULT_INSIGHT = BreakInsight(
    explanation="Unexpected break detected. Escalate to the reconciliation lead.",
    severity="medium",
    recommendation="Escalate to the on-call reconciliation lead for triage.",
    tags=("unknown",),
    confidence=0.3,
    automation="human-review",
)


class BreakAdvisor:
    """Wrapper around OpenAI's API with graceful fallbacks."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()
        self._client = None

        if self.config.api_key:
            try:  # pragma: no cover - exercised only when OpenAI is installed
                from openai import OpenAI
            except Exception as exc:  # pragma: no cover - import error path
                LOGGER.warning("OpenAI client unavailable, using rule-based fallback: %s", exc)
            else:  # pragma: no cover - depends on external package
                kwargs = {"api_key": self.config.api_key}
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                if self.config.request_timeout:
                    kwargs["timeout"] = self.config.request_timeout
                self._client = OpenAI(**kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enabled(self) -> bool:
        return self._client is not None

    def annotate_break(
        self,
        reason_code: str,
        nbim: DividendRecord | None,
        custodian: DividendRecord | None,
    ) -> BreakInsight:
        if not self.enabled():
            return _fallback_annotation(reason_code)

        payload = self._build_payload(reason_code, nbim, custodian)
        try:  # pragma: no cover - requires live API
            completion = self._client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior dividend-operations analyst. "
                            "Classify reconciliation breaks, summarise the likely root cause, "
                            "and propose the next operational step. Return JSON with the keys: "
                            "severity (high|medium|low), explanation, recommendation, tags (array of short "
                            "strings), confidence (0-1 float) and automation (autopilot|assisted|human-review)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, indent=2),
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on API/network
            LOGGER.warning("LLM annotation failed, using fallback: %s", exc)
            return _fallback_annotation(reason_code)

        try:  # pragma: no cover - depends on API response
            message = completion.choices[0].message.content or ""
            parsed = json.loads(message)
        except (IndexError, AttributeError, json.JSONDecodeError) as exc:
            LOGGER.warning("LLM annotation returned invalid JSON, using fallback: %s", exc)
            return _fallback_annotation(reason_code)

        return _parse_llm_payload(reason_code, parsed)

    def summarize_breaks(self, breaks: Iterable[BreakDetail]) -> str:
        breaks = list(breaks)
        if not breaks:
            return "# LLM Operational Brief\n\nNo breaks detected."

        if not self.enabled():
            lines = ["# LLM Operational Brief", ""]
            lines.append("LLM integration is disabled. Displaying deterministic snapshot instead.")
            lines.append("")
            severity_buckets: dict[str, int] = {}
            for detail in breaks:
                severity_buckets[detail.severity] = severity_buckets.get(detail.severity, 0) + 1
            lines.append("## Severity counts")
            for severity, count in sorted(severity_buckets.items()):
                lines.append(f"- {severity.title()}: {count}")
            lines.append("")
            lines.append("## Immediate actions")
            for detail in breaks:
                next_step = detail.recommendation or "Review break manually."
                lines.append(f"- {detail.key.isin} / {detail.key.account}: {next_step}")
            lines.append("")
            lines.append("Enable OPENAI_API_KEY to receive richer narratives and automation insights.")
            return "\n".join(lines)

        prompt_payload = [detail.as_dict() for detail in breaks]
        try:  # pragma: no cover - requires live API
            completion = self._client.chat.completions.create(
                model=self.config.model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an operations chief of staff. Review the dividend reconciliation breaks "
                            "and produce a concise action brief with triage ordering, risk commentary, and "
                            "automation opportunities."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt_payload, indent=2),
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on API/network
            LOGGER.warning("LLM summary failed: %s", exc)
            return "# LLM Operational Brief\n\nUnable to generate LLM summary. See logs for details."

        try:  # pragma: no cover - depends on API response
            return completion.choices[0].message.content.strip()
        except (IndexError, AttributeError):
            return "# LLM Operational Brief\n\nSummary unavailable due to malformed response."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_payload(
        self,
        reason_code: str,
        nbim: DividendRecord | None,
        custodian: DividendRecord | None,
    ) -> dict[str, Any]:
        def _serialize(record: DividendRecord | None) -> dict[str, Any] | None:
            if not record:
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
            "reason_code": reason_code,
            "nbim_record": _serialize(nbim),
            "custodian_record": _serialize(custodian),
        }


def _parse_llm_payload(reason_code: str, payload: dict[str, Any]) -> BreakInsight:
    severity = str(payload.get("severity", "")).strip().lower() or _fallback_annotation(reason_code).severity
    if severity not in {"high", "medium", "low"}:
        severity = _fallback_annotation(reason_code).severity

    recommendation = str(payload.get("recommendation", "")).strip()
    if not recommendation:
        recommendation = _fallback_annotation(reason_code).recommendation

    explanation = str(payload.get("explanation", "")).strip()
    if not explanation:
        explanation = _fallback_annotation(reason_code).explanation

    raw_tags = payload.get("tags", [])
    tags: tuple[str, ...] = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
    if not tags:
        tags = _fallback_annotation(reason_code).tags

    confidence_val = payload.get("confidence")
    confidence: float | None
    try:
        confidence = float(confidence_val)
    except (TypeError, ValueError):
        confidence = _fallback_annotation(reason_code).confidence

    automation = str(payload.get("automation", "")).strip().lower()
    if not automation:
        automation = _fallback_annotation(reason_code).automation

    return BreakInsight(
        explanation=explanation,
        severity=severity,
        recommendation=recommendation,
        tags=tags,
        confidence=confidence,
        automation=automation,
    )


@lru_cache(maxsize=1)
def get_advisor() -> BreakAdvisor:
    return BreakAdvisor()


def _fallback_annotation(reason_code: str) -> BreakInsight:
    return FALLBACK_LIBRARY.get(reason_code, DEFAULT_INSIGHT)


def annotate_break(
    reason_code: str,
    nbim: DividendRecord | None,
    custodian: DividendRecord | None,
) -> BreakInsight:
    """Return an explanation, severity and action plan for the supplied break."""

    advisor = get_advisor()
    return advisor.annotate_break(reason_code, nbim, custodian)
