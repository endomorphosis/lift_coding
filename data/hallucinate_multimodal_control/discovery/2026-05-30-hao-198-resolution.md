# HAO-198 Resolution

Date: 2026-05-30
Source: scripts/virtual_ai_os_todo_supervisor.py:161
Status: resolved

## Finding

The codebase scan flagged line 161 of `scripts/virtual_ai_os_todo_supervisor.py`:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

The scanner detected "todo" in the CLI argument name string and filed an
`annotated_followup` finding.  The same pattern appeared on line 159
(`"--objective-todo-vector-index-path"`) and in the module-level constants
on lines 16–19.

## Root Cause

The CLI flag names `--objective-todo-vector-index-path` and
`--objective-surplus-min-terms-per-todo` are legitimate daemon argument names
where "todo" refers to task-board items, not code annotations.  A previous
author obfuscated these strings using Python concatenation
(`"to" + "do"`) to prevent self-detection, but the scanner resolves constant
folding and still flagged the resulting strings.

## Resolution

Replaced all concatenated string literals with plain string literals so the
code reads naturally and consistently with the approach used in
`scripts/hallucinate_multimodal_control_todo_supervisor.py` (HAO-197):

- Line 17: `"19-virtual-ai-os-submodule-integration." + "to" + "do.md"` →
  `"19-virtual-ai-os-submodule-integration.todo.md"`
- Line 19: `"--" + "to" + "do" + "-path"` → `"--todo-path"`
- Line 159: `"--objective-" + "to" + "do-vector-index-path"` →
  `"--objective-todo-vector-index-path"`
- Line 161: `"--objective-surplus-min-terms-per-" + "to" + "do"` →
  `"--objective-surplus-min-terms-per-todo"`

These are domain terms ("todo" = task-board item), not code action items.

## Validation

- `python3 -m py_compile scripts/virtual_ai_os_todo_supervisor.py` passes.
- Runtime behaviour is unchanged: the concatenated and plain forms evaluate to
  identical strings, so no daemon arguments are affected.
