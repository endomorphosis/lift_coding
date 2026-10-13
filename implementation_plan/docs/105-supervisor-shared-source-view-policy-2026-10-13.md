# Shared source-view policy across inventory, reading and edits — 2026-10-13

The supervisor now has an explicit owner policy that makes historical inventory,
source reading and mapped editing agree on regular `.py`/`.pyi` files and
caller-protected physical lines. The edit adapter consumes the reader's checked
candidate projection instead of independently choosing a suffix/protection
recipe. This closes the first implementation gap in the indexed-reading plan;
model-facing discovery and policy transport remain separate next increments.

Accelerator `a3b26502d23d8a267ae64c04715bbf21c6113859` is published to `origin/main`, preserving
parallel source-view read/edit measurement at
`85b21ded006fa9850ab49ee9f33bd320457a79a5` and the existing model work.

- [Policy API and compatibility](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a3b26502d23d8a267ae64c04715bbf21c6113859/docs/agent_supervisor/reversible_source_views.md#share-an-explicit-policy-across-owner-apis)
- [Qualification, source custody and independent review](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a3b26502d23d8a267ae64c04715bbf21c6113859/docs/agent_supervisor/evidence/shared-source-view-policy-20261013/README.md)
- [Updated comprehensive plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a3b26502d23d8a267ae64c04715bbf21c6113859/docs/agent_supervisor/reversible_codebase_views_plan.md)
- [Prior reading audit](103-supervisor-context-reading-plan-2026-10-13.md)
- [Parallel scripted read/edit measurement](104-supervisor-source-view-read-edit-pair-2026-10-13.md)

The immutable policy detaches caller maps and binds canonical configuration,
resolver implementation and unchanged codec identity. Source inventories retain
Git modes; owner reads independently require safe regular files. New inventory
roots and owner admissions explicitly use version 2. Shared baseline/working
pages use versions 3/4 and discovery version 2. Working generations and
continuations bind the policy through their source scope. Host application
receipts use version 2 and retain the policy digest.

Existing default root, codec manifest and worker wire identities are preserved.
The current closed client/broker handles the legacy policy and refuses new host
pages; this does not silently activate new model tools or mapped mutation.
Runtime archive capability now requires the resolver dependency's exact hash,
including missing/changed/copied-feature refusal controls. Current preparation
requires an archive rebuilt against the new source.

The owner accessor validates the whole captured source population against the
pinned generation before projection, brackets filesystem/currentness checks and
checks retained view/map identities. Coherently changed cached originals/views,
policy drift, stale generations and foreign source paths refuse. Explicit
protected lines remain physical coordinates; same-line retained edits are
supported, and the mapper keeps its conservative newline-change refusal.

Qualification passed 798 collected and executed tests across 23 selected targets,
including 52 new shared-policy cases, with zero failures, errors or skips. All
103 recorded source bindings (74 accelerator and 29 datasets dependencies)
were unchanged before and after execution. The codec, pure mapper and legacy
client/broker bytes match the preceding accelerator baseline. Independent static
review approved the integration after the cached-source, strict-type and runtime
packaging findings were resolved. Its 29-file datasets comparison is scoped to
those dependencies, rather than claiming complete revision equivalence.

The qualification executes immutable datasets
`f47161b757190380e9898aff155067c1ad609217`. Parent datasets pin
`b95938c2a816075466f8dc84f339cf622414030d` is a separate reference, without a
claim to execute that revision. No model/provider calls, training, Docker,
solver or official task verifier were run. Existing family/schema/decoder-task
8D/384D/768D checkpoints, embeddings and database owners are untouched.

The parallel authored read/edit experiment remains 79,362 versus 79,229
displayed bytes, 133 fewer; it had zero model calls and no native token score
or official reward. It is preserved rather than rerun or relabeled as a saving
from this policy change. Complete-session token benefit remains unverified.

All four exact child Documentation Gates workflow blocks passed locally. Manual
checks also passed 69 relative links and nine anchors across the three changed
guides and the new phase README. The public manifest binds 23 changed source,
test, guide and evidence files, excluding itself; private runtime state is not
published.

The [hosted CI observation](../../artifacts/shared-source-view-policy-publication-20261013/hosted-ci.json)
records the exact child separately: run
`38333015290`, job `115086793012`, completed failure before any runner steps;
the fresh annotation reports the account billing lock. This is not a hosted
execution of the successful local gates.

The parent changes only this note, public validation receipts and the accelerator
Gitlink. It preserves datasets `b95938c2a816075466f8dc84f339cf622414030d` and kit
`8ac00bb1974b1378e12091d546d8425af34049e0`.

The [parent validation receipt](../../artifacts/shared-source-view-policy-publication-20261013/parent-checks.json)
binds this note, the hosted observation, published child manifest and staged pins.
