# VAI-214 Resolution

Date: 2026-06-07
Task: VAI-214
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245

## Finding

The mock/gateway deal lookup in `_find_deals_for_cid()` caught every exception
while reading local deal JSON files and silently skipped failures. A malformed,
unreadable, or structurally invalid deal file could therefore hide data quality
problems and still make `get_content_health()` report that no deals exist.

## Fix

The mock deal scan now:

- handles only expected file-read, text decode, and JSON parse failures;
- logs the skipped deal file path and error before continuing;
- validates that decoded deal JSON is an object before calling `.get()`;
- logs and skips non-object JSON deal records.

This preserves the tolerant mock scan behavior while making skipped deal files
observable.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py` -> exit 0

An additional `python3` harness loaded `advanced_filecoin.py`, created temporary
mock deal files for valid, invalid JSON, invalid text encoding, non-object JSON,
and non-matching deal records, and verified that `_find_deals_for_cid()` returned
only the valid matching deal while emitting warnings for the invalid files ->
exit 0.
