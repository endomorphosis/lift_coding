# Learned numerical checkpoint consumption

The experimental `numpy-unary-selection-384@1` checkpoint now has a shared
datasets inference owner and an explicit supervisor consumer. The adapter uses
captured original source with cached GTE-small embeddings and the unchanged
learned selection head. It retains predictions, unsupported input and token
deferrals, and attaches independent projection references only to aligned CALL
fragments. This does not establish general NumPy semantics or discharge proof
obligations.

The supervisor persists and verifies native world/metadata DuckLakes, supplies
bounded candidate IR before goal planning, and carries all selected formalization
families through task bundle `@5`, coding-worker evidence, `llm_router` and the
historical delivery audit. Current source, checkpoint, configuration and receipt
drift are refused before provider dispatch. Replay does not repeat inference.

The [configuration guide](../../external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/NUMERICAL_SELECTION_384.md)
documents opt-in selection, source grammar, bounds and lifecycle. The
[qualification ledger](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/numerical-selection-consumer-20261011/qualification.json)
retains commands, source hashes and JUnit results, distinguishes authored
provider replies from actual checkpoint execution, and identifies failed or
superseded attempts. Seven successful suites contain 541 distinct passing checks
with zero skips; the three final merged suites contain 252 checks. The shared
owner is published in datasets commit
`68374b51032b7a9fa795a79829e4d8eb2f2a5ca4`.
Supervisor code and retained evidence are published at
`7d67f14dc275237d815cb843c8772d95a7e2c8d1`. Local documentation gates pass.
GitHub's [Documentation Gates](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38181882195)
and [Serving Contract Gates](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38181882133)
did not start. Their check annotations (114596002994 and 114596002247) both
report: "The job was not started because your account is locked due to a billing
issue." Those remote checks are not passing validation evidence.

Offline archive checks bind the actual producer bytes and separate model assets.
The no-index arm disables this selected inference. Learned-only execution does
not implicitly start legacy training, and extended indexing budgets reach the
shared worker. The existing cached Docker preview image verified the checkpoint
and all nine GTE files, but lacks `sentence-transformers`, `transformers` and
`tokenizers`; actual model execution in that image remains unqualified.

After completion and STOP, learned observations remain historical. A learned
successor refresh policy is still missing, and mixed selections explicitly
report unavailable instead of regenerating only some families. Further work is
to qualify the declared container dependencies, admit a complete learned refresh
policy, and rerun matched live benchmark arms once the provider route qualifies.
No new training, Hugging Face publication, live provider call, Terminal Bench
score or token-efficiency result is claimed by this change.

The integration preserves concurrent Terminal scoped formal-owner and LegalIR
scope/parser-view work already on `origin/main`, and preserves the existing kit
pin. Runtime qualification commits and subsequent documentation publication
commits remain distinct in the retained ledger.
