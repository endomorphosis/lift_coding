# VAI-142 Resolution

Date: 2026-06-24
Task: VAI-142
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_embeddings_py.py:611
Fingerprint: cbf158a57c000c3f1b158446ce0cd74e7f322942
Kind: swallowed_exception

## Finding

The scan flagged a swallowed cleanup exception in
`IPFSEmbeddingsPy.load_embeddings_from_ipfs()`. In context, the cleanup path also
unconditionally raised an undefined `e` from the `finally` block, which masked
successful IPFS loads and replaced real load errors with a misleading
`NameError`.

## Fix

Kept temporary-file deletion best effort, but now narrows the handled failure to
`OSError` with a debug log. Removed the unconditional `raise e` so successful
loads return their parsed embeddings and real exceptions propagate to the
existing outer error handler.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_embeddings_py/ipfs_embeddings_py.py
```
