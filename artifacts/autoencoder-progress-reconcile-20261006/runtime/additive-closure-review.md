# Additive source recovery review

The wider branch inventory identifies86 published files absent from the canonical workspace at commit `795d960170214d03e2eaf4c0a13ad4eb922c5c08`:85 Python files and one task-contract JSON schema. All are implementation or operations files; the initial inventory includes no tests. Static import closure adds three published dependencies, giving89 source/schema files. There are82 missing dedicated tests and one missing test dependency, `optimizers/logic_theorem_optimizer/codebase_runtime_8d.py`.

[additive-closure-review.json](additive-closure-review.json) contains exact published byte/hash pins, live existence checks, classifications, explicit import edges and changed-existing-owner observations. [additive-static-validation.json](additive-static-validation.json) records successful compilation of all171 Python source/test/support files without importing or executing them. Compilation verifies syntax availability; it does not validate runtime behavior.

| Recovery group | Files in original86 | Role |
| --- | ---: | --- |
| Codebase source384 and semantic state |31| Source units, checkpoints, generations, resident workers, training lifecycle, repository/federation custody and task/refinement contracts |
| Distributed source384 |17| Numerical and owner/worker contracts, local store, exchange, candidate projections, explicit native qualification and supplemental contexts |
| Intent action/effect contracts |9| Explicit source/action associations and native effect checks |
| Native family emitters/interpretations |9| Lean schema and semantic carriers; execution still requires real native gates |
| Source continuation/program/state |7| Original checkpoint continuation, source functions, source state and strict compatibility |
| Contextual Legal384/768 |3| Cached semantic reconstruction and separate output measurements |
| DuckDB catalog/history |3| Single-owner codebase catalog, DuckLake history and retention |
| Security semantics/header checks |3| Source scalar/state support and bounded header checker |
| Metadata publication/registration |2| Immutable Hub metadata publishing and explicit ModelManager import |
| Legal text/source custody |2| Original prose observations and portable source pins |

The three additional dependency files are `logic/backends/codebase_process.py` and `logic/software_verification/{codebase_pipeline,codebase_source_adapters}.py`. Their code can be restored alongside the published86 files. Restoring absent modules does not instantiate a process, run training, open a store, publish metadata, execute a prover or activate serving.

Two existing-owner compatibility gaps require explicit treatment:

- `codebase_resources.py` lacks `codebase_admission_timeout`, needed by the new bounded header/source-unit routes. Published code imports `resource_scheduler.default_proof_admission_timeout_seconds`, also absent locally. Published scheduler includes a larger proof-resource-profile change. Copying that dirty scheduler, inventing a30/90-second stub or changing resource admission implicitly is outside this additive restoration. Retain the new source files, document affected route activation as blocked and reconcile the resource profile separately.
- `security_formalization_evaluation.py` lacks `_function_line_index`, needed by the new source-function owner. The entire published delta is bounded: add a frozen source-local line table and an optional `_function_span` keyword that rejects a different source object. Other code is byte-equivalent. [security_formalization_evaluation.py.diff](security_formalization_evaluation.py.diff) retains that exact change; if applied under its exact preimage, pure `test_source_function_units.py` and `test_function_span_line_index.py` provide appropriate verification.

The source-value training-import relocation already reviewed for contextual reconstruction remains the third guarded existing-file change. It is independent of the resource and function-span owners. Ten changed existing direct dependencies are hash-recorded in the JSON report; none should be overwritten by a bulk checkout or automatic merge. Explicit import analysis cannot prove dynamic imports, filesystem asset references or changed signatures fully compatible.

Restore exact absent files only, using exclusive creation and published hashes. Include original package markers/schema support when absent; preserve all existing paths. Retain all recovered tests, then run the ten reviewed pure full modules listed in `additive-static-validation.json`. They use metadata/generated-IR/synthetic inert controls or mocked transport. Most distributed numerical, qualification, exchange and export tests call real model training; many native Lean tests execute actual Lake even though they are named unit tests. They should not be executed as a bulk group under this no-model review.

The seven continuation/original-prose paths comprise three source modules, two dedicated test modules and two guides: `source_checkpoint_continuation_{v1,numeric_v1}.py`, `ir_legal_text_roundtrip.py`, their tests, and `docs/autoencoders/{source_checkpoint_continuation,legal_original_text_roundtrip}.md`. The source/tests are already covered by the wider inventory. Add the two guides if absent. Continuation uses exact saved-weight contracts; original-text observations preserve the distinction between semantic IR equality and lost wording information.

These files make published agent progress available in the canonical codebase. They retain source, task, family and checkpoint boundaries, explicit unsupported states and actual source-bound family/Lake gates. They do not establish new numerical quality, reconstruction success, teacher qualification or proof authority.
