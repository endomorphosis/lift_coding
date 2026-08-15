# VerifiedGuiOptimizer objective heap

This objective heap is the supervisor-native goal projection for the
VerifiedGuiOptimizer program. The executable taskboard is
implementation_plan/docs/49-verified-gui-optimizer.todo.md and the human
architecture plan is
implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md.

## VGO-G000 Verified GUI optimization with bounded evidence

- Status: pending
- Parent:
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: verified-gui-optimizer
- Bundle: verified-gui-optimizer/root
- Direct child goals: VGO-G010, VGO-G020, VGO-G030, VGO-G040, VGO-G050, VGO-G060, VGO-G070, VGO-G080, VGO-G090, VGO-G100, VGO-G110
- Producing tasks: VGO-099
- Goal: Incrementally analyze and improve the SwissKnife Agent Supervisor console against declared interaction, accessibility, policy, security, state, and visual-regression criteria while retaining exact content-addressed evidence and a reusable, standalone architecture.
- Evidence: VGOEV-G000-ROOT
- Outputs: implementation_plan/evidence/verified_gui_optimizer/final-current-tree-receipt.json, implementation_plan/evidence/verified_gui_optimizer/final-report.md
- Validation: python3 scripts/validate_verified_gui_optimizer_board.py --check-all && scripts/gui-opt report final-current-tree --require-complete --verify-receipts && test -s implementation_plan/evidence/verified_gui_optimizer/final-current-tree-receipt.json && test -s implementation_plan/evidence/verified_gui_optimizer/final-report.md && git diff --check
- Acceptance: Every child goal and all 42 tasks have fresh terminal evidence; the final receipt rehashes the exact current-tree revision and subordinate evidence; exactly 15 benchmark tasks report actual outcomes; accepted changes improve their declared objective without an automatic accessibility, authorization, confirmation, functional, security, or scope regression; the current-tree dependency audit finds no dependency on a prior semantic index or capsule, proof cache, formal-verification cache, or model/provider router; identities establish integrity rather than truth; and the final report uses the bounded claim from the plan without claiming aesthetic optimality.
- Conflict policy: Own only the VGO namespace and declared GUI optimizer paths; preserve unrelated boards, runtime histories, user work, backend authorization, and production service surfaces; never treat a receipt or content identity as a proof cache or as substitute evidence for a check that was not run.

## VGO-G010 Source authority, scope, and security baseline

- Status: pending
- Parent: VGO-G000
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: planning-baseline
- Bundle: verified-gui-optimizer/source-authority
- Direct child goals: none
- Producing tasks: VGO-000, VGO-009
- Goal: Bind the clean control worktree, exact four reviewed commits, canonical versus legacy source findings, selected Agent Supervisor screen, reproducible baseline failures, and browser/host/policy authority before implementation.
- Evidence: VGOEV-G010-SOURCE
- Outputs: implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md, implementation_plan/docs/49-verified-gui-optimizer.objectives.md, implementation_plan/docs/49-verified-gui-optimizer.todo.md, config/verified_gui_optimizer_scheduler.json, scripts/validate_verified_gui_optimizer_board.py, scripts/ops/agent_supervisor/implementation_supervisor_entry.py, scripts/ops/verified_gui_optimizer_vgo009_oracle.py, scripts/ops/verified_gui_optimizer_status.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/authority.py, external/ipfs_accelerate/test/api/test_gui_optimizer_authority.py
- Validation: python3 scripts/validate_verified_gui_optimizer_board.py --check-all && PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ops/verified_gui_optimizer_vgo009_oracle.py --check-all ; cd external/ipfs_accelerate && python3 -m pytest test/api/test_gui_optimizer_authority.py -q
- Acceptance: Source and nested Git revisions match the plan; the target is agent-supervisor; every inspected manifest/registry/policy/test surface has one canonical, projection, duplicate, or legacy disposition; Node/toolchain and pre-existing failures are recorded; browser inputs cannot authorize actions, paths, subprocesses, credentials, or production tools.
- Conflict policy: Record rather than rewrite canonical SwissKnife registries; do not modify the original dirty checkout or infer authority from documentation counts.

