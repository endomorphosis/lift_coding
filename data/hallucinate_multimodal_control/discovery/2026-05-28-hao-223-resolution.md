# HAO-223 Resolution

Date: 2026-05-28 (attempt 1), 2026-05-30 (attempt 2)
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py
Kind: swallowed_exception
Status: fixed

## Fix (attempt 2)

Two additional bare `except:` clauses remained after attempt 1:

1. **Line ~625** (temp index file cleanup in `finally` block): replaced bare
   `except: pass` with `except OSError as e: logger.debug(...)` so only
   filesystem errors are caught and the cleanup failure is surfaced at debug
   level. Mirrors the pattern already applied to the metadata-file cleanup.

2. **Line ~733** (pickle-then-faiss load fallback): replaced bare `except:`
   with `except Exception as e: logger.debug(...)` before falling back to
   `faiss.read_index`. Signals the pickle failure reason without swallowing
   `KeyboardInterrupt`/`SystemExit`.

## Fix (attempt 1)

Replaced bare `except:` with `except OSError as e:` and added a `logger.debug`
call to surface any cleanup failures without hiding unrelated exceptions
(e.g. `KeyboardInterrupt`, `SystemExit`).

The block is a cleanup-only path (`os.unlink` on a temp metadata file); only
`OSError` can legitimately arise here, so narrowing to that type is correct.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py
# exit 0
```
