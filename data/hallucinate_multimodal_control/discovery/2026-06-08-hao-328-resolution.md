# HAO-328 Resolution

Date: 2026-06-08
Task: HAO-328
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_code_issues.sh:229

## Finding

The scanner reported the generated `except Exception as e:\` block in
`fix_code_issues.sh`. That archived patch inserted a fallback
`create_webrtc_router()` implementation that caught all router construction
failures, logged them, and returned `None`, which could hide unexpected FastAPI
or registration errors.

## Fix

The generated fallback now validates `api_prefix` directly and returns `None`
only for a non-string value or a non-empty prefix that does not start with `/`.
Router construction itself is no longer wrapped in a broad exception handler, so
unexpected failures propagate to the caller instead of being silently disabled.

## Validation

```text
test -f external/ipfs_kit/archive/applied_patches/fix_code_issues.sh
# exit 0

bash -n external/ipfs_kit/archive/applied_patches/fix_code_issues.sh
# exit 0

git -C external/ipfs_kit diff --check -- archive/applied_patches/fix_code_issues.sh
# exit 0
```
