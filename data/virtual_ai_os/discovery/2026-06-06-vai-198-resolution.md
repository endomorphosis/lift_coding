# VAI-198 Resolution

Date: 2026-06-06
Source finding: `data/virtual_ai_os/discovery/2026-06-06-vai-198-codebase-scan-e8f8f357776a.md`
Evidence: `hallucinate_app/python/hallucinate_app/control_surface_policy.py:1027`
Kind: swallowed_exception_resolved

## Finding

The codebase scan flagged a bare `except Exception:` at line 1027 inside
`_serialize_ipfs_value()`.  The three `except Exception:` clauses in that
function's fallback chain (for `as_dict()`, `to_dict()`, and `asdict()`)
already logged the exception via `_logger.warning/debug(..., exc_info=True)`,
so the exceptions were not truly silently swallowed.  However, the bare
`except Exception:` pattern (without binding the exception to a variable) is a
recognised maintenance risk: it makes the code look like the exception is
ignored, and `exc_info=True` relies on the implicit `sys.exc_info()` context
rather than the concrete exception object.

## Resolution

- Changed all three `except Exception:` clauses to `except Exception as exc:`
  so the caught exception is explicitly bound.
- Updated the corresponding `_logger` calls from `exc_info=True` to
  `exc_info=exc`, passing the exception object directly.  This is unambiguous
  and survives any future refactor that might move log calls out of the bare
  except block.
- The fallback-chain design (try → log → next strategy) is correct and
  intentional; no further restructuring was needed.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exits with code 0.
