# Supervisor initialization and replay followup

This release fixes three remaining component gaps: benchmark initialization now
receives the selected formula decoder, checkpoint replay has bounded verified
reads, and the shared scheduler can gradually resume admissions after pressure.
It preserves the existing default admission policy and model/proof authorities.

The [benchmark wrapper fix](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/benchmark-initial-context-20261003/README.md)
forwards the frozen formula decoder and reviewed header protocol to the native
initial-context builder. Previously both arguments caused a `TypeError` before
inference. The new boundary and neighboring tests passed 39 cases, including
authored frozen inference, DuckLake hydration and persisted replay. The three
original failures remain in the evidence.

The [artifact replay qualification](../../external/ipfs_datasets/docs/software_contracts/evidence/registry-bounded-replay-20261003/README.md)
has 148 final passing checks. Source384 generations, prior heads and projections,
model-generation corpus attachments and resident inference read exact verified
bytes through the existing registry. Oversized files, FIFOs, symlinks, corruption
and concurrent growth refuse before decoding. This bounds artifact input bytes;
it does not promise a total peak-RSS limit or migrate old producer generations.
The controls include actual CPU inference, source-generation training, pinned
Lake checks and cold replay. An initial run without explicit Lake configuration
skipped 12 cases; the configured rerun executed and passed all 12.

[Shared pressure recovery](../../external/ipfs_datasets/docs/autoencoders/SHARED_PROOF_PRESSURE_RECOVERY.md)
uses the existing host scheduler and durable state lock. With
`IPFS_DATASETS_PROOF_RESOURCE_RECOVERY=1` in every cooperating process, admissions
require spaced healthy samples after cooldown, then resume at a bounded rate.
Validation and cleanup retain their reserved lane and original pressure checks.
The default remains disabled; active clients must agree on the shared policy.
The host readiness probe left its current configuration intact and recorded
the policy mismatch. Controlled pressure tests are distinct from an actual
external-load stress campaign. The recovery suite passed 87 controls, including
four actual subprocess and restart controls with injected pressure and time.

This release adds an opt-in
[Source384 supervisor context](../../external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/SOURCE384_HARBOR_CONTEXT.md).
The full arm consumes the real shared SecurityIR384 checkpoint through the
datasets source-unit owner before planning. Signed source bytes, native AST/CAS
state, model version, GTE assets, inference artifacts and producer identities
are revalidated at planning and dispatch. The bounded prompt includes typed IR
as canonical JSON text with explicit validation status. It grants no proof or
execution authority. Source/model drift rejects; completed publication remains
observable while a new dispatch requires a current generation.

All comparison arms can select the same 5-CPU/12-GiB resource profile, accounting
for the 6-GiB inference parent and scheduler reserve. Original task defaults
remain unchanged. Transport controls qualify exact offline asset relocation
and reject legacy-training combinations; no-index records Source384 disabled.
The final consumer suite passes 13 cases with the actual pinned checkpoint,
including exact IR delivery, no neural replay, population bounds and deadlines.
Its 256-file bound matches the signed creation manifest and can accommodate
the 218-file original checkout plus supervisor inputs.
Separate transport and native lifecycle suites cover 126 and 58 cases.

A retained public Bottle-source canary prepared its complete indexed context
in 156.91 seconds with zero text-provider calls. Of 358 inventoried functions,
127 decoded candidates remain unsupported by the source guard, one exceeds the
GTE token limit, 166 exceed the declared selection budget and 64 fail exact
normalization. Two candidates reach the prompt summary; the other 125 are
explicitly counted as omitted. This is not a fresh official task score or a
formal proof. Its timing predates the final timer-only preflight correction.

The first large-source attempt exhausted the unchanged 90-second inference
phase. Bottle's 4,652 dependency edges exceeded a 4,096-entry CID cache working
set. Fixed 8,192-entry caches retain all validation and reduce instrumented
observation from 27.85 to 13.62 seconds; 64 cache controls passed. Source-unit
extraction/inference and scanner controls passed 79 cases. Failed prefixes and
exact source generations are retained in repository evidence. No weights were
trained or promoted in this release.

The frozen backlog remains 18 of 32 closed, with 26 qualified for their declared
scope and 14 production criteria open. GPU device admission, aggregate resource
enforcement, the joined acceptance matrix and matched benchmark campaign remain
among the outstanding work. Concurrent upstream decoder work is preserved in
the pinned datasets revision. Automatic Source384 successor inference, source
grammar for Bottle's string/header behavior, and fresh matched native
Codex/no-index/full Harbor trials also remain open.

The [header grammar followup](../../external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/SOURCE384_HEADER_GRAMMAR_PLAN.md)
separates source-guard refusal from model expressiveness. All 127 source checks
stop before prediction comparison, and the current binary-expression checkpoint
cannot emit header-string transformations. The next slice reuses the existing
string grammar and independently checked header contracts, with a forked head,
held-out reconstruction measurements and explicit logic-validation gates.

The first fresh Docker qualification enforced the earlier 5-CPU/8-GiB profile
and completed deployment and empty native START. Preparation then timed out at
native resource admission. Its pre-preparation free-memory sample was below
the requested 6-GiB reservation plus unchanged scheduler headroom. The explicit
replacement profile gives every comparison arm 12 GiB; the failed generation
is retained separately and is not an official task score.

The native startup check now polls within its existing deadline, binds the
original root and daemon identities, and requires a stable healthy tree with
an advancing heartbeat. Its 28 distinct controls passed across retained runs;
two initial native failures passed on an unchanged-source retry. Docker report
collection now uses a separate bounded JSON file; 158 controls pass, including
merged-output and malformed-report cases.

