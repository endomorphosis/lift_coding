#!/usr/bin/env python3
"""Generate the protected PCTDD control program from one reviewed source."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1"
BRANCH = "agent/parallel-content-sealing-proof-carrying-tdd-v1"
INVENTORY = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory"
PLAN = ROOT / "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md"
OBJECTIVES = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md"
BOARD = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md"
CONFIG = ROOT / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
BENCHMARK = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json"
SEAL = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"


TASK_TITLES = (
    "Freeze program controls, baseline, seals, and scheduler",
    "Inventory current CID, SHA, canonicalization, and seal paths",
    "Inventory current pytest proof-reuse identity and DI paths",
    "Inventory ZK, signing, key, and proof claim boundaries",
    "Instrument the current cold and warm critical path",
    "Define prepared canonical block and batch contracts",
    "Implement source-object identity bridging",
    "Implement persistent verified hash memo contracts in datasets",
    "Implement the kit hash-memo store",
    "Implement file chunk manifests and auxiliary change-detection profiles",
    "Implement parallel canonicalization and hash scheduling",
    "Implement optional native/Rust batch hashing qualification",
    "Implement verified batch immutable block storage",
    "Implement parallel Merkle leaf/level/category construction",
    "Implement Merkle branch memoization and proof-forest delta updates",
    "Define prepared full-checkpoint and delta-seal contracts",
    "Implement parallel full-checkpoint preparation",
    "Implement parallel delta-seal preparation",
    "Implement parallel proof/certificate verification",
    "Shorten and harden the serial commit boundary",
    "Qualify parallel sealing for concurrency, crash, and corruption",
    "Define fixture-definition closure contracts",
    "Implement fixture-definition closure extraction",
    "Define fixture-instance and injected-dependency contracts",
    "Implement reviewed dependency-injection commitment adapters",
    "Define and implement TestExecutionKeyV2",
    "Define composite phase receipt and statement contracts",
    "Integrate setup-bound execution-key assembly into pytest",
    "Implement guarded post-setup, pre-call reuse",
    "Implement narrowly gated pre-setup whole-item reuse",
    "Extend xdist controller/worker proof-reuse coordination",
    "Implement fixture- and proof-aware xdist scheduling",
    "Integrate current signed runner attestations",
    "Define aggregate test-batch and leaf contracts",
    "Define aggregate test-pass statement and public inputs",
    "Implement aggregate ZK circuit/backend adapter",
    "Implement proof batch coordinator and asynchronous pipeline",
    "Implement fixture-cohort and selected-test proof-forest units",
    "Integrate datasets semantic-state test/proof selection",
    "Add optional direct-execution proof profiles",
    "Implement FastTddLoopController@1",
    "Integrate the fast loop with incremental verification and repair",
    "Integrate context compression and proof-carrying procedure compilation",
    "Add CLI, control-service, and diagnostics surfaces",
    "Activate shadow_hash",
    "Activate shadow_reuse and shadow_proof",
    "Activate protected",
    "Activate required self-hosting",
    "Run the end-to-end acceptance matrix",
    "Run hashing and seal benchmarks",
    "Run pytest, proof, and TDD-loop benchmarks",
    "Run adversarial, privacy, and trust qualification",
    "Perform the required-mode self-hosted capstone",
    "Publish current-tree release, migration, and limitation report",
)
TASKS = {f"PCTDD-{n:03d}": title for n, title in enumerate(TASK_TITLES)}

GOALS: tuple[tuple[str, str, str | None], ...] = (
    ("PCTDD-G000", "Deliver and self-host parallel content sealing and proof-carrying TDD", None),
    ("PCTDD-G010", "Freeze authorities, claims, baselines, and controls", "PCTDD-G000"),
    ("PCTDD-G011", "Inventory current hashing, pytest, proof, and storage paths", "PCTDD-G010"),
    ("PCTDD-G012", "Freeze cold/warm critical-path benchmarks", "PCTDD-G010"),
    ("PCTDD-G013", "Seal identity, trust, and evidence-class boundaries", "PCTDD-G010"),
    ("PCTDD-G020", "Build parallel incremental content preparation", "PCTDD-G000"),
    ("PCTDD-G021", "Canonicalize once and persist verified hash memos", "PCTDD-G020"),
    ("PCTDD-G022", "Add chunk manifests and affected-branch Merkle updates", "PCTDD-G020"),
    ("PCTDD-G023", "Separate parallel seal preparation from serial publication", "PCTDD-G020"),
    ("PCTDD-G030", "Build fixture-aware exact pytest reuse", "PCTDD-G000"),
    ("PCTDD-G031", "Build fixture-definition and fixture-instance identities", "PCTDD-G030"),
    ("PCTDD-G032", "Build staged execution keys and composite phase receipts", "PCTDD-G030"),
    ("PCTDD-G033", "Add pre-setup and post-setup reuse with xdist coordination", "PCTDD-G030"),
    ("PCTDD-G040", "Build batched proof and ZK certification", "PCTDD-G000"),
    ("PCTDD-G041", "Integrate signed runner attestations", "PCTDD-G040"),
    ("PCTDD-G042", "Build aggregate selected-test proof statements and circuits", "PCTDD-G040"),
    ("PCTDD-G043", "Pipeline proof batching and incremental proof-forest sealing", "PCTDD-G040"),
    ("PCTDD-G050", "Integrate the fast TDD loop with supervisor intelligence", "PCTDD-G000"),
    ("PCTDD-G051", "Compose selection, proof reuse, Tactician/Hammer, and repair", "PCTDD-G050"),
    ("PCTDD-G052", "Compile successful TDD trajectories into procedures", "PCTDD-G050"),
    ("PCTDD-G053", "Enforce progressive dogfooding and cognitive-cost accounting", "PCTDD-G050"),
    ("PCTDD-G060", "Qualify security, performance, recovery, and release", "PCTDD-G000"),
    ("PCTDD-G061", "Run adversarial, corruption, concurrency, and privacy gates", "PCTDD-G060"),
    ("PCTDD-G062", "Benchmark, self-host, and publish current-tree release evidence", "PCTDD-G060"),
)


def dependencies() -> dict[str, tuple[str, ...]]:
    d: dict[str, tuple[str, ...]] = {task: () for task in TASKS}
    for n in range(1, 5): d[f"PCTDD-{n:03d}"] = ("PCTDD-000",)
    d.update({
        "PCTDD-005": ("PCTDD-001",), "PCTDD-006": ("PCTDD-001",),
        "PCTDD-007": ("PCTDD-001", "PCTDD-003"), "PCTDD-021": ("PCTDD-002",),
        "PCTDD-023": ("PCTDD-002",), "PCTDD-033": ("PCTDD-002", "PCTDD-003"),
        "PCTDD-008": ("PCTDD-007",), "PCTDD-009": ("PCTDD-005", "PCTDD-006"),
        "PCTDD-010": ("PCTDD-004", "PCTDD-005", "PCTDD-006", "PCTDD-007"),
        "PCTDD-022": ("PCTDD-002", "PCTDD-021"), "PCTDD-024": ("PCTDD-002", "PCTDD-023"),
        "PCTDD-026": ("PCTDD-002", "PCTDD-003", "PCTDD-023"),
        "PCTDD-034": ("PCTDD-026", "PCTDD-033"),
        "PCTDD-011": ("PCTDD-010",), "PCTDD-012": ("PCTDD-005", "PCTDD-008", "PCTDD-010"),
        "PCTDD-013": ("PCTDD-005", "PCTDD-010"), "PCTDD-025": ("PCTDD-021", "PCTDD-023"),
        "PCTDD-032": ("PCTDD-003", "PCTDD-025", "PCTDD-026"),
        "PCTDD-014": ("PCTDD-008", "PCTDD-013"), "PCTDD-015": ("PCTDD-005", "PCTDD-007", "PCTDD-013"),
        "PCTDD-018": ("PCTDD-003", "PCTDD-032"), "PCTDD-027": ("PCTDD-022", "PCTDD-024", "PCTDD-025"),
        "PCTDD-030": ("PCTDD-002", "PCTDD-025", "PCTDD-026"),
        "PCTDD-035": ("PCTDD-003", "PCTDD-034"),
        "PCTDD-016": ("PCTDD-012", "PCTDD-013", "PCTDD-015", "PCTDD-018"),
        "PCTDD-017": ("PCTDD-014", "PCTDD-015", "PCTDD-018"),
        "PCTDD-028": ("PCTDD-027", "PCTDD-032"), "PCTDD-029": ("PCTDD-027", "PCTDD-032"),
        "PCTDD-031": ("PCTDD-004", "PCTDD-022", "PCTDD-030"),
        "PCTDD-036": ("PCTDD-032", "PCTDD-033", "PCTDD-034", "PCTDD-035"),
        "PCTDD-019": ("PCTDD-016", "PCTDD-017", "PCTDD-018"),
        "PCTDD-037": ("PCTDD-014", "PCTDD-036"),
        "PCTDD-038": ("PCTDD-001", "PCTDD-002", "PCTDD-007", "PCTDD-021", "PCTDD-025"),
        "PCTDD-039": ("PCTDD-035",), "PCTDD-020": ("PCTDD-014", "PCTDD-018", "PCTDD-019"),
        "PCTDD-040": ("PCTDD-019", "PCTDD-027", "PCTDD-028", "PCTDD-029", "PCTDD-031", "PCTDD-036", "PCTDD-037", "PCTDD-038"),
        "PCTDD-041": ("PCTDD-040",), "PCTDD-042": ("PCTDD-040", "PCTDD-041"),
        "PCTDD-043": ("PCTDD-036", "PCTDD-040"), "PCTDD-044": ("PCTDD-020", "PCTDD-040"),
        "PCTDD-045": ("PCTDD-028", "PCTDD-036", "PCTDD-044"), "PCTDD-046": ("PCTDD-045",),
        "PCTDD-047": ("PCTDD-046",), "PCTDD-048": ("PCTDD-047",),
        "PCTDD-049": ("PCTDD-020", "PCTDD-048"), "PCTDD-050": ("PCTDD-036", "PCTDD-040", "PCTDD-048"),
        "PCTDD-051": ("PCTDD-048", "PCTDD-049", "PCTDD-050"),
        "PCTDD-052": ("PCTDD-042", "PCTDD-047", "PCTDD-051"),
        "PCTDD-053": ("PCTDD-049", "PCTDD-050", "PCTDD-051", "PCTDD-052"),
    })
    return d


DEPENDENCIES = dependencies()


def goal_for(n: int) -> str:
    if n == 0: return "PCTDD-G010"
    if n in (1, 2): return "PCTDD-G011"
    if n == 3: return "PCTDD-G013"
    if n == 4: return "PCTDD-G012"
    if 5 <= n <= 10: return "PCTDD-G021"
    if 11 <= n <= 14: return "PCTDD-G022"
    if 15 <= n <= 20: return "PCTDD-G023"
    if 21 <= n <= 24: return "PCTDD-G031"
    if 25 <= n <= 27: return "PCTDD-G032"
    if 28 <= n <= 31: return "PCTDD-G033"
    if n == 32: return "PCTDD-G041"
    if 33 <= n <= 35: return "PCTDD-G042"
    if 36 <= n <= 39: return "PCTDD-G043"
    if n in (40, 41): return "PCTDD-G051"
    if n == 42: return "PCTDD-G052"
    if 43 <= n <= 47: return "PCTDD-G053"
    if n in (48, 51): return "PCTDD-G061"
    return "PCTDD-G062"


def owner_for(n: int) -> str:
    if n in {5, 7, 9, 15, 21, 23, 25, 26, 33, 34}:
        return "endomorphosis/ipfs_datasets_py"
    if n in {8, 12, 14, 37}:
        return "endomorphosis/ipfs_kit_py"
    if n in {0, 1, 2, 3, 20, 48, 49, 50, 51, 52, 53}:
        return "cross-repository"
    return "endomorphosis/ipfs_accelerate_py"


def scope_for(n: int, owner: str) -> str:
    if n == 0:
        return "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json"
    if owner.endswith("ipfs_datasets_py"):
        return "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/pctdd, external/ipfs_datasets/tests/unit/logic/zkp/pctdd"
    if owner.endswith("ipfs_kit_py"):
        return "external/ipfs_kit/ipfs_kit_py/proof_seal, external/ipfs_kit/tests/proof_seal"
    if owner == "cross-repository":
        return "external/ipfs_accelerate/artifacts/parallel_content_sealing_proof_carrying_tdd, artifacts/parallel_content_sealing_proof_carrying_tdd"
    if 21 <= n <= 32:
        return "external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse, external/ipfs_accelerate/test/api/proof_carrying_tdd"
    if n <= 20 or n in {37, 38, 39}:
        return "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing, external/ipfs_accelerate/test/api/parallel_content_sealing"
    return "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor, external/ipfs_accelerate/test/api/proof_carrying_tdd"


def rollout_for(n: int) -> str:
    if n <= 43: return "bootstrap"
    if n == 44: return "shadow_hash"
    if n == 45: return "shadow_reuse, shadow_proof"
    if n == 46: return "protected"
    return "required"


def required_evidence(n: int) -> str:
    core = "exact source commit/tree/gitlinks; changed paths; independent tests; proof/claim class; receipt CID; limitations; verifier admission"
    if n >= 47:
        return core + "; pre_semantic_state_root; pre_proof_seal_root; source_snapshot; overlay_token; hash_preparation_receipt; selected_test_proof_manifest; fixture_test_execution_key_receipts; phase_disposition_receipts; aggregate_proof_or_evidence_tier_receipt; proof_forest_delta; prepared_seal_cid; seal_publication_receipt; post_semantic_state_root; post_proof_seal_root; expected_generation; resulting_generation; rollout_mode_required"
    return core


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return "sha256:" + h.hexdigest()


def write(path: Path, value: str | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def render_plan() -> str:
    waves = [
        "W0 PCTDD-000", "W1 PCTDD-001|002|003|004", "W2 PCTDD-005|006|007|021|023|033",
        "W3 PCTDD-008|009|010|022|024|026|034", "W4 PCTDD-011|012|013|025|032",
        "W5 PCTDD-014|015|018|027|030|035", "W6 PCTDD-016|017|028|029|031|036",
        "W7 PCTDD-019|037|038|039", "W8 PCTDD-020|040", "W9 PCTDD-041|042|043",
        "W10 PCTDD-044", "W11 PCTDD-045", "W12 PCTDD-046", "W13 PCTDD-047",
        "W14 PCTDD-048", "W15 PCTDD-049|050", "W16 PCTDD-051", "W17 PCTDD-052", "W18 PCTDD-053",
    ]
    return f"""# Parallel Content Sealing and Proof-Carrying TDD — {PLAN_REVISION}

