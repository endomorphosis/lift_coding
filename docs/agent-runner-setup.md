# Agent Runner Setup Guide

This guide explains how to set up an external agent runner that monitors and processes agent tasks dispatched via the `github_issue_dispatch` provider.

## Overview

The Handsfree Dev Companion can delegate agent tasks by creating GitHub issues in a dispatch repository. An external agent runner monitors these issues, performs the work, and opens pull requests that correlate back to the original tasks.

### Agent Task Dispatch Flow

```
User → Handsfree API (agent.delegate)
    ↓
Handsfree creates GitHub issue in dispatch repo
    ↓
Agent Runner monitors dispatch repo for new issues
    ↓
Agent Runner processes task and opens PR
    ↓
Handsfree receives PR webhook and correlates to task
    ↓
Task marked as completed, notifications emitted
```

### Key Components

1. **Handsfree Backend**: Creates dispatch issues with task metadata
2. **Dispatch Repository**: Dedicated repo for agent task issues (e.g., `owner/repo_dispatch`)
3. **Agent Runner**: External process that monitors issues and performs work
4. **Target Repository**: Where the agent runner opens PRs (the actual codebase)
5. **Webhook Correlation**: Handsfree matches PRs back to tasks via metadata

## Runner Options

You can choose from three main approaches to implement an agent runner:

### Option 1: GitHub Actions Workflow

A GitHub Actions workflow that triggers on new issues with the `copilot-agent` label.

**Pros:**
- Native GitHub integration
- No external infrastructure needed
- Built-in secrets management
- Easy to configure and maintain

**Cons:**
- Limited to GitHub-hosted runners
- Subject to GitHub Actions usage limits
- Less flexible for complex workflows

**Best for:** Simple automation, CI/CD integration, GitHub-centric workflows

### Option 2: GitHub Copilot Agent

Use GitHub Copilot as your agent runner (if available in your organization).

**Pros:**
- AI-powered code generation
- Natural language task processing
- Deep GitHub integration
- Minimal setup required

**Cons:**
- Requires GitHub Copilot Enterprise/Team
- Less control over processing logic
- May have usage limits

**Best for:** Organizations with Copilot access, AI-powered code tasks

### Option 3: Custom Runner (Docker + Python)

A standalone service that polls the dispatch repository and processes tasks.

**Pros:**
- Full control over processing logic
- Can integrate any LLM or automation tools
- Deploy anywhere (on-prem, cloud)
- Flexible task handling

**Cons:**
- Requires infrastructure setup
- Need to handle GitHub API rate limits
- More maintenance overhead

**Best for:** Custom workflows, on-premise deployments, advanced integrations

## Setup Instructions

### Prerequisites (All Options)

1. **Dispatch Repository**: Create or identify a GitHub repository for dispatch issues
   - Example: `your-org/your-project-dispatch`
   - Can be public or private (private recommended for security)

2. **GitHub Token**: Create a Personal Access Token or GitHub App with permissions:
   - `repo` scope (read/write issues, create PRs)
   - Access to both dispatch and target repositories

3. **Configure Handsfree Backend**: Set environment variables:
   ```bash
   HANDSFREE_AGENT_PROVIDER=github_issue_dispatch
   HANDSFREE_AGENT_DISPATCH_REPO=your-org/your-project-dispatch
   GITHUB_TOKEN=ghp_your_token_here
   ```

### Option 1: GitHub Actions Workflow

1. **Create workflow file** in your dispatch repository at `.github/workflows/agent-runner.yml`:

   See the example in `.github/workflows/agent-runner-example.yml` in this repository.

2. **Configure secrets** in your dispatch repository:
   - `GH_TOKEN`: Personal Access Token with `repo` scope
   - (Optional) `OPENAI_API_KEY`: If using AI/LLM for task processing

3. **Enable the workflow**:
   - The example workflow is disabled by default (`workflow_dispatch` only)
   - To enable automatic triggering, uncomment the `issues` trigger section

4. **Test the workflow**:
   - Create a test issue with label `copilot-agent` in your dispatch repo
   - Verify the workflow runs and processes the issue

**Key workflow features:**
- Triggers on issues labeled `copilot-agent`
- Extracts task metadata from issue body
- Processes the task (placeholder logic - customize as needed)
- Opens a PR in the target repository with correlation metadata
- Comments back on the dispatch issue with PR link

### Option 2: GitHub Copilot Agent

1. **Enable Copilot** for your organization or repository

