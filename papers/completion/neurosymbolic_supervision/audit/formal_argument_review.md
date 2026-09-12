# NS-023 Formal argument review

Reviewed 2026-09-12 against Equation 2, §7.3, §I.3.1–I.3.3, and Algorithm 1 in
`papers/completion/neurosymbolic_supervision/paper_extracted.txt` (SHA-256
`809af88bfd4e8f78fc7fbc7c067dc5d41392c6c2d4aaf75ec02ec813036a23a4`). The
restated statements live in
`papers/completion/neurosymbolic_supervision/manuscript/formal_arguments.tex`.
The assumption-to-gate map lives in
`papers/completion/neurosymbolic_supervision/audit/assumption_gate_map.json`.

This review is an independent argument check. It does not treat reconstructed
prose, Algorithm 1's narrative, or isolated passing tests as theorems. It does
not initiate universal-Python proof work. It does not call a prover: the sealed
validation `PATH` `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin` has no
`z3`, `lean`, `coqc`, or `cvc5`. Every sketch remains **unmachine-checked**.

Qualification evidence consulted (caller-level, not A–D experiments):

| Gate family | Record | What it can support |
|---|---|---|
| Translation / checker / nonvacuity | NS-009 `logic_report.md`, `logic_profiles.json` | Lossy-projection rejection, unknown/timeout/unsupported distinct from proof, vacuous implication rejected, Z3 absent |
| Provider / permission / route | NS-008 `provider_gate_report.md` | Deterministic progress, residual only with typed receipts, deny-all not useful progress, `closes_claim` untrusted |
| Fixture / reuse identity | NS-010 `reuse_adapter_report.md`, `reuse_profile.json` | Fail-closed lookup, lifecycle teardown, mutation invalidation; **not** cold-oracle closure |
| Sealing / CAS / restart | NS-012 `sealer_recovery_report.md` | Completeness ≠ membership, exclusive expected-parent CAS, restart continuation; **not** external exactly-once |
| Integrated cycle | NS-013 `end_to_end_witness.json` | One guard-before-write executed composition |
| Native proving | NS-014 `native_scope_decision.md` | Unavailable profile |
| Extensions | NS-015 `extensions_report.md` | No retained world/procedure/refactoring claim |
| Cold-oracle reuse | NS-011 | **Absent.** No `cold_oracle_results.jsonl` and no `receipts/NS-011.json` |

NS-016–NS-020 (frozen runs and independent scoring) are not used. This task
does not invent those results.

## 1. Method

For each formal statement the review records:

1. Precise scope (what objects and transitions are in the claim).
2. Premises (including trusted limitations).
3. Conclusion.
4. Whether the argument is valid *as a conditional implication*.
5. Whether any implementation evidence supports a premise, and only that premise.
6. What must remain undischarged (unknown specs, incomplete projections,
   unlocated mechanisms, missing campaigns).

Validity here means: if the premises hold, the conclusion follows. It does not
mean the premises hold of arbitrary Python, of the whole repository forest, or
of untested write paths.

## 2. FA-EQ2 — acceptance invariant (Equation 2)

**Scope.** One accepted-lineage publication `Publish(s')` under a declared
artifact policy. Not all writes in the process; not Git plus task-database plus
remote services as one transaction.

**Premises.** Current parent, actor authorization, actor scope, complete
requirement manifest, admitted evidence for every required obligation, and
expected-parent compare-and-swap.

**Conclusion.** Publication implies the conjunction of those gates. The
converse is not claimed.

**Independent argument.** As a definitional invariant the implication is valid:
if the publication operation is the unique successor constructor and it
conjoins those checks, every published root has passed them. That is a
conditional design invariant, matching claim C-17 in the NS-003 ledger
(`conditional_design`; publication rule: state initial-policy, exact-input,
exclusive-publication, and trusted-effect assumptions with mapped gates).

The reconstructed sentence “a conditional preservation argument is possible”
is therefore acceptable *as a sketch*, and unacceptable if read as “current
code universally enforces Equation 2” or “side effects occur exactly once.”

