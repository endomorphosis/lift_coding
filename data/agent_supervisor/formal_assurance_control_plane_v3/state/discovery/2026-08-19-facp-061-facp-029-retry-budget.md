# FACP-061 Validation Retry-Budget Finding: FACP-029

Date: 2026-08-19
Source task: FACP-029
Follow-up task: FACP-061
Retry budget: 3
Observed consecutive validation failures: 4

## Evidence

- Failed command: `export PYTHONPATH="$PWD"/Mcp-Plus-Plus:"$PWD"/external/ipfs_accelerate:"$PWD"/external/ipfs_datasets:"$PWD"/external/ipfs_kit:"$PWD"/swissknife; python3 -m pytest test/formal_assurance/test_facp_029_swissknife_browser_vectors.py -q`
- Attempts: 1, 2, 3, 4
- Logs: /home/barberb/lift_coding/.worktrees/formal-assurance-control-plane/data/agent_supervisor/formal_assurance_control_plane_v3/state/lane-1/implementation_logs/facp-029-attempt-1.log, /home/barberb/lift_coding/.worktrees/formal-assurance-control-plane/data/agent_supervisor/formal_assurance_control_plane_v3/state/lane-1/implementation_logs/facp-029-attempt-2.log, /home/barberb/lift_coding/.worktrees/formal-assurance-control-plane/data/agent_supervisor/formal_assurance_control_plane_v3/state/lane-1/implementation_logs/facp-029-attempt-3.log, /home/barberb/lift_coding/.worktrees/formal-assurance-control-plane/data/agent_supervisor/formal_assurance_control_plane_v3/state/lane-1/implementation_logs/facp-029-attempt-4.log

- Validation attempted: `True`
- Validation return code: `4`
- Validation error: `validation_command_failed`
- Validation reason: `declared_validation_failed`
- Failed tests: not recorded
- Failed test paths: not recorded
- Validation target paths: not recorded
- Failure summary: [failure-head-omitted original_bytes=123 sha256=84ea9a270c46924441662443f61513b958e571f6655646b8b6400c2171044d89]
- Coverage errors: not recorded
- Configuration detail: not recorded

## Guardrail Result

The accelerator backlog refinery classified this as backlog work instead of
allowing another implementation attempt to loop on the same failure. The source
task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended for normal daemon parsing.

## Disposition (FACP-061)

- Status: **completed**
- Attempt: 3
- Root cause: inherited validation debt — Python harness required by Validation was
  omitted from FACP-029 Outputs, so admission dropped it and the gate failed with
  `file or directory not found`. Untracked restores were deleted by out-of-scope
  restore before proposal collection; FACP-061 attempt 2 passed local/daemon
  validation after staging, but deliverables were not durable across the next
  worktree.
- Repair: restore SwissKnife vector/TS outputs and stage the harness so scope
  adjudication retains the explicit validation target (`EXPLICIT_VALIDATION_TARGET`).
- Repair evidence: `2026-08-19-facp-061-facp-029-retry-budget-repair.md`
- Validation: `7 passed` for `test/formal_assurance/test_facp_029_swissknife_browser_vectors.py`
- FACP-029 may be released from strategy `blocked_tasks`.
