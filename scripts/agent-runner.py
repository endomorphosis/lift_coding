#!/usr/bin/env python3
"""
Example Custom Agent Runner

This script polls a GitHub dispatch repository for new issues labeled 'copilot-agent',
processes them, and creates pull requests in the target repository with correlation metadata.

This is a reference implementation - customize the task processing logic for your needs.
"""

import base64
import json
import logging
import os
import re
import time
from typing import Any

import requests

# Configuration from environment
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
DISPATCH_REPO = os.environ.get("DISPATCH_REPO", "")
TARGET_REPO = os.environ.get("TARGET_REPO", "")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
GITHUB_API_BASE = "https://api.github.com"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent-runner")


class GitHubClient:
    """Simple GitHub API client"""
    
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "agent-runner/1.0"
        })
    
    def get(self, path: str) -> dict[str, Any]:
        """GET request to GitHub API"""
        url = f"{GITHUB_API_BASE}{path}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST request to GitHub API"""
        url = f"{GITHUB_API_BASE}{path}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def patch(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """PATCH request to GitHub API"""
        url = f"{GITHUB_API_BASE}{path}"
        response = self.session.patch(url, json=data)
        response.raise_for_status()
        return response.json()


def extract_task_metadata(issue_body: str) -> dict[str, Any] | None:
    """Extract agent_task_metadata from issue body"""
    metadata_match = re.search(
        r'<!--\s*agent_task_metadata\s+(.*?)\s*-->',
        issue_body,
        re.DOTALL
    )
    
    if metadata_match:
        try:
            metadata = json.loads(metadata_match.group(1))
            return metadata
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing task metadata: {e}")
            return None
    
    return None


def sanitize_task_id(task_id: str) -> str:
    """
    Sanitize task_id to be safe for use in branch names and file paths.
    Removes all non-alphanumeric characters except hyphens and underscores.
    """
    # Remove any character that's not alphanumeric, hyphen, or underscore
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', task_id)
    
    # Ensure it's not empty and has reasonable length
    if not sanitized:
        sanitized = "unknown"
    
    # Truncate to reasonable length (8 chars is UUID prefix)
    return sanitized[:8]


def process_task(metadata: dict[str, Any]) -> str:
    """
    Process the agent task and return the result.
    
    This is a placeholder implementation - customize for your needs.
    Examples:
    - Call an LLM API (OpenAI, Anthropic, etc.)
    - Run code generation or refactoring scripts
    - Execute pre-defined automation workflows
    - Integrate with other tools or services
    """
    task_id = metadata.get("task_id", "")
    instruction = metadata.get("instruction", "")
    
    logger.info(f"Processing task {task_id}: {instruction}")
    
    # Placeholder processing
    result = f"""# Agent Task Result

Task ID: {task_id}
Instruction: {instruction}

## Implementation

This is a placeholder implementation created by the example agent runner.

Replace this with your actual task processing logic:
1. Parse the instruction
2. Generate or modify code
3. Run tests or validation
4. Return the changes

## TODO

- [ ] Implement actual task processing logic
- [ ] Add error handling and validation
- [ ] Integrate with LLM or automation tools
"""
    
    return result


def create_pull_request(
    client: GitHubClient,
    target_repo: str,
    task_metadata: dict[str, Any],
    task_result: str,
    dispatch_issue_number: int,
    dispatch_repo: str
) -> str | None:
    """
    Create a pull request in the target repository with correlation metadata.
    
    Returns PR URL if successful, None otherwise.
    """
    task_id = task_metadata.get("task_id", "")
    task_id_safe = sanitize_task_id(task_id)
    instruction = task_metadata.get("instruction", "")
    
    # Create branch name
    branch_name = f"agent-task-{task_id_safe}"
    
    # Get default branch
    repo_info = client.get(f"/repos/{target_repo}")
    default_branch = repo_info.get("default_branch", "main")
    
    # Get default branch SHA
    ref_info = client.get(f"/repos/{target_repo}/git/ref/heads/{default_branch}")
    base_sha = ref_info["object"]["sha"]
    
    # Create new branch
    try:
        client.post(f"/repos/{target_repo}/git/refs", {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        })
        logger.info(f"Created branch {branch_name}")
    except requests.HTTPError as e:
        if e.response.status_code == 422:
            logger.warning(f"Branch {branch_name} already exists, using existing branch")
        else:
            raise
    
    # Create file with task result
    file_path = f"agent-tasks/{task_id_safe}.md"
    file_content = task_result.encode("utf-8")
    encoded_content = base64.b64encode(file_content).decode("utf-8")
    
    # Check if file exists
    try:
        existing_file = client.get(f"/repos/{target_repo}/contents/{file_path}?ref={branch_name}")
        file_sha = existing_file.get("sha")
    except requests.HTTPError:
        file_sha = None
    
    # Create or update file
    commit_data = {
        "message": f"Process agent task {task_id_safe}",
        "content": encoded_content,
        "branch": branch_name
    }
    if file_sha:
        commit_data["sha"] = file_sha
    
    client.post(f"/repos/{target_repo}/contents/{file_path}", commit_data)
    logger.info(f"Committed changes to {file_path}")
    
    # Create pull request
    pr_title = f"Agent task: {instruction[:80]}"
    pr_body = f"""This PR was created by the agent runner to address the following task:

**Instruction**: {instruction}

**Task Details**:
- Task ID: {task_id}
- User ID: {task_metadata.get('user_id', 'unknown')}
- Dispatch Issue: {dispatch_repo}#{dispatch_issue_number}

## Changes

{task_result[:500]}

{'...' if len(task_result) > 500 else ''}