**Call-chain consistency.** NS-012 exercises
`IncrementalProofSealer` (`sealer.py`, SHA-256
`9618561ddda1d53b9368ea220ceeff13c7149986d8d49641b78e6623a3a22fed`) with
`EvidenceVerifier.verify_for_admission` (`admission.py`, SHA-256
`16fcc43f52f41641abf297e36e0850e87394fdcfac2c9c0807ada19e4cd9cb4b`) and
`create_full_checkpoint` / `aggregate_verified_units`. Observed dispositions
that match the gates:

- `incomplete_manifest` for empty, missing, duplicate, and membership-only sets.
- `stale_parent` for superseded parents; exactly one concurrent CAS winner.
- `proof_failed` / `simulated_only` / `unknown_proof_system` refuse publication.
- Post-CAS crash recovers the new pointer; pre-CAS crash leaves the old pointer.

`IpfsKitDurableStateAdapter.compare_and_swap_root` (`durable_state.py`, SHA-256
`e718a115671f7d84fc7f5c693c8ef03d4216465d71e79fad04adf2442a277a9f`) is the
operational CAS surface used with a generation token. NS-012 records that
nested `proof_seal_store` is absent from the pinned kit tree and that a labeled
hermetic WAL/CAS shim was installed. The invariant is therefore tested on that
sealer call chain, not on a released kit pin and not on every other persist
API.

**Not inferred.** External exactly-once side effects; federation; global
consensus; that every code path that can write a pointer is this sealer.

## 3. FA-I31 — accepted-lineage induction (§I.3.1)

**Scope.** Roots reachable *solely* through the accepted publication
transitions of FA-EQ2, under a fixed profile Θ and policy predicate PΘ.

**Premises.** Initial-root policy; verified subject bytes and dependency
references; complete manifest; designated checker relation; translation bound;
current parent; exclusive publication; protected policy/checker identities.

**Conclusion.** Every such reachable root satisfies PΘ.

**Independent argument.** The induction is valid on a successor relation that
contains only CAS-linearized successful publications, provided:

- PΘ is checked on the exact bytes that become the new root, not on a proxy.
- The identities that define PΘ cannot change between that check and CAS.
- Completeness and checker relations used in the check are the same as in PΘ.
- No other write path introduces a “reachable” root.

If any of those fail, the sketch does not apply. The draft already excludes
properties omitted by PΘ, truth of unsupported translations, honest signed
observations, and atomicity of external side effects. Those exclusions are
retained; they are not discharged by induction.

**Base case (initial-root policy).** NS-013 publishes from parent seal
`ips.forest.genesis@1` with policy
`sha256:f711f00ed99912349c04196f2348905f2c299cb72fccdef83b03154cc0339f39`.
That genesis is a trusted starting root, not an independently proved interesting
PΘ. The induction therefore *assumes* the initial root; it does not prove it.
Disposition: **trusted limitation** plus one tested publication from that root.

**Inductive step.** NS-012's `stale_parent`, `exactly_one_concurrent_cas_winner`,
and completeness rejections support the claim that failed or stale attempts are
not successors *on the tested sealer*. They do not prove that this sealer is
the sole publication operation in the loaded forest. Disposition of
sole-publication-path: **trusted limitation**.

**Protected authority.** `ReferenceAuthorizationEvaluator` (NS-008/NS-013)
separates permission from publication. NS-013 records that a denied `mallory`
request does not persist writes and that residual dispatch without typed
receipts remains `missing_typed_resolvable_authority_receipts`. NS-015 records
that no extension may self-promote or edit protected validators. Ordinary
worker authority changing PΘ is not a tested positive path; it remains a
protected-authority assumption.

**Nonvacuity.** Deny-all publication would satisfy the invariant vacuously.
NS-012 and NS-013 supply a positive complete-manifest publication
(`sha256:1776714283057d562d41664641edbdaf36dd1fccae7b77d872368a630a5c7b73` in
NS-013; sealer CID `sha256:25180cd72df48fc18f236e9d36799c35b9c9dc765da65bf3cc206cedfd8eab7a`
in NS-012 sequential/parallel preparation). NS-008 records
`deny_all_not_useful_progress`. The sketch is therefore non-vacuous on the
tested call chains.

**Not a machine-checked theorem.** No Lean/Coq/Isabelle artifact exists. The
review does not start one.

## 4. FA-I32 — dependency-projected test reuse (§I.3.2)

**Scope.** Transfer of a previous setup/call/teardown observation under a
declared runtime/effect profile θ.

