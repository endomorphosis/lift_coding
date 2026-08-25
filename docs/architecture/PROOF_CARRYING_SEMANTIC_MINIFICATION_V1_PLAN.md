# Proof-Carrying Semantic Minification v1 — supervisor campaign plan

Program ID: `proof-carrying-semantic-minification-v1`. Short ID: `PCSM`.

## Root objective

Implement proof-carrying semantic minification for Python repository maintenance. Compile relevant source and contracts into canonical semantic IR, select the smallest task-relevant semantic slice, create a tokenizer-efficient model projection with local semantic aliases, accept typed IR patches or typed unresolved questions, deterministically relink admitted M1 edits into the exact current source tree, and use logic, static analysis, selected tests, theorem provers, SMT, CEGAR, interpolation, and proof reuse to validate results and expand only the named missing semantic context.

This is a bounded cross-repository campaign submitted to the existing `ipfs_accelerate_py` supervisor. It is not a new supervisor, planner family, task/event database, model router, proof store, ContextPack family, model server, or generic compiler platform.

## Objective-interface discovery and handoff decision

The bound supervisor source has no callable `supervisor.objectives.submit` or equivalent admitted direct-objective endpoint. `PromptSupervisorService.preview` can elaborate a proposal, but its default service has no independent PlanAdmissionRequest builder and therefore cannot materialize or start it; `Supervisor.run` also fails closed without a `StandardSupervisorRuntimeFactory` and prebuilt complete launch plan. The current canonical executable fallback is the configured-board path: seal this objective heap, plan, task projection, scheduler config, validator, and operator in Git; validate them; materialize exactly one population into `DatabaseTaskSource@1`; start its Quack owner; then launch the existing configured-board supervisor. Materialization is the submission event. This operator repairs only that handoff and does not implement PCSM itself.

## Bootstrap and execution contract

- Execution mode: `execute_with_confirmations`.
- Risk class: `high_assurance_compiler_and_supervisor_change`.
- Required language: Python only for v1; stable language-neutral records are permitted, but no other source language is qualified.
- Initial materialization: exactly 70 tasks.
- Planned named population: 96 tasks.
- Absolute population ceiling: 130 task identities without explicit operator authorization.
- Replan ceiling: 20 epochs; no refill may add more than 10 tasks.
- Frontier-model call ceiling: 130 calls, at most one initial implementation dispatch per admitted task; exhaustion produces a typed unavailable/non-promotion outcome.
- Validation reserve: 40% of token and compute budget, including counterexamples, held-out evaluation, qualification, and audit.
- Four supervisor lanes; DuckDB/`DatabaseTaskSource@1` is task and objective authority, authenticated loopback Quack is the live owner/transport, and DuckLake is optional append-only analytics only.
- `PCSM-119` is the root completion barrier. `PCSM-090` ending the initial materialization must not terminalize the objective.

### Portal repository and receipt scope

`Owning repository` is the Portal filesystem/Git mutation namespace, not the semantic authority named below. Every task uses the Portal root authority `ipfs_accelerate_py` because its output set always includes an outer-superproject receipt and may also include an outer-root-relative path inside one configured nested worktree. A configured nested owner would prefix every output, incorrectly move the outer receipt into that submodule, and double-prefix the already outer-root-relative source paths. The only admitted nested source roots are `external/ipfs_accelerate`, `external/ipfs_datasets`, `external/ipfs_kit`, and `Mcp-Plus-Plus`; receipts remain under `artifacts/proof_carrying_semantic_minification/receipts/`. This common mutation namespace does not transfer canonical semantic, exact-byte storage, or patch-admission authority between repositories.

### Fail-closed refill admission gate

At bootstrap the current `TypedDatabaseTaskSource` cannot admit an objective refill, and Markdown-only objective findings are non-authoritative. The initial 70 tasks are therefore the only executable population until PCSM-080 adds or reuses a closed owner-side PlanDelta admission path before the first below-eight-open-task refill. Each admitted delta must remain within 10 tasks per refill, 130 total tasks, and 20 epochs; report `projection_only_task_count=0`; reseal the exact execution-route policy for the new population; and recycle the four lanes onto that policy. Until this gate passes, `objective_refill_enabled` remains configured for the later qualified path but must fail closed without materializing a refill.

