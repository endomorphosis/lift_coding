#!/usr/bin/env python3
"""Generate and validate the sealed DOEP bootstrap controls.

This file describes one bounded campaign.  It does not implement a planner,
scheduler, queue, state owner, or model router.  The generated JSON population
is consumed by the existing DatabaseTaskSource, while the Markdown projection
is consumed by the existing configured-board scheduler.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "agent-supervisor-direct-objective-and-event-driven-planning-v1"
PLAN_REVISION = "DOEP-PLAN-V2"
ROOT_GOAL = "DOEP-G000"
BRANCH = "agent/agent-supervisor-direct-objective-and-event-driven-planning-v1"
BASES = {
    "lift_coding": {
        "commit": "bb8869ed72eb7002434345d9969efee729c4f7f6",
        "tree": "99e85bfe584b7688ffbeff86da1e612dd6893a42",
    },
    "ipfs_accelerate_py": {
        "commit": "f8c2f633fa6a781b822176fd63e1a229f96b581c",
        "tree": "c52908e40287051336d81c81a8f4799869846f03",
    },
    "ipfs_datasets_py": {
        "commit": "f49afc579c22856849ca9f739435e5820003384f",
        "tree": "47118a8e6d1b6b4e7ae04f9a2efda33aadebca1b",
    },
    "ipfs_kit_py": {
        "commit": "b6c65ba732733d7e33852713ba18aa3b12235668",
        "tree": "14da7d92e130b7ba3523d0d6741a3ef7ef1e1bc2",
    },
}

REPOSITORIES = {
    "ACC": "external/ipfs_accelerate",
    "DATA": "external/ipfs_datasets",
    "KIT": "external/ipfs_kit",
}

BUDGETS = {
    "B0": dict(max_input_tokens=8000, max_output_tokens=2000, max_model_calls=1,
               max_frontier_model_calls=0, max_provider_cost_usd=1, max_cpu_seconds=600,
               max_gpu_seconds=0, max_test_seconds=300, max_prover_seconds=0,
               max_wall_seconds=3600, validation_reserve_percent=25),
    "B1": dict(max_input_tokens=16000, max_output_tokens=5000, max_model_calls=2,
               max_frontier_model_calls=0, max_provider_cost_usd=3, max_cpu_seconds=1200,
               max_gpu_seconds=0, max_test_seconds=900, max_prover_seconds=600,
               max_wall_seconds=7200, validation_reserve_percent=25),
    "B2": dict(max_input_tokens=32000, max_output_tokens=10000, max_model_calls=4,
               max_frontier_model_calls=1, max_provider_cost_usd=10, max_cpu_seconds=3600,
               max_gpu_seconds=900, max_test_seconds=1800, max_prover_seconds=900,
               max_wall_seconds=14400, validation_reserve_percent=25),
    "B3": dict(max_input_tokens=48000, max_output_tokens=14000, max_model_calls=5,
               max_frontier_model_calls=1, max_provider_cost_usd=20, max_cpu_seconds=7200,
               max_gpu_seconds=1800, max_test_seconds=3600, max_prover_seconds=1800,
               max_wall_seconds=28800, validation_reserve_percent=30),
    "B4": dict(max_input_tokens=24000, max_output_tokens=6000, max_model_calls=2,
               max_frontier_model_calls=0, max_provider_cost_usd=10, max_cpu_seconds=14400,
               max_gpu_seconds=3600, max_test_seconds=7200, max_prover_seconds=3600,
               max_wall_seconds=86400, validation_reserve_percent=25),
    "B5": dict(max_input_tokens=120000, max_output_tokens=30000, max_model_calls=20,
               max_frontier_model_calls=4, max_provider_cost_usd=75, max_cpu_seconds=28800,
               max_gpu_seconds=7200, max_test_seconds=14400, max_prover_seconds=7200,
               max_wall_seconds=172800, validation_reserve_percent=30),
    "B6": dict(max_input_tokens=160000, max_output_tokens=40000, max_model_calls=30,
               max_frontier_model_calls=5, max_provider_cost_usd=100, max_cpu_seconds=43200,
               max_gpu_seconds=10800, max_test_seconds=21600, max_prover_seconds=10800,
               max_wall_seconds=259200, validation_reserve_percent=30),
}

GOAL_DEFS = [
    ("DOEP-G010", ROOT_GOAL, "Seal current authority and baseline", "Inventory the canonical objective, task, event, state and cross-repository authorities and freeze a reproducible baseline."),
    ("DOEP-G020", ROOT_GOAL, "Direct objective contracts and interfaces", "Expose one authenticated, delegated, idempotent objective service through thin Python, CLI, MCP and MCP++ adapters."),
    ("DOEP-G030", ROOT_GOAL, "Consolidated staged objective compiler", "Extend the existing compiler/materializer with deterministic normalization, repository analysis, semantic decomposition and bounded residual interpretation."),
    ("DOEP-G040", ROOT_GOAL, "Canonical event path", "Consolidate versioned event envelopes, durable publication, idempotent consumption, replay, causal ordering and sibling validation."),
    ("DOEP-G050", ROOT_GOAL, "Canonical task state machine", "Formalize one revision/CAS, lease/fence, reconciliation and recovery state machine with model-based invariant tests."),
    ("DOEP-G060", ROOT_GOAL, "Incremental reassessment and bounded refill", "Compute minimal impact, apply PlanDelta, refill only logically necessary tasks and enforce convergence and stop conditions."),
    ("DOEP-G070", ROOT_GOAL, "Cross-repository ContextPacks", "Keep semantic construction in Datasets, durable exact bytes and CAS in Kit, and freshness/admission/routing in Accelerate."),
    ("DOEP-G080", ROOT_GOAL, "Deterministic-first route ladder", "Prefer exact receipt reuse, static analysis, selected tests and proofs before bounded model and human escalation."),
    ("DOEP-G090", ROOT_GOAL, "Logic-constrained incremental planning", "Add assume-guarantee, affected-suffix, counterexample, interpolation, CEGAR and semantic-equivalence planning."),
    ("DOEP-G100", ROOT_GOAL, "Typed deterministic-first synthesis", "Consolidate typed PatchPlan, allowlisted synthesis, bounded model fallback and proof/test merge admission."),
    ("DOEP-G110", ROOT_GOAL, "Sibling-supervisor interoperability", "Coordinate capability, task request, receipt and event contracts without cross-supervisor direct state writes."),
    ("DOEP-G120", ROOT_GOAL, "Measurement harnesses and populations", "Instrument the whole pipeline and build reproducible baseline, candidate, corpus, shadow and gated canary inputs."),
    ("DOEP-G130", ROOT_GOAL, "Paired qualification and honest release", "Run paired qualification, demonstrations and guarded cohorts, then issue a closed promotion or non-promotion receipt."),
]

SUBGOALS = {
    "DOEP-G010": ("authority inventory", "reproducible baseline"),
    "DOEP-G020": ("contracts", "canonical service and security", "adapters and parity"),
    "DOEP-G030": ("compiler spine", "semantic decomposition", "plan validation"),
    "DOEP-G040": ("schema and publication", "consumption and recovery", "sibling validation"),
    "DOEP-G050": ("state and CAS", "reconciliation and recovery", "invariant qualification"),
    "DOEP-G060": ("impact and delta", "event reassessment and refill", "convergence and stop"),
    "DOEP-G070": ("semantic build and durable store", "admission and lifecycle", "qualification"),
    "DOEP-G080": ("route implementation", "explanation and quality"),
    "DOEP-G090": ("contracts", "affected-region refinement", "equivalence"),
    "DOEP-G100": ("contract", "synthesis", "admission and merge"),
    "DOEP-G110": ("capability and contracts", "reassessment and isolation"),
    "DOEP-G120": ("instrumentation and harness", "corpora", "guarded cohorts"),
    "DOEP-G130": ("reproducible evaluation", "live gates", "release report"),
}

# id|title|phase goal|subgoal ordinal|owner|dependencies|risk|authority|budget|canonical target
TASK_ROWS = r"""
000|Inventory current objective, planner, task, event, and state authorities|DOEP-G010|1|ACC||R0|O0|B0|docs/architecture/agent_supervisor/DOEP_AUTHORITY_ADR.md
001|Seal current Codex-primed baseline|DOEP-G010|2|ACC||R0|O0|B1|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/baseline_manifest.py
002|Inventory direct-state-write and controller bypasses|DOEP-G010|1|ACC||R0|O0|B0|artifacts/agent_supervisor_direct_objective_event_driven_planning/inventory/direct_state_writes.json
003|Seal current cross-repository contracts and commits|DOEP-G010|1|ACC||R0|O0|B0|artifacts/agent_supervisor_direct_objective_event_driven_planning/inventory/repository_contract_seal.json
010|Define SupervisorObjectiveIntent contract|DOEP-G020|1|DATA|000,003|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
011|Define ObjectiveMaterializationReceipt contract|DOEP-G020|1|DATA|010|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
012|Implement canonical objective-submission service|DOEP-G020|2|ACC|000,010,011|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/intent_service.py
013|Add Python client|DOEP-G020|3|ACC|012,016|R2|A1|B1|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/facade.py
014|Add CLI client|DOEP-G020|3|ACC|012,016|R2|A1|B1|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/cli.py
015|Add MCP/MCP++ adapters|DOEP-G020|3|ACC|012,016|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/agent_supervisor_tools/prompt_entrypoints.py
016|Add authentication, delegation, idempotency, and typed errors|DOEP-G020|2|ACC|002,010,012|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/authority_resolver.py
017|Prove cross-adapter identity parity|DOEP-G020|3|ACC|013,014,015,016|R2|A1|B2|external/ipfs_accelerate/test/api/doep/test_cross_adapter_identity.py
020|Consolidate objective compiler|DOEP-G030|1|ACC|000,001,003|R1|A1|B1|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_compiler.py
021|Add deterministic normalization|DOEP-G030|1|DATA|010,020|R2|S1|B2|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
022|Add repository/capability analysis|DOEP-G030|1|ACC|003,020|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_context.py
023|Add rule-driven objective decomposition|DOEP-G030|2|DATA|021,022|R2|S1|B2|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
024|Add assumptions, guarantees, non-goals, and acceptance conditions|DOEP-G030|2|DATA|010,023|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
025|Add unresolved-question contract|DOEP-G030|2|DATA|024|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
026|Add logic-constrained residual interpretation|DOEP-G030|2|DATA|022,025|R2|S1|B3|external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py
027|Add plan validation and completeness witness|DOEP-G030|3|ACC|016,023,024,025,026|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_validator.py
030|Define canonical event schema|DOEP-G040|1|DATA|000,003|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/schema_registry.py
031|Add transactional event publication|DOEP-G040|1|KIT|030|R3|S1|B3|external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/coordination_storage.py
032|Add idempotent event consumption and cursors|DOEP-G040|2|ACC|030,031|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/database_event_log.py
033|Add materialized-state replay and recovery|DOEP-G040|2|ACC|031,032|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/database_event_log.py
034|Add event coalescing and causal ordering|DOEP-G040|2|ACC|030,032|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/event_log.py
035|Add sibling-supervisor event validation|DOEP-G040|3|ACC|003,030,032|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py
040|Formalize canonical task state machine|DOEP-G050|1|ACC|000,030|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/control_plane_contracts.py
041|Enforce revision/CAS transitions|DOEP-G050|1|ACC|031,040|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/control_plane_transactions.py
042|Enforce claims, leases, fencing, and idempotency|DOEP-G050|1|ACC|016,041|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/quack_owner_mutation.py
043|Add unknown-provider-outcome reconciliation|DOEP-G050|2|ACC|040,041,042|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/provider_execution.py
044|Add owner-loss and owner-restart recovery|DOEP-G050|2|ACC|033,042,043|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/external_quack_owner.py
045|Add stale-plan-epoch handling|DOEP-G050|2|ACC|040,041|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/plan_revision_store.py
046|Add model-based and temporal invariant tests|DOEP-G050|3|ACC|030,031,032,033,034,035,040,041,042,043,044,045|R3|A2|B4|external/ipfs_accelerate/test/api/doep/test_control_plane_model.py
050|Implement incremental plan-impact analysis|DOEP-G060|1|ACC|022,027,030|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/dynamic_impact_frontier.py
051|Add event-driven reassessment|DOEP-G060|2|ACC|032,045,050|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/refill_event_adapter.py
052|Add PlanDelta contract|DOEP-G060|1|DATA|030,050|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
053|Add automatic bounded task refill|DOEP-G060|2|ACC|051,052|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/refill_controller.py
054|Add task semantic deduplication|DOEP-G060|2|ACC|023,053|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/semantic_refill.py
055|Add oscillation, runaway, and nonconvergence controls|DOEP-G060|3|ACC|052,053,054|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/campaign_refill_policy.py
056|Add objective satisfaction and stop conditions|DOEP-G060|3|ACC|027,051,053,055|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py
060|Define SupervisorContextPack contract|DOEP-G070|1|DATA|003,010|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/proof_context/context_pack.py
061|Implement Datasets semantic builder|DOEP-G070|1|DATA|022,060|R2|S1|B3|external/ipfs_datasets/ipfs_datasets_py/proof_context/context_pack.py
062|Implement Kit durable storage and current-root CAS|DOEP-G070|1|KIT|003,031,060|R3|S1|B3|external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/coordination_storage.py
063|Implement Accelerate freshness and selection|DOEP-G070|2|ACC|060,061,062|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/context/context_compiler.py
064|Add incremental context expansion|DOEP-G070|2|DATA|061,062,063|R2|S1|B2|external/ipfs_datasets/ipfs_datasets_py/proof_context/context_pack.py
065|Add ContextPack invalidation|DOEP-G070|2|ACC|030,063,064|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/context/context_contracts.py
066|Benchmark ContextPack reuse and omissions|DOEP-G070|3|ACC|063,064,065|R2|A1|B4|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/context_pack.py
070|Consolidate deterministic-first routing|DOEP-G080|1|ACC|000,001,022|R1|A1|B1|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/model_route.py
071|Add exact receipt reuse|DOEP-G080|1|ACC|003,070|R3|A2|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py
072|Add AST/dependency/static analysis routing|DOEP-G080|1|ACC|022,070|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/analysis_ast_index.py
073|Add selected-test and prover routing|DOEP-G080|1|ACC|060,070,072|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/task_proposal_router.py
074|Add small/medium/frontier escalation policy|DOEP-G080|1|ACC|071,072,073|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/model_route.py
075|Add route explanations and receipts|DOEP-G080|2|ACC|030,074|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/decision_receipts.py
076|Add unnecessary-escalation detection|DOEP-G080|2|ACC|074,075|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/supervisor_efficiency_metrics.py
080|Add assume-guarantee planning contracts|DOEP-G090|1|DATA|024,027,060|R2|S1|B2|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
081|Add affected-suffix replanning|DOEP-G090|2|ACC|050,052,080|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_replanner.py
082|Add counterexample and unsat-core refinement|DOEP-G090|2|DATA|073,080,081|R2|S1|B3|external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/counterexamples/explanation.py
083|Add bounded Craig-interpolation planning assistance where qualified|DOEP-G090|2|DATA|082|R2|S1|B3|external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/interpolation.py
084|Add CEGAR plan refinement|DOEP-G090|2|ACC|081,082,083|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_replanner.py
085|Add equivalent-task and equivalent-plan elimination|DOEP-G090|3|DATA|054,084|R2|S1|B3|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
090|Define SupervisorPatchPlan|DOEP-G100|1|DATA|060,080|R1|S1|B1|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
091|Add deterministic synthesis allowlist|DOEP-G100|2|ACC|072,090|R2|A1|B2|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/program_repair_synthesis.py
092|Add bounded model-assisted synthesis|DOEP-G100|2|ACC|063,074,090|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/program_repair_synthesis.py
093|Add patch scope and semantic-nonempty validation|DOEP-G100|3|ACC|090,091,092|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/scope_adjudication.py
094|Add proof/test-based merge admission|DOEP-G100|3|ACC|042,073,093|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/post_merge_validation.py
100|Add sibling supervisor capability registry|DOEP-G110|1|ACC|003,016,030|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py
101|Add cross-supervisor task requests|DOEP-G110|1|DATA|010,060,100|R1|S1|B2|external/ipfs_datasets/ipfs_datasets_py/logic/external_work_plan_obligations.py
102|Add cross-supervisor receipts|DOEP-G110|1|ACC|062,101|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py
103|Add cross-repository incremental reassessment|DOEP-G110|2|ACC|035,051,052,102|R3|A2|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py
104|Prove no cross-supervisor direct state writes|DOEP-G110|2|ACC|046,100,101,102,103|R3|A2|B4|external/ipfs_accelerate/test/api/doep/test_cross_supervisor_isolation.py
110|Instrument end-to-end token and compute telemetry|DOEP-G120|1|ACC|066,075|R2|A1|B3|external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/benchmark_telemetry.py
111|Build Codex-primed baseline harness|DOEP-G120|1|ACC|001,110|R2|A1|B3|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/baseline.py
112|Build direct-supervisor candidate harness|DOEP-G120|1|ACC|027,056,074,110|R2|A1|B3|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/candidate.py
113|Build hermetic objective corpus|DOEP-G120|2|ACC|027,110|R1|A1|B3|external/ipfs_accelerate/test/fixtures/agent_supervisor_doep/hermetic_objectives.json
114|Build historical replay corpus|DOEP-G120|2|ACC|001,110|R1|A1|B3|external/ipfs_accelerate/test/fixtures/agent_supervisor_doep/historical_replays.json
115|Build held-out objective corpus|DOEP-G120|2|ACC|027,110,113|R1|A1|B2|external/ipfs_accelerate/test/fixtures/agent_supervisor_doep/held_out_objectives.json
116|Add live shadow cohort|DOEP-G120|3|ACC|017,046,056,103,104,110,115|R3|L1|B3|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/live_shadow.py
117|Add low-risk canary cohort|DOEP-G120|3|ACC|046,104,116|R4|H1|B3|external/ipfs_accelerate/benchmarks/agent_supervisor/doep/low_risk_canary.py
120|Run hermetic paired benchmark|DOEP-G130|1|ACC|111,112,113|R2|A1|B5|artifacts/agent_supervisor_direct_objective_event_driven_planning/benchmarks/hermetic_paired.json
121|Run historical paired replay|DOEP-G130|1|ACC|111,112,114|R2|A1|B5|artifacts/agent_supervisor_direct_objective_event_driven_planning/benchmarks/historical_paired.json
122|Run held-out plan-quality evaluation|DOEP-G130|1|ACC|112,115|R2|A1|B5|artifacts/agent_supervisor_direct_objective_event_driven_planning/benchmarks/held_out_plan_quality.json
123|Run live shadow campaign|DOEP-G130|2|ACC|046,104,116,120,121,122|R4|L1|B6|artifacts/agent_supervisor_direct_objective_event_driven_planning/benchmarks/live_shadow.json
124|Run low-risk canary|DOEP-G130|2|ACC|117,123|R4|H1|B6|artifacts/agent_supervisor_direct_objective_event_driven_planning/benchmarks/low_risk_canary.json
125|Produce promotion or honest non-promotion receipt|DOEP-G130|3|ACC|066,076,104,120,121,122,123,124|R4|H1|B3|artifacts/agent_supervisor_direct_objective_event_driven_planning/release/promotion_decision.json
126|Publish residual-gap and marginal-return report|DOEP-G130|3|ACC|125|R1|A1|B2|artifacts/agent_supervisor_direct_objective_event_driven_planning/release/release_report.json
""".strip()

PHASE_DESCRIPTION = {
    "DOEP-G010": "Bootstrap facts only; defer unrelated findings.",
    "DOEP-G020": "One service layer and thin adapters; callers never supply authoritative policy.",
    "DOEP-G030": "Deterministic and semantic stages precede any bounded specialist model.",
    "DOEP-G040": "At-least-once delivery with idempotent, exactly-once logical transitions.",
    "DOEP-G050": "No stale lease, fence, policy, tree or plan epoch may complete.",
    "DOEP-G060": "Only impacted suffixes change; ordinary frontier refill is model-free and bounded.",
    "DOEP-G070": "Semantic, durable-byte and execution-admission authorities remain separated.",
    "DOEP-G080": "Route order is receipt, static, selected tests, proof, small, medium, frontier, human.",
    "DOEP-G090": "Formal methods are qualified by measured benefit and have explicit fallbacks.",
    "DOEP-G100": "A model assertion is never patch acceptance evidence.",
    "DOEP-G110": "Sibling supervisors exchange events and receipts, never database writes.",
    "DOEP-G120": "Missing measurements remain missing, never zero or estimated-as-measured.",
    "DOEP-G130": "Promotion thresholds and zero safety gates cannot be weakened.",
}

TYPED_NON_SUCCESS = [
    "blocked_dependency", "blocked_authority", "blocked_policy",
    "budget_exhausted", "validation_failed", "provider_outcome_unknown",
    "quarantined_nonconvergent", "cancelled",
]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def cid(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def parse_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for ordinal, line in enumerate(TASK_ROWS.splitlines(), 1):
        number, title, phase, subordinal, owner, deps, risk, authority, budget, target = line.split("|", 9)
        task_id = f"DOEP-{number}"
        repo_slug = {"ACC": "accelerate", "DATA": "datasets", "KIT": "kit"}[owner]
        test_path = f"external/ipfs_{repo_slug}/tests/doep/test_{task_id.lower().replace('-', '_')}_{slug(title)[:52]}.py"
        if owner == "ACC":
            test_path = f"external/ipfs_accelerate/test/api/doep/test_{task_id.lower().replace('-', '_')}_{slug(title)[:52]}.py"
        receipt = f"artifacts/agent_supervisor_direct_objective_event_driven_planning/receipts/{task_id}.json"
        output_manifest = f"artifacts/agent_supervisor_direct_objective_event_driven_planning/outputs/{task_id}.json"
        repository = REPOSITORIES[owner]
        root_owner = repository == "ipfs_accelerate_py"

        def owner_relative(path: str) -> str:
            prefix = repository + "/"
            return path if root_owner or not path.startswith(prefix) else path[len(prefix):]

        declared_outputs = [
            owner_relative(target),
            owner_relative(test_path),
            owner_relative(output_manifest),
            owner_relative(receipt),
        ]
        superproject_outputs = [
            path if root_owner else f"{repository}/{path}"
            for path in declared_outputs
        ]
        validation = (
            ["python3", "scripts/run_agent_supervisor_direct_objective_event_driven_planning_validation.py", "--task", task_id]
            if root_owner
            else ["python3", "-m", "pytest", "-q", owner_relative(test_path)]
        )
        task = {
            "stable_task_id": task_id,
            "task_id": task_id,
            "task_alias": task_id,
            "title": title,
            "status": "todo",
            "priority": "P0" if not deps else ("P1" if phase in {"DOEP-G020", "DOEP-G030", "DOEP-G040"} else "P2"),
            "root_goal_id": ROOT_GOAL,
            "parent_goal_id": phase,
            "subgoal_id": f"{phase}.S{subordinal}",
            "owning_repository": repository,
            "repository_authority": owner,
            "plan_revision": PLAN_REVISION,
            "plan_epoch": 1,
            "base_repositories": BASES,
            "dependencies": [f"DOEP-{item}" for item in deps.split(",") if item],
            "exact_inputs": [PLAN_REVISION, "exact source forest", "current dependency receipts", "current policy and toolchain identities"],
            "exact_outputs": declared_outputs,
            "superproject_outputs": superproject_outputs,
            "outputs": [
                {"path": declared_outputs[0], "kind": "primary"},
                {"path": declared_outputs[1], "kind": "independent_test"},
                {"path": declared_outputs[2], "kind": "output_manifest"},
                {"path": declared_outputs[3], "kind": "candidate_receipt"},
            ],
            "primary_output": declared_outputs[0],
            "test_output": declared_outputs[1],
            "output_manifest": declared_outputs[2],
            "receipt_output": declared_outputs[3],
            "superproject_test_output": superproject_outputs[1],
            "superproject_receipt_output": superproject_outputs[3],
            "owned_files": declared_outputs,
            "read_scope": ["declared dependency cone", "admitted current receipts", "canonical interfaces named in the plan"],
            "write_scope": declared_outputs,
            "allowed_effects": ["isolated worktree edits", "local deterministic validation", "reviewed merge request through canonical authority"],
            "forbidden_effects": ["direct DuckDB or DuckLake write", "policy-pointer mutation", "task terminalization", "credential access", "scope expansion"],
            "preconditions": [
                "Exact base commit/tree or a current re-admission receipt for this plan epoch",
                "Every dependency has a current admitted success receipt",
                "Delegated repository, path, method and effect authority is current",
                "At least the declared validation reserve remains available",
            ],
            "postconditions": [
                "All exact outputs exist inside the declared write scope",
                "The exact validation argv exits zero on the resulting tree",
                "Changed paths, commit, tree, CIDs, authority and limitations are in the canonical receipt",
                "No truth, safety, authority or promotion gate has been weakened",
            ],
            "risk_class": risk,
            "authority_requirement": authority,
            "budget_profile": budget,
            "budgets": {**BUDGETS[budget], "max_concurrent_tasks": 1},
            "validation_profile": f"doep-validation/{PLAN_REVISION}/{task_id}@1",
            "execution_validation": [validation],
            "validations": [{"argv": validation, "shell": False}],
            "acceptance": f"Independently verify that '{title}' satisfies the plan-bound task contract, exact outputs and current-tree tests; a worker or model assertion alone is insufficient.",
            "required_evidence": ["source commit/tree/gitlinks", "changed-path digest", "test/proof results", "receipt CID", "limitations", "verifier admission"],
            "proof_obligations": ["authority and scope preservation", "no stale evidence admission", "declared semantic or operational property"],
            "test_obligations": [declared_outputs[1], "current protected regression subset selected by impact analysis"],
            "terminal_success": "Current independent validation and required receipts are admitted; postconditions hold; no required effect is unknown.",
            "terminal_non_success": TYPED_NON_SUCCESS,
            "unknown_effect_rule": "provider_outcome_unknown enters reconciliation and is never blindly retried",
            "rollback": "Reject or revert through the existing merge/rollback authority; invalidate successor receipts without rewriting history.",
            "conflict_policy": "Serialize overlapping schemas, exports, registries, state/CAS, merge and release artifacts; rebase and revalidate current evidence.",
            "objective": f"Extend the current canonical implementation to {title.lower()} without creating a competing subsystem.",
            "completion_mode": "independent_evidence_and_canonical_cas",
            "externally_claimable": authority in {"S1", "L1"},
        }
        task["task_cid"] = cid({
            "task_id": task_id,
            "plan_revision": PLAN_REVISION,
            "parent_goal_id": phase,
            "subgoal_id": task["subgoal_id"],
            "dependencies": task["dependencies"],
            "exact_outputs": task["exact_outputs"],
        })
        if task_id in {"DOEP-124", "DOEP-125"}:
            task["human_gate"] = "An absent or denied human gate closes with a typed not_run/non-promotion receipt; it never remains silently in progress."
        tasks.append(task)
    return tasks


def goals() -> list[dict[str, Any]]:
    result = [{
        "goal_id": ROOT_GOAL, "goal_alias": ROOT_GOAL, "title": "Direct objective and event-driven planning",
        "parent_goal_id": "", "ordinal": 1, "status": "open",
        "objective": "Make the existing supervisor directly invokable from a high-level idea, then incrementally plan, execute, reassess and explain under exact authority and evidence.",
    }]
    ordinal = 2
    for phase_id, parent, title, objective in GOAL_DEFS:
        result.append({"goal_id": phase_id, "goal_alias": phase_id, "title": title, "parent_goal_id": parent, "ordinal": ordinal, "status": "open", "objective": objective})
        ordinal += 1
        for subordinal, subgoal_title in enumerate(SUBGOALS[phase_id], 1):
            sub_id = f"{phase_id}.S{subordinal}"
            result.append({"goal_id": sub_id, "goal_alias": sub_id, "title": subgoal_title, "parent_goal_id": phase_id, "ordinal": ordinal, "status": "open", "objective": f"Complete the {subgoal_title} portion of {title.lower()}."})
            ordinal += 1
    goal_cids = {
        item["goal_id"]: cid({"goal_id": item["goal_id"], "plan_revision": PLAN_REVISION})
        for item in result
    }
    for item in result:
        item["goal_cid"] = goal_cids[item["goal_id"]]
        item["parent_goal_cid"] = goal_cids.get(item["parent_goal_id"], "")
        item["objective_id"] = PROGRAM_ID
        item["objective_alias"] = "DOEP"
        item["priority"] = "P0" if item["goal_id"] == ROOT_GOAL else "P1"
    return result


def plan_identity(tasks: list[dict[str, Any]], goal_rows: list[dict[str, Any]]) -> str:
    return cid({"program": PROGRAM_ID, "revision": PLAN_REVISION, "bases": BASES, "goals": goal_rows, "tasks": tasks})


def render_plan(tasks: list[dict[str, Any]], goal_rows: list[dict[str, Any]], plan_cid: str) -> str:
    lines = [
        f"# Agent Supervisor Direct Objective and Event-Driven Planning — {PLAN_REVISION}", "",
        f"Program: `{PROGRAM_ID}`", f"Plan CID: `{plan_cid}`", "Status: sealed bootstrap campaign; execution is owned by the existing supervisor.", "",
        "## Outcome", "",
        "A human or delegated external agent submits one bounded high-level idea. The existing supervisor authenticates it, compiles a versioned semantic objective and partial-order plan, persists canonical state, opens a bounded executable frontier, incrementally reacts to authoritative events, and stops on admitted satisfaction or a typed terminal condition. No custom Codex campaign prompt is required after qualification.", "",
        "## Immutable source forest", "",
        "| Repository | Commit | Tree |", "|---|---|---|",
    ]
    for name, identity in BASES.items():
        lines.append(f"| `{name}` | `{identity['commit']}` | `{identity['tree']}` |")
    lines += [
        "", "Branch names are navigation only. Every task and receipt is bound to exact commits, trees, plan epoch, policy and validation identity.", "",
        "## Canonical consolidation decision", "",
        "- Objective path: existing `objectives` heap/refinery plus `entrypoints.intent_service` and `plan_materializer`.",
        "- Planner: existing formal plan compiler/validator/replanner and adaptive planner; no second planner family.",
        "- Operational task authority: `DatabaseTaskSource@1` and its existing DuckDB intent repository, served to concurrent workers only by one authenticated `QuackStateServer@1` owner.",
        "- Event path: existing database event log, runtime CAS and durable Kit storage adapters.",
        "- Refill path: existing refill controller/event adapter/semantic refill/campaign policy.",
        "- Model route: existing route planner and proposal router, extended into the required deterministic-first ladder.",
        "- DuckLake: optional, rebuildable, append-only history/analytics projection; never scheduling, completion, policy or proof authority.",
        "- Datasets owns semantic identity, schemas, ContextPack meaning, formal translation and proof relationships. Kit owns exact durable bytes, CIDs, WAL, recovery and current-root CAS. Accelerate owns operational admission, execution, validation, merge, recovery and terminalization.", "",
        "The dormant prompt-first facade is not used as false authority at bootstrap: on the sealed base it fails closed without a production intent factory and complete launch plan. DOEP consolidates and qualifies that intended surface. The reviewed bootstrap route is sealed objective/board → canonical JSON materialization → DuckDB → exclusive Quack owner → existing configured multi-lane supervisor.", "",
        "### Bootstrap revision history", "",
        "`DOEP-PLAN-V1` failed closed before provider dispatch because task records used GitHub authority names where the existing worktree allocator requires configured local gitlink identities. Its complete DuckDB event stream and logs are retained as a superseded failed generation. `DOEP-PLAN-V2` separates semantic repository authority from operational gitlink identity, declares nested-repository outputs relative to their owner, and seals their exact superproject projections for independent validation.", "",
        "## Compiler and execution sequence", "",
        "1. Deterministically validate, normalize scope/budgets/risk, bind repository and policy, and reject authority/path escapes.",
        "2. Inspect manifests, objective/task state, dependency and symbol indexes, schemas, tests, proofs, capabilities, receipts and relevant failures.",
        "3. Apply rule/template decomposition for known objective classes.",
        "4. Send only named unresolved semantic questions and the smallest adequate ContextPack to the smallest adequate specialist; typed output cannot execute tools.",
        "5. Validate contribution, exact outputs/evidence, acyclicity, authority, feasibility, deduplication and explicit assumptions before materialization.",
        "6. Execute the route ladder: exact receipt reuse → AST/symbol/dependency analysis → semantic/interface diff → static/contracts → selected tests → selected proofs → small → medium → frontier → human.",
        "7. On an authoritative event, compute the minimal impact cone, preserve unaffected receipts/tasks, emit PlanDelta and a refill decision, and add only necessary tasks under epoch/wave/convergence limits.", "",
        "## Truth, safety and stop rules", "",
        "Simulated is never live; estimates are never measurements; attempt is never effect; stored proof bytes are not admitted proof; and no model claim completes a task. Stale ContextPacks, receipts, proofs, leases, fences, plan epochs, policies and tree identities are rejected. Unknown effects reconcile rather than blind retry. External agents cannot write the databases, terminalize tasks or provide authoritative policy decisions.", "",
        "An objective stops only when admitted evidence satisfies it, a human/policy decision is required, budget is exhausted, no admissible/convergent plan exists, or it is cancelled. An empty queue is not completion. Promotion is one closed status and retains zero hard-gate violations; absent measurements are missing, not zero.", "",
        "## Bounded campaign controls", "",
        f"- Initial tasks: {len(tasks)}; initial frontier: `DOEP-000`, `DOEP-001`, `DOEP-002`, `DOEP-003`.",
        "- Bootstrap concurrency: four isolated lanes, strict deterministic sharding, per-task lease/fence and merge serialization.",
        "- Bootstrap objective/codebase refill: disabled because the reviewed board is complete and bounded. DOEP-050..056 implement and qualify the canonical bounded event-driven refill before it is activated elsewhere.",
        "- Campaign generation ceiling: the sealed 85 tasks; no additional feature campaign from the residual-gap report.",
        "- Qualification cohorts: ≥60 hermetic fixtures, ≥20 historical exact-tree replays, held-out set, ≥10 live shadow objectives, then a human-gated low-risk canary.",
        "- Suggested promotion thresholds: ≥35% median input-token reduction, ≥25% weighted provider-cost reduction, ≥50% fewer frontier calls, ≥60% non-large-model eligible routes, ≥50% ContextPack reuse, ≥80% model-free ordinary refill, <5% unnecessary churn, <2% manual recovery, no quality degradation and positive net savings.", "",
        "## Goals and waves", "",
        "| Goal | Purpose | Task IDs |", "|---|---|---|",
    ]
    for phase_id, _parent, title, _objective in GOAL_DEFS:
        ids = ", ".join(f"`{t['task_id']}`" for t in tasks if t["parent_goal_id"] == phase_id)
        lines.append(f"| `{phase_id}` {title} | {PHASE_DESCRIPTION[phase_id]} | {ids} |")
    lines += [
        "", "Parallel waves are dependency-derived: inventory; contracts/compiler/events/routes; state/direct adapters/ContextPack; reassessment/planning/sibling/synthesis; invariant qualification and corpora; paired hermetic/historical/held-out evaluation; live shadow; conditional canary; closed release receipt.", "",
        "## Deliverables and completion", "",
        "The terminal release report must include the ADR; versioned contracts; Python/CLI/MCP/MCP++ direct interfaces; objective compiler; event/outbox/replay/recovery; incremental PlanDelta/refill; deterministic-first routing; cross-repository ContextPacks; sibling delegation; telemetry and paired benchmarks; unit/property/state/crash/race/security tests; operator and integration guides; three held-out demonstrations (one generic MCP); exact commits/trees/CIDs and an honest promotion status.", "",
        "Functional completion additionally requires direct high-level submission, first task without custom priming, automatic incremental reassessment and refill, sibling-event safety, external-agent non-bypass, package independence from sibling test layouts, repeated-board draining without manual DB repair, current-head tests, paired measurements and all zero safety gates.", "",
        "## Deferred backlog", "",
        "Nonessential hazards discovered during inventory—legacy ContextPack candidates, noncanonical in-memory event helpers, duplicate adapters and retention/tombstone gaps—are recorded by DOEP-000/002 for later disposition. They do not expand this campaign.", "",
    ]
    return "\n".join(lines)


def render_objectives(tasks: list[dict[str, Any]], goal_rows: list[dict[str, Any]], plan_cid: str) -> str:
    lines = ["# DOEP objective heap", "", f"- Program: {PROGRAM_ID}", f"- Plan revision: {PLAN_REVISION}", f"- Plan CID: {plan_cid}", ""]
    for goal in goal_rows:
        lines += [
            f"## {goal['goal_id']} {goal['title']}",
            f"- Status: {goal['status']}",
            f"- Parent: {goal['parent_goal_id'] or 'none'}",
            f"- Goal: {goal['objective']}",
            f"- Evidence: current admitted task receipts and plan-bound validation",
            f"- Outputs: objective/goal/task/event/receipt records under {PLAN_REVISION}",
            f"- Validation: python3 scripts/generate_agent_supervisor_direct_objective_event_driven_planning_board.py --check-all",
            f"- Acceptance: all child goals are satisfied by current admitted evidence or a permitted typed closed outcome",
            f"- Gap task: {next((t['task_id'] for t in tasks if t['subgoal_id'] == goal['goal_id']), 'none')}",
            "",
        ]
    return "\n".join(lines)


def render_board(tasks: list[dict[str, Any]], plan_cid: str) -> str:
    lines = ["# DOEP bounded supervisor board", "", f"Plan revision: `{PLAN_REVISION}`. Plan CID: `{plan_cid}`. Markdown is a sealed projection; DuckDB through Quack is operational authority.", ""]
    for task in tasks:
        deps = ", ".join(task["dependencies"]) or "none"
        validation = " ".join(task["execution_validation"][0])
        lines += [
            f"## {task['task_id']} {task['title']}",
            f"- Status: {task['status']}",
            f"- Stable task identity: {task['task_id']}",
            f"- Root goal: {task['root_goal_id']}",
            f"- Parent goal: {task['parent_goal_id']}",
            f"- Subgoal id: {task['subgoal_id']}",
            f"- Owning repository: {task['owning_repository']}",
            f"- Depends on: {deps}",
            f"- Exact base commits and trees: {json.dumps(BASES, sort_keys=True, separators=(',', ':'))}",
            f"- Exact outputs: {', '.join(task['exact_outputs'])}",
            f"- Superproject projection: {', '.join(task['superproject_outputs'])}",
            f"- Predicted files: {', '.join(task['owned_files'])}",
            f"- Preconditions: {'; '.join(task['preconditions'])}",
            f"- Postconditions: {'; '.join(task['postconditions'])}",
            f"- Risk class: {task['risk_class']}",
            f"- Authority requirement: {task['authority_requirement']}",
            f"- Token and compute budget: {json.dumps(task['budgets'], sort_keys=True, separators=(',', ':'))}",
            f"- Objective: {task['objective']}",
            f"- Validation profile: {task['validation_profile']}",
            f"- Validation: {validation}",
            f"- Acceptance: {task['acceptance']}",
            f"- Terminal success: {task['terminal_success']}",
            f"- Terminal non-success: {', '.join(task['terminal_non_success'])}",
            f"- Unknown effect rule: {task['unknown_effect_rule']}",
            f"- Allowed effects: {', '.join(task['allowed_effects'])}",
            f"- Forbidden effects: {', '.join(task['forbidden_effects'])}",
            f"- Required evidence: {', '.join(task['required_evidence'])}",
            f"- Proof obligations: {', '.join(task['proof_obligations'])}",
            f"- Conflict policy: {task['conflict_policy']}",
            f"- Rollback: {task['rollback']}",
            f"- Plan epoch: {task['plan_epoch']}",
            f"- Board namespace: {PROGRAM_ID}",
            "",
        ]
    return "\n".join(lines)


def render_population(tasks: list[dict[str, Any]], goal_rows: list[dict[str, Any]], plan_cid: str) -> str:
    goal_cids = {item["goal_id"]: item["goal_cid"] for item in goal_rows}
    operational_tasks = []
    for item in tasks:
        task = dict(item)
        task["goal_id"] = item["subgoal_id"]
        task["goal_cid"] = goal_cids[item["subgoal_id"]]
        task["plan_cid"] = plan_cid
        task["objective_id"] = PROGRAM_ID
        operational_tasks.append(task)
    payload = {
        "schema": "ipfs_accelerate_py/agent-supervisor/doep-bootstrap-population@1",
        "board_namespace": PROGRAM_ID,
        "plan_revision": PLAN_REVISION,
        "plan_root_cid": plan_cid,
        "repository_tree_id": cid({"bases": BASES}),
        "objective": {
            "objective_id": PROGRAM_ID,
            "objective_cid": cid({"objective": PROGRAM_ID, "revision": 1, "plan": plan_cid}),
            "revision": 1,
            "title": "Direct objective and event-driven planning",
            "idea": "Make the existing ipfs_accelerate_py supervisor directly invokable from a high-level idea, then plan and replan incrementally with deterministic-first reasoning and exact receipt lineage.",
            "mode": "execute_low_risk",
            "assumptions": ["Technical reversible ambiguity chooses a conservative recorded assumption", "Sibling repository writes require delegated sibling authority"],
            "non_goals": ["No competing supervisor, planner, state database, scheduler, memory, federation, router or policy engine", "No automatic feature campaign from residual gaps", "No self-authorized production promotion"],
            "guarantees": ["Truth and authority invariants remain fail closed", "Every leaf has exact outputs, budget, validation and terminal contract", "Completion depends on admitted evidence, not an empty queue"],
            "acceptance_conditions": ["All sixteen functional completion conditions in the sealed plan", "All required deliverables", "Three held-out demonstrations including generic MCP", "Closed promotion or honest non-promotion receipt"],
            "requested_budgets": {"max_tasks": 85, "max_concurrent_tasks": 4, "max_replan_epochs": 8, "validation_reserve_percent": 30},
        },
        "goals": goal_rows,
        "goal_edges": [
            {"parent_goal_cid": item["parent_goal_cid"], "child_goal_cid": item["goal_cid"], "edge_kind": "goal_decomposition"}
            for item in goal_rows if item["parent_goal_cid"]
        ],
        "plans": [{"plan_cid": plan_cid, "plan_alias": PLAN_REVISION, "goal_cid": goal_cids[ROOT_GOAL], "status": "active", "plan_epoch": 1}],
        "tasks": operational_tasks,
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_profiles(tasks: list[dict[str, Any]]) -> str:
    profiles = {}
    for task in tasks:
        profiles[task["task_id"]] = {
            "schema": "ipfs_accelerate_py/agent-supervisor/doep-validation-profile@1",
            "profile_id": task["validation_profile"],
            "task_id": task["task_id"],
            "plan_revision": PLAN_REVISION,
            "receipt": task["superproject_receipt_output"],
            "required_outputs": task["superproject_outputs"],
            "commands": [{"argv": ["python3", "-m", "pytest", "-q", task["superproject_test_output"]], "timeout_seconds": task["budgets"]["max_test_seconds"]}],
            "shell": False,
            "worker_claim_is_completion_authority": False,
        }
    return json.dumps({"schema": "ipfs_accelerate_py/agent-supervisor/doep-validation-profiles@1", "plan_revision": PLAN_REVISION, "profiles": profiles}, indent=2, sort_keys=True) + "\n"


def render_config(tasks: list[dict[str, Any]], goal_rows: list[dict[str, Any]], plan_cid: str) -> str:
    root = "data/agent_supervisor/agent_supervisor_direct_objective_event_driven_planning_v1"
    protected = [
        "docs/architecture/AGENT_SUPERVISOR_DIRECT_OBJECTIVE_AND_EVENT_DRIVEN_PLANNING_V1_PLAN.md",
        "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.objectives.md",
        "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.todo.md",
        "config/agent_supervisor_direct_objective_event_driven_planning_board.json",
        "config/agent_supervisor_direct_objective_event_driven_planning_validation_profiles.json",
        "config/agent_supervisor_direct_objective_event_driven_planning_scheduler.json",
        "scripts/generate_agent_supervisor_direct_objective_event_driven_planning_board.py",
        "scripts/run_agent_supervisor_direct_objective_event_driven_planning_validation.py",
        "scripts/ops/agent_supervisor/configured_board_scheduler.py",
        "scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py",
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
    ]
    config = {
        "schema": "ipfs_accelerate_py.agent_supervisor.direct-objective-event-driven-planning.scheduler_config@1",
        "program_identifier": PROGRAM_ID,
        "board_namespace": PROGRAM_ID,
        "accepted_plan_revision_alias": PLAN_REVISION,
        "plan_root_cid": plan_cid,
        "root_goal_id": ROOT_GOAL,
        "goal_prefix": "DOEP-G",
        "task_prefix": "DOEP-",
        "taskboard_path": "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.todo.md",
        "taskboard_json_path": "config/agent_supervisor_direct_objective_event_driven_planning_board.json",
        "objectives_path": "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.objectives.md",
        "plan_path": "docs/architecture/AGENT_SUPERVISOR_DIRECT_OBJECTIVE_AND_EVENT_DRIVEN_PLANNING_V1_PLAN.md",
        "validator_path": "scripts/generate_agent_supervisor_direct_objective_event_driven_planning_board.py",
        "validation_dispatcher_path": "scripts/run_agent_supervisor_direct_objective_event_driven_planning_validation.py",
        "validation_profile_path": "config/agent_supervisor_direct_objective_event_driven_planning_validation_profiles.json",
        "merge_target_branch": BRANCH,
        "max_lanes": 4,
        "lanes": [{"index": i, "name": f"doep-lane-{i}", "initial_focus": ("authority-and-interfaces", "events-and-state", "context-and-planning", "qualification-and-release")[i], "strict_shard_remainder": i} for i in range(4)],
        "strict_task_sharding": True,
        "idle_lane_work_stealing": "",
        "worktree_submodule_paths": ["external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"],
        "protected_paths": protected,
        "runtime_paths": {"root": root, "state": f"{root}/state", "worktrees": f"{root}/worktrees", "merge_queue": f"{root}/merge-queue", "logs": f"{root}/logs", "quack_owner": f"{root}/quack-owner", "evidence": f"{root}/evidence"},
        "database_program": {
            "schema": "ipfs_accelerate_py/agent-supervisor/database-program-config@1",
            "authority_mode": "quack", "task_source_kind": "duckdb", "explicit_legacy": False,
            "store_id": f"{root}/control.duckdb", "store_generation": "doep-v1-r2", "schema_revision": "1",
            "quack_endpoint": "quack:127.0.0.1:47941", "endpoint_secret_handle": "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
            "failover_policy": "fail_closed", "event_store_path": f"{root}/events", "runtime_registry_path": f"{root}/registry", "worktree_root": f"{root}/worktrees", "export_profile": "doep-v1",
        },
        "ducklake_projection_program": {"mode": "enabled_non_authoritative", "authority": False, "may_grant_authority": False, "scheduling_prerequisite": False, "completion_prerequisite": False, "acceptance_prerequisite": False, "catalog_path": f"{root}/ducklake/catalog.duckdb", "data_path": f"{root}/ducklake/data", "outage_policy": "typed unavailable and replayable; never block DuckDB authority"},
        "operational_control_plane": {"name": "DuckDB + exclusive Quack owner + non-authoritative DuckLake", "duckdb_role": "authoritative transactional goals/tasks/CAS/fences/receipts/events", "quack_role": "authenticated exclusive loopback mutation owner", "ducklake_role": "rebuildable analytics/history projection", "markdown_is_bootstrap_only": True, "direct_multi_process_duckdb_file_open_permitted": False, "automatic_file_fallback_permitted": False, "outage_policy": "fail_closed"},
        "provider": {"provider_id": "grok_cli", "model_id": "grok-4.6", "max_concurrency": 4, "completion_authority": "controller-owned sealed validation and database CAS", "secrets_from_environment_only": True},
        "poll_interval_seconds": 5, "daemon_interval_seconds": 20, "check_interval_seconds": 20,
        "stale_seconds": 1800, "watchdog_startup_grace_seconds": 180,
        "implementation_timeout_seconds": 7200, "implementation_max_timeout_seconds": 28800, "implementation_log_stall_seconds": 1200,
        "max_restarts": 3, "max_task_attempts": 2, "implementation_retry_budget": 1, "validation_retry_budget": 2, "merge_retry_budget": 2,
        "exit_when_all_tracks_terminal": False, "objective_refill_enabled": False, "objective_goal_refinement_enabled": False, "codebase_refill_enabled": False,
        "retry_budget_guardrail_enabled": True, "dependency_guardrail_enabled": True, "reconciliation_guardrail_enabled": True,
        "initial_projection": {"goal_count": len(goal_rows), "task_count": len(tasks), "task_dependency_count": sum(len(t["dependencies"]) for t in tasks), "ready_task_ids": [t["task_id"] for t in tasks if not t["dependencies"]], "blocked_task_ids": [], "completed_task_ids": [], "terminal_task_id": "DOEP-126"},
        "anti_runaway": {"max_tasks_per_refill": 4, "max_tasks_per_objective": 109, "max_replan_epochs": 8, "max_generated_tasks": 24, "event_debounce_seconds": 5, "repeated_plan_hash_detection": True, "oscillation_detection": True, "stable_frontier_detection": True, "nonconvergence_quarantine": True},
        "source_binding": {
            "accelerator_required_branch": BRANCH, "accelerator_required_ancestor": BASES["lift_coding"]["commit"], "bootstrap_task_source": "duckdb",
            "lift_coding_planning_revision": BASES["lift_coding"]["commit"], "lift_coding_planning_tree": BASES["lift_coding"]["tree"],
            "ipfs_accelerate_submodule_path": "external/ipfs_accelerate", "ipfs_accelerate_planning_revision": BASES["ipfs_accelerate_py"]["commit"], "ipfs_accelerate_planning_tree": BASES["ipfs_accelerate_py"]["tree"],
            "ipfs_datasets_submodule_path": "external/ipfs_datasets", "ipfs_datasets_planning_revision": BASES["ipfs_datasets_py"]["commit"], "ipfs_datasets_planning_tree": BASES["ipfs_datasets_py"]["tree"],
            "ipfs_kit_submodule_path": "external/ipfs_kit", "ipfs_kit_planning_revision": BASES["ipfs_kit_py"]["commit"], "ipfs_kit_planning_tree": BASES["ipfs_kit_py"]["tree"],
            "require_initialized_gitlinks": True, "require_superproject_gitlink_equals_nested_head": True, "require_clean_nested_worktree_at_task_start": True, "changed_revision_requires_fresh_inventory_and_baseline": True,
        },
        "truth_and_safety": {"hard_promotion_gates_must_remain_zero": ["false_completions", "unauthorized_mutations", "simulated_as_live", "stale_cache_or_context_admissions", "stale_lease_or_fence_completions", "confirmation_replays", "double_terminalization", "double_execution", "path_or_scope_escapes", "hidden_validation_reductions", "critical_omissions", "selected_test_false_negatives", "self_authorized_promotions", "sibling_state_writes"]},
    }
    return json.dumps(config, indent=2, sort_keys=True) + "\n"


def expected_files() -> dict[Path, str]:
    task_rows = parse_tasks()
    goal_rows = goals()
    if len(task_rows) != 85 or len({t["task_id"] for t in task_rows}) != 85:
        raise ValueError("DOEP board must contain exactly 85 unique tasks")
    known = {t["task_id"] for t in task_rows}
    unknown = sorted({d for t in task_rows for d in t["dependencies"] if d not in known})
    if unknown:
        raise ValueError(f"unknown dependencies: {unknown}")
    admitted_owners = {
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
    }
    for task in task_rows:
        owner = task["owning_repository"]
        if owner not in admitted_owners:
            raise ValueError(f"{task['task_id']} has no configured worktree owner")
        outputs = task["exact_outputs"]
        if any(
            not path
            or path.startswith(("/", "external/"))
            or ".." in Path(path).parts
            for path in outputs
        ):
            raise ValueError(f"{task['task_id']} outputs are not owner-relative")
        projected = [f"{owner}/{path}" for path in outputs]
        if task["superproject_outputs"] != projected:
            raise ValueError(f"{task['task_id']} superproject projection drift")
        validation = task["execution_validation"]
        expected_validation = [["python3", "-m", "pytest", "-q", task["test_output"]]]
        if validation != expected_validation or task["test_output"].startswith("external/"):
            raise ValueError(f"{task['task_id']} validation is not nested-owner executable")
    # Kahn check; also seals the intended initial frontier.
    pending = {t["task_id"]: set(t["dependencies"]) for t in task_rows}
    emitted: list[str] = []
    while pending:
        ready = sorted(k for k, v in pending.items() if not v)
        if not ready:
            raise ValueError(f"dependency cycle: {sorted(pending)}")
        emitted.extend(ready)
        for task_id in ready:
            pending.pop(task_id)
        for deps in pending.values():
            deps.difference_update(ready)
    if sorted(t["task_id"] for t in task_rows if not t["dependencies"]) != ["DOEP-000", "DOEP-001", "DOEP-002", "DOEP-003"]:
        raise ValueError("initial frontier drift")
    plan_cid = plan_identity(task_rows, goal_rows)
    return {
        ROOT / "docs/architecture/AGENT_SUPERVISOR_DIRECT_OBJECTIVE_AND_EVENT_DRIVEN_PLANNING_V1_PLAN.md": render_plan(task_rows, goal_rows, plan_cid),
        ROOT / "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.objectives.md": render_objectives(task_rows, goal_rows, plan_cid),
        ROOT / "docs/architecture/agent_supervisor_direct_objective_event_driven_planning.todo.md": render_board(task_rows, plan_cid),
        ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_board.json": render_population(task_rows, goal_rows, plan_cid),
        ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_validation_profiles.json": render_profiles(task_rows),
        ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_scheduler.json": render_config(task_rows, goal_rows, plan_cid),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check-all", action="store_true")
    args = parser.parse_args()
    files = expected_files()
    errors: list[str] = []
    if args.write:
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    for path, expected in files.items():
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"drift: {path.relative_to(ROOT)}")
    tasks = parse_tasks()
    goal_rows = goals()
    report = {
        "valid": not errors,
        "schema": "ipfs_accelerate_py/agent-supervisor/doep-board-validation@1",
        "board_namespace": PROGRAM_ID,
        "plan_revision": PLAN_REVISION,
        "plan_root_cid": plan_identity(tasks, goal_rows),
        "task_count": len(tasks),
        "goal_count": len(goal_rows),
        "dependency_count": sum(len(t["dependencies"]) for t in tasks),
        "initial_frontier": [t["task_id"] for t in tasks if not t["dependencies"]],
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
