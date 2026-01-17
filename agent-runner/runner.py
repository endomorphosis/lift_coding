#!/usr/bin/env python3
"""
Custom agent runner that polls dispatch repository and processes tasks.
"""

import json
import logging
import os
import re
import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from github import Github
from github.GithubException import GithubException

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
DISPATCH_REPO = os.environ.get("DISPATCH_REPO", "endomorphosis/lift_coding_dispatch")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
AGENT_NAME = os.environ.get("AGENT_NAME", "custom-agent")
WORKSPACE_DIR = Path("/workspace")


def extract_task_metadata(issue_body: str) -> dict:
    """Extract task metadata from issue body."""
    metadata = {
        "task_id": None,
        "instruction": None,
        "target_repo": None,
    }

    # Extract task_id from metadata comment
    metadata_match = re.search(r"<!-- agent_task_metadata\s+(.*?)\s*-->", issue_body, re.DOTALL)
    if metadata_match:
        try:
            meta = json.loads(metadata_match.group(1))
            metadata["task_id"] = meta.get("task_id")
        except json.JSONDecodeError:
            logger.warning("Failed to parse agent_task_metadata JSON")

    # Extract instruction (look for ## Instruction section)
    instruction_match = re.search(
        r"## Instruction\s*\n+(.*?)(?:\n##|\Z)", issue_body, re.DOTALL | re.IGNORECASE
    )
    if instruction_match:
        metadata["instruction"] = instruction_match.group(1).strip()

    # Extract target repository
    repo_match = re.search(r"Target Repository:\s*([^\s\n]+)", issue_body)
    if repo_match:
        metadata["target_repo"] = repo_match.group(1)

    return metadata


def clone_or_update_repo(repo_url: str, repo_name: str, gh_token: str) -> Path:
    """
    Clone a repository or update if it already exists.

    Returns the path to the cloned repository.

    Security Note: This function embeds the GitHub token in the clone URL for
    authentication. The token is not logged and is only used for git operations.
    For production use, consider using SSH keys or GitHub App authentication.
    """
    repo_path = WORKSPACE_DIR / repo_name

    # Validate inputs
    if not repo_url or not repo_name:
        raise ValueError("Repository URL and name are required")

    # Add token to URL for authentication
    if "github.com" in repo_url:
        auth_url = repo_url.replace("https://", f"https://{gh_token}@")
    else:
        auth_url = repo_url

    if repo_path.exists():
        logger.info(f"Repository already exists at {repo_path}, updating...")
        try:
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # Try master instead of main
            try:
                subprocess.run(
                    ["git", "reset", "--hard", "origin/master"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to update repo: {e}")
    else:
        logger.info(f"Cloning repository to {repo_path}...")
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", auth_url, str(repo_path)], check=True, capture_output=True, text=True
        )

    return repo_path


def get_task_id_prefix(task_id: str) -> str:
    """Extract a short prefix from task_id for branch naming."""
    # Take first 8 chars of task_id for branch name
    return task_id[:8] if task_id else "unknown"


def create_or_checkout_branch(repo_path: Path, branch_name: str) -> bool:
    """
    Create a new branch or checkout existing one.

    Returns True if branch was created, False if it already existed.
    """
    try:
        # Check if branch exists locally
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info(f"Branch {branch_name} already exists, checking out...")
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return False
        else:
            logger.info(f"Creating new branch {branch_name}...")
            # Ensure we're on main/master first
            try:
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["git", "checkout", "master"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create/checkout branch: {e}")
        raise


def create_trace_file(repo_path: Path, task_id: str, instruction: str, issue_number: int) -> Path:
    """
    Create a trace file with task metadata.

    Returns the path to the created file.
    """
    task_id_prefix = get_task_id_prefix(task_id)
    trace_dir = repo_path / "agent-tasks"
    trace_dir.mkdir(exist_ok=True)

    trace_file = trace_dir / f"{task_id_prefix}.md"

    # Create correlation metadata comment
    correlation_metadata = f'<!-- agent_task_metadata {{"task_id": "{task_id}"}} -->'

    content = f"""# Agent Task Trace

{correlation_metadata}

## Task Information

- **Task ID**: `{task_id}`
- **Issue**: #{issue_number}
- **Agent**: {AGENT_NAME}
- **Created**: {datetime.utcnow().isoformat()}Z
- **Status**: Processed

## Instruction

{instruction}

## Changes

This file serves as a trace of the agent task processing. In a production implementation,
the agent would make actual code changes based on the instruction above.

## Next Steps

1. Review the changes made by the agent
2. Run tests to verify the changes
3. Merge the pull request if everything looks good
"""

    trace_file.write_text(content)
    logger.info(f"Created trace file at {trace_file}")

    return trace_file


def commit_and_push(repo_path: Path, branch_name: str, message: str) -> None:
    """Commit all changes and push to remote."""
    # Configure git if not already configured
    try:
        subprocess.run(
            ["git", "config", "user.email", f"{AGENT_NAME}@agent-runner.local"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", AGENT_NAME],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to configure git: {e}")

    # Add all changes
    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True, text=True)

    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repo_path, capture_output=True
    )

    if result.returncode != 0:
        # There are changes to commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Changes committed")
    else:
        logger.info("No changes to commit")

    # Push to remote
    subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(f"Pushed branch {branch_name} to remote")


def find_existing_pr(gh, repo, branch_name: str):
    """Find existing PR for the given branch."""
    try:
        # Try with head prefix first (for same repo)
        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch_name}")
        for pr in pulls:
            return pr

        # If not found, try without prefix (works for forks and same repo)
        pulls = repo.get_pulls(state="open", head=branch_name)
        for pr in pulls:
            return pr

        return None
    except Exception as e:
        logger.warning(f"Error checking for existing PR: {e}")
        return None


