"""LLM-backed explanations and prioritisation for reconciliation breaks."""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Iterable

from .models import BreakAnnotation, DividendRecord

LOGGER = logging.getLogger(__name__)

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

_VALID_SEVERITIES = {"low", "medium", "high"}

_JSON_SCHEMA = {
    "name": "reconciliation_break_annotation",
    "schema": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "description": "Operational priority: low, medium or high.",
            },
            "summary": {
                "type": "string",
                "description": "Human readable explanation (1-2 sentences).",
            },
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered remediation steps for operators or bots.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0 and 1.",
            },
            "needs_escalation": {
                "type": "boolean",
                "description": "Whether a human supervisor must approve remediation.",
            },
        },
        "required": ["severity", "summary"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration for the LLM integration."""

    model: str
    temperature: float
    api_key: str | None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        model = os.getenv("NBIM_OPENAI_MODEL", "gpt-4o-mini")
        temperature = float(os.getenv("NBIM_OPENAI_TEMPERATURE", "0.2"))
        api_key = os.getenv("NBIM_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        return cls(model=model, temperature=temperature, api_key=api_key)


def _load_openai_client(api_key: str | None):
    if not api_key:
        return None

    try:  # Import lazily so tests work without the dependency installed.
        from openai import OpenAI  # type: ignore import-not-found
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        LOGGER.warning("OpenAI Python client not installed; falling back to rule-based explanations.")
        return None

    return OpenAI(api_key=api_key)


def _serialise_record(record: DividendRecord | None) -> Dict[str, Any] | None:
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


def _compose_user_payload(reason_code: str, nbim: DividendRecord | None, custodian: DividendRecord | None) -> dict[str, Any]:
    return {
        "reason_code": reason_code,
        "nbim_record": _serialise_record(nbim),
        "custodian_record": _serialise_record(custodian),
    }


def _fallback_annotation(
    reason_code: str,
    nbim: DividendRecord | None,
    custodian: DividendRecord | None,
) -> BreakAnnotation:
    message, severity = REASON_MESSAGES.get(
        reason_code,
        ("Unexpected break detected. Escalate to the reconciliation lead.", "medium"),
    )

    account = (nbim or custodian).account if nbim or custodian else ""
    isin = (nbim or custodian).isin if nbim or custodian else ""
    explanation = f"{message} (ISIN {isin} / account {account})."
    return BreakAnnotation(explanation=explanation, severity=severity, source="rule")


class BreakAnnotationService:
    """LLM-powered agent that classifies reconciliation breaks."""

    def __init__(self, config: LLMConfig, client: Any | None) -> None:
        self._config = config
        self._client = client

    @classmethod
    def from_env(cls) -> "BreakAnnotationService":
        config = LLMConfig.from_env()
        client = _load_openai_client(config.api_key)
        return cls(config=config, client=client)

    def annotate(
        self,
        reason_code: str,
        nbim: DividendRecord | None,
        custodian: DividendRecord | None,
    ) -> BreakAnnotation:
        if self._client is None:
            return _fallback_annotation(reason_code, nbim, custodian)

        payload = _compose_user_payload(reason_code, nbim, custodian)
        messages = [
            {
                "role": "system",
                "content": "You are a senior NBIM operations analyst specialised in dividend reconciliations.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Classify and explain the reconciliation break. "
                            "Return JSON that aligns with the provided schema."
                        ),
                    },
                    {"type": "text", "text": json.dumps(payload, indent=2)},
                ],
            },
        ]

        try:
            response = self._client.responses.create(
                model=self._config.model,
                temperature=self._config.temperature,
                input=messages,
                response_format={"type": "json_schema", "json_schema": _JSON_SCHEMA},
            )
        except Exception as exc:  # pragma: no cover - network/runtime failure
            LOGGER.warning("LLM annotation failed; using rule-based fallback: %s", exc)
            return _fallback_annotation(reason_code, nbim, custodian)

        llm_payload = _extract_json_payload(response)
        if not llm_payload:
            return _fallback_annotation(reason_code, nbim, custodian)

        severity = str(llm_payload.get("severity", "")).lower()
        summary = llm_payload.get("summary")
        if severity not in _VALID_SEVERITIES or not summary:
            return _fallback_annotation(reason_code, nbim, custodian)

        actions = llm_payload.get("actions") or []
        if isinstance(actions, Iterable):
            ordered_actions = [a for a in actions if isinstance(a, str)]
        else:
            ordered_actions = []

        confidence = llm_payload.get("confidence")

        extra_segments = []
        if llm_payload.get("needs_escalation"):
            extra_segments.append("Escalate for human sign-off before auto-resolution.")

        explanation_parts = [summary, *extra_segments]
        explanation = " ".join(part.strip() for part in explanation_parts if part)
        metadata = BreakAnnotation(
            explanation=explanation,
            severity=severity,
            actions=tuple(ordered_actions),
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
            needs_escalation=bool(llm_payload.get("needs_escalation")),
            source="openai",
            raw_response=llm_payload,
        )
        return metadata


def _extract_json_payload(response: Any) -> Dict[str, Any] | None:
    """Normalise the OpenAI client response into a Python dictionary."""

    try:
        outputs = getattr(response, "output", None) or getattr(response, "outputs", None)
    except AttributeError:  # pragma: no cover - unexpected client response
        outputs = None

    if not outputs:
        # Older SDKs use `choices`
        outputs = getattr(response, "choices", None)

    if not outputs:
        return None

    # The Responses API emits a list of content blocks under `output[0].content`
    block = outputs[0]
    content = getattr(block, "content", None)
    if isinstance(content, list) and content:
        text = content[0].get("text")
    elif hasattr(block, "message") and hasattr(block.message, "content"):
        text = block.message.content[0].get("text")  # type: ignore[assignment]
    else:
        text = getattr(block, "text", None)

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        LOGGER.warning("LLM response could not be parsed as JSON. Falling back to rules.")
        return None


@lru_cache(maxsize=1)
def _service() -> BreakAnnotationService:
    return BreakAnnotationService.from_env()


def annotate_break(
    reason_code: str,
    nbim: DividendRecord | None,
    custodian: DividendRecord | None,
) -> BreakAnnotation:
    """Return an explanation, severity and metadata for a reconciliation break."""

    return _service().annotate(reason_code, nbim, custodian)
