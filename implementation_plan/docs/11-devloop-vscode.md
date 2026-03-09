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
- For AI workflow development, use the typed endpoint and payload examples documented in `implementation_plan/docs/12-github-cli-copilot-integration.md` under:
  - `Current implemented AI API surface`
  - `Example requests and responses`

### 5) CI/CD
GitHub Actions should run on every PR:
- lint / formatting
- unit tests
- fixture replay tests
- OpenAPI validation (schema checks)

---

## Suggested local workflow
1. Start dependencies: `docker compose up -d` (Redis; DuckDB is embedded)
2. Start backend: `make dev` (or `uvicorn` / `node` etc.)
3. Use simulator:
   - `curl` command with a transcript (see `dev/simulator_cli.md`)
   - or mobile app DEV_SIMULATOR mode
   - for AI workflow testing, prefer the typed AI routes first:
     - `POST /v1/ai/copilot/explain-pr`
     - `POST /v1/ai/copilot/summarize-diff`
     - `POST /v1/ai/copilot/explain-failure`
     - `POST /v1/ai/rag-summary`
     - `POST /v1/ai/accelerated-rag-summary`
     - `POST /v1/ai/failure-rag-explain`
     - `POST /v1/ai/accelerated-failure-explain`
     - `POST /v1/ai/find-similar-failures`
     - `POST /v1/ai/read-stored-output`
     - `POST /v1/ai/accelerate-generate-and-store`
   - for command-surface testing of the new accelerated workflow, use phrases like:
      - `accelerate and store summarize the failure cluster`
      - `generate and store with acceleration summarize the failure cluster to ipfs`
      - `use acceleration for augmented summary for pr 123`
      - `use acceleration for augmented summary for pr 124 to ipfs`
      - `accelerated rag summary for pr 123`
      - `use acceleration for explain failure for pr 321`
      - `use acceleration for explain workflow CI Linux for pr 322`
      - `use acceleration for explain failure for pr 323 to ipfs`
      - `accelerated failure analysis for pr 123`
      - `accelerated explain workflow CI Linux for pr 123`
   - if you want standard `rag summary` commands to default to the accelerated backend,
     set `HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND=accelerated`
   - if you want standard failure-analysis commands to default to composite or accelerated backends,
     set `HANDSFREE_AI_DEFAULT_FAILURE_BACKEND=composite` or
     `HANDSFREE_AI_DEFAULT_FAILURE_BACKEND=accelerated`
   - older compatibility env vars still work, but the `HANDSFREE_AI_DEFAULT_*` ones are now the preferred knobs
   - if you are exercising indexed history reuse locally, optionally set
     `HANDSFREE_AI_HISTORY_RETENTION_DAYS` and `HANDSFREE_AI_HISTORY_MAX_RECORDS_PER_USER`
     to keep `ai_history_index` bounded during repeated test runs
   - for GitHub live-mode dev work, you can now rely on your local GitHub CLI login as a token source:
     - `gh auth status`
     - then set `HANDS_FREE_GITHUB_MODE=live` or `GITHUB_LIVE_MODE=true`
     - `gh auth token` is used only as an explicit live-mode fallback, not in default fixture mode
4. Iterate on:
   - intent parsing
   - GitHub summarization
   - policy gates
5. Before trying on-glasses:
   - run `make test`
   - run fixture replay
   - ensure CI passes

### AI route `curl` examples
Assume a local backend on `http://127.0.0.1:8000` and substitute a valid local auth header as needed.

Use the typed routes for normal client-style testing. Use the generic route when you want to test raw `workflow` or `capability_id` dispatch behavior.

Generic AI execute:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/execute \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "workflow": "pr_rag_summary",
    "profile": "default",
    "context": {
      "repo": "openai/example",
      "pr_number": 123
    },
    "persist_output": true,
    "embeddings": {
      "dimensions": 384
    },
    "ipfs": {
      "pin": true
    }
  }'
