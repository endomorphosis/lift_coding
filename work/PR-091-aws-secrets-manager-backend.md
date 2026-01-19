# PR-091: AWS Secrets Manager backend for secret storage

## Status
- [ ] In progress

## Checklist
- [ ] Review `src/handsfree/secrets/interface.py` for required methods
- [ ] Implement `AWSSecretManager` in `src/handsfree/secrets/aws_secrets.py`
- [ ] Wire `SECRET_MANAGER_TYPE=aws` in `src/handsfree/secrets/factory.py`
- [ ] Update docs in `docs/SECRET_STORAGE_AND_SESSIONS.md`
- [ ] Add tests (or minimal validation snippet) and ensure CI passes

## Notes / Log
- 
