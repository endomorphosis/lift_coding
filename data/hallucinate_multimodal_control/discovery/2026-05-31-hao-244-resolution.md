# HAO-244 Resolution

Date: 2026-05-31
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Kind: annotated_followup (false positive)
Status: fixed

## Finding

The codebase scanner flagged line 307:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Analysis

The scanner flagged this line because of the word "todo" in the CLI flag name
`--objective-surplus-min-terms-per-todo` and variable `OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO`.
The preceding line 307 already contains an annotation added by MGW-191 and MGW-192:

```python
# scanner-resolved: MGW-191, MGW-192 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work marker).
```

The finding for HAO-244 was filed before that annotation was fully propagated, making it
a false positive. The comment has been updated to also reference HAO-244 so the scanner
recognises this line as fully reviewed.

## Conclusion

The word "todo" in `--objective-surplus-min-terms-per-todo` and
`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` refers to backlog task-board entries (the work-item
queue count threshold), not a deferred-work code annotation. No functional code change is
needed; the scanner-resolved comment was updated to add `HAO-244`.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```
Passed with exit code 0.
