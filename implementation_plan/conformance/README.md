# Logic Conformance Harness

This directory is the shared Python/TypeScript source of truth for the
SwissKnife theorem-prover parity harness.

## Layout

- `vectors/` contains portable conformance vectors used by both runners.
- `schema/` contains the JSON shape for vectors and runner results.
- `compare.mjs` compares Python and TypeScript result JSON and writes a parity report.
- `mutate.mjs` creates metamorphic vector variants for invariant testing.
- `symbol-map.json` is the PORT-234 per-symbol reconciliation artifact.
- `symbol_audit.py` regenerates/checks that every public Python logic symbol is
  either directly ported, consolidated into an identified TypeScript surface, or
  explicitly marked not applicable.

Run the local harness from the repository root:

```bash
make conformance
```

By default, the TypeScript runner uses deterministic simulated Z3 behavior for
propositional/FOL policy vectors so the harness is usable without the large Z3
WASM artifact. Set `SWISSKNIFE_CONFORMANCE_LIVE_Z3=1` to require the live Z3
bridge instead.

`make conformance` enforces `CONFORMANCE_THRESHOLD=100` by default for the portable
corpus. Override that variable only when intentionally measuring host-dependent
simulated-vs-real divergence.

The Python runner uses `ipfs_datasets_py.logic` modules as its reference side:
TDFOL proof checks run for every policy vector, DCEC proof checks run for
deontic/modal/legal/ZKP-policy vectors, and live Python `z3` is used when the
`z3` package is installed. If `z3` is absent, the result envelope records
`z3_runtime: unavailable:*` and still emits the TDFOL/DCEC provenance under
`metadata.pythonProverChecks`.

Refresh the symbol reconciliation artifact after adding or removing public
Python logic symbols:

```bash
python3 implementation_plan/conformance/symbol_audit.py --write-map
```
