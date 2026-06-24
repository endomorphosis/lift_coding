# VAI-211 Attempt 1 Validation

Date: 2026-06-24
Task: VAI-211
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984
Finding: swallowed_exception

## Result

The flagged path in `AdvancedFilecoinStorage._get_chain_height()` is already
resolved in the checked-out `external/ipfs_kit` submodule. The current code
catches expected cache-height conversion failures with:

```python
except (TypeError, ValueError) as e:
    logger.warning(f"Invalid cached Filecoin height {chain_height!r}: {e}")
```

It also catches expected cached stats read failures separately with
`except (OSError, json.JSONDecodeError) as e:` and leaves unexpected live API
exceptions to propagate. This matches the existing VAI-211 resolution note and
the submodule history entry `2570146b VAI-212: Resolve implementation
retry-budget failure for VAI-211`.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
exit 0
```
