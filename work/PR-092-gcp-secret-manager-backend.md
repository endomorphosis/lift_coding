# PR-092: Google Secret Manager backend for secret storage

## Status
- [ ] In progress

## Checklist
- [ ] Review `src/handsfree/secrets/interface.py` for required methods
- [ ] Implement `GCPSecretManager` in `src/handsfree/secrets/gcp_secrets.py`
- [ ] Wire `SECRET_MANAGER_TYPE=gcp` in `src/handsfree/secrets/factory.py`
- [ ] Update docs in `docs/SECRET_STORAGE_AND_SESSIONS.md`
- [ ] Add tests (or minimal validation snippet) and ensure CI passes

## Notes / Log
- 
