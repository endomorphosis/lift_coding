# CodebaseIR release dependency audit

This lane inventories existing working source and its Python import dependencies
without editing either external repository. It prepares the roadmap's phase 0
integration manifest; it does not integrate, release, promote, train, prove or
start a service.

Run from the workspace root, choosing a new output directory:

```sh
python3 -B qualification/codebase_ir/release_audit/audit.py \
  --config qualification/codebase_ir/release_audit/codebase_ir.json \
  --output artifacts/codebase_ir_parallel_qualification/release_audit/my-run \
  --snapshot --probe-imports --import-timeout 5
python3 -B -m unittest discover -s qualification/codebase_ir/release_audit -p 'test_*.py'
```

The authored config declares absolute repository roots, ownership of each top
package, ten reviewed seed modules, five import probes, the recorded integration
review, released commits and the former release checkout paths. Current checkout
heads and released commit identities are observed independently. These paths may
have advanced since the review; their names do not establish release identity.

Four independent views are inspected: working bytes; working checkout HEAD
trees; the review's immutable release commits; and the presently observed release
checkout bytes. Git object reads are pinned to resolved commits. The parent
process never imports target source. Scanning visits all lexical imports,
including relative imports, nested function imports, optional branches and
regular ancestor package initializers. Literal `importlib.import_module` calls
are included. Dynamic names, star exports, ambiguous roots, syntax failures,
missing local modules, non-Python assets and external dependencies remain
explicit in each manifest. The scan is a conservative union of code paths.

The default bound is 2,400 modules and 64 MiB of captured Python source per view,
with a 2 MiB per-file ceiling. Bounds are enforced before file-body allocation;
omitted modules are retained in the frontier. Package initializers can expand
the closure well beyond the seed modules. `--max-modules` and `--max-bytes` allow
an explicit ceiling for later qualification. A report can be produced successfully
with unresolved findings: exit status 0 means the working audit was produced,
and does not mean a release gate passed.

`working_vs_*.json` checks each captured working file directly against the
reference source, independently of whether the reference import graph reaches
it. Counts distinguish identical bytes, different bytes, genuinely missing
files, and unread comparisons. The separate `dependency_closure_changes` field
records graph differences. HEAD comparison also records the Git index, so staged
changes are dirty even when current file bytes equal HEAD. Source stability
records the hashes actually analyzed and hashes reread after scanning/probes.
This detects observed changes and is not a filesystem transaction or atomic
capture claim.

Snapshots contain only captured closure Python files and a content manifest.
Files and directories are read-only; omitted assets and modules are not copied.
Each probe uses a separate process with `-I -S -B`, a private current directory,
private temporary/XDG state, a sanitized environment, bounded CPU/address space/
output files and a wall-clock timeout. Only sealed repository roots and the
interpreter's standard library are on its import path. A finder rejects local
module resolution outside the snapshots. An audit hook refuses filesystem
access outside snapshots/private state/stdlib, network operations and subprocess
launches. These Python restrictions prevent accidental interference during
qualification; they are not an adversarial operating-system security boundary.

Import results distinguish `imported`, `absent_local_module`,
`incomplete_snapshot`, `unresolved_dynamic_dependency`,
`environment_unavailable`, `isolated_import_error`, and `timeout`. The raw child
result, stdout/stderr, attempted local imports and resolved local module paths
are retained. Site packages are deliberately disabled, so unavailable external
dependencies indicate a limitation of this probe environment. Optional import
failures may be caught by package code; static manifests and attempted local
imports retain those frontiers. No dependency is auto-installed.

The retained run directory contains configuration and review bytes, source
identities and stability records for each view, direct inclusion comparisons,
immutable snapshots, private import probe evidence, and `summary.json`.
`runtime_closure_proven` and `release_integration_gate_closed` remain false.
Use the manifest to assign the missing/changed files to their existing owners;
do not treat a successful subset import as whole-repository qualification.

## Runtime-demand integration snapshot

The broad lexical scan can exhaust its ceiling before modules needed by a real
import are captured. `runtime_demand.py` addresses that separate gap with a
smaller, observed import scope:

```sh
python3 -B qualification/codebase_ir/release_audit/runtime_demand.py \
  --config qualification/codebase_ir/release_audit/runtime_service.json \
  --output artifacts/codebase_ir_parallel_qualification/release_audit/runtime-run \
  --import-timeout 5
```

The service config names eleven specific finite-service, planner, source-index
and resource modules. The owner copies those modules and ancestor initializers,
seals a read-only generation, and runs private `-I -S -B` import children. Missing
local module requests and exact permitted package-data requests are captured only
after those children finish. The next generation is additive, sealed separately
and chained to its parent's manifest hash. Probes never import from the live
checkout or mutate their snapshots. Duplicate, stale, missing, extra-field and
wrong-type producer bindings are refused; a timeout without its producer binding
remains an unbound failure.

The default bounds are 80 complete probe rounds, 512 captured files, 16 MiB total
source/assets, 2 MiB per file, a five-second individual timeout and a 180-second
capture/probe window. Unresolved results are retained without silently changing
these limits. Module-body imports can be nominated explicitly to avoid repeated
single-module discovery. Such nominations include their source file/hash/line
and remain separate from observed runtime demands; optional branches and lazy
function/class bodies are not nominated.

Permitted data captures stay within the configured package owner and allowed
suffixes. Metadata, workspace, runtime-state and paths outside package ownership
are refused. Native extension modules and unapproved binary assets remain
explicit frontiers. Named `ctypes.dlopen` libraries, network and subprocess
launches remain blocked. The service config explicitly permits
`ctypes.dlopen(None)` solely for standard-library ctypes initialization of the
current Python process API, and records that profile and every permitted handle.
Site packages remain disabled; external runtime dependencies are a separate
environment qualification.

An existing sealed generation can be reused through `--initial-snapshot` and
`--initial-snapshot-sha256`. Its manifest, each copied file, package ownership and
corresponding live source hashes must match the explicit pin. A source change
refuses replay. This reuse does not reset or conceal a prior run's unresolved
result; both runs retain their own bounds and provenance.

`summary.json` includes final snapshot roots/hash, per-seed actual import files,
all requests and nominations, source/head stability, and direct HEAD/released
source inclusion comparisons. `importability_qualified` establishes only that
the specified imports succeeded in the declared environment. Lazy runtime paths,
native service behavior, source/runtime numerical correspondence, signed
authority, resource feasibility and worker execution require their own evidence.

## Recorded invocation source profile

`observed_profile.py` converts a hash-pinned, passed working-source planning
report into an explicit profile of its actual imported core files:

```sh
python3 -B qualification/codebase_ir/release_audit/observed_profile.py \
  --report <planning_qualification.json> --report-sha256 <report SHA256> \
  --config qualification/codebase_ir/release_audit/runtime_service.json \
  --output <fresh invocation-config.json> \
  --seed ipfs_accelerate_py.agent_supervisor.planning.finite_integer_plan_service
python3 -B qualification/codebase_ir/release_audit/runtime_demand.py \
  --config <invocation-config.json> --output <fresh runtime output> \
  --import-timeout 5
```

The adapter preserves each original before/after SHA256, byte size, absolute
source path, observed module names and report identity. Duplicate paths/module
assignments/JSON keys, invalid exact types, changed records, path aliases and
sources outside configured package ownership refuse normalization. Late imports
without before pins remain explicit unqualified records and are not captured.
The profile's normalized owner/module fields are rederived before use.

Runtime capture checks current bytes against those exact recorded pins before
sealing. Every profile file must fit the existing file/byte ceilings; partial
profile capture refuses before probes. Unrecorded demands remain a frontier.
An explicit `--initial-snapshot` with its exact SHA256 can supply additional
previously pinned files: its sealed generation and live source identities must
still match, overlapping observations must agree, and only those manifest-pinned
extras are eligible. No new current source is silently added to a historical
profile. The summary retains both the observation profile and initial snapshot
verification, plus current Git/reference comparisons; current Git identities
are not presented as historical observation identities.

`snapshot_verify.verify_snapshot(root, expected_sha256, expected_roots=[...])`
is a pure standard-library verifier, also importable as
`release_audit.snapshot_verify` when `qualification/codebase_ir` is on the module
path. It checks the canonical generation digest, exact file and directory set,
regular file types, canonical paths, read-only seals and bounded file bytes.
It returns the generation identity, raw manifest-file hash, canonical import
roots and exact file pins. Native consumers can bind their before/after checks
to the same generation without importing core code during verification.

This profile supplies source known to have been imported during the recorded
invocation, and qualifies selected imports in the declared probe environment.
Function invocation coverage remains conditional until a separately authorized
consumer actually executes against the pinned snapshot and records its results.
The snapshot does not qualify external dependencies or change finite numerical,
resource, signing, production-admission or worker-authority limits.

## Retained source and trial provenance

`retained_provenance.py` independently reads a retained finite admission fixture,
its sibling selected-source observations, signed producer declarations and
test ledger. It does not import owner code, verify signatures, evaluate current
finite evidence, materialize tasks or execute a worker:

```sh
python3 -B qualification/codebase_ir/release_audit/retained_provenance.py \
  --fixture artifacts/codebase_ir_terminal_bench/finite-admission-qualification-20261002-04 \
  --workspace /home/barberb/lift_coding \
  --config qualification/codebase_ir/release_audit/runtime_service.json \
  --output <fresh ledger directory>
```

The default selected-source manifests are `critical-source-before.json` and
`critical-source-after.json` in the sibling directory with `qualification`
replaced by `tests`; explicit `--source-before`/`--source-after` paths are also
supported. The output `ledger.json` binds the exact raw fixture result through
`raw_result_sha256` and each other input through `input_artifacts`. It records
retained source hashes, current source observations and direct working HEAD,
reviewed-ref and release-checkout comparisons. Current bytes may differ from
retained bytes without changing historical source custody. A change during
this audit refuses the result instead of claiming an atomic capture.

The fixture04 ledger has 47 critical source copies and ten fixture producer
copies. Nine fixture producers overlap the critical population; the experiment
driver is an additional fixture-only source. All six signed producer hashes
overlap retained critical source, while five have a separate fixture copy.
The signed finite matcher is preserved in the critical source tree, even though
it is absent from the fixture's flattened ten-file directory. These populations
remain separate; they are selected files rather than an executed dependency
closure or process-origin attestation.