2. **Configure Copilot agent** to monitor your dispatch repository:
   - Set up agent to watch for issues with label `copilot-agent`
   - Configure agent to extract task instructions from issue body

3. **Copilot will automatically**:
   - Monitor new issues in the dispatch repo
   - Process task instructions
   - Create PRs in the target repository
   - Reference the original dispatch issue

**Note**: GitHub Copilot agent configuration depends on your Copilot plan and features available. Refer to GitHub Copilot documentation for specific setup steps.

### Option 3: Custom Runner (Docker + Python)

1. **Use the provided Docker Compose setup**:

   See `docker-compose.agent-runner.yml` in this repository for a complete example.

2. **Configure environment variables** in `.env` or docker-compose file:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   DISPATCH_REPO=your-org/your-project-dispatch
   TARGET_REPO=your-org/your-project
   POLL_INTERVAL=60  # seconds
   ```

3. **Start the runner**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml up -d
   ```

4. **Monitor logs**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```

**Key runner features:**
- Polls dispatch repo for new issues every N seconds
- Processes tasks (customize logic in runner code)
- Creates PRs with proper correlation metadata
- Handles errors and reports back to dispatch issue
- Respects GitHub API rate limits

## Configuration Examples

### Task Metadata Format

When Handsfree creates a dispatch issue, it includes structured metadata in the issue body:

```markdown
## Task Details

- **Task ID**: 550e8400-e29b-41d4-a716-446655440000
- **User ID**: user-123
- **Target Repository**: your-org/your-project
- **Instruction**: Add authentication middleware to the API

<!-- agent_task_metadata {"task_id": "550e8400-e29b-41d4-a716-446655440000", "user_id": "user-123", "target_repo": "your-org/your-project", "instruction": "Add authentication middleware to the API"} -->
```

The HTML comment contains JSON metadata for correlation.

### PR Correlation Metadata

When your agent runner creates a PR, it must include correlation metadata for Handsfree to match it back to the task:

**Method 1: Metadata Comment (Recommended)**

Include an HTML comment in the PR body:

```markdown
This PR implements the requested authentication middleware.

<!-- agent_task_metadata {"task_id": "550e8400-e29b-41d4-a716-446655440000"} -->
```

**Method 2: Issue Reference (Fallback)**

Reference the dispatch issue in the PR body:

```markdown
This PR implements the requested authentication middleware.

Fixes your-org/your-project-dispatch#123
```

Handsfree will extract the issue number, look up the dispatch issue, and correlate via the task metadata in that issue.

### Required Permissions

#### GitHub Token Scopes

For a Personal Access Token:
- `repo` (full repository access)
  - Read/write issues
  - Create pull requests
  - Read repository contents

For a GitHub App:
- Issues: Read & Write
- Pull Requests: Read & Write
- Contents: Read & Write
- Metadata: Read

#### Repository Access

Your token/app must have access to:
1. **Dispatch Repository**: To read issues and post comments
2. **Target Repository**: To create pull requests

## Security Considerations

### Use a Dedicated Bot Account

**Strongly recommended**: Create a dedicated bot account (e.g., `your-org-agent-bot`) instead of using personal tokens.

Benefits:
- Clear audit trail of agent actions
- Isolate agent permissions from personal accounts
- Easier to rotate credentials
- Better security compliance

### Token Security

1. **Never commit tokens** to source code or logs
2. **Use environment variables** or secrets management
3. **Rotate tokens regularly** (every 90 days recommended)
4. **Scope tokens minimally** (only required permissions)
5. **Use repository secrets** in GitHub Actions (not hardcoded)

### Rate Limiting

GitHub API has rate limits:
- Authenticated requests: 5,000 per hour
- For polling: Use reasonable intervals (60+ seconds)
- Implement exponential backoff on failures
- Cache responses when possible

### Repository Isolation

- Use separate dispatch repository (don't pollute target repo with task issues)
- Consider private dispatch repo to avoid exposing internal tasks
- Review agent permissions regularly

## Troubleshooting

### Issue: Dispatch issues are not being processed

**Possible causes:**
1. Agent runner is not running or crashed
2. Issue does not have the `copilot-agent` label
3. GitHub token is invalid or expired
4. Token lacks required permissions

**Solutions:**
- Check agent runner logs
- Verify issue has correct label
- Test token with GitHub API: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`
- Ensure token has `repo` scope

### Issue: PRs are not correlating back to tasks

**Possible causes:**
1. Missing correlation metadata in PR body
2. Task ID mismatch
3. PR opened in wrong repository
4. Webhook not received by Handsfree

