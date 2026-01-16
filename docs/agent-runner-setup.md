# Agent Runner Setup Guide

This guide explains how to set up an external agent runner that processes dispatched agent tasks from the HandsFree Dev Companion system.

## Overview

The HandsFree system can delegate tasks to external agents by creating GitHub issues in a dispatch repository. An external agent runner monitors these dispatch issues, performs the requested work, and creates pull requests with correlation metadata that the HandsFree backend uses to track task completion.

### How it Works

1. **Task Dispatch**: HandsFree creates a GitHub issue in the dispatch repository with:
   - A descriptive title (derived from the instruction)
   - A structured body containing task metadata
   - A `copilot-agent` label for easy filtering
   - Hidden JSON metadata comment for correlation

2. **Agent Processing**: An external agent runner:
   - Monitors the dispatch repository for new issues labeled `copilot-agent`
   - Reads the task instruction and metadata
   - Performs the requested work (code changes, analysis, etc.)
   - Creates a pull request with correlation metadata

3. **Task Correlation**: HandsFree receives the PR webhook and:
   - Extracts the task_id from the PR body metadata or issue reference
   - Updates the agent task state to `completed`
   - Stores the PR URL in the task trace
   - Emits a completion notification to the user

## Runner Options

You can choose from several agent runner implementations based on your deployment needs:

### Option 1: GitHub Actions Workflow

**Best for**: Simple deployments, CI/CD integration, cloud-hosted runners

A GitHub Actions workflow that triggers on issue events and processes dispatch tasks using GitHub-hosted or self-hosted runners.

**Pros**:
- No infrastructure to maintain
- Native GitHub integration
- Built-in secrets management
- Easy to customize and extend

**Cons**:
- Requires public workflow or self-hosted runner for private repos
- Limited execution time (6 hours for public repos, configurable for self-hosted)
- GitHub Actions usage costs (for private repos on free plan)