Pinned JUnit XML independently corroborates trial case identities/statuses.
The clean current boundary trial has 38 passing cases. Capacity originally had
18 passes and three failures; three targeted retries yield a 21-case latest
overlay. The older compatibility run has 136 passes and three failures, with a
119-case passing historical subset. The ledger preserves those original
failures and records that the overlay is not a single clean combined run.
Historical signed-verification assertions are retained separately from current
freshness; neither is authenticated by this ledger.

The first real ledger observed a current change in the selected datasets
`logic/backends/process.py` compared with its retained source. Its other selected
source and producer copies still matched their recorded hashes. This is an
observed owner-source change, not evidence that the read-only audit altered
source or that the older trial ran against the current implementation.

Readers reject symlinks, aliases, FIFOs, duplicate JSON keys, nonfinite numbers,
invalid pin types, foreign source ownership, substituted live copies and
case/count/retry corruption. Files are bounded to 4 MiB, first captures plus
reference Git source bodies to 64 MiB, distinct filesystem reads to 256, and
trial case populations to 4096. Stability rereads are bounded to each initially
captured file's size. `ledger_produced` means the provenance inventory was
produced; authority and current-freshness flags stay false.

## Private retained basis for historical replay

`retained_snapshot.py` joins a hash-pinned read-only historical replay's actual
import observations, the original selected critical source copies, and an
explicitly pinned earlier sealed generation. It creates a new generation using
the same manifest and pure verifier contract as the runtime-demand snapshots.
Its required pins are `--historical-report-sha256`,
`--source-before-sha256`, `--source-after-sha256` and
`--initial-snapshot-sha256`; corresponding paths are supplied through
`--historical-report`, `--source-before`, `--source-after` and
`--initial-snapshot`. The selected source paths default to the fixture's sibling
tests directory when `--fixture` is supplied. `--workspace`, `--config` and a
fresh `--output` complete the invocation.

Only actual recorded imports and files from the verified prior generation enter
the sealed import scope. Original critical copies select the retained source
basis for overlapping paths. An override records both the selected old identity
and the differing observed-current identity, its exact retained origin and the
reason for selection. Other historical/prior disagreements refuse. Current
source can supply a recorded import only when its bytes still match that
explicit unchanged observation. There is no current fallback, new import scan
or process-origin claim. Selected files outside that import scope remain
provenance-only, and missing ancestor initializers refuse instead of expanding
the scope silently.

The real retained-basis generation has 220 files and 13,680,425 bytes. All 47
critical copies are verified; seven unobserved selected files, including the
entrypoint facade, remain provenance-only outside the import snapshot. The first
capture's unrecorded facade-package initializer refusal is retained separately.
Its single differing override selects the original retained
datasets `logic/backends/process.py` (SHA256 `5c569b34afd75e1942f11fcb9ecf20d57799d2762927d9379813ce94aca437e1`)
in place of the refused historical attempt's newer source. The live file is not
modified. The generation identity is
`949a715ab5abc0335d1ca3bfe45a5e7265eab888949174ed475fc3682275f5db`.

The output `summary.json` pins copied raw input artifacts, the fixture result,
every selected source origin, explicit overrides and the verified generation.
Late imports, duplicate original paths, conflicting provenance, malformed exact
types, aliases, symlinks, altered retained copies and source drift refuse the
capture. The snapshot retains the 512-file, 16 MiB total and 2 MiB/file bounds.
Creating it does not execute a historical verifier, establish current freshness,
reproduce the original whole dependency closure or authorize a worker. Any
subsequent owner-local historical replay is a separate bounded trial.

`retained_supplement.py` can inventory a named missing import from a hash-pinned
sealed historical trial. It reads only recorded artifacts and selected retained
Python files. The CLI takes `--snapshot-root`, `--snapshot-manifest-sha256`,
`--source-report`, `--source-report-sha256`, `--frontier-report`,
`--frontier-report-sha256`, `--module`, `--initial-snapshot`,
`--initial-snapshot-sha256`, `--config` and a fresh `--output`. Invoke it with
`python -B` like the other sibling-module CLIs. It produces `supplement.json`
(schema `codebase-ir-retained-static-supplement/v1`) and an inventory receipt.
The sealer consumes that exact file through `--supplemental-profile` and
`--supplemental-profile-sha256` and independently rebuilds the selected import
scope before copying it.

Legacy static snapshots require the raw manifest SHA, exact closed pin schema,
file/directory population, read-only seals and selected source hashes. The raw
original capture report must agree with every manifest pin and retain stable
source and Git HEAD observations both before and after its probes. Only selected
source bodies are rechecked; this does not requalify all legacy bytes. The
missing-module trial must bind the exact verified prior generation. Import
inventory includes relative imports, package initializers and imports inside
functions; external, dynamic and star scopes stay explicit. A missing retained
local dependency refuses instead of falling back to current source.

An additional original copy population is supplied through `--retained-before`,
`--retained-before-sha256`, `--retained-after`, `--retained-after-sha256` and
`--workspace`. This separate metadata format is
`finite-admission-selected-source-snapshot@1`. It permits at most 4,096 metadata
rows and requires exact counts, unique original paths, unchanged before/after
pins, an empty change list and the recorded `sources/<original workspace path>`
copy location. Only demanded package sources enter the snapshot. Those origins
are labeled `verified_original_retained_dependency_copy`, separately from
`verified_earlier_static_capture`; enumerating metadata does not qualify every
source body. Snapshot bounds remain 512 files, 16 MiB total and 2 MiB/file.
Input manifests are capped at 4 MiB, the original static report at 32 MiB,
first input captures at 64 MiB, AST nodes at 100,000/file and import nominations
at 8,192. Stability rereads are independently bounded by their captured sizes.

The real legacy-only inventory refused because the earlier 64 MiB closure had
omitted `objectives.ir_learning_campaign_contracts` at its byte frontier. That
refusal is retained in `admission-supplement-inventory-20261002-02`. The original
fixture's broader before/after metadata then supplied exact retained copies of
both the planner and contracts module. The resulting profile
`89b66d0ea21d28497b7712cf3a6d2973a5eb3acd6b718aa04d8c265f6437e91f`
selects two files, 77,251 bytes, with eight imports already in the prior snapshot.
Its 3,003 original metadata rows remain a metadata inventory.

The separate supplemental generation has 222 files and 13,757,676 bytes,
identity `c0dfa09657489dec8ab14cf6a3700151f8b181904f5c1da091ccf98efc08deae`,
under `admission-retained-supplement-snapshot-20261002-01`. Both selected files
come from original retained dependency copies. The old 220-file generation and
its unavailable historical trial are preserved. Sealing this new generation
does not call a native verifier, establish current freshness, attest original
process execution or reproduce the whole producer dependency closure.

The parent then ran one separately retained historical trial against this
222-file generation. Its receipt at
`acceptance/20261002-admission-history-retained-supplement-01/historical_replay.json`
has raw SHA256
`50abedb3ea89597b42f6d6180636f258d4ba7d86ec61bf3f9dceaa9ec715a496`.
It reports `unavailable` at the newly exercised
`ipfs_accelerate_py.agent_supervisor.proof.code_property_catalog` import.
Snapshot identity before/after is stable, with 218 loaded core files and 706
read files unchanged, six signed and nine frontend pins matched, and zero native
verification results or corruption controls. No fallback or retry occurred.

A read-only future-option check found a matching original copied catalog pin,
SHA256 `0d127ae0849060aaa169e7cc435191f623d7511496af456100b642a135687958`,
16,902 bytes, in the same before/after copied-source metadata. Its retained
bytes match that pin. This file was not added to a profile or generation, and
its transitive invocation scope remains unqualified. The successful source
supplement and unavailable historical verification remain separate findings.
## Commit-pinned release reconciliation and selected inclusion

`release_matrix.py` reads only explicit Git objects and hash-pinned public local
documents/retained source bytes. It never fetches, checks out a tree, imports an
owner module, executes a proof/model/service workflow, or changes a status ledger.
It records each of the 32 task claims independently from their prerequisites and
the selected byte-inclusion checks. `status: passed` means this bounded
reconciliation completed with stable inputs; it does not mean release acceptance
was replayed or a recorded gap was repaired.

```sh
python -I -B qualification/codebase_ir/release_audit/release_matrix.py \
  --manifest /home/barberb/lift_coding/qualification/codebase_ir/release_audit/release_matrix_20261002.json \
  --output /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/<fresh-run>
```

The closed input schema is `codebase-ir-release-matrix-input@1`. All top-level
fields are required: `repositories`, `ledger`, `released_documents`,
`local_documents`, `selected_evidence`, `source_profiles`, and `snapshot` (null or
one explicit generation pin). Repository rows bind canonical absolute roots,
exact 40-hex commit IDs, names, and package roots. Ledger/document rows bind raw
SHA-256s; a null released-document digest explicitly requests verified absence.
Local document rows bind exact byte sizes and digests, `source_basis`
(`current_working_source` or `retained_working_observation`) and an `observed_path`
metadata label, with exactly one `task_table` and optional `context` documents.
A retained observation is a separately read/hash-pinned copy outside the source
repository; its original path is metadata and is never used as a live fallback.
Source profiles bind exact selected
package paths to canonical retained copies outside the live repositories; a
snapshot instead binds its complete selected file set through `snapshot_verify`.
Duplicate identities, nonfinite/duplicate JSON, bool counts, malformed or cyclic
prerequisites, symlinks, nonregular local input files, and mutable Git refs refuse.
Output is preflighted outside original repository, snapshot, local-document and
selected retained-copy directories before anything is created.

`release_matrix.json` uses `codebase-ir-release-matrix@1`. It includes the exact
`manifest_sha256`, `declared_counts`, `reconstructed_claim_counts`, 32 `criteria`
rows, `criterion_source`, selected `evidence` and `selected_sources` comparisons,
`input_stability`, and before/after snapshot identity. Each frozen criterion gets
its own text digest. The original whole TODO digest remains a released ledger
claim when its original bytes are unavailable; it is never reconstructed from
the rows. Local criterion changes do not silently replace frozen acceptance
criteria. RPI prerequisite blockers are expanded transitively; conditional and
external TIP declarations remain explicit, without independently qualifying
their claimed profiles.