Status: sealed bootstrap control program. Namespace: `{NAMESPACE}`.

## Outcome and invariant

Build and self-host a fail-closed fast TDD route across the existing accelerator, datasets, and kit authorities. The normative order is: verified exact content reuse; parallel immutable hash/seal preparation; exact datasets-owned semantic selection; fixture-aware execution-key construction; current setup; verified call reuse or current call; current teardown; signed receipt; asynchronous aggregate ZK certification; incremental proof-forest update; serial seal publication; deterministic repair/procedure reuse; minimal-context LLM only for a typed residual.

Parallel work may prepare immutable candidates and independently verify hashes, signatures, proofs, leaves, branches, and blocks. Final ordered WAL append, persisted-byte rehash, generation fence, expected-parent CAS, and current-root publication remain serial, controller-owned, and fail closed.

## Claim boundaries

- A CID establishes exact byte identity under its versioned canonicalization/multicodec/multihash profile, not execution or semantics. A Git blob OID is a verified memo lookup key only; filesystem metadata is candidate-only. A chunk manifest does not replace the raw full-stream CID.
- A signed execution receipt is an allowlisted issuer assertion under verifier-selected policy/key/epoch/revocation state, not independent execution proof.
- An aggregate ZK proof establishes only that the committed admitted receipt set satisfies the selected circuit. It does not prove CPython execution and cannot exceed or upgrade its leaf evidence.
- A direct execution proof establishes only the declared machine/program/committed inputs and outputs.
- An incremental seal commits an accepted parent plus complete valid changed/reused units. `TestPassStatementV1` remains unchanged; composite and aggregate successors are versioned.
- Simulated, mock, structural, or integrity-only proof paths are never production admission. Unknown dependency completeness broadens execution and proving.

