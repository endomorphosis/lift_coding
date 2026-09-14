# From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents — implementation taskboard

Read `papers/completion/law_to_action/review.md` and `papers/completion/README.md` before work.
Objective heap: `papers/completion/law_to_action/paper.objectives.md`. Board namespace: `vericodegen-2026-law_to_action`.

Current user-directed scope: `papers/completion/law_to_action/benchmark/AUTOMATED_EVIDENCE_SCOPE.md`. Outside reviewers are not required for manuscript generation or automated evaluation. Earlier human-review requirements remain historical and are superseded only within this explicit amended scope.

All tasks start open. P0 is submission-critical, P1 supports the full study, P2 is optional extension.
Dependencies still apply across priority levels. A blocked experiment remains blocked until run or explicitly rescoped with a recorded claim change.
Never turn estimates, mocks, dry runs, or missing values into measured results.
Implement in native ephemeral worktrees. Coordinate shared library changes through the supervisor merge queue.
Each task must write its receipt using the contract in the runbook; this is provenance validation, not scientific peer review.

## LA-001 Recover or reconstruct editable manuscript and its private source companion

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: 
- Goal id: LA-G1
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G1
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/references.bib, papers/completion/law_to_action/source_recovery.md, papers/completion/law_to_action/private/source_provenance.json, papers/completion/law_to_action/receipts/LA-001.json
- Predicted files: papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/references.bib, papers/completion/law_to_action/source_recovery.md, papers/completion/law_to_action/private/source_provenance.json, papers/completion/law_to_action/receipts/LA-001.json, papers/completion/law_to_action/receipts/snapshots/LA-001/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-001
- Acceptance: Editable main.tex and bibliography compile without requiring an unavailable remote editor.; All sections, tables, equations, footnotes and references accounted for in a reconstruction/recovery audit.; Private author provenance is separated from anonymous artifact files; no fabricated source pins.; Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.
- Paper evidence: p1 anonymous author block; p14 Appendix D lines 504–507; p17 disclosure lines 546–549; manuscript body provided as PDF; local research template/checklist subsequently supplied; User-supplied Overleaf project: https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0 (which paper(s) it contains is unverified; access/authentication pending); Local user-provided research template/style/checklist inspected 2026-09-11; no manuscript-specific .tex or .bib exists under papers/.
- Reuse candidates: papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/law_to_action/receipts/LA-001.json

Check the user-supplied Overleaf project https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0; its paper membership and authenticated access remain unverified, and no source download has been confirmed. Locate authorized local/history manuscript sources, bibliography, figures and exact source-to-code companion. If source cannot be recovered, reconstruct editable LaTeX and bibliography from the PDF and perform a page/section/table/reference discrepancy audit. Unavailable Overleaf or private records must not block independent protocol/code work; list genuinely unavailable provenance fields and scope claims accordingly. The user has now provided local research-format inputs: papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, and papers/checklist.tex. These are formatting/checklist sources, not recovered manuscript text or bibliography; the three manuscript LaTeX/BibTeX sources remain absent. Use the local research shell for any reconstruction, keeping its style unchanged, and preserve the originals. Do not substitute papers/neurips_2026_vericode_workshop_competition.tex, its competition style, or the generic papers/neurips_2026.sty.

Acceptance criteria:

1. Editable main.tex and bibliography compile without requiring an unavailable remote editor.
2. All sections, tables, equations, footnotes and references accounted for in a reconstruction/recovery audit.
3. Private author provenance is separated from anonymous artifact files; no fabricated source pins.
4. Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-002 Audit claims against pinned code and choose the smallest credible evaluated contribution

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: 
- Goal id: LA-G1
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G1
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/claim_evidence_matrix.json, papers/completion/law_to_action/scope.md, papers/completion/law_to_action/environment_inventory.json, papers/completion/law_to_action/receipts/LA-002.json
- Predicted files: papers/completion/law_to_action/claim_evidence_matrix.json, papers/completion/law_to_action/scope.md, papers/completion/law_to_action/environment_inventory.json, papers/completion/law_to_action/receipts/LA-002.json, papers/completion/law_to_action/receipts/snapshots/LA-002/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-002
- Acceptance: Matrix covers each contribution, every logic/backend family, trained normalizer claim and numerical corpus claim.; Explicit OFF/default in-memory-store and fixture-versus-live limitations recorded.; Bounded paper scope, protected routes and essential versus optional experiments are selected.
- Paper evidence: pp1–2 §1 contributions; pp4–8 §§3–8; pp16–17 Appendix F staged/unavailable work
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py, external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/service.py, external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py
- Receipt: papers/completion/law_to_action/receipts/LA-002.json

Map implemented, tested, trained, staged and future-work claims to exact repositories, commits, symbols and tests. Inspect real defaults, adapters, code-effect sources and live backend availability. Focus on generated-code effects and runtime enforcement; keep neighboring papers’ refactoring/sealing scope separate. Remove or downgrade unsupported claims instead of expanding implementation without a benchmark need.

Acceptance criteria:

1. Matrix covers each contribution, every logic/backend family, trained normalizer claim and numerical corpus claim.
2. Explicit OFF/default in-memory-store and fixture-versus-live limitations recorded.
3. Bounded paper scope, protected routes and essential versus optional experiments are selected.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-003 Predeclare benchmark protocol, task populations, leakage controls and run budget

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-002
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/protocol.md, papers/completion/law_to_action/benchmark/protocol.json, papers/completion/law_to_action/benchmark/resource_plan.json, papers/completion/law_to_action/receipts/LA-003.json
- Predicted files: papers/completion/law_to_action/benchmark/protocol.md, papers/completion/law_to_action/benchmark/protocol.json, papers/completion/law_to_action/benchmark/resource_plan.json, papers/completion/law_to_action/receipts/LA-003.json, papers/completion/law_to_action/receipts/snapshots/LA-003/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-003
- Acceptance: Protocol has exact sample-size/repetition values justified by independent units and available resources; no invented power guarantee.; Source derivatives, CVE vulnerable/fixed pairs and skill variants remain in the same split.; Forbidden effects, allowed task success, false denial, abstention and all failures/timeouts have formulas and reporting rules.; Protocol records model/solver availability and compute/provider requirements without assuming paid access.
- Paper evidence: p8 §7 lines 320–327; p16 Appendix E.1 lines 514–523 and E.2
- Reuse candidates: external/ipfs_datasets/tests/benchmarks/logic/test_intent_admissibility_benchmark.py, external/ipfs_datasets/tests/fixtures/logic/admissibility/benchmark/splits.json
- Receipt: papers/completion/law_to_action/receipts/LA-003.json

Specify research questions, source selection, number of independent source families and cases, mutation taxonomy, seeds/repetitions, resource limits and model/tool requirements before collecting outcomes. Define five arms: unguarded sandbox, prompt-only, retrieval+prompt, lightweight policy+UCAN, full enforcement. Separate fixed-action gate comparison from closed-loop agent planning. Predefine metrics, denominators, confidence intervals, exclusions and negative-result handling. If resources are absent, document a narrower still-useful evaluated contribution.

Acceptance criteria:

1. Protocol has exact sample-size/repetition values justified by independent units and available resources; no invented power guarantee.
2. Source derivatives, CVE vulnerable/fixed pairs and skill variants remain in the same split.
3. Forbidden effects, allowed task success, false denial, abstention and all failures/timeouts have formulas and reporting rules.
4. Protocol records model/solver availability and compute/provider requirements without assuming paid access.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-004 Freeze source manifests and reconcile all reported corpus populations

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-003
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/manifests/sources.json, papers/completion/law_to_action/benchmark/manifests/splits.json, papers/completion/law_to_action/benchmark/corpus_counts.json, papers/completion/law_to_action/benchmark/scripts/recount_sources.py, papers/completion/law_to_action/receipts/LA-004.json
- Predicted files: papers/completion/law_to_action/benchmark/manifests/sources.json, papers/completion/law_to_action/benchmark/manifests/splits.json, papers/completion/law_to_action/benchmark/corpus_counts.json, papers/completion/law_to_action/benchmark/scripts/recount_sources.py, papers/completion/law_to_action/receipts/LA-004.json, papers/completion/law_to_action/receipts/snapshots/LA-004/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-004
- Acceptance: Machine-readable manifests resolve every evaluated source and its source-to-IR parent identities.; Count script reproduces cohort counts and explains dropped/unsupported rows.; Source permissions permit included artifact redistribution; otherwise provide lawful retrieval instructions and hashes.; No full-corpus or worldwide-coverage claim is inferred from bounded samples.
- Paper evidence: pp10–11 Appendix A; p16 E.1 lines 514–518
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/processors/legal_data/canonical_legal_corpora.py, external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/cvefixes/source_snapshot.py, external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/source_adapters/skillcenter.py
- Receipt: papers/completion/law_to_action/receipts/LA-004.json

Acquire bounded source cohorts at exact revisions and preserve bytes, URI, hashes/CIDs, source lineage, license/review state, schema and source failures. Recount every population used by the experiment. Preserve exact CVE snapshot d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2 and SkillCenter f9dd4fec3c86d85ebf116c7408ac5ce602c418a1 unless protocol documents a justified revision change. Distinguish physical rows, unique sources, normalized IRs, tombstones, index rows and checked formalizations. Broader un-recounted release statistics remain attributed background or are removed.

Acceptance criteria:

1. Machine-readable manifests resolve every evaluated source and its source-to-IR parent identities.
2. Count script reproduces cohort counts and explains dropped/unsupported rows.
3. Source permissions permit included artifact redistribution; otherwise provide lawful retrieval instructions and hashes.
4. No full-corpus or worldwide-coverage claim is inferred from bounded samples.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-005 Construct and independently review the legal applicability and fidelity gold set

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-004
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/annotations/legal.jsonl, papers/completion/law_to_action/benchmark/annotations/legal_guidelines.md, papers/completion/law_to_action/benchmark/annotations/legal_review_report.md, papers/completion/law_to_action/receipts/LA-005.json
- Predicted files: papers/completion/law_to_action/benchmark/annotations/legal.jsonl, papers/completion/law_to_action/benchmark/annotations/legal_guidelines.md, papers/completion/law_to_action/benchmark/annotations/legal_review_report.md, papers/completion/law_to_action/receipts/LA-005.json, papers/completion/law_to_action/receipts/snapshots/LA-005/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-005
- Acceptance: Every held-out label has source spans, annotator/review provenance and applicability assumptions.; Ambiguous/unsupported cases have explicit unknown labels rather than silently forced permission or denial.; Agreement/disagreement and final adjudication are documented; missing expert review narrows claims and is visibly unresolved.
- Paper evidence: p2 §2.1 lines 61–68; pp10–11 A.1 lines 386–391; p16 Table E1 legal row
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_compiler_api.py, external/ipfs_datasets/tests/conformance/legal_ir/test_legal_ir_compiler_conformance.py
- Receipt: papers/completion/law_to_action/receipts/LA-005.json

Annotate bounded legal provisions for actor/action/modality/object, conditions, exceptions, effective intervals, jurisdiction, authority, definitions, cross-references and exact source spans. Include omitted-exception, wrong-date/jurisdiction, unsupported-construct and no-applicable-record cases. Obtain competent independent human legal review with disagreement/adjudication records; prepare annotation packets autonomously and expose missing reviewer access as a dependency. Never represent generated labels as expert review.

Acceptance criteria:

1. Every held-out label has source spans, annotator/review provenance and applicability assumptions.
2. Ambiguous/unsupported cases have explicit unknown labels rather than silently forced permission or denial.
3. Agreement/disagreement and final adjudication are documented; missing expert review narrows claims and is visibly unresolved.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-006 Complete source-supported CVE pair evidence under the automated scope

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-004, LA-026, LA-027
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl, papers/completion/law_to_action/benchmark/cases/cve_controls.jsonl, papers/completion/law_to_action/benchmark/annotations/cve_review.md, papers/completion/law_to_action/receipts/LA-006.json
- Predicted files: papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl, papers/completion/law_to_action/benchmark/cases/cve_controls.jsonl, papers/completion/law_to_action/benchmark/annotations/cve_review.md, papers/completion/law_to_action/receipts/LA-006.json, papers/completion/law_to_action/receipts/snapshots/LA-006/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-006
- Acceptance: All frozen 12 pairs/24 cases and 84 excluded controls retain exact identities, source/revision bindings and their LA-026 behavior evidence or explicit unsupported/failed status.; Every reported polarity result binds a scoped machine-checkable behavior contract and actual observation. Unknown polarity remains unknown and no independent-human or universal-security claim is made.; No fabricated CVE, mocked source, fabricated reviewer, self-granted authority or unsupported transfer receives empirical success credit. The amended scope and original failed history are retained.
- Paper evidence: pp2–3 §2.2; p11 A.2 lines 409–414; p16 Table E1 CVE row; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/cvefixes/adapter.py, external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/cvefixes/evaluation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_cve_security_e2e.py
- Receipt: papers/completion/law_to_action/receipts/LA-006.json

