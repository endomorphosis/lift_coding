# Native worktree admission for exact source retrieval — 2026-10-12

The original Quack owner can now join its existing native task admission to the
genuine database-to-Portal projection, active managed-worktree record and exact
task/attempt index before serving source. This closes the allocation-ownership
gap left by [native task admission](97-supervisor-native-source-task-admission-2026-10-12.md).
The host independently supplies its admitted repository, workspace, roots,
merge target and board namespace; matching source bytes or a clean checkout
alone do not establish this ownership.

Accelerator implementation `48f442b4ca468b8cf2e858bca72a676812344302` is published
to `origin/main`.

- [Allocation API and limits](https://github.com/endomorphosis/ipfs_accelerate_py/blob/48f442b4ca468b8cf2e858bca72a676812344302/docs/agent_supervisor/current_source_worktree_allocation.md)
- [Qualification evidence](https://github.com/endomorphosis/ipfs_accelerate_py/tree/48f442b4ca468b8cf2e858bca72a676812344302/docs/agent_supervisor/evidence/current-source-worktree-admission-20261012)
- [Existing source-worker channel](93-supervisor-current-source-worker-retrieval-2026-10-12.md)
- [Preserved selective candidate capsules and obligations](98-supervisor-selective-candidate-context-2026-10-12.md)

The guard retains the original task-admission handle, connection and owner. It
reconstructs the existing Portal binding from the actual current task and native
attempt, verifies the distinct Portal canonical task identity, and checks the
live daemon kernel birth against the lifecycle owner. The allocated checkout
must be the registered linked Git worktree in the admitted canonical repository,
with the expected branch, state directory, lane, merge target and encoded native
attempt. Native task CIDs, Portal task CIDs, database claim leases and worktree
lifecycle leases remain separate identities.

An allocation-marked source reader requires the same exact private allocation
and task handles in the optional worker broker. Serialized observations are
inert. The existing task binder lock spans the empty-reader check, publication
and allocation marker attachment. A refused second bind cannot adopt or remark
an existing reader. Source binding remains consumed once; a late failure can
leave an actually published reader for the original owner's cleanup, without
implying rollback or permission to rebind.

Complete Portal projection/binding and registered Git controls retain their
byte and physical identities. Even a byte-identical replacement refuses. The
lifecycle owner, lease, record and task/attempt fields stay fixed; fence, update
time and expiry may advance monotonically through a genuine same-owned renewal.
Renewal replaces lifecycle and index files individually, so a concurrent
renewal can make a sequential observation refuse and require a retry. This is
not an atomic filesystem lease or transaction across the stores.

The worker broker checks the native claim and allocation around each source
read. A detached allocation check follows the coordinator callback; closing
source-byte checks follow closing custody checks. Successful native backend
envelopes are charged before a later refusal, including lifecycle loss at the
closing clock callback. A refusal therefore does not imply zero incurred bytes.
Native coordinator metadata/event/expiry bookkeeping and its existing
metadata-repair limitation remain; this is not a zero-write observer or a
pre-repair integrity proof. Direct privileged SDK reads retain their generic
currentness checks; additional claim/allocation fencing belongs to this
optional broker path.

All **118 distinct host tests passed**, with zero failures, errors or skips:
31 new allocation cases, five native lifecycle controls and 82 retained
task/source/typed-owner cases. All 37 recorded direct source/test bindings stayed
fixed, with normal pytest plugins and fresh collection/execution AST seals.
The first run passed without a corrective rerun. Its fixture uses real task
materialization, typed Unix grants and admission, native claims, retained source
CAS and Portal projection, followed by actual `begin_preparing`, Git worktree
creation and `mark_active` in their native order. Host provisioning protects the
existing authority paths before capture; the guard creates no allocation or
changes any permissions. Its task read facades reuse the original connection
with schema installation disabled.

The native daemon object runs in the test owner's process. Quack listener
lifecycle/capability and deployment metadata are authored seams. This phase
does not exercise a separate daemon child, coding-worker UID or live supervisor
START, make model/provider/prover calls, run an official task verifier, or
establish a token saving or semantic reconstruction improvement. Existing
source-worker Docker qualifications retain their own scope; they do not
automatically qualify this new allocation guard.

Parallel accelerator publication `06a437cdba28e148912d998bf2cb85a805a3d4d9` was
merged after the passing host run. Its 68 changed paths do not intersect the
37 qualified direct bindings. The shared reversible-view plan merged cleanly;
selective candidate-context results and their historical qualification remain
preserved separately. This comparison does not establish a new combined Docker
or provider run.

The parent preserves datasets `e39fe996bd9e786a84f739fda9dde9a6c70546da` and kit
`8ac00bb1974b1378e12091d546d8425af34049e0`. Qualification used retained datasets
`f47161b757190380e9898aff155067c1ad609217`; the six directly compared retained-source
producer files and complete `software_contracts` Git subtree match the preserved
datasets pin. This bounded comparison does not qualify unrelated datasets
changes or the complete parent. Existing LegalIR, SecurityIR, CodebaseIR and
IntentIR inventories, embeddings and decoder checkpoints remain separate by
family, schema/version, decoder task and 8D/384D/768D profile. No model is
retrained, embedding regenerated or prior asset removed by this phase.

The remaining production sequence is:

1. Retain the original runtime's actual source CAS and inventory supplier,
   then provision the admitted allocation policy explicitly. Qualify ordinary
   single-lane coordinator selection: the current task guard requires the
   process-serialized adapter, which ordinary single-lane daemon execution does
   not automatically select. Preserve the original owner and source assets.
2. Join the original runtime's actual daemon bootstrap receipt and active grant
   to this allocation handle, exact current task body and compiled worker
   context/prompt. Reject crossed attempts, stale contexts and historical
   inventory or semantic-scope identities used as native task substitutes.
3. Add a closed owner-mediated handoff at the real coding launch boundaries.
   Register the actual coding-child kernel birth after `Popen` and before
   prompt delivery, with explicit acknowledgment and failure cleanup. The
   original Quack owner and native daemon launcher are different processes;
   registering the daemon as a broad descendant root would admit unrelated
   coding children and does not satisfy this contract.
4. Qualify that handoff through the deployed helper and separate worker UID,
   including revoked/expired claims, foreign allocations, changed prompts,
   PID reuse, disconnect, restart and post-birth refusal with incurred cost.
   Keep required facts inline until this production path has passed. Native
   source restart/rebinding and edited working overlays need explicit successor
   lifecycles rather than relaxing the clean committed-source profile.
5. Preserve the separate unverified working-source and candidate-context
   refresh paths. Rebuild affected semantic capsules and pending obligations
   selectively, retain unsupported/unknown coverage, and validate mapped
   compact edits against retained original preimages and exact replay. Accepted
   DuckDB/DuckLake proof/index publication must invalidate changed dependencies
   and require independently verified evidence; retrieval and allocation checks
   do not turn pending formulas into proofs.
6. Run matched, balanced complete supervisor sessions with planning enabled and
   native provider routing. Include initialization, catalog discovery,
   expansions, translation tables, refreshes, retries and repairs in the token,
   latency and cost ledger, while retaining original official task rewards.
   Compare compact views, selective capsules/obligations and exact-source
   expansion against the same tasks and assets. Selected formal artifacts can
   still exceed their source bytes; only complete native usage establishes a
   practical token benefit.

All four local documentation workflow blocks and final integrated guide/evidence
anchor checks passed. The exact-commit hosted documentation job did not start:
GitHub reported an account billing lock, with runner ID zero and no steps. Run
`38319835171`, job `115045003943` and the exact annotation are retained in the
[CI observation](../../artifacts/source-worktree-admission-publication-20261012/hosted-ci.json).
This infrastructure failure remains separate from the passing local checks.
