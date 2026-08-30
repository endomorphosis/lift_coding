#!/usr/bin/env python3
"""Deterministically render or check the sealed PCPR bootstrap handoff.

This generator owns only the one-task configured-board projection and its
scheduler configuration.  It does not submit an objective, start a supervisor,
write a database, or generate another controller.  The 66-package PCPR plan is
admitted only after PCPR-004 qualifies the canonical direct-objective path.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "proof-carrying-platform-qualification-and-release-v1"
SHORT_ID = "PCPR"
BOOTSTRAP_TASK_ID = "PCPR-004"
BOOTSTRAP_TASK_TITLE = (
    "Repair and qualify the canonical direct-objective submission path"
)
ROOT_GOAL_ID = "PCPR-G000"
BOOTSTRAP_GOAL_ID = "PCPR-G110"
BOOTSTRAP_LANE = "pcpr-0"
BOOTSTRAP_RISK_CLASSIFICATION = "high-assurance-control-plane-repair"
BOOTSTRAP_RECEIPT = (
    "artifacts/proof_carrying_platform_qualification_and_release/"
    "receipts/PCPR-004.json"
)
BOOTSTRAP_ALLOWED_PATHS = (
    "external/ipfs_accelerate/config/agent_supervisor_prompt_only_self_improvement_v3_scheduler.json",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/facade.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/cli.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/service_factory.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/runtime_factory.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/intent_service.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/prompt/prompt_workflow.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/prompt/plan_supervisor_service.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/plan_revision_store.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/agent_supervisor_tools/prompt_entrypoints.py",
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_python_api.py",
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_cli.py",
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_mcp.py",
    BOOTSTRAP_RECEIPT,
)
BOOTSTRAP_REQUIRED_TESTS = (
    "python -m pytest "
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_python_api.py "
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_cli.py "
    "external/ipfs_accelerate/test/api/test_agent_supervisor_prompt_v3_mcp.py "
    "external/ipfs_accelerate/test/api/test_agent_supervisor_plan_control_conformance.py "
    "external/ipfs_accelerate/test/integration/test_agent_supervisor_planner_doctor_e2e.py "
    "-q; python -m json.tool "
    "artifacts/proof_carrying_platform_qualification_and_release/receipts/PCPR-004.json"
)
BOOTSTRAP_VALIDATION = BOOTSTRAP_REQUIRED_TESTS.replace("-q; python", "-q && python")

PLAN_PATH = (
    ROOT
    / "docs/architecture/"
    "PROOF_CARRYING_PLATFORM_QUALIFICATION_AND_RELEASE_V1_PLAN.md"
)
OBJECTIVES_PATH = (
    ROOT
    / "docs/architecture/"
    "proof_carrying_platform_qualification_and_release_v1.objectives.md"
)
BOARD_PATH = (
    ROOT
    / "docs/architecture/"
    "proof_carrying_platform_qualification_and_release_v1.todo.md"
)
CONFIG_PATH = (
    ROOT / "config/proof_carrying_platform_qualification_and_release_v1_supervisor.json"
)
GENERATOR_PATH = (
    ROOT / "scripts/generate_proof_carrying_platform_qualification_and_release_board.py"
)
VALIDATOR_PATH = (
    ROOT / "scripts/validate_proof_carrying_platform_qualification_and_release_board.py"
)
RUNNER_PATH = (
    ROOT / "scripts/run_agent_supervisor_proof_carrying_platform_qualification_and_release.py"
)

OUTER_REQUIRED_ANCESTOR = "bb8869ed72eb7002434345d9969efee729c4f7f6"
OUTER_REQUIRED_TREE = "99e85bfe584b7688ffbeff86da1e612dd6893a42"
REQUIRED_BRANCH = "agent/proof-carrying-platform-qualification-and-release-v1"

SOURCE_FOREST = OrderedDict(
    (
        (
            "ipfs_accelerate",
            {
                "path": "external/ipfs_accelerate",
                "commit": "42254413e5564cf56cca4999a03af9e96c50fae6",
                "tree": "1e7031564cd6686eb371524309c91a3945ab2db3",
                "origin_main": "f8c2f633fa6a781b822176fd63e1a229f96b581c",
            },
        ),
        (
            "ipfs_datasets",
            {
                "path": "external/ipfs_datasets",
                "commit": "f49afc579c22856849ca9f739435e5820003384f",
                "tree": "47118a8e6d1b6b4e7ae04f9a2efda33aadebca1b",
            },
        ),
        (
            "ipfs_kit",
            {
                "path": "external/ipfs_kit",
                "commit": "b6c65ba732733d7e33852713ba18aa3b12235668",
                "tree": "14da7d92e130b7ba3523d0d6741a3ef7ef1e1bc2",
            },
        ),
    )
)
WORKTREE_SUBMODULE_PATHS = tuple(
    str(item["path"]) for item in SOURCE_FOREST.values()
)

# The complete requested blueprint.  These packages are not the bootstrap
# board population and cannot become executable through this generator.
REQUIRED_PACKAGES = OrderedDict(
    (
        ("PCPR-000", "Seal repositories, contracts, policies, and supervisor baseline"),
        ("PCPR-001", "Qualify direct objective and event-driven supervisor"),
        ("PCPR-002", "Freeze canonical supervisor contracts or issue non-promotion"),
        ("PCPR-003", "Inventory every legacy bypass and false-authority path"),
        ("PCPR-010", "Remove Datasets import-time auto-install"),
        ("PCPR-011", "Remove Datasets false-success fallbacks"),
        ("PCPR-012", "Make typed outcomes canonical"),
        ("PCPR-013", "Canonicalize LogicProviderProtocol"),
        ("PCPR-014", "Stabilize semantic APIs and ContextPack contract"),
        ("PCPR-015", "Package schemas and shared vectors"),
        ("PCPR-016", "Resolve Datasets license metadata"),
        ("PCPR-017", "Qualify real Datasets solver paths"),
        ("PCPR-020", "Requalify local Kit backend"),
        ("PCPR-021", "Qualify pinned IPFS backend"),
        ("PCPR-022", "Qualify or de-scope Iroh"),
        ("PCPR-023", "Qualify VFS/WAL/current-root recovery"),
        ("PCPR-024", "Qualify proof-seal store"),
        ("PCPR-025", "Remove sibling test-tree coupling"),
        ("PCPR-026", "Qualify Python/CLI/MCP/MCP++ parity"),
        ("PCPR-027", "Generate authoritative support matrix"),
        ("PCPR-030", "Quarantine Accelerate legacy mock coordinator"),
        ("PCPR-031", "Remove fabricated hardware capability"),
        ("PCPR-032", "Remove pseudo-CID identity"),
        ("PCPR-033", "Remove fabricated endpoint success"),
        ("PCPR-034", "Consolidate capability ladder"),
        ("PCPR-035", "Pin mutable dependencies"),
        ("PCPR-036", "Correct Python compatibility metadata"),
        ("PCPR-037", "Qualify CPU execution"),
        ("PCPR-038", "Qualify real CUDA execution"),
        ("PCPR-039", "Qualify one real model/provider path"),
        ("PCPR-040", "Stabilize shared contracts"),
        ("PCPR-041", "Add canonical-byte and CID vectors"),
        ("PCPR-042", "Add negative and cross-language vectors"),
        ("PCPR-043", "Add cross-repository compatibility checks"),
        ("PCPR-050", "Build clean Datasets package"),
        ("PCPR-051", "Build clean Kit package"),
        ("PCPR-052", "Build clean Accelerate package"),
        ("PCPR-053", "Produce dependency locks"),
        ("PCPR-054", "Produce SBOMs and provenance"),
        ("PCPR-055", "Produce signed tags and artifacts"),
        ("PCPR-056", "Produce portfolio compatibility lock"),
        ("PCPR-057", "Add branch and release gates"),
        ("PCPR-060", "Submit reference high-level objective"),
        ("PCPR-061", "Build semantic ContextPack"),
        ("PCPR-062", "Persist and publish current ContextPack root"),
        ("PCPR-063", "Execute deterministic-first route"),
        ("PCPR-064", "Produce bounded patch"),
        ("PCPR-065", "Run selected tests and proofs"),
        ("PCPR-066", "Introduce unrelated state change"),
        ("PCPR-067", "Demonstrate safe reuse"),
        ("PCPR-068", "Introduce relevant interface change"),
        ("PCPR-069", "Demonstrate stale rejection and PlanDelta"),
        ("PCPR-070", "Restart authoritative state owner"),
        ("PCPR-071", "Demonstrate recovery and idempotency"),
        ("PCPR-072", "Produce final proof-carrying receipt chain"),
        ("PCPR-080", "Add Python external-client demonstration"),
        ("PCPR-081", "Add generic MCP-client demonstration"),
        ("PCPR-082", "Prove cross-client objective identity parity"),
        ("PCPR-083", "Prove external clients cannot bypass authority"),
        ("PCPR-090", "Prepare threat model"),
        ("PCPR-091", "Prepare trusted-computing-base inventory"),
        ("PCPR-092", "Prepare security and correctness audit package"),
        ("PCPR-093", "Run release-candidate gate"),
        ("PCPR-094", "Produce promotion or honest non-promotion receipt"),
        ("PCPR-095", "Publish residual-gap report"),
        ("PCPR-096", "Recommend the next customer or synthetic pilot"),
    )
)

RECEIPT_ROOT = "artifacts/proof_carrying_platform_qualification_and_release/receipts"

# After PCPR-004 is complete, the configured board may execute the 66-package
# campaign. Direct submit remains preferred; markdown materialization is the
# operator-authorized R&D execution path so the supervisor has remaining work.
CAMPAIGN_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "PCPR-000": (),
    "PCPR-001": ("PCPR-004",),
    "PCPR-002": ("PCPR-001",),
    "PCPR-003": ("PCPR-000",),
    "PCPR-010": ("PCPR-003",),
    "PCPR-011": ("PCPR-010",),
    "PCPR-012": ("PCPR-011",),
    "PCPR-013": ("PCPR-012",),
    "PCPR-014": ("PCPR-013",),
    "PCPR-015": ("PCPR-014",),
    "PCPR-016": ("PCPR-015",),
    "PCPR-017": ("PCPR-016",),
    "PCPR-020": ("PCPR-003",),
    "PCPR-021": ("PCPR-020",),
    "PCPR-022": ("PCPR-021",),
    "PCPR-023": ("PCPR-022",),
    "PCPR-024": ("PCPR-023",),
    "PCPR-025": ("PCPR-024",),
    "PCPR-026": ("PCPR-025",),
    "PCPR-027": ("PCPR-026",),
    "PCPR-030": ("PCPR-003",),
    "PCPR-031": ("PCPR-030",),
    "PCPR-032": ("PCPR-031",),
    "PCPR-033": ("PCPR-032",),
    "PCPR-034": ("PCPR-033",),
    "PCPR-035": ("PCPR-034",),
    "PCPR-036": ("PCPR-035",),
    "PCPR-037": ("PCPR-036",),
    "PCPR-038": ("PCPR-037",),
    "PCPR-039": ("PCPR-038",),
    "PCPR-040": ("PCPR-017", "PCPR-027", "PCPR-039"),
    "PCPR-041": ("PCPR-040",),
    "PCPR-042": ("PCPR-041",),
    "PCPR-043": ("PCPR-042",),
    "PCPR-050": ("PCPR-043",),
    "PCPR-051": ("PCPR-050",),
    "PCPR-052": ("PCPR-051",),
    "PCPR-053": ("PCPR-052",),
    "PCPR-054": ("PCPR-053",),
    "PCPR-055": ("PCPR-054",),
    "PCPR-056": ("PCPR-055",),
    "PCPR-057": ("PCPR-056",),
    "PCPR-060": ("PCPR-002", "PCPR-057"),
    "PCPR-061": ("PCPR-060",),
    "PCPR-062": ("PCPR-061",),
    "PCPR-063": ("PCPR-062",),
    "PCPR-064": ("PCPR-063",),
    "PCPR-065": ("PCPR-064",),
    "PCPR-066": ("PCPR-065",),
    "PCPR-067": ("PCPR-066",),
    "PCPR-068": ("PCPR-067",),
    "PCPR-069": ("PCPR-068",),
    "PCPR-070": ("PCPR-069",),
    "PCPR-071": ("PCPR-070",),
    "PCPR-072": ("PCPR-071",),
    "PCPR-080": ("PCPR-072",),
    "PCPR-081": ("PCPR-080",),
    "PCPR-082": ("PCPR-081",),
    "PCPR-083": ("PCPR-082",),
    "PCPR-090": ("PCPR-083",),
    "PCPR-091": ("PCPR-090",),
    "PCPR-092": ("PCPR-091",),
    "PCPR-093": ("PCPR-092",),
    "PCPR-094": ("PCPR-093",),
    "PCPR-095": ("PCPR-094",),
    "PCPR-096": ("PCPR-095",),
}

CAMPAIGN_GOALS: dict[str, str] = {}
for _task_id in REQUIRED_PACKAGES:
    _n = int(_task_id.split("-")[1])
    if _n <= 3:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G100"
    elif _n < 20:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G200"
    elif _n < 30:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G300"
    elif _n < 40:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G400"
    elif _n < 50:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G500"
    elif _n < 60:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G600"
    elif _n < 80:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G700"
    elif _n < 90:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G800"
    else:
        CAMPAIGN_GOALS[_task_id] = "PCPR-G900"
CAMPAIGN_GOALS["PCPR-000"] = "PCPR-G110"
CAMPAIGN_GOALS["PCPR-001"] = "PCPR-G120"
CAMPAIGN_GOALS["PCPR-002"] = "PCPR-G130"
CAMPAIGN_GOALS["PCPR-003"] = "PCPR-G130"


def campaign_owner(task_id: str) -> tuple[str, tuple[str, ...]]:
    """Return owning repository and write-scope paths for one campaign task."""

    receipt = f"{RECEIPT_ROOT}/{task_id}.json"
    n = int(task_id.split("-")[1])
    if 10 <= n <= 17 or task_id == "PCPR-050":
        return "ipfs_datasets_py", ("external/ipfs_datasets/", receipt)
    if 20 <= n <= 27 or task_id == "PCPR-051":
        return "ipfs_kit_py", ("external/ipfs_kit/", receipt)
    if 30 <= n <= 39 or task_id == "PCPR-052":
        return "ipfs_accelerate_py", ("external/ipfs_accelerate/", receipt)
    if task_id in {"PCPR-000", "PCPR-001", "PCPR-002", "PCPR-003"}:
        return (
            "ipfs_accelerate_py",
            (
                "external/ipfs_accelerate/",
                receipt,
            ),
        )
    return (
        "ipfs_accelerate_py",
        (
            "external/ipfs_accelerate/",
            "external/ipfs_datasets/",
            "external/ipfs_kit/",
            receipt,
        ),
    )


def campaign_ready_ids() -> list[str]:
    completed = {BOOTSTRAP_TASK_ID}
    ready: list[str] = []
    for task_id in REQUIRED_PACKAGES:
        deps = CAMPAIGN_DEPENDENCIES[task_id]
        if all(dep in completed for dep in deps):
            ready.append(task_id)
    return ready


def campaign_dependency_count() -> int:
    return sum(len(deps) for deps in CAMPAIGN_DEPENDENCIES.values())


CAMPAIGN_TASK_COUNT = 1 + len(REQUIRED_PACKAGES)
CAMPAIGN_READY_IDS = campaign_ready_ids()

CLOSED_RELEASE_OUTCOMES = (
    "release_candidate_qualified",
    "non_promoted_supervisor_unqualified",
    "non_promoted_import_or_false_success",
    "non_promoted_live_storage_gap",
    "non_promoted_live_compute_gap",
    "non_promoted_solver_gap",
    "non_promoted_packaging_gap",
    "non_promoted_dependency_reproducibility",
    "non_promoted_security_failure",
    "non_promoted_interoperability_gap",
    "non_promoted_reference_workflow_failure",
    "non_promoted_unmeasured",
    "non_promoted_operator_gate_required",
)

TRUTH_INVARIANTS = (
    "No simulated observation may be represented as live.",
    "No estimated metric may be represented as measured.",
    "No attempted operation may be represented as observed.",
    "No observed operation may be represented as verified without admitted verifier evidence.",
    "No present CID may be represented as proof authority.",
    "No stored proof may be represented as an admitted proof.",
    "No cache hit may be reused against a different tree, policy, objective, schema, interface, toolchain, or relevant environment.",
    "No missing capability may silently fall back to a mock.",
    "No unavailable backend may be advertised as available.",
    "No mock endpoint may be advertised as a real endpoint.",
    "No SHA-256 hexadecimal string may be advertised as an IPFS CID.",
    "No absent dependency may be automatically installed during package import.",
    "No unavailable operation may return `status: success`.",
    "No test or validation failure may be converted into a warning for release.",
    "No task may complete solely from an LLM assertion.",
    "No provider-outcome-unknown may enter blind retry.",
    "No stale lease or fence may complete.",
    "No client-supplied policy `allow` or confirmation is authoritative.",
    "No package may depend on a mutable Git branch in a qualified release.",
    "No package test may require an uninstalled sibling source-tree `tests/` directory.",
    "No release may be published after partial required-build failure.",
    "No production claim may be inferred from hermetic fixtures alone.",
    "No legal, security, model, provider, or data capability may be described more broadly than its current qualification receipt.",
    "No policy promotion may be self-authorized.",
    "An empty task queue does not prove objective satisfaction.",
)

HARD_ZERO_INVARIANTS = (
    "false completions",
    "unauthorized mutations",
    "simulated-as-live outcomes",
    "stale cache admissions",
    "stale ContextPack admissions",
    "stale lease completions",
    "stale fence completions",
    "double execution",
    "double terminalization",
    "confirmation replays",
    "path or scope escapes",
    "hidden validation reductions",
    "accepted critical controlled omissions",
    "selected-test false negatives in release qualification",
    "self-authorized promotions",
    "release creation after failed required gates",
)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _render_campaign_task(task_id: str, title: str) -> str:
    owner, paths = campaign_owner(task_id)
    allowed = ", ".join(paths)
    receipt = f"{RECEIPT_ROOT}/{task_id}.json"
    depends = ", ".join(CAMPAIGN_DEPENDENCIES[task_id])
    goal = CAMPAIGN_GOALS[task_id]
    n = int(task_id.split("-")[1])
    lane = f"pcpr-{(n // 10) % 10}"
    validation = f"python -m json.tool {receipt}"
    return f"""## {task_id} {title}

