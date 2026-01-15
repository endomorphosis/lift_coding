"""GitHub webhook ingestion with signature verification and replay protection."""

import hashlib
import hmac
import logging
import os
import re
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def get_webhook_secret() -> str | None:
    """Get webhook secret from environment.

    Returns:
        Webhook secret string if GITHUB_WEBHOOK_SECRET is set, None otherwise (dev mode).
    """
    return os.environ.get("GITHUB_WEBHOOK_SECRET")


def extract_installation_id(payload: dict[str, Any]) -> int | None:
    """Extract GitHub App installation ID from webhook payload.

    Args:
        payload: Raw webhook payload.

    Returns:
        Installation ID if present, None otherwise.
    """
    # Installation can be at top level or nested in various ways
    if "installation" in payload and isinstance(payload["installation"], dict):
        return payload["installation"].get("id")
    return None


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


def verify_github_signature(
    payload: bytes,
    signature_header: str,
    secret: str | None = None,
) -> bool:
    """Verify GitHub webhook signature.

    Args:
        payload: Raw request body bytes
        signature_header: Value of X-Hub-Signature-256 header
        secret: Webhook secret (None in dev mode allows 'dev' signature)

    Returns:
        True if signature is valid, False otherwise
    """
    # Dev mode: accept "dev" signature
    if signature_header == "dev":
        if secret is None:
            logger.debug("Dev mode: accepting 'dev' signature")
            return True
        logger.warning("Dev signature provided but secret is configured")
        return False

    if secret is None:
        logger.error("Signature verification requires a secret")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Invalid signature format: %s", signature_header)
        return False

    expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
    computed_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, computed_signature)


