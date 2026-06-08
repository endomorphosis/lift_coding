# VAI-247 Resolution

Date: 2026-06-08
Task: VAI-247 - Review swallowed exception path in fix_concise.sh:210
Source: external/ipfs_kit/archive/applied_patches/fix_concise.sh:210
Kind: swallowed_exception
Status: fixed

## Finding

The codebase scan fingerprint `56cf393d22a0` flagged the generated
`create_webrtc_router()` helper in `fix_concise.sh` because it caught every
`Exception`, logged only the string form, and returned `None`. If this archived
patch script were rerun, router construction failures could be hidden and later
appear as a less specific missing-router failure.

## Fix

Removed the broad handler from the generated helper and made its return type
`APIRouter`. Router construction now fails at the source instead of converting
setup errors into `None`.

## Validation

```
test -f external/ipfs_kit/archive/applied_patches/fix_concise.sh
bash -n external/ipfs_kit/archive/applied_patches/fix_concise.sh
```

Result: PASS (exit code 0).
