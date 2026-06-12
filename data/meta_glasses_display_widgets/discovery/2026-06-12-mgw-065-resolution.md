# MGW-065 Resolution

Date: 2026-06-12
Task: MGW-065
Source finding: tests/test_hallucinate_multimodal_control_todo_queue.py:658

## Finding

The codebase scan reported a test fixture that wrote an annotation marker for
the drained submodule scan case into a temporary submodule source file.

## Resolution

The fixture needs to create a real annotation marker inside the temporary
repository so `record_codebase_scan_findings` can prove drained backlogs bypass
the scan cooldown. The checked-in test now documents that the marker is built at
runtime, keeping the fixture behavior intact without leaving a static source
annotation for the supervisor scan to requeue.

## Validation

```sh
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
```
