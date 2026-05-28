# HAO-201 Codebase Scan Finding

Date: 2026-05-28
Fingerprint: befeb053e24bb0786d11d611f44356f13e250a3a
Kind: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:150
Priority: P1
Track: runtime

## Evidence

```text
except Exception as e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (HAO-201)

All `except Exception as e:` blocks in `auth_keystore_integration.py` were using
`logger.error(f"...: {e}")` which discards the stack trace, making runtime failures
very hard to diagnose.

Fixed by replacing all `logger.error(...)` calls inside except blocks with
`logger.exception(...)`, which automatically appends the full traceback. Affected
methods: `init`, `get_authorized_key`, `set_authorized_key`, `delete_authorized_key`,
`list_authorized_providers`, `get_authorized_key_info`, `rotate_authorized_key`,
`issue_key_access_capability`, and `test`.

Validation: `python3 -m py_compile` passes.