Selected Git blob bodies, pinned commit objects and every traversed pathname
tree object are bounded before reads and independently checked against their
Git object IDs. Tree metadata is cached with a 4,096-entry per-tree limit;
unselected blob bodies and commit ancestry are not read. Replacement objects,
ambient Git routing/config variables and lazy fetches are disabled. Commands have
five-second deadlines, an aggregate 120-second window and 2,400-call ceiling.
First-captured local inputs plus Git bodies are limited to 64 MiB, 4 MiB per file;
local inputs have 768-file and equal-size stability-reread bounds. A selected
sealed source generation has separate 512-file/16-MiB/2-MiB-per-file bounds for
each of its two verification passes. Source/evidence inclusion is exact byte
comparison, not importability. Evidence children, private owner state, tools,
native environment dependencies and dynamic imports remain outside this selected
qualification scope. All four native/training/current-authority/production
requalification flags are false.

The authored actual spec freezes accelerate
`8a37a3a81b99be4cc1f8df1143f308a3b7d1875e` and datasets
`8de37ba8d216cd21a5d7134292de01d9e12c9a56`, the 62 top-level evidence IDs in
the released ledger, and the historical 222-file generation `c0dfa096...` above.
Its final raw SHA-256 is
`3df7d1f2f3da7a3ffc2c0c80a4773bccdf709b60b48f6bdd4d8553258e120699`.
The released ledger itself is pinned at
`deaa08bfcda1367427a7f5165f5bcd4adeebbc89b932e648d58333599ed4100c`.
The local TODO was newly captured at
`9a04ac23336265bc508d06b049110b4e71d39bf89a6742cea1e7638ef3d578b1`,
rather than reusing the earlier `3b96...` observation. RPI-003, RPI-029 and RPI-032
criterion text differs from the frozen ledger basis; both roadmap and TODO are
absent at the selected accelerate commit.
The exact documents and a before/after observation receipt are sealed beneath
`release-matrix-inputs-20261002-01`. Receipt raw SHA-256 is
`8db869b31120ef98785def52bdbbc17989111e10c5aa99ef0e5047a156ad27a8`;
the original live-document spec `3cbb63e...` is preserved there separately.
The final input uses retained working observations, so current live document
freshness is explicitly unqualified.

The actual reconciliation retains 18 declared profile closures, 14 open tasks,
and 22 own criteria qualified for their stated profiles. RPI-010, RPI-011 and
RPI-027 remain dependent on open RPI-022; RPI-021 retains external TIP-010/011
blockers. All 62 selected top-level evidence bytes match their ledger pins.
The historical 222-file source profile compares as 204 identical, 12 different,
and 6 missing released files. This says how that selected older source basis
relates to these two commits; it does not invalidate separately qualified newer
profiles or certify a complete released runtime closure.

The six absent source paths are accelerate planning `codebase_feature_context.py`,
`finite_integer_capacity.py`, `finite_integer_capacity_preview.py`, and
`finite_integer_source_custody.py`; accelerate runtime
`finite_repository_admission.py`; and datasets software contracts
`codebase_integer_model_lean.py`. The twelve different source paths are accelerate
proof `multi_prover_resources.py` and `multi_prover_router.py`; datasets
`duckdb_control/codebase_catalog.py`, `logic/backends/process.py`, software
contracts `codebase_finite_integer_observation.py`, `codebase_integer_profile.py`,
`content.py`, and `semantic_index/python_analysis.py`; software verification
`pipeline.py` and `source_adapters.py`; and optimizer
`proof_resource_safety.py` and `resource_scheduler.py`. The report retains both
exact source digests for every differing path.

`release-matrix-20261002-01` preserves the initial completed report. The subsequent
final report adds independent commit/tree-object identity checking and retains
the same exact source/document byte basis through the private document copies.
Neither run expands the earlier
historical replay frontier at `code_property_catalog` or performs native replay.

## Portable selected release-review bundle

`portable_review.py` materializes and independently verifies the already-pinned
review scope. It carries the exact original spec and report as inert provenance,
fixed local document copies, selected historical source bytes, selected released
blob bytes, and the verified commit and traversed tree objects necessary to
authenticate pathname inclusion or absence. Tree objects may mention other
names; no unselected blob bodies or commit ancestry are captured. It does not
execute package sources or replay any native qualification.

```sh
python -I -B qualification/codebase_ir/release_audit/portable_review.py build \
  --manifest /home/barberb/lift_coding/qualification/codebase_ir/release_audit/release_matrix_20261002.json \
  --manifest-sha256 3df7d1f2f3da7a3ffc2c0c80a4773bccdf709b60b48f6bdd4d8553258e120699 \
  --report /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/release-matrix-20261002-03/release_matrix.json \
  --report-sha256 e5ce6590f19aa76a07aa6f1e467362ac10e57e2af98a5e800a425755127c0421 \
  --output /absolute/private/fresh-build

python -I -B /relocated/bundle/tools/portable_review.py verify \
  --bundle /relocated/bundle \
  --bundle-manifest-sha256 <exact-raw-manifest-sha256> \
  --output /absolute/private/fresh-verification
```

The sealed bundle filename is **`bundle_manifest.json`**, with schema
`codebase-ir-portable-release-review@1`. Its closed manifest binds exact relative
files/directories, raw SHA-256s and sizes, selected repository/commit/package
identities, typed Git objects, fixed documents, retained source copies or sealed
snapshot identity, the original spec/report, and the three owned stdlib tool
modules. A build independently reconstructs the pinned matrix and refuses any
changed scope decision. The copied snapshot manifest is pinned to its previously
verified raw digest and the fully sealed copied snapshot is checked again before
build success. Every payload plus the manifest fits 768 files and 64 MiB; selected
source bounds remain 512 files/16 MiB, raw objects/files 4 MiB each, captured Git
objects 512, directories 2,048, commands 2,400, and the operation window 120 seconds.

Verification requires the external exact raw manifest digest. It reads only the
bundle, reconstructs Git object hashes and selected path traversal without Git,
rederives all 32 criteria and selected source/evidence comparisons, and checks
that every captured object body was necessary for that selection. Original paths
inside provenance documents are never opened. Exact no-follow file and streamed
directory/seal populations are checked before processing and after byte rereads;
extra files, FIFOs, symlinks, added/removed empty directories, changed permissions,
hash/type/authority mutations and byte/count overruns refuse. Output must be fresh
and outside the relocated bundle and all lexically recorded original input scopes.

The output filename is **`portable_review.json`**, with schema
`codebase-ir-portable-release-review-verification@1`. It binds
`bundle_manifest_sha256`, the original spec/report raw digests, recomputed task
claims, evidence/source dispositions, file/object/byte counts and stability.
`portable_scope_complete: true` means only that all explicitly selected review
bytes and absence findings were portable. Native execution, training, current
authority, production requalification, original-path reads and Git executable
invocation are false. Evidence children, private owner state, tools/native runtime
environment qualification, dynamic imports and complete runtime closure remain
explicit omissions. Raw digests establish identity, not producer signatures or
the semantic truth of retained numerical/proof claims. Executing packaged tools
assumes reviewed tool code or independently checked tool pins.

The actual build is `portable-release-review-20261002-01/bundle`, with manifest
SHA-256 `d510e678787aa856587d16abd502a1e9b4337ae5860b308b39e651f334e2ebd1`.
The separately retained relocation is
`portable-release-review-relocated-20261002-01/bundle`; its identical raw manifest
binds **601 files, 370 Git objects and 29,237,650 bytes**. The bundled standalone
verifier completed with an empty executable PATH and an audit guard that refused
subprocesses, original workspace reads and owner-source execution. Its scoped
result preserves all 62 matching top-level evidence files and the source
comparison of **204 identical, 12 different and 6 missing**; it does not repair
the gaps or expand the historical admission replay frontier. Original reports,
specs and snapshots remain unchanged. Twelve authored portable controls pass;
the release lane now has 103 passing stdlib tests and repository Ruff is clean.

## Deterministic selected review archive

`portable_archive.py` transports the selected portable capsule through a
deterministic ZIP archive and verifies a fresh local restoration. Both operations
use `--manifest --output`; the verifier requires an exact archive SHA-256 and
byte count independently of the original bundle-manifest SHA-256.

```sh
python -I -B qualification/codebase_ir/release_audit/portable_archive.py build \
  --manifest /absolute/archive_build_input.json \
  --output /absolute/private/fresh-archive-build

python -I -B qualification/codebase_ir/release_audit/portable_archive.py verify \
  --manifest /absolute/archive_input.json \
  --output /absolute/private/fresh-restoration
```

The closed build input schema `codebase-ir-portable-release-archive-build-input@1`
contains `bundle_root` and `bundle_manifest_sha256`. Build verifies the source
capsule, its exact sealed file/directory population and independently pinned
payloads, then emits `portable_review.zip`, `archive_input.json` and
`portable_archive_build.json`. The generated verification input has schema
`codebase-ir-portable-release-archive-input@1`, an `archive` descriptor with
absolute canonical `path`, exact raw `sha256` and integer `size_bytes`, and
`bundle_manifest_sha256`. A copied verification input may share a parent with
the fresh runner destination because payload paths are absolute. Output must
remain outside the archive parent, selected source capsule and original input
scopes; descending from sealed directories is refused before writes.

The codec accepts only canonical ZIP_STORED records: UTF-8 names, sorted entries,
1980-01-01 timestamps, Unix regular-file/directory types and exact 0444/0555
seals. It performs no decompression and never uses `extractall`. Raw EOCD count
and central-directory boundaries are validated before any member inventory is
allocated. Archive bytes fit 64 MiB, entries fit 2,816, central bytes fit
2,816 times 1,071, file bodies fit 4 MiB, payload bytes fit 64 MiB, files fit
768, directories fit 2,048, and each operation fits 120 seconds. Input manifests
fit 256 KiB and the embedded bundle manifest fits 1 MiB. Stable raw input
rereads have separate equal-size limits. ZIP64, compression, encryption,
comments, extras, data descriptors, absolute or traversal paths, platform
aliases, duplicate/unsorted names, symlinks, FIFOs, other file types, trailing
or prepended bytes, gaps, mismatched local/central headers, CRC corruption and
unselected members all refuse. Matching a repaired CRC or archive digest alone
cannot replace the separate bundle-manifest and payload SHA-256 pins.

