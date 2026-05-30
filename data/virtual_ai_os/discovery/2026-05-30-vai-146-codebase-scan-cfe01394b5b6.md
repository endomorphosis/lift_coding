# VAI-146 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: cfe01394b5b600bb0345c08fd14e1e8c9b19f8cf
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118
Priority: P2
Track: runtime

## Evidence

```text
# and became "XXX") must not cause unrelated errors to be treated as
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (VAI-146)

**Status: Resolved — False positive; upstream fix already applied.**

The evidence line `# and became "XXX") must not cause unrelated errors to be treated as`
was part of a comment block that explained why the `_SIMILAR_MIN_LEN` guard is applied to
the exact-match normalised path.  The "XXX" in the comment was the name of the old sentinel
token used in the pre-VAI-144 implementation of `_messages_similar`.

When VAI-144 replaced the `'XXX'` sentinel with a null byte (`'\x00'`), the comment was
updated simultaneously: the current code (line 1129) reads `"became the sentinel"` instead
of `"became 'XXX'"`.  Line 1118 itself — `return True` — is the early-return guard that
fires when `msg1 == msg2` (identical raw messages), which is correct and intentional:
identical messages are always similar, even when short, because there is no collision risk.

The existing test `test_identical_hex_only_messages_are_similar` (HAO-221) already covered
the observable behaviour.  A focused regression test
`test_identical_short_raw_message_returns_true_before_normalization` (VAI-146) has been
added to `test/test_error_monitor.py` to explicitly lock in the early-return semantics at
line 1118 and prevent the scan from re-filing this as unresolved.

