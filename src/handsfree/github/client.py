"""GitHub API client for write operations.

This module provides functions for making GitHub API writes like requesting reviewers.
Uses httpx with timeouts and proper error handling.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import for httpx to avoid dependency when not needed
_httpx = None


def _import_httpx():
    """Lazily import httpx library."""
    global _httpx
    if _httpx is None:
        import httpx as httpx_module

        _httpx = httpx_module
    return _httpx


def request_reviewers(
    repo: str,
    pr_number: int,
    reviewers: list[str],
    token: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Request reviewers on a GitHub PR using the GitHub API.

    This function makes a real HTTP POST request to GitHub's API to add reviewers
    to a pull request. It should only be called when live mode is enabled and a
    valid token is available.

    Args:
        repo: Repository in owner/name format (e.g., "octocat/hello-world").
        pr_number: Pull request number.
        reviewers: List of GitHub usernames to request as reviewers.
        token: GitHub authentication token.
        timeout: Request timeout in seconds (default: 10.0).

    Returns:
        Dictionary with result information:
        - ok: bool - True if request succeeded
        - message: str - Human-readable message
        - status_code: int - HTTP status code
        - response_data: dict - GitHub API response (if successful)

    Raises:
        ValueError: If inputs are invalid (empty repo, pr_number < 1, etc.)

    Note:
        This function logs the request but never logs the token for security.
        Network errors are caught and returned as error results rather than raised.
    """
    # Validate inputs
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if pr_number < 1:
        raise ValueError(f"Invalid pr_number: {pr_number}. Must be >= 1")
    if not reviewers:
        raise ValueError("reviewers list cannot be empty")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()

    # Build API endpoint
    endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requested_reviewers"

    # Build request headers
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Build request payload
    payload = {"reviewers": reviewers}

    logger.info(
        "Requesting reviewers on %s#%d: %s (live mode)",
        repo,
        pr_number,
        ", ".join(reviewers),
    )

    try:
        # Make the POST request
        response = httpx.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        # Check if request was successful (2xx status code)
        if 200 <= response.status_code < 300:
            logger.info(
                "Successfully requested reviewers on %s#%d (HTTP %d)",
                repo,
                pr_number,
                response.status_code,
            )
            return {
                "ok": True,
                "message": f"Review requested from {', '.join(reviewers)}",
                "status_code": response.status_code,
                "response_data": response.json(),
            }
        else:
            # Non-2xx status code
            error_msg = f"GitHub API returned HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = f"{error_msg}: {error_data['message']}"
            except Exception:
                # If response body isn't JSON, use the text
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:200]}"

            logger.error(
                "Failed to request reviewers on %s#%d: %s",
                repo,
                pr_number,
                error_msg,
            )
            return {
                "ok": False,
                "message": error_msg,
                "status_code": response.status_code,
            }

    except Exception as e:
        # Network error, timeout, or other exception
        error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
        logger.error(
            "Failed to request reviewers on %s#%d: %s",
            repo,
            pr_number,
            error_msg,
        )
        return {
            "ok": False,
            "message": error_msg,
            "status_code": 0,  # 0 indicates network error (no response)
        }


