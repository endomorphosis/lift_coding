# Coding-client source discovery and shared-policy transport — 2026-10-13

The source client can now discover its already admitted baseline paths, then
select compact reads and pinned exact expansion. Owner-selected shared policies
travel through versioned descriptors and requests into baseline/working reads;
workers do not select a policy or broaden source admission. This advances the
[shared owner policy](105-supervisor-shared-source-view-policy-2026-10-13.md)
without claiming complete repository admission or token savings. The parallel
[metadata projection experiment](107-supervisor-metadata-projection-pair-2026-10-13.md)
retains its own native token and task observations without re-execution here.

Accelerator `a9bcde965ac8341719069975dc828c54376961a6` is published to
`origin/main`. Its first parent, `330e35f848e2ed7e3f78b21aae78b98daef70755`,
is the source-discovery revision qualified below. Its second parent,
`d13c68ce80dba65478c87f24ada0669ddfb36a1b`, preserves the parallel guarded
numerical publication that arrived afterward. The parent retains parallel
LegalIR, metadata projection, checkpoint readiness and guarded numerical
publications through `ca97e3703c9d734aa36ace32725ca990e85ca28d`.

- [Client workflow](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a9bcde965ac8341719069975dc828c54376961a6/docs/agent_supervisor/worker_source_views.md#discover-admitted-sources)
- [Qualification and limits](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a9bcde965ac8341719069975dc828c54376961a6/docs/agent_supervisor/evidence/source-view-discovery-transport-20261013/README.md)
- [Comprehensive improvement plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a9bcde965ac8341719069975dc828c54376961a6/docs/agent_supervisor/reversible_codebase_views_plan.md)

Discovery request version 3 returns closed metadata rows with current path,
source/view/manifest pins, sizes and effective profiles. It exposes no source
body or restoration map. The owner compares captured originals and deterministic
projections with retained caches before exporting pins. Discovery continues to
use baseline admission, at most 64 files and 1 MiB total; source edits refuse.
It does not provide a working catalog or widen the target repository's scope.

An owner-supplied policy creates descriptor version 2 with policy and baseline
scope hashes. The client automatically chooses request version 3 and shared
baseline/working page versions 3/4. Legacy request/page shapes are preserved;
downgrade and mixed-policy selections refuse. Candidate-context reads keep their
existing current-generation requirement. The router retains the policy/scope
pins in shared dispatch observation version 2. Standard benchmark selection
still uses its existing profile flag and legacy defaults; a frozen benchmark
shared-policy configuration remains a separate next increment. Existing archive
capability pins cover all six changed runtime modules; current preparation
requires rebuilding the archive against their new hashes.

The collector distinguishes discovery rows from source slices and candidate
artifact bytes while charging full response bytes to the existing session
ledger. Shared audit version 3 requires typed discovery counts. Historical
untyped audits retain an unknown count. Discovery metadata confers no proof,
execution, completion or mutation authority.

The qualified source-discovery pytest invocation passed 1,603 distinct cases across 39 selected
suites, including 79 new discovery/transport cases, with zero failures, errors or
skips. All 166 listed source bindings were unchanged before/after. Two earlier
fixture failures and their original source/logs remain retained. The integrated
runner's original receipt also remains unchanged: its collection-prefix parser
reported metadata failure despite pytest exit 0 and 1,603 successful JUnit cases.
A separate standard-library reconciliation joins the exact log count, unique
JUnit identities and source/datasets/kit guards without rerunning tests. Static
review records the source integration and independent result reconciliation.

The qualification uses a separate immutable datasets checkout at
`afadfbcf8d33a67568c133bb761c43d42a9a133c`, matching the parent pin at the
time of execution and providing the Intent384 checkpoint owner. The later
parent pin `9eb06b73658d8203628a697db6199f14ecf479e4` is preserved, and was
not executed in this qualification. Earlier retained failed
attempts used `f47161b757190380e9898aff155067c1ad609217`; neither earlier
reference pin is relabeled as executed. CLI/socket
fixtures use the real semantic producer, Git worktree, framing, owner-peer
checks and registered descendant lifecycle, with explicit authored single-UID
seams. They do not qualify a new cross-UID container boundary. No model/provider
calls, training, checkpoint inference, Docker, solver or official task verifier
are run. Existing family/schema/decoder-task inventories, weights, embeddings
and database owners remain untouched. Complete-session token benefit is unmeasured.

All four local documentation workflow gates passed, together with 85 relative
links and nine anchors across the changed guides and evidence overview. These
checks belong to the qualified source-discovery revision.

The [merge compatibility receipt](../../artifacts/source-view-discovery-transport-publication-20261013/merge-compatibility.json)
verifies that all 47 owned files, including the complete evidence bundle, are
identical in the published merge and that all 166 qualification bindings match
the qualified Git objects. The late numerical publication changes two of those
bindings: the numerical context consumer and one adjacent test fixture. Its
947 passing cases and two explicit checkpoint-dependent skips remain historical
upstream evidence; they were not rerun here. The 1,603-case run is not a full
regression qualification of the later merged tree. To replay the retained
reconciliation verifier, use a checkout at the qualified source-discovery commit
with its recorded datasets and kit checkouts; the verifier checks current files.
Existing numerical receipts and candidate caches whose producer pins changed
require regeneration under the new revision.

The [hosted CI observation](../../artifacts/source-view-discovery-transport-publication-20261013/hosted-ci.json)
records the exact published child separately: GitHub did not start Documentation Gates because the account is locked due to
a billing issue. This is not an executed hosted gate result; the local gates
passed as recorded above.

This parent publication changes only the note, public validation receipts and
accelerator Gitlink. It preserves datasets
`9eb06b73658d8203628a697db6199f14ecf479e4` and kit
`8ac00bb1974b1378e12091d546d8425af34049e0`.

The [parent validation receipt](../../artifacts/source-view-discovery-transport-publication-20261013/parent-checks.json)
binds the note, hosted observation, published manifest and staged pins.
