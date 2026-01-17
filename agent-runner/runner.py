#!/usr/bin/env python3
"""
Simple agent runner that polls GitHub for dispatch issues.

This is a minimal example demonstrating how to:
1. Monitor a GitHub repository for dispatch issues (labeled 'copilot-agent')
2. Extract task metadata from issue bodies
3. Process tasks (placeholder logic - extend as needed)
4. Create PRs with correlation metadata for backend tracking

For production use:
- Implement actual task processing logic
- Add proper error handling and retries
- Use GitHub App authentication for higher rate limits
- Consider using webhooks instead of polling
- Add concurrent task processing
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Any

import requests

# Configuration from environment variables
DISPATCH_REPO = os.getenv("AGENT_DISPATCH_REPO", "endomorphosis/lift_coding_dispatch")
TARGET_REPO = os.getenv("AGENT_TARGET_REPO", "endomorphosis/lift_coding")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
POLL_INTERVAL = int(os.getenv("AGENT_POLL_INTERVAL", "60"))  # seconds
PROCESSED_MARKER = os.getenv("AGENT_PROCESSED_LABEL", "agent-processing")

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN environment variable is required", file=sys.stderr)
    sys.exit(1)


def get_headers() -> dict[str, str]:
    """Get GitHub API request headers."""
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_dispatch_issues() -> list[dict[str, Any]]:
    """
    Fetch open issues with copilot-agent label from dispatch repository.
    
    Returns:
        List of issue objects from GitHub API.
    """
    url = f"https://api.github.com/repos/{DISPATCH_REPO}/issues"
    params = {
        "labels": "copilot-agent",
        "state": "open",
        "sort": "created",
        "direction": "asc",
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=30)
        resp.raise_for_status()
        issues = resp.json()
        
        # Filter out issues already being processed
        return [
            issue for issue in issues
            if not any(label["name"] == PROCESSED_MARKER for label in issue.get("labels", []))
        ]
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch dispatch issues: {e}", file=sys.stderr)
        return []


def extract_task_metadata(issue_body: str) -> dict[str, Any]:
    """
    Extract task metadata from issue body.
    
    Looks for metadata in two formats:
    1. HTML comment: <!-- agent_task_metadata {...} -->
    2. Structured fields: task_id: xxx, user_id: yyy
    
    Args:
        issue_body: The issue body text.
    
    Returns:
        Dictionary with task_id, user_id, and provider.
    """
    metadata = {
        "task_id": "unknown",
        "user_id": "unknown",
        "provider": "github_issue_dispatch",
    }
    
    # Try to extract from HTML comment
    match = re.search(
        r"<!--\s*agent_task_metadata\s*\n?(.*?)\n?-->",
        issue_body,
        re.DOTALL | re.IGNORECASE
    )
    if match:
        try:
            parsed = json.loads(match.group(1))
            metadata.update(parsed)
            return metadata
        except json.JSONDecodeError as e:
            print(f"WARNING: Failed to parse metadata JSON: {e}")
    
    # Fallback: extract from structured fields
    task_id_match = re.search(r"(?i)task[_ ]id:\s*([\w-]+)", issue_body)
    user_id_match = re.search(r"(?i)user[_ ]id:\s*([\w-]+)", issue_body)
    
    if task_id_match:
        metadata["task_id"] = task_id_match.group(1)
    if user_id_match:
        metadata["user_id"] = user_id_match.group(1)
    
    return metadata


def add_issue_label(issue_number: int, label: str) -> bool:
    """
    Add a label to an issue.
    
    Args:
        issue_number: The issue number.
        label: Label name to add.
    
    Returns:
        True if successful, False otherwise.
    """
    url = f"https://api.github.com/repos/{DISPATCH_REPO}/issues/{issue_number}/labels"
    try:
        resp = requests.post(
            url,
            headers=get_headers(),
            json={"labels": [label]},
            timeout=30
        )
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Failed to add label '{label}' to issue #{issue_number}: {e}")
        return False


def comment_on_issue(issue_number: int, comment: str) -> bool:
    """
    Post a comment on an issue.
    
    Args:
        issue_number: The issue number.
        comment: Comment text to post.
    
    Returns:
        True if successful, False otherwise.
    """
    url = f"https://api.github.com/repos/{DISPATCH_REPO}/issues/{issue_number}/comments"
    try:
        resp = requests.post(
            url,
            headers=get_headers(),
            json={"body": comment},
            timeout=30
        )
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to comment on issue #{issue_number}: {e}", file=sys.stderr)
        return False


def process_task(issue: dict[str, Any]) -> bool:
    """
    Process a dispatch issue and create a PR in the target repository.
    
    This is a placeholder implementation that demonstrates the workflow.
    In production, replace this with actual task processing logic:
    - Clone the target repository
    - Make code changes based on the instruction
    - Commit and push changes
    - Create a PR with correlation metadata
    
    Args:
        issue: GitHub issue object.
    
    Returns:
        True if processing succeeded, False otherwise.
    """
    issue_number = issue["number"]
    title = issue["title"]
    body = issue.get("body", "")
    
    print(f"\n{'='*80}")
    print(f"Processing issue #{issue_number}: {title}")
    print(f"{'='*80}")
    
    # Mark as being processed
    add_issue_label(issue_number, PROCESSED_MARKER)
    
    # Extract metadata
    metadata = extract_task_metadata(body)
    task_id = metadata["task_id"]
    user_id = metadata["user_id"]
    provider = metadata["provider"]
    
    print(f"Task metadata:")
    print(f"  - Task ID: {task_id}")
    print(f"  - User ID: {user_id}")
    print(f"  - Provider: {provider}")
    
    # =================================================================
    # TODO: Implement actual task processing logic here
    # =================================================================
    # Examples:
    # 1. Clone target repository
    # 2. Create a feature branch (e.g., "agent-task-{task_id}")
    # 3. Make code changes based on instruction
    # 4. Commit changes with descriptive message
    # 5. Push branch to GitHub
    # 6. Create PR using GitHub API
    # =================================================================
    
    # For this example, we'll simulate the workflow
    branch_name = f"agent-task-{task_id}"
    
    print(f"\nSimulated workflow:")
    print(f"  1. Would clone {TARGET_REPO}")
    print(f"  2. Would create branch: {branch_name}")
    print(f"  3. Would process instruction: {title}")
    print(f"  4. Would commit changes")
    print(f"  5. Would push to GitHub")
    print(f"  6. Would create PR with correlation metadata")
    
    # Prepare PR body with correlation metadata
    # CRITICAL: This metadata format is required for backend correlation
    pr_body = f"""# Agent Task: {title}

