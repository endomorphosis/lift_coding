"""Normalization helpers for CLI outputs."""

import json
from typing import Any


def parse_output(parser_name: str, stdout: str) -> dict[str, Any]:
    """Normalize CLI stdout into structured data."""
    if parser_name == "gh_pr_view":
        return _parse_gh_pr_view(stdout)
    if parser_name in {"gh_copilot_explain_pr", "gh_copilot_response"}:
        return _parse_copilot_explain_pr(stdout)
    if parser_name == "gh_action_result":
        return _parse_action_result(stdout)
    raise ValueError(f"Unknown CLI parser: {parser_name}")


def _parse_gh_pr_view(stdout: str) -> dict[str, Any]:
    data = json.loads(stdout)
    reviews = data.get("reviews", [])
    checks = data.get("statusCheckRollup", [])
    labels = [label["name"] for label in data.get("labels", [])]
    author = data.get("author") or {}

    approved = sum(1 for review in reviews if review.get("state") == "APPROVED")
    changes_requested = sum(1 for review in reviews if review.get("state") == "CHANGES_REQUESTED")
    commented = sum(1 for review in reviews if review.get("state") == "COMMENTED")
    failed = sum(1 for check in checks if check.get("conclusion") == "FAILURE")
    passed = sum(1 for check in checks if check.get("conclusion") == "SUCCESS")
    pending = sum(1 for check in checks if check.get("status") != "COMPLETED")

    return {
        "pr_number": data.get("number"),
        "title": data.get("title", "Unknown"),
        "author": author.get("login", "unknown"),
        "state": str(data.get("state", "open")).lower(),
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "changed_files": data.get("changedFiles", 0),
        "labels": labels,
        "description": data.get("body", ""),
        "checks": {
            "total": len(checks),
            "passed": passed,
            "failed": failed,
            "pending": pending,
        },
        "reviews": {
            "total": len(reviews),
            "approved": approved,
            "changes_requested": changes_requested,
            "commented": commented,
        },
    }


def _parse_copilot_explain_pr(stdout: str) -> dict[str, Any]:
    data = json.loads(stdout)
    return {
        "headline": data.get("headline", ""),
        "summary": data.get("summary", ""),
        "spoken_text": data.get("spoken_text", ""),
    }


def _parse_action_result(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {}
    return json.loads(stdout)
