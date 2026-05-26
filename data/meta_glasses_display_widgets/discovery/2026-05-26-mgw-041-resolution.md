# MGW-041 Placeholder Runtime Path Resolution

Date: 2026-05-26
Task: MGW-041
Source finding: `src/handsfree/ocr/stub_provider.py:38`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-041-codebase-scan-914627da8285.md`

## Finding

The disabled OCR branch raised a raw `NotImplementedError`. That made a normal
runtime configuration state look like a placeholder implementation path.

## Resolution

`StubOCRProvider.extract_text()` now raises `OCRDisabledError` for the disabled
runtime state. The exception remains compatible with the existing command API's
disabled-OCR handling while giving callers a concrete OCR-domain error to catch.

## Validation

```bash
python3 -m py_compile src/handsfree/ocr/stub_provider.py
```