Use the existing LA-026 evidence for the frozen 12 genuine CVE families/24 cases and preserve all 84 excluded controls. Bind exact vulnerable/fixed revisions, source-row locators and runnable isolated behavior evidence or precisely delimited source-supported observations. Record expected polarity only where an explicit machine-checkable scoped behavior contract supports it, with its provenance distinct from the adapter being evaluated. Otherwise retain unknown and exclude it only from the unsupported metric denominator with a recorded reason. No outside reviewer is required. Do not infer general security, exploitability, or independent human agreement from a source label, fix, compiler output or model judgment. Preserve the original LA-006 failed/blocked attempt and original criteria in history.

Acceptance criteria:

1. All frozen 12 pairs/24 cases and 84 excluded controls retain exact identities, source/revision bindings and their LA-026 behavior evidence or explicit unsupported/failed status.
2. Every reported polarity result binds a scoped machine-checkable behavior contract and actual observation. Unknown polarity remains unknown and no independent-human or universal-security claim is made.
3. No fabricated CVE, mocked source, fabricated reviewer, self-granted authority or unsupported transfer receives empirical success credit. The amended scope and original failed history are retained.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-007 Annotate real SkillCenter intent and malicious-Markdown controls

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-004
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/annotations/skills.jsonl, papers/completion/law_to_action/benchmark/cases/skill_adversarial.jsonl, papers/completion/law_to_action/benchmark/annotations/skill_guidelines.md, papers/completion/law_to_action/receipts/LA-007.json
- Predicted files: papers/completion/law_to_action/benchmark/annotations/skills.jsonl, papers/completion/law_to_action/benchmark/cases/skill_adversarial.jsonl, papers/completion/law_to_action/benchmark/annotations/skill_guidelines.md, papers/completion/law_to_action/receipts/LA-007.json, papers/completion/law_to_action/receipts/snapshots/LA-007/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-007
- Acceptance: Original skill and mutation identities/lineage remain distinguishable.; Independent reference annotations are created before viewing evaluated predictions.; Ingestion never executes source Markdown commands, and false textual authority has explicit expected rejection.
- Paper evidence: p3 §2.3 lines 110–120; p11 A.3; p16 Table E1 skill row
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/source_adapters/skillcenter.py, external/ipfs_datasets/tests/unit/logic/intent_ir/test_skillcenter_source.py
- Receipt: papers/completion/law_to_action/receipts/LA-007.json

Select genuine pinned SkillCenter records and annotate goals, pre/postconditions, guards, effects, verification steps and success/failure/retry/parallel/join control edges with source spans. Tag inferred versus grounded nodes. Add bounded malicious Markdown and fake-permission mutations as clearly synthetic negative controls. Define independent review and record actual normalizer/model revisions; scope learned-component claims if no trained system exists.

Acceptance criteria:

1. Original skill and mutation identities/lineage remain distinguishable.
2. Independent reference annotations are created before viewing evaluated predictions.
3. Ingestion never executes source Markdown commands, and false textual authority has explicit expected rejection.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-008 Implement a reproducible sandbox harness with observed generated-code effects

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-003
- Goal id: LA-G4
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G4
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/run.py, papers/completion/law_to_action/benchmark/handlers/, papers/completion/law_to_action/benchmark/cases/schema.json, papers/completion/law_to_action/benchmark/tests/test_measurement_integrity.py, papers/completion/law_to_action/receipts/LA-008.json
- Predicted files: papers/completion/law_to_action/benchmark/run.py, papers/completion/law_to_action/benchmark/handlers/, papers/completion/law_to_action/benchmark/cases/schema.json, papers/completion/law_to_action/benchmark/tests/test_measurement_integrity.py, papers/completion/law_to_action/receipts/LA-008.json, papers/completion/law_to_action/receipts/snapshots/LA-008/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/cve_security_gate.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_constraint_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/execution_permit.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-008
- Acceptance: One authorized operation produces expected observed effects and a rejected operation produces none.; Reject-all policy is detected by allowed-work metrics.; Harness supports deterministic replay, actual exit statuses/timeouts, unique run IDs and raw trace retention.; Harness smoke checks verify measurement correctness without treating fixtures as empirical benchmark results.
- Paper evidence: p5 §4.1 lines 172–187; p8 §7 lines 298–325; p16 E.2 lines 525–529
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/cve_security_gate.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_constraint_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/execution_permit.py
- Receipt: papers/completion/law_to_action/receipts/LA-008.json

Build the benchmark runner and bounded export/code-generation handlers. Record actual delegate/effect counts, arguments, actor/audience, code/handler effects, roots, grants and observed postconditions. Keep independently extracted code effects separate from agent-declared intent. Enumerate legal/CVE/skill/token/proof/replay/context-mutation cases from the protocol. Persist append-only case-level records with explicit fixture/solver/crypto/storage/network/model labels.

Acceptance criteria:

1. One authorized operation produces expected observed effects and a rejected operation produces none.
2. Reject-all policy is detected by allowed-work metrics.
3. Harness supports deterministic replay, actual exit statuses/timeouts, unique run IDs and raw trace retention.
4. Harness smoke checks verify measurement correctness without treating fixtures as empirical benchmark results.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-009 Execute source-to-IR contract, coverage and scoped behavior measurements

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-005, LA-006, LA-007, LA-008, LA-026, LA-027, LA-028
- Goal id: LA-G3
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G3
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/source_ir/raw.jsonl, papers/completion/law_to_action/results/source_ir/metrics.json, papers/completion/law_to_action/results/source_ir/failure_review.md, papers/completion/law_to_action/receipts/LA-009.json, papers/completion/law_to_action/receipts/snapshots/LA-009/
- Predicted files: papers/completion/law_to_action/results/source_ir/raw.jsonl, papers/completion/law_to_action/results/source_ir/metrics.json, papers/completion/law_to_action/results/source_ir/failure_review.md, papers/completion/law_to_action/receipts/LA-009.json, papers/completion/law_to_action/receipts/snapshots/LA-009/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-009
- Acceptance: Every frozen selected case has an actual prediction/observation or explicit failed, unavailable or unsupported record without changing cohorts after outcomes.; Every reported metric is reproducible from case-level files and an exact scoped machine expectation or observation with independent provenance where the metric requires it. Implementation agreement is not semantic accuracy.; Original source-lineage splits and case denominators remain fixed. Human/author review is not a run dependency, and unmeasured expert legal fidelity or agreement is not assigned a numeric score.
- Paper evidence: p16 Table E1 first three Not run rows; pp2–3 source adapters; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py, external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/typed_compiler.py
- Receipt: papers/completion/law_to_action/receipts/LA-009.json

Run actual pinned source adapters/normalizers/compilers on the unchanged frozen selected sources under the amended automated scope. Report source-span linkage and coverage, parse/schema validity, supported/unsupported fields, compiler/checker consistency, and source-supported CVE behavior observations with exact case denominators and producer provenance. Generated interpretations are predictions, not independent gold. Compare against a reference only for the precisely machine-defined property that reference supports and report shared-producer dependence. Expert legal applicability/exception fidelity, semantic accuracy and human agreement are unmeasured unless suitable real independent evidence exists. Preserve all errors, source-unavailable cases and unknowns and separate synthetic qualification controls from empirical source cases.

Acceptance criteria:

1. Every frozen selected case has an actual prediction/observation or explicit failed, unavailable or unsupported record without changing cohorts after outcomes.
2. Every reported metric is reproducible from case-level files and an exact scoped machine expectation or observation with independent provenance where the metric requires it. Implementation agreement is not semantic accuracy.
3. Original source-lineage splits and case denominators remain fixed. Human/author review is not a run dependency, and unmeasured expert legal fidelity or agreement is not assigned a numeric score.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-010 Qualify and run the selected real solver and independent checker routes

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-002, LA-003, LA-008
- Goal id: LA-G3
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G3
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/manifests/provers.json, papers/completion/law_to_action/results/proof_jobs/raw.jsonl, papers/completion/law_to_action/results/proof_jobs/qualification.md, papers/completion/law_to_action/receipts/LA-010.json
- Predicted files: papers/completion/law_to_action/benchmark/manifests/provers.json, papers/completion/law_to_action/results/proof_jobs/raw.jsonl, papers/completion/law_to_action/results/proof_jobs/qualification.md, papers/completion/law_to_action/receipts/LA-010.json, papers/completion/law_to_action/receipts/snapshots/LA-010/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-010
- Acceptance: At least the benchmark-required proof-oriented route executes a real provider/checker with retained raw artifacts.; Authority checks reject SAT-only/simulated/policy-only evidence where theorem evidence is required.; Each reported family has qualified scope and receipt; unavailable optional families are accurately scoped, not assigned invented results.
- Paper evidence: pp4–5 Table 2 and §3.2; p6 §4.2; pp12–13 Appendix B; p16 proof job Not run
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/compose.py, external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/portfolio.py, external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/service.py
- Receipt: papers/completion/law_to_action/receipts/LA-010.json

For each proof route actually used in the bounded benchmark, record installed prover/toolchain, supported fragment, premises, assumptions, translations and resource bounds; execute success, counterexample, timeout, unsupported and forged-evidence cases. Reconstruct and independently kernel-check proof candidates when the chosen assurance requires it. Distinguish solver SAT/UNSAT, runtime monitor, policy approval and theorem evidence. Test QF_LIA interpolation only if claimed and selected; remove unsupported broad-backend claims.

Acceptance criteria:

1. At least the benchmark-required proof-oriented route executes a real provider/checker with retained raw artifacts.
2. Authority checks reject SAT-only/simulated/policy-only evidence where theorem evidence is required.
3. Each reported family has qualified scope and receipt; unavailable optional families are accurately scoped, not assigned invented results.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-011 Wire and verify complete mediation, strict capabilities and exact live context

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-008, LA-010
- Goal id: LA-G4
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G4
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/route_inventory.json, papers/completion/law_to_action/results/mediation/raw.jsonl, papers/completion/law_to_action/results/mediation/qualification.md, papers/completion/law_to_action/patches/mediation_changes.md, papers/completion/law_to_action/receipts/LA-011.json
- Predicted files: papers/completion/law_to_action/benchmark/route_inventory.json, papers/completion/law_to_action/results/mediation/raw.jsonl, papers/completion/law_to_action/results/mediation/qualification.md, papers/completion/law_to_action/patches/mediation_changes.md, papers/completion/law_to_action/receipts/LA-011.json, papers/completion/law_to_action/receipts/snapshots/LA-011/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py, external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-011
- Acceptance: Every route named in the paper has allow/deny/unknown/context-mutation effect-counter tests.; Real cryptographic verification is executed; injected test verifiers are labeled as fixtures only.; No unprotected reachable route is included in the tested safety claim.; Code fixes are isolated and accompanied by meaningful boundary regressions; failures remain recorded.
- Paper evidence: p6 §4.3; pp7–8 §§6.3–6.4; p14 C.4; p16 E.2
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py, external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py, external/ipfs_kit/tests/runtime_readiness/mcplusplus/test_ucan_verifier.py, external/ipfs_kit/tests/runtime_readiness/mcplusplus/test_authorization_dispatch_gate.py
- Receipt: papers/completion/law_to_action/receipts/LA-011.json

Explicitly configure enforce mode, trusted current roots/clock/receipt issuer and actual protected handler paths. Integrate real signed UCAN verification and bind proof-derived capability actor/audience/tool/version/arguments/effects/roots/allowed use to it. Enumerate compatibility/bypass routes and exclude or guard them. Exercise wrong audience, tenant-a versus tenant-ab widening, expiry/revocation, forged proof identifiers, changed args/effects/environment, missing evidence and undeclared generated-code effects.

Acceptance criteria:

