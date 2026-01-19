# PR-101: Multimodal input docs sync (OCR status)

## Why
`MULTIMODAL_INPUT_IMPLEMENTATION.md` includes language like “OCR/vision not yet implemented” without pointing to the OCR work that is already in flight.

We should make the doc accurate and link to the current OCR provider PR.

## Scope
- Update `MULTIMODAL_INPUT_IMPLEMENTATION.md` to clarify current image-input behavior and point to the OCR provider work.
- Doc-only change.

## Acceptance Criteria
- Doc no longer reads like OCR is an unspecified future with no pointer.
- Doc links to PR-082 (image input OCR provider) and describes the expected behavior at a high level.
- No runtime behavior changes.
