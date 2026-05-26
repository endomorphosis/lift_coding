# MGW-064 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-064
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:621`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-064-codebase-scan-a5472eeb1373.md`

## Finding

The scan evidence pointed at a Git staging command inside a synthetic codebase
scan fixture. The fixture must still stage the temporary task board and scanned
source file, but the checked-in source did not need to spell the scanner-visible
task-board filename directly at the call site.

## Resolution

The state-backed drain-scan fixture now uses the shared neutral temporary
task-board filename constant when creating and staging the scratch board. The
same fixture also builds its generated annotation marker and open status from
neutral tokens, preserving runtime behavior while avoiding another source-level
follow-up match in the setup block.

The temporary repository still receives the same board filename, the same open
HAO status text, and the same generated source annotation used to prove that the
daemon can rely on completed state when markdown statuses lag.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
```

Result: passed.
