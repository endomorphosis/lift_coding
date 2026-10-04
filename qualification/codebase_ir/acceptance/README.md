# CodebaseIR adversarial acceptance controls

This lane prepares the roadmap's next integration run using independent files.
It includes 17 deterministic source/prompt controls, exact raw-byte selectors,
separate captured training truth and authored desired requirements, and 13
mutation specifications for genuine owner evidence. Core implementations,
shared registries, roadmap checkboxes, signed admission and worker dispatch are
outside this lane's writes.

The baseline inventory has five source units. `calc.py::increment` implements
`n + 1`; `decoy.py::increment` implements `n + 2` with the same function name.
`helpers.py` and `consumer.py` establish related imports/dependencies. The
consumer calls both the selected implementation and helper. `effectful.py`
prints and stays in inventory as unsupported source. The baseline's two stable
clause IDs request an exact integer result and `n + 2` over `[-2,-1,0,1,2]`.
Fresh finite checking establishes the integer clause and leaves the offset
clause residual. The successor changes only the captured body to `n + 2`;
the original prompt and both clause meanings remain unchanged and both finite
clauses become true.

The fixture `review_ref` is an authored control identifier. It is not a
production review, signed evidence, or source-behavior proof. The baseline's
training truth remains the captured `n + 1` body; desired `n + 2` comes from a
separate requirement ledger. Reference arithmetic rows are authored oracle
expectations. The generator does not execute source or manufacture native facts.

Run from the repository root, using a fresh output path each time:

```bash
python3 -m unittest discover -s qualification/codebase_ir/acceptance -p 'test_*.py' -v
.venv/bin/ruff check qualification/codebase_ir/acceptance
python3 qualification/codebase_ir/acceptance/codebase_ir_acceptance.py \
  --output /tmp/codebase-ir-acceptance-fixtures
```

The generator writes `manifest.json`, exact scenario source files, original
prompt bytes, and `corpus_audit_input.json`. Manifest paths are relative to its
output directory; its SHA-256 and all selectors are deterministic across runs.
The corpus cohort deliberately crosses train/tune/canary/final boundaries with
a formatting clone, related revisions and a consumer/helper dependency group.
Lane 2 should report leakage for this fixture. Dependency-completeness flags
describe this authored local import graph, not a production dynamic closure.
No native registry records or inherited training state are claimed.

The current finite interface admits one complete ASCII/LF module containing one
integer-offset function, and exactly two canonical finite sentences. Therefore:

| Control | Required current disposition |
| --- | --- |
| Baseline, changed literal, changed desired offset/domain, formatting | Supported finite checking, with exact applicable facts/refutations/residuals |
| Successor and explicitly requested decoy | Both clauses satisfy the declared finite domain after fresh observation |
| Guard/polarity changes, Unicode and CRLF source | Unsupported selected source; both original clauses remain residual |
| Unbounded, prohibition, ambiguous, changed requirement guard, additional effects clause | Canonical parser refusal; complete original ledger retained externally for general residual planning |

Unicode/CRLF fixtures preserve source bytes and UTF-8 byte offsets. Normalizing
their bytes would change the selected source and cannot repair unsupported
coverage. An unbounded/prohibition parser refusal does not itself demonstrate a
production planner fallback; that integration remains a retained acceptance gate.

Optional native contract checks call the existing requirement parser and source
compiler without executing the source:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets \
  .venv/bin/python qualification/codebase_ir/acceptance/codebase_ir_native_contracts.py \
  --output /tmp/codebase-ir-native-contracts
```

Optional actual owner checks use private Git/DuckDB/CAS/scheduler state, reserve
bounded capacity, and execute only the selected closed arithmetic function in
isolated Python followed by Lean checks of its recorded finite table:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets \
  .venv/bin/python qualification/codebase_ir/acceptance/codebase_ir_native_contracts.py \
  --output /tmp/codebase-ir-native-owner \
  --observe \
  --lean /home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean
```

The owner run checks all five captured units, exact selected/decoy source identity,
one baseline finite fact and one residual, five resealed forged observation
refusals, a real same-Git-HEAD edit refusing the old source generation, successor
recapture, fresh observation after owner reopen, historical parent readback, and
zero remaining leases/waiters. It retains failed runs, tool identities, run times,
private state paths, and SHA-256 before/after for the actual imported native
implementation files. Missing dependencies return exit 3 with an `unavailable`
report. Assertion failures return nonzero and retain their incomplete report.
Source changes observed across a run prevent a `passed` report.

`validate_native_result` compares genuine matcher results against the fixture's
structural oracle. It verifies clause/predicate/root identity, selected byte
digest, domain, exact integer row types, complete observation rows and applicable
counterexamples. It does not authenticate arbitrary caller JSON or grant any
admission authority. The actual owner run obtains its records by calling the
native matcher and uses the native observation validator to reject resealed
corruptions. Checkpoint, policy, signed admission, worker effects and task commit
mutation specifications remain for the independently owned integration crossing.

The retained successful owner run is under
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-native-owner-final/`.
Its report asserts bounded finite observations only; it does not establish
universal CPython equivalence, signed admission, worker launch, production
qualification, or general instruction understanding.

## Real planning and held-capacity crossing

`codebase_ir_planning_qualification.py` continues through the existing public
`preview_finite_integer_plan` and `preview_capacity_bound_finite_integer_plan`
APIs. It uses the same five-unit source and original two-clause prompt, complete
reviewed update declarations, private authority records, and model-off planning.
The comparison verifies every declared graph task, exact typed goal and producer
nodes, clause/predicate binding, full finite match in critic evidence, operation
closures and exact selected effects. Held schedules must retain the candidate's
task IDs, source root, effect leaves and producers through assignments, waves and
merge order. Receipt stages form one closed, unique eight-stage population;
their serialization order is not an execution-order assertion. All relevant
nested authority flags remain false. The graph retains two declared tasks even when only the offset repair
is selected. A newly captured `n + 2` successor retains both declarations and has
an explicit empty selected plan. This is proposal population accounting; no
signed task population or zero-work publication is claimed.

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets \
  .venv/bin/python -B qualification/codebase_ir/acceptance/codebase_ir_planning_qualification.py \
  --output /tmp/codebase-ir-planning-check \
  --lean /home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean
```

For an immutable release-lane snapshot, repeat `--snapshot-root` for its two
canonical package import roots and supply `--snapshot-sha256` with its canonical
generation identity. The release lane's pure verifier checks that identity,
exact file/directory set, source bytes, bounds and read-only seal before imports
and after the trial; the adapter also pins the verifier's source bytes. Wrong
identity prevents native entry and later drift prevents a passed qualification.
A namespace finder refuses every missing core
module and every core import outside those roots. Snapshot execution and live
working source execution are recorded as different profiles; the adapter never
falls back from an incomplete snapshot to the working tree. Before/after native
source hashes come from the selected import roots. Loaded interpreter site
package files and Python/Lean tool identities are recorded separately; late
external imports stay explicit and transitive runtime closure is not claimed.

An optional external-file manifest prechecks the dependency files observed by a
previous successful run without importing or executing their contents:

```bash
.venv/bin/python -B qualification/codebase_ir/acceptance/codebase_ir_external_pins.py \
  --from-report artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-live-final-01/planning_qualification.json \
  --output /tmp/codebase-ir-external-manifest.json
```

Pass that fresh file as `--external-manifest` to the planning qualification. The
schema is `codebase-ir-external-dependency-manifest@1`, with exact fields
`schema`, `site_packages_roots`, `source_report_sha256` and `files`. Each file row
has `path`, `size_bytes` and `sha256`. Permitted roots come from the running
interpreter's site-package paths under its prefix; a manifest cannot authorize
foreign roots. Reads refuse noncanonical paths, symlinks, nonregular files,
wrong types, duplicate keys, nonfinite JSON values and digest/size drift. Bounds
are 1,024 files, 64 MiB per file, 128 MiB total, 1 MiB manifest and 4 MiB source
report. Actual later loads retain these before pins; additional unlisted files
remain explicit late dependencies. File stability is assessed from bytes rather
than changes in loaded module names. This observed file set does not establish
whole interpreter, native-library, asset or transitive runtime closure.

Real retained baseline results are in
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-development-02/`.
The plain preview passed scan, query, evidence, obligation, candidate and critique,
and refused parallel planning with `parallel:stale_capacity`. Held native
capacity allowed parallel schedule feasibility. Both receipts remain
`review_only`, with admission blocked by `ir_admission_materials_absent`.
The operational arithmetic model was kernel checked and refuted the requested
offset for the captured `n + 1` body. It supplies no CPython behavior authority.

The complete-run development-03 attempt was refused by actual host
`proof_memory_stall` backoff before source capture. Its retained scheduler state
records zero acquisitions and zero live leases/waiters. Failure evidence remains
available; resource safety is not disabled to obtain a passing run.

The implementation has concrete refusal controls for scope/selector drift,
same-name catalog retargeting, changed native clause identity, incomplete task
population, policy-root changes, actual source-byte changes, actual finite
`.olean` corruption, and old generations after a same-Git-HEAD edit. Negative
controls accept only declared native exception classes. Partial stage outputs
and the report are retained on failure. The profile bounds each crossing to 60
seconds, complete qualification to 180 seconds, native owner memory to 1024 MiB,
and the private scheduler to two CPU/process slots under real host proof safety.

`planning_regression_reference.json` contains comparator projections of genuine
historical baseline returns with original artifact hashes. Its authority is
`assertion_reference_only`; it is used by stdlib regression tests and cannot
authenticate observations, authorize workers, or become current evidence.
Signed behavioral admission, native worker edit/publication, and signed successor
admission remain explicitly unsupported by this finite review-only profile.

The final complete service run is
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-live-final-01/planning_qualification.json`.
It passed in 40.86 seconds using the explicit `working_tree_observed` profile.
All 212 actual imported native implementation files had matching before/after
hashes. The baseline selected one offset-repair task and retained both declared
tasks, with one finite fact. Held capacity passed parallel planning. The freshly
captured successor had two finite facts, a proved arithmetic model and an empty
selected plan. All three real receipts kept admission blocked by
`ir_admission_materials_absent`. Eight declared mutation controls produced the
expected native refusal classes, including genuine policy/source/finite-artifact
drift and the stale same-HEAD generation. The run finished with zero active
leases/waiters and preserved the complete two-task declaration population.

The separate pinned trial is retained at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-pinned-final-01/planning_qualification.json`.
It recorded `unavailable` when actual function invocation requested
`ipfs_accelerate_py.agent_supervisor.planning.finite_integer_plan_service`, absent
from the 195-file eager-import snapshot. All 194 core files actually imported
before that refusal were inside the snapshot and had stable bytes; zero leases
or waiters remained. The live final run was a separately declared execution
profile, not a fallback inside the pinned process.

The successful final report retains 741 observed external dependency files as
late/after-only pins and reports external dependency stability false and closure
unproven. That original artifact has the verified `zero_leases_and_waiters`
result; it predates the adapter's additional final-resource-state and external
before-pin fields, which were not added to the original report. It does
not qualify the entire `.venv`, asset/native-library closure, the pinned
snapshot's function invocation dependencies, signed behavioral evidence admission,
worker publication, or signed successor admission. Source/hash stability is an
observed before/after check, not an atomic filesystem-capture claim.

The final comparator was replayed without native execution against all three
original complete final JSON results. The separate receipt is
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-offline-validation-01/replay_results.json`.
It pins each original result by SHA-256, records scenario and capacity profile,
and pins the unchanged comparator source files. All three genuine projections
passed; ten deliberately corrupted copies were refused. These are structural
assertion outcomes, not renewed observation eligibility or authentication.
The owned stdlib suite passes 59 tests, including graph, selector, admission,
held-schedule, snapshot-identity and external-file corruption controls;
repository-config Ruff is clean.

