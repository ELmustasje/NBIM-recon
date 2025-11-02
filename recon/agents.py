"""Agentic planning utilities for dividend reconciliation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from .llm import plan_agent_actions
from .models import BreakDetail


@dataclass(slots=True)
class AgentTask:
    """Lightweight container for a task that should be handled by an agent."""

    id: str
    agent: str
    priority: str
    objective: str
    detail: dict[str, object] = field(default_factory=dict)


def build_agent_plan(breaks: Iterable[BreakDetail]) -> list[AgentTask]:
    plans = plan_agent_actions(breaks)
    tasks: List[AgentTask] = []
    for index, plan in enumerate(plans, start=1):
        agent = str(plan.get("agent", "")).strip()
        priority = str(plan.get("priority", "")).strip().upper()
        objective = str(plan.get("objective", "")).strip()
        detail = plan.get("detail") if isinstance(plan, dict) else {}
        if not isinstance(detail, dict):
            detail = {}

        if not agent or not priority or not objective:
            continue

        tasks.append(
            AgentTask(
                id=f"TASK-{index:03d}",
                agent=agent,
                priority=priority,
                objective=objective,
                detail=detail,
            )
        )
    return tasks


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
