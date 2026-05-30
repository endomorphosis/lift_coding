# HAO-221 Resolution

Date: 2026-05-30
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1119
Kind: bug_fix

## Finding

The annotation at line 1119 warned that a very short cleaned string (e.g. a bare
hex address normalising to "XXX") could cause unrelated errors to be treated as
duplicates. The `_SIMILAR_MIN_LEN` guard was already applied to the substring-match
path, but the exact-match path (`if clean_msg1 == clean_msg2: return True`) had no
such guard. Two different hex-address-only messages (e.g. "0xdeadbeef" and
"0xcafebabe") both normalise to "XXX" and the old code would wrongly return True.

## Fix

1. Added a raw-message identity short-circuit: `if msg1 == msg2: return True` fires
   first so that identical raw messages are always treated as similar.
2. Applied the `_SIMILAR_MIN_LEN` guard to the exact-match path as well, so two
   different short messages that happen to normalise to the same short token are no
   longer falsely merged.

## Validation

- `python3 -m py_compile` passes.
- Two new focused tests added to `TestMessagesSimilar`:
  - `test_two_different_hex_only_messages_not_similar` — asserts False for
    "0xdeadbeef" vs "0xcafebabe" (HAO-221 regression guard).
  - `test_identical_hex_only_messages_are_similar` — asserts True when both
    arguments are the same raw string, even if short.
- All 16 `TestMessagesSimilar` tests pass.