1. Every route named in the paper has allow/deny/unknown/context-mutation effect-counter tests.
2. Real cryptographic verification is executed; injected test verifiers are labeled as fixtures only.
3. No unprotected reachable route is included in the tested safety claim.
4. Code fixes are isolated and accompanied by meaningful boundary regressions; failures remain recorded.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-012 Qualify the real DuckDB owner and durable capability consumption

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-008, LA-011
- Goal id: LA-G4
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G4
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/durable_consumption.py, papers/completion/law_to_action/results/state/raw.jsonl, papers/completion/law_to_action/results/state/failure_matrix.md, papers/completion/law_to_action/patches/state_changes.md, papers/completion/law_to_action/receipts/LA-012.json
- Predicted files: papers/completion/law_to_action/benchmark/durable_consumption.py, papers/completion/law_to_action/results/state/raw.jsonl, papers/completion/law_to_action/results/state/failure_matrix.md, papers/completion/law_to_action/patches/state_changes.md, papers/completion/law_to_action/receipts/LA-012.json, papers/completion/law_to_action/receipts/snapshots/LA-012/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/quack_state_client.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/quack_state_server.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-012
- Acceptance: Enforced benchmark deployment uses the documented actual durable store, never the default in-memory store while claiming restart safety.; Restart/replay/concurrency outcomes and raw owner transaction evidence are retained.; Loss-of-reply does not silently trigger a repeated external effect; uncertainty is explicitly represented.
- Paper evidence: p6 §5 lines 226–243; p14 C.2 lines 471–481; p16 DuckDB pending row
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/quack_state_client.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/quack_state_server.py, external/ipfs_accelerate/test/api/test_agent_supervisor_quack_chaos.py
- Receipt: papers/completion/law_to_action/receipts/LA-012.json

Find or implement the minimal durable consumption adapter required by the selected enforcement deployment and exercise it with the typed Quack owner. Run same-use concurrent attempts, restart, lost reply, stale generation/fence/revision, changed-payload idempotency and owner failure cases. Observe actual handler effect counts around commit/consume/delegate windows. Record unresolved remote-effect outcomes; do not claim arbitrary exactly-once APIs.

Acceptance criteria:

1. Enforced benchmark deployment uses the documented actual durable store, never the default in-memory store while claiming restart safety.
2. Restart/replay/concurrency outcomes and raw owner transaction evidence are retained.
3. Loss-of-reply does not silently trigger a repeated external effect; uncertainty is explicitly represented.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-013 Run actual transport parity and content-retrieval qualification

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: law_to_action
- Depends on: LA-011, LA-012
- Goal id: LA-G4
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G4
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/transport/raw.jsonl, papers/completion/law_to_action/results/transport/configuration.json, papers/completion/law_to_action/results/transport/parity.md, papers/completion/law_to_action/receipts/LA-013.json
- Predicted files: papers/completion/law_to_action/results/transport/raw.jsonl, papers/completion/law_to_action/results/transport/configuration.json, papers/completion/law_to_action/results/transport/parity.md, papers/completion/law_to_action/receipts/LA-013.json, papers/completion/law_to_action/receipts/snapshots/LA-013/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-013
- Acceptance: Actual network versus local/in-process modes are unambiguous in records.; Semantic decisions and effects agree for identical requests on each claimed qualified transport.; Artifact integrity and availability are reported separately; no private evidence is publicly published as a side effect.
- Paper evidence: p7 §§6.1–6.2; p14 C.3; p16 cross-transport pending row
- Reuse candidates: external/ipfs_kit/ipfs_kit_py/mcp_server/server.py, external/ipfs_datasets/tests/integration/test_mcp_p2p_libp2p_smoke.py
- Receipt: papers/completion/law_to_action/receipts/LA-013.json

Exercise the same authorized and rejected requests through real stdio, HTTP and libp2p processes for the routes retained in scope. Retain peer/process identities, negotiated protocol, security settings, transport errors and handler outcomes. Retrieve an evidence artifact through the claimed content-addressed path and validate bytes/profile. A local network test is labeled local; in-process framing cannot be reported as libp2p network evidence. Narrow unexecutable optional transport/publication claims.

Acceptance criteria:

1. Actual network versus local/in-process modes are unambiguous in records.
2. Semantic decisions and effects agree for identical requests on each claimed qualified transport.
3. Artifact integrity and availability are reported separately; no private evidence is publicly published as a side effect.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-014 Implement matched baseline arms and validate experiment comparability

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-003, LA-008, LA-010, LA-011
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/arms.json, papers/completion/law_to_action/benchmark/baselines.py, papers/completion/law_to_action/benchmark/comparability_report.md, papers/completion/law_to_action/receipts/LA-014.json
- Predicted files: papers/completion/law_to_action/benchmark/arms.json, papers/completion/law_to_action/benchmark/baselines.py, papers/completion/law_to_action/benchmark/comparability_report.md, papers/completion/law_to_action/receipts/LA-014.json, papers/completion/law_to_action/receipts/snapshots/LA-014/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/service.py, external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-014
- Acceptance: Arm configurations are machine-readable and differ only by declared policy components.; Fixed-action replay uses identical candidate IDs/arguments/effects across arms.; Prompt-only and retrieval+prompt are distinct, and unguarded execution remains sandboxed.
- Paper evidence: p8 §7 lines 320–327; p16 E.1 lines 519–523
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/service.py, external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py
- Receipt: papers/completion/law_to_action/receipts/LA-014.json

Implement the five protocol arms using identical sources, handlers, candidate actions and scoring. Match model/prompt/context budgets where relevant and state precisely which components each arm receives. Lightweight policy+UCAN must use real strict capabilities and declared policy, and full enforcement must add the selected checked obligations. Validate runner arm switching and comparable observation paths on development cases without tuning to held-out outcomes.

Acceptance criteria:

1. Arm configurations are machine-readable and differ only by declared policy components.
2. Fixed-action replay uses identical candidate IDs/arguments/effects across arms.
3. Prompt-only and retrieval+prompt are distinct, and unguarded execution remains sandboxed.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-015 Run the frozen fixed-action end-to-end safety and utility benchmark

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-004, LA-009, LA-010, LA-011, LA-012, LA-014
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/fixed_actions/run_manifest.json, papers/completion/law_to_action/results/fixed_actions/raw.jsonl, papers/completion/law_to_action/results/fixed_actions/summary.json, papers/completion/law_to_action/receipts/LA-015.json
- Predicted files: papers/completion/law_to_action/results/fixed_actions/run_manifest.json, papers/completion/law_to_action/results/fixed_actions/raw.jsonl, papers/completion/law_to_action/results/fixed_actions/summary.json, papers/completion/law_to_action/receipts/LA-015.json, papers/completion/law_to_action/receipts/snapshots/LA-015/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-015
- Acceptance: Run manifest and raw logs cover the frozen case population and arm matrix with explicit missing cells.; Measured safety uses effect counters, not decision labels alone.; No zero-failure result is inferred from not-run/skipped cases; all results retain denominator and implementation revision.
- Paper evidence: p8 §7; p16 E.1 primary outcome and E.2 counterexamples; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_constraint_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py
- Receipt: papers/completion/law_to_action/receipts/LA-015.json

Run every frozen fixed-action case across all applicable arms with actual proof, capability and handler integrations. Collect observed forbidden effects and allowed work, false denials, unknowns/abstentions, route coverage and stage-specific errors. Include all required cross-source adversarial categories and paired safe controls. Retain every attempted case and all skips/failures; reruns require a recorded reason and fresh run identity. The labels allowed and forbidden refer only to the frozen modeled policy and machine-checkable behavior contract admitted by LA-027. Independent effect observation means a separately observed handler/postcondition trace, not an outside human reviewer. Do not claim real-world legality, expert judgment or universal security from these automated outcomes.

Acceptance criteria:

1. Run manifest and raw logs cover the frozen case population and arm matrix with explicit missing cells.
2. Measured safety uses effect counters, not decision labels alone.
3. No zero-failure result is inferred from not-run/skipped cases; all results retain denominator and implementation revision.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-016 Run a separate closed-loop generated-code agent planning and recovery study

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-007, LA-014, LA-015
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/agents/run_manifest.json, papers/completion/law_to_action/results/agents/raw.jsonl, papers/completion/law_to_action/results/agents/generated_code/, papers/completion/law_to_action/results/agents/recovery_analysis.md, papers/completion/law_to_action/receipts/LA-016.json
- Predicted files: papers/completion/law_to_action/results/agents/run_manifest.json, papers/completion/law_to_action/results/agents/raw.jsonl, papers/completion/law_to_action/results/agents/generated_code/, papers/completion/law_to_action/results/agents/recovery_analysis.md, papers/completion/law_to_action/receipts/LA-016.json, papers/completion/law_to_action/receipts/snapshots/LA-016/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-016
- Acceptance: Actual model calls and generated programs are evidenced or closed-loop claims are explicitly removed with author-visible scope impact.; Task utility is independently observed, not model self-reported.; All retries, failures, blocked outcomes and model tokens are retained by arm/seed/task.
- Paper evidence: p16 E.1 lines 522–523; p8 §7 planning/recovery trace
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-016.json

Have actual pinned model agents generate or revise bounded code/tool plans under protocol arms, with identical task/source distributions, resource budgets and independent scoring. Record prompts/model/tokenizer revisions, generated code, independent effects, repair/replan attempts and useful task completion. Do not pool with fixed-action results because enforcement can alter candidates. If actual model execution is unavailable, record the blocker and explicitly narrow the paper rather than substituting replay fixtures.

Acceptance criteria:

1. Actual model calls and generated programs are evidenced or closed-loop claims are explicitly removed with author-visible scope impact.
2. Task utility is independently observed, not model self-reported.
3. All retries, failures, blocked outcomes and model tokens are retained by arm/seed/task.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-017 Execute paired component ablations against actual effect outcomes

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: law_to_action
- Depends on: LA-015
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/ablations.json, papers/completion/law_to_action/results/ablations/raw.jsonl, papers/completion/law_to_action/results/ablations/summary.json, papers/completion/law_to_action/receipts/LA-017.json
- Predicted files: papers/completion/law_to_action/benchmark/ablations.json, papers/completion/law_to_action/results/ablations/raw.jsonl, papers/completion/law_to_action/results/ablations/summary.json, papers/completion/law_to_action/receipts/LA-017.json, papers/completion/law_to_action/receipts/snapshots/LA-017/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-017
- Acceptance: Each of the seven requested mechanisms has a paired experiment or justified scoped omission.; Raw paired case outcomes and configuration differences are retained.; Attribution discusses interacting checks when another guard masks an ablation; absence of change is not manufactured into benefit.
- Paper evidence: p16 E.2 lines 530–534
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-017.json

In the sandbox, ablate source provenance, hard applicability, intent/code correlation, proof jobs, current-root binding, capability verification and consumption separately from the full arm. Choose corresponding frozen positive and negative controls so each removed mechanism has a meaningful challenge; preserve all other inputs. Measure effect change, useful work and false rejection without enabling ablated configurations in live services.

Acceptance criteria:

1. Each of the seven requested mechanisms has a paired experiment or justified scoped omission.
2. Raw paired case outcomes and configuration differences are retained.
3. Attribution discusses interacting checks when another guard masks an ablation; absence of change is not manufactured into benefit.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-018 Measure full cost and latency for cold and reused evidence

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: law_to_action
- Depends on: LA-015, LA-016
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/efficiency/raw.jsonl, papers/completion/law_to_action/results/efficiency/environment.json, papers/completion/law_to_action/results/efficiency/summary.json, papers/completion/law_to_action/receipts/LA-018.json
- Predicted files: papers/completion/law_to_action/results/efficiency/raw.jsonl, papers/completion/law_to_action/results/efficiency/environment.json, papers/completion/law_to_action/results/efficiency/summary.json, papers/completion/law_to_action/receipts/LA-018.json, papers/completion/law_to_action/receipts/snapshots/LA-018/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-018
- Acceptance: Per-run phase totals reconcile with end-to-end observations with overhead/double-counting explained.; Cold/warm conditions and stale-evidence invalidation are reproducible.; No external price assumptions or unobserved token counts are silently filled.
- Paper evidence: p16 Table E1 efficiency Not run; p16 E.2 lines 532–534; p17 F lines 541–545
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-018.json

Instrument complete wall time and all model input/output/retry tokens, retrieval transfer/cache work, compilation, solver/checker, current clock/root checks, database transactions, artifact storage, network and retries. Define cold/warm cache conditions and invalidation/root changes. Record hardware and concurrency. Report measured usage separately from any price conversion, and preserve final task utility; graph size or token saving is not direct monetary savings.

Acceptance criteria:

