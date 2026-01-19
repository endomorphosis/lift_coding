# PR-077 work log

## Checklist
- [ ] Identify current `_make_request` rate-limit logic.
- [ ] Adjust detection for GitHub semantics (403 + remaining=0).
- [ ] Add bounded retry for transient 5xx.
- [ ] Add tests using `respx` or `httpx.MockTransport`.
- [ ] Run `python -m pytest -q`.

## Notes
- Keep retries conservative (e.g., max 2-3, short backoff).
- Ensure token is never logged.
