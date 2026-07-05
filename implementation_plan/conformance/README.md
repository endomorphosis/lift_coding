# Logic Conformance Harness

This directory is the shared Python/TypeScript source of truth for the
SwissKnife theorem-prover parity harness.

## Layout

- `vectors/` contains portable conformance vectors used by both runners.
- `schema/` contains the JSON shape for vectors and runner results.
- `compare.mjs` compares Python and TypeScript result JSON and writes a parity report.
  Strict structured vectors compare `status`, `reason`, `proverId`,
  `modelHash`, `countermodelHash`, `proofHash`, and `derivationHash`; decided
  strict rows must carry the status-appropriate artifact (`modelHash` for
  `sat`, `proofHash` for `proved`, `countermodelHash` for `refuted`) plus a
  derivation hash or they are reported as mismatches.
  It also supports host-native exclusions so simulated-only slices (for example
  native ZKP vectors marked `excludeFromParityWhenSimulated`) are reported as
  `HOST_NATIVE_EXCLUDED` instead of `MATCH`.
  Compare rows also carry vector `tags`, enabling certificate checks for
  runtime slices such as PORT-239 (`flogic`/`ergo`/`host-native`).
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
- `behavioral_certificate.mjs` now enforces a minimum number of PORT-239 runtime
  evidence rows (default `--port239-runtime-min-rows 3`) derived from compare
  rows tagged `flogic`/`ergo`/`host-native`, plus per-tag minima
  (`--port239-runtime-flogic-min-rows 2`,
  `--port239-runtime-ergo-min-rows 1`,
  `--port239-runtime-host-native-tag-min-rows 3`) and per-tag
  `HOST_NATIVE_EXCLUDED` minima
  (`--port239-runtime-flogic-excluded-min-rows 2`,
  `--port239-runtime-ergo-excluded-min-rows 1`,
  `--port239-runtime-host-native-tag-excluded-min-rows 3`), with zero
  tolerance for non-excluded rows for each of those tags, required runtime
  vector id pinning (`--port239-required-vector-ids`, default
  `zkp-sim-005,zkp-sim-011,zkp-sim-012`) plus expected tag/shape checks for
  those ids and expected vector-corpus fields (`backendMode: host-dependent`,
  `excludeFromParityWhenSimulated: true`, `status: sat`, `decided: true`,
  `acceptableReasons: [sat, proved]`) and canonical vector-hash pinning to
  detect semantic drift, plus required source-file uniqueness/origin pinning
  (`--port239-required-vectors-file`, default `core-policy-vectors.json`) to
  prevent substitution or retagging
  gaming, and strict
  structured artifact coverage for PORT-236.
- `make conformance-temporal-native` gates PORT-255 no-remote temporal
  consistency behavior through native TS TDFOL tests.
- `make conformance-modal-codec-guidance-crosslang` gates PORT-246 compiler
  guidance and frame-audit helper parity against the Python modal codec.
- `make conformance-modal-codec-citation-crosslang` gates PORT-246 citation
  normalization and section/source-id helper parity against the Python modal
  codec.
- `make conformance-modal-codec-temporal-operator-crosslang` gates PORT-246
  modal operator feature key, operator-pair feature key, temporal prefix
  relation, and temporal context-cue helper parity against the Python modal
  codec.
- `make conformance-modal-decompiler-citation-crosslang` gates PORT-247
  decompiler citation normalization and section/source-id helper parity against
  the Python modal decompiler.
- `make conformance-modal-decompiler-temporal-operator-crosslang` gates PORT-247
  modal operator feature key, operator-pair feature key, temporal prefix
  relation, and temporal context-cue helper parity against the Python modal
  decompiler.
- `make conformance-modal-compiler-serialization-crosslang` gates PORT-250
  compiler config and ambiguity serialization parity against the Python modal
  compiler dataclasses.
- `make conformance-self-containment` runs Python + strict TypeScript artifacts,
  writes a dedicated strict compare report under `conformance/self-contained/`,
  and enforces the PORT-257 strict self-containment gate against that report.
  The strict compare stage disables host-native exclusions and treats simulated
  backend/host-dependent expectation rows as `SIMULATED_DEPENDENCY` outcomes so residual dependency on
  simulated engines stays visible as debt instead of being counted as parity, even when one side is missing.
  Host-dependent expected rows are only counted as dependency while at least one side is not `backendMode=real`. It also normalizes
  Python `unknown` host-dependent rows to match TS conclusive strict outputs when
  vectors are non-decided, preventing false-negative mismatches in strict mode;
  those strict-unknown-bridge rows are not dependency-labeled.
  The strict gate additionally enforces zero unresolved compare rows
  (`MISMATCH`, `PY_ONLY_MISSING`, `TS_ONLY_MISSING`) and reports
  `SIMULATED_DEPENDENCY` as explicit residual debt telemetry, with a hard check
  that any remaining dependency rows are confined to `zkp-statement`.
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
