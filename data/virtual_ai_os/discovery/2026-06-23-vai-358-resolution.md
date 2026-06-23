# VAI-358 Resolution

The runner's todo-daemon poll exception path now logs traceback context and
returns that the external poll was attempted. This prevents tasks with
todo-daemon trace metadata from falling through to simulated completion when the
provider status poll raises.

Focused validation was added in `tests/test_agent_runner.py` to cover the
recoverable exception path, verify the task remains running, and confirm the
warning preserves exception details.