The later single invocation-snapshot trial passed at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-planning-invocation-pinned-01/planning_qualification.json`,
with reported elapsed time 30.62 seconds. Its release generation is
`a13efe5bee569d9505df4cb67015645ceec4a678fee0ee39f8d47d04da51d3cf`.
All 213 sealed files (12,660,616 bytes), exact roots and the generation identity
verified before and after; all 212 actually imported core files had unchanged
bytes. The 741 actually loaded external files (100,103,207 bytes) retained their
before pins and matched afterward, with no late files. The explicit final
resource state reports zero leases and waiters. This closes the missing local
invocation frontier for this exercised route and dependency profile. It does
not establish whole runtime closure or qualification of other invocation paths.

The three genuine planning outcomes and all eight native mutation refusal
classes matched the earlier live run. Baseline plain planning still refused
held-capacity feasibility; held baseline planning selected the one offset task;
successor planning retained both declarations, established both finite facts and
requested no task execution. All three receipts remain review-only and retain
the current finite profile's `ir_admission_materials_absent` blocker. No worker
or production admission occurred. Other repository owners may implement separate
admission profiles; this lane qualifies only the APIs and evidence recorded here.

The exact snapshot-only invocation used no working repository import path:

```bash
.venv/bin/python -B qualification/codebase_ir/acceptance/codebase_ir_planning_qualification.py \
  --output /tmp/codebase-ir-planning-invocation-repeat \
  --lean /home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean \
  --snapshot-root /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/invocation-observed-20261002-02/snapshots/generation-000/accelerate \
  --snapshot-root /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/invocation-observed-20261002-02/snapshots/generation-000/datasets \
  --snapshot-sha256 a13efe5bee569d9505df4cb67015645ceec4a678fee0ee39f8d47d04da51d3cf \
  --external-manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261002-external-prepin-01/external_manifest.json
```

The previous live run, memory-pressure refusal, incomplete 195-file pinned
attempt and offline structural replay remain separate unchanged artifacts.

A later read-only review tightened strict loaded-file enumeration to use its
streamed hashes directly, with count and aggregate-byte checks, avoiding a second
unbounded legacy read. The original native trial was preserved and was not
repeated. The tightened path replayed all 741 retained module origins against
the existing before manifest and original native after pins, with unbounded
`Path.read_bytes` disabled during enumeration. All hashes matched, without
importing those external modules. This separate observed-file comparison is at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261002-external-posttrial-validation-02/validation.json`.
The final replay also omits one real file from an authored subset of the before
inventory: an initial-import observation remains after-only, late and unqualified
for stability. Manifest mode never promotes such observations into before pins;
default observed mode keeps its existing baseline semantics. This separate
comparison does not renew native owner evidence or establish runtime closure.

## Retained finite admission evidence

`codebase_ir_admission_evidence.py` correlates an existing owner's complete
finite admission fixture without importing owner code or opening its database:

```sh
python3 -B qualification/codebase_ir/acceptance/codebase_ir_admission_evidence.py \
  --fixture-root artifacts/codebase_ir_terminal_bench/finite-admission-qualification-20261002-04 \
  --output <fresh admission audit directory>
```

`admission_evidence.json` binds the raw result, complete native-plan admission
reference, original type and offset tasks, prerequisite, validation executables,
outputs, clauses, finite facts and retained observation/model artifacts. It
reconstructs workflow content identities and selected query/predicate meanings.
Twenty-nine authored corruption controls rehash unsigned parent references to test
task reduction, validation drift, fact relabeling, missing authority fields and
false no-work grants, including correlated source relabeling and incomplete
cold/incremental comparison. The baseline, successor and cold admissions each
require exactly the six selected producer modules and nine model frontend
modules, with lowercase SHA256 values. Empty, partial, extra and malformed pin
inventories are refused by both structural validation and the historical
precheck. Rehashed copies never authenticate signatures.
`admission_regression_reference.json` is public recorded assertion data used by
unit tests; its paths are not read during those tests and it grants no authority.

The fixture exercises manifest version 1. Versions 2 and 3 remain independently
unqualified; version 4's rejection is a producer profile assertion. Historical
task statuses come from retained producer records, not a reopened task store.
The original task population remains complete even when a manual successor's
finite observations select no work. This does not qualify the worker successor
loop or establish a new admission or launch grant.

Optional `--historical-replay --replay-python .venv/bin/python --workspace
/home/barberb/lift_coding` invokes only the public historical verifier in a
separate bounded process. It denies writes, subprocesses and network access,
tracks exact file reads including directory-relative owner reads, and records
source and owner-file hashes without retaining private key bytes. Its ceilings
are 45 seconds wall time, 30 CPU seconds, 2 GiB address space, 1 MiB child output,
512 core Python files/16 MiB, and 2,048 read files/256 MiB. These Python guards
are not an OS security boundary. Each selected core Python source is observed before
execution and checked afterward; original whole producer closure replay is
never claimed. A requested replay that is refused or unavailable returns 3.

The first retained read-only replay was refused because its guard did not
support the owner's directory-relative reads. The corrected directory-read
profile reached the public verifier but was refused at the operational model
certificate's exact binding check. It loaded 213 core files and observed the
current `logic/backends/process.py` hash differing from the retained model
frontend pin. All 696 observed file reads and 13 directory identities were
stable during that second run; no task store, native proof or worker was opened.
Both runs remain retained under `20261002-admission-history-readonly-01` and
`20261002-admission-history-directory-readonly-01` in this lane's artifact tree.
Fresh historical verification remains unqualified. The default structural
audit's passing result is separate from this refusal.

Sealed historical mode repeats `--snapshot-root` for the two canonical package
roots and requires `--snapshot-sha256`. It verifies the release generation's
exact file population, hashes and read-only seal before and after the child,
and requires the six signed producer pins and nine operational model frontend
pins to match the retained evidence before calling the historical verifier.
Owner profile and artifact read scopes remain the original owner's existing
paths; snapshot mode is not a portable archive replay. It refuses missing core
imports and never adds a working repository import path.

The single retained sealed trial is
[`20261002-admission-history-sealed-01/historical_replay.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-admission-history-sealed-01/historical_replay.json).
The 220-file, 13,680,425-byte generation
`949a715ab5abc0335d1ca3bfe45a5e7265eab888949174ed475fc3682275f5db`
verified unchanged before and after. All six producer pins and nine frontend
pins matched, including the retained backend source. The child loaded 216 core
files and observed 704 file reads and 13 directory identities with stable pins,
but stopped at the conditional import
`ipfs_accelerate_py.agent_supervisor.planning.ir_learning_campaign_planner`.
Its status is `unavailable`; no historical verification result or native
mutation control was completed. The run took 2.66 seconds, denied no operation,
and used no task store, proof, worker or training call. The accompanying
structural audit passed all 21 authored corruption controls and preserved both
original task identities. Source pin agreement does not resolve the missing
invocation dependency or qualify historical signature verification.

The sealed trial used the following command once, without a fallback or retry:

```sh
.venv/bin/python -B qualification/codebase_ir/acceptance/codebase_ir_admission_evidence.py \
  --fixture-root /home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/finite-admission-qualification-20261002-04 \
  --output <fresh admission audit directory> \
  --historical-replay --replay-python /home/barberb/lift_coding/.venv/bin/python \
  --workspace /home/barberb/lift_coding \
  --snapshot-root /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/admission-retained-snapshot-20261002-02/snapshots/generation-000/accelerate \
  --snapshot-root /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/release_audit/admission-retained-snapshot-20261002-02/snapshots/generation-000/datasets \
  --snapshot-sha256 949a715ab5abc0335d1ca3bfe45a5e7265eab888949174ed475fc3682275f5db
```

The source-pin increment's stdlib suite passed 88 tests, including source and predicate
relabeling, closed comparison fields, sealed import refusal and exact replay
argument propagation, and exact pin populations across all three admissions.
Repository Ruff passes. The later read-only structural result at
[`20261002-admission-structural-pin-population-01/admission_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-admission-structural-pin-population-01/admission_evidence.json)
passed all 29 controls; historical replay was not requested. The original
sealed trial's 21-control audit and unavailable native receipt remain unchanged.
These checks do not execute owner code or verify retained signatures.

## Retained native worker lifecycle and publication

`codebase_ir_worker_evidence.py` audits the existing fixture-13 public evidence
without importing owner code or executing a worker:

```sh
python3 -B qualification/codebase_ir/acceptance/codebase_ir_worker_evidence.py \
  --fixture-root artifacts/codebase_ir_terminal_bench/finite-worker-qualification-20261002-13/native \
  --output <fresh retained worker audit directory>
```

The auditor preserves the original `FINITE-TYPE` and `FINITE-OFFSET` tasks and
their immutable content identities. It joins the genuine prerequisite claim,
validation and completion, residual attempt and fence, candidate preimage and
postimage, START/STOP records, retained process identities, UID cleanup, and
explicit owner worktree cleanup. It checks the complete successor/cold
nine-field comparison and the fresh historical completed rows against the
retained artifact population. Exact signed producer populations and the ten
selected worker source copies must agree where their modules overlap.

The schema is `codebase-ir-retained-worker-audit@1`. The result distinguishes
`historical_native_worker_observed: true`, a retained producer observation,
from `worker_execution_during_audit: false`. The former does not authenticate
process origin or attest UID isolation. The audit reads no profile key or task
database, invokes no owner proof, Git process or network operation, and claims
no signature authentication, current launch permission or training step.
Private-state reads are limited to the residual attempt's two public JSON
binding/queue records; database files and credentials are refused.

Reads are capped at 256 files, 32 MiB total and 4 MiB per file before allocation.
Only selected retained paths are allowed, with no symlink or special-file
fallback. Relocated artifact descriptors preserve both the original and
retained path, raw SHA256 and byte count. The parent artifact population is
closed for this specific fixture cohort; this is not a general worker-format
conformance claim.

`codebase_ir_worker_git.py` independently verifies retained SHA1 loose commit,
tree and blob bytes without invoking Git. It checks the baseline, two-parent
merge, implementation parent, complete seven-file inventories and exact
candidate bytes, including unchanged modes. Only `calc.py` may change. Packed
objects or missing loose objects are unavailable rather than silently trusted.
Decompression is capped at 2 MiB per object, with at most 128 unique objects,
128 tree visits, 256 expanded entries and depth eight. These bounds also refuse
repeated empty-tree DAGs whose small stored object population could otherwise
cause excessive traversal.

