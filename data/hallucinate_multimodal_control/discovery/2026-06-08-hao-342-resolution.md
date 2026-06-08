# HAO-342 Resolution

Date: 2026-06-08
Task: HAO-342
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/ipfs_dht_operations.py:279

## Finding

The scan fingerprint `7621188cf0a5` flagged a bare `except:` while decoding
the DHT `VALUE` response `Extra` field in `DHTOperations.get_value()`. That
path should tolerate malformed DHT records, but the bare handler also hid
unexpected exceptions and gave operators no evidence when a malformed record was
skipped.

## Fix

The checked-out submodule commit
`3ff6d08ce6bd573f1d04d3876d03ed353154ea0e` contains the scoped fix for this
path. The DHT `Extra` decode now uses strict base64 validation, catches only
decode or payload-shape failures from that operation (`binascii.Error`,
`TypeError`, and `ValueError`), records `decode_errors`, logs the malformed
payload with the response index, and reports failure when all value payloads are
malformed. Unrelated exceptions are no longer swallowed by the inner handler.

## Validation

Result: passed.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/ipfs_dht_operations.py
```
