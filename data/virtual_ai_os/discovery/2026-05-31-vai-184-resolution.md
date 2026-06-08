# VAI-184 Resolution

Date: 2026-05-31
Source finding: `data/virtual_ai_os/discovery/2026-05-31-vai-184-codebase-scan-ef3c5f5d40a6.md`
Kind: annotated_followup

The scan flagged the docstring opening at
`hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:376`
with the evidence text:

```
"""_SIMILAR_SENTINEL must be a null byte, not the three-character token 'X' + 'XX' (HAO-227).
```

## Investigation

On review the finding is a historical artefact from an older snapshot.  The
current codebase already has the fix in place:

- `hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` line 799:
  `_SIMILAR_SENTINEL` holds the null-byte sentinel value (not the three-character `'X' + 'XX'` placeholder; fixed in VAI-144)
- `_SIMILAR_MIN_LEN = 10` ensures that messages whose entire content normalises
  to the single-character sentinel are never falsely conflated.
- `test_sentinel_is_single_null_byte_not_xxx` (line 375) explicitly asserts
  `len(sentinel) == 1` and `sentinel == '\x00'`, pinning the invariant introduced
  in VAI-144.

The docstring in the current file already uses the updated wording:
  `"""_SIMILAR_SENTINEL must be the null-byte sentinel introduced in VAI-144 (HAO-227).`

No source changes are required.  The finding does not represent a live bug.

## Resolution

- Verified `_SIMILAR_SENTINEL = '\x00'` in `error_monitor.py`.
- Verified test `test_sentinel_is_single_null_byte_not_xxx` asserts the null-byte
  value and that distinct hex-only messages are not falsely considered similar.
- No code or test changes needed; the fix from VAI-144 is already present and pinned.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py
# exit code 0 — PASS
```
