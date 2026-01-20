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

**Setup**: Configure a GitHub Copilot agent for your dispatch repository through the GitHub web interface or API. The agent should be configured to monitor issues with the `copilot-agent` label and create PRs that reference the dispatch issue. Refer to GitHub Copilot documentation for specific configuration steps.

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

### Environment Variables

The HandsFree backend supports several environment variables for configuring agent delegation:

| Variable | Description | Default |
|----------|-------------|---------|
| `HANDSFREE_AGENT_DEFAULT_PROVIDER` | Override the default agent provider | _(none)_ |
| `HANDSFREE_AGENT_DISPATCH_REPO` | GitHub repository for dispatch issues (format: `owner/repo`) | _(none)_ |
| `GITHUB_TOKEN` | GitHub personal access token or App token | _(none)_ |

**Provider Selection Precedence:**

When calling `agent.delegate` without specifying a provider, the system selects a provider using the following precedence:

1. **Explicit provider argument** - If a provider is specified in the API call, it always takes precedence
2. **HANDSFREE_AGENT_DEFAULT_PROVIDER** - If set, this environment variable overrides all defaults
3. **github_issue_dispatch (auto-configured)** - If `HANDSFREE_AGENT_DISPATCH_REPO` and `GITHUB_TOKEN` are both set, `github_issue_dispatch` is automatically selected
4. **copilot (fallback)** - If none of the above are set, falls back to the `copilot` provider

**Example Configurations:**

```bash
# Scenario 1: Use github_issue_dispatch automatically (recommended)
export HANDSFREE_AGENT_DISPATCH_REPO=owner/lift_coding_dispatch
export GITHUB_TOKEN=ghp_your_token_here
# Result: github_issue_dispatch is automatically used

# Scenario 2: Force a specific provider regardless of configuration
export HANDSFREE_AGENT_DEFAULT_PROVIDER=mock
export HANDSFREE_AGENT_DISPATCH_REPO=owner/lift_coding_dispatch
export GITHUB_TOKEN=ghp_your_token_here
# Result: mock provider is used (env var takes precedence)

# Scenario 3: Use copilot provider (no dispatch configured)
# Don't set HANDSFREE_AGENT_DISPATCH_REPO or GITHUB_TOKEN
# Result: copilot provider is used (fallback)
```

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
      
      - name: Process task (customize this step)
        working-directory: target-repo
        run: |
          # IMPORTANT: This is an example workflow step.
          # For a complete implementation, see agent-runner/runner.py in the repository.
          #
          # This step should:
          # - Apply patches from fenced diff/patch blocks (see apply_instruction.py)
          # - Generate code changes (using LLM or other tools)
          # - Create trace files with task metadata
          # - Run tests and validation
          
          echo "Processing instruction: ${{ steps.metadata.outputs.instruction }}"
          
          # Example: Create a simple trace file
          git config user.name "Agent Runner Bot"
          git config user.email "agent-runner@example.com"
          
          # Create agent-tasks directory and trace file
          mkdir -p agent-tasks
          TASK_ID="${{ steps.metadata.outputs.task_id }}"
          if [ -z "$TASK_ID" ]; then
            echo "Error: TASK_ID is empty; metadata parsing may have failed."
            exit 1
          fi
          TASK_PREFIX="${TASK_ID:0:8}"
          
          cat > "agent-tasks/${TASK_PREFIX}.md" << EOF
          # Agent Task Trace: ${TASK_PREFIX}
          
          ## Task Metadata
          - **Task ID**: ${TASK_ID}
          - **Issue Number**: #${{ github.event.issue.number }}
          - **Processed At**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
          
          ## Instruction
          ${{ steps.metadata.outputs.instruction }}
          
          ## Correlation Metadata
          <!-- agent_task_metadata {"task_id": "${TASK_ID}"} -->
          EOF
          
          git add agent-tasks/
          git commit -m "Process agent task from dispatch issue #${{ github.event.issue.number }}"
      
      - name: Create Pull Request
        working-directory: target-repo
        env:
          GH_TOKEN: ${{ secrets.AGENT_RUNNER_TOKEN }}
        run: |
          # Create a branch using task_id prefix (matches runner.py behavior)
          TASK_ID="${{ steps.metadata.outputs.task_id }}"
          TASK_PREFIX="${TASK_ID:0:8}"
          BRANCH_NAME="agent-task-${TASK_PREFIX}"
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

