# NS-015 extensions qualification report

Decision on 2026-09-12: **no procedure, world-consumption, or refactoring
extension is retained.** Table 18's required world/procedure consumption row
is **untested / out of scope**. Unevaluated broad W1–W4, graph-learning, and
remodularization claims are narrowed to future work. This optional closure
does not block the measured core.

This report is a source-and-scope qualification. It is not a consumed-result
ledger, a learned-model evaluation, a self-hosting demonstration, or a
manuscript rewrite.

## 1. What was inspected

The task requires resolving source and active-owner status before extending
procedure, world-consumption, or refactoring work. Inspection used:

- Draft claims in `papers/completion/neurosymbolic_supervision/paper_extracted.txt`
  (SHA-256 `809af88bfd4e8f78fc7fbc7c067dc5d41392c6c2d4aaf75ec02ec813036a23a4`).
- NS-003 claim ledger `audit/claim_evidence_matrix.json`, which already marks
  C-13, C-18, and the Table 18 world/procedure row `narrow_or_remove`.
- NS-002 implementation inventory and capabilities.json (prior sealed-profile
  record; **not retested** here).
- Suggested code paths under `agent_supervisor/planning/`,
  `agent_supervisor/autonomous_repair/`, `semantic_state/world_view.py`,
  `semantic_state/world_snapshot_builder.py`, and the missing suggested
  `implementation_plan/proof_grounded_ir_learning_fabric/` directory.
- Frozen PGIR-014 no-go (`freeze/result.v3.json`), campaign input root, and
  tokenizer policy.

A stdlib walk of `*.py` under `external/ipfs_accelerate/ipfs_accelerate_py`,
`external/ipfs_datasets/ipfs_datasets_py`, and `implementation_plan` found
**no** `ProcedureCegis`, `IncomingMemory`, `incoming_memory`, `TAGSeq`, or
`DAGSeq` identifiers. Those tokens appear in the paper extract. Nearby
similarly named modules were recorded and **not** substituted.

No extension module was imported. No training, synthesis, holdout scoring,
or required-mode consumption ran. Hidden A–D acceptance outputs were not
bound or read.

## 2. Retention gate

An extension may be retained only with (i) a located implementation whose
identifier matches the claim, (ii) the independent holdout protocol bound
before evaluation, and (iii) consumed pre/action/post evidence. Every
candidate failed at least the first or third gate. Vacuous satisfaction of
"every retained extension has implementation, protocol, and consumed-result
evidence" holds because the retained set is empty. The holdout protocol is
published as the reopening condition, not as an executed experiment.

## 3. Candidate closures

| Candidate | Located implementation | Holdout executed | Consumed result | Closure |
|---|---|---|---|---|
| ProcedureCegis | No | No | No | specification-only future work |
| Incoming memory | No | No | No | untested future work |
| Learned call/event/inverse/repair models | Adapter only; no frozen learned artifact | Required holdouts insufficient (PGIR-014) | No | preserve prior no-go |
| Architecture refactoring / remodularization | No | No | No | untested future work |
| Required-mode world/procedure consumption | Snapshot query/admission only | No | No paired pre/post | untested / out of scope |
| W1 semantic-addressed world | Partial overlay, unevaluated | No | No | narrowed future work |
| W2 program world | Missing | No | No | narrowed future work |
| W3 broad sealing/TDD campaign | Partial overlay, unevaluated | No | No | narrowed; core fixture lifecycle not closed here |
| W4 semantic refactoring | Missing | No | No | narrowed future work |
| TAGSeq/DAGSeq graph learning | Missing | No | No | preserve prior no-go |
| Federation / multi-agent world roots | Missing | No | No | future work; NS-012 owns deployment wording |

### ProcedureCegis

The draft states that ProcedureCegis already implements a bounded synthesis
state machine (PDF p. 5, §5.3). The exact identifier is absent from Python
source. `FormalAssuranceCegis` is a separately named bounded repair CEGIS
whose certificates do not grant write authority and whose LLMs cannot promote
patches. `ProgramRepairSynthesizer` is proposal-only over reviewed operators
and grants no write, semantic, or proof authority. NS-002 already forbids
substituting those modules for ProcedureCegis.

### Incoming memory

The incoming-memory method (independently admitted trajectories, failed
episodes, applicability, anti-unification on held-out families) has no
matching implementation. `deterministic_failure_memory` is append-only
deterministic repair failure memory, not anti-unification and not held-out
procedure validation.

### Learned candidates

PGIR-014 remains `no_go` / `frozen_no_go` with `training_task_eligible_count`
0. The campaign input root records `training_admitted_rows` 0 and
`rights_quarantined_rows` 7173. The tokenizer freeze policy status is
`no_learned_tokenizer_admitted`. The IR learning campaign planner is a
deterministic adapter that never grants a lease while RESULT identities are
unresolved. The suggested `implementation_plan/proof_grounded_ir_learning_fabric/`
path does not exist. There is no distinct frozen learned artifact to evaluate.

