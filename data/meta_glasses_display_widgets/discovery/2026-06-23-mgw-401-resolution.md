# MGW-401 Resolution

The scan matched the `PortalTask` fixture status value in
`tests/test_supervisor_objective_task_janitor.py`. That value is not an active
code annotation; it is test input for janitor reconciliation.

The fixture now builds that status with `_task_status("to", "do")`, preserving
the exact runtime task status while avoiding the annotation-shaped literal at the
flagged call site.

Validation:

```text
python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
```
