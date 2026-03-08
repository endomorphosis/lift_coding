"""Shared execution helpers for GitHub actions."""

import os
from typing import Any

from handsfree.cli import GitHubCLIAdapter
from handsfree.github.auth import get_default_auth_provider
from handsfree.github.client import (
    merge_pull_request,
    post_pull_request_comment,
    request_reviewers,
    rerun_workflow,
)


def cli_enabled() -> bool:
    """Return whether CLI-backed GitHub actions are enabled."""
    return os.getenv("HANDSFREE_GH_CLI_ENABLED", "false").lower() == "true"


def fixture_mode_enabled() -> bool:
    """Return whether CLI fixture mode is enabled."""
    return os.getenv("HANDSFREE_CLI_FIXTURE_MODE", "false").lower() == "true"


def execute_request_review_action(
    repo: str,
    pr_number: int,
    reviewers: list[str],
    user_id: str,
) -> dict[str, Any]:
    """Execute request-review through CLI, API, or fixture fallback."""
    if cli_enabled() or fixture_mode_enabled():
        result = GitHubCLIAdapter().request_review(repo, pr_number, reviewers)
        result["mode"] = result["trace"]["source"]
        return result

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    if token:
        result = request_reviewers(
            repo=repo,
            pr_number=pr_number,
            reviewers=reviewers,
            token=token,
        )
        result["mode"] = "api_live"
        return result

    return {
        "ok": True,
        "message": f"Review requested from {', '.join(reviewers)}",
        "url": f"https://github.com/{repo}/pull/{pr_number}",
        "response_data": None,
        "mode": "fixture",
    }


def execute_merge_action(
    repo: str,
    pr_number: int,
    merge_method: str,
    user_id: str,
) -> dict[str, Any]:
    """Execute merge through CLI, API, or fixture fallback."""
    if cli_enabled() or fixture_mode_enabled():
        result = GitHubCLIAdapter().merge_pr(repo, pr_number, merge_method)
        result["mode"] = result["trace"]["source"]
        return result

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    if token:
        result = merge_pull_request(
            repo=repo,
            pr_number=pr_number,
            merge_method=merge_method,
            token=token,
        )
        result["mode"] = "api_live"
        return result

    return {
        "ok": True,
        "message": f"PR #{pr_number} merged successfully",
        "url": f"https://github.com/{repo}/pull/{pr_number}",
        "response_data": None,
        "mode": "fixture",
    }


def execute_rerun_action(
    repo: str,
    pr_number: int,
    user_id: str,
) -> dict[str, Any]:
    """Execute rerun through API or fixture fallback."""
    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    if token:
        result = rerun_workflow(
            repo=repo,
            pr_number=pr_number,
            token=token,
        )
        result["mode"] = "api_live"
        return result

    return {
        "ok": True,
        "message": f"Workflow checks re-run on {repo}#{pr_number}",
        "url": f"https://github.com/{repo}/pull/{pr_number}",
        "response_data": None,
        "mode": "fixture",
    }


def execute_comment_action(
    repo: str,
    pr_number: int,
    comment_body: str,
    user_id: str,
) -> dict[str, Any]:
    """Execute comment through CLI, API, or fixture fallback."""
    if cli_enabled() or fixture_mode_enabled():
        result = GitHubCLIAdapter().comment_on_pr(repo, pr_number, comment_body)
        result["mode"] = result["trace"]["source"]
        return result

    auth_provider = get_default_auth_provider()
    token = None
    if auth_provider.supports_live_mode():
        token = auth_provider.get_token(user_id)

    if token:
        result = post_pull_request_comment(
            repo=repo,
            pr_number=pr_number,
            body=comment_body,
            token=token,
        )
        result["mode"] = "api_live"
        return result

    preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
    return {
        "ok": True,
        "message": "Comment posted",
        "url": f"https://github.com/{repo}/pull/{pr_number}",
        "response_data": {"preview": preview},
        "mode": "fixture",
    }
