# PR-028: External agent runner setup guide (docs + infra)

## Goal
Provide documentation and infrastructure setup guide for running an external agent (Copilot agent, workflow automation, or custom runner) that processes dispatched agent tasks.

## Background
The system can now:
- Dispatch agent tasks by creating GitHub issues (`github_issue_dispatch` provider)
- Track task state via webhook correlation when PRs are opened
- Emit notifications for task lifecycle events

What's missing:
- An actual agent runner that monitors dispatch issues and performs work
- Documentation for setting up such a runner
- Configuration examples for different runner types

## Scope (Docs + Infra as Code)
This PR is primarily documentation and configuration, not code changes to the handsfree backend.

- **Documentation**:
  - Create `docs/agent-runner-setup.md` with:
    - Overview of agent task dispatch flow
    - Options for agent runners (GitHub Actions, Copilot agent, custom runner)
    - Setup instructions for each runner type
    - Configuration examples and required permissions
    - Troubleshooting guide
  
- **GitHub Actions Workflow Example**:
  - Add `.github/workflows/agent-runner-example.yml` (disabled by default)
  - Demonstrates how to monitor dispatch issues and perform work
  - Shows how to open PRs that correlate back to tasks
  - Includes required secrets and permissions documentation

- **Docker Compose for Custom Runner** (optional):
  - Add `docker-compose.agent-runner.yml` with example custom runner
  - Shows how to poll dispatch repo for new issues
  - Demonstrates task processing and PR creation
  - Can be used for local testing and deployment

## Non-goals
- Building a production-ready agent runner (that's a separate project)
- Modifying the handsfree backend API (dispatch already works)
- Creating a hosted agent service (out of scope)
- Advanced agent orchestration or queueing systems

## Acceptance criteria
- `docs/agent-runner-setup.md` exists with clear setup instructions
- GitHub Actions workflow example is provided (disabled by default)
- Documentation includes required GitHub permissions and secrets
- At least one working example runner implementation (Actions or Docker)
- README updated to reference agent runner setup guide
- Tests remain green (no backend code changes)

## Implementation notes
- Focus on documentation quality and examples
- Provide multiple options (Actions, Copilot, custom) to suit different deployments
- Include security considerations (bot account, token scoping, etc.)
- Reference existing webhook correlation mechanism in `api.py`
- Link to PR-016 and PR-022 tracking docs for context

## Related PRs
- PR-016: Agent delegation integration (github_issue_dispatch provider)
- PR-022: Agent delegation polish (auto-start, webhook correlation)
- PR-008: Agent orchestration stub (original agent task model)

## Example Runner Types

### Option 1: GitHub Actions Workflow
- Trigger: issue labeled `copilot-agent`
- Action: Process issue, create PR with task metadata in description
- Backend correlates PR to task via metadata

### Option 2: GitHub Copilot Agent (if available)
- Copilot monitors dispatch repo issues
- Copilot processes instruction and opens PR
- Backend correlates via PR-issue reference

### Option 3: Custom Runner (Docker + Python)
- Polls dispatch repo for new issues (GitHub API)
- Processes task using LLM or automation
- Opens PR with correlation metadata
- Can run on-prem or in cloud

## Configuration Requirements

All runners need:
- GitHub token with repo permissions (read issues, create PRs)
- Access to dispatch repository (e.g., `endomorphosis/lift_coding_dispatch`)
- Ability to create PRs that reference dispatch issues
- Knowledge of task metadata format for correlation

## Deployment Considerations

- **Security**: Use dedicated bot account, not personal tokens
- **Rate Limiting**: Respect GitHub API limits when polling
- **Concurrency**: Handle multiple dispatch issues concurrently if possible
- **Error Handling**: Report failures back to dispatch issue (comments)
- **Monitoring**: Log processing status for observability