1. Per-run phase totals reconcile with end-to-end observations with overhead/double-counting explained.
2. Cold/warm conditions and stale-evidence invalidation are reproducible.
3. No external price assumptions or unobserved token counts are silently filled.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-019 Analyze empirical results with uncertainty and stage-specific failure attribution

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-009, LA-010, LA-012, LA-015, LA-016, LA-017, LA-018
- Goal id: LA-G6
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G6
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/analysis/analyze.py, papers/completion/law_to_action/results/tables/, papers/completion/law_to_action/results/figures/, papers/completion/law_to_action/results/statistical_report.md, papers/completion/law_to_action/results/failure_taxonomy.json, papers/completion/law_to_action/receipts/LA-019.json
- Predicted files: papers/completion/law_to_action/analysis/analyze.py, papers/completion/law_to_action/results/tables/, papers/completion/law_to_action/results/figures/, papers/completion/law_to_action/results/statistical_report.md, papers/completion/law_to_action/results/failure_taxonomy.json, papers/completion/law_to_action/receipts/LA-019.json, papers/completion/law_to_action/receipts/snapshots/LA-019/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-019
- Acceptance: Analysis script recreates summary tables and figures without hand-entered result values.; All headline claims trace to raw run/case IDs and uncertainty intervals.; No observed bounded safety rate is described as universal legal correctness or universal prevention.
- Paper evidence: p8 §7 metrics; p15 D lines 508–511; p16 E.1–E.2; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-019.json

Generate all paper tables/figures from immutable raw records. Use protocol-defined paired comparisons and uncertainty clustered by independent source/task families. Include exact denominators, allowed utility, abstention/false denial, failure taxonomy, unsupported fragments, negative results and zero-event confidence bounds. Separate fixed-action and closed-loop results and fixture/real-provider evidence. Check source leakage and sensitivity to source families. Apply the automated evidence amendment: report policy-relative effects and measured structural/behavioral properties. Do not calculate legal semantic accuracy, annotator agreement or human-validity rates from generated or blank labels. Optional author judgments, if any, are separate descriptive material and cannot replace empirical outcomes.

Acceptance criteria:

1. Analysis script recreates summary tables and figures without hand-entered result values.
2. All headline claims trace to raw run/case IDs and uncertainty intervals.
3. No observed bounded safety rate is described as universal legal correctness or universal prevention.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-020 Replace the narrative walkthrough with a reproducible source-to-effect trace

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-015
- Goal id: LA-G6
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G6
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/results/worked_trace/trace.json, papers/completion/law_to_action/results/worked_trace/trace.md, papers/completion/law_to_action/results/figures/source_to_effect_trace.pdf, papers/completion/law_to_action/receipts/LA-020.json, papers/completion/law_to_action/receipts/snapshots/LA-020/
- Predicted files: papers/completion/law_to_action/results/worked_trace/trace.json, papers/completion/law_to_action/results/worked_trace/trace.md, papers/completion/law_to_action/results/figures/source_to_effect_trace.pdf, papers/completion/law_to_action/receipts/LA-020.json, papers/completion/law_to_action/receipts/snapshots/LA-020/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Proposal artifact envelope: {"binary_paths":["papers/completion/law_to_action/results/figures/source_to_effect_trace.pdf"],"max_file_bytes":16000000,"max_output_bytes":24000000,"max_patch_bytes":16000000,"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@3"}
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-020
- Acceptance: Each illustrated transition links to actual raw evidence under one run/case identity.; Trace contains at least permitted useful work and prevented forbidden effects.; Figure/table does not use a fabricated signature/proof receipt or pretend a conceptual step ran.
- Paper evidence: p8 §7 lines 298–313; p15 Appendix D twelve-step trace
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-020.json

Select an actual successful bounded export/generated-code case and matched rejected recipient/undeclared-effect/replay variants. Trace source spans and CIDs, Intent/Legal/Security IR, exact generated-code effects, assumptions, real proof/checker receipt, signed grant, live context revalidation, consumption, handler effects and owner progression. Label any genuinely absent step and narrow the narrative accordingly.

Acceptance criteria:

1. Each illustrated transition links to actual raw evidence under one run/case identity.
2. Trace contains at least permitted useful work and prevented forbidden effects.
3. Figure/table does not use a fabricated signature/proof receipt or pretend a conceptual step ran.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

Artifact transport: only the exact declared PDF/ZIP files above receive binary admission. Retained before-plus-after artifact bytes must fit the native 16,000,000-byte materialized bound and 24,000,000-byte serialized bound. Keep supplements compact; large datasets/checkpoints use reproducible hash-bound artifact-store references with the required anonymous access review. If an actual required package exceeds the bound, retain its measured size for an explicit runtime-cap qualification before retrying. This transport allowance supplies no scientific or format-validation credit.

## LA-021 Strengthen related work and workshop-specific novelty using primary sources

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: law_to_action
- Depends on: LA-002, LA-003
- Goal id: LA-G6
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G6
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/related_work.md, papers/completion/law_to_action/manuscript/related_work.bib, papers/completion/law_to_action/novelty_statement.md, papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/receipts/LA-021.json
- Predicted files: papers/completion/law_to_action/related_work.md, papers/completion/law_to_action/manuscript/related_work.bib, papers/completion/law_to_action/novelty_statement.md, papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/receipts/LA-021.json, papers/completion/law_to_action/receipts/snapshots/LA-021/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-021
- Acceptance: Closest related systems and implementable baseline rationale are cited from primary sources.; Novelty statement matches the bounded experimental contribution and acknowledges modeling/trust assumptions.; References and workshop fit are reflected in editable manuscript without pretending all listed systems were benchmarked.
- Paper evidence: p9 eight references; pp1–2 contributions; p8 conclusion
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-021.json

Research current primary papers/specifications on verifiable generated code, agent runtime enforcement, proof-carrying authorization, executable legal rules and relevant agent-security benchmarks. Build a concise comparison of actual assurance boundary, source fidelity, generated-code effect observation and useful-work measurement. Confirm citation metadata and avoid unsupported novelty/superiority claims. Keep broad infrastructure descriptions subordinate to the tested contribution. Integrate the reviewed related-work discussion, citations and workshop fit into manuscript/main.tex as part of this task. Ensure the selected bibliography is actually loaded, existing citation keys remain resolvable without duplicate entries, and retain a real compilation/citation check. Inherited bibliography access dates are historical source text, not evidence of fresh verification. Verify the closest current runtime-enforcement systems, including AgentSpec, Progent and CaMeL, from their primary sources; citing a system does not mean it was benchmarked.

Acceptance criteria:

1. Closest related systems and implementable baseline rationale are cited from primary sources.
2. Novelty statement matches the bounded experimental contribution and acknowledges modeling/trust assumptions.
3. References and workshop fit are reflected in editable manuscript without pretending all listed systems were benchmarked.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-022 Complete results, limitations and conclusions in the editable paper

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-001, LA-019, LA-020, LA-021, LA-029
- Goal id: LA-G6
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G6
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/results.tex, papers/completion/law_to_action/manuscript/limitations.tex, papers/completion/law_to_action/claim_evidence_matrix.json, papers/completion/law_to_action/receipts/LA-022.json
- Predicted files: papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/results.tex, papers/completion/law_to_action/manuscript/limitations.tex, papers/completion/law_to_action/claim_evidence_matrix.json, papers/completion/law_to_action/receipts/LA-022.json, papers/completion/law_to_action/receipts/snapshots/LA-022/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-022
- Acceptance: Every Not run/pending result placeholder is resolved by evidence or explicit scoped removal, never invented data.; Claim matrix links manuscript claims to exact experiments or clearly marked nonempirical implementation evidence.; Paper contains reproducible methodology and negative results, with a coherent evaluated verifiable-coding contribution.; Manuscript generation and an evidence-scoped submission candidate require no outside review. Optional author review is labeled non-independent and unsupported expert legal fidelity, human agreement and legal-validity claims are absent.
- Paper evidence: p1 abstract; p8 §§7–8; p16 Table E1; pp16–17 Appendix F; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-022.json

Replace evaluation-template prose and all pending rows with actual measured results or clearly scoped omissions. Rewrite abstract, contributions, method, evaluation and conclusion around supported findings; preserve model assumptions, incomplete legal coverage, source-interpretation uncertainty, protected-route limits and measured deployment scope. Remove unavailable future work from implemented contributions. Cite generated tables and correct all source statistics from manifests. Complete manuscript drafting and compilation without waiting for outside reviewers or optional author feedback. Replace the original Table E1 expert-reviewed legal-fidelity experiment with an explicit withdrawn/unmeasured claim and describe the automated source-contract evaluation that actually ran. State no independent human legal/security/intent validation or inter-annotator agreement was collected unless authentic records support it. Preserve the primary actual protected-effect/useful-work experiment and truthful negative results; this scope change does not turn missing experiments into results. Consume LA029 summary.json, cost_report.md and claim_guidance.md computed from the actual corrected run. Label the LA009 18/18 comparison as shared-producer conformance, the old LA015 rows and LA016/LA017 comparison wording as protocol-unadmitted diagnostic evidence, and LA020 detailed replays as separate diagnostic executions. Preserve original receipts and run identities.

Acceptance criteria:

1. Every Not run/pending result placeholder is resolved by evidence or explicit scoped removal, never invented data.
2. Claim matrix links manuscript claims to exact experiments or clearly marked nonempirical implementation evidence.
3. Paper contains reproducible methodology and negative results, with a coherent evaluated verifiable-coding contribution.
4. Manuscript generation and an evidence-scoped submission candidate require no outside review. Optional author review is labeled non-independent and unsupported expert legal fidelity, human agreement and legal-validity claims are absent.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-023 Assemble a reproducible artifact with pinned environments and lawful source access

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-019, LA-020, LA-022
- Goal id: LA-G7
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G7
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/artifact/README.md, papers/completion/law_to_action/artifact/environment.lock, papers/completion/law_to_action/artifact/reproduce.sh, papers/completion/law_to_action/artifact/manifest.json, papers/completion/law_to_action/artifact/anonymous_supplement.zip, papers/completion/law_to_action/receipts/LA-023.json
- Predicted files: papers/completion/law_to_action/artifact/README.md, papers/completion/law_to_action/artifact/environment.lock, papers/completion/law_to_action/artifact/reproduce.sh, papers/completion/law_to_action/artifact/manifest.json, papers/completion/law_to_action/artifact/anonymous_supplement.zip, papers/completion/law_to_action/receipts/LA-023.json, papers/completion/law_to_action/receipts/snapshots/LA-023/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-023
- Acceptance: A fresh checkout has documented environment setup and one-command bounded reproduction/analysis paths.; Reported results resolve to included or explicitly retrievable artifacts and matching hashes.; Raw logs are anonymized without altering scientific outcome fields; no credentials or private author companion are packaged.
- Paper evidence: pp10–11 Appendix A; p15 Table D1; p16 E.1; p17 disclosure
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-023.json

Package experiment harness, exact repository revisions/patches, source/solver/model manifests, lockfiles/container recipe, commands, raw result hashes, analysis and a small runnable reproduction subset. Include source retrieval instructions and licensing restrictions when redistribution is unavailable. Keep private author identities, provider credentials and author-only source maps outside the anonymous bundle. Require meaningful checks of artifact consistency rather than file-presence assertions.

Acceptance criteria:

1. A fresh checkout has documented environment setup and one-command bounded reproduction/analysis paths.
2. Reported results resolve to included or explicitly retrievable artifacts and matching hashes.
3. Raw logs are anonymized without altering scientific outcome fields; no credentials or private author companion are packaged.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-024 Apply official workshop template, anonymization and actual LLM disclosure

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-022, LA-023
- Goal id: LA-G7
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G7
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/submission/paper.pdf, papers/completion/law_to_action/submission/anonymous_supplement.zip, papers/completion/law_to_action/submission/compliance_audit.md, papers/completion/law_to_action/submission/disclosure.md, papers/completion/law_to_action/manuscript/checklist.tex, papers/completion/law_to_action/manuscript/neurips_2026_vericode.sty, papers/completion/law_to_action/submission/template_inputs.json, papers/completion/law_to_action/receipts/LA-024.json, papers/completion/law_to_action/receipts/snapshots/LA-024/
- Predicted files: papers/completion/law_to_action/submission/paper.pdf, papers/completion/law_to_action/submission/anonymous_supplement.zip, papers/completion/law_to_action/submission/compliance_audit.md, papers/completion/law_to_action/submission/disclosure.md, papers/completion/law_to_action/manuscript/checklist.tex, papers/completion/law_to_action/manuscript/neurips_2026_vericode.sty, papers/completion/law_to_action/submission/template_inputs.json, papers/completion/law_to_action/receipts/LA-024.json, papers/completion/law_to_action/receipts/snapshots/LA-024/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Proposal artifact envelope: {"binary_paths":["papers/completion/law_to_action/submission/paper.pdf","papers/completion/law_to_action/submission/anonymous_supplement.zip"],"max_file_bytes":16000000,"max_output_bytes":24000000,"max_patch_bytes":16000000,"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@3"}
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-024
- Acceptance: Compiled main-text page count is 4–9; PDF <=50 MB and supplementary ZIP <=100 MB.; Anonymous package does not link identifying author-maintained artifacts; necessary neutral aliases have a separate private mapping.; Actual methodology-essential LLM tool/model use and remaining human judgments are disclosed; the official style-generated anonymous Affiliation/Address/email block is retained.; Submission dates/template version are checked against the current CFP and recorded.; The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.; The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.; The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.; Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.
- Paper evidence: p1 placeholder author block; p14 Appendix D lines 504–507; p17 lines 546–549; workshop CFP; Local research template line 10 loads neurips_2026_vericode; line 461 includes checklist.tex. Research style lines 343–350 generate the anonymous Affiliation/Address/email block. Local checklist contains 16 official questions.; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/law_to_action/receipts/LA-024.json

