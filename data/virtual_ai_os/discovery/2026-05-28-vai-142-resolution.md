# VAI-142 Resolution

Date: 2026-05-28
Task: VAI-142
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_embeddings_py.py:611
Fingerprint: cbf158a57c000c3f1b158446ce0cd74e7f322942
Kind: swallowed_exception

## Finding

Bare `except:` at line 611 of `ipfs_embeddings_py.py` (inside the `load_embeddings_from_ipfs`
method of `IPFSEmbeddingsPy`) silently caught all exceptions including `SystemExit` and
`KeyboardInterrupt` during best-effort `os.unlink` cleanup of a temporary file.

## Fix

Changed:
```python
except:
    pass
```
to:
```python
except OSError:
    pass
```

The block does not re-raise because this is best-effort cleanup — the outer `raise e`
on the following line already propagates the original exception. Narrowing to `OSError`
prevents signals like `KeyboardInterrupt` and `SystemExit` from being accidentally
swallowed during temp file cleanup.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_embeddings_py.py
```
→ OK

## Submodule Commit

Fix applied in hallucinate_app submodule at: `3930716c9d5d5f21481bfb09f2244ca70d6d0497`
Merged into main at: `508da0c82adf0b7935d70ed9664655fa877c9a6d`