The [full-checkout indexing fix](../../external/ipfs_datasets/docs/software_contracts/evidence/source-cold-index-performance-20261003/README.md)
uses 32,768-entry CID caches and bounded parameterized AST insert batches.
It preserves current-byte verification, canonical reconstruction and transactional
rollback. Its 146 controls pass, and all 218 public files publish in 55.02 seconds
under the unchanged 90-second deadline. A fresh process observes the same index
in 13.65 seconds. This is separate from the earlier Bottle-only measurements;
no overall speedup ratio is inferred from differently instrumented runs.

The [original-container qualification](../../external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/SOURCE384_DOCKER_QUALIFICATION.md)
now passes native startup, resource admission and cold publication with the
complete original checkout. That fourth attempt still misses the combined
90-second Source384 budget in the source observation immediately before inference;
the context phase ends after 100.86 seconds. The fixed report collector preserves
that native refusal and cleanup removes the container. Actual neural inference
in this full Docker path, the full task result and a new token comparison remain
unqualified. Thirteen real-checkpoint consumer controls passed again in 45.96
seconds against the optimized indexing owners. No weights were changed.

The [manifest reconstruction followup](../../external/ipfs_datasets/docs/software_contracts/evidence/source-combined-observation-performance-20261003/README.md)
adds bounded reuse of canonical manifest reconstruction and a guarded native
comparison at the existing post-read catalog check. It preserves fresh source,
CAS, head, SQL and model validation. Its 114 distinct controls pass across two
invocations. A fresh local run consumes the actual checkpoint over all 220
permitted files in 89.963 seconds against the unchanged cooperative 90-second
budget; its outer wrapper takes 90.041 seconds including cleanup and accounting.
This roughly 37-millisecond native margin does not establish reliable scheduling
or container qualification. All 127 decoded candidates remain unsupported by
the current source grammar; correct formalization and a fresh task score remain
unqualified. Thirteen supervisor checkpoint-consumer controls pass in 43.83
seconds with these exact indexing producers.

The fifth fresh Docker attempt passes deployment, native START/STOP, publication
and the first source observation with the same complete input and resource
profile. Its child worker then times out; no completed model load or inference
artifact is established. Initial context takes 98.30 seconds and the probe
109.86 seconds. Slow dependency downloads extend the separate deployment to
1109.51 seconds. The container is removed and the structured failure is retained
in the [new evidence package](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/source384-docker-reconstruction-20261003/README.md).
The receipt does not isolate worker startup, inference and earlier preparation
costs, so the remaining performance cause needs a timed diagnostic. This attempt
does not provide a new task score, token comparison or proof of source behavior.

Two subsequent instrumented container runs isolated preparation budget starvation:
cold preparation took about 79.4 seconds, with 40.0 seconds in AST projection
persistence. The worker had less than one second remaining in the first run;
the second refused before worker invocation. These stage diagnostics preserve
the original source population, resources and deadlines.

The [SQL and dependency replay](../../external/ipfs_datasets/docs/software_contracts/evidence/source-sql-column-performance-20261003/README.md)
preserves all 31 projections, 13 catalog tables and cold reconstruction. An
off-tree column insertion candidate improves host execute time from 3.399 to
0.946 seconds, but Docker remains at 40.269 versus 38.692 seconds. That SQL patch
was not applied. DuckDB 1.5.5 repeatedly attempts optional pandas imports when
pandas is absent. Four fresh native processes with identical mixed values and
engine binary measure 0.0215/0.0217 seconds with real pandas available, versus
0.9992/0.9958 seconds without it. Every returned value matches. This isolates a
dependency-related conversion cost without claiming an end-to-end speedup.

The container deployment now pins pandas 3.0.2 and NumPy 1.26.4 and checks both
before native START. All 91 focused deployment and transport controls pass.
The index, inference and model owners remain unchanged. A fresh uninstrumented
original-container qualification tests this deployment correction separately.
That attempt stops during the existing 600-second CPU PyTorch installation
limit, before pandas installation, START or inference. The 812.484-second
attempt and cleanup are retained as a separate setup failure. A pinned local
wheel transport is being added to avoid repeating the large network transfer
in each fresh container; runtime and inference deadlines remain unchanged.

The optional, hash-verified local CPU wheel now has 136 passing deployment and
transport controls. Its first run passed setup in 65.266 seconds but exposed
a late inference-publication import of training-only workspace initialization.
The datasets fix shares canonical staging directly with inference while
preserving the training guard; 43 datasets integration tests and 13 actual
checkpoint supervisor tests pass. The earlier failed run remains separately
recorded and makes no completed-inference claim.

The [corrected original-container run](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/source384-docker-inference-publication-20261003/README.md)
now passes setup, native START/STOP, real checkpoint inference, publication
and source-bound replay. All 218 original files remain unchanged under the
five-CPU/12-GiB profile. Source384 completes in 82.872 seconds within its
90-second budget; full initial-context assembly takes 147.267 seconds and
the native probe 171.962 seconds. The saved artifact records one model load,
127 decoded unsupported candidates, one token deferral, 737 selection deferrals
and 79 unsupported normalizations across 944 functions. The container is
removed. Setup took 458.743 seconds and the whole attempt 656.825 seconds;
these are distinct scopes, not a measured speedup against prior failed runs.

The decoder still cannot represent the required header program. This pass
establishes deployed inference plumbing without a source-qualified property,
new benchmark score or token advantage. The full task trial, successor context
refresh after publication, and explicit header grammar remain open. The raw
inference artifact stays local because it contains benchmark source; public
evidence preserves its digest and a reviewed verification summary.
