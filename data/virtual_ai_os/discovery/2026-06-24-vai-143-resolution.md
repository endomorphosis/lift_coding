# VAI-143 Resolution

Date: 2026-06-24
Task: VAI-143
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py:589
Fingerprint: 0c17756fc8217ff11a7444c4cde9f244fdf45626
Kind: swallowed_exception

## Finding

The scan flagged a bare cleanup exception handler in
`IPFSFaissPy.load_from_ipfs()`. The path removes a temporary metadata file after
attempting to load optional index metadata from IPFS.

## Fix

Replaced the local `try` / `except OSError: pass` cleanup block with the module's
existing `_unlink_temp_file(meta_file_path, "metadata")` helper. The helper keeps
cleanup best-effort, narrows the handled failure type to `OSError`, and emits a
debug log instead of silently discarding filesystem cleanup failures.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_faiss_py.py
```
