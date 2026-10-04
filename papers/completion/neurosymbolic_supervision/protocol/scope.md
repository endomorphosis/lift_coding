# Frozen submission scope — NS-003

Status on 2026-09-11: this is a scope-control record, not a result, deployment, author-attestation, or submission record. The authoritative claim ledger is `audit/claim_evidence_matrix.json`.

## Submission thesis and required core

The candidate paper may claim a bounded *method*: state-bound semantic context, obligation-aware routing, evidence applicability, lifecycle-aware reuse, and parent-bound publication are a proposed composition whose useful progress and safety must be tested against a fixed independent oracle. It may not claim that the composition improves repair, cost, safety, or deployment readiness until the frozen, independently scored experiment supports the exact statement.

The required core is deliberately smaller than the draft's program of work:

- Semantic context and invalidation must be qualified on the actual source-linked consumer, including unknown-frontier fallback and source-preserving repair parity (NS-007).
- The real caller must show both authorized residual progress and safe rejection of stale/missing/mismatched evidence; a deny-all route and a candidate boolean are not success (NS-008).
- The retained translation/checker profile must demonstrate loss-aware boundaries and name its solver/checker semantics (NS-009).
- A retained reuse claim must bind collection through teardown and be independently cold-scored against unchanged and adversarially mutated cases (NS-010--011).
- Publication claims must cover complete manifests, CAS/fault/restart reconciliation, and a valid continuation after recoverable failure (NS-012--013).
- The final empirical core is matched A--D conditions, frozen before outcomes, plus independent scoring. It retains failures, abstentions, timeouts, unavailable routes, and unsolved cases in the denominators (NS-004--006 and NS-016--020).

Before final data exist, language for these items is limited to a specification, source inspection, or qualification target. `NS-002` permits the narrow fact that particular source surfaces and repository-reported preliminary artifacts were inspected; it does not establish live integration or efficacy.

## Fixed scientific boundary

The paper goal cannot be met by reducing work rather than producing evidence. In particular:

- The acceptance oracle, hidden target/acceptance material, source-task population, budgets, terminal-state meanings, and A--D matching rules are frozen in the preregistration before final outcomes. Any material protocol revision before that freeze receives a versioned rationale and does not silently relabel an outcome.
- Queue exhaustion, no model invocation, a successful local hook, a stored CID, a `closes_claim` flag, or a resolved plan is not an accepted solution. A solved task requires the frozen independent acceptance decision and current mandatory evidence.
- Full denominators include accepted, rejected, false-accepted, false-denied, failed, timed-out, abstained, unavailable, and unsolved attempts as applicable. An unavailable measurement is `null` with a reason, never a zero or omitted row.
- Unsafe controls that disable an admission check are confined to an adversarial harness with publication disabled. Reuse is compared with a cold full runner that is unavailable to proposal generation.
- Table 17 reports package comparisons until prespecified one-factor ablations support component-level wording. It does not turn C or D into evidence for every constituent mechanism.

## Optional campaigns and truthful closure

The following campaigns are not prerequisites for an evidence-backed core paper. Their default closure is explicit narrowing, not an implementation race.

| Area | Retained only if | Otherwise required closure |
|---|---|---|
| Native Groth16 / theorem or circuit profile | NS-014 records a real backend, circuit, key/setup provenance, verifier, adversarial cases, and measured costs | Mark Table 18 native row untested/unavailable/out of scope; remove performance, execution-proof, and deployment claims. Do not fabricate proof-shaped records. |
| Learned world model, incoming memory, procedures | NS-015 has a frozen learned artifact where applicable, held-out family/time evaluation, controls, consumption evidence, independent validation, and rollback | Preserve the prior learned-artifact no-go; state planned future work, not a measured benefit. |
| Semantic editing, CST/AST relinking, architecture refactoring | A bounded profile has resolver/renderer/round-trip/adversarial evidence and independent preservation checks | Treat as future work; a source map, fewer files, or smaller graph is not equivalence evidence. |
| Federation and remote faults | A named tested deployment exercises the relevant authority/fault boundary | Limit publication claims to the tested local profile; do not imply distributed consensus. |

No optional backend is replaced by a mock, a simulated record, an unavailable capability treated as a negative result, or a weaker oracle. If the default closure is used, `NS-020` and `NS-022` must reconcile the matching Table 18 row and manuscript language.

## Claim classes allowed at this stage

1. **Inspection/provenance:** only source paths, hashes, imports, capability gaps, and the limitations bound in NS-002.
2. **Repository-reported preliminary arithmetic:** Table 5's 40-task/40-transition values only with their existing provenance, estimated/unmeasured labels, and explicit non-live limitations.
3. **Conditional design/protocol:** architecture, equations, evaluation plan, and safety requirements only with assumptions and no operational/effectiveness implication.
4. **Final empirical claims:** only after NS-016--020 freeze, run, independent scoring, and claim-ledger reconciliation.
5. **Author-dependent facts:** author identity, consent, actual model/tool use, artifact-access rights, and disclosure content are outside inference. NS-024--025 must obtain author-confirmable facts or report the precise unresolved input.

## Pre-publication reconciliation rule

NS-022 may retain a main-text statement only if its matrix row is `supported_now`, `conditional_design`, `preliminary_report`, or has its required evidence frozen. Every `narrow_or_remove` item must become an explicit limitation/future-work statement or be deleted. Every Table 17/18 row must either have generated evidence-backed values/witnesses or the matrix's prescribed optional out-of-scope closure. This rule does not authorize submission, publication, consent, or changes to the shared acceptance standard.
