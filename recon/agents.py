"""Agentic planning utilities for dividend reconciliation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from .models import BreakDetail


REASON_AGENT_MAP = {
    "MISSING_IN_CUSTODIAN": (
        "CustodyLiaisonAgent",
        "Request status update from custodian and reconcile holdings",
    ),
    "MISSING_IN_NBIM": (
        "LedgerIngestionAgent",
        "Investigate NBIM booking pipeline and ingest late files",
    ),
    "CURRENCY_MISMATCH": (
        "StaticDataAgent",
        "Check security master and FX configuration",
    ),
    "AMOUNT_DIFFERENCE": (
        "CashAllocatorAgent",
        "Recalculate dividend rate and withholding tax",
    ),
    "STATUS_MISMATCH": (
        "SettlementChaserAgent",
        "Align settlement status between parties",
    ),
}


@dataclass(slots=True)
class AgentTask:
    """Lightweight container for a task that should be handled by an agent."""

    id: str
    agent: str
    priority: str
    objective: str
    detail: dict[str, object] = field(default_factory=dict)


class ControlTower:
    """Plans tasks for specialist agents based on break metadata."""

    def __init__(self) -> None:
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"TASK-{self._counter:03d}"

    def plan_tasks(self, breaks: Iterable[BreakDetail]) -> list[AgentTask]:
        tasks: List[AgentTask] = []
        for detail in breaks:
            agent_name, objective = REASON_AGENT_MAP.get(
                detail.reason_code,
                ("OpsControlAgent", "Triage unexpected reconciliation scenario"),
            )
            priority = detail.severity.upper()
            if detail.needs_escalation:
                priority = "CRITICAL"
            tasks.append(
                AgentTask(
                    id=self._next_id(),
                    agent=agent_name,
                    priority=priority,
                    objective=objective,
                    detail={
                        "isin": detail.key.isin,
                        "account": detail.key.account,
                        "pay_date": detail.key.pay_date.isoformat(),
                        "severity": detail.severity,
                        "needs_escalation": detail.needs_escalation,
                        "actions": list(detail.actions),
                        "confidence": detail.confidence,
                        "llm_source": detail.llm_source,
                        "reason_code": detail.reason_code,
                    },
                )
            )
        return tasks


def build_agent_plan(breaks: Iterable[BreakDetail]) -> list[AgentTask]:
    return ControlTower().plan_tasks(breaks)


def write_agent_plan(path: Path, breaks: Iterable[BreakDetail]) -> None:
    import json

    tasks = build_agent_plan(breaks)
    payload = [
        {
            "id": task.id,
            "agent": task.agent,
            "priority": task.priority,
            "objective": task.objective,
            "detail": task.detail,
        }
        for task in tasks
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
