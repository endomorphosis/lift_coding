"""Legacy compatibility facade for agent providers.

Runtime code should use ``handsfree.agent_providers`` and ``handsfree.agents.service``.
This module keeps older imports working while delegating provider ownership to the
canonical registry where possible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from handsfree.agent_providers import (
    CopilotAgentProvider as _CopilotAgentProvider,
    CustomAgentProvider as _CustomAgentProvider,
    get_provider as _get_canonical_provider,
)
from handsfree.db.agent_tasks import AgentTask


@dataclass
class AgentInvocationResult:
    """Result of an agent invocation attempt."""

    success: bool
    message: str
    trace: dict[str, Any] | None = None


class AgentProvider(ABC):
    """Compatibility interface for older provider imports."""

    @abstractmethod
    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        """Invoke the agent with a task."""

    @abstractmethod
    def get_status(self, task_id: str) -> dict[str, Any]:
        """Get status of a task."""


def _build_task(
    provider_name: str,
    task_id: str,
    instruction: str | None,
    target_type: str | None,
    target_ref: str | None,
) -> AgentTask:
    now = datetime.now(UTC)
    return AgentTask(
        id=task_id,
        user_id="legacy-compat",
        provider=provider_name,
        target_type=target_type,
        target_ref=target_ref,
        instruction=instruction,
        state="created",
        trace=None,
        created_at=now,
        updated_at=now,
    )


class _CanonicalProviderAdapter(AgentProvider):
    """Adapt canonical provider lifecycle hooks to the older invoke/status API."""

    provider_name = ""

    def __init__(self, provider_name: str | None = None) -> None:
        self.provider_name = provider_name or self.provider_name
        self._provider = _get_canonical_provider(self.provider_name)

    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        result = self._provider.start_task(
            _build_task(self.provider_name, task_id, instruction, target_type, target_ref)
        )
        return AgentInvocationResult(
            success=bool(result.get("ok")),
            message=result.get("message", ""),
            trace=result.get("trace"),
        )

    def get_status(self, task_id: str) -> dict[str, Any]:
        task = _build_task(self.provider_name, task_id, None, None, None)
        task.state = "running"
        return self._provider.check_status(task)


class CopilotProvider(_CanonicalProviderAdapter):
    """Compatibility wrapper for the canonical Copilot provider."""

    provider_name = "copilot"

    def __init__(self) -> None:
        self._provider = _CopilotAgentProvider()


class CustomProvider(_CanonicalProviderAdapter):
    """Compatibility wrapper for the canonical custom provider."""

    provider_name = "custom"

    def __init__(self) -> None:
        self._provider = _CustomAgentProvider()


class MockAgentRunner:
    """Deterministic compatibility runner retained for legacy tests."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def register_task(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> None:
        self._tasks[task_id] = {
            "instruction": instruction,
            "target_type": target_type,
            "target_ref": target_ref,
            "state": "registered",
            "steps": [],
        }

    def advance_task(
        self,
        task_id: str,
        new_state: str,
        step_info: dict[str, Any] | None = None,
    ) -> bool:
        if task_id not in self._tasks:
            return False

        self._tasks[task_id]["state"] = new_state
        if step_info:
            self._tasks[task_id]["steps"].append(step_info)
        return True

    def get_task_info(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)

    def clear(self) -> None:
        self._tasks.clear()


_mock_runner = MockAgentRunner()


def get_mock_runner() -> MockAgentRunner:
    """Get the legacy compatibility mock runner."""
    return _mock_runner


class MockProvider(AgentProvider):
    """Compatibility mock provider backed by the legacy mock runner."""

    def __init__(self, runner: MockAgentRunner | None = None) -> None:
        self.runner = runner or get_mock_runner()

    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        self.runner.register_task(task_id, instruction, target_type, target_ref)
        return AgentInvocationResult(
            success=True,
            message="Task registered with mock runner",
            trace={"provider": "mock", "task_id": task_id},
        )

    def get_status(self, task_id: str) -> dict[str, Any]:
        info = self.runner.get_task_info(task_id)
        if not info:
            return {"task_id": task_id, "found": False}

        return {
            "task_id": task_id,
            "found": True,
            "state": info["state"],
            "steps": info["steps"],
        }


def get_provider(provider_name: str) -> AgentProvider:
    """Return a compatibility provider adapter for legacy imports."""
    normalized = provider_name.lower()
    if normalized == "copilot":
        return CopilotProvider()
    if normalized == "custom":
        return CustomProvider()
    if normalized == "mock":
        return MockProvider()

    # Defer provider validation and ownership to the canonical registry.
    _get_canonical_provider(normalized)
    return _CanonicalProviderAdapter(normalized)


__all__ = [
    "AgentInvocationResult",
    "AgentProvider",
    "CopilotProvider",
    "CustomProvider",
    "MockAgentRunner",
    "MockProvider",
    "get_mock_runner",
    "get_provider",
]
