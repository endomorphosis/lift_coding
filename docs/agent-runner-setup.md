# Agent Runner Setup Guide

## Overview

The HandsFree Dev Companion can delegate agent tasks to external runners by creating GitHub issues with task metadata. This guide shows you how to set up an external agent runner that:

1. Monitors a GitHub repository for new dispatch issues (labeled `copilot-agent`)
2. Processes the task instructions
3. Opens a pull request with correlation metadata
4. Allows the backend to track task completion via webhook correlation

## How It Works

### Task Dispatch Flow

```
User → HandsFree Backend → GitHub Issue (dispatch repo)
                             ↓
                    Agent Runner monitors issues
                             ↓
                    Processes task & opens PR
                             ↓
                    Backend correlates PR → Task (via webhook)
```

### Correlation Mechanism

When a runner opens a PR, it includes task metadata in the PR body:

```markdown
<!-- agent_task_metadata
{"task_id": "task-123", "user_id": "user-456", "provider": "github_issue_dispatch"}
-->
```

The backend's webhook handler detects this metadata and updates the task state to `completed`.

## Runner Options

You have three main options for running an agent:

1. **GitHub Actions** - Workflow triggered by dispatch issues
2. **Docker Compose** - Containerized Python runner for local/cloud deployment
3. **GitHub Copilot Agent** - Native Copilot integration (if available)

## Option 1: GitHub Actions Runner

### Setup Steps

1. **Create workflow file** in your **dispatch repository** (e.g., `endomorphosis/lift_coding_dispatch`):

   `.github/workflows/agent-runner.yml`:

   ```yaml
   name: Agent Task Runner
   
   on:
     issues:
       types: [opened, labeled]
     workflow_dispatch:
       inputs:
         issue_number:
           description: 'Issue number to process'
           required: true
   
   permissions:
     contents: write
     issues: write
     pull-requests: write
   
   jobs:
     process-task:
       runs-on: ubuntu-latest
       if: contains(github.event.issue.labels.*.name, 'copilot-agent')
       
       steps:
         - name: Extract task metadata
           id: metadata
           run: |
             echo "Extracting metadata from issue #${{ github.event.issue.number }}"
             BODY="${{ github.event.issue.body }}"
             
             # Extract task_id from issue body (adjust parsing as needed)
             TASK_ID=$(echo "$BODY" | grep -oP '(?<=task_id:\s)[\w-]+' || echo "unknown")
             USER_ID=$(echo "$BODY" | grep -oP '(?<=user_id:\s)[\w-]+' || echo "unknown")
             
             echo "task_id=$TASK_ID" >> $GITHUB_OUTPUT
             echo "user_id=$USER_ID" >> $GITHUB_OUTPUT
             echo "instruction=${{ github.event.issue.title }}" >> $GITHUB_OUTPUT
         
         - name: Checkout target repository
           uses: actions/checkout@v4
           with:
             repository: ${{ secrets.TARGET_REPO }}  # e.g., "owner/repo"
             token: ${{ secrets.AGENT_GITHUB_TOKEN }}
         
         - name: Create feature branch
           run: |
             git config user.name "agent-runner[bot]"
             git config user.email "agent-runner[bot]@users.noreply.github.com"
             git checkout -b agent-task-${{ steps.metadata.outputs.task_id }}
         
         - name: Process task (placeholder)
           run: |
             echo "Processing: ${{ steps.metadata.outputs.instruction }}"
             # TODO: Add your actual task processing logic here
             # Examples:
             # - Run a script that makes code changes
             # - Call an LLM API to generate changes
             # - Execute predefined automation
             
             # For this example, create a simple file
             echo "# Task: ${{ steps.metadata.outputs.instruction }}" > TASK_RESULT.md
             echo "Processed by agent runner" >> TASK_RESULT.md
         
         - name: Commit changes
           run: |
             git add -A
             git commit -m "Agent task: ${{ steps.metadata.outputs.instruction }}" || echo "No changes to commit"
         
         - name: Push branch
           run: |
             git push origin agent-task-${{ steps.metadata.outputs.task_id }}
         
         - name: Create Pull Request
           env:
             GH_TOKEN: ${{ secrets.AGENT_GITHUB_TOKEN }}
           run: |
             # Create PR with correlation metadata
             METADATA='<!-- agent_task_metadata
             {"task_id": "${{ steps.metadata.outputs.task_id }}", "user_id": "${{ steps.metadata.outputs.user_id }}", "provider": "github_issue_dispatch"}
             -->'
             
             gh pr create \
               --title "Agent task: ${{ steps.metadata.outputs.instruction }}" \
               --body "Automated PR for agent task from issue #${{ github.event.issue.number }}

             $METADATA" \
               --head agent-task-${{ steps.metadata.outputs.task_id }} \
               --base main
         
         - name: Comment on dispatch issue
           env:
             GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
           run: |
             gh issue comment ${{ github.event.issue.number }} \
               --body "✅ Task processed. PR created in target repository."
   ```

