# Agent Runner

This directory contains a custom agent runner implementation that polls the dispatch repository for new issues and processes them.

## 🚀 Quick Start

**Want to get started in 5 minutes?** See the [Quick Start Guide](../docs/AGENT_RUNNER_QUICKSTART.md)!

The quick start will help you:
1. Create a GitHub token
2. Add it as a repository secret
3. Create a test issue and see the agent runner in action

## What's Included

- **`Dockerfile`**: Container image definition for the agent runner
- **`requirements.txt`**: Python dependencies
- **`runner.py`**: Main agent runner implementation

## Two Deployment Options

### Option 1: GitHub Actions Workflow (Recommended)

A workflow file at `.github/workflows/agent-runner.yml` provides:
- ✅ Zero infrastructure to maintain
- ✅ Automatic processing of labeled issues
- ✅ Built-in secrets management
- ✅ Native GitHub integration
- ✅ Safe by default (only runs when secrets are present)

**Setup**: See [Quick Start Guide](../docs/AGENT_RUNNER_QUICKSTART.md)

### Option 2: Docker Container (Advanced)

Use `docker-compose.agent-runner.yml` for:
- Custom LLM integrations
- On-premise deployments
- Advanced error handling
- High-volume processing

**Setup**: See [Full Setup Guide](../docs/agent-runner-setup.md)

## How It Works

The agent runner (GitHub Actions or Docker) implements a complete workflow that:

1. Polls the dispatch repository for issues labeled with `copilot-agent`
2. Clones the target repository into `/workspace`
3. Creates a branch named `agent-task-<task_id_prefix>`
4. Optionally applies any fenced `diff`/`patch` blocks embedded in the task instruction
5. Creates a trace file under `agent-tasks/<task_id_prefix>.md` with task metadata and correlation comment
6. Commits and pushes changes
7. Creates a pull request with correlation metadata referencing the dispatch issue

### Deterministic Patch Mode

If the dispatch issue includes fenced code blocks like:

```diff
diff --git a/README.md b/README.md
index 0000000..1111111 100644
--- a/README.md
+++ b/README.md
@@
+Hello from a deterministic agent-runner patch.
```

the runner will apply them via `git apply --index` before creating the PR.

### Quick Start

1. **Set up environment variables** in your `.env` file or docker-compose configuration:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   DISPATCH_REPO=owner/lift_coding_dispatch
   ```

2. **Build and run with docker-compose**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml up -d
   ```

3. **Monitor logs**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```

### Smoke Test

To verify the agent runner is working correctly:

1. **Create a test dispatch issue** in your dispatch repository with:
   - Title: "Test agent task"
   - Label: `copilot-agent`
   - Body:
     ```markdown
     ## Instruction
     Create a simple test file
     
     Target Repository: owner/your-repo
     
     <!-- agent_task_metadata {"task_id": "test-1234-5678-abcd"} -->
     ```

2. **Monitor the agent runner logs**:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```
   
   You should see:
   - "Found new dispatch issue: #N - Test agent task"
   - "Cloning owner/your-repo..."
   - "Creating new branch agent-task-test-123"
   - "Created trace file..."
   - "Created PR #N..."

3. **Verify the results**:
   - A new branch `agent-task-test-123` should exist in the target repository
   - A new PR should be created with:
     - Title: "Agent task: Test agent task"
     - Body containing: `<!-- agent_task_metadata {"task_id": "test-1234-5678-abcd"} -->`
     - Body containing: `Fixes owner/dispatch-repo#N`
   - A file `agent-tasks/test-123.md` should exist in the PR
   - The dispatch issue should have comments from the agent runner
   - The dispatch issue should have a `processed` label

4. **Clean up**:
   - Close or merge the test PR
   - Delete the test branch
   - Close the test dispatch issue

### Customizing the Runner

The `runner.py` file includes a complete implementation of the PR-creation workflow. You can customize it further to:

- **Add LLM-powered code generation**: Integrate OpenAI, Anthropic, or other LLM providers to generate actual code changes based on the instruction
- **Add testing**: Run unit tests, integration tests, or linting before creating the PR
- **Add validation**: Check if changes compile, pass CI checks, or meet other criteria
- **Add retry logic**: Implement exponential backoff for transient failures
- **Add concurrency**: Process multiple tasks in parallel

Example of adding LLM integration:

```python
# In process_task(), before creating the trace file:
from openai import OpenAI

client = OpenAI(api_key=os.environ.get('LLM_API_KEY'))
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": f"Implement this task: {instruction}"}
    ]
)

# Use response.choices[0].message.content to make code changes
# Then commit those changes instead of just the trace file
```

### Integration Options

You can integrate various tools and services:

- **LLM Providers**: OpenAI, Anthropic, Azure OpenAI, local models
- **Code Generation**: Aider, Cursor API, custom prompts
- **Testing**: Run unit tests, integration tests, or E2E tests
- **CI/CD**: Trigger builds, deploy preview environments
- **Monitoring**: Send metrics to Prometheus, logs to ELK stack

## Documentation

For detailed setup instructions, configuration options, and troubleshooting, see:
- [Agent Runner Setup Guide](../docs/agent-runner-setup.md)

## Security Notes

- Never commit tokens or secrets to version control
- Use a dedicated bot account for the agent runner
- Scope tokens to minimum required permissions
- Review generated code before merging
- Use branch protection rules to require reviews

## Support

This is an example implementation. For production use, you'll need to:
- Implement robust error handling
- Add retry logic for transient failures
- Monitor rate limits
- Handle concurrent task processing
- Add observability (metrics, logging, tracing)
- Implement proper secret management
