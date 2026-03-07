# Agent Orchestration

## What "agent" means here
A background system that can:
- take a task description
- modify code / propose changes
- open or update a PR
- report progress and blockers

## Integration approaches
1. Copilot coding agent (if available in your environment)
2. Custom agent runner (e.g., containerized workflows with repo checkout)
3. Hybrid: agent drafts; human reviews; tool merges under policy

## MCP++ integration track (IPFS servers)
To support MCP-native agent execution, add a dedicated provider track using
`endomorphosis/Mcp-Plus-Plus` and the server implementations from:
- `endomorphosis/ipfs_datasets_py`
- `endomorphosis/ipfs_kit_py`
- `endomorphosis/ipfs_accelerate_py`

Plan details and rollout sequencing are captured in:
- `implementation_plan/prs/PR-009-mcp-plus-plus-ipfs-integration.md`

## Agent task lifecycle
- Created -> Running -> Needs input -> Completed -> Failed
Each state change can trigger a notification (profile throttling).

## Commands
- “Ask agent to fix issue 918”
- “Ask agent to address review comments on PR 412”
- “Pause agent”
- “Summarize agent progress”

## Safety
- Agents never auto-merge without explicit user approval + policy
- Agents operate on least-privileged tokens
- Always store a trace: prompt, tools used, commits, PR links
