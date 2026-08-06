# SCA Formal-First Improvement Plan

**Status:** formal_first_enablement live (2026-08-06) — **8-lane** supervisor; **ENABLE-DOCTOR/RPR/UIR completed** (doctor bridge + RPR admission + UIR mapping); ENABLE-CLOSE blocked only on SCA-221  
**Date:** 2026-08-06  
**Program:** SwissKnife Symbolic Contract Assurance (`SCA-`)  
**Board:** `implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md`  
**Profile:** `config/swissknife_symbolic_contract_assurance_supervisor.json`  
**Runtime:** `data/agent_supervisor/swissknife_contract_assurance/`

## 1. Intent

Improve the SCA program so that **formal verification, static analysis, and
deterministic doctor/planner repair** carry most contract work, and **LLMs
are used only after** those layers admit a bounded, counterexample-first
packet. Reorder the board so the **enablement gaps for that stack are
selectable first**, then restart the SCA supervisor on that tranche only.

Secondary intent: SwissKnife **UI** drift (web apps, virtual UI, ORB surfaces)
should be repaired primarily by:

1. UI/UX IR formal round-trips and projection adapters (`UIR-` program),
2. Static AST/call-graph mismatch findings,
3. Proof-gated contract repair (RPR / doctor / hammers),

not by open-ended Grok/Codex edits over large UI trees.

## 2. Diagnosis (current board)

### 2.1 Scale and shape

| Metric | Approx. value |
|--------|----------------|
| SCA tasks | ~437 |
| `completed` | ~97 |
| `todo` | ~317 |
| `blocked` | ~20 |
| `active` | ~3 |

Open work is **dominated by LLM-shaped repair fan-out**:

- Track `parser-failure-row-verification`: **~258** open tasks  
- Track `parser-failure-fan-in` / cluster repair: smaller but still LLM-bound  
- Formal/proof/ZK/index enablement tasks: **~20–35** open (sparse vs noise)

The board therefore **selects noise over capability**: the supervisor burns
retry budget on parser-row verification and implementation repair before the
pipelines that would make repair automatic are fully wired.

### 2.2 Objective heap already names the right hierarchy

The objective tree already places formal stack under SCA-G060–G090 and
production readiness under SCA-G180–G182:

```text
SCA-G020/021  AST + index
SCA-G030/031  Typed graph + GraphRAG/Cypher
SCA-G040–043  Contract catalog + surfaces
SCA-G060–062  Logic IR + provers
SCA-G070–071  Trust-aware proof cache
SCA-G080–082  ZK policy + real backend
SCA-G090–091  Mismatch analyzer
SCA-G100–101  Bounded CodeEditPacket + repair board
SCA-G180–182  Solver/ZK readiness + production authority
```

Many of these goals are **reopened or provisionally complete with
contradictions**, so objective scan keeps re-emitting gap tasks (SCA-6xx)
while 258 parser-row todos sit at equal priority.

### 2.3 Authority model is already correct on paper

`swissknife_symbolic_contract_assurance_supervisor.json` already states:

| Source | Authority |
|--------|-----------|
| Kernel proof | authoritative when exactly bound |
| Real ZK | attested only under approved policy |
| Solver candidate | candidate only |
| Static analysis / tests | observation |
| LLM output | **proposal_only** |
| Simulated ZK | non-attested |

The gap is **operational selection and wiring**, not doctrine.

### 2.4 What we have built since the SCA seal (integration targets)

These are the new surfaces this plan assumes we bind into SCA:

