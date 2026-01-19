# PR-081 work log

## Checklist
- [ ] Locate profile definition/config (server-side).
- [ ] Add `privacy_mode` to profiles (strict/balanced/debug).
- [ ] Replace hard-coded privacy mode in router.
- [ ] Add tests for strict vs balanced vs debug.
- [ ] Run `python -m pytest -q`.

## Notes
- Keep defaults conservative (strict).
- Never allow debug mode by default.
