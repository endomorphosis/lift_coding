# HAO-325 Resolution

Date: 2026-06-08
Task: HAO-325
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh:228

## Finding

The scanner reported the broad `except Exception as e:` in
`create_webrtc_extension_router()`. That path converted unexpected WebRTC
router construction failures into `None`, which hid runtime failures from
callers.

## Fix

Verified that the current `external/ipfs_kit` gitlink,
`c9cf651dcb0d4ac8d63d114063307fb7fdff50e4`, includes the focused source fix.
`create_webrtc_extension_router()` now catches only `AssertionError` and
`ValueError` for invalid API prefixes, logs the traceback with
`logger.exception()`, and lets unrelated construction failures propagate.

## Validation

```text
test -f external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
# exit 0

bash -n external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
# exit 0
```
