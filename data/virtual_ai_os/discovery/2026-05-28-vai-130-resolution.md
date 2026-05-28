# VAI-130 Resolution

Date: 2026-05-28
Fingerprint: 82006c12019b9b0289ff371efaf83c9f3674d31b
Kind: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:815
Status: fixed

## Finding

Bare `except Exception: pass` in cleanup block of `test()` method — exception was silently discarded with no record in logs.

## Fix

Changed `except Exception: pass` to `except Exception as e: logger.warning(...)` so cleanup failures surface in logs without propagating. The block still does not re-raise because it is best-effort table cleanup after test runs.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py` → OK
