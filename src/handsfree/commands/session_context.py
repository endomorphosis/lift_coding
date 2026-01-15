"""Session context manager for tracking repo/PR state across voice commands."""

from typing import Any


class SessionContext:
    """Manages session context for voice commands.

    Tracks the last referenced repo/PR from commands like inbox.list,
    pr.summarize, and checks.status so that subsequent side-effect commands
    (like pr.request_review, checks.rerun, pr.comment) can omit the repo/PR
    and still work correctly.
    """

    def __init__(self) -> None:
        """Initialize the session context manager."""
        # Maps session_id -> {"repo": str, "pr_number": int}
        self._contexts: dict[str, dict[str, Any]] = {}

    def set_repo_pr(self, session_id: str, repo: str, pr_number: int | None = None) -> None:
        """Store repo/PR context for a session.

        Args:
            session_id: Session identifier
            repo: Repository name (e.g., "owner/repo")
            pr_number: Optional PR number
        """
        if not session_id:
            return

        context = {"repo": repo}
        if pr_number is not None:
            context["pr_number"] = pr_number

        self._contexts[session_id] = context

    def get_repo_pr(
        self, session_id: str | None, fallback_repo: str | None = None
    ) -> dict[str, Any]:
        """Retrieve repo/PR context for a session.

        Args:
            session_id: Session identifier
            fallback_repo: Optional fallback repo if no session context exists

        Returns:
            Dictionary with "repo" and optionally "pr_number" keys
        """
        if not session_id or session_id not in self._contexts:
            if fallback_repo:
                return {"repo": fallback_repo}
            return {}

        return self._contexts[session_id].copy()

    def clear_session(self, session_id: str) -> None:
        """Clear context for a specific session.

        Args:
            session_id: Session identifier to clear
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
