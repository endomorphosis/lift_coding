# HAO-290 Resolution: Swallowed Exception at Line 473

Date: 2026-06-05
Task: HAO-290
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:473

## Finding

`_resolve_ipfs_logic_api` used a broad `except Exception:` to handle the
optional import of `ipfs_datasets_py.logic.api`. This swallowed any unexpected
error that could occur during the import (e.g., a `SyntaxError` or
`AttributeError` inside the module), making those failures invisible at runtime.

## Fix

Narrowed the exception clause from `except Exception:` to `except ImportError:`.
`ImportError` (and its subclass `ModuleNotFoundError`) is the correct and only
expected exception when an optional dependency is not installed. All other
exceptions propagate normally so genuine bugs in the dependency surface
immediately.

## Status

- Validation: `python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py` passes.
- False positive: No; bare `except Exception:` on an import is a genuine
  maintenance risk.