- Stable task id: {task_id}
- Completion contract: admitted_current_tree_receipt
- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: {owner}
- Owned paths: {allowed}
- Objective: {title}. Record an honest R&D receipt at {receipt}. Live claims require live evidence; missing environments stay typed unavailable. Do not represent simulated results as live. Do not write DuckDB or Quack state directly.
- Depends on: {depends}
- Priority: P0
- Risk classification: high-assurance-platform-release
- Execution mode: execute_with_confirmations
- Allowed effects: Modify only the owned paths; add the named receipt; run bounded tests without publishing a production release.
- Prohibited effects: Create a new supervisor, planner, task database, or event database; write DuckDB or Quack state directly; weaken fail-closed gates; claim production qualification.
- Acceptance criteria: The named receipt exists, uses promotion_status rnd_non_promoted or an honest typed unavailable/blocked status, and does not claim a closed release outcome.
- Required tests: {validation}
- Required evidence: Current-tree commit and tree; changed-path manifest; test or probe commands and exit codes; explicit limitations.
- Rollback procedure: Revert only this task's accepted commit and receipt. Preserve history.
- Assigned worktree: pcpr-{task_id.lower()}
- Final result CID or artifact identity: pending CID for {receipt}
- Goal id: {goal}
- Outputs: {allowed}
- Validation: {validation}
- Board namespace: {NAMESPACE}
- Bundle: pcpr/{goal.lower()}/{task_id.lower()}
- Parallel lane: {lane}
- Resource class: cpu-large
- Implementation timeout seconds: 7200
- Predicted files: {allowed}
- Allowed paths: {allowed}
- Conflict policy: Hold an exclusive merge-queue lease for overlapping owned paths, rebase onto the latest accepted PCPR gitlink, reject paths outside the allowlist, and publish the receipt only after the nested commit is accepted.
- Acceptance: Honest current-tree evidence for {title}, or a typed unavailable/blocked receipt.
"""


def render_board() -> str:
    """Return the executable campaign board after completed PCPR-004."""

    allowed = ", ".join(BOOTSTRAP_ALLOWED_PATHS)
    ready = ", ".join(CAMPAIGN_READY_IDS)
    campaign_blocks = "\n".join(
        _render_campaign_task(task_id, title)
        for task_id, title in REQUIRED_PACKAGES.items()
    )
    return f"""# PCPR v1 supervisor campaign task board