## Authority reconciliation

`ipfs_datasets_py` owns deterministic semantic/proof schemas, selection, fixture/test identities, statement meaning, and commitment codecs. `ipfs_kit_py` owns verified immutable storage, hash/branch candidate records, proof forest persistence, WAL, recovery, and root CAS without deciding semantic admission. `ipfs_accelerate_py` owns source freezing, scheduling, pytest/xdist execution, receipt admission, proof batching, fast-loop composition, repair/context/procedure integration, and operational acceptance. Existing IncrementalProofSealer, proof-reuse plugin, semantic-state selector, signed runner attestations, TestPass statements, proof store/WAL/CAS, verification planner, Tactician/Hammer, semantic compression, and procedure compiler are predecessors to extend—not duplicate.

The operational task authority is DuckDB through one authenticated loopback Quack owner. DuckLake is a rebuildable, non-authoritative history/analytics projection that cannot schedule, admit, complete, or block a task. Markdown is sealed bootstrap intent only; PCTDD-000 becomes complete solely through evidence-gated DuckDB CAS.

## Technical workstreams

1. Canonicalize once into `PreparedCanonicalBlock@1`, rehash wherever trust crosses, memoize exact source/profile mappings, preserve raw SHA/CID, and add separate chunk manifests.
2. Bound filesystem readers, canonicalizers, hashers, verifiers, provers, store writers, and Merkle reducers. Preserve completion-order-independent output.
3. Build full/delta prepared seals and affected-branch Merkle updates without publication authority; shorten the existing serial sealer commit.
4. Derive collection seed, fixture-definition closure, reviewed fixture-instance commitment, `TestExecutionKeyV2`, and final trace. Opaque or incomplete adapters force full execution.
5. Make post-setup/pre-call reuse primary while running current teardown/finalizers. Pre-setup reuse stays narrowly pure/replay-safe. Never label proof reuse as pytest skip.
6. Bind composite phase receipts to signed runner policy; batch selected populations into aggregate statements/proofs asynchronously; keep direct CPython proof optional.
7. Compose exact selection, receipts, forest delta, seal, repair, compressed residual context, and proof-carrying procedure compilation in `FastTddLoopController@1`.