2. **Configure secrets** in your dispatch repository:
   - `AGENT_GITHUB_TOKEN`: Personal access token or GitHub App token with:
     - `repo` scope (read/write)
     - `pull_requests:write`
     - `issues:write`
   - `TARGET_REPO`: Repository where PRs should be created (e.g., `owner/repo`)

3. **Test the workflow**:
   - Create a test issue in your dispatch repo with the `copilot-agent` label
   - Verify the workflow runs and creates a PR

### Required Permissions

The GitHub token needs:
- Read issues in dispatch repository
- Create branches in target repository
- Open pull requests in target repository
- Comment on issues in dispatch repository

## Option 2: Docker Compose Custom Runner

### Setup Steps

1. **Create agent runner script**:

   `agent-runner/runner.py`:

   ```python
   #!/usr/bin/env python3
   """
   Simple agent runner that polls GitHub for dispatch issues.
   """
   import json
   import os
   import re
   import time
   from datetime import datetime, timedelta
   
   import requests
   
   # Configuration
   DISPATCH_REPO = os.getenv("AGENT_DISPATCH_REPO", "endomorphosis/lift_coding_dispatch")
   TARGET_REPO = os.getenv("AGENT_TARGET_REPO", "endomorphosis/lift_coding")
   GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
   POLL_INTERVAL = int(os.getenv("AGENT_POLL_INTERVAL", "60"))  # seconds
   
   if not GITHUB_TOKEN:
       raise ValueError("GITHUB_TOKEN environment variable required")
   
   
   def get_headers():
       """Get GitHub API headers."""
       return {
           "Authorization": f"Bearer {GITHUB_TOKEN}",
           "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28",
       }
   
   
   def get_dispatch_issues():
       """Fetch open issues with copilot-agent label."""
       url = f"https://api.github.com/repos/{DISPATCH_REPO}/issues"
       params = {"labels": "copilot-agent", "state": "open"}
       
       resp = requests.get(url, headers=get_headers(), params=params)
       resp.raise_for_status()
       return resp.json()
   
   
   def extract_task_metadata(issue_body):
       """Extract task metadata from issue body."""
       # Look for metadata comment
       match = re.search(
           r"<!--\s*agent_task_metadata\s*\n?(.*?)\n?-->",
           issue_body,
           re.DOTALL
       )
       if match:
           try:
               return json.loads(match.group(1))
           except json.JSONDecodeError:
               pass
       
       # Fallback: extract from structured fields
       task_id = re.search(r"task_id:\s*([\w-]+)", issue_body)
       user_id = re.search(r"user_id:\s*([\w-]+)", issue_body)
       
       return {
           "task_id": task_id.group(1) if task_id else "unknown",
           "user_id": user_id.group(1) if user_id else "unknown",
           "provider": "github_issue_dispatch",
       }
   
   
   def process_task(issue):
       """Process a dispatch issue and create a PR."""
       issue_number = issue["number"]
       title = issue["title"]
       body = issue["body"] or ""
       
       print(f"Processing issue #{issue_number}: {title}")
       
       # Extract metadata
       metadata = extract_task_metadata(body)
       task_id = metadata.get("task_id", "unknown")
       
       # TODO: Implement actual task processing logic
       # This is a placeholder that creates a simple PR
       
       # Create a new branch and PR (simplified - in practice use PyGithub or similar)
       branch_name = f"agent-task-{task_id}"
       
       # For this example, we'll create a PR via GitHub API
       # In production, you'd clone the repo, make changes, and push
       
       pr_body = f"""
   Automated PR for agent task from issue #{issue_number}
   
   Task: {title}
   
   <!-- agent_task_metadata
   {json.dumps(metadata, indent=2)}
   -->
   """
       
       # Create PR (this is simplified - requires actual branch creation)
       print(f"Would create PR for task {task_id}")
       print(f"Metadata: {json.dumps(metadata, indent=2)}")
       
       # Comment on issue
       comment_url = f"https://api.github.com/repos/{DISPATCH_REPO}/issues/{issue_number}/comments"
       comment_data = {
           "body": f"✅ Task processed by agent runner. Branch: `{branch_name}`"
       }
       requests.post(comment_url, headers=get_headers(), json=comment_data)
       
       return True
   
   
   def main():
       """Main polling loop."""
       print(f"Agent runner starting...")
       print(f"Dispatch repo: {DISPATCH_REPO}")
       print(f"Target repo: {TARGET_REPO}")
       print(f"Poll interval: {POLL_INTERVAL}s")
       
       processed = set()
       
       while True:
           try:
               issues = get_dispatch_issues()
               print(f"Found {len(issues)} dispatch issue(s)")
               
               for issue in issues:
                   issue_id = issue["id"]
                   if issue_id not in processed:
                       try:
                           if process_task(issue):
                               processed.add(issue_id)
                       except Exception as e:
                           print(f"Error processing issue #{issue['number']}: {e}")
               
               time.sleep(POLL_INTERVAL)
               
           except KeyboardInterrupt:
               print("\nShutting down...")
               break
           except Exception as e:
               print(f"Error in main loop: {e}")
               time.sleep(POLL_INTERVAL)
   
   
   if __name__ == "__main__":
       main()
   ```