Program identifier: proof-carrying-platform-qualification-and-release-v1

Board namespace: proof-carrying-platform-qualification-and-release-v1

This tracked Markdown board is the operator-authorized campaign projection for the existing ipfs_accelerate_py agent supervisor. PCPR-004 is complete on the current tree. The remaining 66 blueprint packages are executable through DatabaseTaskSource. DuckDB becomes authoritative after materialization, Quack is the exclusive authenticated state owner while live, and DuckLake is a non-authoritative replayable analytics projection.

Direct high-level submission remains the preferred materialization path. This board exists so the configured-board supervisor can finish the remaining PCPR work without re-implementing PCPR-004. No raw SQL, second supervisor family, or competing authority is permitted.

Initial readiness frontier: {ready}.

Initial blocked population: none.

Root completion barrier: PCPR-096. An empty queue is not objective satisfaction.

## Execution invariants

- Bind dispatch to this namespace, exact task and task CID, current portfolio and Accelerate commits and trees, current origin/main ancestry, lease, fence, event cursor, isolated worktree, exact allowed paths, validation commands, expected effects, and receipt.
- Prompt text is intent only. It cannot choose authority, approve policy, authorize effects, select a fence, mark a task complete, or create a raw execution payload.
- Reuse Supervisor, PromptSupervisorService, PlanSupervisorService, PlanRevisionStore, DatabaseTaskSource, the existing control plane, configured-board scheduler, state owner, CLI, and MCP adapter. Do not create a new supervisor, planner, controller, task database, event database, profile, provider family, or backend family.
- Preview, admission, materialization, and start are distinct, independently receipted boundaries. Materialization and start require current roots, authorization, idempotency, lease, fence, event cursor, and exact expected effects.
- Unknown, unavailable, ambiguous, stale, partial, or provider-outcome-unknown results fail closed or produce a typed continuation. They never become simulated success, blind retry, completion, or release evidence.
- Workers never write DuckDB directly. Once Quack is live, all task-state mutations pass through its authenticated fenced state-owner interface.
- Model and worker output is candidate evidence only. Independent current-tree validation and canonical task-state CAS own terminalization.
- The generic prompt workflow remains campaign-neutral: it must not embed PCPR task identifiers, synthesize tasks from identifier-shaped evidence, replace the planner graph after planning, or attach a planning receipt to a different graph. The existing planner must elaborate the submitted idea and sealed constraints; failure to produce the required bounded graph is a typed non-promotion.
- The task may change only the exact Accelerate files and its outer receipt listed below. Protected PCPR handoff files cannot be changed by the worker.

