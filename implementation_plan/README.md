# HandsFree Dev Companion Starter Pack

This folder is a **docs/spec/dev** starter you can drop into a repo to guide implementation.

## What's inside
- `docs/` architecture + dev loop docs
- `spec/openapi.yaml` API contract (v1)
- `db/schema.sql` DuckDB schema (initial)
- `../spec/command_grammar.md` voice command grammar + examples
- `dev/` local iteration helpers and fixtures guidance
- `tests/fixtures/` directories for transcripts and GitHub payloads
- `.github/workflows/ci.yml` CI template

## Recommended next step
Wire up a minimal backend that implements:
- `POST /v1/command` (text only to start)
- `GET /v1/inbox` (fixture-backed)
Then add the wearable/mobile layer once core loops are stable.