This PR was automatically created by the agent runner to address the task
dispatched in issue #{issue_number}.

## Task Details

- **Task ID:** `{task_id}`
- **User ID:** `{user_id}`
- **Provider:** `{provider}`
- **Dispatch Issue:** https://github.com/{DISPATCH_REPO}/issues/{issue_number}

## Changes

*[Task processing placeholder - implement actual changes]*

## Correlation Metadata

<!-- agent_task_metadata
{json.dumps(metadata, indent=2)}
-->
"""
    
    print(f"\nPR body prepared (length: {len(pr_body)} chars)")
    
    # In a real implementation, you would:
    # 1. Create the PR using GitHub API or PyGithub
    # 2. Store the PR URL for status updates
    
    # Simulated success
    pr_url = f"https://github.com/{TARGET_REPO}/pull/[SIMULATED]"
    
    # Comment on dispatch issue with status
    success_comment = f"""✅ **Task processed successfully**

- Task ID: `{task_id}`
- Branch: `{branch_name}`
- Pull Request: {pr_url} *(simulated - implement actual PR creation)*

Processed at: {datetime.utcnow().isoformat()}Z
Processed by: agent-runner (example implementation)

**Note:** This is a demonstration. Implement actual task processing logic in `process_task()`.
"""
    
    comment_on_issue(issue_number, success_comment)
    
    print(f"\n✓ Task {task_id} processing complete")
    return True


def main():
    """Main polling loop."""
    print("=" * 80)
    print("Agent Runner Starting")
    print("=" * 80)
    print(f"Dispatch repository: {DISPATCH_REPO}")
    print(f"Target repository:   {TARGET_REPO}")
    print(f"Poll interval:       {POLL_INTERVAL}s")
    print(f"Processing label:    {PROCESSED_MARKER}")
    print("=" * 80)
    print("\nWaiting for dispatch issues...")
    print("(Press Ctrl+C to stop)\n")
    
    processed_issues = set()
    
    while True:
        try:
            issues = get_dispatch_issues()
            
            if issues:
                print(f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Found {len(issues)} unprocessed dispatch issue(s)")
            
            for issue in issues:
                issue_id = issue["id"]
                
                # Skip if already processed in this session
                if issue_id in processed_issues:
                    continue
                
                try:
                    if process_task(issue):
                        processed_issues.add(issue_id)
                except Exception as e:
                    print(f"\nERROR: Failed to process issue #{issue['number']}: {e}", 
                          file=sys.stderr)
                    # Comment on issue about failure
                    error_comment = f"""❌ **Task processing failed**

Error: {str(e)}

Please check the agent runner logs and retry if appropriate.
"""
                    comment_on_issue(issue["number"], error_comment)
            
            # Sleep until next poll
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\nShutting down agent runner...")
            break
        except Exception as e:
            print(f"\nERROR: Unexpected error in main loop: {e}", file=sys.stderr)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