See [Smoke Test Procedure](#smoke-test-procedure) below for detailed testing steps.

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
# Core dependencies
PyGithub>=2.1.1

# Optional dependencies for extending the runner
# Uncomment and install based on your needs:

# For LLM integration (OpenAI, Anthropic, etc.)
# openai>=1.0.0

# For advanced HTTP requests
# httpx>=0.24.0

# For loading .env files
# python-dotenv>=1.0.0
```

The `agent-runner/runner.py` file is provided in the repository and implements a complete workflow that:

1. **Polls for dispatch issues**: Monitors the dispatch repository for issues labeled `copilot-agent`
2. **Extracts task metadata**: Parses the issue body to extract `task_id`, `instruction`, and `target_repo`
3. **Clones the target repository**: Uses git to clone the repository into `/workspace`
4. **Creates a branch**: Names the branch `agent-task-<task_id_prefix>` where `task_id_prefix` is the first 8 characters of the task ID
5. **Applies deterministic patches**: If the instruction contains fenced `diff` or `patch` blocks, applies them using `apply_instruction.py` and `git apply`
6. **Creates a trace file**: Generates `agent-tasks/<task_id_prefix>.md` with task metadata and correlation information
7. **Commits and pushes**: Commits all changes and pushes the branch to the remote repository
8. **Creates a pull request**: Opens a PR with:
   - Title: `"Agent task: {issue.title}"`
   - Body containing correlation metadata: `<!-- agent_task_metadata {"task_id": "{task_id}"} -->`
   - Issue reference: `Fixes {dispatch_repo}#{issue_number}`
9. **Adds processed label**: Labels the dispatch issue with `processed` to prevent reprocessing
10. **Cleans up workspace**: Removes the cloned repository from `/workspace` after processing

### Deterministic Patch Mode

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
        
        # IMPLEMENTATION NOTE: This is a placeholder for task processing logic.
        # For a minimal working implementation that processes tasks from a local database,
        # see the Minimal Agent Runner documentation: docs/MINIMAL_AGENT_RUNNER.md
        #
        # For full GitHub integration with PR creation, see the complete implementation
        # in agent-runner/runner.py which includes:
        # - Clone the target repository
        # - Use an LLM to understand the instruction and generate code
        # - Make the requested changes
        # - Run tests to verify changes
        # - Create a PR with correlation metadata
        
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

1. Extract all fenced `diff` and `patch` blocks from the instruction
2. Apply them sequentially using `git apply --index`
3. Abort the task if any patch fails to apply (preventing misleading PRs)

**Example instruction with patch:**

````markdown
## Instruction

Update the README to add a new section.

```diff
diff --git a/README.md b/README.md
index 1234567..abcdefg 100644
--- a/README.md
+++ b/README.md
@@ -10,0 +11,3 @@
+## New Section
+
+This is a new section added by the agent runner.
```
````

This deterministic mode is implemented via the `apply_instruction.py` helper script, which:
- Parses fenced code blocks from the instruction markdown
- Filters for `diff` and `patch` language tags
- Creates temporary patch files
- Applies them using `git apply --index`
- Reports success or failure

**Reference implementation**: See `agent-runner/runner.py` (function `apply_patches_from_instruction`) and `agent-runner/apply_instruction.py` for the complete implementation.

### Customizing the Runner

You can extend the runner to add:

- **LLM-powered code generation**: Integrate OpenAI, Anthropic, or other providers to generate code changes from natural language instructions
- **Testing and validation**: Run unit tests, linters, or build checks before creating the PR
- **Advanced error handling**: Implement retry logic, exponential backoff, and detailed error reporting
- **Concurrency**: Process multiple tasks in parallel using threading or async/await

For customization examples and integration patterns, see `agent-runner/README.md`.

### Setup Steps for Docker Compose

1. **The agent-runner directory is already included** in the repository at `agent-runner/`:
   - `Dockerfile` - Container image definition
   - `requirements.txt` - Core Python dependencies (PyGithub; optional extras such as `openai`, `httpx`, and `python-dotenv` may also be listed)
   - `runner.py` - Complete runner implementation
   - `apply_instruction.py` - Helper script for deterministic patch mode
   - `README.md` - Additional setup and customization information

2. **Configure environment variables**:
   - Create `.env` file:
     ```bash
     AGENT_RUNNER_GITHUB_TOKEN=ghp_your_token_here
     HANDSFREE_AGENT_DISPATCH_REPO=owner/lift_coding_dispatch
     LLM_API_KEY=your_llm_api_key_here
     ```

3. **Build and run**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml up -d
   ```

4. **Monitor logs**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```

## Smoke Test Procedure

After setting up your agent runner, follow these steps to verify it's working correctly:

### Prerequisites

- Agent runner is running (either via GitHub Actions, Docker, or custom deployment)
- Dispatch repository exists and is accessible
- GitHub token has appropriate permissions
- Target repository exists (can be same as dispatch repo)

### Test Steps

#### Step 1: Create a Test Dispatch Issue

In your dispatch repository (e.g., `owner/lift_coding_dispatch`), create a new issue:

**Title**: `Test agent task - Hello World`

**Labels**: `copilot-agent`

**Body**:
```markdown
<!-- agent_task_metadata {"task_id": "smoke-test-XXXXXXXX"} -->

## Instruction

Create a simple test file to verify the agent runner is working correctly. This is a smoke test.

Target Repository: owner/your-target-repo
```

**Note**: Replace:
- `XXXXXXXX` with a unique 8-character string (e.g., use current timestamp or random hex: `date +%s | md5sum | head -c 8`)
- `owner/your-target-repo` with your actual target repository name (or omit to use the dispatch repo as target)

Example task ID generation:
```bash
# Generate a unique task ID using current timestamp
echo "smoke-test-$(date +%s | tail -c 9)"
# Output: smoke-test-12345678
```

#### Step 2: Monitor Agent Processing

**For Docker deployment**:
```bash
docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
```

**For GitHub Actions**:
- Go to the Actions tab in your dispatch repository
- Watch for the workflow run to start (triggered by the issue creation/labeling)
- Click on the workflow run to see detailed logs

**Expected log output**:
```
INFO - Found new dispatch issue: #X - Test agent task - Hello World
INFO - Processing task: Test agent task - Hello World
INFO - Task ID: smoke-test-12345678
INFO - Cloning repository to /workspace/...
INFO - Creating new branch agent-task-smoke-te...
INFO - Created trace file at .../agent-tasks/smoke-te.md
INFO - Changes committed
INFO - Pushed branch agent-task-smoke-te to remote
INFO - Creating new PR...
INFO - Created PR: #Y
INFO - Added 'processed' label to issue
INFO - Task processed successfully: X
```

#### Step 3: Verify the Pull Request

Navigate to the target repository and verify:

1. **Branch created**: A new branch named `agent-task-smoke-te` (or similar based on task ID prefix)

2. **PR opened** with:
   - **Title**: "Agent task: Test agent task - Hello World"
   - **Body contains**:
     ```markdown
     <!-- agent_task_metadata {"task_id": "smoke-test-12345678"} -->
     
     Automated changes from agent task
     
     Fixes owner/lift_coding_dispatch#X
     ```
   - **Files changed**: A new file `agent-tasks/smoke-te.md` containing:
     - Task ID
     - Instruction text
     - Correlation metadata comment
     - Timestamps

3. **PR references the dispatch issue** (check the "Linked issues" section on GitHub)

#### Step 4: Verify Dispatch Issue Updates

Go back to the dispatch issue and verify:

1. **Comments added**:
   - "🤖 [agent-name] started processing this task at [timestamp]"
   - "✅ [agent-name] completed processing this task.\n\nPull request created: [PR URL]"

2. **Label added**: The `processed` label should be present (if the label exists in the repository)

#### Step 5: Test Idempotency

To verify the runner handles existing PRs correctly:

1. **Keep the test issue open** (don't close it yet)

2. **Restart the agent runner**:
   
   **For Docker**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml restart agent-runner
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```
   
   **For GitHub Actions**: Manually re-trigger the workflow or create a comment on the issue

3. **Expected behavior**:
   - Runner should skip the issue (already in processed_issues cache)
   - OR if cache was cleared, runner should update the existing PR instead of creating a new one
   - Check logs: "PR already exists: #Y, updating..."

4. **Verify**: No duplicate branches or PRs should be created

#### Step 6: Test HandsFree Correlation (Optional)

If you're running the HandsFree backend:

1. **Check HandsFree logs** for webhook processing:
   ```
   INFO - Received webhook: pull_request opened
   INFO - Extracted task_id from PR body: smoke-test-12345678
   INFO - Updated agent task status to completed
   ```

2. **Query the agent task** via API or database:
   ```bash
   curl -X GET http://localhost:8000/agent-tasks/smoke-test-12345678 \
     -H "X-API-Key: your-api-key"
   ```
   
   Verify the task status is `completed` and the trace includes the PR URL.

#### Step 7: Clean Up

After successful testing:

1. **Close the test PR** (or merge if you want to keep the test file)
2. **Delete the test branch** in the target repository
3. **Close the test dispatch issue**
4. **Remove test files** (optional):
   ```bash
   # In target repo
   git checkout main
   git branch -D agent-task-smoke-te
   rm -rf agent-tasks/
   ```

### Troubleshooting

**Issue: Runner doesn't detect the issue**
- Verify the `copilot-agent` label is applied
- Check DISPATCH_REPO environment variable is correct
- Verify GitHub token has access to the repository
- Check runner logs for authentication errors

**Issue: Clone fails**
- Verify GitHub token has `repo` scope
- Check if target repository exists and is accessible
- Verify network connectivity from runner to GitHub

**Issue: Push fails with authentication error**
- Ensure GITHUB_TOKEN is passed to git clone URL
- Verify token hasn't expired
- Check token permissions (needs write access to target repo)

**Issue: PR creation fails**
- Verify token has `pull_requests: write` permission
- Check if base branch (main/master) exists in target repo
- Ensure branch has at least one commit

**Issue: No 'processed' label added**
- The `processed` label might not exist in the repository
- Create the label manually: Settings → Labels → New label
- Label name: `processed`, color: `#0E8A16` (green)
- Re-run the test

**Issue: HandsFree doesn't mark task as completed**
- Verify webhook is configured in target repository
- Check correlation metadata format in PR body
- Verify task_id matches exactly (case-sensitive)
- Check HandsFree logs for webhook processing errors

### Success Criteria

Your agent runner is working correctly if:

✅ Dispatch issue is detected within the poll interval  
✅ Repository is cloned successfully  
✅ Branch is created with correct naming pattern  
✅ Trace file contains correlation metadata  
✅ PR is created with proper metadata and issue reference  
✅ Dispatch issue is marked as processed  
✅ Re-running doesn't create duplicate PRs (idempotency)  
✅ (Optional) HandsFree marks the task as completed  

Congratulations! Your agent runner is now operational.

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

1. **Test the full flow (Smoke Test)**:
   
   a. **Create a test dispatch issue** in your dispatch repository:
      - Title: "Test agent task"
      - Add label: `copilot-agent`
      - Body:
        ```markdown
        ## Instruction
        Create a simple test file to verify agent runner functionality
        
        Target Repository: owner/your-repo
        
        <!-- agent_task_metadata {"task_id": "test-1234-5678-abcd"} -->
        ```
   
   b. **Monitor the agent runner**:
      - For Docker Compose: `docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner`
      - For GitHub Actions: Check the Actions tab in your dispatch repository
      
      Expected log output:
      - "Found new dispatch issue: #N - Test agent task"
      - "Cloning owner/your-repo to /workspace/..."
      - "Creating new branch agent-task-test-123"
      - "Created trace file: agent-tasks/test-123.md"
      - "Committed and pushed changes to agent-task-test-123"
      - "Created PR #N: <PR URL>"
      - "Task processed successfully: N"
   
   c. **Verify the results**:
      - ✅ A new branch `agent-task-test-123` exists in the target repository
      - ✅ A new pull request is created with:
        - Title: "Agent task: Test agent task"
        - Body contains: `<!-- agent_task_metadata {"task_id": "test-1234-5678-abcd"} -->`
        - Body contains: `Fixes owner/dispatch-repo#N`
        - File `agent-tasks/test-123.md` is present in the PR
      - ✅ The dispatch issue has two comments from the agent:
        - "🤖 custom-agent started processing this task..."
        - "✅ custom-agent completed processing this task..."
      - ✅ The dispatch issue has a `processed` label
      - ✅ HandsFree backend marks the task as completed (check task status)
   
   d. **Clean up**:
      - Close or merge the test PR
      - Delete the test branch: `git push origin --delete agent-task-test-123`
      - Close the test dispatch issue

2. **Test deterministic patch mode** (optional):
   
   Create a dispatch issue with an embedded patch:
   
   ````markdown
   ## Instruction
   
   Add a new section to the README.
   
   ```diff
   diff --git a/README.md b/README.md
   index 1234567..abcdefg 100644
   --- a/README.md
   +++ b/README.md
   @@ -1,0 +2,3 @@
   +## New Section
   +
   +This section was added by deterministic patch mode.
   ```
   
   <!-- agent_task_metadata {"task_id": "patch-test-12345678"} -->
   ````
   
   The runner will apply the patch using `git apply` before creating the PR.

3. **Customize for your needs**:
   - The runner in `agent-runner/runner.py` provides a complete working implementation
   - For LLM integration, see customization examples in `agent-runner/README.md`
   - Add validation, testing, or other custom logic as needed

4. **Monitor and optimize**:
   - Watch logs for errors and warnings
   - Optimize polling intervals to balance responsiveness and API rate limits
   - Tune timeouts and retries for your workload

5. **Scale up** (optional):
   - Add more runner instances for concurrency
   - Implement a queue for better load distribution
   - Use auto-scaling based on dispatch issue volume

## Related Documentation

- **[Agent Runner Quick Start](./AGENT_RUNNER_QUICKSTART.md)** - Get started in 5 minutes with GitHub Actions
- **[Agent Runner README](../agent-runner/README.md)** - Implementation details and customization guide
- **[Docker Compose Configuration](../docker-compose.agent-runner.yml)** - Full configuration reference
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