def normalize_github_event(
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Normalize GitHub webhook events to a common format.

    Args:
        event_type: GitHub event type (e.g., 'pull_request')
        payload: Raw webhook payload

    Returns:
        Normalized event dict or None if event type not supported
    """
    if event_type == "pull_request":
        action = payload.get("action")
        if action in ("opened", "synchronize", "reopened", "closed"):
            pr = payload.get("pull_request", {})
            return {
                "event_type": "pull_request",
                "action": action,
                "repo": payload.get("repository", {}).get("full_name"),
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title"),
                "pr_state": pr.get("state"),
                "pr_merged": pr.get("merged"),
                "pr_url": pr.get("html_url"),
                "pr_author": pr.get("user", {}).get("login"),
                "base_ref": pr.get("base", {}).get("ref"),
                "head_ref": pr.get("head", {}).get("ref"),
                "head_sha": pr.get("head", {}).get("sha"),
            }

    elif event_type == "check_suite":
        action = payload.get("action")
        if action == "completed":
            check_suite = payload.get("check_suite", {})
            return {
                "event_type": "check_suite",
                "action": action,
                "repo": payload.get("repository", {}).get("full_name"),
                "check_suite_id": check_suite.get("id"),
                "conclusion": check_suite.get("conclusion"),
                "status": check_suite.get("status"),
                "head_sha": check_suite.get("head_sha"),
                "head_branch": check_suite.get("head_branch"),
                "pr_numbers": [pr.get("number") for pr in check_suite.get("pull_requests", [])],
            }

    elif event_type == "check_run":
        action = payload.get("action")
        if action == "completed":
            check_run = payload.get("check_run", {})
            return {
                "event_type": "check_run",
                "action": action,
                "repo": payload.get("repository", {}).get("full_name"),
                "check_run_id": check_run.get("id"),
                "check_run_name": check_run.get("name"),
                "conclusion": check_run.get("conclusion"),
                "status": check_run.get("status"),
                "head_sha": check_run.get("head_sha"),
                "pr_numbers": [pr.get("number") for pr in check_run.get("pull_requests", [])],
            }

    elif event_type == "pull_request_review":
        action = payload.get("action")
        if action == "submitted":
            review = payload.get("review", {})
            pr = payload.get("pull_request", {})
            return {
                "event_type": "pull_request_review",
                "action": action,
                "repo": payload.get("repository", {}).get("full_name"),
                "pr_number": pr.get("number"),
                "review_id": review.get("id"),
                "review_state": review.get("state"),
                "review_author": review.get("user", {}).get("login"),
                "review_body": review.get("body"),
                "review_url": review.get("html_url"),
            }

    elif event_type == "issue_comment":
        action = payload.get("action")
        if action == "created":
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            comment_body = comment.get("body", "")

            # Extract @mentions from comment body
            mentions = re.findall(r"@(\w+)", comment_body)

            # Check if this is a PR comment (issue with pull_request field)
            is_pr = "pull_request" in issue
            issue_or_pr_number = issue.get("number")

            return {
                "event_type": "issue_comment",
                "action": action,
                "repo": payload.get("repository", {}).get("full_name"),
                "issue_number": issue_or_pr_number,
                "is_pull_request": is_pr,
                "comment_id": comment.get("id"),
                "comment_author": comment.get("user", {}).get("login"),
                "comment_url": comment.get("html_url"),
                "comment_body": comment_body,
                "mentions": mentions,
            }

    elif event_type == "installation":
        action = payload.get("action")
        if action in ("created", "deleted"):
            installation = payload.get("installation", {})
            account = installation.get("account", {})
            repositories = payload.get("repositories", [])

            return {
                "event_type": "installation",
                "action": action,
                "installation_id": installation.get("id"),
                "account_login": account.get("login"),
                "account_type": account.get("type"),
                "repository_selection": installation.get("repository_selection"),
                "repositories": [repo.get("full_name") for repo in repositories],
            }

    elif event_type == "installation_repositories":
        action = payload.get("action")
        if action in ("added", "removed"):
            installation = payload.get("installation", {})
            account = installation.get("account", {})
            repositories_added = payload.get("repositories_added", [])
            repositories_removed = payload.get("repositories_removed", [])

            return {
                "event_type": "installation_repositories",
                "action": action,
                "installation_id": installation.get("id"),
                "account_login": account.get("login"),
                "account_type": account.get("type"),
                "repository_selection": payload.get("repository_selection"),
                "repositories_added": [repo.get("full_name") for repo in repositories_added],
                "repositories_removed": [repo.get("full_name") for repo in repositories_removed],
            }

    # Unsupported event type or action
    return None


class WebhookStore:
    """In-memory webhook event store (stub for PR-003 database)."""

    def __init__(self):
        self._events: dict[str, dict[str, Any]] = {}
        self._delivery_ids: set[str] = set()

    def is_duplicate_delivery(self, delivery_id: str) -> bool:
        """Check if delivery ID has been processed before."""
        return delivery_id in self._delivery_ids

    def store_event(
        self,
        delivery_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_ok: bool,
    ) -> str:
        """Store webhook event.

        Args:
            delivery_id: GitHub delivery ID
            event_type: GitHub event type
            payload: Raw webhook payload
            signature_ok: Whether signature verification passed

        Returns:
            Event ID (UUID in real implementation)
        """
        event_id = str(uuid.uuid4())
        self._events[event_id] = {
            "id": event_id,
            "source": "github",
            "event_type": event_type,
            "delivery_id": delivery_id,
            "signature_ok": signature_ok,
            "payload": payload,
        }
        self._delivery_ids.add(delivery_id)
        logger.info(
            "Stored webhook event: id=%s, type=%s, delivery_id=%s",
            event_id,
            event_type,
            delivery_id,
        )
        return event_id

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Retrieve stored event by ID."""
        return self._events.get(event_id)

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent events."""
        return list(self._events.values())[-limit:]


# Global store instance (for testing; will be replaced with DB in PR-003)
_webhook_store = WebhookStore()


def get_webhook_store() -> WebhookStore:
    """Get the global webhook store instance.

    Note: This is the in-memory store for backward compatibility.
    For DB-backed storage, use get_db_webhook_store from handsfree.db.webhook_events.
    """
    return _webhook_store