## VGO-G020 Closed models, real identities, and receipts

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G010
- Fib priority: 1
- Priority: P0
- Track: contracts-identity
- Bundle: verified-gui-optimizer/contracts
- Direct child goals: none
- Producing tasks: VGO-001, VGO-010, VGO-041
- Goal: Implement all required closed versioned GUI contracts, strict unknown-field rejection, canonical real CIDv1/SHA-256 identities, evidence-level vocabulary, typed receipts, and cross-language golden identity vectors.
- Evidence: VGOEV-G020-CONTRACTS
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/models.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/identity.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/receipts.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_models.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_receipts.py, swissknife/src/services/gui-optimizer/identity.ts, swissknife/test/unit/services/gui-optimizer/identity.test.ts
- Validation: PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ops/verified_gui_optimizer_vgo001_oracle.py --check-all ; cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_models.py tests/unit/logic/gui_optimizer/test_identity.py tests/unit/logic/gui_optimizer/test_receipts.py -q ; cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/identity.test.ts
- Acceptance: Every required model has a schema version and closed decoder; stable identity excludes line-number authority; meaningful component changes alter version identity; unrelated changes preserve stable identity; Python and TypeScript agree on canonical bytes, digest, and valid CIDv1; analysis classification remains independent of verification status.
- Conflict policy: Reuse reviewed strict canonical/CID primitives only; never emit CID-looking placeholders or import semantic-index, previous semantic-capsule, proof-cache, or model-routing code.

## VGO-G030 Safe static analysis, graph, and semantic capsules

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G020
- Fib priority: 1
- Priority: P0
- Track: static-analysis
- Bundle: verified-gui-optimizer/analysis
- Direct child goals: none
- Producing tasks: VGO-002, VGO-011, VGO-012
- Goal: Statically scan the selected JavaScript/template screen and reusable TSX/JSX/HTML/CSS surfaces without executing repository code, then emit typed dependency graphs and compact component/screen capsules with explicit completeness.
- Evidence: VGOEV-G030-ANALYSIS
- Outputs: swissknife/src/services/gui-optimizer/models.ts, swissknife/src/services/gui-optimizer/scanner.ts, swissknife/src/services/gui-optimizer/component-graph.ts, swissknife/src/services/gui-optimizer/ui-capsule.ts, swissknife/test/unit/services/gui-optimizer/scanner.test.ts, swissknife/test/unit/services/gui-optimizer/component-graph.test.ts, swissknife/test/unit/services/gui-optimizer/ui-capsule.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/scanner.test.ts test/unit/services/gui-optimizer/component-graph.test.ts test/unit/services/gui-optimizer/ui-capsule.test.ts
- Acceptance: Required elements, states, handlers, styles, routes, localization, action/policy/browser crossings, tests, and screenshots are represented; every edge has source/target/relation/span/method/confidence/extractor; dynamic uncertainty lowers classification; opaque targets require raw source; arbitrary repository code is never evaluated.
- Conflict policy: Read the live Agent Supervisor source and stable public registries; do not promote archived/mirrored code or the untracked datasets UI/UX IR tree.

