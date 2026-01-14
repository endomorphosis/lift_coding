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

    This function makes real HTTP requests to GitHub's API to re-run workflow runs.
    If run_id is provided, it will re-run that specific workflow run.
    Otherwise, it will fetch the latest workflow run for the PR's head SHA and re-run it.
def get_pull_request(
    repo: str,
    pr_number: int,
    token: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Get PR details from GitHub API for precondition validation.

    This function fetches PR details to validate merge preconditions like:
    - PR is open
    - Checks status
    - Review status
    - Mergeability

    Args:
        repo: Repository in owner/name format (e.g., "octocat/hello-world").
        pr_number: Pull request number.
        token: GitHub authentication token.
        run_id: Optional workflow run ID. If not provided, fetches latest for PR.
        timeout: Request timeout in seconds (default: 10.0).

    Returns:
        Dictionary with result information:
        - ok: bool - True if request succeeded
        - message: str - Human-readable message
        - status_code: int - HTTP status code
        - response_data: dict - GitHub API response (if successful)
        - run_id: int - The workflow run ID that was re-run
        - pr_data: dict - PR details (if successful) including state, mergeable, etc.

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
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()

    # Build API endpoint
    endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"

    # Build request headers
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # If run_id is not provided, fetch the latest workflow run for this PR
    if run_id is None:
        logger.info(
            "Fetching latest workflow run for %s#%d (live mode)",
            repo,
            pr_number,
        )

        try:
            # First, get the PR to find its head SHA
            pr_endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
            pr_response = httpx.get(pr_endpoint, headers=headers, timeout=timeout)

            if not (200 <= pr_response.status_code < 300):
                error_msg = f"Failed to fetch PR info: HTTP {pr_response.status_code}"
                try:
                    error_data = pr_response.json()
                    if "message" in error_data:
                        error_msg = f"{error_msg}: {error_data['message']}"
                except Exception:
                    if pr_response.text:
                        error_msg = f"{error_msg}: {pr_response.text[:200]}"
                logger.error("Failed to fetch PR %s#%d: %s", repo, pr_number, error_msg)
                return {
                    "ok": False,
                    "message": error_msg,
                    "status_code": pr_response.status_code,
                }

            pr_data = pr_response.json()
            head_sha = pr_data.get("head", {}).get("sha")

            if not head_sha:
                error_msg = "Could not find head SHA for PR"
                logger.error("Failed to get head SHA for %s#%d", repo, pr_number)
                return {
                    "ok": False,
                    "message": error_msg,
                    "status_code": pr_response.status_code,
                }

            # Now fetch workflow runs for this SHA
            runs_endpoint = f"https://api.github.com/repos/{repo}/actions/runs"
            runs_response = httpx.get(
                runs_endpoint,
                headers=headers,
                params={"head_sha": head_sha, "per_page": 1},
                timeout=timeout,
            )

            if not (200 <= runs_response.status_code < 300):
                error_msg = f"Failed to fetch workflow runs: HTTP {runs_response.status_code}"
                try:
                    error_data = runs_response.json()
                    if "message" in error_data:
                        error_msg = f"{error_msg}: {error_data['message']}"
                except Exception:
                    if runs_response.text:
                        error_msg = f"{error_msg}: {runs_response.text[:200]}"
                logger.error(
                    "Failed to fetch workflow runs for %s#%d: %s",
                    repo,
                    pr_number,
                    error_msg,
                )
                return {
                    "ok": False,
                    "message": error_msg,
                    "status_code": runs_response.status_code,
                }

            runs_data = runs_response.json()
            workflow_runs = runs_data.get("workflow_runs", [])

            if not workflow_runs:
                error_msg = f"No workflow runs found for PR #{pr_number}"
                logger.warning("No workflow runs found for %s#%d", repo, pr_number)
                return {
                    "ok": False,
                    "message": error_msg,
                    "status_code": 404,
                }

            run_id = workflow_runs[0]["id"]
            logger.info("Found workflow run ID %d for %s#%d", run_id, repo, pr_number)

        except Exception as e:
            error_msg = f"Failed to fetch workflow run: {type(e).__name__}: {str(e)}"
            logger.error(
                "Failed to fetch workflow run for %s#%d: %s",
                repo,
                pr_number,
                error_msg,
            )
            return {
                "ok": False,
                "message": error_msg,
                "status_code": 0,
            }

    # Now re-run the workflow
    rerun_endpoint = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/rerun"

    logger.info(
        "Re-running workflow run %d on %s#%d (live mode)",
        run_id,
        repo,
        pr_number,
    )

    try:
        # Make the POST request to re-run
        response = httpx.post(
            rerun_endpoint,
    logger.info("Getting PR details for %s#%d (live mode)", repo, pr_number)

    try:
        # Make the GET request
        response = httpx.get(
            endpoint,
            headers=headers,
            timeout=timeout,
        )

        # Check if request was successful (2xx status code)
        if 200 <= response.status_code < 300:
            pr_data = response.json()
            logger.info(
                "Successfully fetched PR %s#%d: state=%s, mergeable=%s (HTTP %d)",
                repo,
                pr_number,
                pr_data.get("state"),
                pr_data.get("mergeable"),
                response.status_code,
            )
            return {
                "ok": True,
                "message": "PR details fetched successfully",
                "status_code": response.status_code,
                "pr_data": pr_data,
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

            logger.error("Failed to get PR %s#%d: %s", repo, pr_number, error_msg)
            return {
                "ok": False,
                "message": error_msg,
                "status_code": response.status_code,
            }

    except Exception as e:
        # Network error, timeout, or other exception
        error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
        logger.error("Failed to get PR %s#%d: %s", repo, pr_number, error_msg)
        return {
            "ok": False,
            "message": error_msg,
            "status_code": 0,  # 0 indicates network error (no response)
        }


def merge_pull_request(
    repo: str,
    pr_number: int,
    merge_method: str,
    token: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Merge a GitHub PR using the GitHub API.

    This function makes a real HTTP PUT request to GitHub's API to merge a pull request.
    It should only be called when live mode is enabled and a valid token is available,
    and after all preconditions have been validated.

    Args:
        repo: Repository in owner/name format (e.g., "octocat/hello-world").
        pr_number: Pull request number.
        merge_method: Merge method ("merge", "squash", or "rebase").
        token: GitHub authentication token.
        timeout: Request timeout in seconds (default: 10.0).

    Returns:
        Dictionary with result information:
        - ok: bool - True if merge succeeded
        - message: str - Human-readable message
        - status_code: int - HTTP status code
        - response_data: dict - GitHub API response (if successful)
        - error_type: str - Error classification (if failed):
          "conflict", "blocked", "not_open", etc.

    Raises:
        ValueError: If inputs are invalid (empty repo, pr_number < 1, etc.)

    Note:
        This function logs the request but never logs the token for security.
        Network errors are caught and returned as error results rather than raised.
        
        GitHub API error codes:
        - 405: PR not mergeable (checks failing, not open, etc.)
        - 409: Merge conflict exists
        - 422: Validation failed (PR already merged, closed, etc.)
    """
    # Validate inputs
    if not repo or "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    if pr_number < 1:
        raise ValueError(f"Invalid pr_number: {pr_number}. Must be >= 1")
    if merge_method not in ("merge", "squash", "rebase"):
        raise ValueError(f"Invalid merge_method: {merge_method}. Must be merge, squash, or rebase")
    if not token:
        raise ValueError("token cannot be empty")

    httpx = _import_httpx()

    # Build API endpoint
    endpoint = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"

    # Build request headers
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HandsFree-Dev-Companion/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Build request payload
    payload = {"merge_method": merge_method}

    logger.info(
        "Merging PR %s#%d with method '%s' (live mode)",
        repo,
        pr_number,
        merge_method,
    )

    try:
        # Make the PUT request
        response = httpx.put(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        # Check if request was successful (2xx status code)
        if 200 <= response.status_code < 300:
            logger.info(
                "Successfully re-ran workflow run %d on %s#%d (HTTP %d)",
                run_id,
                "Successfully merged PR %s#%d (HTTP %d)",
                repo,
                pr_number,
                response.status_code,
            )
            return {
                "ok": True,
                "message": f"Workflow checks re-run on PR #{pr_number}",
                "status_code": response.status_code,
                "run_id": run_id,
            }
        else:
            # Non-2xx status code
            error_msg = f"GitHub API returned HTTP {response.status_code}"
                "message": f"PR #{pr_number} merged successfully",
                "status_code": response.status_code,
                "response_data": response.json(),
            }
        else:
            # Non-2xx status code - classify the error
            error_msg = f"GitHub API returned HTTP {response.status_code}"
            error_type = "unknown"
            
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = f"{error_msg}: {error_data['message']}"
            except Exception:
                # If response body isn't JSON, use the text
                if response.text:
                    error_msg = f"{error_msg}: {response.text[:200]}"

            logger.error(
                "Failed to re-run workflow on %s#%d: %s",
                repo,
                pr_number,
                error_msg,
            # Classify error types based on status code
            if response.status_code == 405:
                error_type = "not_mergeable"
                error_msg = "PR is not mergeable (checks may be failing or PR is not open)"
            elif response.status_code == 409:
                error_type = "conflict"
                error_msg = "PR has merge conflicts"
            elif response.status_code == 422:
                error_type = "invalid_state"
                error_msg = (
                    "PR is not in a valid state for merging "
                    "(may be closed or already merged)"
                )
            elif response.status_code == 403:
                error_type = "forbidden"
                error_msg = "Insufficient permissions to merge PR"
            elif response.status_code == 404:
                error_type = "not_found"
                error_msg = "PR not found"

            logger.error(
                "Failed to merge PR %s#%d: %s (error_type=%s)",
                repo,
                pr_number,
                error_msg,
                error_type,
            )
            return {
                "ok": False,
                "message": error_msg,
                "status_code": response.status_code,
                "error_type": error_type,
            }

    except Exception as e:
        # Network error, timeout, or other exception
        error_msg = f"Request failed: {type(e).__name__}: {str(e)}"
        logger.error(
            "Failed to re-run workflow on %s#%d: %s",
            repo,
            pr_number,
            error_msg,
        )
        logger.error("Failed to merge PR %s#%d: %s", repo, pr_number, error_msg)
        return {
            "ok": False,
            "message": error_msg,
            "status_code": 0,  # 0 indicates network error (no response)
            "error_type": "network_error",
        }