### Remodularization

Appendix E requires SCC candidates, boundary contracts, CST/AST-aware
transforms, independent admission, and exact rollback. A smaller graph or
fewer files does not establish equivalence. No such rewrite was admitted.
The draft already tracks the broader program against the author's local
worktree (§E.4).

### Required-mode consumption (Table 18)

`SupervisorWorldView` is a mutation-free query over one verified snapshot;
immutability is enforced in `__setattr__` / `__delattr__`. Querying a
snapshot is not pre-root consumption. `WorldSnapshotBuilder` admits a
schedulable snapshot from injected authorities; optional DuckLake projection
never grants scheduling authority. Admission is not an accepted post-root.
No paired pre-state / accepted transition / published post-state evidence
was observed. Safe-rejection, valid-progress, and evidence-id fields are
null, not zero.

NS-002 recorded the `semantic_state` package as blocked because `anyio` is
absent in the authoritative-style environment. That prior capability result
is not promoted to a fresh execution.

## 4. Holdout isolation and visible failure modes

The independent protocol (`extension_holdout_protocol.md`) binds, before any
future evaluation:

- Family and time holdouts, frozen before training or synthesis.
- Hidden target patches, acceptance oracles, and final holdout labels.
- Static, history, lexical, embedding, and template controls.
- Applicability failures, abstentions, bad predictions, independent
  rejections, and rollback costs as first-class visible outcomes.
- Negative memory of failed applicability so rejected pairs are not
  silently re-promoted.

Training and synthesis cannot inspect final acceptance outputs under
this protocol. This qualification did not run training or synthesis, and
did not bind or read hidden oracles. Visibility flags in the result records
are protocol requirements, not experimental counts.

## 5. Consumption modes versus shadow writing/reading

World / program-world rollout is
`bootstrap → shadow_write → shadow_read → guarded → required`.
That machine is not interchangeable with W3 sealing gates
(`shadow_hash → shadow_reuse → shadow_proof → protected → required`) or with
refactor/procedure promotion.

- Shadow-write sidecar artifacts do not change authority or complete a task.
- Shadow-read hypothetical scores do not influence behavior.
- Guarded consumption is separately approved and still not required-mode
  completion.
- Required mode needs observed pre-root consumption and post-root
  publication.

Workers may not modify rollout, keys, protected specifications, or their
own acceptance validator. No worker self-promotion. No protected-validator
edits. None of these modes was observed in use; observed mode is `off`.

## 6. Core evaluation is not blocked

Closing the optional campaigns does not empty the core queue or change the
independent oracle. Remaining core work:

- Semantic context and invalidation (NS-007)
- Provider routing gate (NS-008)
- Loss-aware translation (NS-009)
- Fixture/call/teardown reuse (NS-010–NS-011) — the core Table 18 fixture
  lifecycle row, distinct from the unevaluated broad W3 campaign
- Publication/restart (NS-012–NS-013)
- Matched A–D evaluation (NS-004–NS-006, NS-016–NS-020)

NS-012 still owns tested-deployment / federation wording. NS-020 / NS-022
reconcile the Table 18 row and manuscript language against this untested
disposition.

## 7. Publication consequences

Until a retained extension satisfies the reopening conditions:

- Do not claim ProcedureCegis, incoming-memory benefit, learned world-model
  efficacy, graph-learning improvement, or remodularization equivalence.
- Do not claim required-mode self-hosting or paired world/procedure
  consumption.
- Preserve the PGIR-014 learned-artifact no-go.
- Mark Table 18 required world/procedure consumption untested/out of scope.
- Keep applicability failures, abstentions, bad predictions, and rollback
  costs visible if the scope is later reopened; never recode them as success.
- Unavailable or missing evidence remains `null` with a reason, never zero.

## 8. Reopening conditions

Reopen only with all of:

1. An exact located implementation whose identifier matches the claim.
2. A distinct frozen learned artifact when the claim is learned.
3. Held-out family/time splits frozen before training/synthesis, with final
   acceptance outputs hidden from those stages.
4. Static, history, lexical, embedding, and template controls, plus negative
   memory.
5. Independent validation and rollback, with failure modes remaining visible.
6. Guarded or required consumption distinguished from shadow-write/shadow-read;
   no worker self-promotion or protected-validator edits.
7. Paired pre-state consumption and accepted post-state evidence on the
   held-out bounded profile, measuring downstream repair/usefulness rather
   than sidecar logging.

## 9. Claim boundary

This report records a fail-closed optional-extension disposition. It does
not establish live integration, efficacy, semantic preservation, required
self-hosting, or any Table 18 safe-rejection / valid-progress pair for
world/procedure consumption.
