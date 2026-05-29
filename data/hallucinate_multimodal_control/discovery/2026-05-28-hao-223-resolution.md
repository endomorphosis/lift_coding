# HAO-223 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py:589
Kind: swallowed_exception
Status: fixed

## Fix

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