The passing result is
[`20261002-worker-retained-02/worker_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-worker-retained-02/worker_evidence.json).
It binds input result SHA256
`014c1aa78f337a7ccd49e09223399cccc47cdd7124f596c88b2982aa1834f15e`,
checks 159 retained public files totaling 5,340,867 bytes unchanged, verifies
13 Git objects, and refuses all 28 authored correlated corruption controls.
The producer's 83.397-second native worker run is a retained observation; this
audit did not repeat it. The first audit remains retained at
`20261002-worker-retained-01`: its control caught an unsigned publication-parent
mutation that was not yet joined to the physically verified Git facts. The
corrected auditor explicitly binds the final publication fields to those facts.

`worker_regression_reference.json` contains public assertion data and grants no
authority. Tests cover genuine record joins, correlated task/process/source/CID
mutations, canonical task aliases, bounded path reads, decompression failures,
Git mode drift and tree traversal budgets. The worker increment's lane suite passed 111 stdlib
tests and repository Ruff.

The complete held-capacity preview was not serialized, so its
`fresh_evidence_cid` is not independently rederived. Worktree cleanup was an
explicit owner fixture action, not automatic completion or crash recovery.
Selected source copies and stable retained records do not establish complete
executed dependency closure, current owner state, portable admission or worker
isolation. The separately retained 222-file sealed historical replay reached
another missing conditional import, `proof.code_property_catalog`, and remains
unavailable; this structural audit does not change that outcome.

## Advisory stages and complete selected attempt accounting

`codebase_ir_advisory_evidence.py` is a separate stdlib workflow over explicitly
pinned public advisory records. It checks retained completed stages and failed
attempt distinctions without importing native owners, numerical runtimes or the
other owner's archive auditor:

```sh
python3 -B qualification/codebase_ir/acceptance/codebase_ir_advisory_evidence.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261002-advisory-retained-input-01/advisory_input.json \
  --output <fresh advisory audit directory>
```

The closed input schema is `codebase-ir-advisory-audit-input@1`, with exactly
`schema` and `attempts`. All six ordered attempt IDs, `01` through `06`, are
required. Each attempt has exactly `id`, `root` and `files`; `root` is a canonical
absolute directory. Each selected file has exactly `role`, `path`, `sha256` and
`bytes`, using a canonical relative selector, lowercase SHA256 and an exact
integer byte count. `role_paths()` declares the selected public roles for each
cohort profile. Missing, duplicated, extra, aliased or foreign selectors are
refused. There is no latest-run search, directory scan or missing-file fallback.
The manifest itself is bounded and hashed before selected files are read.

The workflow checks the two original native task meanings, signed model-off
evidence references, thirteen independently reconstructed advisory comparison
fields, the exact trusted replacement and proposal-to-worker bridge, native
START/STOP and completion/fence records, explicit owner cleanup and all nine
successor/cold finite fields. A retained worker checkpoint can remain
`incomplete` while its worker stage is completed and its overall attempt later
fails; those scopes are reported separately. Published commits are joined to
the original/successor signed source baselines and JSON publication receipts.
This workflow performs no Git object verification.

Returned epochs are checked against retained checkpoint reports, context
identities, ordered child ancestry, frozen feature/optimizer basis, fixed
evaluation splits and selected measurement records. Best selected optimizer
epochs remain distinct from attempted epochs. An unreturned fitting call has
an explicit unknown disposition, never an inferred zero from its configuration.
All three frozen previews must select the separately retained training
context's state, feature space, contract, record, checkpoint, parent, source head
and optimizer steps, with frozen mode and zero fitting. Both model-off previews
must carry no selected state or epochs. The completed result's model IDs,
measurements, continuations and repeated advisory/bridge stages must match
their separately retained records.
The known `n + 2` source was in the original training cohort; these retained
measurements do not establish held-out repair prediction or convergence.

The passing report is
[`20261002-advisory-retained-02/advisory_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-advisory-retained-02/advisory_evidence.json),
SHA256 `eca824d5a4614939bf4f3ba85e0c776c7d195a3ef13fd5855e64c8f0185f742d`.
It binds the selected manifest SHA256
`ab2b419c58c712c32ec4ebe1900dd60c5d04361ec3196dae99191c9958bbe66e`
and the completed attempt-06 result
`bedba288e6c0df9f3cc89e1549bbe9b928f00f37416bafb07346c4b579ecb54f`.
All 198 reads, including the manifest, totaling 47,071,248 bytes remained
unchanged. The six separate attempts returned 176 epochs: 128 in failed
attempts and 48 in the completed attempt, with zero unknown fitting calls.
Their selected native timers sum to 1,109.120 seconds; wrapper timers separately
sum to 1,190.706 seconds. These are not full invocation costs.
The earlier 14-control report remains unchanged at
[`20261002-advisory-retained-01/advisory_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-advisory-retained-01/advisory_evidence.json),
SHA256 `8feb33e7019d72a82439062141ba94d515bb3b6d110b44d9d972f5d1090c3cb9`.
Report 02 adds independent completed-model and frozen/off-context joins and
refuses all 56 authored controls. A separate read-only reviewer accepted the
genuine history and refused all 14 focused repinning probes in
[`advisory-peer-review-20261002-03/peer_fixed_review.json`](../../../artifacts/codebase_ir_parallel_qualification/corpus_audit/advisory-peer-review-20261002-03/peer_fixed_review.json).

Attempt 02 retains two leases and one waiter in its archived fresh-replay ledger
after a timeout; container removal is not described as draining those rows.
Attempt 05's child returned zero and retained a completed numerical/historical
response after 22 diagnostic stdout lines, while the parent still failed JSON
parsing. Attempt 04 retains its host pressure refusal and wait, without a native
timer. Every failure remains part of accounting. Call intervals must be disjoint
before their sum is reported; overlapping inclusive owner lifetimes, host waits
already inside wrapper time, and later total checkpoints are kept separate.
Source-copy, deployment setup, image inspection and scheduler setup costs remain
unmeasured rather than being silently excluded from a claimed complete latency.

The report schema is `codebase-ir-advisory-retained-audit@1`. `status: passed`
means the selected structural joins and accounting checks passed. It retains
`full_join_qualified`, `native_execution_performed`, `training_executed`,
`current_authority_claimed`, `signature_authentication_performed`,
`owner_database_opened`, `profile_keys_read` and
`git_object_verification_performed` as false. The other owner's complete
archive/signature/tamper qualification is separate; this report neither repeats
nor substitutes for it.

Reads are capped at 256 files, 64 MiB total, 4 MiB per selected file and 256 KiB
for the manifest, with regular-file/no-symlink checks and bounds before
allocation. JSON rejects duplicate keys, nonfinite values and excessive
depth/nodes. Recorded time values are exact nonboolean numbers bounded at
3,600 seconds each, preventing overflowing aggregate reports. Output preflight
refuses existing paths, input-root descendants and canonical-path bypasses
before creating a directory or emitting any report.

Fifty-six authored controls run against inert copies, including correlated
bridge/task revisions, epochs and lifecycle/fence mutations, all three frozen
model selections, both off modes, completed model IDs and duplicated training
measurements. Several regenerate outer content IDs, raw SHA256 descriptors and
selected input pins; they still refuse at independent task, checkpoint,
selected-model or signed model-off meaning joins.
No signature is issued or authenticated by these controls.
`advisory_stage_reference.json` is public assertion data, not admission evidence.
Frozen checkpoint, record and lineage descriptors must exactly match the
independently byte-pinned training artifacts. Frozen-only invocation, inference
and metrics descriptors receive bounded structural checks; their separate bodies
are not selected or verified (`frozen_auxiliary_artifact_bodies_verified: false`).
Twenty-six tests cover these joins, protocol/failure accounting, unknown epochs,
cost overlap/overflow and bounded read/output safety. The full lane passes 137
stdlib tests and repository Ruff. No native worker, training, inference, proof,
database, private key or network operation was performed by this increment.

## Selected frozen auxiliary bodies

`codebase_ir_frozen_auxiliary.py` separately closes the body-selection gap
reported by advisory report 02. It does not modify that report, its original
manifest or the earlier public assertion reference:

```sh
python3 -B qualification/codebase_ir/acceptance/codebase_ir_frozen_auxiliary.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261002-frozen-auxiliary-input-01/frozen_auxiliary_input.json \
  --output <fresh frozen auxiliary audit directory>
```

The closed input schema is `codebase-ir-frozen-auxiliary-input@1`, with exactly
`schema`, `prior_advisory_manifest`, `prior_advisory_report` and `attempts`.
The two prior descriptors have absolute canonical `path`, lowercase `sha256`
and exact integer `bytes`. All three ordered staged attempts, `02`, `05` and
`06`, are required. Each has exactly `id`, absolute canonical `root` and `files`.
Each file has `role`, fixed relative `path`, lowercase `sha256` and exact
integer `bytes`. `role_paths()` closes the twelve selected bodies per attempt:
context, invocation, inference and metrics for root, initial child and successor
child frozen models. The spec can be copied unchanged because external root
and prior-file mappings are absolute. There is no path discovery or fallback.

The supplement checks 27 auxiliary bodies and nine frozen context bodies.
Every raw hash, byte count and native blob/context CID must agree with its
selected preview descriptor. Independently selected training context,
checkpoint, record, lineage and inference/metrics files are read only through
the original manifest's exact pins, cross-checked against report 02's selected
inventory, and revalidated as three retained training phases per attempt.
Selected source heads, model and parent IDs, state/feature/contract hashes and
optimizer steps remain bound across the frozen context and retained training
records. Frozen invocation bodies request no new parent training version;
their null requested parent is distinct from the selected model's actual parent
in its context and lineage.

The passing selected-body report is
[`20261002-frozen-auxiliary-retained-01/frozen_auxiliary_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261002-frozen-auxiliary-retained-01/frozen_auxiliary_evidence.json),
SHA256 `1cd1db1dc30189a5278bd41ade669a1839a26e45cb7a5a814990af33a396b22e`.
It binds supplemental manifest SHA256
`229445a29c53ebfeabcacd34502687601c2bef399511ad56c81daffe0a06d887`,
preserves the earlier advisory report SHA256
`eca824d5a4614939bf4f3ba85e0c776c7d195a3ef13fd5855e64c8f0185f742d`,
and checks 123 selected files totaling 30,268,787 bytes unchanged. All 42
authored correlated controls refuse. This standalone audit performed no new
fitting or native execution.
An independent read-only review also accepted all nine selections, refused all
42 controls, rechecked the same selected files and passed all sixteen focused
tests. Its receipt is retained at
[`frozen-auxiliary-peer-review-20261002-02/peer_review.json`](../../../artifacts/codebase_ir_parallel_qualification/corpus_audit/frozen-auxiliary-peer-review-20261002-02/peer_review.json).

Frozen inference payloads must match the independently retained selected
inference, including their four source rows. Metrics must match the prior
training metrics and selected checkpoint report. Their sixteen reported epochs
are copied training observations; this audit adds zero attempted epochs and
requires zero frozen fitting. Different retained worker receipts are checked
against their closed profile and bounded exact types. The selected files do
not contain complete worker protocol input/output envelopes, so their protocol
digests and actual process provenance are not independently rederived.

The report schema is `codebase-ir-frozen-auxiliary-retained-audit@1`, emitted as
`frozen_auxiliary_evidence.json`. A passing selected-body report sets
`frozen_auxiliary_artifact_bodies_verified` to true only for this supplement's
explicit body population. `numerical_state_replayed`, `worker_receipt_authenticated`,
`worker_protocol_output_digest_rederived`, `native_execution_performed`,
`training_executed`, `current_authority_claimed`, `full_join_qualified`,
`signature_authentication_performed`, `owner_database_opened` and
`profile_keys_read` remain false. Retained payload equality does not establish
independent numerical correctness, full archive/runtime closure or any current
grant.

Forty-two authored corruption controls cover all three attempt-06 frozen
selections. They regenerate changed auxiliary raw pins, native blob/context
CIDs and unsigned preview-context references, then refuse changed source/model,
lineage, mode, metrics, inference rows, optimizer or authority against unchanged
independent training records. `frozen_auxiliary_reference.json` contains only
public inert assertion data and grants no authority. Sixteen focused tests
cover genuine joins, those correlated controls, requested versus selected
parent semantics, safe outputs and bounded/stable reads. The lane passes 153
stdlib tests and repository Ruff.

Reads retain the advisory workflow's 256-file, 64-MiB total, 4-MiB per-file and
256-KiB manifest caps; supplemental body declarations are additionally limited
to 2 MiB. Existing, noncanonical, symlinked or input-root output paths are
refused before creation. All selected files are reread for stability before
passing publication. No native owner, upstream archive auditor, numerical
runtime, proof checker, task database, private key or network is used.

