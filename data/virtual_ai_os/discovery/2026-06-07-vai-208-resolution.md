# VAI-208 Resolution

Date: 2026-06-07
Task: VAI-208
Kind: swallowed_exception fix
Source: external/ipfs_kit/.github/scripts/generate_workflow_list.py:36

## Finding

The workflow-name extractor caught `Exception`, printed a warning, and returned
`None`. A read failure or unrecoverable YAML parse error could therefore remove a
workflow from the generated trigger list without failing the generator.

## Fix

Replaced the catch-all with a typed `WorkflowListError` path:

- file read and decode failures now raise `WorkflowListError`
- YAML parse failures still use the top-level `name:` regex fallback when it can
  recover the workflow name
- YAML parse failures without a recoverable name now raise `WorkflowListError`
- `main()` catches `WorkflowListError`, prints a clear error, and exits nonzero

The regex fallback remains intentional because this checkout contains
`webrtc_benchmark.yml`, which PyYAML rejects but which still exposes a top-level
workflow name.

## Validation

```text
python3 -m py_compile external/ipfs_kit/.github/scripts/generate_workflow_list.py
# exit 0

python3 external/ipfs_kit/.github/scripts/generate_workflow_list.py count
# exit 0, output: 39

python3 - <<'PY' ... parser error-path validation ... PY
# exit 0, output: parser error-path validation passed
```