The initial board contains PCSM-000–004, 010–019, 020–028, 030–036, 040–047, 050–057, 060–068, 070–076, 080–085, and 090. Refill 1 admits 091–096 and 100–103 (10); refill 2 admits 104–109 and 110–113 (10); refill 3 admits 114–119 (6). Further remediation tasks must name failed canonical evidence, use `PCSM-R<epoch>-<n>`, and remain within all ceilings.

## Non-negotiable authority boundaries

- `ipfs_datasets_py` owns canonical semantic identity, source/code IR schemas, symbols and lineage, AST/CFG/data-flow relationships, contracts, assumptions, guarantees, invariants, obligations, semantic capsules and slices, qualified rewrites, source/IR link metadata, semantic proof-result relationships, validation, and future training/evaluation examples.
- `ipfs_kit_py` owns exact source, canonical-IR and projection bytes; CID verification; immutable storage; source/alias maps; manifests; root CAS; ContextPack/proof-seal/delta/tombstone/invalidation storage; WAL, recovery, retention, and optional replication. Kit does not judge semantic soundness, proof validity, patch admission, reuse, task completion, or model correctness.
- `ipfs_accelerate_py` owns tier/slice/model/tokenizer/budget choice, semantic expansion, model invocation, typed decoding, deterministic-link admission, selected tests/provers/CEGAR, reuse admission, objective/task state, and promotion/non-promotion.
- A local alias is never canonical identity. The authoritative chain is canonical semantic CID → local projection alias → typed output → canonical semantic CID → exact current-tree node/span.

## Assurance classes

- M1 `LOSSLESS_STRUCTURAL`: the only v1 tier allowed to create an automatically applied mutation. It requires current commit/tree/file CID/source-map identity, exact mutable spans, relevant binding/control/type/call/effect/exception semantics, typed edits, deterministic linking, stale rejection, and preservation of unaffected bytes where supported.
- M2 `SOUND_SEMANTIC_ABSTRACTION`: planning, routing, impact/test/proof selection, contract propagation, and likely-edit discovery. Every summary names derivation, qualified fragment, assumptions, omitted semantics, and completeness witness. Mutation requires exact M1 expansion.
- M3 `LEARNED_SEMANTIC_COMPRESSION`: `experimental_advisory_only`; no execution, proof, release, or blocking authority in v1.

## Canonical records and closed grammar

Reuse current PGIR, ContextPack, software-contract, semantic-state, source-lineage, proof, and compression contracts before introducing any versioned delta. Required conceptual records are `CanonicalCodeIR@1`, `SemanticCapsule@1`, `TaskSemanticSlice@1`, `ModelTokenCostProfile@1`, `ProjectionAliasDictionary@1`, `ProofCarryingSemanticProjection@1`, `SemanticIRPatchPlan@1`, `SemanticProjectionExpansionRequest@1`, `SemanticProjectionValidationReceipt@1`, and `SourceLinkReceipt@1`.

The model grammar is deterministic, versioned, closed, parser-validated, bounded in strings/arrays/nesting, duplicate-key rejecting, and safe-escaping. Model responses are limited to typed PatchPlan, unresolved question, no-change, or refusal/insufficient-context records. Source, comments, literals, logs, tests, and external text are inert untrusted data; no model response or projection is mutation or validation authority.

Alias selection uses the exact provider/model/tokenizer revision and measures token cost, frequency, dictionary and grammar overhead, prefix caching, semantic-anchor value, expansion probability, and ambiguity. Only aliases used by the slice are sent. Natural anchors such as `requests.get`, `pytest.fixture`, `asyncio.Lock`, `DuckDB`, `CID`, `Quack`, `Lean`, and `Z3` are retained when cheaper or semantically useful. Character counts never stand in for token counts.

## Compiler, slicing, linker, and assurance flow

