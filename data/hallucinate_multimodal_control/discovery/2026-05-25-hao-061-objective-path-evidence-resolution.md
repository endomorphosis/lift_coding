# HAO-061 Objective Path Evidence Resolution

Date: 2026-05-25
Task: HAO-061
Goal id: VAIOS-G010

## Finding

The first objective-gap scan treated `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` as missing evidence because the scanner deliberately skipped the objective document's prose to avoid self-satisfying free-text terms.

That behavior was correct for prose evidence, but too strict for concrete path evidence. Existing tracked paths should count by file existence even when the scanner ignores their contents.

## Resolution

The objective evidence index now counts safe repo-relative path terms as present when the target path exists. Regression coverage adds a path evidence term to the objective-goal scan test, so this gap does not reappear.

## Validation

```bash
PYTHONPATH=external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -k objective_goal
```
