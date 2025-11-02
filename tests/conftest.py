import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from recon import llm


@pytest.fixture(autouse=True)
def stubbed_llm_client():
    """Provide deterministic LLM outputs for tests without network access."""

    class _StubClient:
        _SEVERITY_MAP = {
            "MISSING_IN_CUSTODIAN": "high",
            "MISSING_IN_NBIM": "high",
            "CURRENCY_MISMATCH": "medium",
            "AMOUNT_DIFFERENCE": "medium",
            "STATUS_MISMATCH": "low",
        }

        _SUMMARY_MAP = {
            "MISSING_IN_CUSTODIAN": "Custodian is missing this dividend; coordinate booking.",
            "MISSING_IN_NBIM": "NBIM ledger is missing the custodian event; investigate ingestion.",
            "CURRENCY_MISMATCH": "Currency codes disagree; align static data before settlement.",
            "AMOUNT_DIFFERENCE": "Amounts differ beyond tolerance; review rate and tax setup.",
            "STATUS_MISMATCH": "Settlement statuses diverge; chase outstanding instructions.",
        }

        def request(self, *, messages, schema):  # type: ignore[override]
            payload = self._extract_payload(messages)
            schema_name = schema.get("name")
            if schema_name == "reconciliation_break_annotation":
                return self._annotation_payload(payload)
            if schema_name == "reconciliation_agent_plan":
                return self._plan_payload(payload)
            raise AssertionError(f"Unexpected schema requested: {schema_name!r}")

        def _extract_payload(self, messages):
            for block in reversed(messages):
                content = block.get("content")
                if not isinstance(content, list):
                    continue
                for item in reversed(content):
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") not in {"text", "input_text"}:
                        continue
                    try:
                        return json.loads(item.get("text", ""))
                    except json.JSONDecodeError:
                        continue
            return {}

        def _annotation_payload(self, payload):
            reason = payload.get("reason_code", "")
            severity = self._SEVERITY_MAP.get(reason, "medium")
            summary = self._SUMMARY_MAP.get(
                reason, "Investigate reconciliation data quality issues."
            )
            return {
                "severity": severity,
                "summary": summary,
                "actions": ["Review automated reconciliation output"],
                "confidence": 0.5,
                "needs_escalation": reason == "MISSING_IN_CUSTODIAN",
            }

        def _plan_payload(self, payload):
            tasks = []
            for detail in payload.get("breaks", []):
                reason = detail.get("reason_code", "UNKNOWN")
                key = detail.get("key", {})
                isin = key.get("isin", "UNKNOWN")
                tasks.append(
                    {
                        "agent": f"{reason}_AGENT",
                        "priority": detail.get("severity", "medium").upper(),
                        "objective": f"Resolve {reason} for ISIN {isin}",
                        "detail": detail,
                    }
                )
            return {"tasks": tasks}

    stub = _StubClient()
    llm.set_structured_client_for_testing(stub)
    yield
    llm.set_structured_client_for_testing(None)