Use the supplied local research workshop template and verify the final main text is 4–9 pages excluding references/appendices. Audit title/author block, acknowledgments, URLs, PDF metadata, figures, code comments and linked artifacts for double-blind compliance while preserving legitimate independent-source attribution. Disclose methodology-essential LLM tools, model versions and human review accurately. Confirm current CFP deadlines and size requirements without submitting externally. Build from the supplied local research shell papers/neurips_2026_vericode_workshop.tex and an unchanged copy of papers/neurips_2026_vericode.sty, using the supplied default \usepackage{neurips_2026_vericode} with no final, preprint, nonanonymous, or sglblindworkshop option. Do not use the competition/single-blind variant or the generic neurips_2026.sty. Copy papers/checklist.tex into this paper's manuscript directory, include it after references and optional appendices, remove only its BEGIN/END INSTRUCTIONS block, preserve the heading/questions/subheadings/guidelines, and replace all 16 \answerTODO{} and 16 \justificationTODO{} fields with actual evidence-backed \answerYes{}, \answerNo{}, or \answerNA{} and 1–2 sentence justifications. Do not edit the user's shared template/style/checklist originals or fabricate author-dependent answers. Pin input checksums. The style intentionally prints Anonymous Author(s), Affiliation, Address, and email: preserve this official anonymous block and exclude it from unresolved-placeholder failures. Record outside human validation as not collected for the amended study unless authentic returns exist. The author may optionally review the draft, but that is not independent annotation, expert validation, agreement evidence or a prerequisite to generate the manuscript. Answer checklist questions from actual automated work and actual human involvement, not planned reviewer packets.

Acceptance criteria:

1. Compiled main-text page count is 4–9; PDF <=50 MB and supplementary ZIP <=100 MB.
2. Anonymous package does not link identifying author-maintained artifacts; necessary neutral aliases have a separate private mapping.
3. Actual methodology-essential LLM tool/model use and remaining human judgments are disclosed; the official style-generated anonymous Affiliation/Address/email block is retained.
4. Submission dates/template version are checked against the current CFP and recorded.
5. The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.
6. The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.
7. The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.
8. Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

Artifact transport: only the exact declared PDF/ZIP files above receive binary admission. Retained before-plus-after artifact bytes must fit the native 16,000,000-byte materialized bound and 24,000,000-byte serialized bound. Keep supplements compact; large datasets/checkpoints use reproducible hash-bound artifact-store references with the required anonymous access review. If an actual required package exceeds the bound, retain its measured size for an explicit runtime-cap qualification before retrying. This transport allowance supplies no scientific or format-validation credit.

## LA-025 Reproduce key results in a clean environment and provide optional author handoff

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-024
- Goal id: LA-G8
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G8
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/submission/final_validation.md, papers/completion/law_to_action/submission/checksums.sha256, papers/completion/law_to_action/submission/author_handoff.md, papers/completion/law_to_action/submission/metadata.json, papers/completion/law_to_action/receipts/LA-025.json
- Predicted files: papers/completion/law_to_action/submission/final_validation.md, papers/completion/law_to_action/submission/checksums.sha256, papers/completion/law_to_action/submission/author_handoff.md, papers/completion/law_to_action/submission/metadata.json, papers/completion/law_to_action/receipts/LA-025.json, papers/completion/law_to_action/receipts/snapshots/LA-025/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-025
- Acceptance: Clean isolated reproduction commands, environment, observed outcomes and discrepancies are retained, with automated versus human activities labeled accurately.; No unsupported empirical claims or unresolved scientific placeholders remain. Missing outside reviewers or optional author feedback are not blockers, but missing required execution evidence or invalid artifact claims remain blockers.; Final paper/artifact checksums, optional author-review handoff and proposed submission metadata are complete without implying submission, human validation or workshop acceptance.
- Paper evidence: p16 all pending experiments; p17 final disclosure; workshop reproducibility expectations; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates: 
- Receipt: papers/completion/law_to_action/receipts/LA-025.json

From a clean isolated environment, rerun the documented bounded reproduction and regenerate key metrics/figures, rebuild manuscript and audit claims against raw evidence. Check missing citations, unresolved references/placeholders, broken artifact links, table consistency and PDF rendering. Provide reviewable final files, experiment inventory and explicit residual limitations/blockers. Prepare submission metadata for the authors; do not submit, upload or impersonate authors as part of autonomous completion. Verify research-template input checksums, all 16 completed checklist answers/justifications, preserved official style/anonymous block and workshop footer. Exempt only style-generated anonymous Affiliation/Address/email text from the residual-placeholder scan; scientific/checklist placeholders remain failures. Independent reproduction here means execution in a clean isolated environment with retained commands and evidence comparison and may be automated. No outside reviewer or returned annotation is required for completion. Deliver the compiled manuscript and handoff with optional author review clearly labeled, while preserving actual technical/scientific blockers and prohibiting unsupported claims.

Acceptance criteria:

1. Clean isolated reproduction commands, environment, observed outcomes and discrepancies are retained, with automated versus human activities labeled accurately.
2. No unsupported empirical claims or unresolved scientific placeholders remain. Missing outside reviewers or optional author feedback are not blockers, but missing required execution evidence or invalid artifact claims remain blockers.
3. Final paper/artifact checksums, optional author-review handoff and proposed submission metadata are complete without implying submission, human validation or workshop acceptance.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## LA-026 Complete source-bound CVE reproductions and reviewer-ready evidence

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-004, LA-008
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl, papers/completion/law_to_action/benchmark/cases/cve_controls.jsonl, papers/completion/law_to_action/benchmark/cve_reproduction/, papers/completion/law_to_action/benchmark/annotations/cve_review.md, papers/completion/law_to_action/benchmark/annotations/review_packet_manifest.json, papers/completion/law_to_action/receipts/LA-026.json, papers/completion/law_to_action/receipts/snapshots/LA-026/
- Predicted files: papers/completion/law_to_action/benchmark/cases/cve_pairs.jsonl, papers/completion/law_to_action/benchmark/cases/cve_controls.jsonl, papers/completion/law_to_action/benchmark/cve_reproduction/, papers/completion/law_to_action/benchmark/annotations/cve_review.md, papers/completion/law_to_action/benchmark/annotations/review_packet_manifest.json, papers/completion/law_to_action/receipts/LA-026.json, papers/completion/law_to_action/receipts/snapshots/LA-026/
- Allowed paths:
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-026
- Acceptance: Every reserved pair has exact source/revision hashes and an isolated reproduction or precisely defined source-supported behavior evidence, with failure records for all attempted recovery.; The frozen 12 pairs/24 cases and 84 excluded controls remain distinguishable with complete source and mutation lineage; no synthetic control enters empirical sample counts.; Reviewers receive source evidence, scope assumptions and blank polarity/adjudication fields in a complete manifest; independent review remains pending in LA-027 and LA-006.
- Paper evidence: Authorized September 12 unblock review: dependencies must lead to executed evidence, with independent human judgments explicitly pending.
- Reuse candidates:
- Receipt: papers/completion/law_to_action/receipts/LA-026.json

Finish the technical work held by LA-006 while independent review is pending. Recover exact vulnerable/fixed source bodies for the existing 12 source-family pairs/24 reserved cases and preserve all 84 excluded controls. Use official/upstream pinned sources, isolated effect-observing reproductions or precisely supported behavior evidence, retain failed attempts and unknown applicability, and update the review packets. Do not change frozen population, manufacture CVEs or infer independent expected polarity from the implementation under evaluation.

Acceptance criteria:

1. Every reserved pair has exact source/revision hashes and an isolated reproduction or precisely defined source-supported behavior evidence, with failure records for all attempted recovery.
2. The frozen 12 pairs/24 cases and 84 excluded controls remain distinguishable with complete source and mutation lineage; no synthetic control enters empirical sample counts.
3. Reviewers receive source evidence, scope assumptions and blank polarity/adjudication fields in a complete manifest; independent review remains pending in LA-027 and LA-006.

Retain source/artifact hashes, exact commands, actual outcomes and limits in the task receipt. Never close missing empirical or human evidence with a fixture, estimate or placeholder.

## LA-027 Implement and qualify the automated evidence scope without an outside-review gate

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-005, LA-007, LA-026, LA-028
- Goal id: LA-G2
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G2
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/automated_evidence_amendment.json, papers/completion/law_to_action/benchmark/AUTOMATED_EVIDENCE_SCOPE.md, papers/completion/law_to_action/benchmark/automated_evidence.py, papers/completion/law_to_action/benchmark/tests/test_automated_evidence.py, papers/completion/law_to_action/benchmark/qualify_final_runtime.py, papers/completion/law_to_action/benchmark/source_pipeline.py, papers/completion/law_to_action/benchmark/protocol.json, papers/completion/law_to_action/benchmark/protocol.md, papers/completion/law_to_action/benchmark/FINAL_RUN.md, papers/completion/law_to_action/benchmark/annotations/automated_reference_manifest.json, papers/completion/law_to_action/results/automated_scope_qualification, papers/completion/law_to_action/receipts/LA-027.json, papers/completion/law_to_action/receipts/snapshots/LA-027/
- Predicted files: papers/completion/law_to_action/benchmark/automated_evidence_amendment.json, papers/completion/law_to_action/benchmark/AUTOMATED_EVIDENCE_SCOPE.md, papers/completion/law_to_action/benchmark/automated_evidence.py, papers/completion/law_to_action/benchmark/tests/test_automated_evidence.py, papers/completion/law_to_action/benchmark/qualify_final_runtime.py, papers/completion/law_to_action/benchmark/source_pipeline.py, papers/completion/law_to_action/benchmark/protocol.json, papers/completion/law_to_action/benchmark/protocol.md, papers/completion/law_to_action/benchmark/FINAL_RUN.md, papers/completion/law_to_action/benchmark/annotations/automated_reference_manifest.json, papers/completion/law_to_action/results/automated_scope_qualification, papers/completion/law_to_action/receipts/LA-027.json, papers/completion/law_to_action/receipts/snapshots/LA-027/
- Allowed paths:
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-027
- Acceptance: An explicit versioned amendment binds the unchanged source population/splits, original protocol and receipts, machine-expectation provenance, permitted automated metrics and withdrawn expert/legal-validity/human-agreement claims before any new evaluated predictions.; Actual normal automated admission works without reviewer identities or human labels, while focused controls reject missing runtime/source bindings, incomplete case accounting, invalid expectation provenance, self-reported success, stale profile or budget, and any attempt to label automated output independent human gold.; The selected native source adapters, proof/capability route and independent effect observer execute in an isolated qualification with exact commands, hashes, failures and raw logs. Fixtures remain qualification-only and no held-out result or useful-work success is inferred from them.; The runtime, analysis and manuscript instructions no longer require outside reviewers for the automated scope. All human fields remain absent/uncollected unless authentic returns exist, optional author review is labeled non-independent, and original task/receipt/blank-packet history is preserved.
- Paper evidence: Superseded historical September 12 planning required independent human judgments. The current user-directed automated scope removes that outside-review prerequisite and does not claim human validation.; User clarification on 2026-09-12: no outside reviewers are available or required for manuscript generation. Unsupported human-agreement and expert legal-fidelity claims must be withdrawn rather than assigned generated labels.
- Reuse candidates:
- Receipt: papers/completion/law_to_action/receipts/LA-027.json

