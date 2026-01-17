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
from datetime import datetime, timedelta
from pathlib import Path

from github import Github
from github.GithubException import GithubException

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
DISPATCH_REPO = os.environ.get('DISPATCH_REPO', 'endomorphosis/lift_coding_dispatch')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL_SECONDS', '30'))
AGENT_NAME = os.environ.get('AGENT_NAME', 'custom-agent')
WORKSPACE_DIR = Path('/workspace')


def extract_task_metadata(issue_body: str) -> dict:
    """Extract task metadata from issue body."""
    metadata = {
        'task_id': None,
        'instruction': None,
        'target_repo': None,
    }
    
    # Extract task_id from metadata comment
    metadata_match = re.search(
        r'<!-- agent_task_metadata\s+(.*?)\s*-->',
        issue_body,
        re.DOTALL
    )
    if metadata_match:
        try:
            meta = json.loads(metadata_match.group(1))
            metadata['task_id'] = meta.get('task_id')
        except json.JSONDecodeError:
            logger.warning("Failed to parse agent_task_metadata JSON")
    
    # Extract instruction (look for ## Instruction section)
    instruction_match = re.search(
        r'## Instruction\s*\n+(.*?)(?:\n##|\Z)',
        issue_body,
        re.DOTALL | re.IGNORECASE
    )
    if instruction_match:
        metadata['instruction'] = instruction_match.group(1).strip()
    
    # Extract target repository
    repo_match = re.search(
        r'Target Repository:\s*([^\s\n]+)',
        issue_body
    )
    if repo_match:
        metadata['target_repo'] = repo_match.group(1)
    
    return metadata


def process_task(issue, metadata: dict) -> bool:
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
        
        # TODO: Implement your actual task processing logic here
        # Examples:
        # - Clone the target repository
        # - Use an LLM to understand the instruction and generate code
        # - Make the requested changes
        # - Run tests to verify changes
        
        # For this example, we'll just create a placeholder change
        target_repo = metadata.get('target_repo', DISPATCH_REPO)
        instruction = metadata.get('instruction', issue.title)
        
        # Simulate work (placeholder - remove in production)
        # In a real implementation, this is where you would process the task
        
        # Create a PR with correlation metadata
        # In a real implementation, you would:
        # 1. Clone the target repository
        # 2. Create a branch
        # 3. Make changes based on the instruction
        # 4. Commit and push changes
        # 5. Create a PR using GitHub API
        
        # For now, just log success
        logger.info(f"Task processed successfully: {issue.number}")
        
        # Create correlation comment
        task_id = metadata.get('task_id')
        correlation_metadata = f'<!-- agent_task_metadata {{"task_id": "{task_id}"}} -->' if task_id else ''
        
        issue.create_comment(
            f"✅ {AGENT_NAME} completed processing this task.\n\n"
            f"**Next steps**: A pull request should be created with the correlation metadata:\n"
            f"```markdown\n{correlation_metadata}\nFixes #{issue.number}\n```"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process task: {e}", exc_info=True)
        
        try:
            issue.create_comment(
                f"❌ {AGENT_NAME} failed to process this task: {str(e)}"
            )
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
                state='open',
                labels=['copilot-agent'],
                sort='created',
                direction='asc'
            )
            
            for issue in issues:
                # Skip if already processed
                if issue.number in processed_issues:
                    continue
                
                logger.info(f"Found new dispatch issue: #{issue.number} - {issue.title}")
                
                # Extract task metadata
                metadata = extract_task_metadata(issue.body)
                
                if not metadata.get('task_id'):
                    logger.warning(f"Issue #{issue.number} missing task_id, skipping")
                    continue
                
                # Process the task
                success = process_task(issue, metadata)
                
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


if __name__ == '__main__':
    main()
