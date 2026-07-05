# Logic Conformance Harness

This directory is the shared Python/TypeScript source of truth for the
SwissKnife theorem-prover parity harness.

## Layout

- `vectors/` contains portable conformance vectors used by both runners.
- `schema/` contains the JSON shape for vectors and runner results.
- `compare.mjs` compares Python and TypeScript result JSON and writes a parity report.
  It also supports host-native exclusions so simulated-only slices (for example
  native ZKP vectors marked `excludeFromParityWhenSimulated`) are reported as
  `HOST_NATIVE_EXCLUDED` instead of `MATCH`.
- `mutate.mjs` creates metamorphic vector variants for invariant testing.
- `symbol-map.json` is the PORT-234 per-symbol reconciliation artifact.
- `symbol-evidence.json` binds symbol families to concrete conformance test ids
  and native input slices for PORT-241/243 anti-gaming checks.
- `symbol_audit.py` regenerates/checks that every public Python logic symbol is
  either directly ported, consolidated into an identified TypeScript surface, or
  explicitly marked not applicable, and now enforces evidence-rule linkage.
- `coverage_reconciliation.mjs` reconciles runtime TS V8 coverage against the
  evidence rules and writes `conformance/ts-coverage-reconciliation.json`.
- `port239_host_native_gate.mjs` enforces PORT-239 host-native classification
  for `external_provers/*` and `flogic/ergoai_wrapper.py` symbols; it writes
  `conformance/port239-host-native-gate.json`.
- `make conformance-temporal-native` gates PORT-255 no-remote temporal
  consistency behavior through native TS TDFOL tests.
- `make conformance-modal-codec-guidance-crosslang` gates PORT-246 compiler
  guidance and frame-audit helper parity against the Python modal codec.
- `make conformance-modal-codec-citation-crosslang` gates PORT-246 citation
  normalization and section/source-id helper parity against the Python modal
  codec.
- `make conformance-modal-decompiler-citation-crosslang` gates PORT-247
  decompiler citation normalization and section/source-id helper parity against
  the Python modal decompiler.
- `make conformance-modal-compiler-serialization-crosslang` gates PORT-250
  compiler config and ambiguity serialization parity against the Python modal
  compiler dataclasses.
- `make conformance-self-containment` runs Python + strict TypeScript artifacts,
  writes a dedicated strict compare report under `conformance/self-contained/`,
  and enforces the PORT-257 strict self-containment gate against that report.
- `make conformance-self-containment-strict` evaluates the strict gate against the
  default `conformance/report.json` + `conformance/ts-results.json` artifacts.

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