## Exact retained worker response digests

`codebase_ir_worker_protocol.py` reconstructs the worker's exact canonical
response envelope from each of the nine selected frozen inference bodies.
The reviewed 5,967-byte worker source is retained as inert input with SHA256
`91174cb51a0832e4cd691e56f94c0d6b34af1f06e6afec2c0d780d58fa3196db`.
Its inference response has exactly `schema`, `inference`, `training_executed`
and `proof_authority`; canonical ASCII JSON is emitted without a newline.
The supplement compares the reconstructed bytes against each independently
pinned inference receipt's `output_sha256`, after repeating the original
training/context/body joins and checking the prior frozen report's complete
selected-input inventory. The inert source is never imported or executed.

```bash
python3 -B qualification/codebase_ir/acceptance/codebase_ir_worker_protocol.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261003-worker-protocol-input-01/worker_protocol_input.json \
  --output <fresh worker protocol audit directory>
```

The closed input schema is `codebase-ir-worker-protocol-input@1`, with exactly
`schema`, `prior_frozen_manifest`, `prior_frozen_report` and
`protocol_worker_source`. Each descriptor contains canonical absolute `path`,
raw `sha256` and exact integer `bytes`. Unreviewed worker contracts, descriptor
aliases and input-root output locations are refused. Reads reuse the 256-file,
64-MiB total, 4-MiB file and 256-KiB manifest caps; each reconstructed envelope
is bounded to 64 KiB. All captured inputs and written envelopes are reread
before a passing report is published.

