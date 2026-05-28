# HAO-193 Resolution: False Positive Annotation at run_vai_mgw_hao_supervisors.sh:92

Date: 2026-05-28
Task: HAO-193
Source finding: 2026-05-28-hao-193-codebase-scan-167e512adcc4.md

## Finding

The codebase scanner flagged line 92 of `scripts/run_vai_mgw_hao_supervisors.sh`
as an `annotated_followup` because the argument name and variable both contain
the substring "todo":

```bash
  --objective-surplus-min-terms-per-todo "$OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO"
```

## Assessment: False Positive

`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` is a shell variable that wires a numeric
threshold (minimum search terms per task-board item) into the common argument
list shared by the VAI, MGW, and HAO supervisor processes. The word "todo" in
the name refers to task-board items (backlog entries), **not** a `# TODO` code
annotation. All three supervisor scripts correctly handle this argument. This
matches the same false-positive pattern resolved in HAO-190, HAO-191.

## Fix Applied

A clarifying inline comment was added immediately above the flagged line so the
scanner can distinguish it from an actual code annotation on future scans:

```bash
  # Not a code annotation; "todo" in the flag name refers to task-board items.
  --objective-surplus-min-terms-per-todo "$OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO"
```

## Validation

```
test -f scripts/run_vai_mgw_hao_supervisors.sh
bash -n scripts/run_vai_mgw_hao_supervisors.sh
```

Both exit 0 — file present and syntax clean.