## {BOOTSTRAP_TASK_ID} {BOOTSTRAP_TASK_TITLE}

- Stable task id: {BOOTSTRAP_TASK_ID}
- Completion contract: admitted_current_tree_receipt
- Status: complete
- Completion: auto
- Is schedulable: false
- Review only: false
- Owning repository: ipfs_accelerate_py
- Owned paths: {allowed}
- Objective: Repair and qualify the current production prompt facade so one authenticated high-level objective supplied to Supervisor.run, the product supervisor run CLI, or agent_supervisor_run over MCP is resolved into a bounded typed PromptWorkflowRequest and PlanCreateRequest, scanned, elaborated, independently admitted, atomically materialized through the existing PlanRevisionStore and DatabaseTaskSource, and separately started through the existing configured runtime. Remove the current requirement that the caller inject a pre-built CompleteLaunchPlan. Preserve the proposal, admission, mutation, and lifecycle boundaries and all current fail-closed behavior.
- Depends on:
- Priority: P0
- Risk classification: {BOOTSTRAP_RISK_CLASSIFICATION}
- Execution mode: execute_with_confirmations
- Allowed effects: Inspect the exact sealed portfolio; modify only the exact existing Accelerate configuration, facade, CLI, service composition, runtime factory, intent service, prompt workflow, plan facade, plan revision store, MCP prompt adapter, and three conformance test files named in Allowed paths; add only this task receipt at the named outer artifact path; run bounded tests without publishing releases or contacting unapproved external systems.
- Prohibited effects: Create a new supervisor, planner, meta-controller, lifecycle controller, task source, task database, event database, state owner, MCP++ profile, dashboard, provider family, or backend family; write DuckDB or Quack state directly; edit this plan, objective heap, board, generator, validator, or operator; grant prompt, model, client, worker, or candidate evidence mutation or completion authority; invent a CompleteLaunchPlan, authorization, root, lease, fence, event cursor, success, capability, CID, proof, or receipt; hardcode PCPR identifiers in a generic workflow, synthesize tasks from identifier-shaped evidence, replace or expand a planner graph after the planning receipt is issued, impose 66 tasks as a minimum for unrelated objectives, or bind a receipt to a different graph; weaken admission, validation, safety, confirmation, path, budget, or current-tree gates; expand beyond PCPR.
- Acceptance criteria: A normal production Supervisor.open on the activated exact repository can accept the PCPR high-level idea through Supervisor.run without caller injection of a CompleteLaunchPlan; the service deterministically observes the authenticated repository, state, objective, policy, capability, provider, and current-tree bindings and constructs all bounded typed inputs; PromptSupervisorService and PlanSupervisorService return an admitted rather than proposal-only or review-only preview with complete materialization inputs; authorized application uses PlanRevisionStore and DatabaseTaskSource and publishes exact projection identities without raw database access; START is a separate authorized control operation using the existing configured-board runtime; every stage binds idempotency, expected effects, lease, fence, event cursor, current roots, and source revision; stale, missing, ambiguous, unauthorized, replay-conflicting, partial, and unavailable cases fail closed; linked objective, preview, admission, plan revision, task-source, start, process, and run receipts are emitted; Python, CLI, and MCP produce the same objective and plan identities and equivalent outcomes; a generic high-level PCPR submission can materialize the 66 named blueprint tasks within the initial-task ceiling; no task is marked complete by a model assertion or empty queue.
- Required tests: {BOOTSTRAP_REQUIRED_TESTS}
- Required evidence: Exact pre-change and post-change Accelerate commit and tree; current origin/main ancestry; changed-path manifest; proof that every changed path is allowed; production-composition identity; canonical high-level objective identity; PromptWorkflowRequest and PlanCreateRequest identities; admitted preview and admission receipts; PlanRevisionStore apply and DatabaseTaskSource projection receipts; separate START and process-birth receipts; lease, fence, idempotency, event-cursor, root, expected-effect, and observed-effect bindings; Python, CLI, and MCP identity parity; negative stale, unauthorized, missing-runtime, missing-capability, replay, path, and direct-database-bypass results; exact test commands, exit codes, outputs, durations, token and provider-call counts, and limitations.
- Rollback procedure: Stop only the PCPR runtime through its canonical lifecycle operation, invalidate the PCPR direct-handoff qualification receipt and dependent materialization, revert only this task's accepted Accelerate commit and outer receipt commit, restore the prior activated production composition, and preserve all prior objective, task, event, attempt, and receipt history. Never reset, clean, or rewrite unrelated repositories or worktrees.
- Assigned worktree: pcpr-pcpr-004
- Final result CID or artifact identity: pending CID for {BOOTSTRAP_RECEIPT}
- Goal id: {BOOTSTRAP_GOAL_ID}
- Outputs: {allowed}
- Validation: {BOOTSTRAP_VALIDATION}
- Board namespace: {NAMESPACE}
- Bundle: pcpr/pcpr-g110/pcpr-004
- Parallel lane: {BOOTSTRAP_LANE}
- Resource class: cpu-large
- Implementation timeout seconds: 7200
- Predicted files: {allowed}
- Allowed paths: {allowed}
- Conflict policy: Hold an exclusive merge-queue lease for each shared entrypoint or control-plane file, rebase the nested Accelerate change on the latest accepted PCPR gitlink, reject any changed path outside the exact allowlist, rerun all affected conformance and negative tests, and publish the outer receipt only after the nested commit is accepted and its gitlink is current.
- Acceptance: The existing canonical public prompt path accepts the exact PCPR idea and produces admitted, authorized, current-tree, cross-transport-equivalent objective, plan, materialization, and start receipts without pre-built-plan injection, false authority, direct database mutation, or a new subsystem; otherwise this task ends in a typed honest failure receipt and the 66-package campaign remains unmaterialized.

