# VAI-045 Resolution

Date: 2026-05-26
Task: VAI-045
Source finding: `src/handsfree/stt/stub_provider.py:42`

## Review

The scan evidence captured a historical `raise NotImplementedError(` in the
stub STT provider runtime path. In this checkout, `StubSTTProvider.transcribe`
already performs the runtime behavior required for CI/dev use:

- disabled providers raise `STTDisabledError`
- unsupported formats raise `ValueError`
- supported formats return the deterministic transcript `show my inbox`

## Change

Kept the provider behavior intact and made the runtime contract explicit by
promoting supported formats and the deterministic transcript to class-level
constants. This preserves the replacement for the placeholder runtime path while
making future scans less likely to confuse the active implementation with a
temporary stub.

## Validation

Ran:

```bash
python3 -m py_compile src/handsfree/stt/stub_provider.py
pytest -q tests/test_stt_providers.py::test_stub_provider_transcribe tests/test_stt_providers.py::test_stub_provider_unsupported_format tests/test_stt_providers.py::test_stub_provider_disabled
```