## VGO-G040 Explicit state machines and bounded constraints

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G020, VGO-G030
- Fib priority: 1
- Priority: P0
- Track: state-formal-policy
- Bundle: verified-gui-optimizer/formal
- Direct child goals: none
- Producing tasks: VGO-016, VGO-020, VGO-021, VGO-023
- Goal: Derive the selected screen's reachable states/events/recovery paths and verify the bounded state, form, focus, identity, accessibility-structure, confirmation, policy, and action-binding invariants defined in the plan.
- Evidence: VGOEV-G040-FORMAL
- Outputs: swissknife/src/services/gui-optimizer/state-machine.ts, swissknife/test/unit/services/gui-optimizer/state-machine.test.ts, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/formal_adapter.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/invariants.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_formal_adapter.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_invariants.py, swissknife/src/services/gui-optimizer/policy-validator.ts, swissknife/test/unit/services/gui-optimizer/policy-validator.test.ts
- Validation: cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_formal_adapter.py tests/unit/logic/gui_optimizer/test_invariants.py -q ; cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/state-machine.test.ts test/unit/services/gui-optimizer/policy-validator.test.ts
- Acceptance: Undefined targets, incomplete async/failure behavior, impossible required actions, unconfirmed destructive dispatch, stale/browser policy authority, ambiguous bindings, inaccessible forms, and broken modal/focus obligations yield typed counterexamples or unsupported status; supported cvc5 results bind exact inputs; no result claims complete accessibility, security, or aesthetic proof.
- Conflict policy: Use basic reviewed state/SMT facilities without proof caches; preserve runtime host authorization as the authority and never weaken confirmation to satisfy a UI metric.

## VGO-G050 Precise invalidation and compact context

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G030, VGO-G040
- Fib priority: 2
- Priority: P0
- Track: impact-context
- Bundle: verified-gui-optimizer/impact-context
- Direct child goals: none
- Producing tasks: VGO-027, VGO-030
- Goal: Calculate explicit minimal change-impact plans and build deterministic token-accounted context packs with exact edit sources, affected tests/styles, compact unchanged capsules, failures, artifacts, criteria, exclusions, and escalation rules.
- Evidence: VGOEV-G050-CONTEXT
- Outputs: swissknife/src/services/gui-optimizer/invalidation.ts, swissknife/src/services/gui-optimizer/context-pack.ts, swissknife/test/unit/services/gui-optimizer/invalidation.test.ts, swissknife/test/unit/services/gui-optimizer/context-pack.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/invalidation.test.ts test/unit/services/gui-optimizer/context-pack.test.ts
- Acceptance: Implementation, contract, state, style/token, action-binding, and localization changes invalidate the required typed closure without invalidating unrelated application screenshots; uncertainty triggers a documented fallback; opaque/stale/edit targets include raw source; token totals and compression ratio reproduce exactly.
- Conflict policy: No repository-wide semantic index or prior capsule/context system; dependency traversal is local, typed, bounded, and source-addressed.

## VGO-G060 Deterministic evaluation and evidence capture

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G030, VGO-G040
- Fib priority: 2
- Priority: P0
- Track: evaluation
- Bundle: verified-gui-optimizer/evaluation
- Direct child goals: none
- Producing tasks: VGO-003, VGO-031, VGO-032, VGO-034, VGO-040
- Goal: Define controlled evaluation scenarios and deterministic baseline, accessibility, visual, interaction, responsive, localization, reduced-motion, service, confirmation, and objective-metric receipts for the selected screen.
- Evidence: VGOEV-G060-EVALUATION
- Outputs: swissknife/src/services/gui-optimizer/scenario-catalog.ts, swissknife/test/fixtures/gui-optimizer/scenarios/agent-supervisor-scenarios.json, swissknife/test/unit/services/gui-optimizer/scenario-catalog.test.ts, swissknife/src/services/gui-optimizer/accessibility.ts, swissknife/docs/gui-optimizer/ACCESSIBILITY_TOOLING_DECISION.md, swissknife/test/unit/services/gui-optimizer/accessibility.test.ts, swissknife/src/services/gui-optimizer/visual-regression.ts, swissknife/test/unit/services/gui-optimizer/visual-regression.test.ts, swissknife/src/services/gui-optimizer/interaction-runner.ts, swissknife/test/unit/services/gui-optimizer/interaction-runner.test.ts, swissknife/src/services/gui-optimizer/baseline.ts, swissknife/src/services/gui-optimizer/evaluator.ts, swissknife/test/unit/services/gui-optimizer/evaluator.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/scenario-catalog.test.ts test/unit/services/gui-optimizer/accessibility.test.ts test/unit/services/gui-optimizer/visual-regression.test.ts test/unit/services/gui-optimizer/interaction-runner.test.ts test/unit/services/gui-optimizer/evaluator.test.ts
- Acceptance: Required scenarios use frozen fixtures and no production effects; receipts bind exact browser/viewport/locale/text/color/component/source identities; automated accessibility is separated from manual/unsupported criteria; pixel differences use expected/forbidden regions and thresholds; subjective metrics are heuristic or human-reviewed.
- Conflict policy: Extend stable browser harnesses narrowly; do not report synthetic images as live screenshots or automated checks as WCAG certification.

