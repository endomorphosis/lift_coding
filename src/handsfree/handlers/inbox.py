"""Handler for inbox.list command."""

from typing import Any

from ..commands.profiles import ProfileConfig
from ..github import GitHubProvider


def handle_inbox_list(
    provider: GitHubProvider,
    user: str,
    privacy_mode: bool = True,
    profile_config: ProfileConfig | None = None,
) -> dict[str, Any]:
    """
    Handle inbox.list command to show attention items.

    Args:
        provider: GitHub provider instance
        user: GitHub username
        privacy_mode: If True, no code snippets are included (default: True)
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
            if check.get("status") == "completed":
                if check.get("conclusion") == "success":
                    checks_passed += 1
                elif check.get("conclusion") == "failure":
                    checks_failed += 1
                # Skip other conclusions: neutral, skipped, cancelled, timed_out, action_required
            else:
                # queued, in_progress
                checks_pending += 1
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

        # Add checks summary to item
        items.append(
            {
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
        )

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
