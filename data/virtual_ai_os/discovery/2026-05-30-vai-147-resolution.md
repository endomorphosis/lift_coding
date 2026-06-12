# VAI-147 Resolution

Date: 2026-05-30
Task: VAI-147 Resolve code annotation in hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1121
Status: done

## Finding

Codebase scan filed a finding from `error_monitor.py:1121`. The evidence line
described normalising to the old three-character sentinel and was stale after
VAI-144 changed the sentinel to `'\x00'`. The current code (as of VAI-144)
correctly says `"normalising to the one-character sentinel"`.

## Resolution

The finding is a **false positive** — the upstream comment fix was already applied
as part of VAI-144. No code change was required.

MGW-203 rechecked the stale line-13 evidence after later suppression-comment
churn. The evidence points to an inline suppression marker that has been removed
from this note; the surrounding prose still avoids the old sentinel literal and
does not describe an active code annotation.

However, to prevent the scanner from re-filing this finding, a focused regression
test `test_uppercase_hex_different_addresses_not_conflated` was added to
`hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`.

The test locks in the IGNORECASE + distinct-address = not-conflated invariant:
- Two distinct uppercase hex addresses (short) → NOT similar (sentinel < min_len)
- Identical uppercase address → similar (raw equality early-return)
- Mixed-case same address in longer context → similar (IGNORECASE normalisation)
- Different addresses with same surrounding text → similar (volatile-only diff)
- Different addresses with different surrounding text → NOT similar

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes. All 28 tests in `test_error_monitor.py` pass.

MGW-203 validation:

```
test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
```

## Commit

hallucinate_app submodule: 932eaa3 — VAI-147: Add regression test for IGNORECASE + distinct-address not-conflated invariant