Compile sharded Python AST/CST, CFG, data-flow, calls, reads/writes, effects, exceptions, contracts, proof obligations, source spans, and exact identities. Slice by objective/task, changes, dependencies, callers/callees, tests, proofs, failures, receipts, state transitions, security, and effects. Every slice emits a completeness witness; `eval`, `exec`, monkey patching, dynamic imports/code generation/attributes, unbounded reflection, metaclasses, and framework injection lower assurance and can require M1 expansion, traces, review, or full-source fallback.

The linker resolves alias → canonical CID → current source map; verifies base commit/tree/file CID/node/span; applies only versioned closed operations; rejects overlap, ambiguity, staleness, missing targets, or path escape; formats after rewriting; regenerates changed IR; and produces a SourceLinkReceipt. Initial operations are bounded expression/literal/import/rename/argument/decorator/guard/return/type/error/fixture/schema/config/proof edits and typed-template additions. Arbitrary source replacement, shell commands, unbounded restructuring, and generated-code mutation are excluded.

Formal work is qualified, not decorative: abstract interpretation states domains/assumptions/widening/limits; assume-guarantee substitution requires current admitted guarantees and satisfied assumptions; SMT/theorem receipts bind exact trees; interpolation is independently checked and unsat-core fallback is never called an interpolant; CEGAR expands only implicated facts within bounds; e-graph rules are typed, effect/exception/language/float aware; theorem hammers select facts while an admitted kernel checks proofs. Missing provers remain typed unavailable.

## Semantic paging, invalidation, adapters, and security

Expansion requests name the missing CID/fact/contract/span/counterexample/obligation, insufficiency reason, affected decision, and added-token ceiling. Record expansion precision/recall, false positives/negatives, fallbacks, rounds, tokens, compute, and result. Bound rounds/tokens/capsules, detect repeated expansion hashes, and quarantine nonconvergence.

Repository/tree/source/symbol/interface/schema/contract/proof/test/tokenizer/model/builder/source-map events selectively invalidate affected capsules, slices, aliases, and projections; mtime alone is never freshness evidence. Preserve unaffected capsules/proofs and emit safe deltas.

Expose one implementation through Python, CLI, MCP, and supported MCP++ adapters. External clients may request/explain/expand/validate projections and propose typed patches, but cannot choose authority identities, override freshness, apply/admit patches, bypass policy/tests/proofs, terminalize work, or promote advisory abstractions. Python and generic MCP clients must return the same projection CID for the same canonical request.

Adversarial coverage includes prompt injection in comments/docstrings/literals/test output, forged/colliding/stale aliases, source-map or projection-CID substitution, unauthorized paths, hidden commands, and executable metadata. Required accepted counts for arbitrary execution, prompt authority, path escape, stale admission, alias collision, semantic mismatch, and critical omission are all zero.

## Demonstrations and evaluation

1. Read-only Quack attach-token persistence impact analysis: raw/M1/M2 projections, exact identities, tests/proofs, no mutation, unrelated-doc change, and projection reuse.
2. Bounded mutation replacing one false-success fallback with typed unavailable: M2 plan, exact M1 expansion, typed PatchPlan, deterministic link, static/type/schema/tests/proofs, and receipt chain.
3. Controlled omitted caller contract: first validation fails with named missing region, bounded expansion retrieves only it, second validates, unaffected context stays compressed, and refinement cost is recorded.
4. Stale projection: source tree changes after projection, stale patch is rejected pre-mutation, only affected capsules rebuild, and a new projection plus PlanDelta is emitted. At least one complete demonstration uses a generic MCP client.

Paired routes are raw context, current semantic compression, M1 structural projection, and M2 abstraction with M1 expansion, all on identical trees/tasks/models/acceptance. Corpora contain at least 80 read-only, 60 bounded-mutation, 30 exact historical, a tuning-isolated held-out split, 15 live shadow tasks, and a gated low-risk canary.