2. **Create Docker Compose file**:

   `docker-compose.agent-runner.yml`:

   ```yaml
   version: '3.8'
   
   services:
     agent-runner:
       build:
         context: ./agent-runner
         dockerfile: Dockerfile
       environment:
         - AGENT_DISPATCH_REPO=${AGENT_DISPATCH_REPO:-endomorphosis/lift_coding_dispatch}
         - AGENT_TARGET_REPO=${AGENT_TARGET_REPO:-endomorphosis/lift_coding}
         - GITHUB_TOKEN=${GITHUB_TOKEN}
         - AGENT_POLL_INTERVAL=${AGENT_POLL_INTERVAL:-60}
       restart: unless-stopped
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

3. **Create Dockerfile**:

   `agent-runner/Dockerfile`:

   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Install dependencies
   RUN pip install --no-cache-dir requests PyGithub
   
   # Copy runner script
   COPY runner.py .
   
   # Run as non-root user
   RUN useradd -m -u 1000 agent && chown -R agent:agent /app
   USER agent
   
   CMD ["python", "runner.py"]
   ```

4. **Create .env file** (or export variables):

   ```bash
   AGENT_DISPATCH_REPO=endomorphosis/lift_coding_dispatch
   AGENT_TARGET_REPO=endomorphosis/lift_coding
   GITHUB_TOKEN=ghp_your_token_here
   AGENT_POLL_INTERVAL=60
   ```

5. **Run the runner**:

   ```bash
   docker compose -f docker-compose.agent-runner.yml up -d
   
   # View logs
   docker compose -f docker-compose.agent-runner.yml logs -f
   
   # Stop runner
   docker compose -f docker-compose.agent-runner.yml down
   ```

### Required Environment Variables

- `AGENT_DISPATCH_REPO`: Repository to monitor for dispatch issues (format: `owner/repo`)
- `AGENT_TARGET_REPO`: Repository where PRs should be created
- `GITHUB_TOKEN`: GitHub token with appropriate permissions
- `AGENT_POLL_INTERVAL`: Polling interval in seconds (default: 60)

### Required Permissions

The GitHub token needs:
- Read issues in dispatch repository
- Create branches in target repository
- Open pull requests in target repository
- Comment on issues in dispatch repository

## Option 3: GitHub Copilot Agent

If you have access to GitHub Copilot for Business/Enterprise:

1. Configure Copilot to monitor your dispatch repository
2. Set up Copilot to respond to issues labeled `copilot-agent`
3. Ensure Copilot includes the correlation metadata in PR bodies

Refer to GitHub's Copilot documentation for specific setup instructions.

## Configuration Requirements