All names, populations, raw hashes, lengths and CRCs pass before restoration.
The fresh restored capsule is sealed, passed to the existing offline portable
verifier, and reread again before the archive report is published. The output
`portable_archive.json` has schema
`codebase-ir-portable-release-archive-verification@1`; it binds the raw input,
archive and bundle-manifest digests, a retained restored verification report,
exact counts, review omissions and source/evidence dispositions. Its
`archive_roundtrip_verified` and `portable_scope_complete` flags apply only to
these selected review bytes. Native execution, training, current authority,
production requalification, Git subprocesses, original-path reads, network
access and runtime/environment qualification remain false. Producer signatures,
numerical correctness and complete released runtime closure remain outside
this selected byte transport scope. Package sources and bundled tools remain
inert archive payload; verification uses the reviewed local qualification tools.

The actual archive is
`portable-review-archive-build-20261003-01/portable_review.zip`, raw SHA-256
`2013fc6a2264d1c89fce1b0df92951c0067ce9b5b41ff0608c8edebaa556465a`,
with **29,378,906 archive bytes, 601 files, 45 directories and 370 Git objects**.
The raw payload remains 29,237,650 bytes with bundle-manifest SHA-256
`d510e678787aa856587d16abd502a1e9b4337ae5860b308b39e651f334e2ebd1`.
Its `archive_input.json` raw SHA-256 is
`f9be1f7b886bc918d4a5ada65cb007e812fbc0b3091473e5a6b861c2766daadb`.
The retained restoration report is
`portable-review-archive-restored-20261003-01/portable_archive.json`, raw SHA-256
`fb94b713ee96e73fd3747a8f47995a2701bba9191689ca0867410e19928b6e4a`.
It preserves **62 matching evidence files and 204 identical, 12 different,
6 missing selected source files**. Twenty-one archive tests cover deterministic
standard-ZIP compatibility, custody pins, attacks, bounds, output preflight,
late input/restored drift and Git-free relocation; the release lane has 124
passing stdlib tests. Earlier capsules, matrices and source profiles are retained
unchanged.

## Released child evidence custody

`evidence_children.py` audits the public children explicitly listed by selected
released evidence manifests. It uses the existing independently hashed,
sanitized, bounded Git object reader; it never imports or executes a retained
driver, source file, checker, model or signed record.

```sh
python -I -B qualification/codebase_ir/release_audit/evidence_children.py \
  --manifest /absolute/evidence-children-input/manifest.json \
  --output /absolute/private/fresh-evidence-children
```

The closed input schema is `codebase-ir-released-evidence-children-input@1`,
with exact `repositories`, `ledger`, `selected_evidence` and `expansion_policy`
fields. Repositories and the released ledger reuse the existing matrix's exact
commit and raw SHA-256 pin contracts. The policy is
`one_level_explicit_files@1`. Four reviewed manifest schemas have exact
`schema`/`files` fields: `repository-evidence-files@1` and
`codebase-source384-acceptance-evidence@1` use `path`/`sha256`/`bytes` child rows;
`closed-local-evidence-manifest@1` and `retained-evidence-manifest@1` use
`path`/`sha256`/`size_bytes`. Unknown parent schemas remain unsupported rather
than being interpreted heuristically. Child payloads remain inert, including
JSON bodies that themselves describe additional references.

Every child path is resolved relative to its declaring public `docs/` manifest
at the same immutable commit. Working files are never a fallback. Missing,
different, repeated-within-parent, cyclic selected-manifest references and
unsupported parent schemas retain explicit dispositions. A shared body declared
by two parents retains both memberships and one copied body; it is distinct
from a repeated row within one parent. `all_selected_children_verified` is true
only when every selected parent expands and every declared child row verifies.
`status: passed` means the bounded diagnostic inventory completed with stable
inputs, even when that flag is false.

The workflow bounds input/parent manifests to 256 KiB, selected parents to 16,
aggregate child rows to 256, declared child bytes to 32 MiB, individual Git
bodies to 4 MiB, and original-input plus initial/fresh Git-object reads to
64 MiB. It retains the existing 2,400-command/120-second bounds. Aggregate
declared counts and bytes are checked before child body reads. Original input
rereads and two retained-copy checks have separate equal-size budgets. A fresh
Git reader rechecks selected commit/tree/blob identities and exact path results.
Copies are sealed, with exact file/directory/type/permission populations checked
before publication. Fresh output must lie outside original repositories and the
input manifest's parent, with no symlink or sealed-directory ancestry.

The report is `evidence_children.json`, schema
`codebase-ir-released-evidence-children-audit@1`, binding `manifest_sha256` and
`ledger_sha256`. `child_evidence_custody_inventory_produced` and
`git_object_verification_performed` establish this selected byte inventory.
Producer authentication, numerical/checker replay, runtime/environment closure,
current authority and production requalification remain false. One-level child
custody does not establish complete transitive evidence or execution semantics.

The actual input `evidence-children-input-20261003-01/manifest.json` has raw
SHA-256 `faed032a116aca7854195962ca46fd8a3d7aa9c8443cc0fec6a6d70853a4cdee`
and preserves the earlier accelerate/datasets release pins and ledger. The final
retained report `evidence-children-retained-20261003-03/evidence_children.json`
has raw SHA-256
`d54732305a84a033d84c8e478e0a5bc3fbbdb67e2e45b90960a30dffe0b53b64`.
All **104 children** verify: 56 native supervision, 21 behavioral admission,
9 behavioral planning and 18 source384 acceptance. Their **5,151,792 bytes** are
retained with the input, ledger and four parent manifests as **110 files and
5,265,603 bytes**. The run uses 544 bounded read-only Git commands; original,
selected Git and copied byte identities remain stable. The source384 public
learned/zero-head/model-off/qualification bodies are available as sealed inert
inputs for the separate corpus diagnostics lane. The earlier 01 inventory keeps
its original two-supported/two-unsupported scope, and all preceding matrices,
archives and source generations remain unchanged.

Twenty new controls cover memberships, correlated rebinding, unsupported and
missing evidence, path/schema/bound refusals, late input/Git/copy drift, changed
permissions and extra directories/FIFOs. The full release lane has **144 passing
stdlib tests** with project Ruff passing.

## Portable released child evidence

`portable_evidence_children.py` builds a separate capsule from an exactly pinned
child input and qualified custody report. It independently repeats custody with
the existing bounded Git reader, retains the selected commit/tree/blob bodies,
and compares every parent and child decision with the pinned report. Earlier
release capsules and source snapshots retain their original scope.

```sh
python -I -B qualification/codebase_ir/release_audit/portable_evidence_children.py build \
  --manifest /absolute/child-capsule-build-input/manifest.json \
  --output /absolute/private/fresh-child-capsule-build
python -I -B qualification/codebase_ir/release_audit/portable_evidence_children.py verify \
  --manifest /absolute/relocated-child-archive-input.json \
  --output /absolute/private/fresh-child-capsule-restoration
```

The closed build schema is `codebase-ir-portable-evidence-children-build-input@1`,
with `source_manifest` and `source_report` absolute `path`/`sha256`/`size_bytes`
descriptors. The closed verification schema is
`codebase-ir-portable-evidence-children-input@1`, with an exact `archive`
descriptor and `capsule_manifest_sha256`. The inner manifest is
`capsule_manifest.json`, schema `codebase-ir-portable-evidence-children-capsule@1`.
Verification publishes `portable_evidence_children.json`, schema
`codebase-ir-portable-evidence-children-verification@1`, bound to the raw input,
archive and inner manifest hashes.

The deterministic stored ZIP reuses the existing strict ZIP codec, sealed
population checks and bounded readers. Verification replaces only Git object
transport with an inert object store; the existing tree and blob proof checks
still derive exact paths from independently hashed commit and tree bodies.
Original source input bytes stay pinned and inert. Only repository roots are
rebased in a new temporary replay input, without opening their original paths.
The comparison preserves declared and observed hashes, sizes, Git identities,
commits, child memberships and missing/different/repeated/shared/cyclic decisions.
It normalizes only copied/input locations and variable read costs. Unused objects,
undeclared files and directories, missing proof bodies and scope changes refuse
verification. A completed diagnostic capsule can still contain unavailable or
unverified children; `all_selected_children_verified` retains that distinction.

The capsule bounds 768 files, 2,048 directories, 512 selected Git objects,
4 MiB per payload, a 1 MiB inner manifest and 64 MiB aggregate payload/archive
sizes; the archive allows at most 2,816 entries. Object, file and byte counts are
checked before payload reads, and the inherited 120-second and 2,400-object-query
bounds remain active. Equal-size rereads check original inputs, copied payloads,
written archive and restored payloads before reports are published. Output lies
outside selected input and original repository scopes, with symlink and sealed
ancestry refused. This is observed sequential stability, without an atomic
capture or producer-authentication claim.

The selected build `portable-evidence-children-build-20261003-01` packages the
prior `faed032a...` child input and `d5473230...` report without changing them.
Its **242 files, 37 directories and 124 Git objects** retain all **104 children
and four parents**, with **11,037,125 capsule bytes**. The stored archive is
**11,117,145 bytes**, SHA-256
`4b96d3ba7b97878bae1255885148a40ec7f2b8bcefcb46ba1dc7e03edc03ca86`;
the inner manifest SHA-256 is
`5eb5d61d6c319bc906a92697d18ac0e7d3856c5339f79e897164df0c6babf7a8`.
The relocated input `portable-evidence-children-relocated-20261003-01/manifest.json`
has SHA-256 `06e45d495df7d545119310d9235c9c6080ee9dbfedb7f5e5f615a355f5da9d21`.
Its restoration report has SHA-256
`6aabbd0c6415d25673c1f65acd7821bd39ac3441dc196cfa81fae4d276009a76`.

A separate audit-hook guard executes only the six copied verifier modules with
an empty `PATH`. It refuses child processes, network events, original workspace
opens and public/owner source execution. The selected run records zero attempts
and retains `offline_guard_receipt.json`, SHA-256
`e96019f226c0c0ac22948e5e23089106a134d18cb1061bb543f679afe67bccd7`.
These stdlib restrictions are an independent observed-operation control, not an
adversarial operating-system boundary. One-level expansion remains explicit;
transitive expansion, signatures, checkers, numerical execution, runtime closure,
current authority and production requalification remain false.

