# HAO-306 Codebase Scan Finding

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

The embedded documentation extractor no longer catches every exception, prints
to stderr, and returns `None`, which could silently omit modules from generated
documentation. File read and source parse failures now raise
`DocumentationExtractionError` with the affected path preserved, and `ast.parse`
receives the source filename so syntax errors include file-specific context.

## Validation

```text
test -s external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml
# exit 0

python3 - <<'PY' ... embedded extractor compile/error-path validation ... PY
# exit 0, output: embedded extractor validation passed

python3 - <<'PY' ... workflow YAML embedded extractor parse validation ... PY
# exit 0, output: workflow YAML embedded extractor parse passed
```
