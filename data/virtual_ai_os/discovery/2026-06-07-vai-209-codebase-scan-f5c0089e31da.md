# VAI-209 Codebase Scan Finding

Date: 2026-06-07
Fingerprint: f5c0089e31da2efddc7e21f9518143c36e2fd9f6
Kind: swallowed_exception
Source: external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml:120
Priority: P1
Track: ops

## Evidence

```text
except Exception as e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

The workflow embedded extractor previously printed a per-file error and returned
`None`, allowing generated module documentation to omit unreadable or unparsable
modules without failing the maintenance run. The extractor now raises a typed
`DocumentationExtractionError` for read and parse failures, aggregates failures
during module scanning, and exits the workflow step nonzero before writing a
partial `module_structure.md`.

## Validation

- `test -s external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml`
- `python3 -m py_compile /tmp/vai209_extract_docs.py`
- Temporary malformed-module extraction check confirmed the workflow script exits
  nonzero before writing `module_structure.md`.