Sixteen additional controls cover deterministic encoding, relocation after
original inputs disappear, forged prior decisions and correlated hash repairs,
unused/missing Git objects, diagnostic memberships, preallocation ceilings,
strict JSON and output scopes, and late archive/body/type/permission drift.
The release lane has **160 passing stdlib tests**, with project Ruff passing.

## Committed producer-source bindings

`producer_source_bindings.py` adds a separate source-inclusion capsule for the
two already verified public producer inventories under behavioral admission
and behavioral supervision. The old 222-file source profile selected none of
their eight producer paths. The source binding keeps ten declared memberships,
including two sources shared by both receipts, and preserves each declared SHA
and the presence or absence of a declared size.

```sh
python -I -B qualification/codebase_ir/release_audit/producer_source_bindings.py build \
  --manifest /absolute/producer-source-build-input/manifest.json \
  --output /absolute/private/fresh-producer-source-build
python -I -B qualification/codebase_ir/release_audit/producer_source_bindings.py verify \
  --manifest /absolute/relocated-producer-source-input.json \
  --output /absolute/private/fresh-producer-source-restoration
```

The closed build schema is `codebase-ir-producer-source-bindings-build-input@1`,
with an exact `custody_capsule_manifest` `path`/`sha256`/`size_bytes` descriptor
and two `selected_receipts` rows containing `evidence_id`,
`receipt_relative_path`, `sha256` and `size_bytes`. The selected IDs are
`behavioral-repository-admission` and `behavioral-native-supervision`, with
`producer-sources.json` relative to each parent. The former receipt has schema
`repository-behavioral-admission-sources@1` and declares sizes for three claims;
the latter uses `qualified-source-inventory@1` and declares only SHA-256 for
seven claims. Observed file sizes never become declared size checks.

Build reads selected inert views from the earlier pinned custody capsule and
independently checks its ledger, two public parent manifests and two receipt
bodies through the existing immutable Git reader. It then captures only the
eight declared source paths at accelerate commit
`8a37a3a81b99be4cc1f8df1143f308a3b7d1875e`. Fresh commit/tree/blob reads recheck
every selected path. Current working source is never a fallback or comparison.
Source payloads stay inert, including tests and benchmark drivers. The workflow
retains verified, different, missing, repeated and undeclared-size dispositions;
shared memberships stay separate. A completed diagnostic audit can contain
different or missing producer source. `all_selected_sources_verified` is true
only when every selected membership meets its declared checks.

The separate capsule is `producer_source_capsule.json`, schema
`codebase-ir-producer-source-bindings-capsule@1`. The closed verification input
is `codebase-ir-producer-source-bindings-input@1`, with `archive`,
`capsule_manifest_sha256` and `custody_capsule_manifest_sha256` pins. Verification
publishes `producer_source_bindings.json`, schema
`codebase-ir-producer-source-bindings-verification@1`. It reuses the unchanged
strict stored-ZIP codec, readers, exact seals and inherited offline Git proof
logic. Every source decision and membership is independently rederived, with
unused objects, unselected files, authority changes and altered provenance
refused. Final fences reread the written archive/input and restored payloads.
The bounds are 32 source claims, 128 objects, 256 capsule files/directories,
4 MiB per payload, 1 MiB per capsule header and 64 MiB aggregate bytes, with
the inherited 120-second and 2,400-object-query ceilings. Uncaptured proof bodies
cannot be promoted into a successful portable verification.

The selected build uses input SHA-256
`d97cc28036f050fb46707621bd8c7c08a2a54519f2ae10f04cb740e2012cb45a`
and binds the existing `5eb5d61d...` child capsule without modifying it. The
admission receipt SHA-256 is `8c94715a...` (739 bytes), and supervision is
`6197d1bb...` (1,391 bytes). All eight committed files are retained. Eight of ten
claim memberships match, while two supervision benchmark sources differ:

| Source beneath `benchmarks/agent_supervisor/container_coding/` | Declared SHA prefix | Committed SHA prefix | Observed bytes |
| --- | --- | --- | --- |
| `native_repository_finite_supervision.py` | `78e36aa2` | `b2a94ee2` | 50,696 |
| `repository_benchmark_preparation.py` | `47a39301` | `b8ea36fd` | 19,981 |

Their declared sizes remain unavailable, and `all_selected_sources_verified`
is false. These differences establish a release-inclusion gap between public
producer claims and the selected committed bodies. They do not establish which
bytes ran or invalidate the separate verified custody of the receipt bodies.

The capsule contains **56 files, 31 directories and 31 Git objects**, totaling
**1,327,026 bytes**. Its stored ZIP is **1,343,610 bytes**, SHA-256
`43359dbe7729362786ac5af251e8d91fc6fe71b9009077df96fc5d3e121b2e28`;
the inner manifest SHA-256 is
`0fe184b4e8ca3cef43c12d9b3172da2a58fc1828d8d1567bdf9bef78fd9c05d9`.
The relocated `producer-source-bindings-relocated-20261003-01/manifest.json`
has SHA-256 `78ac13e44da6c108fa3d1cf98e6412c4b119722b00e10d96fb78c878097f56cc`.
Restoration report SHA-256 is
`cf6970e41fcbb8d3f7eb31259badb0eab82fcdc354d459fc26d3c42069c827c2`.
The independent guard executes seven copied verifier modules with empty PATH,
refusing original workspace opens, payload execution, network and subprocesses.
It preserves the two differences with zero forbidden-operation attempts;
guard receipt SHA-256 is
`a110b1591302553f7c37ccee6b6feb2be241d99f7f65b03e974014edd086d62b`.

Seventeen new controls cover shared/repeated/conflicting source claims,
undeclared sizes, missing/changed bodies, deterministic relocation, repaired
outer pins on source/parent/receipt object forgeries, unused/missing proof objects,
preallocation and schema/path refusal, ignored dirty working bytes, and late
original/input/archive/copy/type/permission drift. The release suite has
**177 passing tests**, with its final full log retained under
`producer-source-bindings-validation-20261003-01/release-tests.log` and Ruff
passing. Source imports, producer execution authentication, semantics, dependency
closure, runtime qualification and production requalification remain false.


## Explicit historical producer-source provenance

`producer_source_provenance.py` diagnoses the two committed SHA gaps without
changing their existing dispositions. It independently joins the original
producer verification input/report, the unchanged producer capsule and the
104-child custody capsule. The only candidate discovery is SHA matching within
the selected supervision parent's explicit child declarations. Unlisted files,
other parents, Git history and working sources are never fallback inputs.

```sh
python -I -B qualification/codebase_ir/release_audit/producer_source_provenance.py build \
  --manifest /absolute/provenance-build-input/manifest.json \
  --output /absolute/private/fresh-provenance-build
python -I -B qualification/codebase_ir/release_audit/producer_source_provenance.py verify \
  --manifest /absolute/relocated-provenance-input.json \
  --output /absolute/private/fresh-provenance-restoration
```

The closed build schema is
`codebase-ir-producer-source-provenance-build-input@1`, with exact
`producer_source_input`, `producer_source_report`, `producer_capsule_manifest`
and `custody_capsule_manifest` descriptors and unique `selected_source_paths`.
The selected paths must be SHA discrepancies in the original supervision
receipt. A matching retained candidate must have an explicit same-parent
membership, exact prior retained-view pin and independently reconstructed
immutable commit/tree/blob identity. The original producer archive identity is
reconstructed deterministically from all unchanged producer capsule bodies and
joined to its independently pinned input/report. Only the path-dependent prior
stability population is normalized by requiring `unchanged=true`; committed
source decisions, hashes, sizes, scope, omissions and population stay exact.

The selected driver claim has declared SHA-256 `78e36aa2...`. Its same-parent
`driver-at-native-01.py.txt` child supplies exactly **37,053 bytes**, full SHA-256
`78e36aa29bc4bb18d878be58f62d41035ced9a597c6927b0a6deafd8275e1b22`,
and Git blob `19fc18207ee334b0bb53559eccf51563bdb405ff` at the released evidence
path in accelerate commit `8a37a3a81b99be4cc1f8df1143f308a3b7d1875e`.
That body is a separate inert historical view. The current committed original
benchmark path remains **different**, SHA prefix `b2a94ee2`, 50,696 bytes. The
preparation claim `47a39301...` has no matching body in the selected parent's
explicit child list and remains **historical-source-unavailable**. This is a
bounded selected-provenance result, without a claim about all repository history.
Both producer sizes remain undeclared; the historical child size never upgrades
them into declared producer size checks. The original source inventory still
has **eight verified memberships and two different memberships**.

The new capsule `provenance_capsule.json` has schema
`codebase-ir-producer-source-provenance-capsule@1`; its separate deterministic
stored ZIP is `producer_provenance.zip`. The closed verification input schema
is `codebase-ir-producer-source-provenance-input@1`, with exact `archive`,
`capsule_manifest_sha256`, `producer_capsule_manifest_sha256`,
`custody_capsule_manifest_sha256`, `producer_source_input_sha256` and
`producer_source_report_sha256` bindings. Verification emits
`producer_source_provenance.json`, schema
`codebase-ir-producer-source-provenance-verification@1`. It preserves every
selected committed and historical decision; shared historical views keep their
claim memberships while retained byte totals count each selected view once.

The workflow reuses unchanged ZIP, reader, seal and offline Git proof helpers.
It packages the unchanged producer capsule and extends its 31-object proof
store only with the one explicitly retained historical driver blob. All 32
objects must participate in selected proofs. There is no Git subprocess in
build or offline verification. File, directory, object and source limits are
320, 384, 160 and 32, with 4 MiB payloads, a 1 MiB capsule header and 64 MiB
aggregate capsule/archive bounds. Planned file/byte budgets are checked before
historical payload reads. Readers retain the inherited 120-second deadline and
2,400-query limit. Exact population/seals, original inputs, written ZIP/input,
copied bodies and referenced provenance/producer reports are checked through
final publication fences. These are sequential rereads, without atomic capture
or producer-authentication claims.

