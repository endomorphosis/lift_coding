# Agent Runner Example

This directory contains an example implementation of a custom agent runner that polls the dispatch repository for new issues and processes them.

## What's Included

- **`Dockerfile`**: Container image definition for the agent runner
- **`requirements.txt`**: Python dependencies
- **`runner.py`**: Main agent runner implementation (example/placeholder)

## Usage

This is a **reference implementation** that demonstrates a functional agent runner that:
- Polls dispatch issues labeled `copilot-agent`
- Clones the target repository
- Creates a working branch (`agent-task-<task_id_prefix>`)
- Commits a trace file with correlation metadata
- Opens a PR referencing the dispatch issue
- Marks the issue as processed

The runner implements idempotent PR creation - if a branch or PR already exists, it will update instead of failing.

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

To verify the runner is working correctly:

1. **Create a test dispatch issue** in your dispatch repository with:
   - Title: "Test agent task"
   - Label: `copilot-agent`
   - Body:
     ```markdown
     <!-- agent_task_metadata {"task_id": "test-task-12345678"} -->
     
     ## Instruction
     
     Create a simple test file to verify the agent runner is working.
     
     Target Repository: owner/target-repo
     ```

2. **Wait for the runner to process the issue** (check logs):
   ```bash
   docker-compose -f docker-compose.agent-runner.yml logs -f agent-runner
   ```
   
   You should see:
   - "Found new dispatch issue: #X - Test agent task"
   - "Processing task: Test agent task"
   - "Cloning repository..."
   - "Creating new branch agent-task-test-tas..."
   - "Created PR: #Y"

3. **Verify the results**:
   - A new branch `agent-task-test-tas` (or similar) should exist in the target repository
   - A PR should be created with:
     - Correlation metadata: `<!-- agent_task_metadata {"task_id": "test-task-12345678"} -->`
     - Issue reference: `Fixes owner/dispatch-repo#X`
     - A trace file in `agent-tasks/test-tas.md`
   - The dispatch issue should have:
     - A comment showing the PR URL
     - A `processed` label (if the label exists in the repository)

4. **Test idempotency** by restarting the runner:
   ```bash
   docker-compose -f docker-compose.agent-runner.yml restart agent-runner
   ```
   
   The runner should skip the already-processed issue (check logs for "Skip if already processed").

5. **Clean up** when done:
   ```bash
   # Close the PR and delete the branch in the target repository
   # Close or delete the test dispatch issue
   docker-compose -f docker-compose.agent-runner.yml down
   ```

### Customizing the Runner

The `runner.py` file implements a complete agent workflow that:

1. **Clones the target repository** into `/workspace`
2. **Creates a branch** named `agent-task-<task_id_prefix>`
3. **Generates a trace file** at `agent-tasks/<task_id_prefix>.md` with:
   - Task ID and correlation metadata
   - Instruction text
   - Timestamps
4. **Commits and pushes** the changes
5. **Creates a PR** with correlation metadata in the body
6. **Marks the issue as processed** with a comment and label

To customize the runner for your needs, modify the `create_trace_file()` function to make actual code changes instead of just creating a trace file. For example:

```python
def create_trace_file(repo_path: Path, task_id: str, instruction: str, issue_number: int) -> Path:
    # Instead of creating a trace file, use an LLM to generate code changes
    # based on the instruction
    
    # Example with OpenAI:
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": "You are a code generation assistant."},
    #         {"role": "user", "content": f"Implement the following: {instruction}"}
    #     ]
    # )
    # code = response.choices[0].message.content
    # 
    # # Write the generated code to appropriate files
    # # ...
    
    pass
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
