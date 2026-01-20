# PR-075 work log

## Checklist
- [ ] Identify where task state transitions occur (service + API).
- [ ] Identify existing notification creation helpers.
- [ ] Add integration: on task transition, create + dispatch notification.
- [ ] Add tests for completion and failure paths.
- [ ] Run `python -m pytest -q`.

## Payload sketch
- `type`: `agent.task.completed` / `agent.task.failed`
- `task_id`
- `status`
- `message`
- `pr_url` (optional)
- `reason` (optional)

