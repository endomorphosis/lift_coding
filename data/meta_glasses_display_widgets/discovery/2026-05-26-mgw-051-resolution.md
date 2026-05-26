# MGW-051 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-051
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:159`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-051-codebase-scan-0886ebe3b4a6.md`

## Finding

The scan evidence pointed at a synthetic `PortalTask` status fixture in the HAO
queue tests. The fixture must still model an open backlog task so nested
submodule commit behavior is exercised with realistic daemon metadata.

## Resolution

The direct open-task status constructor argument had already been neutralized by
the shared `PENDING_TASK_STATUS` token. This task now centralizes synthetic
open-task metadata in `_pending_task_metadata()`, keeping the behavior unchanged
while removing annotation-shaped status wiring from the individual `PortalTask`
fixtures.

Adjacent open MGW findings for different constructor path wiring were left
unchanged so the supervisor-fed backlog remains separately parseable.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
```