The actual retained report is
[`20261003-worker-protocol-retained-01/worker_protocol_evidence.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261003-worker-protocol-retained-01/worker_protocol_evidence.json),
SHA256 `3d368aca0f57de1003410011177cd6b57f1e50d75df0dde4c6d3be49b7790b40`.
It rederives nine distinct response digests from 62,304 reconstructed bytes,
pins 126 unchanged input files totaling 30,339,232 bytes, and refuses thirty
authored response/receipt corruptions. Correlated numerical controls rebind
unsigned body pins and context IDs and alter both copied inference payloads;
their unchanged receipt digest still refuses them. Fifteen focused stdlib
tests cover these controls, exact stdout encoding, closed typed fields,
source identity, safe outputs and bounded/stable reads.

The report schema is `codebase-ir-worker-protocol-retained-audit@1`, emitted as
`worker_protocol_evidence.json`. It sets
`worker_protocol_output_digest_rederived` and
`frozen_auxiliary_artifact_bodies_verified` to true for these selected bodies.
The earlier advisory and auxiliary reports remain unchanged. Newly written
envelopes are explicitly reconstructed artifacts; separately retained original
stdout is absent from the selected input population, so
`original_worker_output_envelopes_retained` remains false.

All nine stdin digests remain unrederived retained identifiers. Exact request
bytes, including the dynamically sampled `max_seconds`, are not selected;
no request digest, seed or timer claim is inferred from the output. Thus
`worker_protocol_input_digest_rederived`, `worker_receipt_authenticated` and
`numerical_state_replayed` remain false. Process origin, interpreter execution,
independent numerical correctness, runtime closure and current authority remain
unqualified. No worker runs or training epochs are added.

## Independent inventory/query receiving controls

`inventory_query_controls/receiver.py` adds a separate receiving fixture for
RPI-007/013/023/029/032. Its inventory, evidence ledger, query pages and
dispositions are **independently authored assertion data**, not retained native
scan/query execution or a production codec. No complete native inventory/evidence
join export is selected; native export adoption remains explicitly unavailable.
This work prepares receiving controls without changing native catalog, scanner,
query, planner, admission or worker implementations.

```bash
.venv/bin/python -B qualification/codebase_ir/acceptance/inventory_query_controls/receiver.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261003-inventory-query-input-02/inventory_query_input.json \
  --output <fresh inventory query controls directory>
```

The closed input schema is `codebase-ir-inventory-query-controls-input@1`, with
exactly `schema`, `fixture_origin`, `fixture` and `sources`. `fixture_origin` is
`independently_authored_receiver_controls`. The fixture descriptor has absolute
canonical `path`, raw `sha256` and exact integer `bytes`. Each ordered source
descriptor adds `unit_id` to those fields. Absolute descriptors allow an unchanged
manifest copy to be consumed by the combined runner. Output must be fresh and
outside the original fixture scope; copied-manifest siblings are allowed.

`inventory_query_controls/fixtures/receiver_fixture.json` contains seven complete
inventory members and six exact source bodies. Three inferred rows have two
ordered shards. Deferred inference, unsupported source, parser failure and an
opaque unavailable body remain explicit inventory dispositions. Source bodies
use `.source` filenames as inert fixture data and are never imported, parsed or
executed. Authored source/inventory/ledger SHA256 identities are separate from
production CIDs, proof keys and authoritative current heads.

Six independent evidence records include contradictory records for one source,
an independently indexed deferred source, a base conditional refutation with an
empty requested domain, and an unknown conditional record. The receiving audit
derives exact page populations and summaries from the independently selected
ledger and source bodies. It keeps conditional verdicts, premise status and
requested-domain applicability separate. Multiple records remain separate;
an ambiguous pair is not collapsed to a preferred verdict.

The six required query cases cover complete three-page retrieval, one retained
page before budget exhaustion, an insufficient first-page budget, complete empty
membership, a wrong-contract empty selector and evidence for a deferred inference
member. Partial retrieval yields `matched_partial` or `unknown_budget`; it never
establishes absence. An unretained first page charges zero retained bytes and
provides no continuation. Retained cursors bind source/inventory/ledger identities,
evidence epoch, exact selector and next offset. Every case preserves both original
clause texts, residual dispositions and declared tasks with zero runtime facts,
zero task omissions and no execution authority.

The actual report is
[`20261003-inventory-query-retained-02/inventory_query_controls.json`](../../../artifacts/codebase_ir_parallel_qualification/acceptance/20261003-inventory-query-retained-02/inventory_query_controls.json),
SHA256 `8c7d0c8c2c6f879ffc3ad8418cd8f712a2788d11bc6d722ac12e80c6b162ff3b`.
It binds input manifest SHA256
`20f663f13f024a4a12dd681f4556c01abc2d62c628d192fe5d1907b0b9ecf450`
and fixture SHA256
`c03a045ca109aca0c0ce7fef2ff2fa4c1f995dbf36e355193764d7d423d6afcd`.
All eight selected inputs totaling 24,655 bytes remained unchanged and matched
their retained copies. Five pages were retained across six query cases. Thirty-eight
rehashed corruptions refused, including correlated status/summary/byte changes
against the independent ledger, missing/duplicate/out-of-order pages, altered
cursor roots/offsets, hidden ambiguity, invented absence and authority/task changes.
The first development input/report remains retained separately and unchanged.

The report schema is `codebase-ir-inventory-query-controls-report@1`, emitted as
`inventory_query_controls.json`. A passed report means authored receiving
conformance only. `authored_receiver_conformance` and `input_files_unchanged` are
true. Native export adoption, native execution, numerical replay, training,
signature authentication, current authority and production acceptance remain
false; runtime facts, omitted tasks and additional training epochs are exact
integer zero. Rehashing every independent anchor does not authenticate a producer
or establish source/property/numerical truth. Production query formats, complete
proof keys, durable recovery and native admission require separate owner evidence.

Bounds precede allocation: 66 selected files, 8 MiB total, 256 KiB manifest,
1 MiB fixture, 64 KiB source, 64 units, 128 evidence records and bounded pages.
Actual descriptor reads are capped by the remaining aggregate budget and declared
pin size; stability reads use the originally captured byte length. Strict JSON
rejects duplicate keys, noninteger numbers, excess structure and numeric authority
aliases. Inputs and retained copies are reread before passing publication.
Twenty-five focused tests verify independently stated golden outcomes, rehashed
corruptions, allocation growth, typed fields, FIFO/symlink refusal, output scope
and original/copy drift. No native query, owner database, private key, solver,
source execution, inference, training, worker or network operation is used.

## Selected native inventory query receiving conformance

`inventory_query_controls/native_receiver.py` receives the completed native
`inventory-evidence-join-qualification-20261003-04` public export through a fixed
selected input closure. This extends the independent six-case authored receiver
above; its scripts, fixture bodies, and previous reports are unchanged.

The selected closure contains the 263,983-byte primary read-only audit, the
producer generation-input descriptor, five joins, three joined previews and the
independent authored baseline preview, five verification/applicability pairs,
and six producer files retained as inert `.source` bytes. The primary audit's raw
SHA256 is fixed in the receiver. Every selected native body must match its
historical public path and raw digest in that audit; producer copies must also
match the generation-input descriptor. The 7 MiB result, state databases, model
state, source CAS bodies, keys, solver programs and executable workers are outside
this closure.

```sh
.venv/bin/python qualification/codebase_ir/acceptance/inventory_query_controls/native_receiver.py \
  --manifest /absolute/path/native_inventory_query_input.json \
  --output /absolute/path/fresh-native-receiving-output
```

The closed input schema is `codebase-ir-native-inventory-query-input@1`: `schema`,
`prior_primary_audit`, `generation_inputs`, `native_files`, `protocol_sources`.
The audit descriptor has `path`, `sha256`, `bytes`; other descriptors also retain
`original_path`, and the two lists add `name`. All body paths are absolute, pinned,
regular files. Historical original paths are provenance locators and are never
opened by this receiver. The manifest can be copied to a runner directory while
its body descriptors still point to the selected immutable input directory.
A run is limited to 64 files, 16 MiB total, 2 MiB per body, and 256 KiB for the
manifest. Strict UTF-8 JSON rejects duplicate keys, surrogates, nonfinite numbers,
excessive nesting/population, and integers outside the signed 64-bit magnitude
bound. Reads reserve the remaining aggregate budget before allocation. Output
must be fresh and outside both retained and historical selected input scopes;
original selected bodies and their output copies are reread before success.

`native_inventory_query.json`, schema
`codebase-ir-native-inventory-query-receiving-report@1`, binds the raw manifest
and `prior_primary_audit_sha256`, retains raw original/copy descriptors, and
records exact per-profile member ledgers and query bindings. It reconciles native
raw/dag-json CIDs, ordered 28-member membership, shard/source ordering, page and
cursor chains, typed authority ceilings, selectors, canonical proof keys, and
summary source/contract/domain identities against separate original proof and
applicability bodies. Complete, partial, zero-byte, deferred-inference, and exact
key profiles remain distinct. Ambiguous records are both retained; an empty
domain establishes neither a conditional property nor runtime facts.

Three advisory previews must retain the baseline's six independently authored
semantic material digests, all four declared tasks and unresolved runtime
requirements, and zero current facts or omitted tasks. The report includes 36
correlated controls that recompute unsigned container CIDs while preserving the
independent original bodies. `test_codebase_ir_native_inventory_query.py` adds
28 focused receiving regressions with independently stated golden native CIDs,
coverage, ambiguity, domain/verdict, and residual task expectations. These tests
require the retained selected export fixture at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-inventory-query-input-01`;
they read only those inert bodies and execute no owner package.

The actual selected receiving report is retained in
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-inventory-query-retained-01`.
Only structural `native_export_receiving_conformance` is true. The raw audit
anchor is not signature authentication or an execution attestation; numerical
state, source semantics, checker runs, live eligibility, current authority and
production native adoption remain unqualified. Inference shard digests and
closing-fence CIDs remain recorded metadata; their unselected bodies and live
owners are not reconstructed. The baseline material digests do not independently
reconstruct their underlying planning objects. An adversary replacing every
independent unsigned anchor could construct a consistent export that this
receiving profile cannot authenticate.


## Selected native batch query and original requirement custody

`inventory_query_controls/native_batch_receiver.py` receives the selected public
8-unit closure from `codebase-query-many-qualification-20261003`. The five input
bodies are the immutable qualification summary, native result, independent cold
restart request, cold response stdout, and source snapshot. Their total is
2,247,483 bytes; the selected manifest is also pinned and retained. No native
32-unit result, owner database, source CAS object, process event ledger, worker,
solver, or owner module is opened. All previous receiving fixtures and reports
remain unchanged.

```sh
.venv/bin/python qualification/codebase_ir/acceptance/inventory_query_controls/native_batch_receiver.py \
  --manifest /absolute/path/native_batch_query_input.json \
  --output /absolute/path/fresh-batch-receiving-output
```

The closed input schema is `codebase-ir-native-batch-query-input@1`: `schema`,
`prior_qualification`, `native_result`, `restart_request`, `restart_response`,
`source_snapshot`. Each descriptor contains absolute `path`, `sha256`, `bytes`;
the four selected native descriptors also contain `original_path`. The
qualification summary's raw SHA256 is fixed independently in the receiver, and
its public artifact commitments bind the other four bodies and historical role
paths. Those paths remain provenance labels. A copied manifest may refer to the
original private input bodies while output is written to a fresh sibling of the
copied manifest. Output is prohibited inside selected input scopes. The receiver
caps reads at six files, 8 MiB total, 2 MiB per body, and 256 KiB for the manifest,
with remaining-budget allocation bounds and stable original/copy rereads. Strict
JSON rejects duplicate keys, nonfinite numbers, surrogates, excessive structure,
and integers beyond the signed 64-bit magnitude bound.

`native_batch_query.json`, schema
`codebase-ir-native-batch-query-receiving-report@1`, exposes independent
`prior_qualification_sha256`, `native_result_sha256`, `restart_request_sha256`,
`restart_response_sha256`, `source_snapshot_sha256`, and `manifest_sha256`
bindings. Six ordered 1/8/32-selector observations retain all 82 batch pages and
82 individual pages, including repeated receipts and complete tuple order.
The independent cold request and stdout retain 32 pages and a three-entry partial
resume with its continuation. Source head, inventory, epoch, selector, cursor,
entry, and container identities are reconciled without issuing a query.

The four original requirements retain eight normative clauses, their complete
IntentIR statement/source-reference ledgers, exact original text, character
spans, derived UTF-8 byte spans and source-slice hashes. All eight runtime
residuals remain unresolved. The supported mathematical lookups preserve the
recorded proved, refuted and vacuous dispositions; the unsupported fourth
requirement remains unknown. These dispositions grant no current behavioral
fact or task omission. Twenty-six rehashed corruption controls keep independent
request and original individual-clause anchors fixed while altering order,
request membership, pages, source/epoch identity, clauses, spans, residuals,
unknowns, typed authority and whole-operation integrity.

`test_codebase_ir_native_batch_query.py` adds 22 focused tests, including an
authored Unicode span control and copied-implementation discovery. Actual tests
use the inert selected fixture at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-batch-query-input-01`;
they import no owner package. The actual receiving report is retained at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-batch-query-retained-01`.

Structural `native_batch_receiving_conformance`,
`original_requirement_custody_reconciled`, and
`restart_request_response_bindings_reconciled` are true. The export does not
retain typed per-call request tuple bodies or their original page-size and
budget ceilings, so request execution custody and batch resource execution
remain unqualified. Original text/reference reconciliation does not verify human
review custody, interpretation, source semantics or runtime behavior. Timings and
resource counters are retained separately as historical producer claims;
throughput improvement, native execution, signatures, numerical/source/checker
replay, live eligibility, current authority and production adoption remain false.
Runtime facts, omitted tasks and additional attempted training epochs are exact
integer zero. Replacing every unsigned independent anchor could produce a
consistent export that this profile cannot authenticate.


## Selected SMT@2 request, evidence and phase custody

`smt_v2_controls/receiver.py` receives the completed historical SMT@2 operation
qualification through eleven explicitly selected public bodies (3,093,253 bytes)
and a pinned private manifest. The native result contains 36 baseline cases,
two parent-owned cases, six typed interruption controls and 446 recorded native
launch/lifecycle phases. The closure also contains the original benchmark command,
three audit bodies, twelve separate deterministic injected wire fixtures before
and after the runtime change, their comparison, and two inert runtime sources.
The retained owner qualification remains `passed_partial_scope`; this receiving
profile closes no production acceptance task.

```sh
.venv/bin/python qualification/codebase_ir/acceptance/smt_v2_controls/receiver.py \
  --manifest /absolute/path/smt_v2_custody_input.json \
  --output /absolute/path/fresh-smt-custody-output
```

The closed input schema is `codebase-ir-smt-v2-custody-input@1`. Its fields are
`schema`, `prior_qualification`, `native_result`, `native_command`, `launch_audit`,
`lifecycle_audit`, `control_audit`, `wire_before`, `wire_after`, `wire_comparison`,
`runtime_before`, and `runtime_after`. Descriptors have absolute `path`, `sha256`,
`bytes`; all except the qualification add `original_path` provenance labels.
The fixed private qualification hash is
`c80c5cbec17b29401fc55022d63bdd7c94cc38cdf295d51dd995a9d27eef560a`.
A second independent fixed raw anchor binds the native result. Every other
selected body must match the qualification's public role/digest commitments.
A prior observed qualification revision is recorded separately in the acquisition
receipt; it is not reconstructed or silently treated as the selected anchor.

Acquisition retained private copies and twice reread all originals and copies.
Subsequent receiving opens only those private selected bodies and its output
copies. Historical executable, working-directory, source and owner paths are
labels. Their bytes, database, keys, tools, live leases and scheduler are never
opened. The receiver caps twelve files, 8 MiB total, 1 MiB per body, 256 KiB for
the manifest, 512 phase records and 64 cases. Descriptor reads reserve the
remaining aggregate budget before allocation. Strict JSON rejects duplicate
keys, nonfinite numbers, surrogates, excess structure and out-of-bound integers.
Fresh output must be outside private and historical input scopes; a copied
manifest can produce a fresh sibling without weakening body-scope protection.

`smt_v2_custody.json`, schema `codebase-ir-smt-v2-custody-report@1`, independently
binds all eleven `<role>_sha256` values and `manifest_sha256`. It reconciles full
request/obligation/evidence identity digests, declared request bounds, artifact
model/core hashes, replay identities, differential peer roles and dispositions,
per-case launch/lifecycle populations, command/limit correspondence and recorded
output budgets. All 396 baseline, 30 nested and 20 interruption phases remain.
Stopped calls retain no returned result or late replay. All twelve original
injected wire cases retain their independent outer request and complete before/
after encodings; static AST comparisons confirm six unchanged wire-record
classes without importing the archived runtime sources.

Thirty-seven coherent corruption controls keep independent qualification,
original fixture, wire and audit anchors fixed while recomputing mutable
request/evidence/audit commitments. Thirty-one focused tests add independent
golden hashes/counts, typed-return-code and authority controls, acquisition-anchor
repin refusal, private-only reads, symlink/output safeguards and original/copy
drift. They use only the selected inert fixture at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-smt-v2-custody-input-01`
and also run from a fresh implementation snapshot. The selected actual report is
retained in `artifacts/codebase_ir_parallel_qualification/acceptance/20261003-smt-v2-custody-retained-01`.

Structural custody, original wire compatibility, unchanged wire definitions and
private input stability are true. The native complete caller request survives
only inside its result, while the separate original fixture binds its obligation,
provider and mode. Phase stdin bodies are absent, and launch/lifecycle records
lack a shared unique phase ID; case-local order and command joins provide no
unique invocation attestation. A focused control deliberately shows that an
arbitrary coherently rehashed stdin digest remains structurally consistent and
unauthenticated. Recorded API `theorem_established` is also true on native
`disproved/sat` cases; the report preserves this claim category alongside its
separate disposition, verdict and `is_proved` field. It grants no theorem fact.

Solver verdict authentication, proof certificates, actual request/stdin custody,
resource enforcement, native/source/checker execution, signatures, current
eligibility and authority, behavioral admission and production acceptance stay
false. Runtime facts, omitted tasks and additional training epochs are exact
integer zero. Timings and resource observations remain separate historical
producer claims. No earlier fixture, module or checkpoint is rewritten.


## Selected JVM identity-probe custody

`jvm_probe_controls/receiver.py` receives one completed historical JVM support-probe
qualification from eleven frozen public bodies (618,004 bytes). Its native result
records thirty probes across five routes, two repeats and widths 1/2/4, two probes
under one actual parent reservation, two pre-cancel controls with no launch, and
two live cancellations. All 34 recorded launch and lifecycle phases survive.
The owner qualification remains `passed_partial_scope`; support usability and
constructor availability establish no model check, proof or execution grant.

```sh
.venv/bin/python qualification/codebase_ir/acceptance/jvm_probe_controls/receiver.py \
  --manifest /absolute/path/jvm_probe_custody_input.json \
  --output /absolute/path/fresh-jvm-probe-custody-output
```

The closed input schema is `codebase-ir-jvm-probe-custody-input@1`: `schema`,
`prior_qualification`, `native_result`, `native_command`, `launch_audit`,
`lifecycle_audit`, `control_audit`, `wire_before`, `wire_after`, `wire_comparison`,
`runtime_before`, and `runtime_after`. Descriptors contain absolute `path`,
`sha256`, exact integer `bytes`, and (except the qualification) historical
`original_path` labels. The private manifest is retained under
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-jvm-probe-custody-input-01`.
Acquisition froze the independently pinned qualification and native result,
matched all ten declared body commitments, and twice reread originals and copies.
Receiving subsequently reads only the private closure and its copies. Original
owner, executable, working-directory and source paths remain provenance labels.

The fixed qualification hash is
`8c274ef09bf40f173955bd8005c26de8a610a85a773b541a709006e324489838`, and the
independent native-result hash is
`ddeb99132e4108f541f61c2dc1127463d19ca27f3f288b21719f11539e8d5837`.
Twelve files including the manifest, 4 MiB aggregate, 512 KiB per body,
256 KiB manifest, 64 phases and 40 cases bound the receiver. Reads reserve the
remaining aggregate and declared byte budgets before allocation; strict JSON
rejects duplicate keys, nonfinite numbers, surrogates and excess structure.
Fresh output must be outside frozen and historical input scopes. Both copied
manifests with sibling output and copied implementation snapshots are supported.

`jvm_probe_custody.json`, schema `codebase-ir-jvm-probe-custody-report@1`, binds
`manifest_sha256` and all eleven independent `<role>_sha256` values. It reconciles
complete ordered route membership, native banner/major/output digests, recorded
JVM and prlimit commands, finite declared budgets, case/thread/lease environment
joins, unique selected lease labels, root accounting and the two child probes
under one captured parent. Children are not added again to root allocations.
Local cancellation returns unusable identity, while the shorter ambient scope
retains its typed `ProofOperationCancelled` and no result. The separate original
non-native wire fixture and inert before/after ASTs preserve the seven-field
`JavaRuntimeProbe` definition without importing archived sources.

Thirty-seven coherent controls rehash mutable audit references while preserving
independent qualification, original wire, runtime source and native-result
anchors. Thirty-two focused tests add independent golden counts/hashes and
support/stop outcomes, exact Boolean/integer types, command and parent capacity
controls, private-only reads, copied-manifest output, read allocation bounds,
original/copy late drift, and fixed-anchor repin refusal. A well-formed altered
launcher digest deliberately remains consistent without authenticating its
unavailable body. All prior modules, fixtures and checkpoints remain unchanged.

Structural custody, recorded phase bindings, wire fixture compatibility, unchanged
wire definitions and private input stability are true. Raw original caller/stdin
and full environment custody, unique execution attestation, binary/launcher
identity, resource enforcement, throughput gains, native expiry/backoff coverage,
constructor parent propagation to later proof work, model checking, source/runtime
semantics, proofs, current authority and production acceptance remain false.
Recorded empty input, environment sanitization, cleanup and lease observations
are historical producer claims. Selected launcher and delegated JVM bytes are
absent. The native run records no real-time expiry or induced pressure episode.
The sampled largest reaped-child RSS is retained separately from aggregate peak
memory and hard containment. Runtime facts, omitted tasks and additional training
epochs are exact integer zero. No Java, checker, owner database, key or native
resource operation runs during receiving.


## Authored requirement matching over retained finite tables

`finite_match_controls/receiver.py` adds a closed independent receiving profile
for the phase 3 valid/refuted/uncovered/unsupported distinction. It matches
explicitly authored requirement domains and properties to the three previously
frozen finite-proof custody groups, without importing or executing captured
Python, Lean, native tools, owner packages, a checker or Git. It performs no
production catalog, planner or admission operation.

```sh
.venv/bin/python -I -B qualification/codebase_ir/acceptance/finite_match_controls/receiver.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261003-finite-match-input-01/finite_match_input.json \
  --output <fresh finite matching directory>
```

The exact `codebase-ir-finite-match-controls-input@1` fields are `schema`,
`fixture_origin`, `requirements`, `prior_manifest`, `prior_report`,
`prior_selected_custody` and `groups`. Each descriptor contains an absolute
canonical `path`, `sha256` and exact integer `size_bytes`; artifact descriptors
also carry `role`. Three ordered groups declare eight ordered roles each:
captured source, compiled model, request, finite trace, Lean text, inert olean,
certificate and observation result. The original manifest must be supplied:
its containing directory and each declared input directory are protected from
output writes. Prior original input, custody report and selected receipt are
independently fixed at `5303a265…`, `a818ce74…` and `c5f58dcb…`; coherently
rehashed internal evidence cannot replace those immutable receiving anchors.

The requirements body has exact fields `schema`, `requirements` and `tasks`.
Each complete requirement carries its original ID/text, group/source/compiled
identity, retained assumptions, typed property and strictly sorted unique exact
integer requested domain. Supported property profiles are the recorded bound
integer-offset clause and the recorded exact integer-output clause. A different
offset remains unsupported by that certificate profile. Universal source
semantics and missing checker timeout custody remain unsupported; source runtime
requirements stay deferred. No missing timeout receipt is reconstructed.

The disposition and domain applicability are independent. Complete requested
finite rows can produce `recorded_supported`; an actual captured counterexample
produces `recorded_refuted`, including when other requested values remain
uncovered. Outside-domain values remain in `uncovered_inputs`. An empty domain
is unknown and cannot create vacuous support. Every selected record retains its
source/compiled/contract/trace/certificate identities, finite-domain reference
and all three original assumptions. The domain CID recipe is still unavailable.
The finite repair group preserves input -2, observed output -1, required output 0.

The actual authored fixture contains twelve requirements and thirteen complete
tasks: three recorded supports, two recorded refutations, three uncovered
requests, two unsupported properties and two runtime deferrals. Two overlapping
incompatible offset requirement pairs are reported as authored mathematical
diagnostics; both requirements and all their tasks stay present. All thirteen
tasks retain an explicit unqualified runtime obligation. Historical table
support never removes a task or grants execution eligibility.

Original and copied input captures share a 64-file/8-MiB allocation ceiling;
individual inputs and generated reports are bounded to 512 KiB. Authored lists
and requested domains are capped at 32 entries, IDs at 64 characters and original
requirement text at 512 characters. Strict JSON refuses duplicate keys,
nonfinite values, surrogates and excess depth/structure. Regular NOFOLLOW and
NONBLOCK descriptors, exact role/body pins, equal-size original/copy rereads and
final output population checks refuse drift, aliases and late extra files.
These sequential rereads do not claim an atomic filesystem snapshot.

The `finite_match_controls.json` report has schema
`codebase-ir-finite-match-controls@1` and separately binds the raw manifest,
requirements and three prior anchors. Its true scope is authored requirement
matching and retained finite-row reconciliation with complete original
requirement/task preservation. Runtime facts, omitted tasks and additional
training epochs are exact integer zero. Checker/kernel/source execution,
producer/request authentication, resource enforcement, proof reuse, native
adoption, production acceptance and current authority remain false.

The new tests assert independent recorded row values and twelve golden
dispositions; they cover mixed refuted/uncovered requests, empty domains,
incompatible properties, unavailable timeout custody, complete tasks,
coherently rehashed native refutation/authority forgeries, immutable prior
anchors, Unicode/JSON types, allocation ceilings and reachable late-output
injection. Retained input discovery walks only twelve explicit ancestors;
`FINITE_MATCH_MANIFEST` supplies an exact fixture path for a copied snapshot
outside the workspace. Original fixtures and prior qualification reports remain
unchanged.

## Completed 300-member resumed inventory receiving controls

`resumed_inventory_controls/receiver.py` receives the independently pinned
historical `codebase-inventory-resume-{root,page,cursor,completion}@1` export.
This is a separate protocol from the earlier 256-member verification-query
reader. It opens only a private frozen copy of thirty explicitly selected
packets: the ninth attempt's independent scan audit and failed native result,
four chunk records and their recorded stdout/stderr, the aggregate resume
record, fourteen root/page/completion/reference bodies, and the fourteenth
attempt's composed native result. The selected closure contains 7,637,392 bytes.
No model/checkpoint bodies, source preimages, native databases, keys or runtime
implementation modules are consumed or imported.

The acquisition receipt at
`artifacts/codebase_ir_parallel_qualification/acceptance/20261003-resumed-inventory-input-01/acquisition.json`
records two repeated original and retained-copy observations before the new
implementation was written. Historical original paths are provenance labels;
the receiver's unchanged-input claim concerns its private frozen packets.
Its three independent raw anchors remain:

- Historical scan audit: `501330f167706f39bdbde7ac235de2444f2c94cb7a14bfe27f0f5258fb87e940`.
- Failed ninth native result: `56275f04227e19d7bebe3f9ed1df18ddeefd140e417e6841ead56f447ede982d`.
- Composed fourteenth native result: `b6307c0c8cd912c55161c3f6d50563cbf71e2d1ac9ba5538b52cb498a90e353f`.

```sh
.venv/bin/python qualification/codebase_ir/acceptance/resumed_inventory_controls/receiver.py \
  --manifest /home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/acceptance/20261003-resumed-inventory-input-01/resumed_inventory_input.json \
  --output /absolute/fresh/resumed-inventory-result
```

The closed input schema is `codebase-ir-resumed-inventory-controls-input@1`:
`schema`, `fixture_origin`, the three named anchor descriptors,
`transport_artifacts`, `chunks`, and `resume_record`. Descriptors have exactly
`path`, `sha256`, and `size_bytes`. Fourteen ordered transport roles each bind
one `role` and `input`; four ordered chunk records bind `run_number`, `record`,
`stdout`, and `stderr`. Original manifest and input scopes are protected from
output writes. Limits apply before reading or allocation: 64 unique files,
32 MiB combined original/copy/report bytes, 8 MiB per body, 256 KiB manifest,
1 MiB report, bounded JSON structure, and exact finite numeric types.

The receiver independently reconstructs full and page membership CIDs, raw
page CIDs, source/head/model labels, predecessor chains, exact member/inference
indices, coverage atoms, worker receipt joins, reference opt-out equivalence,
four root-bound chunk requests and responses, and the final complete chain.
All 300 ordered members remain: 205 inferred, 89 deferred by the recorded
worker-input byte budget, two opaque, one parse failure, one unindexed and two
unsupported targets. Deferred targets retain structural atom coverage without
receiving numerical rows. Seven receiving views retain the 0/32/64/128/192/256/300
frontiers. Prefixes and a full page population without its completion remain
incomplete; no frontier creates runtime facts, inferred absence or omitted
tasks. The ninth whole attempt stays failed despite its completed scan. The
fourteenth composed result remains a distinct recorded success that reused
that chain with zero new scan pages or fitting and two inherited setup epochs.

The `codebase-ir-resumed-inventory-controls@1` report is
`resumed_inventory_controls.json`. Five typed conformance/preservation flags
are true; fifteen execution/authentication/current-authority flags and the
fourteen native authority-ceiling flags stay false. Runtime facts, task
omissions and additional attempted training epochs are exact integer zero.
Recorded worker hashes, PID labels, durations, optimizer metadata, resource
limits and cleanup counters are historical observations. Raw numerical worker
stdin/stdout remains unavailable. Neither hash reconciliation nor the recorded
composed success authenticates numerical output, process origin, source
semantics, signatures, enforcement, production adoption or present authority.

The actual report retains thirty selected input copies and the original manifest.
Bounded NOFOLLOW/NONBLOCK regular descriptors are reread after reconciliation
and controls. Final fences reread original frozen packets, all retained bodies
and the report, then check the canonical output root and its exact population.
These sequential observations do not claim atomic filesystem custody.
Twenty-six coherent corruption controls preserve the independent raw audit
while repairing local page/completion references. The authored tests assert
independent 300/10/4 and 205/89/6 goldens, complete-versus-prefix behavior,
typed booleans/integers, duplicate/nonfinite JSON, original/copy/report drift,
late extra output and root or nested symlink substitutions. Tests construct
their own bounded inert packets and run from a four-file copied implementation
outside the workspace without an external fixture lookup or native tool.

## Failed TLA whole-operation observation receiving

`tla_operation_controls/receiver.py` adds an independent offline receiving
profile for three explicitly selected **failed** whole-operation attempts. The
new roadmap section's linked `tla-operation-control-qualification-20261003/REPORT.md`
was absent at acquisition. The retained `native-selected`, `native-final` and
`native-accepted` command receipts all exited with integer one, and all three
native results report failure. Naming a directory `accepted` does not establish
a successful qualification. This reader preserves those observations and does
not monitor or repeat owner work.

```sh
.venv/bin/python -I -B qualification/codebase_ir/acceptance/tla_operation_controls/receiver.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/20261003-tla-operation-input-02/tla_operation_input.json \
  --output /absolute/fresh/tla-operation-result
```

The private input acquisition contains 35 inert packets and 3,759,484 bytes:
three result/command/source-freeze anchors; exact request, launch, lifecycle and
control audits; authored model/config fixtures; recorded benchmark commands;
saved scheduler configurations; small launcher descriptions; and two partial
snapshots. Two repeated original/copy observations precede implementation.
Original paths remain historical provenance labels; subsequent unchanged-input
claims concern the private captured packets. Acquisition generation01 stopped
before selected input capture during preparation and remains retained separately.
No source modules, installed binaries/JARs, model state, catalog, database, keys
or native owner are opened. Launcher text, model text and paths are inert data.

The closed input schema `codebase-ir-tla-operation-controls-input@1` contains
`schema`, `fixture_origin` and ordered `attempts` with IDs `initial`, `final`,
`accepted`. Each attempt has exactly twelve named roles: `source_freeze`,
`command_result`, `result`, `request_audit`, `launch_audit`, `lifecycle_audit`,
`control_audit`, `fixtures`, `command`, `scheduler_config`, `wrapper`, `partial`.
The first partial is null; all other descriptors have exact `path`, `sha256`,
`size_bytes`. The nine raw result/command/source-freeze anchors are independently
fixed in the receiver, beyond internally repaired audit hashes. The original
manifest and every input directory are protected from output writes.

The initial attempt retains six native phases and an oversized `tool_version`
construction error, with no completed batch or stop control. Each later failed
attempt retains 44 native phases: three batches at one/two/four callers, twelve
completed individual cases, five no-result controls, and three phases from an
unreturned `live_model_deadline` control. Combined counts are 94 phases, six
completed batches, 24 individual cases and ten retained no-result controls.
The later whole failures report `interrupted aggregate operation published a
result`; the exact returned value of that failed control is unavailable. The
reader preserves this producer assertion and its phase frontier without
inventing a result, attributing a verified production defect or upgrading a
partial `running` snapshot into whole-operation success.

Request/launch/lifecycle rows join by exact case and phase, including the recorded
`prlimit` prefix derived from declared CPU/file/address-space limits. Typed
outer interruptions retain their request budgets and zero-result dispositions.
Captured fixture UTF-8 model/config hashes join native input sizes/digests and
module/config receipts. Safe completed lifecycles, finite counterexample state
populations and all recorded theorem/proof ceilings remain explicit. Raw source
bodies and the actual Java/JAR trees are unavailable: 79 source declarations and
recorded wrapper bytes establish custody consistency, not execution origin.

Engine and backend request digests remain distinct. The captured V2 receipt
normalizes a backend numeric timeout `15.0` to integer `15`; both encodings are
retained. Phase budget samples occur at different instants, so a recorded native
request timeout may slightly exceed the later recorded remaining time. These
values are preserved separately and do not qualify exact original caller request
custody, deadline enforcement, installation budgets or an aggregate reservation.
Observed durations, lease labels and cleanup counters remain historical records;
no throughput improvement is inferred.

`tla_operation_controls.json` has schema `codebase-ir-tla-operation-controls@1`.
Five typed receiving/preservation flags are true. Nineteen execution, request,
authentication, resource, model-check/proof, current-authority and production
qualification flags remain false. Runtime facts, task omissions and additional
training epochs are exact integer zero. The 22 authored record controls repair
local audit-container hashes while preserving the independently frozen originals.
They reject whole-failure promotion, phase/ordering ambiguity, forged request or
launch bindings, boolean aliases, receipt/proof promotion, published stop results
and promoted partial snapshots.

Regular NOFOLLOW/NONBLOCK descriptors apply bounds before allocation: 96 total
original/copy/report paths, 32 MiB combined bytes, 2 MiB per input, 128 KiB manifest
and 4 MiB report. Strict JSON refuses duplicates, nonfinite values, surrogates and
excess structure. Original/copy/report rereads and canonical exact output
population fences observe late drift and aliases; they do not claim atomic
filesystem custody. The authored tests create their own complete bounded packets
and run from a three-file copied implementation outside the workspace, without
external fixture lookup or any Java/checker/source execution. All previous
qualification files, fixtures and checkpoints remain intact.


## Apalache admission and raw-witness receiving

`apalache_admission_controls/receiver.py` adds an independent offline receiving
profile for the completed Apalache execution-admission qualification. Its closed
input schema is `codebase-ir-apalache-admission-controls-input@1`; its report is
`apalache_admission_controls.json`, with schema
`codebase-ir-apalache-admission-controls@1`.

```sh
.venv/bin/python -I -B qualification/codebase_ir/acceptance/apalache_admission_controls/receiver.py \
  --manifest artifacts/codebase_ir_parallel_qualification/acceptance/apalache-admission-input-20261003-01/apalache_admission_input.json \
  --output /absolute/fresh/apalache-admission-result
```

Forty explicitly selected bodies, totaling 3,703,397 bytes, were copied into a
private input directory before receiver implementation. Two repeated original
and copy observations completed during acquisition. An old 4.6-MiB acceptance
reference exceeded the preparation helper's separate prior-file cap afterward;
that failure and script remain retained. Completion checked the frozen copies
and preserved the prior files without reopening the owner originals. Subsequent
unchanged-input claims concern this private closure; historical owner paths are
provenance labels, with no current-authority claim.

The input has exact `schema`, `fixture_origin`, `qualification`, `focused_xml`,
`registry_diagnostic_xml`, `registry_test_source` and ordered `attempts` fields.
The four attempt IDs are `capacity_failed`, `resource_failed`, `accepted_smoke`
and `accepted_full`. Each supplies nine descriptors: result, outer command
result, request/launch/lifecycle/control/environment audits, fixtures and saved
scheduler configuration. Descriptors have exact `path`, `sha256`, `size_bytes`.
The original qualification and eight result/command bodies have independent
fixed raw anchors; each role also joins the qualification's named artifact
inventory and the result's raw audit commitments. Selected bodies and the
original manifest are protected from output writes. The native saved scheduler
schema is `codebase-saved-scheduler-config@1`; the reader rejects future versions
of its supported native and V2 schemas explicitly.

The selected closure contains 149 launches and 150 lifecycles. The accepted
smoke and full attempts account for 60 phases, 18 completed cases and four
withheld-result controls. Across all four selected attempts there are 42
serialized cases and seven completed no-result controls. The qualification's
161-launch/162-lifecycle totals include two additional historical smoke runs
whose full audit bodies are outside this selection; those totals remain
reported declarations rather than newly replayed populations.

The capacity failure preserves one version-admission refusal with no launch,
PID, stdout or returned V2 result. Its four unreturned operation frontiers
remain distinct from serialized successful cases. The resource failure preserves
the `-9`, `resource_exhausted=true` model lifecycle before its intended wall
deadline; its exact returned V2 result and OS-level cause are unavailable. The
accepted 300-ms outer timeout remains separate from both failures. Cancellation
boundaries, live markers, phase budgets and recorded cleanup join retained phase
identities and PIDs; they do not authenticate execution or enforce deadlines.

The reader reconciles recorded one-CPU/three-process Apalache reservations,
requested RSS, the half-RSS JVM heap, SerialGC and processor flags, explicit empty
runtime configuration, private-home markers, `prlimit` arguments and finite
extraction limits. Owned lease sums remain separate from whole-pool allocation
and its recorded foreign difference. These observations do not establish cgroup
containment, whole-install ownership, foreign ownership or resource enforcement.
Requested caller widths one/two/four all retain effective dispatch width one;
recorded timings remain separate clocks, with no throughput or overlap claim.
Mixed TLC descriptive `-help` exit one is retained separately from model exits.
Its historical fixture body and actual tool/source bodies are outside this
selection; available declarations do not establish execution provenance.

Apalache invalid cases retain the original violation-file UTF-8 bytes and digest,
raw `State0/1/2` labels and values `0/1/2`, and zero parsed states. The captured
legacy `replayed=true` and `external_tool_proof=true` flags are publisher records.
They do not establish trace replay, checker truth or new proof authority. The
receiver preserves Safety-only, three-step Apalache bounds and excludes new
fairness, liveness and universal-proof claims. Compiler artifact and request
identities are retained without inferring unavailable digest recipes or original
caller request bytes.

The prior registry diagnostic JUnit records the captured `ERROR` with the
missing `ResultStatus.TIMEOUT` diagnostic. The final focused JUnit and inert test
AST preserve the passing expectation of that same controlled error. No test
source is imported or executed, and no native registry result is available.
Native engine/helper success cannot qualify registry-native success.

Six receiving/preservation flags are true; 23 execution, authentication,
resource, replay, registry-native, quality, current-authority and production
flags are false. Runtime facts, task omissions and additional training epochs
are exact integer zero. Thirty correlated record controls repair audit-container
hash labels while keeping the original independent anchors fixed. They refuse
future schemas, Boolean aliases, forged native/JVM/lease/request bindings,
manufactured parsed states, proof promotion, published stop results, omitted
advisory dispatch and changed operation/case populations.

The 37 authored tests create their own bounded packets and run from a copied
three-file implementation outside the workspace. Bounds apply before descriptor
allocation: 96 paths, 32 MiB combined original/copy/report bytes, 1 MiB per input,
128 KiB manifest and 4 MiB report. Strict JSON excludes duplicate keys, nonfinite
numbers, surrogates and excess structure. XML is bounded UTF-8 with no DTD or
entities; test AST is inert. Regular NOFOLLOW/NONBLOCK descriptors, original/copy/
report rereads and final canonical exact output populations reject late changes,
FIFOs and root or nested aliases. These sequential observations do not claim an
atomic filesystem snapshot. All earlier files and artifact generations remain
unchanged except this README append.

The retained native receipt keeps the configuration text terminal LF, while its
wire configuration omits that LF. The receiver retains both original encodings
and checks their observed terminal-LF normalization. It does not infer a new
configuration or request digest recipe.


## Retained generic foreign outcomes — eighth parallel qualification

`foreign_outcome_controls/receiver.py` receives the fixed
`registry-foreign-outcome-qualification-20261003` records with only the Python
standard library. Its manifest explicitly selects 20 frozen bodies (623,677 bytes):
the qualification, source-evolution metadata, and nine roles for each of the
initial failed and accepted attempts. Metadata paths naming producer sources,
executables, snapshots or earlier qualifications are descriptive; those nested
bodies are not opened, imported or executed.

The initial whole attempt records three phases and no accepted case. Its authored
three-step artifact was executed with the historical decoder's 64-step command;
the exact fixture assertion remains preserved. The accepted whole attempt records
six phases and two cases using the compiler-default 64-step artifacts, with empty
source maps and projection losses. The later artifact, trace-parser and registry
budget milestones are outside this selected closure. Nine historical phases are
not nine accepted phases. The producer's 1,914 selected tests, 363 focused tests
and 82 new tests overlap; this receiver does not sum or rerun them.

Both accepted generic attempts remain `succeeded` with `unknown` conclusions.
Their payloads preserve the exact original `model_check` typed result and its
`satisfied` or `violated` status, bounded ceiling, assumptions, source/configuration
bindings, raw witness and diagnostics. Compact, sorted ASCII JSON independently
rederives request and attempt digests. Result/attempt identities and the original
no-authority-upgrade diagnostic remain bound. The inherited generic output digest
is preserved and reconciled between attempt and result; its producer's digest
algorithm is not independently rederived. Generic zero usage is kept separate from
original native measurements. No theorem, satisfiability fact or current authority
is minted from the retained typed evidence.

The invalid case retains raw `State0`, `State1` and `State2` assignments with values
0, 1 and 2, zero parsed states, the historical `replayed=true` label, and the
`no parseable State blocks` diagnostic. This is a preserved historical observation
with no structural or semantic trace replay qualification. Native phases reconcile
logical/actual commands, selected input hashes, recorded benchmark-owned deadlines,
owned lease profiles, private JVM configuration and cleanup. Whole-pool allocations
are lower bounds for recorded owned leases; foreign reservations and live resource
enforcement are not authenticated. The benchmark's outer scope establishes no
new production registry setup-budget guarantee.

The input/report schemas are `codebase-ir-foreign-outcome-controls-input@1` and
`codebase-ir-foreign-outcome-controls@1`. Run the receiver with `--manifest` and a
fresh `--output` directory. It retains the input manifest and all 20 selected
bodies before publishing `foreign_outcome_controls.json`; original/copy/report
raw rereads and two exact output-population fences close the run. Bounds are 64
captured files, 1 MiB per selected body, 8 MiB combined original/copy/report bytes,
128 KiB manifest, 4 MiB report, depth 32 and 100,000 JSON values. Duplicate keys,
nonfinite numbers, surrogates, oversized integers, aliases, FIFOs, changed files
and extra output entries are refused. The observations remain sequential, without
an atomic snapshot claim.

Seven receiving flags are true, 24 execution/authentication/replay/resource/quality/
current-authority/production flags are false, and runtime facts, task omissions and
additional training epochs are exact integer zero. Twenty repaired-audit-digest
record controls exercise the independent conversion and phase predicates. The 37
new authored tests include typed Boolean rejection, failed/accepted separation,
rebound identities, original payload mutations, file and structure limits, and late
original/copy/manifest/report/population changes. The copied three-file suite and
actual receiving guard run without a native workspace or owner imports. Existing
qualification source and the first 94,571 bytes of this README remain unchanged.


### Serialized TLA artifact payload custody (2026-10-03, ninth parallel tranche)

`artifact_payload_controls/receiver.py` is a stdlib-only receiver for sixteen
explicit retained metadata bodies from the completed artifact-payload milestone.
It preserves complete serialized artifacts through canonical, submitted, decoded,
registry-request and controlled static V2 projections. It independently hashes
UTF-8 model/configuration text and canonical nontext artifact metadata, excluding
`artifact_digest` and the three text bodies from the outer identity recipe. Both
selected artifacts retain compile `max_steps=3`, two source-map records, one loss
disclosure, translator identity, safety properties and fairness limitations.
Compiler default `max_steps=64` remains a separate static declaration.

The receiver reconciles six ordered historical setup/model/help receipts with
request, launch, lifecycle, environment and benchmark-owned budget metadata. The
model command's literal `--length=3`, model/configuration input digests and sizes,
request and attempt identities, and exact original typed payload bind to the
selected artifacts. Generic conversion remains `unknown`; original typed results
remain `satisfied` or `violated`, with `model_check` authority and a `bounded`
translation ceiling. Generic output digests are preserved and bound; their
producer algorithm is not independently rederived.

The invalid artifact-stage witness retains the earlier raw State0/1/2 bytes,
empty parsed state list and legacy `replayed=True` observation. This workflow does
not interpret trace grammar or claim structural or semantic replay. The fixed
foreign-outcome report separately preserves the earlier failed three-phase
3-to-64 bound mismatch and accepted six-phase default-64 attempt. Those historical
reference phases and overlapping test counts are never added to this increment.
The artifact producer recorded 2,015 selected tests, 531 focused tests, 101 new
artifact tests, two native cases and six phases. Prior preservation and source/tool
inventories remain selected metadata declarations; nested referenced bodies are
not followed.

API: `audit(manifest_path, output)` returns the published report or raises
`Refusal`/an ordinary filesystem error. The CLI accepts only `--manifest` and
`--output`, using an absent output beneath an existing canonical parent. Input
schema `codebase-ir-artifact-payload-controls-input@1` has the closed fields
`schema` and `selected_files`; sixteen rows have exactly `role`, `path`, `sha256`
and `size_bytes`, in this order:

1. `qualification`
2. `source_evolution`
3. `source_snapshot`
4. `execution_freeze`
5. `benchmark_preflight`
6. `joined_selected_result`
7. `native_command_result`
8. `native_command`
9. `native_result`
10. `native_fixtures`
11. `native_request_audit`
12. `native_phase_budget_audit`
13. `native_lifecycle_audit`
14. `native_apalache_environment_audit`
15. `native_launch_audit`
16. `historical_foreign_outcome_reference`

Report schema `codebase-ir-artifact-payload-controls@1`, workflow
`artifact_payload_controls`, is published as `artifact_payload_controls.json`.
It provides flat `manifest_sha256` and `<role>_sha256` bindings for all sixteen
roles, ordered `selected_files` with exact retained-copy descriptors, two artifact
summaries, two static decoder summaries, the six-phase `native_attempt`, separate
`qualification` and `historical_foreign_reference` summaries, closed scope flags,
and 27 repaired-digest negative controls. `qualified=True` and `status=passed`
qualify this selected metadata custody profile only. Every authority, execution,
producer authentication, semantic source-map, translation correctness, theorem,
unbounded proof, native V2, general legacy-fallback, replay, default-registry
production-budget, model-quality, live-eligibility, production-activation and
throughput flag remains false. Runtime facts, omitted tasks, extra attempted
training epochs and production tasks closed remain zero/empty.

Limits are 64 original selections, 128 captured files, 1 MiB per selected body,
8 MiB total captured bytes, 128 KiB manifest, 4 MiB report, JSON depth 32 and
100,000 JSON values per document. Selected paths must be absolute and canonical,
regular and distinct by physical inode; duplicate JSON keys, non-finite values,
unpaired surrogates, malformed descriptors, booleans in integer fields and
unknown nested fields are refused. The output has exactly eighteen regular files
and one retained directory. Original and retained bytes, sizes and inode
identities are reread after report publication. Exclusive publication verifies
that captured manifest, retained and report bodies equal the intended bytes.

Fresh input acquisition:
`artifacts/codebase_ir_parallel_qualification/acceptance/artifact-payload-input-20261003-01/manifest.json`
(raw SHA-256 `3a01d9e9158fe4dc63007d065e21ce87b345328a8f96d023148b32d3b0a88c6e`)
selects sixteen frozen copies totaling 771,480 bytes. Acquisition preceded these
new qualification sources. The original accepted metadata bodies remain pinned
in `acquisition.json`. Retained output and frozen validation receipts are sibling
`artifact-payload-retained-20261003-01` and
`artifact-payload-validation-20261003-01` artifact directories.

Run the receiver with `/usr/bin/python3 -B` and absolute manifest/output paths.
Run its 63 focused tests with:

```sh
/usr/bin/python3 -B -m unittest discover -s qualification/codebase_ir/acceptance -p test_codebase_ir_artifact_payload_controls.py -q
```

The focused suite tests actual receiving boundaries, repaired metadata forgeries,
complete payload preservation and publication drift. Copied receiver/init/test
sources run independently with empty PATH/PYTHONPATH. The guarded receiving run
uses actual stdlib metadata reads and rejects subprocess/network/database/native
loading/producer import events. Existing acceptance sources and the previous
98,758-byte README prefix are preserved in full. The earlier receiver and all
prior retained qualification artifacts remain unchanged.


### Signed successor worker acceptance metadata (2026-10-03, tenth parallel tranche)

`signed_worker_acceptance_controls/receiver.py` receives twenty fixed metadata
bodies from completed signed successor attempt08 using only the standard library.
The original source-successor review keeps `signed_successor_worker_qualified=False`;
the later expansion review separately records qualified signed dispatch. Seven
failed-attempt descriptors remain historical references. Their archive bodies and
the 23,202-file independent archive are not opened or qualified by this receiver.

The receiver preserves both original TYPE and FORMAT administrator tasks, their
TYPE-to-FORMAT dependency, four mandatory pending evidence requirements, complete
scope/output/validation declarations and their signed manifest/receipt projections.
TYPE is already completed at revision 4 before START. Only the ready FORMAT residual
is selected for dispatch; it advances from revision 1 through in-progress revision 3
to completed revision 4. These two populations remain separate. Native admission
contains `manifest`, `graph` and `receipt`; the public plan contains only `graph`
and `receipt`. Complete signed manifest and planning-receipt DAG-JSON/SHA256 byte
CIDs are rederived. Owner/profile/signature syntax is reconciled as declaration
metadata; native `sha256:` profile labels retain their distinct meaning.

Raw and decoded public worker artifacts preserve complete JSON equality and the
raw artifact's exact filename/hash binding. The independently parsed retained log
has the boundary receipt at line 9 and materialized edit receipt at line 10. UID1001,
PID, private-path denial, source/instruction hashes and task/context/selection CIDs
join their retained projections. Historical signature verification remains true in
the original receipt; this receiver's cryptographic-verification flag is false.
Neither copied signatures nor worker output confer completion or proof authority.

The selected completion keeps the prerequisite TYPE claim/validation, unchanged
FORMAT task contract, ordinary portal-gate result and accepted-source-transition
record. Worker self-approval and task-completion authority remain false. Attempt,
claim, lease and fence identifiers reconcile with the database-attempt declaration.
The accepted transition joins the declared tracked `calc.py` output, two-parent
merge and both published public check observations. Exact stdout/stderr bytes and
hashes are independently reconciled; no Git or public check executes here. The
source publication's generation 2 to 3 record joins its previous head and exact
`StaleCodebaseError`/`resume catalog head changed` observation. Corpus/source/AST
dependency invalidation is separately received by the publication-dependency lane.

The recorded dispatch inherits two setup epochs, ten default pages and one
reference page, with zero new fits, inference attempts, scan pages or provider
calls. Its public reference close timed out; it is not a completed speed baseline
or an integrity refusal. Recorded UID/STOP/cleanup observations establish no new
process-origin, physical-absence, native admission, resource or cgroup authority.
Checkpoint/Adam preservation is metadata equality, without opening model bodies.

API `audit(manifest_path, output)` and CLI `--manifest`/`--output` use an absent
output under an existing canonical parent. Closed input/report schemas are
`codebase-ir-signed-worker-acceptance-controls-input@1` and
`codebase-ir-signed-worker-acceptance-controls@1`. The report is
`signed_worker_acceptance_controls.json`, workflow `signed_worker_acceptance_controls`,
with `manifest_sha256`, twenty ordered `selected_files[i].sha256` bindings and
matching flat `<role>_sha256` aliases. Ten receiving flags are true, 36 execution,
authentication, source/intent/behavioral/physical-absence/resource/quality/current
and production-authority flags are false, and eight runtime/task/training/fit/
inference/scan/reference/provider counters are exact integer zero. Production
tasks closed remain empty. Qualified status applies only to selected metadata
receiving and custody; original native qualification claims keep historical scope.

Limits are 64 selected and 128 captured files, 4 MiB per body, 32 MiB combined original/
retained/report bytes, 128 KiB manifest, 4 MiB report, JSON depth 32 and 100,000 values.
Strict JSON and a fixed nested profile reject duplicate keys, nonfinite values,
unpaired surrogates, Boolean integer aliases, unknown fields and future schemas.
NOFOLLOW/NONBLOCK regular descriptors and physical identities reject aliases,
FIFOs, drift and late equal-byte inode replacement. Ancestor directory generations
are retained. Original/copy/manifest/report rereads and repeated exact publication
populations close the run: 22 regular output files and one retained directory,
43 observed raw bodies. Observations are sequential, without atomic-snapshot claims.

The input acquisition at
`artifacts/codebase_ir_parallel_qualification/acceptance/signed-worker-acceptance-input-20261003-01/manifest.json`
(raw SHA256 `ced54dd8ef34a703345f6bc767a77ed4aed1cbdf70821cd62206122a9e868472`)
preceded qualification source creation. Its twenty copies total 5,987,964 bytes;
original bodies and all 63 prior acceptance files were separately pinned.
`successor_expansion_review` uses the root's acquired private machine-review copy,
so later owner documentation changes cannot alter this selection. Retained output
and validation receipts use sibling `signed-worker-acceptance-retained-20261003-01`
and `signed-worker-acceptance-validation-20261003-01` directories. Refused development
source generations are retained separately from the accepted report.

The 49 authored tests carry bounded compressed fixed inputs and run independently
from copied init/receiver/test sources with empty PATH/PYTHONPATH. They include
repaired linked metadata forgeries that reach their intended semantic predicates,
actual descriptor limits and late original/copy/manifest/report/inode/directory/
population changes. The separate nonmock receiving guard records actual reads and
five typed-zero subprocess/network/database/native-load/owner-import counters.
Run the focused suite with:

```sh
/usr/bin/python3 -B -m unittest discover -s qualification/codebase_ir/acceptance -p test_codebase_ir_signed_worker_acceptance_controls.py -q
```

All earlier acceptance files and the previous 104,813-byte README prefix remain
unchanged. No owner source, parser, native tool, database, profile key or model is
opened, imported or executed by the new receiving workflow.