## VGO-G070 Isolated patching and resumable acceptance

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G050, VGO-G060
- Fib priority: 2
- Priority: P0
- Track: improvement-loop
- Bundle: verified-gui-optimizer/execution
- Direct child goals: none
- Producing tasks: VGO-043, VGO-045, VGO-050, VGO-051, VGO-053, VGO-054
- Goal: Enforce declared patch scope, accept caller-selected deterministic/model/human proposals through a vendor-neutral interface, execute only in fenced worktrees, run affected and fallback checks, compare metrics, journal interruption, and admit only complete safe receipts.
- Evidence: VGOEV-G070-LOOP
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/patch_scope.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/proposal.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/worktree_executor.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/check_plan.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/improvement_loop.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/run_journal.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/artifact_store.py, external/ipfs_accelerate/test/api/test_gui_optimizer_patch_scope.py, external/ipfs_accelerate/test/api/test_gui_optimizer_proposal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_worktree_executor.py, external/ipfs_accelerate/test/api/test_gui_optimizer_check_plan.py, external/ipfs_accelerate/test/api/test_gui_optimizer_improvement_loop.py, external/ipfs_accelerate/test/api/test_gui_optimizer_run_journal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_artifact_store.py
- Validation: cd external/ipfs_accelerate && python3 -m pytest test/api/test_gui_optimizer_patch_scope.py test/api/test_gui_optimizer_proposal.py test/api/test_gui_optimizer_worktree_executor.py test/api/test_gui_optimizer_check_plan.py test/api/test_gui_optimizer_improvement_loop.py test/api/test_gui_optimizer_run_journal.py test/api/test_gui_optimizer_artifact_store.py -q
- Acceptance: Undeclared, excessive, unrelated, authorization, credential, arbitrary-HTML, security-disabling, test-deleting, or unverified binding changes are rejected/reviewed; rejected worktrees cannot mutate the canonical branch; affected checks run first with uncertainty fallback; interruption resumes only after identity revalidation; no interface performs model routing.
- Conflict policy: Compose existing supervisor lease/fence/worktree mechanics; do not alter global provider routing, merge policy, backend authorization, or other boards.

