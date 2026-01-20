# PR-078 work log

## Checklist
- [ ] Find current auth dependency and `api_key` mode behavior.
- [ ] Implement API key parsing from headers.
- [ ] Validate key against DB (revocation, ownership).
- [ ] Add tests for missing/invalid/revoked/valid.
- [ ] Update docs.
- [ ] Run `python -m pytest -q`.

## Notes
- Be careful not to log API keys.
- Prefer constant-time compare when checking plaintext keys.
