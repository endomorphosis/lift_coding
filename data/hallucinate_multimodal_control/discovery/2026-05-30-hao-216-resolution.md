# HAO-216 Resolution

Date: 2026-05-30
Task: HAO-216
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118
Kind: annotated_followup → resolved

## Finding

The scanner flagged line 1118 with this fragment:

```python
# that was entirely a hex address and became "XXX") would otherwise cause
```

This was an incomplete comment hanging over a logic gap: the `_messages_similar`
equality branch (`if clean_msg1 == clean_msg2: return True`) had no min-length
guard.  Two entirely different errors whose messages each consisted solely of a
volatile token (e.g. bare hex addresses `"0xDEAD"` and `"0xBEEF"`, both
normalising to `"XXX"`) would incorrectly collapse into the same duplicate bucket.

## Fix Already Applied

Prior passes (HAO-219 through HAO-221) consolidated the logic and the current
code at line 1122 reads:

```python
if clean_msg1 == clean_msg2 and len(clean_msg1) >= self._SIMILAR_MIN_LEN:
    return True
```

The min-length guard now applies uniformly to the equality branch as well as both
substring branches.  The comment block (lines 1116-1121) was rewritten to be
complete and self-contained rather than a dangling fragment.

Note: the `or msg1 == msg2` escape hatch proposed in the original HAO-216
attempt-1 resolution is unnecessary because the identical-message early-return
at line 1109 (`if msg1 == msg2: return True`) guarantees `msg1 != msg2` by the
time we reach the cleaned-string comparison, making that extra clause dead code.

## Gap Addressed (Attempt 2)

Two focused tests specifically documenting the HAO-216 equality-branch behaviour
were missing from the test suite (the HAO-221 tests cover the same paths via
hex-only messages; these tests add coverage via timestamps and longer messages):

1. **test_equality_branch_requires_min_len** — two bare timestamps that both
   normalise to `"XXX"` must NOT be treated as similar; the equality branch
   is blocked by the min-length guard.
2. **test_equality_branch_passes_with_long_normalised_string** — two messages
   differing only in a hex address normalise to the same long string and MUST
   be treated as similar; verifies the guard does not over-block.

## Changes

- `hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`:
  Added `test_equality_branch_requires_min_len` and
  `test_equality_branch_passes_with_long_normalised_string` (both tagged HAO-216).

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes.  Both new tests pass.  No production code was modified; the underlying
fix was already in place.
