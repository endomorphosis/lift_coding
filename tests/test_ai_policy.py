"""Tests for AI backend policy resolution."""

from handsfree.ai.policy import (
    build_policy_resolution,
    get_ai_backend_policy,
    resolve_policy_workflow,
)
from handsfree.models import AIWorkflow


def test_ai_backend_policy_defaults_to_safe_values(monkeypatch):
    """Backend policy should default to non-accelerated settings."""
    monkeypatch.delenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_ACCELERATED_SUMMARY_ENABLED", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_COMPOSITE_FAILURE_ENABLED", raising=False)

    policy = get_ai_backend_policy()

    assert policy.summary_backend == "default"
    assert policy.failure_backend == "default"


def test_ai_backend_policy_reads_new_env_vars(monkeypatch):
    """Backend policy should honor the new typed env selectors."""
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")

    policy = get_ai_backend_policy()

    assert policy.summary_backend == "accelerated"
    assert policy.failure_backend == "composite"


def test_ai_backend_policy_keeps_legacy_failure_fallback(monkeypatch):
    """Legacy composite failure env flag should still map through policy."""
    monkeypatch.delenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", raising=False)
    monkeypatch.setenv("HANDSFREE_AI_COMPOSITE_FAILURE_ENABLED", "true")

    policy = get_ai_backend_policy()

    assert policy.failure_backend == "composite"


def test_ai_backend_policy_keeps_legacy_summary_fallback(monkeypatch):
    """Legacy accelerated summary env flag should still map through policy."""
    monkeypatch.delenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", raising=False)
    monkeypatch.setenv("HANDSFREE_AI_ACCELERATED_SUMMARY_ENABLED", "true")

    policy = get_ai_backend_policy()

    assert policy.summary_backend == "accelerated"


def test_resolve_policy_workflow_remaps_pr_summary(monkeypatch):
    """Workflow alias should remap to accelerated PR summary when policy says so."""
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")

    workflow, capability_id = resolve_policy_workflow(
        workflow=AIWorkflow.PR_RAG_SUMMARY,
        capability_id=None,
    )

    assert workflow == AIWorkflow.ACCELERATED_PR_SUMMARY
    assert capability_id == "github.pr.accelerated_summary"


def test_resolve_policy_workflow_remaps_failure_analysis(monkeypatch):
    """Workflow alias should remap to accelerated failure analysis when policy says so."""
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "accelerated")

    workflow, capability_id = resolve_policy_workflow(
        workflow=AIWorkflow.FAILURE_RAG_EXPLAIN,
        capability_id=None,
    )

    assert workflow == AIWorkflow.ACCELERATED_FAILURE_EXPLAIN
    assert capability_id == "github.check.accelerated_failure_explain"


def test_resolve_policy_workflow_keeps_explicit_capability(monkeypatch):
    """Explicit capability IDs should bypass policy remapping."""
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")

    workflow, capability_id = resolve_policy_workflow(
        workflow=AIWorkflow.PR_RAG_SUMMARY,
        capability_id="github.pr.rag_summary",
    )

    assert workflow == AIWorkflow.PR_RAG_SUMMARY
    assert capability_id == "github.pr.rag_summary"


def test_build_policy_resolution_marks_remap_when_workflow_changes():
    """Policy resolution metadata should mark workflow remaps explicitly."""
    resolution = build_policy_resolution(
        requested_workflow=AIWorkflow.PR_RAG_SUMMARY,
        resolved_workflow=AIWorkflow.ACCELERATED_PR_SUMMARY,
        requested_capability_id=None,
        resolved_capability_id="github.pr.accelerated_summary",
    )

    assert resolution.policy_applied is True
    assert resolution.requested_workflow == AIWorkflow.PR_RAG_SUMMARY
    assert resolution.resolved_workflow == AIWorkflow.ACCELERATED_PR_SUMMARY


def test_build_policy_resolution_ignores_explicit_capability_calls():
    """Explicit capability calls should not be marked as policy remaps."""
    resolution = build_policy_resolution(
        requested_workflow=AIWorkflow.PR_RAG_SUMMARY,
        resolved_workflow=AIWorkflow.PR_RAG_SUMMARY,
        requested_capability_id="github.pr.rag_summary",
        resolved_capability_id="github.pr.rag_summary",
    )

    assert resolution.policy_applied is False
