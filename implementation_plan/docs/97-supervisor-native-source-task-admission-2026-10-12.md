# Native task admission for exact source retrieval — 2026-10-12

The exact-source reader can now derive task identity from a live native claim
instead of relying on manually supplied task fields. An owner-private handle
retains the original Quack server, existing process-serialized coordinator and
active owner-attested daemon grant. It reads the actual task alias, revision and
entire canonical body, pins that snapshot and supplies its body CID when binding
the existing source reader. A reader marked by this admission requires the same
private handle in the optional worker broker, which refences reads against the
live claim and daemon grant.

The closing claim check now runs before both closing source checks. If a native
clock callback changes source during that fence, delivery refuses. A validated
backend response remains charged even when a later claim/source check refuses
publication. No token saving, reconstruction metric or formal proof follows
from this source-byte/currentness check.

Accelerator implementation:
`c7e16b122fd931b9a6d385c920eca9abe0f32a5e`, published to `origin/main`.

- [Admission API and limits](https://github.com/endomorphosis/ipfs_accelerate_py/blob/c7e16b122fd931b9a6d385c920eca9abe0f32a5e/docs/agent_supervisor/current_source_task_admission.md)
- [Qualification evidence](https://github.com/endomorphosis/ipfs_accelerate_py/tree/c7e16b122fd931b9a6d385c920eca9abe0f32a5e/docs/agent_supervisor/evidence/current-source-task-admission-20261012)
- [Existing source-worker qualification](93-supervisor-current-source-worker-retrieval-2026-10-12.md)
- [Parallel working-source refresh](94-supervisor-working-source-refresh-2026-10-12.md)
- [Parallel candidate capsule/formula refresh](96-supervisor-candidate-context-refresh-2026-10-12.md)
- [Retained LegalIR curriculum and checkpoint archive](95-legal-matched-temporal-curriculum-2026-10-12.md)

All **82 distinct host tests passed**, with zero failures, errors or skips: 17
new native-admission cases, 21 existing worker channel/router cases, 40 current
source reader/CLI/transport cases and four typed-owner controls. The fixture
uses actual task materialization, route sealing, typed admission/grants,
`DatabaseImplementationDaemon.claim_next()` and its existing native
process-serialized coordinator. Quack listener lifecycle and deployment metadata
are authored seams. This run does not qualify the new guard through a separate
coding-worker UID, automatic allocation or a live model.

Normal pytest plugins and separate collection/execution AST seals were retained;
all 29 recorded direct source/test bindings stayed identical. The initial
permission-related fixture setup failure, exact fixture bytes, logs, commands
and JUnit remain retained beside the passing run. The host explicitly protected
its existing authority files and lane directory; generic Quack startup does not
automatically meet this narrower prerequisite. All four local documentation
workflow blocks and final guide/evidence anchor checks passed. Independent
component and integration reviews found no blocker within this declared scope.

The parent preserves the newer LegalIR datasets pin
`e39fe996bd9e786a84f739fda9dde9a6c70546da`, along with all parallel supervisor
progress. Qualification used retained datasets
`f47161b757190380e9898aff155067c1ad609217`; the six direct source-reader
dependencies and complete `software_contracts` Git subtree match the preserved
pin exactly. This is a bounded dependency comparison, not a whole-parent
regression. Kit remains at `8ac00bb1974b1378e12091d546d8425af34049e0`.
Existing inventories, embeddings and LegalIR/SecurityIR/CodebaseIR/IntentIR
checkpoints remain separate by family, schema/version, decoder task and
8D/384D/768D profile. This phase retrains no model and regenerates no embeddings.

The native coordinator retains its normal bookkeeping/event/expiry writes and
can repair metadata before fencing. The new guard does not establish strict
read-before-repair schema integrity. Source/claim checks are sequential, source
binding is consumed once, and a late failure can leave a published reader for
the original owner's cleanup. Direct privileged SDK reads retain generic
currentness checks; the optional broker supplies the additional claim fence.

The next production handoff needs these concrete joins and refusal controls:

1. Retain the original runtime's actual server and existing source CAS/inventory
   supplier. Capture native task CID, complete body and live claim directly;
   reject historical inventory labels, signed contract CIDs and semantic scope
   IDs as substitutes. Support for ordinary single-lane coordinator selection
   needs its own qualified contract; this component requires the existing
   process-serialized adapter.
2. Authenticate the daemon's real bootstrap receipt and active native grant at
   the original owner. Join the actual allocated worktree lifecycle record,
   canonical repository/source population, native attempt and compiled context.
   Keep lifecycle lease/fence identities separate from the native database
   claim lease/fence. Refuse stale/reused allocations, crossed tasks, mismatched
   full bodies, paths and prompts.
3. Authenticate the actual coding-child birth at the remote launch boundary,
   after `Popen` and before prompt delivery. The original Quack owner and daemon
   launcher are different processes. A closed owner-mediated handoff must join
   the current native claim, admitted allocation, exact prompt and kernel child
   identity, with explicit acknowledgment and cleanup. A daemon PID or broader
   run root cannot replace the coding child or authorize all its descendants.
4. Qualify the deployed helper with that real handoff and a separate worker UID,
   including launch failure, expired/revoked claims, wrong allocations, PID
   reuse, stale prompt/context, disconnect, restart and refusal after incurred
   bytes. Keep required facts inline until this path has actually passed.
5. Keep clean committed-source admission distinct from unverified semantic
   working snapshots. The existing candidate refresh rebuilds session-local
   capsules and pending formulas; accepted DuckDB/DuckLake proof/index publication
   must still invalidate changed dependencies and retain explicit unknown or
   unsupported coverage. Mapped compact edits require retained source preimages
   and exact forward/inverse replay before acceptance.
6. Measure complete planned provider sessions with expansions, refreshes,
   retries and repairs included, using matched balanced comparisons and original
   official rewards. Formal artifacts can exceed source size; selective
   retrieval and complete native usage decide whether the treatment saves
   tokens. Local byte counts, source restoration and pending formulas are
   separate measurements.

The exact-commit hosted documentation job did not start because GitHub reported
an account billing lock, with runner ID zero and no steps. The
[CI observation](../../artifacts/source-task-admission-publication-20261012/hosted-ci.json)
retains this infrastructure failure separately from the passing local checks.
