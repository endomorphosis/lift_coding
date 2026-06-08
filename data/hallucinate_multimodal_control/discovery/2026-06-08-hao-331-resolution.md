# HAO-331 Resolution

Date: 2026-06-08
Task: HAO-331
Kind: stale_scan_resolution
Source: external/ipfs_kit/archive/applied_patches/fix_ipfs_model.py:210

## Finding

The codebase scanner reported a placeholder runtime path in
`external/ipfs_kit/archive/applied_patches/fix_ipfs_model.py` with evidence from
the fallback `raise NotImplementedError("Could not find a suitable method to add content")`
branch.

## Resolution

The pinned `external/ipfs_kit` submodule commit already contains the focused
runtime fix from commit `e766d57a` (`VAI-251`). The minimal `add_content`
fallback now searches compatible add methods on both `self` and `self.ipfs`,
supports awaitable and synchronous implementations, falls back to IPFS command
methods when available, and reports the attempted method list in a `RuntimeError`
only after no usable runtime path is found.

The current line 210 is an early `return None` from the local method-dispatch
helper when a candidate owner or method is unavailable. The stale
`NotImplementedError` placeholder branch is no longer present in the checked-out
source.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_ipfs_model.py
# exit 0
```
