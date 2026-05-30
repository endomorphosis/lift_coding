# HAO-226 Resolution

Date: 2026-05-30
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118
Status: resolved

## Finding

The original scan flagged a comment at line 1118 of `error_monitor.py` that read:

```python
# and became "XXX") must not cause unrelated errors to be treated as
```

The string `"XXX"` was a placeholder sentinel name left in a code comment after the
actual sentinel value (`'XXX'`) had been replaced by a null-byte sentinel (`'\x00'`)
in the VAI-144 fix.  This was an annotation-only issue — no runtime bug — but the
misleading comment could confuse future readers about the sentinel's identity and
length.

## Resolution

**`error_monitor.py` (already fixed):** The comment at the formerly-line-1118 location
(now line 1129 after nearby guard code was inserted by HAO-225) was already updated
prior to this worktree to read:

```python
# and became the sentinel) must not cause unrelated errors to be treated
```

No further edits to `error_monitor.py` were required.

**`test/test_error_monitor.py` (stale comments fixed):** Two test methods
(`test_short_msg2_not_falsely_matched` and `test_short_msg1_not_falsely_matched`)
contained inline comments that still referenced the old `"XXX"` sentinel with its
former length of 3:

```python
# msg2 is entirely an address — after normalisation it becomes "XXX" (len 3).
# "XXX" is shorter than _SIMILAR_MIN_LEN (10), so no substring match.
```

These were updated to accurately describe the current null-byte sentinel:

```python
# msg2 is entirely an address — after normalisation it becomes '\x00' (len 1).
# '\x00' is shorter than _SIMILAR_MIN_LEN (10), so no substring match.
```

The same pair of comments in `test_short_msg1_not_falsely_matched` was corrected
symmetrically.

## Validation

- `python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` passes.
- Existing focused tests in `test/test_error_monitor.py` remain correct:
  - `test_two_different_hex_only_messages_not_similar` – verifies `'\x00'` sentinel < `_SIMILAR_MIN_LEN`
  - `test_message_containing_sentinel_not_falsely_similar` – asserts `_SIMILAR_SENTINEL == '\x00'`
  - `test_short_msg2_not_falsely_matched` / `test_short_msg1_not_falsely_matched` – updated comments match actual sentinel
