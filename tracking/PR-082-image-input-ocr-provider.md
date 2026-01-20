# PR-082: Image input OCR provider (stub-first)

## Goal
Implement basic handling for `input.type = image` so image commands can be accepted and turned into text via an OCR/vision provider.

## Context
The API models include image input, but `src/handsfree/api.py` currently responds with "OCR/vision processing not yet implemented." The implementation plan mentions optional images and privacy modes explicitly mention images.

## Scope
- Add an OCR/vision provider interface similar to STT/TTS providers.
- Provide a **stub** OCR provider (default) that returns deterministic output for tests/dev.
- Optionally add a real provider behind an env flag (only if low-effort and dependency-light).
- Update the command pipeline to:
  - accept `image` input when privacy mode allows
  - run OCR to produce a transcript/text
  - pass that text through the existing intent parsing and handlers

## Non-goals
- High-accuracy computer vision.
- UI work for capturing images on mobile.

## Acceptance criteria
- `POST /v1/command` with `image` input works in balanced/debug privacy modes.
- In strict mode, image input remains rejected.
- Tests cover:
  - strict mode rejection
  - stub OCR producing deterministic text
  - routing OCR text through intent parsing

## Suggested files
- `src/handsfree/api.py`
- New module: `src/handsfree/ocr/` (or similar)
- Update `spec/openapi.yaml` if needed
- Tests under `tests/`

## Validation
- Run `python -m pytest -q`.
