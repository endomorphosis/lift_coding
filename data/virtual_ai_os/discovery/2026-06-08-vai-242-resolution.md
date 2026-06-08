# VAI-242 Resolution

Date: 2026-06-08
Task: VAI-242 - Review swallowed exception path in fix_all_remaining_issues.sh:204
Source: external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh:204
Kind: swallowed_exception
Status: fixed

## Finding

The codebase scan fingerprint `1e9236e8f40d` flagged the generated
`create_webrtc_router()` helper in `fix_all_remaining_issues.sh` because it
caught every `Exception`, logged only the string form, and returned `None`.
That could hide router construction failures when this archived patch script is
rerun, then surface later as a less specific `None` router error.

## Fix

Removed the broad handler from the generated helper and made its return type
`APIRouter`. Router construction now fails at the source instead of converting
setup errors into `None`.

## Validation

```
test -f external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
bash -n external/ipfs_kit/archive/applied_patches/fix_all_remaining_issues.sh
```

Result: PASS (exit code 0).