## Rollout and waves

The closed rollout is `bootstrap -> shadow_hash -> shadow_reuse -> shadow_proof -> protected -> required`. Promotion requires zero identity divergence, false phase reuse, stale reuse, selection false-negative regression, simulated admission, self-authority, unauthorized publication, lost update, escaped critical mutation, or secret/witness leak. Missing performance targets produce non-promotion, never weakened safety.

```text
{os.linesep.join(waves)}
```

Each worker receives a unique lease/fence/worktree, exact task CID and tree, bounded allowed paths/resources/context, verifier-owned acceptance, and one unique receipt. Shared exports, registries, plugin hooks, schemas, gitlinks, scheduler controls, and release evidence serialize through the current merge authority.

## Verification and benchmarks

Identity tests require serial/parallel/native byte and root equality, strict decoding, profile separation, and Git/chunk identity boundaries. Memo/Merkle tests cover corruption, dirty overlays, mode/type changes, full fallback, stale parents/snapshots, concurrent writers, crash phases, and recovery. Pytest tests cover closure invalidation, privacy-safe adapters, setup/call/teardown truth, xdist controller authority, signatures, aggregate completeness, cancellation, malicious workers, and import safety.

Preregistered hash workloads cover small/mixed/large files, clean and dirty states, 1/10/50% deltas, cold/warm memo, full/delta seal, bounded 1/2/4/8/16 workers, local and reproducible slow I/O. TDD workloads cover all fixture/reuse/proof classes. Supervisor metrics count model calls/tokens/context and exact avoidance causes. Targets are >=90% fewer warm unchanged bytes, >=50% faster 1% delta preparation, >=30% faster warm selected loops, >=25% fewer repeat general-model repairs, and >=30% smaller median model context, all subordinate to zero-regression floors.

## Terminal and rollback

Required completion means every mandatory task has accepted or explicitly permitted typed terminal evidence, validators pass, identities match, the required-mode capstone has complete pre/post roots and publication receipt, and final roots verify transitively. No unavailable prover/key ceremony/performance result may be fabricated. Rollback disables policy promotion, invalidates successor evidence, restores full hashing/execution/reproof fallback, and uses existing WAL/CAS recovery without rewriting predecessor history.
"""


def render_objectives() -> str:
    children: dict[str, list[str]] = {gid: [] for gid, _, _ in GOALS}
    for gid, _, parent in GOALS:
        if parent: children[parent].append(gid)
    lines = [f"# PCTDD objective hierarchy\n\nNamespace: `{NAMESPACE}`. Revision: `{PLAN_REVISION}`. DuckDB/Quack becomes live authority after evidence-gated materialization; this file is non-authoritative bootstrap intent.\n"]
    for gid, title, parent in GOALS:
        producing = [task for task in TASKS if goal_for(int(task[-3:])) == gid]
        if not producing: producing = [task for task in TASKS if goal_for(int(task[-3:])).startswith(gid[:8])]
        lines += [f"## {gid} {title}", "", "- Status: active", f"- Parent goal: {parent or 'none'}", "- Depends on: none", "- Priority: P0", f"- Track: {gid.lower()}", f"- Goal: {title} while preserving exact identity, claim, storage, execution, and publication authorities.", f"- Producing tasks: {', '.join(producing) if producing else 'derived through child goals'}", f"- Evidence: artifacts/parallel_content_sealing_proof_carrying_tdd/goals/{gid}.json", "- Acceptance: All producing tasks and child goals have independently admitted current-tree evidence or an explicitly permitted typed terminal, with no weakened safety floor.", ""]
    return "\n".join(lines)


def render_board() -> str:
    lines = [f"""# PCTDD supervisor task board

Namespace: `{NAMESPACE}`. Revision: `{PLAN_REVISION}`. This is a sealed bootstrap projection; DuckDB through Quack owns live status. Markdown is non-authoritative and is not completion authority. PCTDD-000 remains `todo` here and is completed only by an evidence-gated task-store transaction.

## Execution invariants