Implement the user-directed claim and protocol amendment in benchmark/automated_evidence_amendment.json and AUTOMATED_EVIDENCE_SCOPE.md. This replaces the former external-human gate with an executable automated evidence contract and a fresh task receipt. Preserve the original LA-005/007/026/028 receipts, blank review packets, failed imports and original LA-027 contract as history; none becomes human gold. Add a distinct typed automated admission path in benchmark/automated_evidence.py and wire qualify_final_runtime.py/source_pipeline.py/FINAL_RUN.md and protocol metadata to it. Retain review_import.py strict refusal of agent-authored human provenance for optional actual author/human returns; do not pass fabricated review.admitted=true to the old gate. Automated admission must bind the exact source/split/case inventory, pre-prediction machine expectations and their producer provenance, selected real runtime/profile versions, budgets, actual protected-handler/observer qualification and allowed claim set. Development qualification alone cannot admit held-out scores. Derive source-contract metrics and observed policy-relative effects, not legal truth or human semantic agreement. Actual source-unavailable or runtime-incomplete cases stay failed/unknown. Optional author review can be recorded separately but is not required to run or write this scoped paper.

Acceptance criteria:

1. Actual human legal/intent/security judgments bind the selected source units, versions, reviewers and timestamps, with explicit ambiguity/unknown and disagreement/adjudication records.
2. Every empirical CVE pair has independently reviewed expected polarity plus the LA-026 supported behavior evidence required by the unchanged LA-006 contract.
3. A validated import preserves original blank packets, all selected cases and review provenance; missing reviewers or labels cannot yield a complete review or scored fidelity claim.

Retain source/artifact hashes, exact commands, actual outcomes and limits in the task receipt. Never close missing empirical or human evidence with a fixture, estimate or placeholder.

## LA-028 Qualify real source adapters, review import and benchmark execution before final scoring

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-005, LA-007, LA-008, LA-010, LA-011, LA-012, LA-013, LA-014, LA-026
- Goal id: LA-G3
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G3
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/source_pipeline.py, papers/completion/law_to_action/benchmark/review_import.py, papers/completion/law_to_action/benchmark/qualify_final_runtime.py, papers/completion/law_to_action/benchmark/runtime_manifest.json, papers/completion/law_to_action/results/development_qualification/, papers/completion/law_to_action/benchmark/FINAL_RUN.md, papers/completion/law_to_action/receipts/LA-028.json, papers/completion/law_to_action/receipts/snapshots/LA-028/
- Predicted files: papers/completion/law_to_action/benchmark/source_pipeline.py, papers/completion/law_to_action/benchmark/review_import.py, papers/completion/law_to_action/benchmark/qualify_final_runtime.py, papers/completion/law_to_action/benchmark/runtime_manifest.json, papers/completion/law_to_action/results/development_qualification/, papers/completion/law_to_action/benchmark/FINAL_RUN.md, papers/completion/law_to_action/receipts/LA-028.json, papers/completion/law_to_action/receipts/snapshots/LA-028/
- Allowed paths:
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-028
- Acceptance: Selected source adapters actually process development legal/CVE/skill sources into retained predictions or explicit failures, with all inputs and runtime versions pinned.; An executable end-to-end development command reaches the selected proof/capability/effect-observing handler boundary and records actual model/provider calls when the chosen arm requires them; fixture-only routes are not represented as production.; Review import, final admission and analysis refuse missing independent labels, unavailable runtime routes and incomplete populations; final inputs/arm budgets are frozen before evaluated predictions.
- Paper evidence: Authorized September 12 unblock review: dependencies must lead to executed evidence, with independent human judgments explicitly pending.
- Reuse candidates:
- Receipt: papers/completion/law_to_action/receipts/LA-028.json

Prepare actual source extraction/normalization and the final-run entry points independently of missing human judgments. Qualify the real frozen source adapters and protected handlers on development sources, with stage-specific receipts and a review-return importer that refuses missing/agent-generated human provenance. Distinguish the prior fixed-candidate fixture runs from model/held-out comparisons. Make source access, selected solver/crypto/transport/runtime profiles, budgets and final admission requirements executable. Do not inspect final labels or score final examples before LA-027.

Acceptance criteria:

1. Selected source adapters actually process development legal/CVE/skill sources into retained predictions or explicit failures, with all inputs and runtime versions pinned.
2. An executable end-to-end development command reaches the selected proof/capability/effect-observing handler boundary and records actual model/provider calls when the chosen arm requires them; fixture-only routes are not represented as production.
3. Review import, final admission and analysis refuse missing independent labels, unavailable runtime routes and incomplete populations; final inputs/arm budgets are frozen before evaluated predictions.

Retain source/artifact hashes, exact commands, actual outcomes and limits in the task receipt. Never close missing empirical or human evidence with a fixture, estimate or placeholder.

## LA-029 Execute the frozen fixed-action benchmark under measured operator resource boundaries

- Status: blocked
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-008, LA-014, LA-015, LA-027
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/fixed_action_operator/, papers/completion/law_to_action/results/fixed_actions_admitted/run_manifest.json, papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl, papers/completion/law_to_action/results/fixed_actions_admitted/costs.jsonl, papers/completion/law_to_action/results/fixed_actions_admitted/resource_admission.json, papers/completion/law_to_action/results/fixed_actions_admitted/cost_report.md, papers/completion/law_to_action/results/fixed_actions_admitted/claim_guidance.md, papers/completion/law_to_action/results/fixed_actions_admitted/summary.json, papers/completion/law_to_action/receipts/LA-029.json, papers/completion/law_to_action/receipts/snapshots/LA-029/
- Predicted files: papers/completion/law_to_action/benchmark/fixed_action_operator/, papers/completion/law_to_action/results/fixed_actions_admitted/run_manifest.json, papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl, papers/completion/law_to_action/results/fixed_actions_admitted/costs.jsonl, papers/completion/law_to_action/results/fixed_actions_admitted/resource_admission.json, papers/completion/law_to_action/results/fixed_actions_admitted/cost_report.md, papers/completion/law_to_action/results/fixed_actions_admitted/claim_guidance.md, papers/completion/law_to_action/results/fixed_actions_admitted/summary.json, papers/completion/law_to_action/receipts/LA-029.json, papers/completion/law_to_action/receipts/snapshots/LA-029/
- Allowed paths:
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-029
- Acceptance: All 900 frozen case-arm-seed identities have exactly one new accounted operator disposition, with source/candidate/schedule/runtime hashes and all original diagnostic histories preserved. An incomplete or unadmitted matrix remains an explicit unfinished benchmark obligation.; Each executed cell has observed singleton cpuset and CPU quota, 2 GiB/no-swap/16-process enforcement, actual whole-group timeout/termination evidence and measured descendant-inclusive cost accounting under the frozen 20 s/18,000 CPU-second stopping limits. Any prospective accounting clarification is explicit and frozen before this corrected run.; Actual frozen arm implementations produce retained independent effect-observer counters, useful-work outcomes and source-bound native proof/capability/durable-consumption evidence. The original mechanisms, schedule and shared private store/key semantics are unchanged.; No failed or unknown-termination cell is replayed, no usage is refunded or invented, and no diagnostic unadmitted rate is promoted to an admitted headline result. Downstream analysis and trace tasks consume only exact admitted correction evidence or explicitly retain its incompleteness. The recalculated admitted-run analysis/statistics, corrected cost report and explicit shared-validator, diagnostic-rate and separate-replay guidance are retained for LA019 and LA022.
- Paper evidence: LA-003/v3 fixed-action per-attempt resource contract remains unchanged.; LA-015 completed receipt53b3b162 records900 protocol-unadmitted diagnostic cells and does not discharge the admitted benchmark obligation.; Root authorized a separately accounted operator correction on2026-09-12, preserving original and rescue runs and requiring no outside human reviewer.
- Reuse candidates: papers/completion/law_to_action/receipts/snapshots/LA-015/run_fixed_actions.py
- Receipt: papers/completion/law_to_action/receipts/LA-029.json

Use the exact operator-controlled per-cell Docker route staged in benchmark/fixed_action_operator, with the unchanged 60 frozen candidates, 900-cell schedule, five arm mechanisms and three seeds from source 7fc7c210. Ordinary provider authoring containers must not substitute another whole-loop diagnostic run or flip a resource-admission boolean. A host operator may supply the necessary Docker boundary and import exact retained results through normal source/evidence admission. Each cell uses one singleton CPU, 1-core quota, 2 GiB aggregate memory/no swap, 16 processes/threads, 20 s wall/aggregate CPU and the fixed global 18,000 CPU-second stopping budget. Keep one exclusive persistent benchmark DuckDB and study UCAN key across cells. Retain original 900 plus rescue 900 diagnostics, every raw outcome and failure, patch rejection/rescue history and all known/unknown costs separately. This task remains blocked until the concrete operator execution route and accounted admission are available. No outside reviewer or human annotations are required. The completion evidence must contain actual resource-qualified operator execution, not a missing-runtime report. Do not rerun, resample, change arms, claim model efficacy or upgrade modeled-policy outcomes to legal validity. LA029 owns the corrected operator run's recalculated analysis/statistics and actual cost report because LA018 completed and active LA019 retains its prior diagnostic scope. Recalculate the admitted matrix summary, denominators and uncertainty from the exact new operator run, preserving any missing or unadmitted dispositions, rather than using an old summary flag. Join each cell's measured group CPU, wall, memory peak, termination and setup/cleanup metadata without double-counting nested phases. Preserve both original 900-cell diagnostic histories, known costs and unknown historical CPU explicitly. Record a claim-guidance artifact: LA009's 18/18 is shared-producer conformance, LA015 compact rows are protocol-unadmitted diagnostic outcomes, LA016/LA017 evaluated-comparison wording does not establish an admitted benchmark, and LA020's detailed replay is a separate diagnostic execution rather than the historical LA015 run. Preserve all old receipts/replays and distinguish each new run identity.

Acceptance criteria:

1. All 900 frozen case-arm-seed identities have exactly one new accounted operator disposition, with source/candidate/schedule/runtime hashes and all original diagnostic histories preserved. An incomplete or unadmitted matrix remains an explicit unfinished benchmark obligation.
2. Each executed cell has observed singleton cpuset and CPU quota, 2 GiB/no-swap/16-process enforcement, actual whole-group timeout/termination evidence and measured descendant-inclusive cost accounting under the frozen 20 s/18,000 CPU-second stopping limits. Any prospective accounting clarification is explicit and frozen before this corrected run.
3. Actual frozen arm implementations produce retained independent effect-observer counters, useful-work outcomes and source-bound native proof/capability/durable-consumption evidence. The original mechanisms, schedule and shared private store/key semantics are unchanged.
4. No failed or unknown-termination cell is replayed, no usage is refunded or invented, and no diagnostic unadmitted rate is promoted to an admitted headline result. Downstream analysis and trace tasks consume only exact admitted correction evidence or explicitly retain its incompleteness. The recalculated admitted-run analysis/statistics, corrected cost report and explicit shared-validator, diagnostic-rate and separate-replay guidance are retained for LA019 and LA022.

Record exact operator commands, admitted boundary/cost receipts, all attempted cells and failures. This is an automated evidence obligation, not an outside review gate.