## VGO-G080 CLI and controlled conformance fixtures

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G070
- Fib priority: 3
- Priority: P1
- Track: cli-fixtures
- Bundle: verified-gui-optimizer/conformance
- Direct child goals: none
- Producing tasks: VGO-060, VGO-070, VGO-071, VGO-072, VGO-075
- Goal: Expose fixed scan/baseline/impact/evaluate/context/verify/improve/report commands and comprehensive static, formal, security, accessibility, interaction, visual, invalidation, interruption, and determinism fixtures.
- Evidence: VGOEV-G080-CONFORMANCE
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/cli.py, external/ipfs_accelerate/test/api/test_gui_optimizer_cli.py, swissknife/src/services/gui-optimizer/cli.ts, swissknife/test/unit/services/gui-optimizer/cli.test.ts, scripts/gui-opt, swissknife/test/fixtures/gui-optimizer/static/unrelated-style.css, swissknife/test/fixtures/gui-optimizer/static/changed-token.css, swissknife/test/fixtures/gui-optimizer/static/opaque-component.ts, swissknife/test/fixtures/gui-optimizer/static/stale-capsule.json, swissknife/test/unit/services/gui-optimizer/static-impact-context.test.ts, external/ipfs_accelerate/test/fixtures/gui_optimizer/formal-security-cases.json, external/ipfs_accelerate/test/api/test_gui_optimizer_formal_security_fixtures.py, swissknife/test/fixtures/gui-optimizer/browser/a11y-visual-cases.json, swissknife/test/e2e/verified-gui-optimizer-fixtures.spec.ts, external/ipfs_datasets/tests/fixtures/gui_optimizer/identity-vectors.json, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity_vectors.py, swissknife/test/fixtures/gui-optimizer/identity-vectors.json, swissknife/test/unit/services/gui-optimizer/identity-vectors.test.ts
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_cli.py test/api/test_gui_optimizer_formal_security_fixtures.py -q ; cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/cli.test.ts test/unit/services/gui-optimizer/static-impact-context.test.ts test/unit/services/gui-optimizer/identity-vectors.test.ts && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/verified-gui-optimizer-fixtures.spec.ts --reporter=line ; cmp external/ipfs_datasets/tests/fixtures/gui_optimizer/identity-vectors.json swissknife/test/fixtures/gui-optimizer/identity-vectors.json ; cd external/ipfs_datasets && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/logic/gui_optimizer/test_identity_vectors.py -q ; scripts/gui-opt --help
- Acceptance: All eight command families emit closed stable JSON; paths and commands are allowlisted; every required malformed/unsafe/stale/opaque/regression/interrupted fixture has a deterministic expected disposition; repeated identical inputs reproduce baseline and receipt identities.
- Conflict policy: The root adapter is fixed-path and narrow; it may not accept arbitrary commands, create another supervisor, or depend on forbidden prior subsystems.

## VGO-G090 Selected-screen baseline and bounded improvement

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G080
- Fib priority: 3
- Priority: P0
- Track: target-agent-supervisor
- Bundle: verified-gui-optimizer/agent-supervisor-screen
- Direct child goals: none
- Producing tasks: VGO-061, VGO-062, VGO-068, VGO-080, VGO-081
- Goal: Build controlled Agent Supervisor fixtures, semantic and live-browser baselines, apply at most the evidence-supported focus/error-association improvement, and prove that action, confirmation, policy, accessibility, state, and screenshot acceptance gates still hold.
- Evidence: VGOEV-G090-TARGET
- Outputs: swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-host.html, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-services.js, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-scenarios.json, swissknife/test/unit/services/gui-optimizer/agent-supervisor-fixtures.test.ts, swissknife/src/services/gui-optimizer/targets/agent-supervisor.ts, swissknife/test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-semantic-baseline.json, swissknife/build-tools/configs/playwright.verified-gui-optimizer.config.ts, swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-baseline.spec.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline-artifacts.json, swissknife/web/js/apps/agent-supervisor.js, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-proposal.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-improvement-receipt.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-artifacts.json, swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts, swissknife/test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-regression-receipt.json
- Validation: scripts/gui-opt verify agent-supervisor-target --receipt implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-improvement-receipt.json ; cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/agent-supervisor-fixtures.test.ts test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts test/browser/agent-supervisor-console-gateway.test.ts test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/agent-supervisor-console.spec.ts test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts test/e2e/verified-gui-optimizer-agent-supervisor-baseline.spec.ts test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts --reporter=line
- Acceptance: Baseline identities and problems are reproducible; the declared patch stays in scope and measurably improves the objective; focus/error semantics pass live checks; confirmation remains exact; disabled/prohibited paths cannot dispatch; affected visual changes are explained; otherwise the proposal is rejected without canonical mutation.
- Conflict policy: Touch only declared target UI/tests/artifacts; never alter Agent Supervisor backend authorization, credentials, production services, or unrelated SwissKnife applications.

