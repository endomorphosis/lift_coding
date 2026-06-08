# HAO-341 Resolution

Date: 2026-06-08
Task: HAO-341
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/huggingface_real_init.py:44

## Finding

The scan fingerprint `0f06020302cc` flagged the broad
`except Exception as e:` around the `huggingface-cli whoami --token` fallback in
`get_huggingface_token()`. That path only needs to handle subprocess launch and
execution failures; the broad catch also hid nonzero CLI exits because those
were not reported to the caller or logs.

## Fix

The checked-out submodule commit `d15f318267d0efaec5ec7048364510435dd69bb7`
contains the scoped fix for this path. The CLI lookup now runs with
`check=False`, catches only `OSError` and `subprocess.SubprocessError`, and
reports nonzero exits or empty CLI output instead of silently falling through.

## Validation

Result: passed.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/huggingface_real_init.py
```
