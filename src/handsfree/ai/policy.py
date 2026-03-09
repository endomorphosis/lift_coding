"""AI backend policy resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from handsfree.models import AIPolicyResolution, AIWorkflow


@dataclass(frozen=True)
class AIBackendPolicy:
    """Resolved default backend policy for AI workflows."""

    summary_backend: str = "default"
    failure_backend: str = "default"


def _normalize_backend(value: str | None, *, allow_composite: bool = False) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "accelerated":
        return "accelerated"
    if allow_composite and normalized == "composite":
        return "composite"
    return "default"


def get_ai_backend_policy() -> AIBackendPolicy:
    """Return the AI backend policy from env with legacy fallback support."""
    summary_backend = _normalize_backend(os.getenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND"))
    failure_backend = _normalize_backend(
        os.getenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND"),
        allow_composite=True,
    )

    # Legacy rollout flags remain supported as compatibility fallbacks.
    if summary_backend == "default" and os.getenv(
        "HANDSFREE_AI_ACCELERATED_SUMMARY_ENABLED", "false"
    ).lower() == "true":
        summary_backend = "accelerated"

    if failure_backend == "default" and os.getenv(
        "HANDSFREE_AI_COMPOSITE_FAILURE_ENABLED", "false"
    ).lower() == "true":
        failure_backend = "composite"

    return AIBackendPolicy(
        summary_backend=summary_backend,
        failure_backend=failure_backend,
    )


def resolve_policy_workflow(
    *,
    workflow: "AIWorkflow | None",
    capability_id: str | None,
) -> tuple["AIWorkflow | None", str | None]:
    """Resolve workflow/capability through backend policy.

    Explicit capability IDs are left untouched. Policy only applies when the
    caller targets a workflow alias.
    """
    if capability_id is not None or workflow is None:
        return workflow, capability_id

    from handsfree.models import AIWorkflow

    policy = get_ai_backend_policy()

    if workflow == AIWorkflow.PR_RAG_SUMMARY and policy.summary_backend == "accelerated":
        return AIWorkflow.ACCELERATED_PR_SUMMARY, "github.pr.accelerated_summary"

    if workflow == AIWorkflow.FAILURE_RAG_EXPLAIN:
        if policy.failure_backend == "accelerated":
            return AIWorkflow.ACCELERATED_FAILURE_EXPLAIN, "github.check.accelerated_failure_explain"
        if policy.failure_backend == "composite":
            return AIWorkflow.FAILURE_RAG_EXPLAIN, "github.check.failure_rag_explain"

    return workflow, None


def build_policy_resolution(
    *,
    requested_workflow: "AIWorkflow | None",
    resolved_workflow: "AIWorkflow | None",
    requested_capability_id: str | None,
    resolved_capability_id: str,
) -> "AIPolicyResolution":
    """Build API-facing metadata describing policy remapping."""
    from handsfree.models import AIPolicyResolution

    return AIPolicyResolution(
        requested_workflow=requested_workflow,
        resolved_workflow=resolved_workflow,
        requested_capability_id=requested_capability_id,
        resolved_capability_id=resolved_capability_id,
        policy_applied=(
            requested_capability_id is None
            and requested_workflow is not None
            and requested_workflow != resolved_workflow
        ),
    )