```

If this request uses `workflow` instead of an explicit `capability_id`, the backend may be remapped by the current AI backend policy. Explicit `capability_id` calls bypass that remapping.
Check the response `policy_resolution` field when you want to confirm whether remapping actually happened.
For command-surface testing, the same metadata is now available under `debug.policy_resolution`.
For a quick admin-side snapshot of the currently resolved defaults and recent remaps, use `GET /v1/admin/ai/backend-policy`.
If you do not want that read to create a persisted snapshot, use `GET /v1/admin/ai/backend-policy?capture=false`.
For bucketed recent history, use `GET /v1/admin/ai/backend-policy/history?window_hours=24&bucket_hours=1`.
For persisted point-in-time samples, use `GET /v1/admin/ai/backend-policy/snapshots`.
If you are exercising snapshot persistence repeatedly, optionally set
`HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS` and
`HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER` and
`HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS`
to keep the snapshot table bounded during local test runs.
That report now includes:
- fixed `last_hour` and `last_24_hours` buckets
- per-workflow remap totals by requested and resolved workflow
- the current non-secret GitHub auth source (`github_app`, `env_token`, `gh_cli`, or `fixtures`)
- capability usage split into remapped vs direct AI capability counts
- compact `top_capabilities` lists so local inspection does not require sorting raw maps
- compact `top_remaps` entries for the busiest workflow remap pairs

Copilot explain PR:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/copilot/explain-pr \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "profile": "default"
  }'
```

Copilot summarize diff:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/copilot/summarize-diff \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "profile": "default"
  }'
```

Copilot explain failure:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/copilot/explain-failure \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "workflow_name": "CI Linux",
    "profile": "default"
  }'
```

RAG summary with IPFS persistence:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/rag-summary \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "profile": "default",
    "summary_backend": "accelerated",
    "persist_output": true,
    "embeddings": {
      "dimensions": 384
    },
    "ipfs": {
      "pin": true
    }
  }'
```

Accelerated RAG summary:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/accelerated-rag-summary \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "profile": "default",
    "generation": {
      "model": "llama3"
    },
    "embeddings": {
      "dimensions": 256
    }
  }'
```

Failure RAG explain:

```bash
# `history_cids` is optional here. If omitted, the backend may auto-discover
# recent matching persisted failure-analysis CIDs for the same repo/target,
# primarily through `ai_history_index` with a compatibility fallback for older records.
curl -X POST http://127.0.0.1:8000/v1/ai/failure-rag-explain \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "workflow_name": "CI Linux",
    "profile": "default",
    "failure_backend": "accelerated",
    "history_cids": ["bafy-history-1"],
    "generation": {
      "model": "llama3"
    },
    "embeddings": {
      "dimensions": 384
    }
  }'
```

Accelerated failure explain:

```bash
# `history_cids` is optional here. If omitted, the backend may auto-discover
# recent matching persisted failure-analysis CIDs for the same repo/target,
# primarily through `ai_history_index` with a compatibility fallback for older records.
curl -X POST http://127.0.0.1:8000/v1/ai/accelerated-failure-explain \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 123,
    "repo": "openai/example",
    "workflow_name": "CI Linux",
    "profile": "default",
    "history_cids": ["bafy-history-1"],
    "generation": {
      "model": "llama3"
    },
    "embeddings": {
      "dimensions": 256
    }
  }'
```

Find similar failures:

```bash
# `history_cids` is optional here. If omitted, the backend may auto-discover
# recent matching persisted failure-analysis CIDs for the same repo/target,
# primarily through `ai_history_index` with a compatibility fallback for older records.
curl -X POST http://127.0.0.1:8000/v1/ai/find-similar-failures \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "pr_number": 125,
    "repo": "openai/example",
    "workflow_name": "CI Linux",
    "profile": "default",
    "top_k": 2,
    "history_cids": ["bafy-history-1"],
    "history_candidates": [
      {
        "summary": "Dependency install failed during CI Linux setup.",
        "repo": "openai/example",
        "pr_number": 101,
        "failure_target": "CI Linux",
        "failure_target_type": "workflow"
      },
      {
        "summary": "A UI snapshot changed unexpectedly.",
        "repo": "openai/example",
        "pr_number": 99,
        "failure_target": "Visual tests",
        "failure_target_type": "check"
      }
    ]
  }'
```

Read stored output by CID:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/read-stored-output \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "cid": "bafyexample123",
    "profile": "default"
  }'
```

Accelerated generate and store:

```bash
curl -X POST http://127.0.0.1:8000/v1/ai/accelerate-generate-and-store \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "prompt": "Summarize the current CI failure cluster for voice playback.",
    "profile": "default",
    "generation": {
      "model": "llama3"
    },
    "ipfs": {
      "pin": false
    },
    "kit_pin": true,
    "metadata": {
      "repo": "openai/example",
      "source": "devloop"
    }
  }'
```

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