## VGO-G100 Benchmark and adversarial acceptance audit

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G090
- Fib priority: 5
- Priority: P1
- Track: benchmark-audit
- Bundle: verified-gui-optimizer/benchmark
- Direct child goals: none
- Producing tasks: VGO-083, VGO-086, VGO-090, VGO-091, VGO-093
- Goal: Execute the 15 controlled improvement tasks, measure context/invalidation/interaction/accessibility/visual outcomes, exercise hostile proposals, and independently audit every automatic acceptance against scope, confirmation, policy, security, and evidence-level rules.
- Evidence: VGOEV-G100-BENCHMARK
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/benchmark.py, external/ipfs_accelerate/test/fixtures/gui_optimizer/benchmark-tasks.json, external/ipfs_accelerate/test/api/test_gui_optimizer_benchmark_catalog.py, external/ipfs_accelerate/test/fixtures/gui_optimizer/adversarial-proposals.json, external/ipfs_accelerate/test/api/test_gui_optimizer_acceptance_adversarial.py, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.md, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark-artifacts.json, implementation_plan/evidence/verified_gui_optimizer/acceptance-security-audit.json, implementation_plan/evidence/verified_gui_optimizer/current-tree-verification.json
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_benchmark_catalog.py test/api/test_gui_optimizer_acceptance_adversarial.py test/api/test_gui_optimizer_authority.py test/api/test_gui_optimizer_patch_scope.py -q ; cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/policy-validator.test.ts test/browser/all-app-tool-gateway.test.ts test/browser/agent-supervisor-console-gateway.test.ts test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts --reporter=line ; scripts/gui-opt report benchmark-agent-supervisor --require-complete --expected-tasks 15 --verify-receipts && scripts/gui-opt report acceptance-security-audit --require-complete --verify-receipts && scripts/gui-opt verify final-current-tree --full --receipt implementation_plan/evidence/verified_gui_optimizer/current-tree-verification.json
- Acceptance: Actual results are reported for exactly 15 controlled tasks; median context reduction and invalidation precision are measured; every automatic acceptance is independently audited; no critical accessibility or authorization/confirmation regression is automatically accepted; accepted tasks improve their declared metric; rejected/human-review cases retain reasons and proposal method; and full-current-tree evidence records a fail-closed forbidden-dependency audit for the standalone package boundaries.
- Conflict policy: Benchmark fixtures are nonproduction and deterministic; do not cherry-pick successes, conceal target misses, or convert heuristic design ratings into verified facts.

## VGO-G110 Architecture and application-extension guidance

- Status: pending
- Parent: VGO-G000
- Depends on: VGO-G100
- Fib priority: 5
- Priority: P0
- Track: closeout
- Bundle: verified-gui-optimizer/closeout
- Direct child goals: none
- Producing tasks: VGO-096
- Goal: Publish the implemented formal/structural/heuristic/human evidence architecture, standalone dependency boundary, non-goals, commands, and exact prerequisites for adapting one additional application.
- Evidence: VGOEV-G110-CLOSEOUT
- Outputs: swissknife/docs/gui-optimizer/ARCHITECTURE.md, external/ipfs_datasets/docs/gui_optimizer_contracts.md, external/ipfs_accelerate/docs/architecture/VERIFIED_GUI_OPTIMIZER.md, external/ipfs_accelerate/test/api/test_gui_optimizer_architecture_docs.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_architecture_docs.py -q ; PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_verified_gui_optimizer_board.py --check-all && git diff --check
- Acceptance: Documentation names the selected screen and exact implementation boundaries; separates formal, structural, integrity, simulated, heuristic, and human evidence; explains that content identities and receipts do not prove truth; documents the prohibition on prior semantic-index/capsule, proof-cache, formal-verification-cache, and model-routing dependencies; records exclusions and non-goals; and lists exact manifest, target, scenario, action, policy, test, screenshot, and acceptance additions needed for another application.
- Conflict policy: Documentation reflects immutable current-tree evidence only; it may not rewrite failed results, delete runtime history, auto-release to users, broaden optimization to other applications, or present a forbidden prior subsystem as an implementation dependency.
