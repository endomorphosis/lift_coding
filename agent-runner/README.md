# Agent Runner

This directory contains a minimal example agent runner that monitors GitHub issues for agent tasks and processes them.

## Quick Start

### Using Docker Compose

The easiest way to run the agent runner:

```bash
# From the repository root
docker compose -f docker-compose.agent-runner.yml up -d

# View logs
docker compose -f docker-compose.agent-runner.yml logs -f

# Stop runner
docker compose -f docker-compose.agent-runner.yml down
```

### Using Python Directly

```bash
cd agent-runner

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN=ghp_your_token_here
export AGENT_DISPATCH_REPO=endomorphosis/lift_coding_dispatch
export AGENT_TARGET_REPO=endomorphosis/lift_coding

# Run the runner
python runner.py
```

## Configuration

Set these environment variables:

- `GITHUB_TOKEN` (required): GitHub personal access token with repo permissions
- `AGENT_DISPATCH_REPO`: Repository to monitor for dispatch issues (default: `endomorphosis/lift_coding_dispatch`)
- `AGENT_TARGET_REPO`: Repository where PRs should be created (default: `endomorphosis/lift_coding`)
- `AGENT_POLL_INTERVAL`: Polling interval in seconds (default: 60)
- `AGENT_PROCESSED_LABEL`: Label to mark issues being processed (default: `agent-processing`)

## How It Works

1. **Polls dispatch repository** for issues labeled `copilot-agent`
2. **Extracts task metadata** from issue body (task_id, user_id, provider)
3. **Processes task** (placeholder logic - extend as needed)
4. **Creates PR** with correlation metadata for backend tracking
5. **Comments on issue** with status updates

## Extending

This is a **demonstration implementation**. For production use:

### Implement Task Processing

Replace the placeholder logic in `process_task()` with actual task execution:

```python
def process_task(issue: dict[str, Any]) -> bool:
    # 1. Clone target repository
    # 2. Create feature branch
    # 3. Make code changes based on instruction
    # 4. Commit and push changes
    # 5. Create PR using GitHub API
    # 6. Handle errors and edge cases
    pass
```

### Add GitHub API Integration

Use PyGithub for easier GitHub operations:

```python
from github import Github

g = Github(GITHUB_TOKEN)
target_repo = g.get_repo(TARGET_REPO)

# Create branch, make changes, create PR
# See: https://pygithub.readthedocs.io/
```

### Implement LLM Integration

For AI-powered task execution:

```python
import openai

def generate_code_changes(instruction: str) -> str:
    # Call LLM API to generate changes
    # Apply changes to repository
    pass
```

### Add Error Handling

- Retry failed operations
- Report errors back to dispatch issues
- Log errors for debugging

### Use Webhooks Instead of Polling

For better efficiency:

1. Set up webhook endpoint
2. Listen for `issues.opened` and `issues.labeled` events
3. Process tasks immediately when triggered

## Security

- Use a dedicated bot account, not personal tokens
- Scope GitHub token minimally (only required permissions)
- Validate and sanitize task instructions before executing
- Audit log all operations
- Rotate tokens regularly

## Troubleshooting

**Runner not detecting issues:**
- Verify `GITHUB_TOKEN` has repo read access
- Check `AGENT_DISPATCH_REPO` is correct
- Confirm issues have `copilot-agent` label

**Permission errors:**
- Token needs `repo` scope for private repos
- Token needs `public_repo` for public repos
- Verify bot account has access to repositories

**Rate limiting:**
- Reduce `AGENT_POLL_INTERVAL` (increase time between polls)
- Use conditional requests with ETags
- Consider GitHub App authentication for higher limits

## Documentation

See `docs/agent-runner-setup.md` for complete setup guide and runner options.
