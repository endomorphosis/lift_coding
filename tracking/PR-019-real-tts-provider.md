# PR-019: Add real TTS provider selection (keep stub for tests)

## Goal
Add a real TTS provider option while keeping the deterministic stub for fixture-first development and CI.

## Background
The plan includes TTS response playback; the repo currently always uses a stub provider.

## Scope
- Add `get_tts_provider()` factory similar to STT.
- Keep `StubTTSProvider` as default.
- Add one real provider implementation (proposed: OpenAI TTS) behind an optional dependency.
- Update `/v1/tts` endpoint to use the selected provider.
- Add tests ensuring stub remains default and real provider is gated by env vars.

## Non-goals
- Streaming audio.
- Multi-voice catalog management.

## Acceptance criteria
- Default behavior unchanged (stub).
- Setting `HANDSFREE_TTS_PROVIDER=openai` uses the real provider.
- Missing dependency or API key cleanly falls back (or returns a clear error, depending on config).
- CI remains green.

