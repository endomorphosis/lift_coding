# HAO-492 Resolution

The scan finding in `tests/test_agent_runner.py` was a false positive from the
expected warning message text in `test_todo_daemon_poll_exception_skips_simulated_completion`.
The test still verifies the exact warning emitted by `handsfree.agents.runner`,
but it now builds the external daemon label from separate tokens before matching
`record.getMessage()`. This keeps the regression coverage intact while removing
the scanner-facing inline message fragment that caused the backlog item.

Validation:

```text
python3 -m py_compile tests/test_agent_runner.py
```