## LA-030 Qualify a native generated-code and bounded-repair development runner

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-016, LA-029
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/generated_code_development/common.py, papers/completion/law_to_action/benchmark/generated_code_development/native_candidate.py, papers/completion/law_to_action/benchmark/generated_code_development/container_runner.py, papers/completion/law_to_action/benchmark/generated_code_development/loop.py, papers/completion/law_to_action/benchmark/generated_code_development/bounded_http.py, papers/completion/law_to_action/benchmark/generated_code_development/qualify.py, papers/completion/law_to_action/benchmark/generated_code_development/qualify_interfaces.py, papers/completion/law_to_action/benchmark/generated_code_development/verify_development.py, papers/completion/law_to_action/benchmark/generated_code_development/development_runtime.json, papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v3/, papers/completion/law_to_action/benchmark/generated_code_development/README.md, papers/completion/law_to_action/receipts/LA-030.json, papers/completion/law_to_action/receipts/snapshots/LA-030/
- Predicted files: papers/completion/law_to_action/benchmark/generated_code_development/common.py, papers/completion/law_to_action/benchmark/generated_code_development/native_candidate.py, papers/completion/law_to_action/benchmark/generated_code_development/container_runner.py, papers/completion/law_to_action/benchmark/generated_code_development/loop.py, papers/completion/law_to_action/benchmark/generated_code_development/bounded_http.py, papers/completion/law_to_action/benchmark/generated_code_development/qualify.py, papers/completion/law_to_action/benchmark/generated_code_development/qualify_interfaces.py, papers/completion/law_to_action/benchmark/generated_code_development/verify_development.py, papers/completion/law_to_action/benchmark/generated_code_development/development_runtime.json, papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v3/, papers/completion/law_to_action/benchmark/generated_code_development/README.md, papers/completion/law_to_action/receipts/LA-030.json, papers/completion/law_to_action/receipts/snapshots/LA-030/
- Allowed paths: papers/completion/law_to_action/benchmark/generated_code_development/
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-030
- Acceptance: A retained, reproducible constructed development qualification demonstrates actual execution of exact response program bytes, native facts bound to those bytes, independent task-policy intent, and real A4 pre-invocation admission before a real handler effect. Facts alone never authorize execution.; The declared direct-calls-v1 language is enforced before execution and rejects imports, attributes, dynamic calls, decorators, annotations, generic type parameters, unsupported signatures and extra statements. Candidate code cannot access admission objects or hidden utility expectations.; Actual A0 undeclared-effect control is observed; actual A4 permitted useful work succeeds; actual A4 undeclared candidate is denied before delegation and then repaired from retained observed feedback to useful work; a generic-function candidate is rejected; actual A3 permitted work uses real policy/UCAN. These five controls/six candidate executions remain development evidence only.; Every candidate has actual one-CPU, 2-GiB/no-extra-swap, 16-process, no-network/read-only containment and a 20-second cell wall/descendant-CPU allowance. Exact-owned cleanup and an empty retained parent cgroup prove termination; complete descendant costs and any unknown accounting are retained.; Native A4 receipts bind candidate, task, policy, runtime, arguments, effects, context and current time; actual file-backed native durable consumption is used. Independent file bytes and journal reconciliation determine useful work and forbidden effects. No model self-report, mock proof, or in-memory store substitutes for the mechanism.; All requests, raw responses, candidates, retries, failures, feedback and known/unknown costs are retained. Failed inference reservations still consume a call, unavailable token usage stays unknown, and uncertain execution never becomes measured absence of forbidden effects. Fresh output directories prevent silent replay; a full durable resume scheduler remains downstream.; A0/A1/A2 prompt composition is explicitly distinct and A2/A3/A4 model context is matched, while actual A3/A4 execution mechanisms differ. Constructed responses establish neither prompt efficacy nor retrieval efficacy, and the two-sink development profile does not replace the full scientific population.; The pluggable HTTP interface retains request/response/failure evidence and uses a parent-enforced complete HTTP deadline. Actual model use remains gated by hash-bound model weights, tokenizer, revisions, template, deployment, decoding, prompt and real preflight evidence; study admission additionally binds the actual development report/code/runtime and separate full-cohort/runtime qualifications.; The read-only verifier passes on the exact final retained qualification and current implementation. Qualification source snapshots and earlier failed/successful development attempts remain intact. Completing LA-030 does not mark LA-G5 or the original downstream 900-cell scientific study complete.
- Paper evidence: Original LA-016 describes an actual pinned-model, generated-code planning and repair comparison; its completed omission receipt did not implement that loop.; Original protocol preserves 30 independently lineaged families, 60 paired cases, all A0-A4 arms and all 900 case-arm-seed cells.; LA-029 provides real native policy, UCAN, durable consumption, independent effects and operator resource containment to reuse, without reclassifying fixed actions as generated programs.
- Reuse candidates: papers/completion/law_to_action/benchmark/fixed_action_operator/controller.py, papers/completion/law_to_action/benchmark/baselines.py, papers/completion/law_to_action/benchmark/handlers/effects.py
- Receipt: papers/completion/law_to_action/receipts/LA-030.json

Implement and qualify the missing byte-bound generated-response to native facts, independently supplied policy intent, actual native admission, real contained handlers, independent filesystem/journal utility, and bounded observed-feedback repair path. Reuse the actual LA-029 containment implementation. This successor completes a concrete development increment, not the original generated-code empirical study. Preserve LA-016's withdrawn 900-cell record, the final manuscript, historical receipts and failed development attempts. Constructed development responses are explicitly labeled and never reported as model calls or scientific benchmark evidence. Real model inference, final-cohort release and scientific scheduling are outside this task's execution authority and require separate prospective qualifications.

Acceptance criteria:

1. A retained, reproducible constructed development qualification demonstrates actual execution of exact response program bytes, native facts bound to those bytes, independent task-policy intent, and real A4 pre-invocation admission before a real handler effect. Facts alone never authorize execution.
2. The declared direct-calls-v1 language is enforced before execution and rejects imports, attributes, dynamic calls, decorators, annotations, generic type parameters, unsupported signatures and extra statements. Candidate code cannot access admission objects or hidden utility expectations.
3. Actual A0 undeclared-effect control is observed; actual A4 permitted useful work succeeds; actual A4 undeclared candidate is denied before delegation and then repaired from retained observed feedback to useful work; a generic-function candidate is rejected; actual A3 permitted work uses real policy/UCAN. These five controls/six candidate executions remain development evidence only.
4. Every candidate has actual one-CPU, 2-GiB/no-extra-swap, 16-process, no-network/read-only containment and a 20-second cell wall/descendant-CPU allowance. Exact-owned cleanup and an empty retained parent cgroup prove termination; complete descendant costs and any unknown accounting are retained.
5. Native A4 receipts bind candidate, task, policy, runtime, arguments, effects, context and current time; actual file-backed native durable consumption is used. Independent file bytes and journal reconciliation determine useful work and forbidden effects. No model self-report, mock proof, or in-memory store substitutes for the mechanism.
6. All requests, raw responses, candidates, retries, failures, feedback and known/unknown costs are retained. Failed inference reservations still consume a call, unavailable token usage stays unknown, and uncertain execution never becomes measured absence of forbidden effects. Fresh output directories prevent silent replay; a full durable resume scheduler remains downstream.
7. A0/A1/A2 prompt composition is explicitly distinct and A2/A3/A4 model context is matched, while actual A3/A4 execution mechanisms differ. Constructed responses establish neither prompt efficacy nor retrieval efficacy, and the two-sink development profile does not replace the full scientific population.
8. The pluggable HTTP interface retains request/response/failure evidence and uses a parent-enforced complete HTTP deadline. Actual model use remains gated by hash-bound model weights, tokenizer, revisions, template, deployment, decoding, prompt and real preflight evidence; study admission additionally binds the actual development report/code/runtime and separate full-cohort/runtime qualifications.
9. The read-only verifier passes on the exact final retained qualification and current implementation. Qualification source snapshots and earlier failed/successful development attempts remain intact. Completing LA-030 does not mark LA-G5 or the original downstream 900-cell scientific study complete.

Execution boundaries and remaining obligations:

```json
{
  "runtime_boundaries": {
    "provider_calls_allowed": false,
    "model_loads_allowed": false,
    "final_cohort_release_allowed": false,
    "actual_candidate_controls": 6,
    "concurrent_candidate_executions": 1,
    "cell_cpu_cores": 1,
    "cell_memory_bytes": 2147483648,
    "cell_process_limit": 16,
    "cell_wall_seconds": 20,
    "cell_descendant_cpu_seconds": 20,
    "attempt_maximum_calls": 8,
    "attempt_maximum_wall_seconds": 120,
    "paid_budget": 0,
    "unknown_effect_or_cleanup_action": "Stop, preserve unknown disposition and reconcile; do not replay silently."
  },
  "input_boundaries": {
    "permitted": [
      "Pinned native implementation and existing LA-029 containment",
      "Explicitly constructed non-benchmark development tasks/responses",
      "Isolated local HTTP fault servers carrying test JSON and no model payloads"
    ],
    "not_released": [
      "New scientific sources or final cohort",
      "Existing hidden final oracles",
      "Model service inference or provider credentials"
    ]
  },
  "write_boundaries": {
    "allowed": [
      "papers/completion/law_to_action/benchmark/generated_code_development/",
      "Exact-owned ephemeral containment resources declared in each retained request"
    ],
    "preserve": [
      "papers/final/",
      "All historical LA-016 and LA-029 receipts/results",
      "All previously recorded development attempts"
    ]
  },
  "downstream_still_required": [
    "Freeze the separate original full 30-family/60-case cohort, lawful immutable source pins, ranked population splits, exact/normalized text and lineage audits, source-relative tasks, independent utility/effect oracles, permitted retrieval and all 900 scheduled identities before outcomes.",
    "Qualify the actual scientifically adequate generated-program and handler profile for all intended tasks and original arms; do not substitute the two-sink development controls or fixed LA-029 programs.",
    "Qualify full native/runtime/dependency provenance and actual already-loaded model service, exact weights/tokenizer/template/deployment revisions, token preflight agreement, decoding, resource accounting and cancellation behavior.",
    "Implement and qualify a durable complete-schedule reservation/resume/reconciliation driver and a hard complete-attempt deadline covering transport, execution and cleanup, retaining every failure/unknown cost without refunded calls or silent replay.",
    "Run matched A0-A4 on seeds 104729, 104759 and 104761 with all 900 planned cells, including 540 final cells, original per-call token limits and original per-attempt budgets. Preserve denominator and omissions if any cell remains unrun.",
    "Analyze source-family paired effects, useful task completion, repair attempts and complete costs from actual model-generated candidates, then update the manuscript only from those measurements. Outside annotations are not required for the established automated policy-relative evidence scope."
  ],
  "verifier_command": "python3 -B papers/completion/law_to_action/benchmark/generated_code_development/verify_development.py --output papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v3"
}
```

