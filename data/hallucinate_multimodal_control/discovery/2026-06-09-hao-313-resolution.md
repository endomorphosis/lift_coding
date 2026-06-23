# HAO-313 Resolution

Date: 2026-06-09
Task: HAO-313
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245

## Finding

The requested scan evidence file
`data/hallucinate_multimodal_control/discovery/2026-06-07-hao-313-codebase-scan-d700867b5fc4.md`
was not present in this attempt checkout. The target source still contained the
flagged pattern: `_find_deals_for_cid()` used `except Exception: pass` while
loading local mock deal JSON files, hiding unreadable files, invalid JSON, and
malformed deal records.

## Fix

Replaced the swallowed broad exception with explicit handling for expected file
and JSON failures. Those cases now emit a warning with the mock deal path and
continue scanning other files. Non-object JSON deal records are also reported and
ignored before accessing `deal.get(...)`.

Unexpected programming errors are no longer swallowed by this inner loop.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
```
