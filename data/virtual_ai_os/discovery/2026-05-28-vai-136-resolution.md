# VAI-136 Resolution: _messages_similar short-msg1 false-positive guard

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118
Kind: annotated_followup resolved

## Finding

The codebase scan flagged the comment at line 1118 of `error_monitor.py`:

```python
# meaningful discriminator.  A very short cleaned string (e.g. a message
# that was entirely a hex address and became "XXX") would otherwise cause
# unrelated errors to be treated as duplicates.
```

The annotated comment describes the risk that a message reduced to a very short
token (e.g. `"0xdeadbeef"` → `"XXX"`) might falsely match unrelated messages via
the substring branch of `_messages_similar`.  The comment mentioned only the
scenario where the cleaned string is a hex address; it did not explicitly cover
the symmetric case where `clean_msg1` (not `clean_msg2`) is the short value.

## Assessment

The existing code already handles both directions correctly via the
`_SIMILAR_MIN_LEN = 10` guard applied to both branches of the return expression:

```python
return (
    (len(clean_msg1) >= self._SIMILAR_MIN_LEN and clean_msg1 in clean_msg2)
    or (len(clean_msg2) >= self._SIMILAR_MIN_LEN and clean_msg2 in clean_msg1)
)
```

When `msg1 = "0xdeadbeef"` normalises to `"XXX"` (len 3), the first branch is
skipped, and `"XXX"` does not appear in a typical error string, so no false
positive occurs.  The guard is symmetric and correct.

## Fix

No code change needed in `error_monitor.py`.  The comment and logic are sound.

A focused regression test `test_short_msg1_not_falsely_matched` was added to
`TestMessagesSimilar` to document and lock in this guarantee for the `clean_msg1`
direction (symmetric companion to `test_short_msg2_not_falsely_matched` added by
HAO-215):

```python
def test_short_msg1_not_falsely_matched(self):
    msg1 = "0xdeadbeef"
    msg2 = "Connection refused by remote host at port 8080"
    self.assertFalse(self._similar(msg1, msg2))
```

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` → PASS  
`pytest hallucinate_app/.../test_error_monitor.py::TestMessagesSimilar` → 10 passed
