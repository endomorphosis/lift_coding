# HAO-306 Resolution

Date: 2026-06-07
Source: external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml:120

## Decision

The flagged `except Exception` path was a real maintenance risk. The generated
documentation extractor printed per-file extraction failures and returned `None`,
letting the workflow produce incomplete docs without failing the maintenance job.

## Change

`extract_module_info` now records the source filename in `ast.parse` diagnostics
and raises a contextual `RuntimeError` for expected file, decode, syntax, or
parse-value failures instead of skipping the module.

## Validation

- `python3 -c 'import pathlib, sys; p=pathlib.Path(sys.argv[1]); assert p.read_text(encoding="utf-8").strip()' external/ipfs_kit/.github/workflows/auto-doc-maintenance.yml`
- Embedded `/tmp/extract_docs.py` block compiled from the workflow.
