# HAO-112 Resolution

Date: 2026-05-26
Task: HAO-112
Source finding: `scripts/smoke_demo.py:141`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-112-codebase-scan-d3346a231149.md`

## Finding

The codebase scanner flagged a broad `except Exception` block while the TTS
smoke check tried to parse non-2xx error details. The exception was swallowed,
so a non-JSON error response hid the server's diagnostic body.

## Resolution

- Added `log_response_error_details` to report JSON error details when
  available, or a bounded text response body when the response is not JSON.
- Reused the helper for both `/v1/tts` and the matching `/v1/command` error
  path, preserving the existing failed-check return behavior.

## Validation

```bash
python3 -m py_compile scripts/smoke_demo.py
```