| Capability | Location / program | Role for SCA |
|------------|--------------------|--------------|
| Deterministic doctor / tactician / hammers | `agent_supervisor/control/*doctor*`, `proof/goal_directed_tactician.py`, doctor tests | Analytical repair transforms, impact closure, fixed-point |
| Proof-gated contract repair (RPR) | `AGENT_SUPERVISOR_PROOF_GATED_CONTRACT_REPAIR_PLAN.md`, `code_contract_prover.py`, `contract_repair_task_source.py` | Broken path → admitted target → packet without LLM write authority |
| Formal planning / prover matrix | `AGENT_SUPERVISOR_FORMAL_*`, `formal_verification_*` | ATP/SMT/kernel routing |
| Multi-prover / datasets logic | `ipfs_datasets_py.logic.external_provers`, hammers, CEC, TDFOL, ir_core | Obligation prove/refute + reconstruction |
| Trust-aware proof cache | formal_verification_cache / TrustAwareProofCache | Exact invalidation + hit re-derivation |
| Proof reuse / cold surfaces | accelerate PTR + cold package root (#124–#126) | Hermetic validation without provider thrash |
| UI/UX IR (UIR) | `45-ipfs-datasets-ui-ux-ir.*` (~60 completed) | Formal UI IR, FOL/F-logic/event calculus, MCP-IDL/ORB projection |
| Swissknife virtual UI bindings | `src/handsfree/swissknife_virtual_ui.py` | ORB/virtual desktop control surfaces as first-class contracts |
| Grok-quota Terra gate | accelerate #126 | Keep residual LLM lanes fail-closed and quota-correct |

## 3. North-star operating model (after this plan)

```text
SwissKnife tree + MCP++/runtime surfaces
        |
        v
[1] Exact snapshot + AST index + multi-root surfaces   (static)
        |
        v
[2] Call/effect/contract graph + UI/UX IR projection     (static/formal IR)
        |
        v
[3] Obligation compilation (Logic IR) + solver route     (provers)
        |
        v
[4] TrustAwareProofCache + optional real-ZK attest       (cache/attest)
        |
        v
[5] Mismatch analyzer → typed finding + impact closure   (static)
        |
        v
[6] Deterministic doctor / hammers / RPR transforms      (no LLM)
        |
        v
[7] Bounded CodeEditPacket ONLY if [6] abstains          (LLM proposal)
        |
        v
[8] Re-index, re-prove, post-merge validation            (proof-first)
```

**Hard rule:** no SCA implementation task with `provider role: grok-implement`
may become selectable unless its packet is bound to a current counterexample
from [5] and [6] has recorded `analytical_abstention` or `transform_applied`.

## 4. Board redesign principles

### 4.1 Priority bands (replace flat P0/P1 noise)

Assign every SCA task a **band** (new field or encode in Priority):

| Band | Name | Selectable when | LLM? |
|------|------|-----------------|------|
| **B0** | Platform enablement | Always first | Prefer deterministic-only |
| **B1** | Symbolic production path | After B0 blockers clear | No LLM for prove path |
| **B2** | Structured repair (doctor/RPR) | After B1 mismatch path live | Optional LLM only on abstain |
| **B3** | Parser-row / UI cosmetic | After B2 admits packets | LLM allowed but packet-bounded |
| **B4** | Ops / hygiene | Parallel, low weight | N/A |

**Immediate action:** demote all `parser-failure-row-verification` tasks to
**B3** and set `Depends on: SCA-ENABLE-CLOSE` (or concrete SCA-645 + SCA-221 +
SCA-218) so they are **not selectable** until the formal path is green.

### 4.2 Freeze rules (supervisor config)

Add to `swissknife_symbolic_contract_assurance_supervisor.json`:

```json
"selectionPolicy": {
  "phase": "formal_first_enablement",
  "allowTracks": [
    "snapshot", "ast", "ast-index", "graph", "contracts", "mismatches",
    "proof-orchestration", "proof-readiness", "zk-backend", "zk-policy",
    "zk-readiness", "production-graphrag", "datasets-graph", "provider-index",
    "runtime-baseline", "runtime-catalog", "runtime-proof", "analyzer-health",
    "actual-surface-composition", "production-index-graph", "ui-ir-binding",
    "doctor-bridge", "formal-enablement"
  ],
  "denyTracks": [
    "parser-failure-row-verification"
  ],
  "denyTracksUntilTaskCompleted": {
    "parser-failure-row-verification": "SCA-ENABLE-CLOSE",
    "parser-failure-fan-in": "SCA-ENABLE-CLOSE",
    "parser-failure-cluster-repair": "SCA-645"
  },
  "maxOpenLlmImplementationTasks": 1,
  "requireCounterexampleBindingForLlmTasks": true,
  "requireDoctorAbstentionOrTransformForLlmTasks": true
}
```

Until config schema supports this natively, implement as:

1. Board field `Depends on` / `Selection phase: formal_first`,
2. Lane inventory filter in `scripts/swissknife_parallel_implementation_supervisor.py`,
3. Objective scan exclusion for tracks in `denyTracks`.

### 4.3 Task template for formal-first work

Every B0/B1 task should declare:

- `Implementation mode: deterministic_only` when possible  
- `Provider role: none | codex-review-only`  
- `Validation:` pytest + prover CLI + cache round-trip (no “looks good”)  
- `Re-proof command:` exact command the supervisor re-runs after merge  
- `UI relevance:` `none | virtual_ui | web_apps | orb` (for later projection)

## 5. Enablement tranche (do these first)

This is the **ordered** work the restarted supervisor should execute. Existing
SCA IDs are preferred; new IDs are proposed only for missing joins.

### Phase A — Static foundation (no LLM)

| Order | Task / goal | Outcome | Existing IDs |
|------:|-------------|---------|--------------|
| A1 | Exact snapshot + coverage | Clean tree authority | SCA-641 / SCA-G010, SCA-185/198 |
| A2 | Polyglot AST + incremental index | Whole-tree index generation | SCA-651, SCA-652, SCA-225 |
| A3 | Multi-root provider index | accelerate/kit/datasets/MCP++ surfaces | SCA-625 |
| A4 | Reviewed contract catalog + actual surfaces | Expected vs extracted | SCA-653, SCA-604, SCA-642 |
| A5 | Typed call/effect graph | Program graph for repair | SCA-643 / SCA-G030 |
| A6 | Datasets GraphRAG + Cypher AST binding | Context-only retrieval | SCA-626, SCA-605 |

**Exit A:** One authoritative index generation with analyzer health **passed**
(not missing). Objective SCA-G020/G021/G040 no longer reopened solely for
missing analyzer health.

### Phase B — Prover and proof path (no LLM for prove)

| Order | Task / goal | Outcome | Existing IDs |
|------:|-------------|---------|--------------|
| B1 | Solver readiness fail-closed | Capability probe + typed blockers | SCA-606 |
| B2 | Logic IR obligations + prover binding | Claims compile to obligations | SCA-G060–G062, related todos |
| B3 | Prover + proof cache + mismatch wiring | End-to-end prove/refute path | SCA-218, SCA-618 |
| B4 | Contract mismatch analyzer | Deterministic findings | SCA-645 / SCA-G090 |
| B5 | ZK policy + ProveKit gate | No simulated ATTESTED | SCA-646, SCA-607, SCA-219/623 |
| B6 | Production authority gate | Mandatory child receipts | SCA-621, SCA-G180–G182 |

**Exit B:** For a fixture suite of N MCP++/UI contracts:  
`prove | refute | unsupported | inconclusive` with **zero** LLM calls, and
cache hits re-derive assurance.

### Phase C — Deterministic repair (LLM optional)

| Order | Task / goal | Outcome | New / existing |
|------:|-------------|---------|----------------|
| C1 | **SCA-ENABLE-DOCTOR** Bridge doctor/tactician/hammers into SCA findings | Finding → analytical transform or abstention receipt | **NEW** |
| C2 | **SCA-ENABLE-RPR** Bind proof-gated contract repair task source | Admitted target decision before any implement lane | **NEW** (align RPR board) |
| C3 | Project mismatches to bounded packets | CodeEditPacket schema only | SCA-221 / SCA-G100–G101 |
| C4 | Cluster parser failures (not row-by-row) | Collapse 258 rows → cluster repairs | SCA-233–237 then fan-in |

**Exit C:** `SCA-ENABLE-CLOSE` completable: doctor path live, LLM path gated.

### Phase D — UI surfaces under IR (after C)

| Order | Work | Outcome |
|------:|------|---------|
| D1 | **SCA-ENABLE-UIR** Bind UIR IR as SwissKnife UI contract authority for web/virtual/ORB apps | UI claims compile through UI/UX IR, not free-form TS review |
| D2 | Map `swissknife/web/js/apps/*`, virtual UI, ORB bindings to UIR components | Projection adapters + round-trip tests |
| D3 | Release parser-row / UI cosmetic B3 tasks | Only with packets from C3 |

**Exit D:** SwissKnife UI repairs prefer UIR-constrained synthesis; LLM sees
IR + counterexample, not full app sources.

## 6. New tasks to add to the SCA board (proposed text)

Add these **before** restarting the supervisor. Place them at the top of the
todo file after SCA-000 (or under a new section `## Formal-first enablement`).

### SCA-ENABLE-000 Seal formal-first selection phase

- Status: todo  
- Priority: P0 / Band B0  
- Track: formal-enablement  
- Depends on: SCA-000  
- Goal id: SCA-G001  
- Outputs: this plan; updated supervisor profile `selectionPolicy`; lane
  inventory phase flag  
- Validation: `python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json`  
- Acceptance: Config and board declare `phase=formal_first_enablement`;
  parser-row track not selectable.  
- Implementation mode: deterministic_only  

### SCA-ENABLE-001 Demote parser-row and freeze LLM implementation

- Status: todo  
- Priority: P0 / Band B0  
- Depends on: SCA-ENABLE-000  
- Effects: All `parser-failure-row-verification` tasks set
  `Depends on: SCA-ENABLE-CLOSE` (or equivalent gate); priority demoted to B3.  
- Validation: script counts zero **ready** tasks in denied tracks  
- Implementation mode: deterministic_only  

### SCA-ENABLE-DOCTOR Bind deterministic doctor into SCA repair path

- Status: todo  
- Priority: P0 / Band B0  
- Track: doctor-bridge  
- Depends on: SCA-645 (or provisional mismatch analyzer)  
- Goal id: SCA-G100  
- Outputs: adapter module under `agent_supervisor` or SCA runtime that maps
  `ContractFinding` → doctor/tactician plan → transform receipt or abstention  
- Validation: unit tests with fixture finding; zero model calls  
- Interfaces: DeterministicDoctor service, goal_directed_tactician, hammers  
- Conflict policy: Do not weaken proof authority; doctor cannot mint kernel proof  

### SCA-ENABLE-RPR Bind proof-gated contract repair selection

- Status: todo  
- Priority: P0 / Band B0  
- Track: doctor-bridge  
- Depends on: SCA-ENABLE-DOCTOR, SCA-218  
- Goal id: SCA-G100  
- Outputs: SCA profile hooks to `contract_repair_task_source` / RPR admission  
- Acceptance: Implementation daemon rejects LLM tasks without admitted target
  decision + current snapshot binding  

### SCA-ENABLE-UIR Bind UI/UX IR for SwissKnife UI contracts

- Status: todo  
- Priority: P0 / Band B1  
- Track: ui-ir-binding  
- Depends on: SCA-643, SCA-ENABLE-DOCTOR  
- Goal id: SCA-G030 (extend) + UIR-G000  
- Outputs: mapping table SwissKnife UI modules → UIR IR; validation that
  unsupported UI fragments are `unsupported` not silent pass  
- Acceptance: At least one SwissKnife web app and `swissknife_virtual_ui`
  binding round-trip through UIR formal views or explicit unsupported  

### SCA-ENABLE-CLOSE Formal path gate for B3 work

- Status: todo  
- Priority: P0 / Band B0  
- Depends on: SCA-ENABLE-000, SCA-ENABLE-001, SCA-ENABLE-DOCTOR, SCA-ENABLE-RPR,
  SCA-218, SCA-645, SCA-606, SCA-221  
- Acceptance: Documented checklist green; `selectionPolicy.phase` may move to
  `symbolic_repair`; parser-row tasks become selectable under packet rules only  

## 7. Integration architecture (how pieces join)

```text
                    ┌─────────────────────────────┐
                    │ SCA scanner / refill (lane0) │
                    └──────────────┬──────────────┘
                                   │ findings
           ┌───────────────────────┼───────────────────────┐
           v                       v                       v
   AST/index/graph          UI/UX IR projector      Runtime contract probes
   (accelerate+SK)          (datasets UIR)          (model/orch/sched/sup)
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   v
                        Obligation compiler (Logic IR)
                                   │
                    ┌──────────────┼──────────────┐
                    v              v              v
                 SMT/ATP        Hammers      Kernel/ZK (if ready)
                    │              │              │
                    └──────────────┼──────────────┘
                                   v
                         TrustAwareProofCache
                                   │
                    prove | refute | unsupported | inconclusive
                                   │
                         Mismatch analyzer (SCA-G090)
                                   │
                    ┌──────────────┴──────────────┐
                    v                             v
           Deterministic doctor              Abstention receipt
           transforms / RPR target           │
                    │                        v
                    │                 Bounded LLM packet (optional)
                    └────────────┬───────────┘
                                 v
                    Re-index + re-prove + merge validation
```

### 7.1 Planner / doctor

- **Planner:** proof-carrying / adaptive / formal replanner choose **which
  obligation or impact set** to work next — not free-form feature inventing.  
- **Doctor:** applies **analytical** repairs (imports, renames, schema
  defaults, test symbol maps) when the impact graph admits a unique transform.  
- **Tactician/hammers:** attempt logic reconstruction before any model.  

SCA should treat doctor output as `transform_receipt@1` evidence, same
schema family as proof receipts where possible.

### 7.2 UI/UX IR

Map SwissKnife UI layers:

| SwissKnife surface | UIR role |
|--------------------|----------|
| `swissknife/web/js/apps/*` | Web projection adapters |
| Virtual desktop / ORB | `SwissknifeVirtualUIBinding` / ORB plane |
| MCP control / P2P network UIs | Control-surface + Intent IR mediation |
| Glasses / mobile (MGW) | Capability-constrained projection (later) |

Contract claims about UI behavior should compile to UIR IR + logic views
(UIR-G030) so refutation is structural, not “LLM read the React tree.”

### 7.3 Theorem provers / formal verification

Bind SCA `symbolicProviders.logic` to live capability probes:

- Fail closed if SMT/ATP/hammer not ready (SCA-606).  
- Route obligations via `multi_prover_router` / `code_contract_prover`.  
- Never promote solver **candidate** to kernel assurance without
  reconstruction policy already in datasets doctor logic tests.  

## 8. Board surgery procedure (concrete steps)

Execute in order; commit each step so the supervisor can resume.

1. **Write** this plan (done as this file).  
2. **Patch** `config/swissknife_symbolic_contract_assurance_supervisor.json`:
   - add `selectionPolicy` (or equivalent),
   - set `mode` from `shadow_first` → `formal_first_enablement` until
     SCA-ENABLE-CLOSE,
   - optionally lower lane count to 2 for enablement (reduce thrash).  
3. **Patch** `config/swissknife_symbolic_contract_assurance_lane_inventory.json`
   to only schedule B0/B1 shards.  
4. **Board edit** `44-…todo.md`:
   - insert SCA-ENABLE-* tasks,
   - bulk-update `parser-failure-row-verification` tasks: add dependency on
     `SCA-ENABLE-CLOSE`, set `Priority: P3` / band B3, set
     `Selection phase: deferred_until_formal_path`,
   - raise Priority of Phase A/B tasks listed in §5 to P0.  
5. **Objective heap** `44-…objectives.md`:
   - add goals SCA-G200 Formal-first enablement, children for doctor/RPR/UIR
     bridges,
   - mark SCA-G000 gap task to prioritize G060–G090 and G180 before G100 LLM
     repair volume.  
6. **Script** `scripts/sca_formal_first_ready.py` (new):
   - exits 0 only if enablement checklist green (index health, prover probe,
     mismatch fixture, doctor dry-run).  
7. **Stop** any running SCA multi-lane supervisors cleanly.  
8. **Restart** with formal-first profile (see §9).  
9. When SCA-ENABLE-CLOSE completes, flip phase to `symbolic_repair` and allow
   cluster (not row) parser repairs.  

## 9. Supervisor restart recipe

```bash
# 1) Stop existing SCA lanes (example; adjust to your process manager)
# pkill -f swissknife_parallel_implementation_supervisor || true
# pkill -f swissknife_contract_assurance || true

# 2) Verify formal-first config
python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null
python3 scripts/sca_formal_first_ready.py --expect-phase formal_first_enablement || true

# 3) Launch only enablement-capable lanes (sketch)
python3 scripts/swissknife_parallel_implementation_supervisor.py \
  --profile config/swissknife_symbolic_contract_assurance_supervisor.json \
  --selection-phase formal_first_enablement \
  --lanes 2 \
  --deny-track parser-failure-row-verification
```

**Merge target** remains `agent/swissknife-sca-parallel` until formal path is
stable; then consider promoting proof-only merges with stricter post-merge
validation (already tightened on accelerate main).

**Provider routing during enablement:**

- Implementation: `deterministic_only` preferred; Grok only for admitted
  packets after C.  
- Review: Codex on non-deterministic changes only.  
- Terra fallback: use post-#126 quota gate; never unrestricted Codex implement.

## 10. Success metrics

| Metric | Before (now) | Target after enablement |
|--------|--------------|-------------------------|
| Ready tasks in parser-row track | high | 0 until SCA-ENABLE-CLOSE |
| LLM implementation attempts / day | high | ≤ 1 concurrent; only packet-bound |
| Fixture contracts resolved without LLM | low / unknown | ≥ 80% of supported fragment |
| Analyzer health on SCA goals | often `missing` | `passed` on index generation |
| Doctor/RPR abstention rate | N/A | tracked; falling as transforms grow |
| UI repair context tokens median | large | ≤ packet median target (2k) |

## 11. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Demoting 258 tasks hides real bugs | Keep them on board; run **cluster** repairs (SCA-233–237) after B1; do not delete |
| Formal path never closes → UI frozen | Time-box Phase A/B (e.g. 1–2 supervisor days); escalate only blocked probes |
| Doctor over-repairs | Transforms require proof/re-index fixed point; merge still serial |
| UIR not covering all SwissKnife UI | Explicit `unsupported` dispositions; no silent pass |
| Objective scan re-floods gap tasks | Pin scan exclusions during formal_first; clear cooldowns only for B0/B1 |

## 12. Out of scope (this plan)

- Full bulk port of UIIR `post_merge_review` live module  
- Completing all 258 parser-row tasks individually  
- Replacing SwissKnife product design via LLM  
- Weakening CID / proof authority to “make green”  

## 13. Recommended next actions (execution order)

1. **Approve** this plan (this file).  
2. Implement **SCA-ENABLE-000/001** board+config surgery (no code features yet).  
3. Restart supervisor in **formal_first_enablement** with 2 lanes.  
4. Land **SCA-ENABLE-DOCTOR** and **SCA-ENABLE-RPR** adapters.  
5. Close **SCA-ENABLE-CLOSE**; open cluster repairs + UIR binding.  
6. Only then allow broad SwissKnife UI LLM repair under packet rules.

## 14. References

- SCA board: `implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md`  
- SCA objectives: `implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md`  
- SCA profile: `config/swissknife_symbolic_contract_assurance_supervisor.json`  
- UI/UX IR: `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md`  
- Proof-gated repair: `external/ipfs_accelerate/docs/architecture/AGENT_SUPERVISOR_PROOF_GATED_CONTRACT_REPAIR_PLAN.md`  
- Tactician/hammer: `external/ipfs_accelerate/docs/architecture/AGENT_SUPERVISOR_TACTICIAN_HAMMER_LOGIC_REPAIR_PLAN.md`  
- Deterministic doctor guide: `external/ipfs_accelerate/docs/guides/DETERMINISTIC_DOCTOR_GUIDE.md`  
- Browser UI board (completed): `implementation_plan/docs/39-swissknife-browser-compatibility-followups-2026-07-08.todo.md`  
- Virtual UI: `src/handsfree/swissknife_virtual_ui.py`  

---

**End of plan.** Ready for board surgery + supervisor restart when approved.


## 15. Execution log

### 2026-08-06 — Board surgery applied

- `config/swissknife_symbolic_contract_assurance_supervisor.json`: `mode=formal_first_enablement`, `selectionPolicy` added, lanes=2.
- Board: inserted SCA-ENABLE-000 (completed), SCA-ENABLE-001 (completed), SCA-ENABLE-DOCTOR/RPR/UIR/CLOSE (todo).
- Demoted open parser-failure-row / fan-in / cluster-repair tasks: Priority P3, `Depends on` includes SCA-ENABLE-CLOSE, Selection band B3.
- Objectives: added SCA-G200 formal-first enablement.
- Script: `scripts/sca_formal_first_ready.py` (phase + demotion checks pass).
- **Next:** stop any running SCA multi-lane supervisors; restart with formal-first profile (2 lanes).