The selected input `producer-source-provenance-build-input-20261003-01/manifest.json`
has SHA-256 `2f7f7b86c760191d7ba7cb4f8eca95c643e0ab533cb76f515b1f953b8a89965e`.
The capsule has **70 files, 43 directories and 32 Git objects**, totaling
**1,690,105 bytes**. Its **1,711,905-byte** ZIP has SHA-256
`e0652ffcdcaf4f2f571055eb6cd5cc2fb584b371cf270aea17a85360ce6ae295`,
and inner header SHA-256
`7be65648b0dd0c4c5ca532b801127a133791c1fcdb91ef321cc8a8a35a7a35d6`.
The relocated input SHA-256 is
`39b11d747bd26307d54cb5d6b196315c9362d4a533e48255b27e941871d2bd90`.
A separate audit-hook guard executes only eight copied verifier modules with
empty PATH, refusing original workspace opens, owner/public source execution,
child processes and network. It preserves one recovered and one unavailable
historical source, both original committed discrepancies, and zero prohibited
operation attempts. The guard is an observed stdlib control, without an
adversarial operating-system isolation claim.

Twenty-two new controls cover relocation and deterministic archives, shared
historical memberships, missing history, original-source fallback refusal,
repaired outer pins on body/blob/report forgeries, repaired blob identities,
unused/missing objects, authority/path/output-scope refusal, preallocation and
late original/body/archive/report/permission drift. The full release suite has
**199 passing tests and zero skips**, with release Ruff passing. Historical
source substitution, original-path historical commit authentication, producer
execution authentication, source semantics, signatures, checkers, runtime and
production qualification remain false. Prior capsules, reports and source
profiles preserve their original bytes and scope.


## Released finite-proof and toolchain custody

`finite_proof_toolchain_custody.py` reconciles the three completed public
`behavioral-native-supervision` groups: `cold-observation`,
`successor-observation` and `finite-repair-behavioral-preview`. It reads only
explicitly selected retained bytes from the unchanged 104-child capsule,
independently reconstructing the released ledger, parent and child commit/tree/
blob paths. It performs no new Git subprocess or history/body discovery. An
inert `.olean` artifact is hashed as bytes and is never loaded or checked.

```sh
python -I -B qualification/codebase_ir/release_audit/finite_proof_toolchain_custody.py \
  --manifest /absolute/finite-proof-toolchain-input/manifest.json \
  --output /absolute/private/fresh-finite-proof-toolchain-audit
```

The closed input schema `codebase-ir-finite-proof-toolchain-custody-input@1`
contains `schema`, an exact `custody_capsule_manifest` path/SHA/size descriptor,
`evidence_id` equal to `behavioral-native-supervision`, and the exact three
ordered `selected_groups`. The independently pinned prior header remains
`5eb5d61d6c319bc906a92697d18ac0e7d3856c5339f79e897164df0c6babf7a8`.
The output `finite_proof_toolchain_custody.json` has schema
`codebase-ir-finite-proof-toolchain-custody@1`, independently binds the input and
prior header, and references a final reread `selected_custody.json` receipt.

Each group contributes twelve bodies: captured Python, inert driver, compiled
model, request, recorded trace, Python process, Lean text, `.olean`, certificate,
Lean process, tool policy and observation result. Raw artifact CIDv1/SHA-256,
size and role-path commitments are reconciled. Canonical recorded policy,
compiled model, contract, trace and result identities are rederived separately.
The certificate source CID joins the Lean text; request/result source identities
join captured Python bytes. Finite domain values and the domain CID reference
are cross-joined, but the domain CID preimage recipe is unavailable in this
selected public scope and `domain_cid_recipe_qualified` remains false.

The ledger preserves historical finite outcomes. Cold and successor records
satisfy the recorded offset clause; the group named finite repair does not. Its
recorded counterexample remains input -2, observed output -1, required output 0.
The corresponding `offset_counterexample` label stays separate from the two
`offset_clause` labels. Table consistency and source byte identity do not prove
Python observation origin, source applicability or a universal runtime theorem.

Recorded compiler/version commands, stdout identities, environment and positive
finite limit declarations are checked for structural consistency across separate
and embedded receipts. Executable SHA/size declarations remain unavailable
bytes in the selected parent's explicit children. The import `Init`, compiled
Lean dependencies, Python standard library, shared libraries and launcher runtime
retain explicit custody frontiers. No executable, ambient dependency, installation
or current host is probed. Resource limits remain recorded claims; neither
resource enforcement nor execution is authenticated. Tool declarations and
recorded versions retain each group membership.

The actual selection has **36 artifact memberships, 26 unique raw body hashes,
234,501 selected artifact bytes and 38 used Git proof objects** at accelerate
commit `8a37a3a81b99be4cc1f8df1143f308a3b7d1875e`. All used proof objects and
selected public copies are retained, with exact **81-file/18-directory** output
population before the main report is added. The selected custody receipt is
48,649 bytes, SHA-256
`c5f58dcbcf365a5758b7e255d9801295c343396fcec5df448c192268fc0a5d62`.
Input SHA-256 is
`5303a265baf20bbfa0b3f9bc3fd5d946cdd7e0b49fa948d2e287694d646db6fe`;
actual audit report SHA-256 is
`a818ce74292b706e28f948e9666e3ac2cb41fbcf1356943aa71996e2bfa4fde2`.

The independent relocated guard reassembles only selected copied evidence and
used proof objects under the unchanged pinned header. It runs seven copied
qualification tools with empty PATH, refusing original workspace/executable
opens, source payload execution, subprocesses and network. Zero prohibited
operations were attempted, with the same finite outcomes and dependency gaps.
Guard receipt SHA-256 is
`761ae5b8b30e3fd1cfcb73fcaae3afbfe1b24f762b7317e3fc11a5c3c26fdb5f`;
relocated report SHA-256 is
`538d3943bcec8f9a41dcec2f4820021c30b8b554f790b3e5cd143ad790bab668`.
This is an observed stdlib audit-hook control, without an adversarial OS isolation
claim. It qualifies selected evidence transport, not a complete old capsule or
a toolchain dependency closure. No new archive or old capsule is written.

Bounds are 256 KiB inputs, 1 MiB payloads, 192 read/copy files and directories,
96 selected proof objects and 16 MiB first capture/Git reads, with the inherited
120-second and 2,400-query ceilings. Original, copied and referenced receipt
bytes, selected old seals and exact new output population are checked through
final publication. Stability uses equal-size sequential rereads without an atomic
snapshot claim. Twenty-one new controls include coherent source/parent/ledger/
report repinning against immutable roots, repaired Git identities, typed process
limits, distinct source roles, recorded refutation preservation, indented imports,
relocation and late original/copy/receipt/population/seal drift. All **220 release
tests pass with zero skips**, and release Ruff passes. Source imports, native
checking, kernel replay, signatures, historical environment authentication,
transitive dependencies, proof reuse eligibility and production authority remain
unqualified. Earlier artifacts and implementation scopes remain unchanged.


## Released admission declaration and test-history custody

`admission_declaration_custody.py` reads the immutable child-capsule header and the
exact 21 explicitly declared bodies of `behavioral-repository-admission`. It
reconstructs the selected ledger, parent and children with 30 used offline Git
commit/tree/blob objects. It imports qualification transport helpers only; it
never imports producer sources, follows the adjacent daemon pointer, calls Git,
runs native checkers, or reads owner databases, keys or executable bodies.

The closed input schema is `codebase-ir-admission-declaration-custody-input@1`:
`schema`, `custody_capsule_manifest` with an absolute path, SHA-256 and integer
`size_bytes`, `evidence_id` equal to `behavioral-repository-admission`, and
`selected_profile` equal to `released-test-declarations@1`. Invoke it with the
original input location:

```sh
.venv/bin/python -I -B qualification/codebase_ir/release_audit/admission_declaration_custody.py \
  --manifest /absolute/path/to/manifest.json --output /absolute/fresh/output
```

The report `admission_declaration_custody.json` uses
`codebase-ir-admission-declaration-custody@1`, binds the original manifest and
`custody_capsule_manifest_sha256`, and separately pins `selected_custody.json`.
The fixed selected release retains 392,723 bytes across 21 artifact memberships,
three producer source declarations, nine recorded runs and ten final cases.
All eight earlier attempts remain adverse. The six re-signed controls explicitly
reuse a previously checked match: `fresh_checker_per_control=false`; they are
not six authenticated fresh checker executions.

The audit independently joins ordered qualification rows to bounded UTF-8,
entity-free pytest XML and terminal log outcomes. Seven earlier XML reports
contain one case outcome after collection of ten cases; the joined adverse
report has four outcomes after collection of 21. The final report has ten of
ten. Across the historical reports there are 21 case memberships and 80 collected
cases without retained XML outcomes. These are recorded pytest coverage gaps;
no native task omission or execution count is inferred. Log and XML clocks are
retained separately because their elapsed-time recipes differ.

No complete task, signed admission, signed behavioral handoff, proof snapshot,
retained native artifact bundle or intent-match body is declared by this parent.
The plan, baseline, critic and signature/public-key bodies are also undeclared.
The report retains these distinct missing-body/declaration frontiers. Quoted
traceback fragments and passing test names cannot supply complete envelopes,
signature custody or a missing CID recipe. Producer source SHA/size declarations
remain declarations within this subprofile; producer source bodies are not read.
The adjacent daemon pointer is retained as an outside-scope reference and is not
interpreted as successor/restart evidence for the selected admission parent.

True flags qualify the receiving custody, selected raw artifact bindings and
recorded qualification/control populations. Signature/envelope custody,
producer and owner authentication, checker/control replay, model-off execution,
training absence, task population, current eligibility, proof reuse, source
semantics, runtime closure and production acceptance stay false. Strict zero
runtime facts, omitted tasks and additional training epochs describe what this
receiving audit produces; they do not certify absence of historical work.

The new output retains only the original input, unchanged old header, selected
raw bodies/Git proof objects and a nested custody receipt. Its 58 retained
reference files and 15 directories are rechecked before and after bounded
original/copy rereads; the main report brings the output to 59 files. Fresh
output must lie outside input scopes. Final checks reject source or nested-receipt
drift, extra members, supplied-root aliases and changed old capsule seals. The
old 104-child capsule and the finite-proof groups are unchanged. A copied-tool
relocation guard verifies this selected scope with empty PATH and no original
workspace, Git, network, producer-source or native-tool access; its instrumentation
observations do not claim adversarial operating-system isolation.

