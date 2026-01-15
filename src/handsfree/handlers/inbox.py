"""Handler for inbox.list command."""

from typing import Any

from ..commands.profiles import ProfileConfig
from ..github import GitHubProvider
from ..logging_utils import redact_secrets
from ..models import PrivacyMode


def handle_inbox_list(
    provider: GitHubProvider,
    user: str,
    privacy_mode: PrivacyMode = PrivacyMode.STRICT,
    profile_config: ProfileConfig | None = None,
) -> dict[str, Any]:
    """
    Handle inbox.list command to show attention items.

    Args:
        provider: GitHub provider instance
        user: GitHub username
        privacy_mode: Privacy mode (strict/balanced/debug), default: strict
        profile_config: Optional profile configuration for response shaping

    Returns:
        Response dict with spoken_text and items
    """
    # Get user's PRs
    user_prs = provider.list_user_prs(user)

    # Process PRs into inbox items
    items = []
    for pr in user_prs:
        # Fetch checks for this PR
        try:
            checks = provider.get_pr_checks(pr["repo"], pr["pr_number"])
        except Exception:
            # If checks fetch fails, continue with empty checks
            checks = []

        # Calculate checks summary
        checks_passed = 0
        checks_failed = 0
        checks_pending = 0

        for check in checks:
            status = check.get("status")
            conclusion = check.get("conclusion")

            if status != "completed":
                # queued, in_progress
                checks_pending += 1
            elif conclusion == "success":
                checks_passed += 1
            elif conclusion == "failure":
                checks_failed += 1
            # Skip other conclusions (neutral, skipped, cancelled, timed_out, action_required)
            # These are not counted as passed, failed, or pending
        # Determine item type
        item_type = "pr"

        # Calculate priority based on labels, reviewer status, and failing checks
        priority = 3  # default
        labels = pr.get("labels", [])

        if "urgent" in labels or "security" in labels:
            priority = 5
        elif "bug" in labels:
            priority = 4
        elif pr.get("requested_reviewer", False):
            priority = 3
        elif pr.get("assignee", False):
            priority = 3
        else:
            priority = 2

        # Boost priority if checks are failing
        if checks_failed > 0 and priority < 4:
            priority = 4

        # Build summary
        label_text = f" ({', '.join(labels)})" if labels else ""
        role = ""
        if pr.get("requested_reviewer", False):
            role = "review requested"
        elif pr.get("assignee", False):
            role = "assigned"

        summary = f"{pr['title']}{label_text}"
        if role:
            summary = f"{role}: {summary}"

        # Apply redaction based on privacy mode
        if privacy_mode == PrivacyMode.BALANCED:
            # Redact any potential secrets in summary
            summary = redact_secrets(summary)
        elif privacy_mode == PrivacyMode.STRICT:
            # In strict mode, ensure no code-like content
            summary = redact_secrets(summary)

        item_data = {
            "type": item_type,
            "title": pr["title"],
            "priority": priority,
            "repo": pr["repo"],
            "url": pr["url"],
            "summary": summary,
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "checks_pending": checks_pending,
        }

        # Add debug info in debug mode
        if privacy_mode == PrivacyMode.DEBUG:
            item_data["debug_info"] = {
                "labels": labels,
                "requested_reviewer": pr.get("requested_reviewer", False),
                "assignee": pr.get("assignee", False),
            }

        # Add checks summary to item
        items.append(item_data)

    # Sort by priority (highest first), then by updated_at
    # Create a mapping for efficient lookup
    pr_by_url = {pr["url"]: pr for pr in user_prs}
    items.sort(
        key=lambda x: (
            -x["priority"],
            pr_by_url[x["url"]].get("updated_at", ""),
        )
    )

    # Generate spoken text
    if not items:
        spoken_text = "Your inbox is empty. No PRs need your attention right now."
    else:
        count = len(items)
        spoken_text = f"You have {count} item{'s' if count != 1 else ''} in your inbox. "

        # Mention failing checks
        failing_checks_count = sum(1 for item in items if item["checks_failed"] > 0)
        if failing_checks_count > 0:
            spoken_text += f"{failing_checks_count} with failing checks. "

        # Mention top priority items
        high_priority = [item for item in items if item["priority"] >= 4]
        if high_priority and failing_checks_count == 0:
            spoken_text += f"{len(high_priority)} high priority. "

        # List top 3 items
        top_items = items[:3]
        for i, item in enumerate(top_items, 1):
            repo_short = item["repo"].split("/")[-1]
            spoken_text += f"{i}. {item['title']} in {repo_short}. "

        if count > 3:
            spoken_text += f"Plus {count - 3} more."

    # Apply profile-based truncation if profile_config is provided
    # Note: Optional truncation maintains backward compatibility with callers
    # that don't provide profile_config
    if profile_config:
        spoken_text = profile_config.truncate_spoken_text(spoken_text.strip())
    else:
        spoken_text = spoken_text.strip()

    return {
        "items": items,
        "spoken_text": spoken_text,
    }