Metrics distinguish measured, estimated, simulated, and unavailable: all token components and retries; compiler/slice/alias/projection/storage/model/decode/link/format/type/static/test/prover/CEGAR/wall/CPU/GPU/memory compute; provider and local cost net of compilation/retrieval/validation/proof/audit/retry; correctness, localization, test/proof selection, patch outcomes, semantic equivalence, regressions, link/stale/scope/omission results; compression/reuse/fallback/expansion/refinement/frontier-call results. Missing is never zero.

## Promotion and completion gates

M1 and M2 receive separate closed outcomes. Efficiency targets are at least 50% median input-token reduction, 30% net provider-cost reduction after all overhead, 40% frontier-call reduction, positive held-out/live net cost, under 20% qualified localized full-source fallback, and at least 50% eligible capsule/projection reuse. Quality permits at most two percentage points accepted-patch degradation, no material localization regression, zero selected-test false negatives, 100% admitted M1 link/map consistency, and zero critical omission/scope/stale/alias/identity admissions. Controlled omissions must resolve at least 90% within bounded CEGAR; nonconvergence quarantines. Security counts above remain zero.

Closed outcomes are `promoted_m1_m2`, `non_promoted_unmeasured`, `non_promoted_token_economics`, `non_promoted_quality`, `non_promoted_source_linker`, `non_promoted_context_omission`, `non_promoted_state_freshness`, `non_promoted_security`, `non_promoted_nonconvergence`, and `non_promoted_live_evidence_missing`. Gates are never lowered. M3 remains `experimental_advisory_only`.

Functional completion requires separate canonical IDs/aliases, exact current-tree M1 targets, explicit M2 soundness/completeness, compact reasoning, typed output, deterministic linking, stale rejection, bounded expansion, reuse, complete telemetry, Python/MCP identity parity, external non-authority, current-head tests, held-out and live-shadow evidence or typed absence, closed outcome, and no automatic campaign expansion beyond PCSM.

## Work-package ledger

