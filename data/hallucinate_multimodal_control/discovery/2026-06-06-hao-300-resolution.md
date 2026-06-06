# HAO-300 Resolution

Date: 2026-06-06
Task: HAO-300
Source: hallucinate_app/python/hallucinate_app/control_surface_store.py:513

## Finding

The HAO codebase scanner flagged two bare `except Exception: pass` blocks in the
`_json_safe` helper inside `control_surface_store.py`. Exceptions thrown by
`as_dict()` and `to_dict()` were silently discarded with no logging, making
failures invisible in production.

## Root Cause of Implementation Failures (HAO-303 context)

All three HAO-300 implementation attempts were terminated with signal 15 (SIGTERM)
during the commit/merge phase (`python3 -m
ipfs_accelerate_py.agent_supervisor.llm_merge_resolver_fallback`). The merge
resolver module depends on `ipfs_kit_py.backends`, which is unavailable in this
environment. The resolver hung waiting for the module and was killed by the
implementation daemon's timeout watchdog.

HAO-299 landed the same fix (lines 508 and 513) as a side effect of its broader
`_json_safe` improvement before HAO-300 could complete, so the underlying bug was
already corrected by the time HAO-303 was filed.

## Resolution

The fix applied by HAO-299 (`commit 1740d5f` in the hallucinate_app submodule):

```diff
-        except Exception:
-            pass
+        except Exception as exc:  # noqa: BLE001
+            _log.debug("_json_safe: as_dict() failed for %r: %s", type(value).__name__, exc)
```

Both `as_dict()` and `to_dict()` fallback branches now log at DEBUG level instead
of silently swallowing the exception. The `# noqa: BLE001` suppressor is
intentional — these are expected fallback paths, not error conditions.

HAO-303 adds a docstring to `_json_safe` to document the cascading fallback
behaviour so the scanner does not re-file this pattern as an unreviewed exception.

## Validation

```bash
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_store.py
```
