"""Handler for inbox.list command."""

from typing import Any

from ..github import GitHubProvider


def handle_inbox_list(
    provider: GitHubProvider, user: str, privacy_mode: bool = True
) -> dict[str, Any]:
    """
    Handle inbox.list command to show attention items.

    Args:
        provider: GitHub provider instance
        user: GitHub username
        privacy_mode: If True, no code snippets are included (default: True)

    Returns:
        Response dict with spoken_text and items
    """
    # Get user's PRs
    user_prs = provider.list_user_prs(user)

    # Process PRs into inbox items
    items = []
    for pr in user_prs:
        # Determine item type
        item_type = "pr"

        # Calculate priority based on labels and reviewer status
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

        items.append(
            {
                "type": item_type,
                "title": pr["title"],
                "priority": priority,
                "repo": pr["repo"],
                "url": pr["url"],
                "summary": summary,
            }
        )

    # Sort by priority (highest first), then by updated_at
    items.sort(
        key=lambda x: (
            -x["priority"],
            user_prs[[p["url"] for p in user_prs].index(x["url"])].get("updated_at", ""),
        )
    )

    # Generate spoken text
    if not items:
        spoken_text = "Your inbox is empty. No PRs need your attention right now."
    else:
        count = len(items)
        spoken_text = f"You have {count} item{'s' if count != 1 else ''} in your inbox. "

        # Mention top priority items
        high_priority = [item for item in items if item["priority"] >= 4]
        if high_priority:
            spoken_text += f"{len(high_priority)} high priority. "

        # List top 3 items
        top_items = items[:3]
        for i, item in enumerate(top_items, 1):
            repo_short = item["repo"].split("/")[-1]
            spoken_text += f"{i}. {item['title']} in {repo_short}. "

        if count > 3:
            spoken_text += f"Plus {count - 3} more."

    return {
        "items": items,
        "spoken_text": spoken_text.strip(),
    }