| ID | Work package |
|---|---|
| PCSM-000 | Inventory current PGIR, ContextPack, compression, proof, and source-map systems |
| PCSM-001 | Seal exact repositories, trees, policies, providers, and baseline |
| PCSM-002 | Inventory existing code IRs, symbol indexes, AST tools, and patch systems |
| PCSM-003 | Inventory current semantic-compression and proof-reuse benchmarks |
| PCSM-004 | Define canonical-versus-projection authority boundary |
| PCSM-010 | Define CanonicalCodeIR contract or select existing authority |
| PCSM-011 | Define SemanticCapsule contract |
| PCSM-012 | Define TaskSemanticSlice contract |
| PCSM-013 | Define ModelTokenCostProfile |
| PCSM-014 | Define AliasDictionary |
| PCSM-015 | Define ProofCarryingSemanticProjection |
| PCSM-016 | Define SemanticIRPatchPlan |
| PCSM-017 | Define ExpansionRequest |
| PCSM-018 | Define ProjectionValidationReceipt |
| PCSM-019 | Add canonical-byte and CID vectors |
| PCSM-020 | Implement Python semantic compiler |
| PCSM-021 | Implement module and symbol identity |
| PCSM-022 | Implement AST and source-span maps |
| PCSM-023 | Implement CFG and data-flow relationships |
| PCSM-024 | Implement read/write/call/effect summaries |
| PCSM-025 | Integrate contracts and proof obligations |
| PCSM-026 | Add dynamic-feature risk classification |
| PCSM-027 | Add incremental changed-region compilation |
| PCSM-028 | Add compiler round-trip and identity tests |
| PCSM-030 | Implement semantic capsule builder |
| PCSM-031 | Implement dependency and reverse-dependency slicing |
| PCSM-032 | Implement test and proof-obligation slicing |
| PCSM-033 | Implement completeness witness |
| PCSM-034 | Integrate current receipts and prior failures |
| PCSM-035 | Add assumption-guarantee capsule substitution |
| PCSM-036 | Add capsule invalidation and delta updates |
| PCSM-040 | Design compact model grammar |
| PCSM-041 | Implement grammar parser and serializer |
| PCSM-042 | Implement tokenizer cost profiling |
| PCSM-043 | Implement alias optimization |
| PCSM-044 | Implement semantic-anchor preservation |
| PCSM-045 | Implement bounded alias-table construction |
| PCSM-046 | Add projection builder |
| PCSM-047 | Add projection receipts and token accounting |
| PCSM-050 | Implement typed IR patch parser |
| PCSM-051 | Implement source-map resolver |
| PCSM-052 | Implement bounded Python linker/rewriter |
| PCSM-053 | Implement formatting and unchanged-span preservation |
| PCSM-054 | Implement stale-tree and stale-map rejection |
| PCSM-055 | Implement semantic-nonempty validation |
| PCSM-056 | Implement scope and path enforcement |
| PCSM-057 | Add linker positive and negative vectors |
| PCSM-060 | Integrate abstract interpretation |
| PCSM-061 | Integrate assume-guarantee validation |
| PCSM-062 | Integrate selected tests |
| PCSM-063 | Integrate incremental SMT |
| PCSM-064 | Integrate qualified Craig interpolation |
| PCSM-065 | Integrate unsat-core fallback |
| PCSM-066 | Integrate CEGAR semantic paging |
| PCSM-067 | Integrate qualified e-graph normalization |
| PCSM-068 | Integrate theorem-prover admission |
| PCSM-070 | Add semantic expansion service |
| PCSM-071 | Add symbol and capsule expansion |
| PCSM-072 | Add source-span expansion |
| PCSM-073 | Add counterexample expansion |
| PCSM-074 | Add test/proof expansion |
| PCSM-075 | Add bounded refinement controller |
| PCSM-076 | Add nonconvergence and fallback behavior |
| PCSM-080 | Integrate projection events with supervisor state |
| PCSM-081 | Add tree and symbol invalidation |
| PCSM-082 | Add projection and alias root CAS through Kit |
| PCSM-083 | Add durable projection storage and recovery |
| PCSM-084 | Add projection reuse and stale rejection |
| PCSM-085 | Add event-driven delta projections |
| PCSM-090 | Add Python API |
| PCSM-091 | Add CLI |
| PCSM-092 | Add MCP adapter |
| PCSM-093 | Add MCP++ adapter where currently supported |
| PCSM-094 | Add cross-client projection identity parity |
| PCSM-095 | Add external-agent patch proposal flow |
| PCSM-096 | Prove external agents cannot apply or admit patches directly |
| PCSM-100 | Build raw-context baseline |
| PCSM-101 | Build current semantic-compression baseline |
| PCSM-102 | Build M1 projection benchmark |
| PCSM-103 | Build M2-plus-M1-expansion benchmark |
| PCSM-104 | Build read-only development corpus |
| PCSM-105 | Build bounded-mutation development corpus |
| PCSM-106 | Build historical replay corpus |
| PCSM-107 | Build held-out corpus |
| PCSM-108 | Add live shadow cohort |
| PCSM-109 | Add low-risk canary cohort |
| PCSM-110 | Run tokenizer and alias benchmarks |
| PCSM-111 | Run read-only paired benchmarks |
| PCSM-112 | Run mutation paired benchmarks |
| PCSM-113 | Run controlled-omission CEGAR benchmarks |
| PCSM-114 | Run historical replay |
| PCSM-115 | Run held-out evaluation |
| PCSM-116 | Run live shadow evaluation |
| PCSM-117 | Run low-risk canary |
| PCSM-118 | Produce promotion or honest non-promotion receipt |
| PCSM-119 | Publish residual-gap and marginal-return report |

`PCSM-118` issues separate M1/M2 outcomes and leaves unavailable evidence visible. `PCSM-119` reports exact commits/trees, board status, contract/grammar/IR/map/linker identities, supported Python versions/features, token/grammar/alias/cost/compute/model-call/reuse/fallback/refinement/link/quality/security results, limitations, and evidence-based recommendations. It may not generate a broader architecture campaign, M3 promotion, tokenizer/model training, or additional-language work.
