# HAO-141 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-141-codebase-scan-feb489a0c62a.md

## Finding

The codebase scan flagged `src/handsfree/ipfs_kit_adapters.py` because the
`resolve()` adapter still ended in a `NotImplementedError` placeholder when the
top-level `ipfs_kit_py.resolve` helper was absent.

## Resolution

The adapter now falls back to concrete runtime surfaces for name resolution:
canonical backend methods (`resolve`, `name_resolve`, `ipfs_name_resolve`) and
then the documented high-level `IPFSSimpleAPI.resolve` surface. If none are
available, it raises `IPFSKitUnavailableError` with the missing surfaces listed.

## Validation

Passed from the HAO-141 worktree:

```bash
python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
PYTHONPATH=src pytest tests/test_ipfs_kit_adapters.py -q
```
