# MGW-042 Swallowed Exception Resolution

Date: 2026-05-26
Task: MGW-042
Source finding: `src/handsfree/peer_chat.py:122`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-042-codebase-scan-e0404f01baad.md`

## Finding

The peer chat ingest path treated any exception during DB persistence as a
successful in-memory fallback. That kept dev chat delivery available when the DB
was unavailable, but it also hid persistence outages and unrelated programming
errors from operators.

## Resolution

The persistence and persisted-read fallback paths now catch only expected DuckDB
and filesystem errors, log the fallback with conversation context, and allow
unexpected exceptions to propagate. The in-memory fallback behavior remains in
place for local transport bring-up when persistence is temporarily unavailable.

## Validation

```bash
python3 -m py_compile src/handsfree/peer_chat.py
```