All runners must:

1. **Monitor dispatch issues**:
   - Watch for issues with label `copilot-agent`
   - Extract task metadata from issue body

2. **Process tasks**:
   - Parse task instruction
   - Execute task logic (code changes, automation, etc.)
   - Create a feature branch

3. **Create correlated PRs**:
   - Open PR in target repository
   - Include correlation metadata in PR body:
     ```markdown
     <!-- agent_task_metadata
     {"task_id": "...", "user_id": "...", "provider": "github_issue_dispatch"}
     -->
     ```

4. **Report status** (optional):
   - Comment on dispatch issue with status updates
   - Handle errors gracefully

## Smoke Test

### Prerequisites
- HandsFree backend running
- Dispatch repository configured (`HANDSFREE_AGENT_DISPATCH_REPO` env var)
- Agent runner deployed and running

### Test Steps

1. **Trigger a test dispatch** via backend API:

   ```bash
   curl -X POST http://localhost:8080/v1/agent/tasks \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "instruction": "Add a hello world function to utils.py",
       "provider": "github_issue_dispatch"
     }'
   ```

2. **Verify dispatch issue created**:
   - Check dispatch repository for new issue
   - Confirm `copilot-agent` label applied
   - Verify task metadata in issue body

3. **Wait for runner to process**:
   - Monitor runner logs
   - Confirm task detected and processed

4. **Verify PR created**:
   - Check target repository for new PR
   - Confirm correlation metadata in PR body
   - Verify branch name matches task_id

5. **Verify backend correlation**:
   - PR webhook should trigger backend correlation
   - Task state should update to `completed`
   - Check via API:
     ```bash
     curl http://localhost:8080/v1/agent/tasks/TASK_ID \
       -H "Authorization: Bearer YOUR_TOKEN"
     ```

Expected result: Task state is `completed` with `pr_url` in trace.

## Security Considerations

- **Use a dedicated bot account**: Don't use personal tokens
- **Scope tokens minimally**: Only grant required permissions
- **Rotate tokens regularly**: Especially for long-running runners
- **Validate task instructions**: Sanitize inputs before executing
- **Rate limit API calls**: Respect GitHub API limits (5000 req/hour)
- **Audit logging**: Log all task processing for security review
- **Secrets management**: Use environment variables or secret stores, never hardcode

## Troubleshooting

### Runner not detecting issues

- Verify `AGENT_DISPATCH_REPO` matches backend `HANDSFREE_AGENT_DISPATCH_REPO`
- Check GitHub token has `repo` read access
- Confirm issues have `copilot-agent` label
- Review runner logs for API errors

### PRs not correlating with tasks

- Ensure correlation metadata is in PR body (exact format matters)
- Verify backend webhook is configured for target repository
- Check task_id matches between issue and PR
- Review backend logs for webhook processing errors

### GitHub API rate limits

- Reduce polling frequency (`AGENT_POLL_INTERVAL`)
- Use conditional requests (ETags) to save quota
- Consider GitHub App authentication (higher limits)

### Permission errors

- Verify token has required scopes
- Check repository access (public vs private)
- Confirm bot account has been invited to repositories

## Advanced Configuration

### Using GitHub Apps

For higher rate limits and better security:

1. Create a GitHub App with required permissions
2. Install the app on dispatch and target repositories
3. Use app authentication in runner (JWT + installation token)

### Concurrent processing

To handle multiple tasks simultaneously:

1. Use a job queue (Redis, AWS SQS)
2. Run multiple runner instances
3. Implement task locking to prevent duplicates

### Enhanced task processing

Integrate with:
- LLM APIs (OpenAI, Anthropic) for intelligent task execution
- CI/CD systems for testing changes before PR creation
- Code analysis tools for quality checks

## Related Documentation

- Backend webhook correlation: `src/handsfree/api.py` (`_correlate_pr_with_agent_tasks`)
- Dispatch provider: `src/handsfree/agent_providers.py` (`GitHubIssueDispatchProvider`)
- PR correlation tests: `tests/test_pr_correlation.py`

## Support

For issues or questions:
- Open an issue in the main repository
- Check existing documentation in `docs/`
- Review tracking docs: `tracking/PR-016-agent-delegation-integration.md`, `tracking/PR-022-agent-delegation-polish.md`