The input ceiling is 256 KiB; individual payloads are bounded at 1 MiB, first
capture plus Git reads at 16 MiB, read and retained populations at 192, selected
Git objects at 96, and inherited operation/time ceilings remain 2,400/120 seconds.
XML additionally permits at most 32 cases, 256 nodes and depth eight. Stability
rereads are bounded equal-size sequential reads and do not claim an atomic
filesystem/database transaction.


## Recorded generation-12 dispatch attempt custody

`dispatch_attempt_custody.py` receives the closed `recorded-dispatch-attempts@1` dossier: the machine dispatch review, final attempt-cost ledger, and post-ledger cost supplement. Its input schema is `codebase-ir-dispatch-attempt-custody-input@1`; each of the three role descriptors has exactly `path`, `sha256`, and `size_bytes`. The module independently requires the selected public SHA-256 roots and joins the machine review's ledger/supplement commitments before following only the declared selected roles.

```sh
.venv/bin/python qualification/codebase_ir/release_audit/dispatch_attempt_custody.py \
  --manifest artifacts/codebase_ir_parallel_qualification/release_audit/dispatch-attempt-custody-input-20261003-01/manifest.json \
  --output /absolute/fresh/dispatch-attempt-custody-output
```

The selected population is 107 inert files totaling 11,370,451 bytes: three input documents and 104 explicit raw children. The receiver derives 11 host attempt outcomes from JSONL setup/call/teardown records and XML cases, nine Docker driver outcomes, two isolated stream attempts, 23 retained metadata audits, 21 preparation records, and the separate preentry/progress-observer failure metadata. It retains all ten adverse host attempts and five unqualified Docker attempts. The failed 37-case generation-11 run, failed 23-case generation-12 run, and separate passing one-case generation-13 retry stay separate. A recorded `passed` summary with no cases remains disqualified; the final three-case summary retains positive completion and two `in_progress`/`unknown-retained` child outcomes.

Ordered recorded driver sums are 10,966.148815490993 host seconds, 4,513.090357009984 Docker seconds, and 6.957427843000914 stream seconds. Stream internal test clocks and outer launcher clocks remain distinct. These overlapping historical clocks do not measure unique CPU time or total calendar time. Total wall time, complete process census, broad host training census, and post-ledger finalization times remain null when unrecorded. The generation manifest, large source capsules, native result/signature/database/key bodies, and other unselected ledger references remain explicit frontiers; no source generation or native publication is reconstructed.

The report `dispatch_attempt_custody.json` has schema `codebase-ir-dispatch-attempt-custody@1` and independent `machine_review_sha256`, `attempt_ledger_sha256`, and `postledger_supplement_sha256` bindings. `selected_custody.json` holds all role memberships and exact original/copy descriptors. The output contains 108 retained byte copies, that nested receipt, and the main report: 110 regular files and one retained directory. Canonical, nonsymlink regular-file reads are bounded before allocation: at most 192 reads per capture, 2 MiB per selected input, 32 MiB per original/copy capture, 120 seconds per capture, and 4 MiB for the main report. JSON duplicate/nonfinite values, untyped counts, malformed complete JSONL rows, repeated phase identities, XML entities, extra output entries, and late original/copy/nested/main changes are refused. All referenced bytes and the canonical output population are checked after writing the main report.

`status=passed` qualifies historical byte custody and recorded declaration consistency. Producer authentication, signature checks, current authorization, live lease eligibility, historical process origin, complete runtime closure, whole same-generation passing host suite, absence of external effects/training, native publication, proof authority, and production acceptance remain false. The receiver launches zero new native jobs and zero additional training epochs; those zeros describe this audit's own work.

The retained actual run is `release_audit/dispatch-attempt-custody-actual-20261003-01`. `dispatch-attempt-relocated-guard-20261003-02` copies one stdlib-only receiving tool and all 107 selected bodies, uses an exact logical-to-physical map with no fallback, and reproduces the full path-independent findings projection under empty `PATH`. Its audit hook blocks original/external reads, owner imports, subprocesses, and network access; the successful run records zero blocked operations. The earlier guard-01 launch diagnostic is preserved separately after an unpreloaded stdlib dependency was refused before the receiver ran. Twenty-one authored controls use fresh temporary inputs, including coherent outer repinning, UNKNOWN/empty-population/generation promotions, strict count aliases, output aliases/nonregular entries, final publication changes, and relocation without original input access.

## Current runtime15 cleanup and regression custody

`current_runtime_cleanup_custody.py` receives the current-runtime portion of the
source delta/runtime review through a closed, ordered selection of 35 raw files:

```sh
python3 -B qualification/codebase_ir/release_audit/current_runtime_cleanup_custody.py \
  --manifest <current-runtime-cleanup-input.json> --output <fresh custody directory>
```

The `codebase-ir-current-runtime-cleanup-custody-input@1` manifest selects the
`retained-current-runtime15-cleanup@1` profile. Every row has exactly `role`,
`path`, `sha256` and `size_bytes`. The independently pinned machine review binds
the prior review, runtime15 native/container results, explicit owner cleanup,
independent worker audit, source receipt, actual stdout and separate reader
controls. Those reviews bind six current successful, fourteen prior successful
and two failed JUnit receipts, plus the exact native lifecycle, before/after
execution scopes and authored verification. Header commitments are checked
before opening the remaining selected bodies. Optional explicit relocation
requires all 35 distinct mapped bodies and never falls back to original paths.

The receiver rejoins recorded START/STOP, original cleanup allocation, unchanged
execution-scope bytes, completed task population and worker stdout identities.
It recomputes 835 prior and 252 current successful case identities, with 175
overlapping and 77 new identities, producing 912 combined identities. Complete
parameterized names remain intact; an isolated prefix through `.test.api.` is
normalized to `api.`. The 278 current successful executions remain distinct from
deduplicated identities. Failed receipts retain 193 executions, 190 identities,
eight initial affected-suite failures and 105.036 seconds of failed receipt cost.
A repeated failed case is allowed only for its separate failure and cleanup-error
records. Successful duplicate identities refuse. Fifty-four stdlib reader cases
stay outside the pytest population. Nested native, outer, audit and test costs
remain separate rather than being added as elapsed time.

The source receipt's 19,381 metadata rows are checked for closed fields, canonical
owner-relative membership, uniqueness, per-repository counts, aggregate bytes and
four selected core declarations. Source bodies are never followed. The snapshot
receipt's original `qualification_pending=True` remains historical; metadata
reconciliation does not attest execution origin or a complete dependency closure.
Inherited scan pages and two setup epochs remain separate from this receiver's
zero native jobs, fitting attempts and source-body reads. Numerical summary
agreement does not reconstruct checkpoints or authorize learned successor reuse.

Input and copy caches each admit at most 48 files and 24 MiB, with 10 MiB per
file, a 256 KiB input manifest, 4 MiB main report and one 120-second operation
window. JSON keys/types/numbers/nesting, XML nodes/depth/case identities and source
metadata populations are bounded. Reads require canonical regular files through
`O_NOFOLLOW | O_NONBLOCK`. The output retains exact selected bytes and a local
`selected_custody.json`; original inputs, retained copies, local nested report,
main raw report and exact output population are rechecked after writing the main
report. Observations are sequential and do not claim an atomic filesystem seal.

The `codebase-ir-current-runtime-cleanup-custody@1` result establishes selected
historical receipt/test/cost consistency. Current cleanup, live eligibility,
signature authentication, process origin, source bodies, checkpoints, whole
runtime behavior, proof authority and production acceptance remain unqualified.
All no-Git, no-import, no-database/key, no-network and no-native-work flags describe
this receiver's own work. Separate validation may run legacy private synthetic
Git/probe fixtures under explicit qualification authorization.


## Retained successor planning custody

`successor_planning_custody.py` receives a fixed ordered selection of ten small
JSON bodies from the source-successor machine review and closed audit metadata.
It opens the declared machine review, audit, successful and failed native results,
authored request, warm/cold planning previews, warm/cold typed preimages and
resource-admission receipt. It follows no other artifact or owner path.

```sh
python3 -B qualification/codebase_ir/release_audit/successor_planning_custody.py \
  --manifest /absolute/path/to/input.json \
  --output /absolute/path/to/fresh-output
```

The input schema is `codebase-ir-successor-planning-custody-input@1`, selected
profile `retained-native-source-successor-planning@1`. The output schema is
`codebase-ir-successor-planning-custody@1`, workflow `successor_planning_custody`,
with main report `successor_planning_custody.json` and pinned local receipt
`selected_custody.json`. The manifest and all ten original bodies are retained.
Every original and copy is reread after publication, along with the exact local
receipt and main raw report; the output population is closed.

The receiver reconciles both authored runtime requirements and both tasks as
residual, with zero facts or omissions. It preserves all eight stages: six pass,
while admission and parallel planning fail with their recorded blockers. Three
variants each carry twenty typed preimages. Their sixty field digests use the
native field-specific domain and exported typed JSON bytes, preserving tuple,
list, record and enum tags without importing native classes. This establishes
material byte identity. `semantic_digest_replay_qualified` remains false.
Critic, obligation graph and execution-plan bodies are not selected, and their
body closure is explicitly unknown. Native artifact IDs remain declarations.

Both fresh pages concern the same first 32 ordered members of the declared
300-member successor: 22 inferred, nine deferred by budget and one unindexed.
This does not qualify complete successor scanning or 64 distinct members. The
cold preview and preimages are byte-identical to warm evidence; warm reconstructed
preimages were reused against the cold consumed binding. Native owner reopen is
a same-process declaration and does not qualify a process restart.

Successful and failed attempt durations and phase lists remain separate. The
failed reference deadline observation is retained. Four explicit benchmark
setup epochs across the two attempts are separate from two unit-fixture epochs;
receiving adds zero attempted training epochs. A zero source-property solver
count does not qualify the whole planner as solver-free. Scheduler lease/waiter
drain is reconciled as historical metadata, without current cleanup or kernel
resource-enforcement claims.