**Solutions:**
- Verify PR includes `<!-- agent_task_metadata {...} -->` comment
- Check task_id matches original dispatch issue
- Ensure PR is in target repository (not dispatch repo)
- Check Handsfree webhook logs for PR events

### Issue: GitHub API rate limit exceeded

**Possible causes:**
1. Polling too frequently
2. Too many API calls per task
3. Shared token across multiple services

**Solutions:**
- Increase poll interval (60+ seconds)
- Cache API responses
- Use conditional requests (ETag headers)
- Consider GraphQL API for fewer requests
- Use dedicated token for agent runner

### Issue: Agent runner can't authenticate

**Possible causes:**
1. Token format incorrect (should start with `ghp_` or `github_pat_`)
2. Token expired
3. Token revoked
4. Wrong environment variable name

**Solutions:**
- Regenerate token and update configuration
- Check token format (no extra spaces/newlines)
- Verify environment variable is set: `echo $GITHUB_TOKEN`
- Test token: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`

### Issue: Task stuck in "running" state

**Possible causes:**
1. Agent runner crashed mid-processing
2. PR creation failed
3. Correlation failed
4. No error reporting back to Handsfree

**Solutions:**
- Check agent runner logs for errors
- Manually create PR with correlation metadata
- Comment on dispatch issue with error details
- Consider adding task timeout logic

## Monitoring and Observability

### Recommended Monitoring

1. **Agent Runner Health**:
   - Uptime monitoring (ping endpoint or log file)
   - Error rate tracking
   - Processing latency

2. **GitHub API Usage**:
   - Rate limit remaining (check `X-RateLimit-Remaining` header)
   - API call count per hour
   - Failed request rate

3. **Task Processing**:
   - Average time from dispatch to PR creation
   - Success/failure rate
   - Stuck task count (running > X minutes)

4. **Webhook Delivery**:
   - PR webhook received count
   - Correlation success rate
   - Webhook processing errors

### Logging Best Practices

- Log all GitHub API requests and responses (redact tokens)
- Log task processing start/end with task_id
- Log correlation attempts (success/failure)
- Include timestamps and structured data (JSON)
- Rotate logs regularly

## Advanced Topics

### Concurrent Task Processing

To handle multiple dispatch issues concurrently:

1. **GitHub Actions**: Use matrix strategy to process multiple issues in parallel
2. **Custom Runner**: Use worker pool or async processing (e.g., asyncio, multiprocessing)
3. **Rate Limiting**: Ensure concurrent requests don't exceed GitHub API limits

### Error Reporting

When agent runner encounters errors:

1. **Comment on dispatch issue** with error details:
   ```markdown
   ❌ Task processing failed: [error message]
   
   Details:
   - Step: [which step failed]
   - Error: [full error message]
   - Logs: [link to logs if available]
   ```

2. **Update issue labels**: Add `agent-failed` label

3. **Consider retry logic**: Some errors are transient (rate limits, network issues)

### Task Prioritization

If you have multiple dispatch issues:

1. **Use issue labels**: `priority:high`, `priority:low`
2. **Process high priority first** in agent runner logic
3. **Use GitHub Projects** for backlog management

### Integration with CI/CD

Agent runners can integrate with existing CI/CD:

1. **GitHub Actions**: Chain agent runner with other workflows
2. **Custom Runner**: Trigger builds/tests after PR creation
3. **Status Checks**: Report agent processing status as commit status

## Related Documentation

- [PR-016: Agent Delegation Integration](../tracking/PR-016-agent-delegation-integration.md) - Original dispatch implementation
- [PR-022: Agent Delegation Polish](../tracking/PR-022-agent-delegation-polish.md) - Auto-start and webhook correlation
- [Webhook Development Guide](./webhook-development.md) - Webhook processing details
- [Authentication Guide](./AUTHENTICATION.md) - Token and auth setup

## Example Implementation

See the following files for complete working examples:

1. **GitHub Actions**: `.github/workflows/agent-runner-example.yml`
2. **Custom Runner**: `docker-compose.agent-runner.yml` + `scripts/agent-runner.py`

These examples are production-ready templates you can customize for your needs.

## Support

For issues with agent runner setup:

1. Check logs first (runner logs, Handsfree logs, webhook logs)
2. Review troubleshooting section above
3. Search existing issues in the repository
4. Open a new issue with:
   - Runner type (Actions/Copilot/Custom)
   - Error messages and logs (redact tokens)
   - Steps to reproduce
   - Environment details (OS, Docker version, etc.)