- Preserve exact canonical profiles and extend existing authorities only. Simulated proof is never admitted as production; an aggregate claim cannot exceed leaf evidence.
- Final ordered WAL and generation-bearing current-root CAS are serial and fail closed. Workers prepare immutable candidates and never publish authority.
- Workers cannot edit protected controls, approve their own output, select acceptance policy, or mark completion.
"""]
    for n, (task, title) in enumerate(TASKS.items()):
        owner = owner_for(n)
        scope = scope_for(n, owner)
        receipt = f"artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/{task}.json"
        output = receipt if n == 0 else f"{receipt}"
        deps = ", ".join(DEPENDENCIES[task]) or "none"
        operator = n == 0
        completion = "operator_evidence" if operator else "independent_evidence_and_review"
        schedulable = str(not operator).lower()
        lane = "operator" if operator else f"pctdd-lane-{n % 4}"
        protected = ", ".join(sorted(PROTECTED_ARTIFACTS)) if operator else "all scheduler protected_paths; no worker edits"
        no_model = "operator inventory, deterministic validators, source seals, and scheduler dry-run" if operator else "exact reuse -> deterministic analysis/tests/proofs -> symbolic repair -> procedure reuse"
        validation = "python scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py --check-all && python scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py --check-all" if operator else "focused owning-repository pytest plus cross-package API tests; identity/proof differential checks where applicable"
        lines += [f"## {task} {title}", "", "- Status: todo", f"- Completion mode: {completion}", f"- Is schedulable: {schedulable}", f"- Operator only: {str(operator).lower()}", "- Priority: P0", f"- Track: {goal_for(n)}", f"- Depends on: {deps}", f"- Bundle: pctdd/{goal_for(n).lower()}/{task.lower()}", f"- Parallel lane: {lane}", "- Resource class: cpu-medium; explicit prover/hash/store reservations when required", "- Timeout seconds: 21600", "- Provider role: bootstrap_operator" if operator else "- Provider role: implementation_worker_then_independent_validator", f"- Owning repository: {owner}", f"- Exact inputs: {PLAN_REVISION}; exact source forest; predecessor APIs; dependency seal; dependency receipts: {deps}", f"- Outputs: {output}", f"- Predicted paths: {scope}", f"- Predicted symbols: {title.replace(' ', '')}; versioned @1/@2 contracts only where the task introduces them", "- Interfaces: existing datasets semantic/proof contracts; kit immutable store/WAL/CAS; accelerator execution/scheduler/admission; adapters only", "- Preconditions: Exact clean leased worktree; current parent receipts; complete source/environment/policy/toolchain binding; no self-approval", f"- Declared effects: Modify only {scope}; emit immutable receipt; request reviewed merge through existing authority", f"- Validation: {validation}", f"- Required evidence: {required_evidence(n)}", f"- Acceptance criteria: {title} is implemented or reconciled against an existing current authority, independently tested on the exact tree, and honestly records unsupported/unavailable cases without changing claim meaning.", "- Conflict policy: Serialize shared schemas, exports, registries, plugin hooks, gitlinks, WAL/CAS, and release artifacts through the current merge queue; rebase and revalidate after any overlap.", "- Context budget: 24000 tokens maximum; send only affected source/contracts/counterexample/current receipts", f"- No-model route: {no_model}", "- Model fallback: General model only for a typed unresolved residual after deterministic/symbolic/procedure routes; model output is proposal-only", f"- Rollout mode: {rollout_for(n)}", f"- Protected paths: {protected}", "- Known limitations: Production ZK/key ceremony and optional native/direct-execution profiles may be typed unavailable; unknown dependency or fixture semantics force full fallback.", f"- Goal id: {goal_for(n)}", f"- Board namespace: {NAMESPACE}", ""]
    return "\n".join(lines)


PROTECTED_ARTIFACTS = (
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/authority_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/proof_claim_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/benchmark_preregistration.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
)


def source_record(name: str, relative: str) -> dict[str, Any]:
    repo = ROOT / relative
    return {"name": name, "path": relative, "origin": git("remote", "get-url", "origin", cwd=repo), "head": git("rev-parse", "HEAD", cwd=repo), "tree": git("rev-parse", "HEAD^{tree}", cwd=repo), "gitlink": git("rev-parse", "HEAD", cwd=repo), "dirty": False, "authority": True}


def render_config() -> dict[str, Any]:
    base = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.parallel-content-sealing-proof-carrying-tdd.scheduler_config@1",
        "program_identifier": NAMESPACE, "board_namespace": NAMESPACE, "accepted_plan_revision_alias": PLAN_REVISION,
        "taskboard_path": BOARD.relative_to(ROOT).as_posix(), "objectives_path": OBJECTIVES.relative_to(ROOT).as_posix(), "plan_path": PLAN.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py", "dependency_validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py", "materializer_path": "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
        "task_prefix": "PCTDD-", "goal_prefix": "PCTDD-G", "root_goal_id": "PCTDD-G000", "merge_target_branch": BRANCH,
        "source_binding": {"accelerator_required_ancestor": base, "accelerator_planning_revision": base, "accelerator_planning_tree": tree, "accelerator_required_branch": BRANCH, "bootstrap_task_source": "duckdb", "ipfs_accelerate_submodule_path": "external/ipfs_accelerate", "ipfs_accelerate_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_accelerate_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_datasets_submodule_path": "external/ipfs_datasets", "ipfs_datasets_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_datasets"), "ipfs_datasets_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_datasets"), "ipfs_kit_submodule_path": "external/ipfs_kit", "ipfs_kit_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_kit"), "ipfs_kit_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_kit"), "require_initialized_gitlinks": True, "require_superproject_gitlink_equals_nested_head": True, "require_clean_nested_worktree_at_task_start": True, "require_origin_main_as_ancestor": False, "record_recursive_repository_forest_at_launch": True, "changed_revision_requires_fresh_inventory_and_baseline": True, "planning_revision_is_runtime_completion_evidence": False},
        "initial_projection": {"task_count": 54, "task_dependency_count": sum(map(len, DEPENDENCIES.values())), "completed_task_ids": ["PCTDD-000"], "ready_task_ids": [f"PCTDD-{n:03d}" for n in range(1, 5)], "blocked_task_ids": [], "terminal_task_id": "PCTDD-053", "goal_count": 24, "root_goal_id": "PCTDD-G000"},
        "database_program": {"authority_mode": "quack", "task_source_kind": "duckdb", "endpoint_secret_handle": "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "quack_endpoint": "quack:127.0.0.1:42777", "store_id": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/control.duckdb", "store_generation": "pctdd-v1-g5", "schema_revision": "1", "event_store_path": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/events", "runtime_registry_path": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/registry", "worktree_root": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/worktrees", "export_profile": "pctdd-v1", "failover_policy": "fail_closed", "explicit_legacy": False},
        "operational_control_plane": {"name": "DuckDB + Quack + non-authoritative DuckLake", "duckdb_role": "authoritative transactional goals/tasks/CAS/fences/receipts/events", "quack_role": "authenticated exclusive loopback state owner", "ducklake_role": "rebuildable analytics/history projection", "direct_multi_process_duckdb_file_open_permitted": False, "automatic_file_fallback_permitted": False, "outage_policy": "fail_closed", "markdown_is_bootstrap_only": True},
        "ducklake_projection_program": {"mode": "enabled_non_authoritative", "authority": False, "may_grant_authority": False, "scheduling_prerequisite": False, "acceptance_prerequisite": False, "completion_prerequisite": False, "catalog_path": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/ducklake/catalog.duckdb", "data_path": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/ducklake/data", "logical_datasets": ["bootstrap_history"], "outage_policy": "typed unavailable and replayable; never block DuckDB authority"},
        "max_lanes": 4, "strict_task_sharding": True, "idle_lane_work_stealing": "", "exit_when_all_tracks_terminal": False, "objective_refill_enabled": False, "codebase_refill_enabled": False, "objective_goal_refinement_enabled": False, "retry_budget_guardrail_enabled": True, "dependency_guardrail_enabled": True, "reconciliation_guardrail_enabled": True,
        "poll_interval_seconds": 5, "daemon_interval_seconds": 20, "check_interval_seconds": 20, "stale_seconds": 1800, "watchdog_startup_grace_seconds": 600, "max_restarts": 3, "max_task_attempts": 2, "implementation_retry_budget": 1, "validation_retry_budget": 2, "merge_retry_budget": 2, "implementation_timeout_seconds": 7200, "implementation_max_timeout_seconds": 21600, "implementation_log_stall_seconds": 1200,
        "worktree_submodule_paths": ["external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"], "protected_paths": list(PROTECTED_ARTIFACTS),
        "runtime_paths": {"root": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5", "state": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/state", "worktrees": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/worktrees", "merge_queue": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/merge-queue", "logs": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/logs", "evidence": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/evidence", "quack_owner": "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/quack-owner", "generated_runtime_artifacts_are_completion_authority": False},
        "lanes": [{"index": n, "name": f"pctdd-lane-{n}", "strict_shard_remainder": n, "initial_focus": focus} for n, focus in enumerate(("content-identities", "pytest-fixtures", "proof-batching", "integration-qualification"))],
        "provider": {"primary_provider_id": "grok_cli", "primary_model_id": "grok-4.6", "fallback_provider_id": "codex", "fallback_model_id": "gpt-5.6-terra", "fallback_trigger": "primary_quota_exhausted", "fallback_reasoning_effort": "high", "max_concurrency": 4, "secrets_from_environment_only": True, "secrets_in_argv_prompts_logs_or_receipts": False},
        "resource_budgets": {"filesystem_readers": 4, "canonicalization_workers": 4, "sha_cid_workers": 4, "proof_verifiers": 2, "prover_workers": 1, "immutable_store_writers": 2, "merkle_reducers": 4, "test_workers": 4},
        "safety_floors": {"identity_divergence": 0, "false_test_phase_reuse": 0, "stale_authoritative_reuse": 0, "selection_false_negative_regressions": 0, "simulated_proof_admissions": 0, "model_created_proof_authority_completion": 0, "unauthorized_root_publications": 0, "lost_concurrent_updates": 0, "escaped_critical_seeded_defects": 0, "secret_witness_leaks": 0},
        "rollout_gates": ["bootstrap", "shadow_hash", "shadow_reuse", "shadow_proof", "protected", "required"], "benchmark_freeze": "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json", "required_evidence_per_task": "board.required_evidence", "current_tree_revalidation_before_launch": True,
    }


def benchmark_config() -> dict[str, Any]:
    return {"schema": "pctdd/benchmark-preregistration@1", "status": "frozen_before_implementation", "revision": PLAN_REVISION, "safety_floors": render_config()["safety_floors"], "hash_seal_workloads": {"layouts": ["many_small", "mixed_repository", "few_large"], "changes": ["clean", "1_percent", "10_percent", "50_percent", "dirty_overlay"], "cache": ["cold_memo", "warm_memo"], "seal": ["full_checkpoint", "delta_seal"], "workers": [1, 2, 4, 8, 16], "storage": ["local_ssd", "reproducible_slow_io"]}, "pytest_tdd_workloads": ["no_fixture", "pure", "module_session", "parameterized", "temp_filesystem", "transactional_db", "clock_rng", "service_simulation", "opaque_dynamic", "teardown_finalizer", "xdist", "slow_fast_calls", "proof_hit_miss", "changed_fixture", "changed_plugin_conftest", "changed_environment"], "metrics": ["wall_time", "cpu_time", "peak_rss", "files_opened", "bytes_read", "bytes_hashed", "memo_hits_rejections", "root_equality", "phase_times", "selection_recall", "mutation_escapes", "proof_batch_cost", "wal_cas_time", "model_calls_tokens_context", "calls_avoided_by_reuse_procedure_repair"], "targets": {"warm_bytes_reread_reduction_percent": 90, "warm_1_percent_delta_prepare_reduction_percent": 50, "warm_selected_loop_reduction_percent": 30, "repeat_general_llm_call_reduction_percent": 25, "median_model_context_reduction_percent": 30}, "anti_gaming": "No hidden failures, uncounted work, skipped validation, oracle leakage, or denominator exclusions."}


def inventories() -> dict[str, dict[str, Any]]:
    sources = [source_record("ipfs_accelerate_py", "external/ipfs_accelerate"), source_record("ipfs_datasets_py", "external/ipfs_datasets"), source_record("ipfs_kit_py", "external/ipfs_kit")]
    return {
        "repository_baseline.json": {"schema": "pctdd/repository-baseline@1", "captured_utc": "2026-08-28", "planning_root": str(ROOT), "planning_base_head": "8601408d6406681a14a9488d31d1cd9a16164649", "planning_base_tree": "e35dfaebbd229d7e7de988b2e0345444d9284221", "branch": BRANCH, "sources": sources, "dirty_user_tree_preserved": True, "original_tree_evidence": {"root_status_sha256": "f0a737302e4455c55e60edc28403da4f339e9b64811cc0b0dcf0c87e2d9629b3", "root_diff_sha256": "72f6c22550da009960d570f8b5128077c9160ef2d4ae2d5cc75498ab69e08fb7", "root_untracked_list_sha256": "c20615c1a314943dca33d6d1764014096ebbd9632a5404b55992a97883a2a8ac", "accelerate_status_sha256": "c261a97a9d4d91da96af386077e5cdf9c1532273614a73911d8c07a063913798", "datasets_status_sha256": "a1b4619c21ab5c19d90aa666b48d10d7f5034a2abe2ce57e0f854892429d9c83"}, "evidence_note": "Hashes bind captured status/diff/path lists without copying user content into the control worktree."},
        "authority_matrix.json": {"schema": "pctdd/authority-matrix@1", "canonical_semantic_and_statement_authority": "ipfs_datasets_py", "verified_storage_wal_cas_authority": "ipfs_kit_py", "execution_scheduling_admission_authority": "ipfs_accelerate_py", "task_transaction_authority": "DuckDB via exclusive authenticated Quack owner", "analytics_projection": "DuckLake non-authoritative", "markdown": "non-authoritative bootstrap", "forbidden_duplicates": ["proof system", "canonical profile", "CID system", "pytest runner", "test selector", "proof cache", "block store", "WAL", "current-root store", "agent framework", "scheduler", "worktree system", "provider router", "merge engine"]},
        "overlap_gap_matrix.json": {"schema": "pctdd/overlap-gap@1", "entries": [{"capability": "IncrementalProofSealer full/delta/WAL/CAS", "owner": "ipfs_accelerate_py + ipfs_kit_py", "classification": "available_with_caveats", "successor": "prepared-seal consumer adapter"}, {"capability": "pytest proof reuse/DI/xdist controller publication", "owner": "ipfs_accelerate_py", "classification": "available_with_caveats", "successor": "fixture-staged V2 identity/composite phases"}, {"capability": "semantic selection", "owner": "ipfs_datasets_py consumed by accelerate", "classification": "available", "successor": "adapter only"}, {"capability": "verified persistent hash memo", "owner": "datasets contract + kit store", "classification": "partial", "successor": "versioned records/store"}, {"capability": "aggregate selected-test ZK", "owner": "datasets statement + accelerate backend", "classification": "missing", "successor": "versioned aggregate statement; typed unavailable without admitted production key"}, {"capability": "FastTddLoopController", "owner": "ipfs_accelerate_py", "classification": "partial", "successor": "compose current authorities"}]},
        "hash_identity_inventory.json": {"schema": "pctdd/hash-identity@1", "rules": ["CID is exact byte identity under a versioned profile", "Git blob OID is memo lookup key only", "filesystem metadata nominates a candidate only", "chunk manifest does not replace raw full-stream CID", "ordinary SHA-256 of one stream is not composed from independent chunk hashes"], "preserve": ["canonical bytes", "codec", "multicodec", "multihash", "CID version", "multibase", "ordering", "normalization"]},
        "hashing_critical_path.json": {"schema": "pctdd/hashing-critical-path@1", "current_path": ["source discovery", "canonical serialization", "SHA/CID", "proof verification", "Merkle", "immutable store", "serial WAL/CAS"], "observed_gaps": ["duplicate serialization/hashing requires task instrumentation", "unverified metadata cannot authorize reuse", "parallel immutable preparation absent or partial"], "candidate_methods": ["hashlib.file_digest", "readinto reusable buffer", "safe mmap", "threaded independent SHA", "process canonicalization", "optional qualified native batch"]},
        "pytest_identity_inventory.json": {"schema": "pctdd/pytest-identity@1", "authority_paths": ["external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py", "external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py", "external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runner_pass_attestation.py"], "current": ["locator-first seed", "runtime trace", "DI lookup/store/provider/issuer", "controller-owned xdist publication"], "gap": "exact fixture-instance key becomes safely authoritative only after current setup; add pre-call V2 key and honest composite phase receipt"},
        "fixture_adapter_inventory.json": {"schema": "pctdd/fixture-adapter-inventory@1", "closed_reuse_classes": ["pure", "deterministic_snapshot", "transactional", "idempotent_external", "effectful_replayable", "effectful_nonreplayable", "opaque"], "default": "opaque", "initial_review_candidates": ["immutable scalar", "frozen canonical record", "path-independent temp directory root", "transaction baseline", "clock", "RNG", "service image/config/corpus", "explicit environment projection"], "secret_rule": "commit provider identity/version/epoch/policy, never secret bytes"},
        "proof_claim_matrix.json": {"schema": "pctdd/proof-claim-matrix@1", "IntegrityCommitment": {"establishes": "exact bytes/digest/CID/Merkle inclusion", "does_not": "execution or semantics"}, "SignedExecutionReceipt": {"establishes": "trusted issuer assertion under explicit verifier policy", "does_not": "independent faithful execution"}, "ReceiptAggregationZkProof": {"establishes": "committed admitted receipt population satisfies circuit", "does_not": "CPython execution and cannot exceed leaf evidence"}, "DirectExecutionProof": {"establishes": "declared machine/program/inputs executed", "does_not": "broader correctness"}, "IncrementalCommitSeal": {"establishes": "accepted parent plus complete valid changed/reused units", "does_not": "arbitrary repository correctness"}, "legacy": "TestPassStatementV1 remains unchanged", "production": "simulated or structural proof cannot be admitted"},
        "zkp_backend_inventory.json": {"schema": "pctdd/zkp-backend-inventory@1", "groth16_binary": {"classification": "real_backend_binary_present_unqualified", "sha256": "sha256:7cd14f8810fda8c16bf8a3b3ad02fda67b3c85ff0fc05883e21825781e33ce15", "production_admitted": False, "reason": "presence and key bytes do not establish ceremony/allowlist/current public-input binding"}, "provekit": {"classification": "adapter_source_present", "production_admitted": False}, "simulated": {"classification": "simulated", "production_admitted": False}, "direct_cpython": {"classification": "research_only", "production_admitted": False}, "ordinary_inner_loop": "signed receipts permitted by explicit policy; ZK asynchronous"},
        "storage_recovery_inventory.json": {"schema": "pctdd/storage-recovery@1", "existing": ["immutable proof-seal persistence", "ordered WAL", "current-pointer compare-and-swap", "stale-parent rejection", "crash recovery"], "authority": "kit stores/verifies bytes; accelerate admits proof/test meaning", "required_invariant": "parallel immutable preparation has no publication authority; final ordered WAL and generation-bearing current-root CAS remain serial and fail closed"},
        "benchmark_preregistration.json": benchmark_config(),
    }


def render_seal() -> dict[str, Any]:
    artifacts = {path: sha256(ROOT / path) for path in REQUIRED_HASHED if (ROOT / path).is_file()}
    python = Path(sys.executable).resolve()
    return {"schema": "pctdd/dependency-source-seal@1", "status": "sealed", "board_namespace": NAMESPACE, "plan_revision": PLAN_REVISION, "artifacts": artifacts, "sources": [source_record("ipfs_accelerate_py", "external/ipfs_accelerate"), source_record("ipfs_datasets_py", "external/ipfs_datasets"), source_record("ipfs_kit_py", "external/ipfs_kit")], "environment": {"python": {"name": "python", "executable": str(python), "version": platform.python_version(), "sha256": sha256(python)}, "pytest_version": "9.1.1", "pytest_xdist_version": "3.8.0", "duckdb_version": "1.5.5", "capabilities": {"quack": {"name": "quack", "available": True, "loaded": True, "version": "c154811", "required_for_launch": True}, "ducklake": {"name": "ducklake", "available": True, "loaded": True, "version": "d8a1881e", "required_for_launch": False}, "lean": {"name": "lean", "available": True, "version": "Lean (version 4.33.1, aarch64-unknown-linux-gnu, commit 819816b2e0a3bf405af45ae5c7af2491d8f5bee6, Release)", "required": False, "provisioning": "ipfs_datasets_py managed theorem-prover installer"}, "cvc5": {"name": "cvc5", "available": True, "version": "This is cvc5 version 1.3.3 [git 8ff882e on branch HEAD]", "required": False, "provisioning": "ipfs_datasets_py managed theorem-prover installer"}, "coq": {"name": "coq", "available": False, "version": "", "required": False, "classification": "typed_optional_unavailable_at_capture", "provisioning": "ipfs_datasets_py managed theorem-prover installer"}}}, "proof_backends": inventories()["zkp_backend_inventory.json"]}


REQUIRED_HASHED = (
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
    *(f"docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/{name}" for name in ("repository_baseline.json", "authority_matrix.json", "overlap_gap_matrix.json", "hash_identity_inventory.json", "hashing_critical_path.json", "pytest_identity_inventory.json", "fixture_adapter_inventory.json", "proof_claim_matrix.json", "zkp_backend_inventory.json", "storage_recovery_inventory.json", "benchmark_preregistration.json")),
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
)


def main() -> int:
    if len(TASKS) != 54 or len(GOALS) != 24: raise SystemExit("sealed cardinality changed")
    write(PLAN, render_plan()); write(OBJECTIVES, render_objectives()); write(BOARD, render_board())
    write(CONFIG, render_config()); write(BENCHMARK, benchmark_config())
    for name, value in inventories().items(): write(INVENTORY / name, value)
    for path, title in ((ROOT / "test/api/parallel_content_sealing/README.md", "Parallel content sealing API qualification"), (ROOT / "test/api/proof_carrying_tdd/README.md", "Proof-carrying TDD API qualification"), (ROOT / "benchmarks/agent_supervisor/parallel_content_sealing/README.md", "Parallel content sealing benchmarks"), (ROOT / "benchmarks/agent_supervisor/proof_carrying_tdd/README.md", "Proof-carrying TDD benchmarks")):
        write(path, f"# {title}\n\nProtected bootstrap placeholder. Implementation and measured results are owned by the corresponding PCTDD worker tasks; no result is inferred from this directory.\n")
    write(SEAL, render_seal())
    write(ROOT / "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json", {"schema": "pctdd/operator-control-receipt@1", "task_id": "PCTDD-000", "board_namespace": NAMESPACE, "plan_revision": PLAN_REVISION, "status": "sealed_pending_evidence_gated_database_completion", "markdown_non_authoritative": True, "completion_authority": "DatabaseTaskSource.record_evidence plus compare_and_set_status through the DuckDB/Quack control plane", "dependency_seal": SEAL.relative_to(ROOT).as_posix(), "claim": "This tracked receipt identifies the operator control package; it does not itself complete the task."})
    print(json.dumps({"namespace": NAMESPACE, "tasks": len(TASKS), "goals": len(GOALS), "dependencies": sum(map(len, DEPENDENCIES.values())), "sealed_artifacts": len(render_seal()["artifacts"])}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
