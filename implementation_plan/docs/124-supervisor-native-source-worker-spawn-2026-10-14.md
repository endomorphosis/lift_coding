# 124: Native source-worker launch custody, 2026-10-14

The supervisor source broker now checks its retained native task, source
nomination and managed allocation before a trusted launcher creates a child,
then checks that same custody again before enabling child source reads.
The [updated improvement plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/df577aee916a20594e6672dceadd6e40e3948d16/docs/agent_supervisor/reversible_codebase_views_plan.md#native-broker-launch-boundary-2026-10-14)
and [permission/process handoff proposal](https://github.com/endomorphosis/ipfs_accelerate_py/blob/df577aee916a20594e6672dceadd6e40e3948d16/docs/agent_supervisor/evidence/native-source-worker-spawn-20261014/permission-handoff-design.json)
keep writable delegation, cross-process wrapper authentication and signed
context adoption as separate subsequent increments with explicit acceptance,
refusal and cleanup checks. The proposal changes no deployed permissions.

The [indexed-proof context followup](https://github.com/endomorphosis/ipfs_accelerate_py/blob/df577aee916a20594e6672dceadd6e40e3948d16/docs/agent_supervisor/evidence/native-source-worker-spawn-20261014/indexed-proof-context-followup.json)
proposes reusing the existing DuckDB-backed repository index, capsules and checked
verification cache. It requires a complete admitted key, current source generation
and independently checked correspondence between Git-tree and SHA256 identities.
Mandatory evidence, assumptions and residual obligations remain present. This
proposal implements no adapter and claims no learned reconstruction or token gain.

## Qualified behavior

The [broker guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/df577aee916a20594e6672dceadd6e40e3948d16/docs/agent_supervisor/source_lookup_worker.md#check-before-launch-and-before-registration)
places `require_before_spawn()` immediately before the launcher's literal
`Popen`, followed by `note_spawned(actual_child)`. Native registration requires
the original initialized process object, live kernel birth, the original owner's
direct child and the allocated working directory. Copied preparation, serialized
handles, duplicate/reentrant admission and currentness loss refuse. The existing
registration path remains available for legacy sessions without native handles.

Both canonical and allocated complete source populations stay independently
checked, including omitted originals. Closing checks recheck native claim,
grant, lease, lifecycle, nomination and private endpoints. Callback-bearing CAS
loads run outside SERVER; coordinator fences keep their existing lock order.
Source selection and detached observations supply no proof or task authority.
Checks are sequential and do not exclude concurrent filesystem writers.

Before-birth refusal prevents this launcher from spawning. A refusal after an
actual birth closes the session, revokes source access and leaves registration
disabled. The launcher retains the actual child's termination/reaping and
worker-cleanup responsibility; the broker does not kill it or undo prior costs.
Successful owner-side inert-child admission does not qualify a deployed worker
UID, provider command, compiled context or Terminal task completion.

## Parallel progress and publication

The qualified accelerator leaf is `df577aee916a20594e6672dceadd6e40e3948d16`, retained in published
`df577aee916a20594e6672dceadd6e40e3948d16`. This contribution incorporates published parallel integration
`e4b8c4bba2fc7d5b7484b9021cbb9a5bcfc5e7d4`, including capsule budgets, per-turn
usage and acceptance declarations. Its 417 incoming paths do not overlap the
seven owned source/test/guide paths, but 28 listed dependencies change.
A fresh complete run qualifies the combined listed source state; the original
premerge execution and every earlier attempt remain separately retained.
Incoming tests outside this run's twelve-suite roster are not added to its count.

Parent publication builds on `d32bc5848a2a13f1a7902d5a76b1cc6f3467e63b`, preserving the parallel
integration, [balanced LegalIR preparation](122-legal-conditions-balanced-preparation-2026-10-14.md)
and [storage continuation](123-legal-storage-continuation-2026-10-14.md).
Only the accelerator gitlink advances. The incoming datasets pin remains
`a0f60d42f836571a0023515e92dfb0e5724f0d79` and kit remains `40c98c71b95be750509ffdb21e7e5494d91b4e79`.
Execution uses immutable datasets `ebdf6539a4afaf1f10c20744cb14222ef9db4d2b`
and kit `8ac00bb1974b1378e12091d546d8425af34049e0`. All 51 listed datasets
objects equal the incoming parent pin; no kit source files are listed. Dependency
ancestry and listed-byte comparisons do not qualify unlisted decoder or kit code.
Foreign working files and physical parent submodules are preserved.

## Evidence and limits

The [qualification bundle](https://github.com/endomorphosis/ipfs_accelerate_py/blob/df577aee916a20594e6672dceadd6e40e3948d16/docs/agent_supervisor/evidence/native-source-worker-spawn-20261014/README.md)
retains a final complete run of **276 distinct passing tests across twelve
suites**, including 53 new cases, with zero failures, errors or skips.
Collection and JUnit identities agree; all 218 listed source bindings stayed
unchanged: 167 accelerator and 51 datasets files and supporting records.
The retained elapsed time is 1018.995 seconds. Four exact local documentation
workflow blocks pass, plus 121 relative links and 16 anchors.
The original reversible source codec and edit mapper remain unchanged.
These records do not attest a complete dynamic import or toolchain closure.

The fixtures use real claims/coordinator/CAS, sealed Portal projections, managed
Git worktrees and inert same-UID Python processes. Each actual child is
terminated/reaped in its caller's finally path. Actual same-owner socket refusal
is distinct from worker-UID qualification. The router suite exercises authored
provider responses and UID/descriptor adapters; listener/deployment metadata
remain authored seams. No live provider/model, training, solver, Docker or
an official task verifier is invoked. Existing separate IR family, schema/version,
decoder-task and 8D/384D/768D checkpoints, embeddings, model-manager entries and
DuckDB/DuckLake assets are reused and preserved. This establishes no learned
reconstruction improvement or complete-session token saving.

The [merge compatibility record](../../artifacts/native-source-worker-spawn-publication-20261014/merge-compatibility.json),
[exact published CI observation](../../artifacts/native-source-worker-spawn-publication-20261014/hosted-ci.json),
[parent checks](../../artifacts/native-source-worker-spawn-publication-20261014/parent-checks.json)
and [publication manifest](../../artifacts/native-source-worker-spawn-publication-20261014/manifest.json)
retain source, dependency, CI and link custody separately. GitHub [run 38520734939](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38520734939) was billing-blocked before execution: runner ID zero and an empty step list. Hosted gates are not claimed as passing.
No workflow dispatch or rerun is requested.

Next provision read-only worker access before allocation capture, then seal
writable delegation without replacing original witnesses. Authenticate the
original daemon/wrapper and actual worker ancestry across processes; independently
join signed profile @4 and compiled instruction @5. Reuse the integrated
capsule/usage work for repeated matched-success full sessions, counting planning,
coding, retrieval, expansion, refresh, repair and failed attempts.
