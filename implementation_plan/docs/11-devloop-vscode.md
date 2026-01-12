# Tight Dev Loop with VS Code (No Debugging Hell)

This project is designed so you can iterate quickly in VS Code without depending on the glasses for every change.

## Goals
- Reproduce wearable flows locally (no on-device debugging required for most work)
- Deterministic tests using fixtures
- Contract tests that validate request/response payloads
- CI gates that prevent “works on my glasses” regressions

---

## Core techniques

### 1) Wearable Simulator (local)
Create a simulator that mimics:
- audio input (mic capture or pre-recorded files)
- optional camera snapshots (static images)
- audio output (playback on laptop speakers)

**Approach**
- The mobile app should have a `DEV_SIMULATOR` mode that:
  - uses phone mic/speaker (or desktop mic/speaker in an emulator)
  - bypasses wearable connectivity
  - shows transcript + parsed intent + backend response in a debug panel
- In parallel, keep a small CLI simulator in `dev/simulator_cli.md` that hits the backend directly with text.

### 2) Transcript fixtures
Treat “what the user said” as a test input.
- Put canonical transcripts in `tests/fixtures/transcripts/*.txt`
- Include noisy variants (gym noise, misrecognitions)
- Your intent parser should be testable purely from transcript text.

### 3) GitHub fixtures + replay
Never debug webhooks live if you can avoid it.
- Save webhook payloads to `tests/fixtures/github/webhooks/*.json`
- Save representative REST responses to `tests/fixtures/github/api/*.json`
- Provide a replay script (see `dev/replay_webhook.py` skeleton) to POST a fixture into your local server.

### 4) Contract tests
Use the OpenAPI spec (`spec/openapi.yaml`) as the source of truth.
- Validate that server responses match schemas (golden tests)
- Validate webhook ingestion accepts your stored fixture payloads

### 5) CI/CD
GitHub Actions should run on every PR:
- lint / formatting
- unit tests
- fixture replay tests
- OpenAPI validation (schema checks)

---

## Suggested local workflow
1. Start dependencies: `docker compose up -d` (Postgres + Redis)
2. Start backend: `make dev` (or `uvicorn` / `node` etc.)
3. Use simulator:
   - `curl` command with a transcript (see `dev/simulator_cli.md`)
   - or mobile app DEV_SIMULATOR mode
4. Iterate on:
   - intent parsing
   - GitHub summarization
   - policy gates
5. Before trying on-glasses:
   - run `make test`
   - run fixture replay
   - ensure CI passes

---

## Debugging checklist (when something breaks)
- Can you reproduce with a transcript fixture?
- Can you reproduce with a webhook fixture?
- Does the response violate OpenAPI schema?
- Is the policy engine blocking a side effect?
- Are idempotency keys being reused correctly?

---

## Minimal “first week” setup
- Day 1: simulator CLI + OpenAPI stub responses
- Day 2: inbox.list integration using GitHub fixture data
- Day 3: pr.summarize + golden outputs
- Day 4: webhook replay + notifications mocked to console/TTS
- Day 5: CI gates + pre-commit hooks