**Premises.** A complete projection πD and a deterministic fθ such that
Obsθ(t,s) = fθ(πD(s)) on every state the reuse policy admits.

**Conclusion.** Equal projections imply equal observations, so a previous
observation may transfer only inside that profile.

**Independent argument.** The implication is valid as function application. It
is vacuous as a software theorem unless completeness and determinism of πD are
established. The draft correctly names that as the hard obligation. Two equal
digests of incomplete manifests do not satisfy the premise. Definitions of
fixture names without values, function coverage without plugins/clocks/network
or teardown, and runtime traces without a closed identity are insufficient.

**Call-chain consistency.** NS-010 qualifies `TestProofCache.lookup` and
`ProofCachedTestValidation` on constructed locators/keys/receipts plus live
identity APIs:

- Collection seeds never authorize skip (`may_authorize_skip=false`).
- Unchanged eligible reuse: `SKIP` / `proof_cache_hit` for receipt
  `baguqeerazrfpi6jrmof7phetw2w3pxpkjhnuxa4jwibxyfiwnhenllha3ljq`.
- Fixture, plugin, conftest, runtime-trace, external-snapshot, and policy
  mutations force `RUN`.
- Teardown failure blocks `admitted=True` and cannot skip.
- Incomplete traces, uncontrolled fixture values, and opaque objects fall back
  to `RUN` or reject. They are **not** treated as equal projections.

Those results support fail-closed *identity mismatch* and lifecycle rules.
They do **not** prove that the execution key is a complete observational
projection for arbitrary pytest, clocks, networks, databases, or unmodeled
plugins. Universal dependency closure is therefore **not inferred**.

**Cold oracle.** NS-010 explicitly assigns independent cold full-run scoring
and mutation rates to NS-011. This workspace has no `cold_oracle_results.jsonl`
and no NS-011 receipt. The reuse argument cannot silently treat cold-oracle
agreement as discharged.

**Not inferred.** Universal πD completeness; Groth16 proof that pytest
executed (cache verifier is a local authoritative callback over retained
bytes); matched A–D reuse effectiveness.

## 5. FA-I33 — three acceptance questions (§I.3.3)

**Scope.** Any candidate described as accepted.

**Premises / conclusions.** Behavioral correctness, action permission, and
publication are different questions. A positive answer to one is not an answer
to the others.

**Independent argument.** This is a type distinction, not an induction. It is
valid and is the right reading of the architecture:

| Question | Tested gate | Supporting record |
|---|---|---|
| Behavioral claim | Independent pytest / designated checker; `closes_claim` ignored | NS-008 `closes_claim_not_independent_success`; NS-009 kernel vs solver classes; NS-013 pytest exit 0 on the fenced worktree |
| Action permission | `ReferenceAuthorizationEvaluator` | NS-008 `authorization_permit_execute` / `authorization_deny_task_scope`; NS-013 alice permit / mallory deny |
| Publication | Complete-manifest expected-parent CAS | NS-012 / NS-013 `incomplete_manifest` and `simulated_only` cannot complete |

The reconstructed remark that reference pre-dispatch code uses an in-memory
consumption ledger is retained as a limitation on durable real-tool
authorization. NS-013's authorization surface is the reference evaluator on a
frozen qualification task, not a production identity provider.

## 6. Nonvacuity, unknown, and inconsistent specifications (§I.2)

Unknown, timeout, unsupported, and unavailable solver outcomes are distinct
from proof (NS-009). Unsatisfiable G making G⇒A true is recorded as
`vacuity_unsat_guarantee` and rejected as proof. Unknown is not inconsistent
and not proved. Mutating axioms to close a proof would be a new authorized
specification change; no such automatic repair is claimed.

These rows prevent the acceptance arguments from silently discharging unknown
or inconsistent specifications. They do not make the specifications complete.

Unlocated draft mechanisms remain **unavailable**, not simulated success:

- QF_LIA interpolating CEGAR adapter
- interpolant checker
- `CompositionEdge`
- cyclic assume-guarantee closure
- incremental SMT wrapper
- Z3 SAT/UNSAT (binary and module absent)

## 7. FA-ALG1 — Algorithm 1 composition label

Algorithm 1 is an intended control-flow specification. Isolated stop-path tests
do not establish the complete loop.

