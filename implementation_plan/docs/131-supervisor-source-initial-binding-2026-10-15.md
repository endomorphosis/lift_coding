# Supervisor initial source-reader binding — 2026-10-15

This increment detaches retained source-inventory CAS replay from SERVER during
initial binding and preserves the exact reader published by each native bind
attempt. It continues the query-replay work in [note 130](130-supervisor-source-query-replay-2026-10-14.md).

## Result and boundaries

The public `CurrentSourceLookup` constructor still configures and replays its
original repository and retained CAS. The gateway can privately configure that
same exact reader, snapshot its owner-bound binding and original inputs, release
SERVER for retained replay, and then close the original owner and source checks
before publication. The server and native task binder release their corresponding
outer SERVER acquisitions across the replay. Existing task and allocation whole
operation guards remain in force.

Native task and allocation closing fences run through the existing admissions
before publication. One final binding clock sample runs without SERVER after
those fences; the final task-grant and allocation-expiry checks reuse that
sample without invoking another closing clock callback. A private, nonserialized witness records the actual candidate,
original gateway/connection, binding bytes, CAS, and workspace. Native cleanup
consumes its own witness after publication, including a later exception, rather
than adopting whichever genuine reader happens to occupy the gateway slot.
Failures before this attempt publishes leave its task/allocation markers empty;
a competing reader is neither adopted nor removed.

The gateway shares a short busy guard between initial binding and source reads.
It checks original request/limits guards, owner identity, server configuration,
connection, transaction lock, candidate scope, empty continuation registry, full
source population, native task body/revision and retained store identity. An
active or unknown native transaction refuses binding; no borrowed transaction is
committed or rolled back by this path.

This is finite owner-side CAS callback and publication qualification. Native
claim/grant/lease clocks retain their existing contracts. Sequential observations
do not establish a filesystem writer lease, universal callback safety, deployment
UID custody, a coding-child adoption, an official benchmark result, or measured
session token savings.

## Validation and publication

The baseline runs the allocation-route CAS callback regression against the five
unchanged runtime sources at accelerator `55c42dd740d75c3ba04d6991c90cf0aa0dccd8a9`.
It fails with the expected SERVER ownership assertion. Exact snapshots, raw logs,
JUnit and source/index guards are retained. The selected full qualification
passed **299 unique cases across 13 complete suites**, including **32 new
initial-binding cases**, with zero failures, errors or skips, in
1691.656 seconds. All 279 listed source bindings and fixed
execution HEAD/index guards passed. The original expected failure is not added
to that passing total.

The four pinned local documentation workflow blocks passed, together with
121 relative links and 18 anchors. The child manifest binds 43 files; the
independent parent checker joins the published Git objects, all 279 qualified
source files, baseline, raw JUnit, documentation receipt and preserved incoming
parent objects before advancing the parent accelerator pin.

Accelerator publication is
[`09b9d761373a9fded02f6e39d18d00907d332a2c`](https://github.com/endomorphosis/ipfs_accelerate_py/commit/09b9d761373a9fded02f6e39d18d00907d332a2c).
[Hosted CI observation](../../artifacts/source-initial-binding-publication-20261015/child-ci-observation.json)
records exact-commit run `38661325944`: failure with a billing-lock annotation,
zero hosted steps and no hosted gate pass. No workflow dispatch or rerun was
requested. These hosted results are separate from the local passing gates.

The new increment uses the existing fixed datasets checkout at
`f4a823231ad52c9252504810a1b00ed4738346b6` and kit checkout at
`40c98c71b95be750509ffdb21e7e5494d91b4e79`. The prior separate 45-case datasets
API result remains historical evidence; its count is not added to this run.

Child evidence lives at
`docs/agent_supervisor/evidence/source-initial-binding-20261015/` in the accelerator
repository. Parent evidence lives in
[the publication artifact directory](../../artifacts/source-initial-binding-publication-20261015/).

## Relation to the autoformalization work

This publication preserves the incoming source, research and model assets. It
performs no model loading, training, embedding regeneration, checkpoint upload or
ModelManager promotion. CodebaseIR, IntentIR, LegalIR, SecurityIR and UI/UX IR
remain separate families, with independent 8D/384D/768D, schema/version and decoder
task identities. The recorded F17 reconstruction experiment is research evidence,
not a qualified 384D teacher or a successful 768D distillation. Exact source
retrieval and exact legal-text/semantic-IR reconstruction remain separate metrics.

The bounded review also found a separate direct-host lifetime identity gap:
the gateway can accept an internal equal-binding genuine reader substitution
between requests because its generic binding assertion checks the current slot,
rather than the permanent publication witness. Existing native task/allocation/
broker joins reject that replacement, and in-flight queries pin the literal
reader. This is a direct-host follow-up, not a new native-claim bypass. Its
proposal and a separate worker-permission/provenance proposal remain unimplemented
and have no passing test counts assigned to them.

The broader remaining work includes compiled worker context and signed scope
adoption, formal proof-cache authority, qualified semantic reconstruction and
measured end-to-end supervisor token use. This increment makes source binding
safer while retaining those explicit evaluation gates.
