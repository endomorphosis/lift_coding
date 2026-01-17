# Agent Runner Example

This directory contains an example implementation of a custom agent runner that polls the dispatch repository for new issues and processes them.

## What's Included

- **`Dockerfile`**: Container image definition for the agent runner
- **`requirements.txt`**: Python dependencies
- **`runner.py`**: Main agent runner implementation (example/placeholder)

## Usage

This is a **reference implementation** that demonstrates the structure of a custom agent runner. The `runner.py` file contains placeholder logic that you should replace with your actual task processing implementation.

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

### Customizing the Runner

The `runner.py` file includes a `process_task()` function where you should implement your actual agent logic:

```python
def process_task(issue, metadata: dict) -> bool:
    # TODO: Replace this with your actual implementation
    # Examples:
    # - Clone the target repository
    # - Use an LLM to generate code changes
    # - Make the requested changes
    # - Run tests
    # - Create a PR with correlation metadata
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
