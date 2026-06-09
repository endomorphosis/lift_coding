# MGW-045 Placeholder Runtime Path Resolution

Date: 2026-05-26
Task: MGW-045
Source finding: `src/handsfree/stt/stub_provider.py:42`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-045-codebase-scan-b40c594b84b1.md`

## Finding

The disabled STT stub path was filed as a placeholder runtime path because it
previously raised a raw `NotImplementedError` for a normal disabled-runtime
configuration state.

## Resolution

`StubSTTProvider.transcribe()` now raises the STT-domain `STTDisabledError`
when speech-to-text is disabled. This keeps the disabled-provider behavior
explicit and lets the command API map that condition to `error.stt_disabled`
instead of treating it as a generic audio failure.

## Validation

```bash
python3 -m py_compile src/handsfree/stt/stub_provider.py
```
