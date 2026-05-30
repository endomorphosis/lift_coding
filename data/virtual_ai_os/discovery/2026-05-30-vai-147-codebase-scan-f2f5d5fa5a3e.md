# VAI-147 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: f2f5d5fa5a3eabee79769615ad128e7b3e2d9184
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1121
Priority: P2
Track: runtime

## Evidence

```text
# normalising to the three-character token "XXX") are not conflated.
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (VAI-147)

**Status: Resolved — False positive; upstream fix already applied.**

The evidence line `# normalising to the three-character token "XXX") are not conflated.`
was part of a comment block (lines 1130–1132) explaining why the `_SIMILAR_MIN_LEN` guard
applies to the substring-match path of `_messages_similar`.  The "XXX" in that comment was
the name of the old sentinel token used before VAI-144 was landed.

When VAI-144 replaced the hardcoded `'XXX'` sentinel with a null byte (`'\x00'`), the
inline comment was updated simultaneously: the current code at line 1132 reads
`"normalising to the one-character sentinel"` instead of `"normalising to the
three-character token 'XXX'"`.  The `_SIMILAR_PATTERN` comment block at lines 1120–1124
correctly documents that `re.IGNORECASE` causes uppercase hex (e.g. `0xDEADBEEF`) to be
normalised and that the null-byte sentinel prevents false-positive similarity matches.

The relevant logic is exercised by the `TestMessagesSimilar` suite; notably:
- `test_hex_case_insensitive` (line 226) — IGNORECASE normalisation for deduplication
- `test_two_different_hex_only_messages_not_similar` (HAO-221) — distinct hex-only
  messages not conflated

A focused regression test `test_uppercase_hex_different_addresses_not_conflated` (VAI-147)
has been added to `test/test_error_monitor.py` to specifically lock in the IGNORECASE +
distinct-address = not-conflated invariant and prevent the scan from re-filing this finding.
