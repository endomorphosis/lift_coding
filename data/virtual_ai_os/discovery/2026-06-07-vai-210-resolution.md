# VAI-210 Resolution

Date: 2026-06-07
Task: VAI-210
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/add_pins_monkey_patch.py:39

## Finding

The dynamic import fallback caught every `Exception`, printed only the exception
message, and returned `None`. That collapsed unexpected module-load failures into
the same result as an ordinary missing import path.

## Fix

The dynamic import fallback now handles only expected discovery failures:

- missing dependencies or import errors
- missing source files or filesystem load errors
- an import spec that cannot be built
- a loaded module that does not define `IPFSSimpleAPI`

Unexpected failures raised while executing `high_level_api.py` now propagate with
their original traceback instead of being swallowed by the fallback.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/applied_patches/add_pins_monkey_patch.py` -> exit 0

An additional `python3 -B` harness forced the fallback import path and verified
that an unexpected dynamic loader `RuntimeError` propagates instead of returning
`None` -> exit 0.
