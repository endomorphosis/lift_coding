# HAO-371 Resolution

Date: 2026-06-12
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller.py:1119
Kind: swallowed_exception -> fixed

## Finding

The scan reported a broad `except Exception:` in `get_content()` while sniffing
retrieved IPFS bytes for JSON content. Invalid JSON was intentionally non-fatal,
but the broad handler also hid unexpected runtime errors and gave operators no
debug context.

## Fix

Narrowed the handler to the expected JSON parsing failures:
`json.JSONDecodeError` and `UnicodeDecodeError`. The fallback still keeps the
default `application/octet-stream` media type for invalid JSON-like content, but
now logs a debug message with the CID and parse error.

The requested whole-file compile validation also exposed pre-existing generated
syntax defects in this archived controller: missing commas in response dict
literals and two malformed function signatures. Those syntax blockers were
corrected mechanically so `py_compile` can validate the file.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller.py` - PASS