See [GitHub Actions Example](#github-actions-workflow-example) below.

### Option 2: GitHub Copilot Agent

**Best for**: Organizations with GitHub Copilot for Business/Enterprise

If you have access to GitHub Copilot workspace agents, you can configure Copilot to monitor dispatch issues and perform work automatically.

**Pros**:
- Fully managed by GitHub
- AI-powered task understanding and execution
- No infrastructure needed

**Cons**:
- Requires GitHub Copilot for Business/Enterprise
- Less control over execution logic
- May require GitHub support to configure

**Setup**: Contact GitHub support to configure a Copilot agent for your dispatch repository. The agent should be instructed to monitor issues with the `copilot-agent` label and create PRs that reference the dispatch issue.

### Option 3: Custom Runner (Docker + Python)

**Best for**: On-premise deployments, custom workflows, advanced automation

A standalone service that polls the dispatch repository and processes tasks using custom logic or LLM integrations.

**Pros**:
- Full control over execution logic
- Can run on-premise or in any cloud
- Supports custom LLM providers
- Advanced error handling and retry logic

**Cons**:
- Infrastructure to maintain
- Need to handle GitHub API rate limits
- More complex setup and monitoring

See [Docker Compose Example](#docker-compose-custom-runner) below.

## Configuration Requirements

All runners need the following:

### 1. GitHub Authentication

Create a GitHub personal access token or GitHub App with the following permissions:

**For Personal Access Token**:
- `repo` (full control of private repositories)
  - Or `public_repo` (for public repositories only)
- `read:org` (if dispatch repo is in an organization)

**For GitHub App** (recommended for production):
- Repository permissions:
  - Issues: Read & Write
  - Pull Requests: Read & Write
  - Contents: Read & Write
  - Metadata: Read-only

**Security Best Practices**:
- Use a dedicated bot account, not a personal account
- Scope tokens to specific repositories when possible
- Rotate tokens regularly
- Use GitHub App authentication for better security and auditability

### 2. Dispatch Repository Access

The runner needs access to:
- **Dispatch Repository**: Where dispatch issues are created (e.g., `owner/lift_coding_dispatch`)
- **Target Repository**: Where pull requests will be created (often the same as dispatch repo)

### 3. Correlation Metadata Format

When creating a pull request, include correlation metadata in the PR body to link it back to the agent task:

**Method 1: Agent Task Metadata Comment** (recommended)
```markdown
<!-- agent_task_metadata {"task_id": "550e8400-e29b-41d4-a716-446655440000"} -->
```

**Method 2: Issue Reference**
```markdown
Fixes #123
```
or
```markdown
Closes #123
```
or
```markdown
Resolves #123
```

Where `#123` is the issue number of the dispatch issue in the dispatch repository.

**Note**: Method 1 is preferred as it works across repositories and is more explicit.

## GitHub Actions Workflow Example

Create `.github/workflows/agent-runner.yml` in your dispatch repository:

```yaml
name: Agent Runner

on:
  issues:
    types: [opened, labeled]

jobs:
  process-agent-task:
    # Only run if the issue has the copilot-agent label
    if: contains(github.event.issue.labels.*.name, 'copilot-agent')
    runs-on: ubuntu-latest
    
    permissions:
      issues: write
      pull-requests: write
      contents: write
    
    steps:
      - name: Checkout dispatch repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.AGENT_RUNNER_TOKEN }}
      
      - name: Extract task metadata
        id: metadata
        run: |
          # Parse issue body to extract task metadata
          ISSUE_BODY="${{ github.event.issue.body }}"
          
          # Extract task_id from metadata comment
          TASK_ID=$(echo "$ISSUE_BODY" | grep -oP '<!-- agent_task_metadata \K[^>]+' | jq -r '.task_id // empty')
          
          # Extract instruction
          INSTRUCTION=$(echo "$ISSUE_BODY" | sed -n '/## Instruction/,/##/p' | sed '1d;$d' | tr -d '\n')
          
          # Extract target repository if specified
          TARGET_REPO=$(echo "$ISSUE_BODY" | grep -oP 'Target Repository: \K[^\s]+' || echo "${{ github.repository }}")
          
          echo "task_id=$TASK_ID" >> $GITHUB_OUTPUT
          echo "instruction=$INSTRUCTION" >> $GITHUB_OUTPUT
          echo "target_repo=$TARGET_REPO" >> $GITHUB_OUTPUT
      
      - name: Comment on issue (processing started)
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.AGENT_RUNNER_TOKEN }}
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '🤖 Agent runner started processing this task...'
            });
      
      - name: Checkout target repository
        uses: actions/checkout@v4
        with:
          repository: ${{ steps.metadata.outputs.target_repo }}
          token: ${{ secrets.AGENT_RUNNER_TOKEN }}
          path: target-repo
      
      - name: Process task (example - customize this step)
        working-directory: target-repo
        run: |
          # This is a placeholder - replace with your actual agent logic
          # Examples:
          # - Run an LLM to generate code changes
          # - Execute a script that makes automated changes
          # - Call an external API or service
          
          echo "Processing instruction: ${{ steps.metadata.outputs.instruction }}"
          
          # Example: Create a simple change
          git config user.name "Agent Runner Bot"
          git config user.email "agent-runner@example.com"
          
          # Make your changes here (this is just an example)
          echo "# Agent Task Output" > AGENT_OUTPUT.md
          echo "" >> AGENT_OUTPUT.md
          echo "Task: ${{ steps.metadata.outputs.instruction }}" >> AGENT_OUTPUT.md
          echo "Processed at: $(date)" >> AGENT_OUTPUT.md
          
          git add AGENT_OUTPUT.md
          git commit -m "Process agent task from dispatch issue #${{ github.event.issue.number }}"
      
      - name: Create Pull Request
        working-directory: target-repo
        env:
          GH_TOKEN: ${{ secrets.AGENT_RUNNER_TOKEN }}
        run: |
          # Create a branch
          BRANCH_NAME="agent-task-${{ github.event.issue.number }}"
          git checkout -b "$BRANCH_NAME"
          git push origin "$BRANCH_NAME"
          
          # Create PR with correlation metadata
          PR_BODY="Automated changes from agent task

          Fixes ${{ github.repository }}#${{ github.event.issue.number }}

          <!-- agent_task_metadata {\"task_id\": \"${{ steps.metadata.outputs.task_id }}\"} -->

          ## Changes
          This PR was automatically generated by the agent runner in response to dispatch issue #${{ github.event.issue.number }}.

          ## Task Instruction
          ${{ steps.metadata.outputs.instruction }}"
          
          gh pr create \
            --title "Agent task: ${{ github.event.issue.title }}" \
            --body "$PR_BODY" \
            --base main
      
      - name: Comment on issue (completed)
        if: success()
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.AGENT_RUNNER_TOKEN }}
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '✅ Agent runner completed processing and created a pull request.'
            });
      
      - name: Comment on issue (failed)
        if: failure()
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.AGENT_RUNNER_TOKEN }}
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '❌ Agent runner failed to process this task. Check the workflow logs for details.'
            });
```

### Setup Steps for GitHub Actions

1. **Create the dispatch repository** (if it doesn't exist):
   ```bash
   # Create a new repository on GitHub (e.g., owner/lift_coding_dispatch)
   # This can be public or private based on your security requirements
   ```

2. **Create a GitHub token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate a new token with `repo` scope
   - Or create a GitHub App with the required permissions

3. **Add the token as a secret**:
   - In your dispatch repository, go to Settings → Secrets and variables → Actions
   - Create a new secret named `AGENT_RUNNER_TOKEN`
   - Paste your GitHub token

4. **Add the workflow file**:
   - Create `.github/workflows/agent-runner.yml` in the dispatch repository
   - Copy the example workflow above and customize the "Process task" step

5. **Configure HandsFree**:
   - Set environment variables:
     ```bash
     HANDSFREE_AGENT_PROVIDER=github_issue_dispatch
     HANDSFREE_AGENT_DISPATCH_REPO=owner/lift_coding_dispatch
     GITHUB_TOKEN=ghp_your_token_here
     ```

6. **Test the workflow**:
   - Create a test issue with the `copilot-agent` label
   - Verify the workflow runs and creates a PR
   - Check that HandsFree marks the task as completed

## Docker Compose Custom Runner

For a custom runner implementation, create `docker-compose.agent-runner.yml`:

```yaml
version: '3.8'

services:
  agent-runner:
    build:
      context: ./agent-runner
      dockerfile: Dockerfile
    environment:
      # GitHub authentication
      - GITHUB_TOKEN=${AGENT_RUNNER_GITHUB_TOKEN}
      
      # Dispatch repository configuration
      - DISPATCH_REPO=${HANDSFREE_AGENT_DISPATCH_REPO:-endomorphosis/lift_coding_dispatch}
      - POLL_INTERVAL_SECONDS=${AGENT_POLL_INTERVAL:-30}
      
      # Agent configuration
      - AGENT_NAME=${AGENT_NAME:-custom-agent}
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=${LLM_MODEL:-gpt-4}
      
      # Logging
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    
    volumes:
      # Mount workspace for processing tasks
      - agent-workspace:/workspace
      # Optional: mount custom scripts or plugins
      - ./agent-runner/plugins:/app/plugins:ro
    
    restart: unless-stopped
    
    networks:
      - agent-runner-net

networks:
  agent-runner-net:
    driver: bridge

volumes:
  agent-workspace:
```

Create `agent-runner/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent runner code
COPY . .

# Run the agent
CMD ["python", "runner.py"]
```

Create `agent-runner/requirements.txt`:

```
PyGithub>=2.1.1
openai>=1.0.0
httpx>=0.24.0
python-dotenv>=1.0.0
```

Create `agent-runner/runner.py`:

```python
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
        
        # Simulate work
        time.sleep(5)
        
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
    processed_issues = set()
    
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
                    # Mark as processed
                    processed_issues.add(issue.number)
                    
                    # Optional: close the issue or add a label
                    # issue.edit(state='closed')
                    # issue.add_to_labels('processed')
            
            # Clean up old processed issues from memory (keep last 1000)
            if len(processed_issues) > 1000:
                processed_issues = set(list(processed_issues)[-1000:])
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        
        # Wait before next poll
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
```

### Setup Steps for Docker Compose

1. **Create the agent-runner directory**:
   ```bash
   mkdir -p agent-runner
   cd agent-runner
   ```

2. **Create the files**:
   - Copy the `Dockerfile`, `requirements.txt`, and `runner.py` from above

3. **Configure environment variables**:
   - Create `.env` file:
     ```bash
     AGENT_RUNNER_GITHUB_TOKEN=ghp_your_token_here
     HANDSFREE_AGENT_DISPATCH_REPO=owner/lift_coding_dispatch
     LLM_API_KEY=your_llm_api_key_here
     ```

4. **Build and run**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml up -d
   ```

5. **Monitor logs**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```

## Troubleshooting

### Runner not detecting dispatch issues

**Problem**: The agent runner doesn't find or process dispatch issues.

**Solutions**:
- Verify the `copilot-agent` label exists on the issues
- Check that the runner has access to the dispatch repository
- Verify the GitHub token has the required permissions (`repo` scope)
- Check the runner logs for authentication errors
- Ensure the dispatch repository name is correct (format: `owner/repo`)

### Task not marked as completed

**Problem**: The PR is created but HandsFree doesn't mark the task as completed.

**Solutions**:
- Verify the PR body includes correlation metadata:
  ```markdown
  <!-- agent_task_metadata {"task_id": "actual-task-id"} -->
  ```
  or
  ```markdown
  Fixes #123
  ```
- Check that the webhook is being received by HandsFree (check webhook logs)
- Verify the task_id matches exactly (UUIDs are case-sensitive)
- Check that the PR is opened in the same repository as the dispatch issue (for issue references)
- Look at HandsFree logs for correlation attempts and errors

### GitHub API rate limiting

**Problem**: Runner hits GitHub API rate limits.

**Solutions**:
- Increase `POLL_INTERVAL_SECONDS` to reduce API calls
- Use a GitHub App instead of personal access token (higher rate limits)
- Implement conditional requests using ETags
- Use GraphQL API instead of REST API for complex queries
- Monitor rate limit headers and implement exponential backoff

### Authentication failures

**Problem**: Runner fails to authenticate with GitHub.

**Solutions**:
- Regenerate the GitHub token and update secrets
- Verify token hasn't expired
- Check token scopes include `repo` permission
- For GitHub Apps, verify the app installation and permissions
- Test token manually using `curl`:
  ```bash
  curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
  ```

### Workflow doesn't trigger

**Problem**: GitHub Actions workflow doesn't run when issues are created.

**Solutions**:
- Verify the workflow file is in `.github/workflows/` in the default branch
- Check that the repository has Actions enabled (Settings → Actions)
- Verify the workflow has the correct trigger conditions
- Check the Actions tab for any errors or disabled workflows
- Ensure the `copilot-agent` label is applied to the issue

## Security Considerations

### Token Security
- **Never commit tokens to version control**
- Use GitHub Actions secrets or environment variables
- Rotate tokens regularly (every 90 days recommended)
- Use fine-grained tokens with minimal required permissions
- Consider using GitHub Apps for better auditability

### Bot Account
- Create a dedicated bot account for the agent runner
- Don't use personal accounts for automation
- Document the bot account and its purpose
- Restrict bot account permissions to only what's needed

### Code Execution
- Validate and sanitize all inputs from dispatch issues
- Use sandboxed environments for executing untrusted code
- Implement timeout limits for task processing
- Review generated code before merging (don't auto-merge)
- Use branch protection rules to require reviews

### Secrets Management
- Use GitHub Actions secrets or external secret managers (Vault, AWS Secrets Manager)
- Don't log secrets or sensitive data
- Implement secret scanning in repositories
- Rotate secrets regularly

### Rate Limiting
- Respect GitHub API rate limits
- Implement exponential backoff for retries
- Cache responses when possible
- Use conditional requests to save quota

## Monitoring and Observability

### Logging
- Log all task processing attempts and outcomes
- Include timestamps and correlation IDs
- Avoid logging sensitive data (tokens, user data)
- Use structured logging (JSON) for easier parsing

### Metrics
- Track task processing success/failure rates
- Monitor GitHub API rate limit usage
- Measure task processing duration
- Count active/completed/failed tasks

### Alerts
- Alert on repeated failures
- Alert on API rate limit warnings
- Alert on authentication failures
- Alert on extended processing times

### Example Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

tasks_processed = Counter('agent_tasks_processed_total', 'Total tasks processed', ['status'])
task_duration = Histogram('agent_task_duration_seconds', 'Task processing duration')
github_rate_limit = Gauge('github_api_rate_limit_remaining', 'GitHub API rate limit remaining')
```

## Next Steps

After setting up your agent runner:

1. **Test the full flow**:
   - Create a test dispatch issue manually
   - Verify the runner processes it
   - Check that a PR is created with correlation metadata
   - Verify HandsFree marks the task as completed

2. **Customize the processing logic**:
   - Integrate your preferred LLM provider
   - Add custom validation and testing
   - Implement error recovery strategies

3. **Monitor and optimize**:
   - Watch logs for errors and warnings
   - Optimize polling intervals
   - Tune timeouts and retries

4. **Scale up**:
   - Add more runner instances for concurrency
   - Implement a queue for better load distribution
   - Use auto-scaling based on dispatch issue volume

## Related Documentation

- [PR-016: Agent delegation integration](../tracking/PR-016-agent-delegation-integration.md) - Details on the dispatch provider
- [PR-022: Agent delegation polish](../tracking/PR-022-agent-delegation-polish.md) - Auto-start and webhook correlation
- [PR-008: Agent orchestration stub](../tracking/PR-008-agent-orchestration-stub.md) - Original agent task model
- [GitHub Webhooks Documentation](./webhooks.md) - Webhook ingestion and processing

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review runner logs for specific errors
3. Verify configuration and permissions
4. Open an issue in the repository with:
   - Runner type (Actions, Docker, custom)
   - Error messages and logs
   - Configuration (with sensitive data redacted)
   - Steps to reproduce