{campaign_blocks}"""


def render_config() -> dict[str, Any]:
    """Return the exact scheduler configuration for the bootstrap board."""

    runtime_root = "data/agent_supervisor/proof_carrying_platform_qualification_and_release_v1"
    protected = [
        relative(PLAN_PATH),
        relative(OBJECTIVES_PATH),
        relative(BOARD_PATH),
        relative(CONFIG_PATH),
        relative(GENERATOR_PATH),
        relative(VALIDATOR_PATH),
        relative(RUNNER_PATH),
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
    ]
    source_binding: dict[str, Any] = {
        "accelerator_required_ancestor": OUTER_REQUIRED_ANCESTOR,
        "accelerator_planning_revision": OUTER_REQUIRED_ANCESTOR,
        "accelerator_planning_tree": OUTER_REQUIRED_TREE,
        "accelerator_required_branch": REQUIRED_BRANCH,
        "bootstrap_task_source": "duckdb",
        "require_initialized_gitlinks": True,
        "require_superproject_gitlink_equals_nested_head": True,
        "require_clean_nested_worktree_at_task_start": True,
        "require_origin_main_as_ancestor": True,
        "record_recursive_repository_forest_at_launch": True,
        "changed_revision_requires_fresh_inventory_and_baseline": True,
        "planning_revision_is_runtime_completion_evidence": False,
    }
    for prefix, record in SOURCE_FOREST.items():
        source_binding[f"{prefix}_submodule_path"] = record["path"]
        source_binding[f"{prefix}_planning_revision"] = record["commit"]
        source_binding[f"{prefix}_planning_tree"] = record["tree"]
        source_binding[f"{prefix}_origin_main_revision"] = record.get(
            "origin_main", record["commit"]
        )

    return {
        "schema": (
            "ipfs_accelerate_py.agent_supervisor."
            "proof-carrying-platform-qualification-and-release-v1.scheduler_config@1"
        ),
        "program_identifier": NAMESPACE,
        "taskboard_path": relative(BOARD_PATH),
        "objectives_path": relative(OBJECTIVES_PATH),
        "plan_path": relative(PLAN_PATH),
        "validator_path": relative(VALIDATOR_PATH),
        "task_prefix": "PCPR-",
        "goal_prefix": "PCPR-G",
        "board_namespace": NAMESPACE,
        "accepted_plan_revision_alias": "PCPR-PLAN-V1",
        "merge_target_branch": REQUIRED_BRANCH,
        "objective_submission": {
            "requested_interface": "supervisor.objectives.submit",
            "direct_interface_status": "bootstrap_complete_campaign_executable",
            "proposal_only_interface": "PromptSupervisorService.preview",
            "canonical_bootstrap_handoff": (
                "configured_board_git_seal_then_duckdb_materialization_over_quack"
            ),
            "bootstrap_task_id": BOOTSTRAP_TASK_ID,
            "bootstrap_task_count": 1,
            "required_blueprint_task_count": len(REQUIRED_PACKAGES),
            "full_campaign_terminal_task_id": "PCPR-096",
            "full_campaign_must_use_repaired_direct_interface": False,
            "manual_full_campaign_materialization_permitted": True,
            "campaign_count": 1,
        },
        "source_binding": source_binding,
        "initial_projection": {
            "task_count": CAMPAIGN_TASK_COUNT,
            "task_dependency_count": campaign_dependency_count(),
            "completed_task_ids": [BOOTSTRAP_TASK_ID],
            "ready_task_ids": list(CAMPAIGN_READY_IDS),
            "blocked_task_ids": [],
            "terminal_task_id": "PCPR-096",
            "goal_count": 37,
            "root_goal_id": ROOT_GOAL_ID,
        },
        "database_program": {
            "authority_mode": "quack",
            "task_source_kind": "duckdb",
            "endpoint_secret_handle": "handle:pcpr-v1",
            "quack_endpoint": "quack:127.0.0.1:47831",
            "owner_mode": "exclusive",
            "store_id": f"{runtime_root}/control.duckdb",
            "store_generation": "pcpr-v1-c1",
            "schema_revision": "1",
            "event_store_path": f"{runtime_root}/events",
            "runtime_registry_path": f"{runtime_root}/registry",
            "worktree_root": f"{runtime_root}/worktrees",
            "export_profile": "pcpr-v1-c1",
            "failover_policy": "fail_closed",
            "explicit_legacy": False,
            "claim_policy": {
                "schema": (
                    "ipfs_accelerate_py/agent-supervisor/database-claim-policy@1"
                ),
                "task_prefix": "PCPR-",
                "task_shard_count": 3,
                "strict_task_sharding": True,
                "idle_lane_work_stealing": "virgin-transfer",
            },
        },
        "operational_control_plane": {
            "name": "DuckDB + exclusive Quack with non-authoritative DuckLake",
            "duckdb_role": (
                "authoritative transactional objective, goal, task, lifecycle, "
                "CAS, fencing, receipt, release-state, and outbox records"
            ),
            "quack_role": (
                "authenticated loopback transport and exclusive fenced state-owner boundary"
            ),
            "ducklake_role": (
                "rebuildable non-authoritative append-only history and analytics projection"
            ),
            "direct_multi_process_duckdb_file_open_permitted": False,
            "automatic_file_fallback_permitted": False,
            "outage_policy": "fail_closed",
            "markdown_is_bootstrap_only": True,
        },
        "ducklake_projection_program": {
            "mode": "enabled_non_authoritative",
            "authority": False,
            "scheduling_prerequisite": False,
            "acceptance_prerequisite": False,
            "completion_prerequisite": False,
            "release_prerequisite": False,
            "source_authority": "DuckDB committed outbox cursor over Quack",
            "catalog_path": f"{runtime_root}/ducklake/catalog.duckdb",
            "data_path": f"{runtime_root}/ducklake/data",
            "logical_datasets": ["pcpr_events", "qualification_history"],
            "outage_policy": (
                "typed unavailable and replayable; never block DuckDB scheduling, "
                "acceptance, completion, validation, or release decisions"
            ),
            "may_grant_authority": False,
        },
        "max_lanes": 3,
        "strict_task_sharding": True,
        "idle_lane_work_stealing": "virgin-transfer",
        "exit_when_all_tracks_terminal": False,
        "objective_refill_enabled": False,
        "codebase_refill_enabled": False,
        "objective_goal_refinement_enabled": False,
        "retry_budget_guardrail_enabled": True,
        "dependency_guardrail_enabled": True,
        "reconciliation_guardrail_enabled": True,
        "poll_interval_seconds": 5,
        "daemon_interval_seconds": 20,
        "check_interval_seconds": 10,
        "stale_seconds": 300,
        "watchdog_startup_grace_seconds": 300,
        "max_restarts": 8,
        "max_task_attempts": 2,
        "implementation_retry_budget": 1,
        "validation_retry_budget": 2,
        "merge_retry_budget": 2,
        "implementation_timeout_seconds": 14400,
        "implementation_max_timeout_seconds": 21600,
        "implementation_log_stall_seconds": 1200,
        "worktree_submodule_paths": list(WORKTREE_SUBMODULE_PATHS),
        "protected_paths": protected,
        "runtime_paths": {
            "root": runtime_root,
            "state": f"{runtime_root}/state",
            "worktrees": f"{runtime_root}/worktrees",
            "merge_queue": f"{runtime_root}/merge-queue",
            "logs": f"{runtime_root}/logs",
            "evidence": f"{runtime_root}/evidence",
            "quack_owner": f"{runtime_root}/quack-owner",
            "generated_runtime_artifacts_are_completion_authority": False,
        },
        "lanes": [
            {
                "index": 0,
                "name": "pcpr-0",
                "strict_shard_remainder": 0,
                "initial_task_ids": list(CAMPAIGN_READY_IDS),
                "initial_focus": "pcpr-campaign-lane-0",
            },
            {
                "index": 1,
                "name": "pcpr-1",
                "strict_shard_remainder": 1,
                "initial_task_ids": list(CAMPAIGN_READY_IDS),
                "initial_focus": "pcpr-campaign-lane-1",
            },
            {
                "index": 2,
                "name": "pcpr-2",
                "strict_shard_remainder": 2,
                "initial_task_ids": list(CAMPAIGN_READY_IDS),
                "initial_focus": "pcpr-campaign-lane-2",
            },
        ],
        "task_groups": {
            goal: (
                ([BOOTSTRAP_TASK_ID] if goal == BOOTSTRAP_GOAL_ID else [])
                + [
                    task_id
                    for task_id, mapped in CAMPAIGN_GOALS.items()
                    if mapped == goal
                ]
            )
            for goal in sorted({BOOTSTRAP_GOAL_ID, *CAMPAIGN_GOALS.values()})
        },
        "provider": {
            "primary_provider_id": "grok_cli",
            "primary_model_id": "grok-4.6",
            "fallback_provider_id": "codex",
            "fallback_model_id": "gpt-5.6-terra",
            "fallback_trigger": "primary_quota_exhausted",
            "fallback_reasoning_effort": "high",
            "max_concurrency": 3,
            "secrets_from_environment_only": True,
            "secrets_in_argv_prompts_logs_or_receipts": False,
        },
        "budget_policy": {
            "max_initial_tasks": 80,
            "max_total_tasks": 140,
            "max_replan_epochs": 20,
            "max_automatically_generated_tasks_per_refill": 12,
            "max_frontier_model_calls": 40,
            "validation_token_and_compute_reserve_percent": 30,
            "reserve_applies_before_scope_expansion": True,
            "missing_budget_evidence_disposition": "non_promoted_unmeasured",
        },
        "refill_policy": {
            "source": "qualified_direct_objective_interface",
            "append_only": True,
            "content_addressed": True,
            "seed_tasks_are_immutable": True,
            "unscoped_codebase_refill_allowed": False,
            "empty_scan_may_claim_completion": False,
            "root_terminal_task_id": "PCPR-096",
            "activation_gate": {
                "task_id": BOOTSTRAP_TASK_ID,
                "interface": "supervisor.objectives.submit",
                "requires_admitted_current_tree_receipt": True,
                "requires_operator_invocation": True,
                "direct_database_toggle_permitted": False,
                "config_flag_mutation_permitted": False,
                "full_campaign_markdown_materialization_permitted": True,
            },
            "derived_refill": {
                "max_goals_per_epoch": 12,
                "max_tasks_per_epoch": 12,
                "min_open_tasks": 8,
                "max_open_tasks": 48,
                "max_refinement_depth": 3,
                "max_unchanged_failure_retries": 2,
                "cooldown_seconds": 300,
                "max_epochs": 20,
                "max_total_tasks": 140,
                "mutate_seed_board": False,
            },
        },
        "authority_policy": {
            "canonical_semantic_authority": "ipfs_datasets_py",
            "exact_bytes_storage_authority": "ipfs_kit_py",
            "orchestration_admission_authority": "ipfs_accelerate_py",
            "duckdb_transactional_authority": True,
            "quack_exclusive_owner_transport": True,
            "ducklake_projection_authority": False,
            "no_repository_may_silently_remint_foreign_identity": True,
            "external_direct_authority_mutation_permitted": False,
            "model_or_llm_assertion_is_completion_authority": False,
            "empty_task_queue_is_objective_satisfaction": False,
            "unknown_ambiguous_stale_or_unsupported_disposition": (
                "abstain_quarantine_reconcile_or_require_operator"
            ),
        },
        "closed_release_outcomes": list(CLOSED_RELEASE_OUTCOMES),
        "hard_zero_invariants": list(HARD_ZERO_INVARIANTS),
    }


def render_config_text() -> str:
    return json.dumps(render_config(), indent=2, sort_keys=True) + "\n"


def check_generated_files() -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        relative(BOARD_PATH): render_board(),
        relative(CONFIG_PATH): render_config_text(),
    }
    for name, wanted in expected.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing generated file: {name}")
            continue
        observed = path.read_text(encoding="utf-8")
        if observed != wanted:
            errors.append(f"generated file differs: {name}")
    return {
        "schema": "pcpr/bootstrap-generator-check@1",
        "valid": not errors,
        "mode": "check",
        "errors": errors,
        "bootstrap_task_ids": [BOOTSTRAP_TASK_ID],
        "required_blueprint_task_count": len(REQUIRED_PACKAGES),
        "generated_paths": sorted(expected),
    }


def generate_files() -> dict[str, Any]:
    """Write only the deterministic board and config after explicit request."""

    BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOARD_PATH.write_text(render_board(), encoding="utf-8")
    CONFIG_PATH.write_text(render_config_text(), encoding="utf-8")
    return {
        "schema": "pcpr/bootstrap-generator-result@1",
        "valid": True,
        "mode": "generate",
        "bootstrap_task_ids": [BOOTSTRAP_TASK_ID],
        "required_blueprint_task_count": len(REQUIRED_PACKAGES),
        "generated_paths": sorted((relative(BOARD_PATH), relative(CONFIG_PATH))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="compare the board and config with deterministic renderings",
    )
    mode.add_argument(
        "--generate",
        action="store_true",
        help="write only the deterministic board and config",
    )
    arguments = parser.parse_args()

    if len(REQUIRED_PACKAGES) != 66 or len(set(REQUIRED_PACKAGES)) != 66:
        result = {
            "schema": "pcpr/bootstrap-generator-result@1",
            "valid": False,
            "mode": "static-validation",
            "errors": ["required PCPR blueprint must contain 66 unique IDs"],
        }
    elif arguments.check:
        result = check_generated_files()
    else:
        result = generate_files()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
