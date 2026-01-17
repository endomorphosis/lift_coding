"""Handler for pr.summarize command."""

from typing import Any

from ..commands.profiles import ProfileConfig
from ..github import GitHubProvider
from ..logging_utils import redact_secrets
from ..models import PrivacyMode


def handle_pr_summarize(
    provider: GitHubProvider,
    repo: str,
    pr_number: int,
    privacy_mode: PrivacyMode = PrivacyMode.STRICT,
    profile_config: ProfileConfig | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Handle pr.summarize command to provide PR summary.

    Args:
        provider: GitHub provider instance
        repo: Repository name (e.g., "owner/repo")
        pr_number: PR number
        privacy_mode: Privacy mode (strict/balanced/debug), default: strict
        profile_config: Optional profile configuration for response shaping
        user_id: Optional user ID for authentication (enables live mode)

    Returns:
        Response dict with spoken_text and summary details
    """
    # Get PR details
    pr_details = provider.get_pr_details(repo, pr_number, user_id=user_id)
    pr_checks = provider.get_pr_checks(repo, pr_number, user_id=user_id)
    pr_reviews = provider.get_pr_reviews(repo, pr_number, user_id=user_id)

    # Extract key information
    title = pr_details["title"]
    description = pr_details.get("description", "")
    state = pr_details.get("state", "open")
    author = pr_details["author"]
    additions = pr_details.get("additions", 0)
    deletions = pr_details.get("deletions", 0)
    changed_files = pr_details.get("changed_files", 0)
    labels = pr_details.get("labels", [])

    # Analyze checks
    checks_summary = _summarize_checks(pr_checks)

    # Analyze reviews
    reviews_summary = _summarize_reviews(pr_reviews)

    # Build spoken text (privacy-friendly, no code)
    spoken_text = f"PR {pr_number}: {title}. "

    # Add author
    spoken_text += f"By {author}. "

    # Add diff stats
    if changed_files > 0:
        spoken_text += f"{changed_files} file{'s' if changed_files != 1 else ''} changed, "
        spoken_text += f"{additions} addition{'s' if additions != 1 else ''}, "
        spoken_text += f"{deletions} deletion{'s' if deletions != 1 else ''}. "

    # Add checks status
    if checks_summary["total"] > 0:
        if checks_summary["failed"] > 0:
            spoken_text += (
                f"Checks: {checks_summary['failed']} failing, {checks_summary['passed']} passing. "
            )
        elif checks_summary["pending"] > 0:
            spoken_text += (
                f"Checks: {checks_summary['pending']} pending, {checks_summary['passed']} passing. "
            )
        else:
            spoken_text += f"All {checks_summary['passed']} checks passing. "

    # Add review status
    if reviews_summary["total"] > 0:
        review_parts = []
        if reviews_summary["changes_requested"] > 0:
            review_parts.append(f"{reviews_summary['changes_requested']} requested changes")
        if reviews_summary["approved"] > 0:
            review_parts.append(f"{reviews_summary['approved']} approved")
        if reviews_summary["commented"] > 0 and not review_parts:
            review_parts.append(f"{reviews_summary['commented']} commented")

        if review_parts:
            spoken_text += f"Reviews: {', '.join(review_parts)}. "

        # Add latest review details
        latest_review = _get_latest_review(pr_reviews)
        if latest_review:
            review_state = latest_review.get("state", "")
            reviewer = latest_review.get("user", "unknown")
            spoken_text += f"Latest review: {review_state} by {reviewer}. "

    # Add labels if important
    important_labels = [
        label for label in labels if label in ["urgent", "security", "bug", "breaking"]
    ]
    if important_labels:
        spoken_text += f"Labels: {', '.join(important_labels)}. "

    # Handle description based on privacy mode
    description_excerpt = None
    if description:
        if privacy_mode == PrivacyMode.BALANCED:
            # Balanced: allow short description excerpts with redaction
            excerpt = redact_secrets(description[:100].strip())
            if len(description) > 100:
                excerpt += "..."
            spoken_text += f"Description: {excerpt}"
            description_excerpt = excerpt
        elif privacy_mode == PrivacyMode.DEBUG:
            # Debug: include full description in debug field (returned separately)
            description_excerpt = redact_secrets(description)
        # Strict mode: no description excerpts in spoken text

    # Apply profile-based truncation if profile_config is provided
    # Note: Optional truncation maintains backward compatibility with callers
    # that don't provide profile_config
    if profile_config:
        spoken_text = profile_config.truncate_spoken_text(spoken_text.strip())
    else:
        spoken_text = spoken_text.strip()

    result = {
        "pr_number": pr_number,
        "title": title,
        "state": state,
        "author": author,
        "additions": additions,
        "deletions": deletions,
        "changed_files": changed_files,
        "labels": labels,
        "checks": checks_summary,
        "reviews": reviews_summary,
        "spoken_text": spoken_text,
    }

    # Include debug info in debug mode
    if privacy_mode == PrivacyMode.DEBUG and description_excerpt:
        result["debug_description"] = description_excerpt

    return result


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize check runs."""
    total = len(checks)
    passed = sum(1 for c in checks if c.get("conclusion") == "success")
    failed = sum(1 for c in checks if c.get("conclusion") == "failure")
    pending = sum(1 for c in checks if c.get("status") != "completed")

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
    }


def _summarize_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize reviews."""
    total = len(reviews)
    approved = sum(1 for r in reviews if r.get("state") == "APPROVED")
    changes_requested = sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")
    commented = sum(1 for r in reviews if r.get("state") == "COMMENTED")

    return {
        "total": total,
        "approved": approved,
        "changes_requested": changes_requested,
        "commented": commented,
    }


def _get_latest_review(reviews: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Get the latest review by submitted timestamp.

    Args:
        reviews: List of review objects with 'submitted_at' (ISO 8601 timestamp),
                 'state', and 'user' fields

    Returns:
        Latest review dict or None if no reviews exist
    """
    if not reviews:
        return None

    # Filter out reviews without submitted_at timestamp
    reviews_with_timestamp = [r for r in reviews if r.get("submitted_at")]

    if not reviews_with_timestamp:
        # If no reviews have timestamps, return the first one
        return reviews[0]

    # Sort by submitted_at timestamp descending (most recent first)
    # ISO 8601 timestamps sort correctly as strings
    sorted_reviews = sorted(reviews_with_timestamp, key=lambda r: r["submitted_at"], reverse=True)

    return sorted_reviews[0]