def create_or_update_pr(gh, repo, branch_name: str, title: str, body: str, issue_number: int):
    """Create a new PR or update existing one."""
    existing_pr = find_existing_pr(gh, repo, branch_name)

    if existing_pr:
        logger.info(f"PR already exists: #{existing_pr.number}, updating...")
        existing_pr.edit(title=title, body=body)
        existing_pr.create_issue_comment(
            f"🔄 Updated by {AGENT_NAME} at {datetime.utcnow().isoformat()}Z"
        )
        return existing_pr
    else:
        logger.info("Creating new PR...")
        # Determine base branch
        default_branch = repo.default_branch
        pr = repo.create_pull(title=title, body=body, head=branch_name, base=default_branch)
        logger.info(f"Created PR: #{pr.number}")
        return pr


def process_task(gh, issue, metadata: dict) -> bool:
    """
    Process an agent task.

    Returns True if successful, False otherwise.
    """
    logger.info(f"Processing task: {issue.title}")
    logger.info(f"Task ID: {metadata.get('task_id')}")
    logger.info(f"Instruction: {metadata.get('instruction')}")

    try:
        # Comment on issue that processing started
        issue.create_comment(
            f"🤖 {AGENT_NAME} started processing this task at {datetime.utcnow().isoformat()}Z"
        )

        # Extract task information
        task_id = metadata.get("task_id")
        if not task_id:
            raise ValueError("Task ID is required")

        target_repo_name = metadata.get("target_repo", DISPATCH_REPO)
        instruction = metadata.get("instruction", issue.title)

        # Get target repository
        target_repo = gh.get_repo(target_repo_name)
        repo_url = target_repo.clone_url
        repo_name = target_repo_name.replace("/", "_")

        # Clone or update repository
        repo_path = clone_or_update_repo(repo_url, repo_name, GITHUB_TOKEN)

        # Create branch name
        task_id_prefix = get_task_id_prefix(task_id)
        branch_name = f"agent-task-{task_id_prefix}"

        # Create or checkout branch
        create_or_checkout_branch(repo_path, branch_name)

        # Create trace file with correlation metadata
        create_trace_file(repo_path, task_id, instruction, issue.number)

        # Commit and push changes
        commit_message = f"Process agent task from dispatch issue #{issue.number}"
        commit_and_push(repo_path, branch_name, commit_message)

        # Create PR with correlation metadata
        pr_title = f"Agent task: {issue.title}"

        correlation_metadata = f'<!-- agent_task_metadata {{"task_id": "{task_id}"}} -->'

        # Construct the issue reference
        # If target repo is different from dispatch repo, use full reference
        if target_repo_name != DISPATCH_REPO:
            issue_ref = f"{DISPATCH_REPO}#{issue.number}"
        else:
            issue_ref = f"#{issue.number}"

        pr_body = f"""{correlation_metadata}

Automated changes from agent task

Fixes {issue_ref}

## Task Information

- **Task ID**: `{task_id}`
- **Agent**: {AGENT_NAME}
- **Processed**: {datetime.utcnow().isoformat()}Z

## Instruction

{instruction}

## Changes

This PR contains a trace file documenting the agent task processing. In a production
implementation, the agent would make actual code changes based on the instruction.

## Review Checklist

- [ ] Review the trace file in `agent-tasks/`
- [ ] Verify the changes are appropriate
- [ ] Run tests to ensure nothing is broken
- [ ] Merge when ready
"""

        pr = create_or_update_pr(gh, target_repo, branch_name, pr_title, pr_body, issue.number)

        # Mark issue as processed
        issue.create_comment(
            f"✅ {AGENT_NAME} completed processing this task.\n\n"
            f"Pull request created: {pr.html_url}"
        )

        # Add processed label if it exists
        try:
            issue.add_to_labels("processed")
            logger.info("Added 'processed' label to issue")
        except Exception as e:
            logger.warning(f"Failed to add 'processed' label (label may not exist): {e}")

        logger.info(f"Task processed successfully: {issue.number}")
        return True

    except Exception as e:
        logger.error(f"Failed to process task: {e}", exc_info=True)

        try:
            issue.create_comment(f"❌ {AGENT_NAME} failed to process this task: {str(e)}")
        except Exception:
            logger.error("Failed to post error comment to issue")

        return False


def main():
    """Main agent runner loop."""
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable is required")
        return

    logger.info(f"Starting {AGENT_NAME}")
    logger.info(f"Monitoring dispatch repository: {DISPATCH_REPO}")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")

    # Initialize GitHub client
    gh = Github(GITHUB_TOKEN)

    # Track processed issues to avoid duplicate work
    # Using deque with maxlen for automatic LRU eviction
    processed_issues = deque(maxlen=1000)

    while True:
        try:
            # Get the dispatch repository
            repo = gh.get_repo(DISPATCH_REPO)

            # Get open issues with copilot-agent label
            issues = repo.get_issues(
                state="open", labels=["copilot-agent"], sort="created", direction="asc"
            )

            for issue in issues:
                # Skip if already processed
                if issue.number in processed_issues:
                    continue

                logger.info(f"Found new dispatch issue: #{issue.number} - {issue.title}")

                # Extract task metadata
                metadata = extract_task_metadata(issue.body)

                if not metadata.get("task_id"):
                    logger.warning(f"Issue #{issue.number} missing task_id, skipping")
                    continue

                # Process the task
                success = process_task(gh, issue, metadata)

                if success:
                    # Mark as processed (deque automatically evicts old items when full)
                    processed_issues.append(issue.number)

                    # Optional: close the issue or add a label
                    # issue.edit(state='closed')
                    # issue.add_to_labels('processed')

        except GithubException as e:
            logger.error(f"GitHub API error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)

        # Wait before next poll
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
