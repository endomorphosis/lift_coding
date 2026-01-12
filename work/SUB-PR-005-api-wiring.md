SUB-PR: PR-005 API wiring (end-to-end inbox + PR summary)

Base: copilot/sub-pr-6 (PR #18) which itself stacks on PR #6
Goal: Make PR-005 meet acceptance criteria end-to-end via HTTP API, using fixture data only.

Background
- PR #18 implemented a fixture-backed GitHub provider and handler functions:
  - inbox.list -> handle_inbox_list
  - pr.summarize -> handle_pr_summarize
- The FastAPI/OpenAPI server skeleton is currently in PR #11.

Agent checklist (keep scope tight)
- [ ] Cherry-pick/rebase the minimal API/server from PR #11 needed to run on http://localhost:8080.
- [ ] Add endpoint wiring so that, with fixtures only:
  - POST /v1/command "inbox" returns deterministic spoken_text (use handle_inbox_list)
  - POST /v1/command "summarize pr <n>" returns deterministic spoken_text (use handle_pr_summarize)
  - GET /v1/inbox returns a deterministic fixture-backed list
- [ ] Ensure privacy defaults remain strict (privacy_mode=True by default; no code snippets).
- [ ] Add minimal integration tests proving the HTTP endpoints return the expected spoken_text using fixtures.
- [ ] Keep CI green: make fmt-check, make lint, make test, make openapi-validate.

Out of scope
- Real GitHub auth (fixture-only)
- Write actions (PR-007)
