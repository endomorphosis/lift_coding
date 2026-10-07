This private runtime implements a bounded replay experiment for the frozen E384
authored formula decoder. The balanced-only continuation previously improved
confidence on sources it already reconstructed, but regressed retained wording.
This experiment alternates the authentic control and balanced banks while
keeping the original decoder/count/used113 streams, objective, optimizer,
selection, architecture and target vocabulary unchanged.

The benchmark CLI is `scripts/ops/autoencoder/benchmark_dual_bank_replay.py`.
Both `--phase preflight` and `--phase training` require `--dimension 384`,
`--dependency-root`, `--extension-root`, `--manifest`, `--plan` and `--output`.
The reserved guardian must provide a fresh output directory, owned resource
admission and complete input/source bindings before executing either phase.
The benchmark performs no work on import. Its phase profiles are exported in
`phase-profiles.json`; `source-freeze.json` pins the source, tests and validation
logs. These files establish no independent execution readiness.

`dual_bank_runtime_adapter.py` supplies the existing numerical trainer's exact
auxiliary interface. `prepare_bank` reruns both genuine profile validators with
their distinct control13 and balanced16 exclusion envelopes, then compares each
complete bank with its frozen expected bytes. Its explicit descriptor stores
two separately sealed180-row banks. It does not manufacture one360-row bank.
`prepare_tensor_cache` prepares both genuine caches for the same working model,
preserves their validated detached handles, and checks every scheduled local
draw. The cache pair copies neither a model nor a tensor and does not mutate an
old cache. The inherited trainer retains its original protected working-model
copy; the dual adapter adds no further model copy.

For global committed step t, even steps use control and odd steps use balanced.
The authentic cache index is its own local ordinal floor(t/2), rather than the
global step. Each bank therefore receives85 updates and510 presentations. All
180 sources in each bank are visited,150 three times and30 twice. Adjacent
control/balanced updates see the same original-rule/template slots using their
distinct native source vectors. Each of the four actual templates receives255
presentations; each modality receives340 overall. The original170 decoder draws
remain independent of this auxiliary schedule. Auxiliary chronology differs
from the archived control fit, so comparison cannot isolate bank composition
from chronology or establish a throughput gain.

Each update calls exactly one unchanged authentic six-source full32 modality CE
forward. The existing trainer adds0.05 times that loss to the ordinary objective
and performs its original backward, clipping, optimizer and checkpoint selection.
The new wrapper preserves the authentic receipt's bank-local committed step
inside `authentic_receipt` and adds the global step, role and schedule hash
outside it. Dispatch has no cursor, so an aborted forward or retry cannot
consume a draw. Attempted, completed and committed work remain separate in the
inherited report. The preflight checks both genuine caches and records two
detached parent loss observations, one from each bank, before fitting.

The numerical trainer's original summary assumes a single bank and computes an
incorrect510 presentations for every declared template. The driver first saves
`training-inherited.json` without alteration and validates the original170
decoder/count/used113 streams against the completed parent report. It then
replays all actual committed dual receipts, validates the full32 CE arithmetic,
and saves `training.json` with the correct bank/template/member counts. The old
counters remain preserved and explicitly inapplicable. Numerical losses,
updates, selected tensor hash and last-attempt tensor hash are not changed by
this metadata reconciliation.

The driver retains both complete endpoints, physically runs all nine original
panels for each, and reads all four source fields from both180 banks. The later
independent evaluator must separately collect the original, old normative and
new balanced TRAIN cohorts before applying the postfit retention check. Exposed
v3 can be read after generation as development evidence, never as an epoch or
checkpoint selector. Selected/last tensor aliases do not become repetitions.

This runtime uses verified existing native384 vectors and historical frozen
numerical/schema owners. It downloads no weights, refits no preprocessing,
changes no encoder context, and performs no canonical parser/compiler source
repair. All outputs are authored empty-qualifier32-token fixture diagnostics.
The original paragraph vectors retain their prior caller-authenticated
provenance limits. A successful reconstruction, valid JSON/schema, loss or
receipt is not source-semantic qualification, proof or Lean admission. Actual
family coverage and `lake build <Lib>` remain separate requirements. The
Constitution remains unformalized, and no checkpoint is promoted by this run.

Fifteen pure/interface tests pass. They exercise both authentic interface calls,
distinct envelopes, actual detached-cache handle retention, all170 local draws,
retry/abort indexing, graph flags, full32 arithmetic, original-report retention,
counter reconciliation and the authentic private import interceptor. Their
synthetic handles and logits execute no neural model. The frozen pure schedule
and its existing17 contract tests remain a separate dependency. Actual memory,
storage, time, retention and emitted-formula effects must be measured during
the independently reviewed guardian phases.
