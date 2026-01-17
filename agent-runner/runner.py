#!/usr/bin/env python3
"""
Custom agent runner that polls dispatch repository and processes tasks.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

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


def clone_repository(repo_full_name: str, target_dir: Path) -> bool:
    """Clone a repository to the specified directory."""
    try:
        # Use https URL without embedding token
        clone_url = f"https://github.com/{repo_full_name}.git"

        logger.info(f"Cloning {repo_full_name} to {target_dir}")

        # Configure git credential helper to use the token from environment
        subprocess.run(
            ["git", "clone", clone_url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

        # Configure git to use token for push operations
        subprocess.run(
            ["git", "config", "--local", "credential.helper", ""],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_full_name}.git",
            ],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {getattr(e, 'stderr', str(e))}")
        return False


def create_and_push_branch(repo_dir: Path, branch_name: str) -> bool:
    """Create a new branch and ensure it doesn't already exist."""
    try:
        # Configure git
        subprocess.run(
            ["git", "config", "user.name", AGENT_NAME],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", f"{AGENT_NAME}@agent-runner.local"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Check if branch already exists on remote
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            logger.info(f"Branch {branch_name} already exists remotely, checking it out")
            subprocess.run(
                ["git", "fetch", "origin", branch_name],
                cwd=repo_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", branch_name], cwd=repo_dir, check=True, capture_output=True
            )
        else:
            logger.info(f"Creating new branch {branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=repo_dir,
                check=True,
                capture_output=True,
            )

        return True
    except subprocess.CalledProcessError as e:
        error_msg = getattr(e, "stderr", "") or str(e)
        logger.error(f"Failed to create/checkout branch: {error_msg}")
        return False


def create_trace_file(repo_dir: Path, task_id: str, issue_number: int, instruction: str) -> bool:
    """Create a trace file with task metadata."""
    try:
        # Create agent-tasks directory if it doesn't exist
        tasks_dir = repo_dir / "agent-tasks"
        tasks_dir.mkdir(exist_ok=True)

        # Create a short prefix from task_id (first 8 chars)
        task_id_prefix = task_id[:8] if task_id and len(task_id) >= 8 else str(issue_number)
        trace_file = tasks_dir / f"{task_id_prefix}.md"

        # Generate trace content
        trace_content = f"""# Agent Task Trace: {task_id_prefix}

## Task Metadata
- **Task ID**: {task_id}
- **Issue Number**: #{issue_number}
- **Started At**: {datetime.utcnow().isoformat()}Z
- **Agent**: {AGENT_NAME}

## Instruction
{instruction}

## Correlation Metadata
<!-- agent_task_metadata {{"task_id": "{task_id}"}} -->

## Status
Processing completed at {datetime.utcnow().isoformat()}Z
"""

        # Write trace file
        trace_file.write_text(trace_content)
        logger.info(f"Created trace file: {trace_file}")

        return True
    except Exception as e:
        logger.error(f"Failed to create trace file: {e}")
        return False


def apply_patches_from_instruction(repo_dir: Path, instruction: str) -> bool:
    """Apply any fenced diff/patch blocks found in the instruction.

    This uses the local helper script `apply_instruction.py` so behavior matches
    the GitHub Actions workflow.
    """
    try:
        helper_path = Path(__file__).resolve().parent / "apply_instruction.py"
        if not helper_path.exists():
            logger.warning("apply_instruction.py not found; skipping patch application")
            return True

        with NamedTemporaryFile("w", delete=False, suffix=".md") as temp_file:
            temp_file.write(instruction or "")
            instruction_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    "python",
                    str(helper_path),
                    "--instruction-file",
                    instruction_path,
                    "--repo-dir",
                    str(repo_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode in (0,):
                stdout = (result.stdout or "").strip()
                if stdout and stdout != "no patches found":
                    logger.info(stdout)
                return True

            stderr = (result.stderr or result.stdout or "").strip()
            logger.error(f"Failed applying patches from instruction: {stderr}")
            return False
        finally:
            try:
                os.unlink(instruction_path)
            except OSError:
                pass
    except Exception as e:
        logger.error(f"Unexpected error applying patches: {e}")
        return False


def commit_and_push_changes(repo_dir: Path, branch_name: str, commit_message: str) -> bool:
    """Commit and push changes to the remote repository."""
    try:
        # Stage all changes
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_dir, capture_output=True
        )

        if result.returncode == 0:
            logger.info("No changes to commit")
            return True

        # Commit changes
        subprocess.run(
            ["git", "commit", "-m", commit_message], cwd=repo_dir, check=True, capture_output=True
        )

        # Push changes
        subprocess.run(
            ["git", "push", "origin", branch_name], cwd=repo_dir, check=True, capture_output=True
        )

        logger.info(f"Committed and pushed changes to {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = getattr(e, "stderr", "") or str(e)
        logger.error(f"Failed to commit/push changes: {error_msg}")
        return False


def create_pull_request(
    gh_client, repo_full_name: str, branch_name: str, issue: object, task_id: str
) -> bool:
    """Create or update a pull request with correlation metadata."""
    try:
        repo = gh_client.get_repo(repo_full_name)

        # Check if PR already exists for this branch
        existing_prs = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch_name}")

        pr_title = f"Agent task: {issue.title}"

        # Build PR body with correlation metadata
        dispatch_repo = issue.repository.full_name
        task_id_short = task_id[:8] if task_id and len(task_id) >= 8 else str(issue.number)
        pr_body = f"""Automated changes from agent task

<!-- agent_task_metadata {{"task_id": "{task_id}"}} -->

Fixes {dispatch_repo}#{issue.number}

## Task Details
- **Task ID**: {task_id}
- **Dispatch Issue**: {dispatch_repo}#{issue.number}
- **Agent**: {AGENT_NAME}
- **Processed At**: {datetime.utcnow().isoformat()}Z

## Changes
This PR was automatically generated by the agent runner in response to a dispatch issue.

See `agent-tasks/{task_id_short}.md` for task trace.
"""

        # Check if PR already exists
        pr = None
        for existing_pr in existing_prs:
            pr = existing_pr
            logger.info(f"Updating existing PR #{pr.number}")
            pr.edit(title=pr_title, body=pr_body)
            break

        if not pr:
            # Get the default branch dynamically
            default_branch = repo.default_branch

            # Create new PR
            logger.info(f"Creating new PR from {branch_name} to {default_branch}")
            pr = repo.create_pull(
                title=pr_title, body=pr_body, head=branch_name, base=default_branch
            )
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")

        return True
    except GithubException as e:
        logger.error(f"Failed to create/update PR: {e}")
        return False


def process_task(gh_client, issue, metadata: dict) -> bool:
    """
    Process an agent task by creating a branch, committing changes, and opening a PR.

    Returns True if successful, False otherwise.
    """
    logger.info(f"Processing task: {issue.title}")
    logger.info(f"Task ID: {metadata.get('task_id')}")
    logger.info(f"Instruction: {metadata.get('instruction')}")

    repo_dir = None

    try:
        # Comment on issue that processing started
        issue.create_comment(
            f"🤖 {AGENT_NAME} started processing this task at {datetime.utcnow().isoformat()}Z"
        )

        # Extract task information
        task_id = metadata.get("task_id")
        instruction = metadata.get("instruction", issue.title)
        target_repo = metadata.get("target_repo")

        if not task_id:
            raise ValueError("Missing task_id in metadata")

        # Determine target repository (default to dispatch repo)
        if not target_repo:
            target_repo = DISPATCH_REPO
            logger.info(f"No target_repo specified, using dispatch repo: {target_repo}")

        # Create branch name from task_id prefix
        task_id_prefix = task_id[:8] if task_id and len(task_id) >= 8 else task_id
        branch_name = f"agent-task-{task_id_prefix}"

        # Prepare workspace directory
        WORKSPACE_DIR.mkdir(exist_ok=True)
        repo_dir = WORKSPACE_DIR / target_repo.replace("/", "_")

        # Remove existing directory if present
        if repo_dir.exists():
            shutil.rmtree(repo_dir)

        # Clone the target repository
        if not clone_repository(target_repo, repo_dir):
            raise RuntimeError("Failed to clone repository")

        # Create or checkout branch
        if not create_and_push_branch(repo_dir, branch_name):
            raise RuntimeError("Failed to create/checkout branch")

        # Deterministic mode: apply any diff/patch blocks embedded in the instruction.
        # If patch application fails, abort so we don't create a misleading PR.
        if not apply_patches_from_instruction(repo_dir, instruction):
            raise RuntimeError("Failed to apply patches from instruction")

        # Create trace file with task metadata
        if not create_trace_file(repo_dir, task_id, issue.number, instruction):
            raise RuntimeError("Failed to create trace file")

        # Commit and push changes
        commit_message = (
            f"Process agent task from dispatch issue #{issue.number}\n\nTask ID: {task_id}"
        )
        if not commit_and_push_changes(repo_dir, branch_name, commit_message):
            raise RuntimeError("Failed to commit/push changes")

        # Create pull request with correlation metadata
        if not create_pull_request(gh_client, target_repo, branch_name, issue, task_id):
            raise RuntimeError("Failed to create pull request")

        logger.info(f"Task processed successfully: {issue.number}")

        # Comment on issue with success
        issue.create_comment(
            f"✅ {AGENT_NAME} completed processing this task.\n\n"
            f"A pull request has been created with correlation metadata in the target repository."
        )

        # Add processed label to issue
        try:
            issue.add_to_labels("processed")
        except Exception as e:
            logger.warning(f"Could not add 'processed' label: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to process task: {e}", exc_info=True)

        try:
            issue.create_comment(f"❌ {AGENT_NAME} failed to process this task: {str(e)}")
        except Exception:
            logger.error("Failed to post error comment to issue")

        return False
    finally:
        # Cleanup workspace
        if repo_dir and repo_dir.exists():
            try:
                shutil.rmtree(repo_dir)
                logger.info(f"Cleaned up workspace: {repo_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace: {e}")


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
