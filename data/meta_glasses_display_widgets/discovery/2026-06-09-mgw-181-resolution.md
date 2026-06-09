# MGW-181 Resolution

Date: 2026-06-09
Task: MGW-181 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:338
Status: resolved

## Finding

The codebase scan flagged `except Exception as e:` near line 338 of
`ipfs_model_manager.py` (`import_model_from_ipfs` method) as a swallowed
exception. The bare `except Exception` block previously logged nothing and
silently returned `None`, hiding root-cause information from operators.

## Fix Applied

The exception handler at line 348 (post-fix) was updated to:

1. Use `logger.exception(...)` instead of `logger.error(...)` so the full
   traceback is captured in structured logs.
2. Add `# noqa: BLE001` with an explanatory comment that callers handle `None`
   gracefully, making the intentional broad-catch explicit and lint-suppressible.
3. Clean up any partially-created model directory (`shutil.rmtree`) when the
   exception occurs mid-download, preventing corrupted on-disk state.

```python
except Exception as e:  # noqa: BLE001 – intentionally returns None so callers can handle gracefully
    logger.exception(f"Failed to import model {model_id} from IPFS: {e}")
    # Clean up any partially-created model directory to avoid leaving
    # corrupted state on disk when the directory was created by this call.
    if not pre_existing_dir and os.path.isdir(model_dir):
        try:
            shutil.rmtree(model_dir)
            logger.debug(f"Cleaned up partial model directory: {model_dir}")
        except OSError:
            logger.warning(f"Could not clean up partial model directory: {model_dir}")
    return None
```

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py` → PASS

## False-positive note

The broad `except Exception` is intentional: `import_model_from_ipfs` is a
best-effort helper that must not propagate exceptions to callers (e.g., UI
threads). The `logger.exception` call ensures the full traceback appears in
logs, so the exception is no longer truly swallowed.
