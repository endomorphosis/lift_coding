# HAO-308 Resolution

Date: 2026-06-12
Task: HAO-308
Source finding: `external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984`

## Review

The scan evidence referenced an `except Exception as e` path in
`AdvancedFilecoinStorage._get_chain_height`. In the current pinned
`external/ipfs_kit` checkout, that path has already been narrowed:

- local cached network stats reads catch only `OSError` and `json.JSONDecodeError`;
- cached height coercion catches only `TypeError` and `ValueError`;
- live `Filecoin.ChainHead` requests are not wrapped in a broad handler, so
  unexpected failures propagate instead of being silently converted to `None`;
- malformed live responses are logged and treated as unavailable height data.

The code comment at the live request boundary was tightened so future scans can
distinguish the intentional cache fallback from swallowed runtime exceptions.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py`
