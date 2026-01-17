"""GitHub provider interface and fixture-backed implementation."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from handsfree.github.auth import GitHubAuthProvider, get_default_auth_provider

logger = logging.getLogger(__name__)


class GitHubProviderInterface(ABC):
    """Abstract interface for GitHub data providers."""

    @abstractmethod
    def list_user_prs(self, user: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee."""
        pass

    @abstractmethod
    def get_pr_details(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews."""
        pass

    @abstractmethod
    def get_pr_checks(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get check runs for a PR."""
        pass

    @abstractmethod
    def get_pr_reviews(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get reviews for a PR."""
        pass


class GitHubProvider(GitHubProviderInterface):
    """GitHub provider that supports both fixture and live modes.

    In fixture mode (default), returns data from fixture files.
    In live mode (when GITHUB_LIVE_MODE=true and GITHUB_TOKEN is set),
    calls the real GitHub API.
    """

    def __init__(
        self,
        fixtures_dir: Path | None = None,
        auth_provider: GitHubAuthProvider | None = None,
    ):
        """Initialize with optional fixtures directory path and auth provider.

        Args:
            fixtures_dir: Path to fixture files (defaults to tests/fixtures/github/api).
            auth_provider: Auth provider for GitHub tokens (defaults to environment-based).
        """
        if fixtures_dir is None:
            # Default to tests/fixtures/github/api relative to repo root
            fixtures_dir = Path(__file__).parent.parent.parent.parent / "tests/fixtures/github/api"
        self.fixtures_dir = Path(fixtures_dir)

        if auth_provider is None:
            auth_provider = get_default_auth_provider()
        self.auth_provider = auth_provider

        # Create a live provider instance for when live mode is enabled
        self._live_provider: LiveGitHubProvider | None = None

    def _load_fixture(self, fixture_name: str) -> Any:
        """Load a fixture file by name."""
        fixture_path = self.fixtures_dir / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        with open(fixture_path) as f:
            return json.load(f)

    def _is_live_mode(self, user_id: str | None) -> bool:
        """Check if live mode should be used for this request.

        Args:
            user_id: User ID for the request.

        Returns:
            True if live mode is enabled and a token is available.
        """
        if not self.auth_provider.supports_live_mode():
            return False
        if user_id is None:
            return False
        token = self.auth_provider.get_token(user_id)
        return token is not None

    def _get_live_provider(self, user_id: str) -> "LiveGitHubProvider":
        """Get or create a live provider instance for the given user.

        Args:
            user_id: User ID for authentication

        Returns:
            LiveGitHubProvider instance configured for the user
        """

        # Create a simple token provider that wraps the auth_provider.
        # This must implement the TokenProvider ABC because LiveGitHubProvider
        # enforces the type at runtime.
        from handsfree.github.auth import TokenProvider

        class UserTokenProvider(TokenProvider):
            def __init__(self, auth_provider: GitHubAuthProvider, user_id: str):
                self._auth_provider = auth_provider
                self._user_id = user_id

            def get_token(self) -> str | None:
                return self._auth_provider.get_token(self._user_id)

        # Create or reuse live provider
        if self._live_provider is None:
            token_provider = UserTokenProvider(self.auth_provider, user_id)
            self._live_provider = LiveGitHubProvider(token_provider)

        return self._live_provider

    def list_user_prs(self, user: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee.

        Args:
            user: GitHub username.
            user_id: User ID for auth (optional).

        Returns:
            List of PR dictionaries.
        """
        if self._is_live_mode(user_id):
            try:
                live_provider = self._get_live_provider(user_id)
                return live_provider.list_user_prs(user, user_id)
            except Exception as e:
                logger.warning("Live mode failed, falling back to fixture: %s", str(e))
        return self._load_fixture("user_prs.json")

    def get_pr_details(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            PR details dictionary.
        """
        if self._is_live_mode(user_id):
            try:
                live_provider = self._get_live_provider(user_id)
                return live_provider.get_pr_details(repo, pr_number, user_id)
            except Exception as e:
                logger.warning("Live mode failed, falling back to fixture: %s", str(e))
        return self._load_fixture(f"pr_{pr_number}_details.json")

    def get_pr_checks(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get check runs for a PR.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            List of check run dictionaries.
        """
        if self._is_live_mode(user_id):
            try:
                live_provider = self._get_live_provider(user_id)
                return live_provider.get_pr_checks(repo, pr_number, user_id)
            except Exception as e:
                logger.warning("Live mode failed, falling back to fixture: %s", str(e))
        return self._load_fixture(f"pr_{pr_number}_checks.json")

    def get_pr_reviews(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get reviews for a PR.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            List of review dictionaries.
        """
        if self._is_live_mode(user_id):
            try:
                live_provider = self._get_live_provider(user_id)
                return live_provider.get_pr_reviews(repo, pr_number, user_id)
            except Exception as e:
                logger.warning("Live mode failed, falling back to fixture: %s", str(e))
        return self._load_fixture(f"pr_{pr_number}_reviews.json")


class LiveGitHubProvider(GitHubProviderInterface):
    """Live GitHub provider that makes real API calls.

    Uses a token provider to get authentication credentials.
    Falls back to fixture behavior if no token is available.
    """

    def __init__(self, token_provider):
        """Initialize with a token provider.

        Args:
            token_provider: TokenProvider instance for authentication
        """
        from handsfree.github.auth import TokenProvider

        if not isinstance(token_provider, TokenProvider):
            raise TypeError(
                f"token_provider must be an instance of TokenProvider, "
                f"got {type(token_provider).__name__}"
            )

        self._token_provider = token_provider
        self._fallback_provider = GitHubProvider()  # For fixture fallback

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitHub API requests.

        Returns:
            Dict of headers including Authorization if token available
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HandsFree-Dev-Companion/1.0",
        }

        token = self._token_provider.get_token()
        if token:
            # SECURITY: Token is in memory only, never logged
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a GET request to GitHub API.

        Args:
            endpoint: API endpoint path (e.g., "/repos/owner/repo/pulls/123")
            params: Optional query parameters

        Returns:
            JSON response as dict or list

        Raises:
            RuntimeError: If no token is available or if HTTP request fails
        """
        token = self._token_provider.get_token()
        if not token:
            logger.warning(
                "No GitHub token available, cannot make live API request to %s", endpoint
            )
            raise RuntimeError("GitHub token not available for live API calls")

        try:
            import httpx

            url = f"https://api.github.com{endpoint}"
            headers = self._get_headers()

            logger.debug("Making GitHub API request: %s", url)

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params or {})

                # Check for rate limiting
                if response.status_code == 429:
                    rate_limit_reset = response.headers.get("X-RateLimit-Reset", "unknown")
                    logger.error("GitHub API rate limit exceeded. Reset at: %s", rate_limit_reset)
                    raise RuntimeError(
                        f"GitHub API rate limit exceeded. Try again after {rate_limit_reset}"
                    )

                # Check for authentication errors
                if response.status_code == 401:
                    logger.error("GitHub API authentication failed: 401 Unauthorized")
                    raise RuntimeError(
                        "GitHub API authentication failed. Token may be invalid or expired."
                    )

                if response.status_code == 403:
                    logger.error("GitHub API access forbidden: 403 Forbidden")
                    raise RuntimeError(
                        "GitHub API access forbidden. Token may lack required permissions."
                    )

                # Raise for other HTTP errors
                if response.status_code >= 400:
                    logger.error(
                        "GitHub API request failed: HTTP %d - %s",
                        response.status_code,
                        response.text[:200],
                    )
                    raise RuntimeError(
                        f"GitHub API request failed with status {response.status_code}"
                    )

                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException as e:
            logger.error("GitHub API request timed out: %s", str(e))
            raise RuntimeError(f"GitHub API request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error("GitHub API request error: %s", str(e))
            raise RuntimeError(f"GitHub API request failed: {e}") from e
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            logger.error("Unexpected error during GitHub API request: %s", str(e))
            raise RuntimeError(f"GitHub API request failed: {e}") from e

    def _transform_search_prs_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform GitHub search issues response to fixture format.

        Args:
            response: GitHub API search response

        Returns:
            List of PRs in fixture format
        """
        items = response.get("items", [])
        transformed = []

        for item in items:
            # Extract repo from html_url or repository_url
            repo = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
            if not repo:
                # Try to extract from html_url
                html_url = item.get("html_url", "")
                # https://github.com/owner/repo/pull/123 -> owner/repo
                parts = html_url.split("/")
                if len(parts) >= 5:
                    repo = f"{parts[3]}/{parts[4]}"

            pr_number = item.get("number", 0)
            labels = [label.get("name", "") for label in item.get("labels", [])]

            # Determine if user is requested reviewer or assignee
            # GitHub search API doesn't directly provide this, so we make reasonable guesses
            assignee = item.get("assignee") is not None
            # For requested_reviewer, we'd need to check if any reviewer is set
            requested_reviewer = len(item.get("assignees", [])) == 0 and item.get("state") == "open"

            transformed.append(
                {
                    "repo": repo,
                    "pr_number": pr_number,
                    "title": item.get("title", ""),
                    "url": item.get("html_url", ""),
                    "state": item.get("state", "open"),
                    "author": item.get("user", {}).get("login", ""),
                    "requested_reviewer": requested_reviewer,
                    "assignee": assignee,
                    "updated_at": item.get("updated_at", ""),
                    "labels": labels,
                }
            )

        return transformed

    def list_user_prs(self, user: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee.

        Falls back to fixtures if live mode not available.
        """
        try:
            # Allow callers (including the API) to pass a placeholder username.
            # In live mode we can resolve the authenticated user's login.
            if not user or user in {"me", "fixture-user"}:
                me = self._make_request("/user")
                if isinstance(me, dict) and me.get("login"):
                    user = str(me["login"])

            # Search for PRs involving the user (review-requested or assigned)
            query = f"type:pr state:open involves:{user}"
            response = self._make_request("/search/issues", params={"q": query, "per_page": 100})
            return self._transform_search_prs_response(response)
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for list_user_prs")
            return self._fallback_provider.list_user_prs(user)

    def _transform_pr_details_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Transform GitHub PR response to fixture format.

        Args:
            response: GitHub API PR response

        Returns:
            PR details in fixture format
        """
        # Extract repo from base.repo
        base_repo = response.get("base", {}).get("repo", {})
        repo = base_repo.get("full_name", "")

        labels = [label.get("name", "") for label in response.get("labels", [])]

        return {
            "repo": repo,
            "pr_number": response.get("number", 0),
            "title": response.get("title", ""),
            "description": response.get("body", ""),
            "url": response.get("html_url", ""),
            "state": response.get("state", "open"),
            "author": response.get("user", {}).get("login", ""),
            "created_at": response.get("created_at", ""),
            "updated_at": response.get("updated_at", ""),
            "labels": labels,
            "base_branch": response.get("base", {}).get("ref", ""),
            "head_branch": response.get("head", {}).get("ref", ""),
            "additions": response.get("additions", 0),
            "deletions": response.get("deletions", 0),
            "changed_files": response.get("changed_files", 0),
            "draft": response.get("draft", False),
            "mergeable": response.get("mergeable", True),
        }

    def get_pr_details(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews.

        Falls back to fixtures if live mode not available.
        """
        try:
            response = self._make_request(f"/repos/{repo}/pulls/{pr_number}")
            return self._transform_pr_details_response(response)
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_details")
            return self._fallback_provider.get_pr_details(repo, pr_number)

    def _transform_pr_checks_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform GitHub check runs response to fixture format.

        Args:
            response: GitHub API check runs response

        Returns:
            List of checks in fixture format
        """
        check_runs = response.get("check_runs", [])
        transformed = []

        for check in check_runs:
            transformed.append(
                {
                    "name": check.get("name", ""),
                    "status": check.get("status", ""),
                    "conclusion": check.get("conclusion", ""),
                    "started_at": check.get("started_at", ""),
                    "completed_at": check.get("completed_at", ""),
                    "url": check.get("html_url", ""),
                }
            )

        return transformed

    def get_pr_checks(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get check runs for a PR.

        Falls back to fixtures if live mode not available.
        """
        try:
            # First get the PR to get the head SHA
            pr_response = self._make_request(f"/repos/{repo}/pulls/{pr_number}")
            head_sha = pr_response.get("head", {}).get("sha")

            if not head_sha:
                logger.warning("Could not get head SHA for PR %s/%d", repo, pr_number)
                raise RuntimeError("Could not determine PR head SHA")

            # Get check runs for the head commit
            response = self._make_request(f"/repos/{repo}/commits/{head_sha}/check-runs")
            return self._transform_pr_checks_response(response)
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_checks")
            return self._fallback_provider.get_pr_checks(repo, pr_number)

    def _transform_pr_reviews_response(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform GitHub reviews response to fixture format.

        Args:
            reviews: GitHub API reviews response (list)

        Returns:
            List of reviews in fixture format
        """
        transformed = []

        for review in reviews:
            transformed.append(
                {
                    "user": review.get("user", {}).get("login", ""),
                    "state": review.get("state", ""),
                    "submitted_at": review.get("submitted_at", ""),
                    "body": review.get("body", ""),
                }
            )

        return transformed

    def get_pr_reviews(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get reviews for a PR.

        Falls back to fixtures if live mode not available.
        """
        try:
            reviews = self._make_request(f"/repos/{repo}/pulls/{pr_number}/reviews")
            return self._transform_pr_reviews_response(reviews)
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_reviews")
            return self._fallback_provider.get_pr_reviews(repo, pr_number)