The NS-013 witness is one integrated guard-before-write cycle on task
`baguqeerayjn2552ymrf3qtqjbvfe43q5yequcbhmowkmaazqaabyo5xuntxq`. Mapping to
Algorithm 1:

| Witness step | Algorithm 1 line | Composition label |
|---|---|---|
| `capture_state` / `state_obligation` | 1 (partial) | Qualification freeze of F, policy, obligation; **not** live event-service reconcile |
| `plan_bounded_repair` | 4 | Executed on the frozen task |
| `choose_reasoning_route` | 7 (deterministic) | Executed: `medium_model` → `deterministic_only` after bound source/proof |
| residual without receipts | 7 / 8 | Rejected: `missing_typed_resolvable_authority_receipts`; **not** a production residual-model execution |
| `validate_candidate` | 9 | Executed: `IsolatedPatchWorktree`, caller root unchanged |
| independent pytest | 10–11 | Executed as independent checker, not worker pass-claim |
| `reuse_narrowly` | 11 | Executed: `proof_cache_hit` on an unchanged eligible receipt |
| `incomplete_cannot_complete` / `simulation_labeled_qualification` | 13 | Executed negatives |
| `seal_and_publish` | 14, 16 | Executed complete-manifest CAS |
| NS-012 stale parent / restart | 15 (sealer only) | Tested on the sealer, **not** as Algorithm 1 event-service reconcile |
| `learn_without_self_approval` | 17 | Negative: no self-promotion; **not** executed procedure/policy learning |
| budget/cancel, wait-or-review, residual production model, native proof, federation, A–D | 2, 5, 7 residual, 8, 12, world/procedure | **Intended only** |

The algorithm is therefore labeled **intended composition**, with
**executed composition** only where the NS-013 witness (and the NS-012 sealer
faults that witness reuses) support it. It is not labeled as a newly executed
implementation result of the full loop.

## 8. What implementation evidence must not be used to infer

| Forbidden inference | Why it is forbidden | Recorded disposition |
|---|---|---|
| External side-effect atomicity | WAL/CAS/lifecycle is a local boundary | NS-012 limitation; FA-EQ2 / FA-I31 trusted-effect assumption |
| Universal dependency closure | πD completeness is unproved; NS-011 absent | FA-I32 undischarged |
| Universal Python correctness | Hashes, solvers, and checkers have bounded statements | C-ABS-03; no universal proof work started |
| Silent discharge of unknown specs | Unknown ≠ proved | NS-009 `unknown_not_proved` |
| Silent discharge of inconsistent specs | Vacuous G⇒A rejected | NS-009 `vacuity_unsat_guarantee` |
| Silent discharge of incomplete projections | Incomplete traces RUN | NS-010 `incomplete_trace` |
| Native Groth16 of pytest | Profile unavailable | NS-014 |
| World/procedure consumption | No retained extension | NS-015 |
| Matched A–D efficacy | Unrun | Not this task |

## 9. Publication recommendations for NS-022

1. Keep Equation 2 and §I.3.1 worded as conditional design invariants with the
   mapped assumptions visible.
2. Keep §I.3.2 as a proof obligation. Do not promote NS-010 cache hits to
   universal reuse soundness or to a false-reuse rate.
3. Keep the three questions separate in any “accepted” wording.
4. Label Algorithm 1 as intended composition except for the NS-013 executed
   subset listed above. Do not convert the schematic Table 6 cycle into a live
   A–D result; NS-013 already replaced schematic R0/P0/T0 with recorded IDs
   for that qualification witness only.
5. Do not start a universal-Python formalization campaign to “complete” these
   sketches. Unmachine-checked status is the correct scientific label.

## 10. Reviewer judgment

The restated arguments in `manuscript/formal_arguments.tex` are valid
conditional implications with precise scope. Implementation evidence from
NS-008, NS-009, NS-010, NS-012, and NS-013 supports only the tested premises
named in the assumption-gate map. External side-effect atomicity and universal
dependency closure are not inferred. Unknown specifications, inconsistent
vacuous implications, incomplete projections, unlocated solvers, unavailable
native proving, and the missing NS-011 cold oracle remain undischarged.
Algorithm 1 is labeled executed composition only on the integrated witness
subset.