## LA-031 Complete and execute the original generated-code planning and recovery study

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: law_to_action
- Depends on: LA-030, LA-016, LA-029, LA-027
- Goal id: LA-G5
- Parent goal: LA-G000
- Objective heap: papers/completion/law_to_action/paper.objectives.md
- Board namespace: vericodegen-2026-law_to_action
- Bundle: law_to_action/LA-G5
- Parallel lane: law_to_action
- Outputs: papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json, papers/completion/law_to_action/benchmark/generated_code_study/cohort/, papers/completion/law_to_action/benchmark/generated_code_study/qualification/, papers/completion/law_to_action/benchmark/generated_code_study/model_profile.json, papers/completion/law_to_action/benchmark/generated_code_study/schedule.json, papers/completion/law_to_action/benchmark/generated_code_study/driver.py, papers/completion/law_to_action/results/generated_code_study/run_manifest.json, papers/completion/law_to_action/results/generated_code_study/raw.jsonl, papers/completion/law_to_action/results/generated_code_study/generated_code/, papers/completion/law_to_action/results/generated_code_study/costs.jsonl, papers/completion/law_to_action/results/generated_code_study/summary.json, papers/completion/law_to_action/results/generated_code_study/recovery_analysis.md, papers/completion/law_to_action/results/generated_code_study/reproducibility/, papers/completion/law_to_action/results/generated_code_study/manuscript_evidence_crosswalk.json, papers/completion/law_to_action/benchmark/generated_code_study/verify_study.py, papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/results.tex, papers/completion/law_to_action/manuscript/limitations.tex, papers/completion/law_to_action/submission/, papers/final/law_to_action/editable/, papers/final/law_to_action/paper.pdf, papers/final/law_to_action/supplement.zip, papers/completion/law_to_action/artifact/, papers/final/law_to_action/BUILD.md, papers/final/law_to_action/provenance/, papers/completion/law_to_action/receipts/LA-031.json, papers/completion/law_to_action/receipts/snapshots/LA-031/
- Predicted files: papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json, papers/completion/law_to_action/benchmark/generated_code_study/cohort/, papers/completion/law_to_action/benchmark/generated_code_study/qualification/, papers/completion/law_to_action/benchmark/generated_code_study/model_profile.json, papers/completion/law_to_action/benchmark/generated_code_study/schedule.json, papers/completion/law_to_action/benchmark/generated_code_study/driver.py, papers/completion/law_to_action/results/generated_code_study/run_manifest.json, papers/completion/law_to_action/results/generated_code_study/raw.jsonl, papers/completion/law_to_action/results/generated_code_study/generated_code/, papers/completion/law_to_action/results/generated_code_study/costs.jsonl, papers/completion/law_to_action/results/generated_code_study/summary.json, papers/completion/law_to_action/results/generated_code_study/recovery_analysis.md, papers/completion/law_to_action/results/generated_code_study/reproducibility/, papers/completion/law_to_action/results/generated_code_study/manuscript_evidence_crosswalk.json, papers/completion/law_to_action/benchmark/generated_code_study/verify_study.py, papers/completion/law_to_action/manuscript/main.tex, papers/completion/law_to_action/manuscript/results.tex, papers/completion/law_to_action/manuscript/limitations.tex, papers/completion/law_to_action/submission/, papers/final/law_to_action/editable/, papers/final/law_to_action/paper.pdf, papers/final/law_to_action/supplement.zip, papers/completion/law_to_action/artifact/, papers/final/law_to_action/BUILD.md, papers/final/law_to_action/provenance/, papers/completion/law_to_action/receipts/LA-031.json, papers/completion/law_to_action/receipts/snapshots/LA-031/
- Allowed paths: papers/completion/law_to_action/benchmark/generated_code_development/, papers/completion/law_to_action/benchmark/generated_code_study/, papers/completion/law_to_action/results/generated_code_study/, papers/completion/law_to_action/manuscript/, papers/completion/law_to_action/submission/, papers/final/law_to_action/, papers/completion/law_to_action/artifact/
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper law_to_action --task LA-031
- Acceptance: Before outcome inspection, freeze exactly 30 new source-lineage families and 60 paired cases: 6 legal, 12 CVE and 12 skill families. Establish lawful immutable source pins, actual source bytes, exact and normalized text hashes, ancestry and nearest-neighbor leakage audit; exclude every LA-004/LA-029 fixed-action family and all its derivatives. Apply the original ranked hash split with salt vericodegen-2026-law-to-action-LA016-v1 and population quotas legal 2/1/3, CVE 2/3/7, skill 2/2/8 for development/calibration/final. All descendant cases inherit their parent split.; Implement source-relative prompts/tasks and independent machine-checkable effect/utility expectations for all 60 cases. Retain each source-to-policy/task/oracle mapping. Generated candidates must perform useful bounded work through actual handlers, not select a canned fixed program. The LA-030 two-sink controls remain development evidence and are not relabeled as this cohort. Qualify the generated-code language/handler profile against supported useful tasks and undeclared effects before final release.; Implement real A0 task-only, A1 policy prompting, A2 retrieval plus policy, A3 actual policy/UCAN, and A4 full actual native enforcement interventions. Match task source, payload, permitted retrieval, model, decoding, execution bounds and independent scoring within case/seed. Preserve every proposed candidate and observed-feedback repair. Demonstrate actual positive useful-work and negative effect/authorization qualification for each supported mechanism; no inert metadata substitutes for a model intervention.; Qualify a concrete actual local model deployment with immutable model/weights/tokenizer/revision/template/deployment hashes, original token ceilings, decoding/seed behavior, exact prompt/template token agreement and measured service resource boundaries. Reuse the model warm during active inference as requested. A bounded runner may replace systemd; do not require an always-on service or reload between ordinary requests. Respect the user's current 10000-second total service wall preference and separate 360-second startup readiness bound while retaining separate original 120-second scientific attempt limits. Preserve actual startup, warm-service, per-call and shutdown/cancellation costs without double counting.; Implement and qualify an actual durable full-schedule driver: reserve each case-arm-seed cell and model call before dispatch, retain unknown delivery/usage, continue only after explicit failed-run reconciliation, and never silently refund or replay. Qualify interruption/resume, stale ownership, one-time capability use, complete descendant cleanup and an outer hard 120-second attempt deadline across transport, generated-code execution and cleanup. CPU, memory, token, model-call and paid-budget costs remain known or explicitly unknown, never replaced by configured limits.; Freeze the complete balanced original schedule and prospectively qualified code/runtime/model/cohort/prompt/oracle artifacts before scientific outputs. Execute exactly the original 60 cases x 5 arms x seeds 104729/104759/104761, preserving all 900 identities: 180 development, 180 calibration and 540 final. Freeze thresholds/analysis before final outputs. Every planned identity has an accounted terminal disposition; any unrun or unadmitted cell keeps this empirical execution obligation incomplete and remains in reporting denominators.; Retain real model HTTP/provider request and response bytes, precise candidate bytes, source/fact/admission identity, actual native handler and durable-consumption evidence, independent observed effect/utility outcomes, repair feedback, model calls/tokens and measured costs for every attempt. At least actual executed model calls and generated programs must exist; constructed transport, model-free LA-029 programs, omission reports and logged intended commands cannot satisfy this requirement.; Recompute matched arm comparisons, source-family-aware uncertainty, useful work, forbidden effects, repair behavior and complete cost/omission summaries from the exact admitted records. Keep the generated-code study separate from fixed-action evidence and distinguish policy-relative safety/utility from legal validity or human semantic fidelity. Validate a portable reproducibility package from raw records.; Update the editable Law-to-Action manuscript and final local artifact from the actual new evidence, preserving page limits, citation accuracy, anonymity and historical records. Qualify the final source/results/package crosswalk and compilation. No external workshop upload or submission is part of this task. LA-G5 may be completed only when its actual remaining acceptance criteria are met.; The dedicated scientific verifier fails if any original scheduled identity is absent, unrun or unadmitted; if real model calls or generated-program execution evidence is missing; if reservation/candidate/admission/effect/cost bindings fail; or if source-family paired analysis or manuscript/package crosswalk cannot be reproduced from raw records. A completed omission cannot pass this verifier.
- Paper evidence: Original LA-016 and LA-003/v3 protocol RQ3 require actual pinned-model generation and revision under matched A0-A4 interventions.; LA-016's historical completed receipt contains no model calls and 900 not-started cells; LA-029 fixed programs and LA-030 constructed development outputs do not supply those measurements.; LA-027 permits automated source-contract and policy-relative effect/utility measurements without outside annotations; expert legal validity and independent human semantic-fidelity claims remain excluded.
- Reuse candidates: papers/completion/law_to_action/benchmark/generated_code_development/loop.py, papers/completion/law_to_action/benchmark/generated_code_development/native_candidate.py, papers/completion/law_to_action/benchmark/generated_code_development/container_runner.py, papers/completion/law_to_action/benchmark/generated_code_development/bounded_http.py, papers/completion/law_to_action/benchmark/protocol.md, papers/completion/law_to_action/benchmark/resource_plan.json
- Receipt: papers/completion/law_to_action/receipts/LA-031.json

Finish the actual scientific work left unrun by LA-016. Use LA-030's concrete native generated-response/effect/repair runner as a development foundation. Implement the missing source-relative tasks, independently computed policy-relative utility/effect oracles, qualified generated-program profile and original arm interventions; qualify actual existing local model transport and runtime; implement durable reservation/resume and complete-attempt resource accounting; then execute and analyze the original complete 900-cell study. Missing readiness is an engineering or qualification task to complete, not a reason to install a permanent false dispatch gate or mark the study completed by a new withdrawal. Preserve original historical receipts and failed attempts. A benchmark omission may be reported truthfully, but it does not satisfy this task's completion acceptance.

Acceptance criteria:

1. Before outcome inspection, freeze exactly 30 new source-lineage families and 60 paired cases: 6 legal, 12 CVE and 12 skill families. Establish lawful immutable source pins, actual source bytes, exact and normalized text hashes, ancestry and nearest-neighbor leakage audit; exclude every LA-004/LA-029 fixed-action family and all its derivatives. Apply the original ranked hash split with salt vericodegen-2026-law-to-action-LA016-v1 and population quotas legal 2/1/3, CVE 2/3/7, skill 2/2/8 for development/calibration/final. All descendant cases inherit their parent split.
2. Implement source-relative prompts/tasks and independent machine-checkable effect/utility expectations for all 60 cases. Retain each source-to-policy/task/oracle mapping. Generated candidates must perform useful bounded work through actual handlers, not select a canned fixed program. The LA-030 two-sink controls remain development evidence and are not relabeled as this cohort. Qualify the generated-code language/handler profile against supported useful tasks and undeclared effects before final release.
3. Implement real A0 task-only, A1 policy prompting, A2 retrieval plus policy, A3 actual policy/UCAN, and A4 full actual native enforcement interventions. Match task source, payload, permitted retrieval, model, decoding, execution bounds and independent scoring within case/seed. Preserve every proposed candidate and observed-feedback repair. Demonstrate actual positive useful-work and negative effect/authorization qualification for each supported mechanism; no inert metadata substitutes for a model intervention.
4. Qualify a concrete actual local model deployment with immutable model/weights/tokenizer/revision/template/deployment hashes, original token ceilings, decoding/seed behavior, exact prompt/template token agreement and measured service resource boundaries. Reuse the model warm during active inference as requested. A bounded runner may replace systemd; do not require an always-on service or reload between ordinary requests. Respect the user's current 10000-second total service wall preference and separate 360-second startup readiness bound while retaining separate original 120-second scientific attempt limits. Preserve actual startup, warm-service, per-call and shutdown/cancellation costs without double counting.
5. Implement and qualify an actual durable full-schedule driver: reserve each case-arm-seed cell and model call before dispatch, retain unknown delivery/usage, continue only after explicit failed-run reconciliation, and never silently refund or replay. Qualify interruption/resume, stale ownership, one-time capability use, complete descendant cleanup and an outer hard 120-second attempt deadline across transport, generated-code execution and cleanup. CPU, memory, token, model-call and paid-budget costs remain known or explicitly unknown, never replaced by configured limits.
6. Freeze the complete balanced original schedule and prospectively qualified code/runtime/model/cohort/prompt/oracle artifacts before scientific outputs. Execute exactly the original 60 cases x 5 arms x seeds 104729/104759/104761, preserving all 900 identities: 180 development, 180 calibration and 540 final. Freeze thresholds/analysis before final outputs. Every planned identity has an accounted terminal disposition; any unrun or unadmitted cell keeps this empirical execution obligation incomplete and remains in reporting denominators.
7. Retain real model HTTP/provider request and response bytes, precise candidate bytes, source/fact/admission identity, actual native handler and durable-consumption evidence, independent observed effect/utility outcomes, repair feedback, model calls/tokens and measured costs for every attempt. At least actual executed model calls and generated programs must exist; constructed transport, model-free LA-029 programs, omission reports and logged intended commands cannot satisfy this requirement.
8. Recompute matched arm comparisons, source-family-aware uncertainty, useful work, forbidden effects, repair behavior and complete cost/omission summaries from the exact admitted records. Keep the generated-code study separate from fixed-action evidence and distinguish policy-relative safety/utility from legal validity or human semantic fidelity. Validate a portable reproducibility package from raw records.
9. Update the editable Law-to-Action manuscript and final local artifact from the actual new evidence, preserving page limits, citation accuracy, anonymity and historical records. Qualify the final source/results/package crosswalk and compilation. No external workshop upload or submission is part of this task. LA-G5 may be completed only when its actual remaining acceptance criteria are met.
10. The dedicated scientific verifier fails if any original scheduled identity is absent, unrun or unadmitted; if real model calls or generated-program execution evidence is missing; if reservation/candidate/admission/effect/cost bindings fail; or if source-family paired analysis or manuscript/package crosswalk cannot be reproduced from raw records. A completed omission cannot pass this verifier.

Execution boundaries and remaining obligations:

```json
{
  "original_study_budget": {
    "planned_cells": 900,
    "final_cells": 540,
    "source_families": 30,
    "paired_cases": 60,
    "arms": [
      "A0",
      "A1",
      "A2",
      "A3",
      "A4"
    ],
    "seeds": [
      104729,
      104759,
      104761
    ],
    "maximum_model_calls_per_attempt": 8,
    "maximum_input_tokens_per_call": 2048,
    "maximum_output_tokens_per_call": 1024,
    "maximum_total_model_calls": 7200,
    "maximum_total_input_output_tokens": 22118400,
    "maximum_wall_seconds_per_attempt": 120,
    "maximum_aggregate_attempt_wall_hours": 30,
    "maximum_parallel_attempts": 1,
    "paid_provider_budget": 0
  },
  "completion_evidence_boundary": "Actual qualified generated-model execution and analysis are required. Readiness reports, development qualification, source freeze alone, missing-runtime reports or manuscript withdrawal do not complete LA-031.",
  "execution_authority": "This file is a concrete task contract for root/native registration, not an instruction to dispatch inference while the current LA-030 development task is running. Registered execution must satisfy the prospective artifact and runtime gates, preserve existing authorization and follow the user's warm-model and bounded-service preferences.",
  "verifier_command": "python3 -B papers/completion/law_to_action/benchmark/generated_code_study/verify_study.py --study papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json --results papers/completion/law_to_action/results/generated_code_study"
}
```
