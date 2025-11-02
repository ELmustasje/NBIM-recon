"""LLM-backed explanations and planning for reconciliation breaks."""
from __future__ import annotations
from .models import BreakAnnotation, BreakDetail, DividendRecord

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Dict, Iterable, Protocol
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


LOGGER = logging.getLogger(__name__)


class StructuredResponseClient(Protocol):
    """Protocol representing a client capable of returning structured JSON."""

    def request(
        self, *, messages: list[dict[str, Any]], schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an LLM call and return the parsed JSON payload."""


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
        api_key = os.getenv("NBIM_OPENAI_API_KEY") or os.getenv(
            "OPENAI_API_KEY")
        return cls(model=model, temperature=temperature, api_key=api_key)


class OpenAIStructuredClient:
    """Adapter that issues structured responses via the OpenAI SDK."""

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            raise RuntimeError(
                "NBIM_OPENAI_API_KEY (or OPENAI_API_KEY) must be set for LLM features."
            )

        try:  # Import lazily so tests work without the dependency installed.
            from openai import OpenAI  # type: ignore import-not-found
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "OpenAI Python client is not installed; install `openai` to continue."
            ) from exc

        self._client = OpenAI(api_key=config.api_key)
        self._model = config.model
        self._temperature = config.temperature

    def request(
        self, *, messages: list[dict[str, Any]], schema: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            response = self._client.responses.create(  # type: ignore[attr-defined]
                model=self._model,
                temperature=self._temperature,
                input=messages,
                response_format={"type": "json_schema", "json_schema": schema},
            )
        except Exception as exc:  # pragma: no cover - network/runtime failure
            raise RuntimeError("OpenAI response generation failed") from exc

        payload = _extract_json_payload(response)
        if payload is None:
            raise RuntimeError(
                "OpenAI response did not include structured JSON payload")
        return payload


_CUSTOM_CLIENT: StructuredResponseClient | None = None
_CLIENT_INSTANCE: StructuredResponseClient | None = None


def set_structured_client_for_testing(client: StructuredResponseClient | None) -> None:
    """Install a fake client so tests can bypass the OpenAI dependency."""

    global _CUSTOM_CLIENT, _CLIENT_INSTANCE
    _CUSTOM_CLIENT = client
    _CLIENT_INSTANCE = None


def _client() -> StructuredResponseClient:
    global _CLIENT_INSTANCE

    if _CUSTOM_CLIENT is not None:
        return _CUSTOM_CLIENT

    if _CLIENT_INSTANCE is None:
        config = LLMConfig.from_env()
        _CLIENT_INSTANCE = OpenAIStructuredClient(config)

    return _CLIENT_INSTANCE


_VALID_SEVERITIES = {"low", "medium", "high"}

_ANNOTATION_SCHEMA = {
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

_AGENT_PLAN_SCHEMA = {
    "name": "reconciliation_agent_plan",
    "schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "string"},
                        "priority": {"type": "string"},
                        "objective": {"type": "string"},
                        "detail": {"type": "object"},
                    },
                    "required": ["agent", "priority", "objective", "detail"],
                    "additionalProperties": True,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    },
}


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


def _serialise_break(detail: BreakDetail) -> dict[str, Any]:
    return {
        "reason_code": detail.reason_code,
        "severity": detail.severity,
        "needs_escalation": detail.needs_escalation,
        "explanation": detail.explanation,
        "actions": list(detail.actions),
        "key": {
            "isin": detail.key.isin,
            "account": detail.key.account,
            "pay_date": detail.key.pay_date.isoformat(),
        },
        "nbim_record": _serialise_record(detail.nbim),
        "custodian_record": _serialise_record(detail.custodian),
    }


def _compose_annotation_messages(
    reason_code: str, nbim: DividendRecord | None, custodian: DividendRecord | None
) -> list[dict[str, Any]]:
    payload = {
        "reason_code": reason_code,
        "nbim_record": _serialise_record(nbim),
        "custodian_record": _serialise_record(custodian),
    }
    return [
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


def _compose_plan_messages(breaks: Iterable[BreakDetail]) -> list[dict[str, Any]]:
    payload = {"breaks": [_serialise_break(detail) for detail in breaks]}
    return [
        {
            "role": "system",
            "content": (
                "You are the NBIM reconciliation control tower. "
                "Design specialist agent tasks that remediate the breaks."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Create a task list for execution. "
                        "Each task must specify the agent best positioned to act, an operations-ready objective, "
                        "and a priority consistent with the provided severity. "
                        "Use the schema to emit valid JSON."
                    ),
                },
                {"type": "text", "text": json.dumps(payload, indent=2)},
            ],
        },
    ]


def _request_payload(messages: list[dict[str, Any]], schema: dict[str, Any]) -> dict[str, Any]:
    client = _client()
    LOGGER.debug(
        "Submitting structured LLM request using schema %s", schema.get("name"))
    return client.request(messages=messages, schema=schema)


def annotate_break(
    reason_code: str,
    nbim: DividendRecord | None,
    custodian: DividendRecord | None,
) -> BreakAnnotation:
    """Return an explanation, severity and metadata for a reconciliation break."""

    messages = _compose_annotation_messages(reason_code, nbim, custodian)
    payload = _request_payload(messages, _ANNOTATION_SCHEMA)

    severity = str(payload.get("severity", "")).lower()
    summary = str(payload.get("summary", "")).strip()
    if severity not in _VALID_SEVERITIES:
        raise RuntimeError(f"Invalid severity returned by LLM: {severity!r}")
    if not summary:
        raise RuntimeError("LLM annotation did not include a summary")

    actions_field = payload.get("actions") or []
    actions: tuple[str, ...]
    if isinstance(actions_field, Iterable):
        actions = tuple(str(item).strip()
                        for item in actions_field if str(item).strip())
    else:
        actions = ()

    confidence_value = payload.get("confidence")
    confidence = (
        float(confidence_value)
        if isinstance(confidence_value, (int, float))
        else None
    )

    needs_escalation = bool(payload.get("needs_escalation"))
    explanation = summary
    if needs_escalation:
        explanation = f"{
            summary} Escalate for human sign-off before auto-resolution."

    return BreakAnnotation(
        explanation=explanation,
        severity=severity,
        actions=actions,
        confidence=confidence,
        needs_escalation=needs_escalation,
        source="openai",
        raw_response=payload,
    )


def plan_agent_actions(breaks: Iterable[BreakDetail]) -> list[dict[str, Any]]:
    """Use the LLM to design a task list for the control tower."""

    break_list = list(breaks)
    if not break_list:
        return []

    messages = _compose_plan_messages(break_list)
    payload = _request_payload(messages, _AGENT_PLAN_SCHEMA)

    tasks_payload = payload.get("tasks", [])
    if not isinstance(tasks_payload, list):
        raise RuntimeError(
            "LLM agent plan response did not include a task list")

    normalised_tasks: list[dict[str, Any]] = []
    for raw_task in tasks_payload:
        if not isinstance(raw_task, dict):
            continue
        agent = str(raw_task.get("agent", "")).strip()
        objective = str(raw_task.get("objective", "")).strip()
        priority = str(raw_task.get("priority", "")).strip()
        detail = raw_task.get("detail")
        if not isinstance(detail, dict):
            detail = {}

        if not agent or not objective or not priority:
            continue

        normalised_tasks.append(
            {
                "agent": agent,
                "objective": objective,
                "priority": priority,
                "detail": detail,
            }
        )

    if not normalised_tasks:
        raise RuntimeError(
            "LLM agent plan response did not contain any usable tasks")

    return normalised_tasks


def _extract_json_payload(response: Any) -> Dict[str, Any] | None:
    """Normalise the OpenAI client response into a Python dictionary."""

    try:
        outputs = getattr(response, "output", None) or getattr(
            response, "outputs", None)
    except AttributeError:  # pragma: no cover - unexpected client response
        outputs = None

    if not outputs:
        # Older SDKs use `choices`
        outputs = getattr(response, "choices", None)

    if not outputs:
        return None

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
        LOGGER.warning("LLM response could not be parsed as JSON.")
        return None