def rerun_workflow(
    repo: str,
    pr_number: int,
    token: str,
    run_id: int | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Re-run workflow checks for a PR using the GitHub API.

    If run_id is provided, reruns that workflow run. Otherwise, resolves the
    latest Actions workflow run for the PR's head SHA and reruns it.
    """
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if pr_number < 1:
        raise ValueError(f"Invalid pr_number: {pr_number}. Must be >= 1")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resolved_run_id = run_id
        if resolved_run_id is None:
            pr_result = get_pull_request(
                repo=repo, pr_number=pr_number, token=token, timeout=timeout
            )
            if not pr_result.get("ok"):
                return {
                    "ok": False,
                    "message": f"Failed to fetch PR info: {pr_result.get('message')}",
                    "status_code": pr_result.get("status_code", 0),
                }

            pr_data = pr_result.get("pr_data") or {}
            head_sha = (pr_data.get("head") or {}).get("sha")
            if not head_sha:
                return {
                    "ok": False,
                    "message": "Could not determine PR head SHA",
                    "status_code": pr_result.get("status_code", 200),
                }

            runs_endpoint = f"https://api.github.com/repos/{repo}/actions/runs"
            runs_response = httpx.get(
                runs_endpoint,
                headers=headers,
                params={"head_sha": head_sha, "per_page": 1},
                timeout=timeout,
            )

            if not (200 <= runs_response.status_code < 300):
                return {
                    "ok": False,
                    "message": f"Failed to fetch workflow runs: HTTP {runs_response.status_code}",
                    "status_code": runs_response.status_code,
                }

            runs_data = runs_response.json() or {}
            workflow_runs = runs_data.get("workflow_runs") or []
            if not workflow_runs:
                return {
                    "ok": False,
                    "message": f"No workflow runs found for PR #{pr_number}",
                    "status_code": 404,
                }

            resolved_run_id = int(workflow_runs[0]["id"])

        rerun_endpoint = f"https://api.github.com/repos/{repo}/actions/runs/{resolved_run_id}/rerun"
        rerun_response = httpx.post(rerun_endpoint, headers=headers, timeout=timeout)

        if 200 <= rerun_response.status_code < 300:
            return {
                "ok": True,
                "message": f"Workflow checks re-run on PR #{pr_number}",
                "status_code": rerun_response.status_code,
                "run_id": resolved_run_id,
            }

        error_msg = f"GitHub API returned HTTP {rerun_response.status_code}"
        try:
            error_data = rerun_response.json()
            if isinstance(error_data, dict) and error_data.get("message"):
                error_msg = f"{error_msg}: {error_data['message']}"
        except Exception:
            if rerun_response.text:
                error_msg = f"{error_msg}: {rerun_response.text[:200]}"

        return {
            "ok": False,
            "message": error_msg,
            "status_code": rerun_response.status_code,
            "run_id": resolved_run_id,
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Request failed: {type(e).__name__}: {str(e)}",
            "status_code": 0,
        }


def get_pull_request(
    repo: str,
    pr_number: int,
    token: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Get PR details from GitHub API."""
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if pr_number < 1:
        raise ValueError(f"Invalid pr_number: {pr_number}. Must be >= 1")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()
    endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    logger.info("Getting PR details for %s#%d (live mode)", repo, pr_number)

    try:
        response = httpx.get(endpoint, headers=headers, timeout=timeout)
        if 200 <= response.status_code < 300:
            return {
                "ok": True,
                "message": "PR details fetched successfully",
                "status_code": response.status_code,
                "pr_data": response.json(),
            }

        error_msg = f"GitHub API returned HTTP {response.status_code}"
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and error_data.get("message"):
                error_msg = f"{error_msg}: {error_data['message']}"
        except Exception:
            if response.text:
                error_msg = f"{error_msg}: {response.text[:200]}"

        return {"ok": False, "message": error_msg, "status_code": response.status_code}
    except Exception as e:
        return {
            "ok": False,
            "message": f"Request failed: {type(e).__name__}: {str(e)}",
            "status_code": 0,
        }


def merge_pull_request(
    repo: str,
    pr_number: int,
    merge_method: str,
    token: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Merge a PR using the GitHub API."""
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if pr_number < 1:
        raise ValueError(f"Invalid pr_number: {pr_number}. Must be >= 1")
    if merge_method not in ("merge", "squash", "rebase"):
        raise ValueError(f"Invalid merge_method: {merge_method}. Must be merge, squash, or rebase")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()
    endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    logger.info("Merging PR %s#%d (method=%s, live mode)", repo, pr_number, merge_method)

    try:
        response = httpx.put(
            endpoint,
            json={"merge_method": merge_method},
            headers=headers,
            timeout=timeout,
        )

        if 200 <= response.status_code < 300:
            response_data = None
            try:
                response_data = response.json()
            except Exception:
                response_data = None
            return {
                "ok": True,
                "message": f"PR #{pr_number} merged successfully",
                "status_code": response.status_code,
                "response_data": response_data,
            }

        error_type = "unknown"
        if response.status_code == 405:
            error_type = "not_mergeable"
        elif response.status_code == 409:
            error_type = "conflict"
        elif response.status_code == 422:
            error_type = "invalid_state"
        elif response.status_code == 403:
            error_type = "forbidden"
        elif response.status_code == 404:
            error_type = "not_found"

        error_msg = f"GitHub API returned HTTP {response.status_code}"
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and error_data.get("message"):
                error_msg = f"{error_msg}: {error_data['message']}"
        except Exception:
            if response.text:
                error_msg = f"{error_msg}: {response.text[:200]}"

        return {
            "ok": False,
            "message": error_msg,
            "status_code": response.status_code,
            "error_type": error_type,
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Request failed: {type(e).__name__}: {str(e)}",
            "status_code": 0,
            "error_type": "network_error",
        }


def create_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Create a GitHub issue using the GitHub API.

    Args:
        repo: Repository in owner/name format (e.g., "octocat/hello-world").
        title: Issue title.
        body: Issue body.
        labels: Optional list of label names to apply.
        token: GitHub authentication token.
        timeout: Request timeout in seconds (default: 10.0).

    Returns:
        Dictionary with result information:
        - ok: bool - True if request succeeded
        - message: str - Human-readable message
        - status_code: int - HTTP status code
        - issue_data: dict - GitHub API response (if successful)
        - issue_url: str - URL to the created issue (if successful)
        - issue_number: int - Issue number (if successful)

    Raises:
        ValueError: If inputs are invalid (empty repo, title, etc.)
    """
    # Validate inputs
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if not title:
        raise ValueError("title cannot be empty")
    if not body:
        raise ValueError("body cannot be empty")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()

    # Build API endpoint
    endpoint = f"https://api.github.com/repos/{repo}/issues"

    # Build request headers
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Build request payload
    payload: dict[str, Any] = {
        "title": title,
        "body": body,
    }
    if labels:
        payload["labels"] = labels

    logger.info(
        "Creating issue in %s with title: %s (live mode)",
        repo,
        title[:50] + ("..." if len(title) > 50 else ""),
    )

    try:
        # Make the POST request
        response = httpx.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        # Check if request was successful (2xx status code)
        if 200 <= response.status_code < 300:
            issue_data = response.json()
            logger.info(
                "Successfully created issue %s#%d (HTTP %d)",
                repo,
                issue_data.get("number"),
                response.status_code,
            )
            return {
                "ok": True,
                "message": f"Issue #{issue_data.get('number')} created successfully",
                "status_code": response.status_code,
                "issue_data": issue_data,
                "issue_url": issue_data.get("html_url"),
                "issue_number": issue_data.get("number"),
            }
        else:
            # Non-2xx status code
            error_msg = f"GitHub API returned HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = f"{error_msg}: {error_data['message']}"
            except Exception:
                # If response body isn't JSON, use the text
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:200]}"

            logger.error(
                "Failed to create issue in %s: %s",
                repo,
                error_msg,
            )
            return {
                "ok": False,
                "message": error_msg,
                "status_code": response.status_code,
            }

    except Exception as e:
        # Network error, timeout, or other exception
        error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
        logger.error(
            "Failed to create issue in %s: %s",
            repo,
            error_msg,
        )
        return {
            "ok": False,
            "message": error_msg,
            "status_code": 0,  # 0 indicates network error (no response)
        }