## Correlation Metadata

<!-- agent_task_metadata {json.dumps({"task_id": task_id})} -->

Fixes {dispatch_repo}#{dispatch_issue_number}
"""
    
    try:
        pr_data = client.post(f"/repos/{target_repo}/pulls", {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": default_branch
        })
        pr_url = pr_data.get("html_url", "")
        logger.info(f"Created PR: {pr_url}")
        return pr_url
    except requests.HTTPError as e:
        logger.error(f"Error creating PR: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None


def comment_on_issue(
    client: GitHubClient,
    repo: str,
    issue_number: int,
    comment: str
):
    """Post a comment on a GitHub issue"""
    try:
        client.post(f"/repos/{repo}/issues/{issue_number}/comments", {
            "body": comment
        })
        logger.info(f"Commented on issue {repo}#{issue_number}")
    except requests.HTTPError as e:
        logger.error(f"Error commenting on issue: {e}")


def mark_issue_processed(
    client: GitHubClient,
    repo: str,
    issue_number: int,
    label: str = "agent-processed"
):
    """Add a label to mark issue as processed"""
    try:
        client.post(f"/repos/{repo}/issues/{issue_number}/labels", {
            "labels": [label]
        })
        logger.info(f"Added label '{label}' to issue {repo}#{issue_number}")
    except requests.HTTPError as e:
        logger.error(f"Error adding label to issue: {e}")


def poll_dispatch_issues(client: GitHubClient):
    """Poll dispatch repository for new issues and process them"""
    logger.info(f"Polling {DISPATCH_REPO} for new agent tasks...")
    
    try:
        # Get issues with 'copilot-agent' label that are not yet processed
        issues = client.get(
            f"/repos/{DISPATCH_REPO}/issues"
            f"?labels=copilot-agent"
            f"&state=open"
            f"&sort=created"
            f"&direction=asc"
        )
        
        logger.info(f"Found {len(issues)} open agent task issues")
        
        for issue in issues:
            issue_number = issue.get("number")
            if not issue_number:
                logger.warning("Issue missing number field, skipping")
                continue
            
            issue_labels = [
                label.get("name", "")
                for label in issue.get("labels", [])
                if isinstance(label, dict)
            ]
            
            # Skip if already processed
            if "agent-processed" in issue_labels or "agent-failed" in issue_labels:
                continue
            
            logger.info(f"Processing issue #{issue_number}: {issue['title']}")
            
            # Extract task metadata
            metadata = extract_task_metadata(issue.get("body", ""))
            if not metadata:
                logger.warning(f"No valid task metadata in issue #{issue_number}, skipping")
                comment_on_issue(
                    client,
                    DISPATCH_REPO,
                    issue_number,
                    "❌ Could not extract task metadata from issue body. "
                    "Please ensure the issue was created by the Handsfree backend "
                    "with proper metadata."
                )
                mark_issue_processed(client, DISPATCH_REPO, issue_number, "agent-failed")
                continue
            
            # Process task
            try:
                task_result = process_task(metadata)
                
                # Create PR
                pr_url = create_pull_request(
                    client,
                    TARGET_REPO,
                    metadata,
                    task_result,
                    issue_number,
                    DISPATCH_REPO
                )
                
                if pr_url:
                    # Success - comment and label
                    comment_on_issue(
                        client,
                        DISPATCH_REPO,
                        issue_number,
                        f"✅ Task processed successfully!\n\n"
                        f"**Pull Request Created**: {pr_url}\n\n"
                        f"The PR has been opened in the target repository "
                        f"with correlation metadata. "
                        f"The Handsfree backend will automatically correlate "
                        f"this PR to the task."
                    )
                    mark_issue_processed(client, DISPATCH_REPO, issue_number)
                else:
                    # PR creation failed
                    comment_on_issue(
                        client,
                        DISPATCH_REPO,
                        issue_number,
                        "❌ Failed to create pull request. Check agent runner logs for details."
                    )
                    mark_issue_processed(client, DISPATCH_REPO, issue_number, "agent-failed")
            
            except (requests.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Error processing task: {e}", exc_info=True)
                comment_on_issue(
                    client,
                    DISPATCH_REPO,
                    issue_number,
                    f"❌ Task processing failed: {str(e)}\n\n"
                    f"Check agent runner logs for details."
                )
                mark_issue_processed(client, DISPATCH_REPO, issue_number, "agent-failed")
    
    except requests.HTTPError as e:
        logger.error(f"Error fetching issues: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Error parsing issue data: {e}", exc_info=True)


def main():
    """Main runner loop"""
    logger.info("Starting agent runner...")
    
    # Validate configuration
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable is required")
        return
    
    if not DISPATCH_REPO:
        logger.error("DISPATCH_REPO environment variable is required (format: owner/repo)")
        return
    
    if not TARGET_REPO:
        logger.error("TARGET_REPO environment variable is required (format: owner/repo)")
        return
    
    logger.info("Configuration:")
    logger.info(f"  Dispatch repo: {DISPATCH_REPO}")
    logger.info(f"  Target repo: {TARGET_REPO}")
    logger.info(f"  Poll interval: {POLL_INTERVAL} seconds")
    
    # Initialize GitHub client
    client = GitHubClient(GITHUB_TOKEN)
    
    # Test authentication
    try:
        user = client.get("/user")
        logger.info(f"Authenticated as: {user.get('login')}")
    except requests.HTTPError as e:
        logger.error(f"Authentication failed: {e}")
        return
    
    # Main loop
    logger.info("Entering main polling loop...")
    while True:
        try:
            poll_dispatch_issues(client)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
        
        logger.info(f"Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
