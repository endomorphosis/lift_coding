"""Policy evaluation engine.

Evaluates whether actions should be allowed, denied, or require confirmation
based on repository policies.
"""

from dataclasses import dataclass
from enum import Enum

import duckdb

from handsfree.db.repo_policies import get_default_policy, get_repo_policy


class PolicyDecision(str, Enum):
    """Policy decision enum."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


@dataclass
class PolicyEvaluationResult:
    """Result of a policy evaluation."""

    decision: PolicyDecision
    reason: str
    policy_checked: bool = True
    requires_checks_green: bool = False
    required_approvals: int = 0


def evaluate_action_policy(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
    action_type: str,
    pr_checks_status: str | None = None,
    pr_approvals_count: int = 0,
) -> PolicyEvaluationResult:
    """Evaluate whether an action should be allowed based on policy.

    Args:
        conn: Database connection.
        user_id: UUID of the user requesting the action.
        repo_full_name: Full repository name (owner/name).
        action_type: Type of action (e.g., "merge", "rerun", "request_review").
        pr_checks_status: Status of PR checks ("passing", "failing", None if unknown).
        pr_approvals_count: Number of approvals on the PR.

    Returns:
        PolicyEvaluationResult with decision and reason.
    """
    # Get policy for this user + repo, or use default
    policy = get_repo_policy(conn, user_id, repo_full_name)
    if not policy:
        policy = get_default_policy()

    # Check if action type is allowed
    action_allowed = False
    if action_type == "merge":
        action_allowed = policy.allow_merge
    elif action_type == "rerun":
        action_allowed = policy.allow_rerun
    elif action_type == "request_review":
        action_allowed = policy.allow_request_review
    else:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason=f"Unknown action type: {action_type}",
            policy_checked=True,
        )

    # If action is not allowed, deny immediately
    if not action_allowed:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason=f"Action '{action_type}' is not allowed by policy for {repo_full_name}",
            policy_checked=True,
        )

    # Check if checks need to be green for merge actions
    if action_type == "merge" and policy.require_checks_green:
        if pr_checks_status == "failing":
            return PolicyEvaluationResult(
                decision=PolicyDecision.DENY,
                reason="PR checks are failing and policy requires checks to be green",
                policy_checked=True,
                requires_checks_green=True,
            )
        elif pr_checks_status is None:
            # If we don't know the status, require confirmation
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_CONFIRMATION,
                reason="Check status unknown; confirmation required",
                policy_checked=True,
                requires_checks_green=True,
            )

    # Check if required approvals are met for merge actions
    if action_type == "merge" and policy.required_approvals > 0:
        if pr_approvals_count < policy.required_approvals:
            reason = (
                f"PR has {pr_approvals_count} approval(s) but "
                f"policy requires {policy.required_approvals}"
            )
            return PolicyEvaluationResult(
                decision=PolicyDecision.DENY,
                reason=reason,
                policy_checked=True,
                required_approvals=policy.required_approvals,
            )

    # If confirmation is required, return that
    if policy.require_confirmation:
        return PolicyEvaluationResult(
            decision=PolicyDecision.REQUIRE_CONFIRMATION,
            reason="Policy requires user confirmation for this action",
            policy_checked=True,
        )

    # Otherwise, allow the action
    return PolicyEvaluationResult(
        decision=PolicyDecision.ALLOW,
        reason="Action allowed by policy",
        policy_checked=True,
    )
