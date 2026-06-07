# VAI-209 Resolution

Date: 2026-06-07
Task: VAI-209
Kind: swallowed_exception fix
Source: external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml:120

## Finding

The inline module-structure extractor caught every `Exception`, printed an error,
and returned `None`. A read, decode, or Python syntax failure in a source module
could therefore remove that module from generated documentation while allowing the
maintenance workflow to continue and create a misleading clean PR.

## Fix

Removed the broad swallowed exception path from `extract_module_info()`.
`generate_module_docs()` now records expected file read, decode, and syntax
failures across scanned modules, reports the failing paths, and exits nonzero
before writing `module_structure.md`.

Unexpected extractor defects now propagate normally with a Python traceback.

## Validation

```text
python3 -c 'import pathlib, sys; p=pathlib.Path(sys.argv[1]); assert p.read_text(encoding="utf-8").strip()' external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml
# exit 0

python3 - <<'PY' ... extract embedded /tmp/extract_docs.py and compile ... PY
# exit 0, output: embedded extract_docs.py compiles

python3 - <<'PY' ... embedded extract_docs.py error-path validation ... PY
# exit 0, output: embedded extract_docs.py error path validation passed
```
