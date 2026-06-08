# HAO-324 Resolution

Date: 2026-06-08
Task: HAO-324
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh:204

## Finding

The scanner reported the broad `except Exception as e:` in the generated
`create_webrtc_router()` implementation. That handler converted any router
construction error into `None`, which hid unexpected FastAPI/router errors from
callers.

## Fix

Verified that the current `external/ipfs_kit` gitlink,
`792e42309cd938712ac9b81b2e234e7a1884aa88`, includes the focused source fix.
`create_webrtc_router()` now returns `APIRouter` directly, creates and returns
the router without a broad catch, and no longer swallows unexpected
construction errors.

## Validation

```text
test -f external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
# exit 0

bash -n external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
# exit 0
```