Per-file reads are capped at 1 MiB, with independent 8 MiB original and copy
caches of at most 32 files. Manifests are limited to 256 KiB and reports to 4 MiB;
JSON depth is at most 32 and its lexical and decoded populations at most 100,000
values, under a shared 120-second deadline. Reads require canonical regular
files with NOFOLLOW/NONBLOCK and stable descriptor/path identities. Duplicate
keys, nonfinite numbers and Boolean count aliases are refused. The receiver
uses only the standard library and performs no native execution, training,
owner source imports, owner database/key/checkpoint reads, Git or network work.


## Retained full-successor receiving custody

`successor_receiving_custody.py` receives ten explicitly selected JSON metadata
bodies. The selection joins the complete full-successor native result and its
independent closed audit, unsigned actual receiving generation 04, the shared
host configuration, detached transport and signed-reader controls, and the
separate failed signed-worker generations 02 and 03 with their final container
reports. Each original raw body is bounded and pinned before parsing, copied
into a fresh output, and reread after publication. Paths inside the selected
metadata never authorize another body read.

```sh
python3 -B qualification/codebase_ir/release_audit/successor_receiving_custody.py \
  --manifest /absolute/input.json --output /absolute/fresh-output
```

The input schema is `codebase-ir-successor-receiving-custody-input@1`, selected
profile `retained-full300-successor-receiving@1`. The main report schema is
`codebase-ir-successor-receiving-custody@1`, workflow
`successor_receiving_custody`, file `successor_receiving_custody.json`. Its
`custody.local_receipt` pins `selected_custody.json`; ten ordered
`selected_files` rows pin the original and retained raw copies. The closed
output contains exactly thirteen files and one `retained` directory. Typed
scope flags and integer zero fields appear both at the top level and in the
closed `scope` object.

The receiver rederives the declared archive metadata CIDs and complete row
counts. The staged declaration contains 1,631 regular members totaling
75,553,659 bytes, excluding `progress.json` and the model owner lock from the
1,633-member source archive. Those totals describe metadata; the receiver opens
none of the named source, database, checkpoint or deep archive bodies. The
1,593-member earlier archive remains another descriptive generation. Complete
source/member and page dispositions are qualified separately by the corpus lane.

Two complete path-relocation observations must differ only in their local
artifact-root fields. The relocation itself retains registry generation eight;
the recorded sole new native pair advances it to nine. Complete source tables,
registry rows, parent/child checkpoint declarations, source/model selections and
inherited ten default pages, one reference page and two setup epochs must agree.
Unsigned actual receiving records zero new page inference and fitting. It
qualifies neither signatures nor worker dispatch. Saved Adam step and checkpoint
hash declarations are compared without numerical or optimizer reconstruction.

Failed signed worker 02 preserves its whole structured-identity refusal after
three recorded completed phases. Failed worker 03 preserves all five phases,
including the task-manifest signing deadline refusal. Each separate 30-second
public close timeout remains a budget refusal without an integrity finding.
Neither attempt is upgraded by passed preflight or cleanup metadata. Their
recorded 12-CPU/8-GiB/512-PID cgroup observations agree with the held outer host
envelope, and the inner nine-CPU/6,553-MiB pool retains its distinct container PID
scope. A held reservation snapshot and a later release observation remain
separate. The receiver does not call Docker, reobserve current cleanup or assert
process origin. Independent failed-attempt audit/body closure stays unknown.

The 79 transport cases and 78 signed-reader cases are retained test declarations.
The latter includes synthetic full-300 records and public-signature controls;
no signature verification or native qualification runs in this receiver. The
selected failed native and driver durations are retained separately and are not
summed into unique CPU time, total calendar time or throughput.

Bounds are 2 MiB per selected body, separate 8 MiB original and copy caches,
32 files per cache, a 128 KiB manifest, a 4 MiB report, depth 32, 100,000 JSON
values and 120 seconds. Duplicate keys, nonfinite numbers, surrogate text,
Boolean count aliases, oversized inputs, symlinks, FIFOs, reordered selection,
coherently rehashed metadata mutations and late original/copy/report/population
changes refuse. The receiver uses only the standard library and performs zero
native execution, training, owner imports, database/key reads, Git or network
operations. Every production acceptance task remains open.


## Recorded default-registry operation deadline custody

`registry_operation_deadline_custody.py` receives 18 fixed historical JSON metadata bodies from `registry-operation-budget-qualification-20261003`. Its standalone stdlib receiver reconciles the production-created 30-second deadline across factory entry/return, Java setup, Apalache model check and version probe for each of two recorded cases. Each case retains its original complete request and serialized artifact, request and attempt digests, conservative generic `unknown` conclusion, bounded typed outcome and exact phase output. Advisory predispatch precedes the API deadline and remains a separate observation.

The closed phase population contains six launches and lifecycles, with six unique ordered unparented leases, recorded finite CPU/RSS/child profiles and JVM settings, cleaned workspaces, zero owned leases/waiters and next sequence seven. The false model case's expected exit 12 remains a completed bounded violation with `nonzero_exit`; neither case supplies native cancellation evidence. The 2,215 selected tests, 747 overlapping focused tests, 126 operation-control cases and 15 legacy native deselections are retained historical declarations. Counts are not added. The 1,618 prior artifacts, 19 prior qualifications and single production-source change are reconciled from selected declarations; named source, test, tool, preimage, diff and prior qualification bodies are not opened.

The custody result grants no current default-registry, signature, proof, model-truth or process-origin authority. Production tasks closed remain empty. Deadline cooperation does not establish hard callback preemption, hard aggregate containment, installation cancellation or propagation into other adapters and standalone availability probes. Structural and semantic counterexample replay remain outside this receiver's scope.

```sh
python -B qualification/codebase_ir/release_audit/registry_operation_deadline_custody.py   --manifest /absolute/path/to/input.json   --output /absolute/path/to/fresh/output
python -B -m unittest discover -s qualification/codebase_ir/release_audit   -p test_registry_operation_deadline_custody.py
```

The input schema is `codebase-ir-registry-operation-deadline-custody-input@1`, with profile `recorded-default-registry-deadlines@1` and exactly 18 ordered `{role,path,sha256,size_bytes}` selections. Public raw pins are fixed independently of caller-provided descriptors. `audit(manifest, output, relocated_sources=None)` permits only a complete explicit relocation of the manifest and all selected bodies. Paths must be canonical regular files without symlinks or shared selected inodes. Each original/copy cache is capped at 32 files, 1 MiB per selected file and 8 MiB aggregate; the manifest is capped at 128 KiB, each receipt at 4 MiB, JSON at depth 32 and 100,000 values, and the receiver at 120 seconds. Duplicate keys, nonfinite values, bool counts, special files, aliased paths, changed pins and unexpected output members refuse.

Output has exactly 21 files: 19 retained raw inputs, a closed `selected_custody.json` and `registry_operation_deadline_custody.json`. Two repeated closing passes reopen every selected original and copy and both receipts after output-population observations, checking captured bytes and physical identities. This is bounded filesystem custody, not an atomic filesystem snapshot. The 102 standalone controls include deadline, resource, population, authority and overlap mutations with repaired outer commitments, plus original/copy/receipt drift, inode replacement, added entries and aliases during closing passes. No production owner imports or new native execution are needed.


## Recorded ambient inheritance into admitted native execution

`native_operation_inheritance_custody.py` receives 27 fixed metadata bodies from the completed ambient-native-inheritance qualification. It reconciles six admitted request, invocation, launch, live-process and lifecycle populations. The earlier production-created deadline crosses factory and native entry; effective wall and existing CPU ceilings agree with the remaining budget, including OS rounding. Original address-space, RSS, output, storage and child limits remain distinct. The recorded cancellation signal is inherited without explicit runner forwarding.

Four Lean/Rocq positive and negative kernel cases finish normally. Their original complete requests, attempts, typed outcomes, generic `unknown` or `error` conclusions and raw native flags remain separate from two owned Python transport controls. The timeout control keeps logical `timed_out`, native timeout plus cancellation flags and cleanup after the deadline; the cancellation control retains a signal requested after its child was observed alive. Neither transport control qualifies native kernel cancellation. Logical interruption accounting and native cleanup duration are retained separately.

The metadata declares six unique ordered leases, one CPU and child per launch, cleaned workspaces, zero owned leases/waiters and next sequence seven. It preserves all five test attempts and both native-command attempts, including the initial nine test failures and source-import refusal. The 2,314 selected cases contain the earlier 2,215 cases and exactly 58 new inheritance plus 41 additional existing cases; the overlapping 818 focused cases are not added. Production, clock-fixture and benchmark corrections, 1,708 prior artifacts and 20 prior qualifications remain selected declarations. Source, diff, assertion, executable, library, JUnit and prior artifact bodies are not followed.

```sh
python -B qualification/codebase_ir/release_audit/native_operation_inheritance_custody.py --manifest /absolute/path/to/input.json --output /absolute/path/to/fresh/output
python -B -m unittest discover -s qualification/codebase_ir/release_audit -p test_native_operation_inheritance_custody.py
```

The input schema is `codebase-ir-native-operation-inheritance-custody-input@1`, profile `recorded-admitted-ambient-inheritance@1`, with exactly 27 ordered `{role,path,sha256,size_bytes}` selections and independent fixed raw pins. `audit(manifest, output, *, relocated_sources=None)` accepts only a complete explicit relocation of the manifest and all selected bodies. Each original/copy cache is bounded to 32 files, 1 MiB per selected file and 8 MiB aggregate; the manifest is capped at 128 KiB, each receipt at 4 MiB, JSON at depth 32 and 100,000 values, and the receiver at 120 seconds.

Output contains exactly 30 files: 28 retained raw inputs, `selected_custody.json` and `native_operation_inheritance_custody.json`. Repeated physical closing passes reopen originals, copies, manifest and receipts after output-population observations. Duplicate keys, nonfinite values, Boolean counts, symlinks, FIFOs, shared selected inodes, unexpected entries and observed late byte or inode changes refuse. The 122 standalone controls include coherent deadline, CPU, resource, PID, stop, attempt, authority and count mutations plus late population and body changes. The receiver performs no native execution, owner imports, database/key reads, Git or network access. Current runner behavior, process origin, live cleanup, solver cancellation, hard preemption, aggregate containment and model or theorem truth remain unqualified; production tasks closed remain empty. This bounded custody does not provide an atomic filesystem snapshot.
