"""Tests for fenced multi-phase objective reconciliation (PTR-121)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "proof_backed_test_reuse_objective_reconciliation.py"
SUPERVISOR = ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"

ALL_GOAL_IDS = (
    "PTR-G000",
    "PTR-G010",
    "PTR-G020",
    "PTR-G030",
    "PTR-G040",
    "PTR-G050",
    "PTR-G060",
    "PTR-G070",
    "PTR-G080",
    "PTR-G090",
    "PTR-G100",
    "PTR-G110",
)
CHILD_GOAL_IDS = tuple(gid for gid in ALL_GOAL_IDS if gid not in {"PTR-G000", "PTR-G110"})


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "proof_backed_test_reuse_objective_reconciliation", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def recon_mod() -> Any:
    return _load_module()


def _goal_block(
    goal_id: str,
    title: str,
    *,
    status: str = "active",
    parent: str = "",
    depends_on: str = "",
) -> str:
    return textwrap.dedent(
        f"""\
        ## {goal_id} {title}

        - Status: {status}
        - Parent: {parent}
        - Depends on: {depends_on}
        - Fib priority: 1
        - Priority: P0
        - Track: test
        - Bundle: test/bundle
        - Goal: synthetic goal for {goal_id}
        - Evidence: synth/{goal_id}@1
        - Acceptance criteria: synth/{goal_id}@1
        - Outputs: none
        - Validation: true
        - Acceptance: synthetic
        - Gap task: none
        """
    )


def _objective_text() -> str:
    blocks = [
        "# Synthetic PTR objective heap\n",
        _goal_block("PTR-G000", "Root", parent=""),
    ]
    for goal_id in CHILD_GOAL_IDS:
        blocks.append(_goal_block(goal_id, f"Child {goal_id}", parent="PTR-G000"))
    blocks.append(
        _goal_block(
            "PTR-G110",
            "Final gate",
            parent="PTR-G000",
            depends_on="PTR-G100",
        )
    )
    return "\n".join(blocks)


def _todo_text(*, open_tasks: bool = False) -> str:
    status = "todo" if open_tasks else "completed"
    tasks = []
    for index in range(1, 4):
        tasks.append(
            textwrap.dedent(
                f"""\
                ## PTR-{index:03d} Task {index}

                - Status: {status}
                - Depends on:
                - Goal id: PTR-G010
                """
            )
        )
    return "# Board\n\n" + "\n".join(tasks)


def _init_git_repo(repo: Path, *, tree_label: str = "tree-aaa") -> str:
    """Create a minimal clean git checkout; return the real tree id."""

    subprocess.run(
        ["git", "init", "-b", "agent/proof-backed-test-reuse"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "ptr@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PTR Test"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "-A"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"fixture {tree_label}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return tree


def _write_fixture(
    tmp_path: Path,
    *,
    open_tasks: bool = False,
    healthy: bool = True,
    gate_tree: str | None = None,
    include_gate: bool = True,
    include_evidence: bool = True,
    init_git: bool = True,
) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    objective = repo / "objectives.md"
    todo = repo / "todo.md"
    objective.write_text(_objective_text(), encoding="utf-8")
    todo.write_text(_todo_text(open_tasks=open_tasks), encoding="utf-8")
    real_tree = "tree-aaa"
    if init_git:
        real_tree = _init_git_repo(repo)
    if gate_tree is None:
        gate_tree = real_tree
    state = tmp_path / "state" / "projection" / "completion"
    state.mkdir(parents=True)
    gate = state / "goal_completion_gate.json"
    evidence = state / "goal_completion_evidence.json"
    lifecycle = state / "objective_projection.md"
    candidate = state / "objective_candidate.md"
    health = state / "supervisor_health_input.json"
    status = state / "closeout_status.json"
    if include_gate:
        gate.write_text(
            json.dumps(
                {
                    "passed": True,
                    "repository_tree": gate_tree,
                    "producing_task_id": "PTR-122",
                    "final_gate_criterion": ("ptr/final-current-tree-gate@1"),
                    "root_criterion": ("ptr/cross-repository-current-tree-gate@1"),
                    "captured_at_unix_ns": 1_700_000_000_000_000_000,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if include_evidence:
        goals = {
            goal_id: {"evidence_cids": [f"baguqeera{goal_id[-3:].lower()}xx"]}
            for goal_id in ALL_GOAL_IDS
        }
        evidence.write_text(
            json.dumps(
                {
                    "repository_tree": gate_tree,
                    "goals": goals,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    health.write_text(
        json.dumps(
            {
                "schema": ("ipfs_accelerate_py/proof-backed-test-reuse-supervisor-health-input@1"),
                "status": {
                    "healthy": healthy,
                    "work_complete": healthy,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "repo": repo,
        "objective": objective,
        "todo": todo,
        "gate": gate,
        "evidence": evidence,
        "lifecycle": lifecycle,
        "candidate": candidate,
        "health": health,
        "status": status,
        "state": state,
        "tree_id": real_tree,  # type: ignore[dict-item]
    }


def _make_reconciler(
    recon_mod: Any,
    paths: dict[str, Path],
    **overrides: Any,
) -> Any:
    tree_id = str(paths.get("tree_id") or "tree-aaa")
    kwargs: dict[str, Any] = {
        "repo_root": paths["repo"],
        "objective_path": paths["objective"],
        "todo_path": paths["todo"],
        "gate_path": paths["gate"],
        "evidence_path": paths["evidence"],
        "lifecycle_projection_path": paths["lifecycle"],
        "candidate_objective_path": paths["candidate"],
        "supervisor_health_input_path": paths["health"],
        "status_path": paths["status"],
        "phase_count": 3,
        # Prefer the real git tree when the fixture initialized a repo;
        # tests that need a synthetic runner override git_runner/baseline.
        "baseline_tree": tree_id,
        "allow_synthetic_evidence": True,
        "optional_services": {
            "groth16": False,
            "provekit": False,
            "ipfs": True,
        },
        "validation_runner": lambda: {"passed": True, "mode": "off"},
    }
    kwargs.update(overrides)
    return recon_mod.ProofTestReuseObjectiveReconciler(**kwargs)


# ---------------------------------------------------------------------------
# Argv contract
# ---------------------------------------------------------------------------


def test_module_exports_predicted_symbols(recon_mod: Any) -> None:
    assert hasattr(recon_mod, "ProofTestReuseObjectiveReconciler")
    assert hasattr(recon_mod, "ObjectiveCloseoutPhase")
    assert hasattr(recon_mod, "ObjectiveCloseoutReceipt")
    assert hasattr(recon_mod, "ObjectiveCloseoutFence")
    assert recon_mod.PROOF_TEST_REUSE_OBJECTIVE_RECONCILER_INTERFACE.endswith("@1")
    assert recon_mod.OBJECTIVE_COMPLETION_EVIDENCE_ARTIFACT == (
        "ObjectiveCompletionEvidenceArtifact"
    )


def test_cli_accepts_exact_supervisor_closeout_argv(recon_mod: Any) -> None:
    """Supervisor closeout argv must parse without extras being required."""

    parser = recon_mod.build_arg_parser()
    # Mirrors scripts/proof_backed_test_reuse_supervisor.py _closeout command.
    argv = [
        "--repo-root",
        "/repo",
        "--objective-path",
        "/repo/obj.md",
        "--todo-path",
        "/repo/todo.md",
        "--gate-path",
        "/state/gate.json",
        "--evidence-path",
        "/state/evidence.json",
        "--lifecycle-projection-path",
        "/state/life.md",
        "--candidate-objective-path",
        "/state/cand.md",
        "--supervisor-health-input-path",
        "/state/health.json",
        "--status-path",
        "/state/status.json",
        "--phase-count",
        "3",
    ]
    args = parser.parse_args(argv)
    assert args.phase_count == 3
    assert args.report_only is False
    # Confirm supervisor source still emits this flag set.
    source = SUPERVISOR.read_text(encoding="utf-8")
    for flag in (
        "--repo-root",
        "--objective-path",
        "--todo-path",
        "--gate-path",
        "--evidence-path",
        "--lifecycle-projection-path",
        "--candidate-objective-path",
        "--supervisor-health-input-path",
        "--status-path",
        "--phase-count",
    ):
        assert flag in source


# ---------------------------------------------------------------------------
# Report-only
# ---------------------------------------------------------------------------


def test_report_only_never_writes_repository(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    objective_before = paths["objective"].read_bytes()
    todo_before = paths["todo"].read_bytes()
    reconciler = _make_reconciler(recon_mod, paths, report_only=True)
    result = reconciler.diagnose()
    assert result["mode"] == "report_only"
    assert result["repository_written"] is False
    assert result["operator_commit_required"] is False
    assert paths["objective"].read_bytes() == objective_before
    assert paths["todo"].read_bytes() == todo_before
    # Report-only must not create candidate / status outputs either.
    assert not paths["candidate"].exists()
    assert not paths["status"].exists()
    assert not paths["lifecycle"].exists()


@pytest.mark.parametrize(
    ("include_gate", "include_evidence", "expected_reason"),
    (
        (False, True, "missing_gate_artifact"),
        (True, False, "missing_evidence_artifact"),
    ),
)
def test_report_only_fails_closed_when_required_artifact_is_missing(
    recon_mod: Any,
    tmp_path: Path,
    include_gate: bool,
    include_evidence: bool,
    expected_reason: str,
) -> None:
    paths = _write_fixture(
        tmp_path,
        include_gate=include_gate,
        include_evidence=include_evidence,
    )
    files_before = {
        path.relative_to(paths["repo"]): path.read_bytes()
        for path in paths["repo"].rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == [expected_reason]
    assert result["diagnosis"]["ready_for_closeout"] is False
    assert result["repository_written"] is False
    files_after = {
        path.relative_to(paths["repo"]): path.read_bytes()
        for path in paths["repo"].rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert files_after == files_before
    assert not paths["candidate"].exists()
    assert not paths["status"].exists()
    assert not paths["lifecycle"].exists()


@pytest.mark.parametrize(
    ("artifact_key", "mutation", "expected_reason"),
    (
        (
            "gate",
            {"repository_tree": "tree-from-another-checkout"},
            "mismatched_gate_artifact",
        ),
        (
            "evidence",
            {"repository_tree": "tree-from-another-checkout"},
            "mismatched_evidence_artifact",
        ),
        ("gate", {"stale": True}, "stale_gate_artifact"),
        ("evidence", {"stale": True}, "stale_evidence_artifact"),
    ),
)
def test_report_only_detects_stale_or_mismatched_artifacts(
    recon_mod: Any,
    tmp_path: Path,
    artifact_key: str,
    mutation: dict[str, Any],
    expected_reason: str,
) -> None:
    paths = _write_fixture(tmp_path)
    artifact_path = paths[artifact_key]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact.update(mutation)
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_before = artifact_path.read_bytes()

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == [expected_reason]
    assert result["diagnosis"]["artifact_notes"]
    assert artifact_path.read_bytes() == artifact_before
    assert not paths["candidate"].exists()
    assert not paths["status"].exists()
    assert not paths["lifecycle"].exists()


def test_report_only_detects_failed_gate(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
    gate["passed"] = False
    paths["gate"].write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["gate_failed"]


def test_report_only_requires_explicit_gate_tree_binding(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
    del gate["repository_tree"]
    paths["gate"].write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["missing_gate_tree_binding"]


def test_report_only_rejects_conflicting_gate_tree_aliases(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
    gate["binding"] = {"tree_id": "tree-from-another-checkout"}
    paths["gate"].write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["mismatched_gate_artifact"]


def test_report_only_requires_explicit_gate_passed_decision(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    gate = json.loads(paths["gate"].read_text(encoding="utf-8"))
    del gate["passed"]
    paths["gate"].write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["missing_gate_passed"]


@pytest.mark.parametrize("missing_goal_id", (None, "PTR-G100"))
def test_report_only_requires_admissible_evidence_for_every_child_goal(
    recon_mod: Any,
    tmp_path: Path,
    missing_goal_id: str | None,
) -> None:
    paths = _write_fixture(tmp_path)
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    if missing_goal_id is None:
        evidence["goals"] = {}
        expected = [f"missing_evidence:{goal_id}" for goal_id in CHILD_GOAL_IDS]
    else:
        del evidence["goals"][missing_goal_id]
        expected = [f"missing_evidence:{missing_goal_id}"]
    paths["evidence"].write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(
        recon_mod,
        paths,
        report_only=True,
        allow_synthetic_evidence=False,
    ).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == expected


def test_report_only_rejects_present_child_with_empty_evidence(
    recon_mod: Any, tmp_path: Path
) -> None:
    paths = _write_fixture(tmp_path)
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    evidence["goals"]["PTR-G010"]["evidence_cids"] = []
    paths["evidence"].write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(
        recon_mod,
        paths,
        report_only=True,
        allow_synthetic_evidence=False,
    ).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["missing_evidence:PTR-G010"]


def test_normal_diagnosis_requires_gate_and_evidence_artifacts(
    recon_mod: Any, tmp_path: Path
) -> None:
    paths = _write_fixture(
        tmp_path,
        include_gate=False,
        include_evidence=False,
    )

    diagnosis = _make_reconciler(
        recon_mod,
        paths,
        report_only=False,
        allow_synthetic_evidence=False,
    )._collect_diagnosis(write_allowed=True)

    assert diagnosis["ready_for_closeout"] is False
    assert diagnosis["reason_codes"] == [
        "missing_gate_artifact",
        *(f"missing_evidence:{goal_id}" for goal_id in CHILD_GOAL_IDS),
    ]


def test_ptr122_gate_with_ptr120_evidence_passes_and_extracts_canonical_ids(
    recon_mod: Any, tmp_path: Path
) -> None:
    paths = _write_fixture(tmp_path)
    tree = str(paths["tree_id"])
    final_criterion = "ptr/final-current-tree-gate@1"
    root_criterion = "ptr/cross-repository-current-tree-gate@1"

    def final_evidence(goal_id: str, criterion: str) -> dict[str, Any]:
        return {
            "producing_task_id": "PTR-122",
            "goal_id": goal_id,
            "acceptance_criterion": criterion,
            "satisfied_requirements": [criterion],
            "authority": "authoritative",
            "tree_id": tree,
        }

    gate = {
        "schema": ("ipfs_accelerate_py/agent-supervisor/proof-test-reuse-persisted-gate-bundle@1"),
        "interface": "ProofTestReusePersistedGateBundle@1",
        "producing_task_id": "PTR-122",
        "tree_id": tree,
        "git_tree_id": tree,
        "decision": {
            "passed": True,
            "final_gate_completion_evidence": final_evidence("PTR-G110", final_criterion),
            "root_completion_evidence": final_evidence("PTR-G000", root_criterion),
        },
    }
    evidence = {
        "schema": ("ipfs_accelerate_py.agent_supervisor.objective_daemon.completion_evidence.v1"),
        "interface": "ObjectiveCompletionEvidenceArtifact",
        "binding": {
            "repository_id": "repo:fixture",
            "tree_id": tree,
            "git_tree_id": tree,
        },
        "goals": {
            goal_id: {
                "binding": {
                    "repository_id": "repo:fixture",
                    "tree_id": tree,
                },
                "completion_evidence_records": [
                    {
                        "provenance_cid": f"baguqeera{goal_id[-3:].lower()}ptr120",
                        "validation_passed": True,
                        "repository_tree": tree,
                        "tree_id": tree,
                        "freshness": {"fresh": True},
                    }
                ],
            }
            for goal_id in ALL_GOAL_IDS
        },
    }
    paths["gate"].write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["evidence"].write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        report_only=True,
        allow_synthetic_evidence=False,
    )

    result = reconciler.diagnose()

    assert result["passed"] is True
    assert result["reason_codes"] == []
    assert reconciler._evidence_for_goal("PTR-G010") == ["baguqeera010ptr120"]

    record = evidence["goals"]["PTR-G010"]["completion_evidence_records"][0]
    del record["repository_tree"]
    del record["tree_id"]
    paths["evidence"].write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rejected = reconciler.diagnose()
    assert rejected["passed"] is False
    assert rejected["reason_codes"] == ["missing_evidence:PTR-G010"]


def test_ptr120_aggregate_gate_cannot_substitute_for_ptr122_final_gate(
    recon_mod: Any,
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    tree = str(paths["tree_id"])
    goals = {required_goal_id: {"passed": True} for required_goal_id in ALL_GOAL_IDS}
    paths["gate"].write_text(
        json.dumps(
            {
                "binding": {"tree_id": tree, "git_tree_id": tree},
                "producing_task_id": "PTR-120",
                "goals": goals,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _make_reconciler(recon_mod, paths, report_only=True).diagnose()

    assert result["passed"] is False
    assert result["reason_codes"] == ["wrong_gate_producer"]


def test_report_only_via_cli(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, open_tasks=True)
    code = recon_mod.main(
        [
            "--repo-root",
            str(paths["repo"]),
            "--objective-path",
            str(paths["objective"]),
            "--todo-path",
            str(paths["todo"]),
            "--gate-path",
            str(paths["gate"]),
            "--evidence-path",
            str(paths["evidence"]),
            "--lifecycle-projection-path",
            str(paths["lifecycle"]),
            "--candidate-objective-path",
            str(paths["candidate"]),
            "--supervisor-health-input-path",
            str(paths["health"]),
            "--status-path",
            str(paths["status"]),
            "--phase-count",
            "3",
            "--report-only",
        ]
    )
    # Open tasks => not ready => non-zero, but still no repo writes.
    assert code == 1
    assert paths["objective"].read_text(encoding="utf-8") == _objective_text()
    assert not paths["candidate"].exists()


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def test_closeout_refuses_open_tasks(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, open_tasks=True)
    reconciler = _make_reconciler(recon_mod, paths)
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    assert exc.value.reason_code == "open_tasks"
    assert "PTR-001" in exc.value.message


def test_closeout_refuses_dirty_checkout(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    # Dirty the real checkout after the fixture commit.
    (paths["repo"] / "extra.txt").write_text("dirty\n", encoding="utf-8")
    reconciler = _make_reconciler(recon_mod, paths)
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    assert exc.value.reason_code == "dirty_checkout"


def test_closeout_refuses_changed_source_tree(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        baseline_tree="not-the-real-tree",
    )
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    assert exc.value.reason_code == "dirty_checkout"


def test_closeout_refuses_unhealthy_supervisor(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, healthy=False)
    reconciler = _make_reconciler(recon_mod, paths)
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    assert exc.value.reason_code == "unhealthy_supervisor"


def test_closeout_refuses_concurrent_writers(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    fence_path = paths["state"] / "closeout.fence"
    # Hold the fence exclusively in this process.
    holder = recon_mod.ObjectiveCloseoutFence(fence_path=fence_path, writer_id="holder-1")
    holder.acquire()
    try:
        reconciler = _make_reconciler(
            recon_mod, paths, fence_path=fence_path, writer_id="challenger-2"
        )
        with pytest.raises(recon_mod.ConcurrentWriterError):
            reconciler.closeout()
    finally:
        holder.release()


def test_closeout_refuses_stale_gate_in_phase_three(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, gate_tree="tree-stale")
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        allow_synthetic_evidence=False,
    )
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    # Failure may surface as stale gate or phase3 failure.
    assert exc.value.reason_code in {
        "mismatched_gate_artifact",
        "stale_or_mismatched_gate",
        "phase3_failed",
        "stale_artifact",
        "gate_not_admitted",
        "missing_evidence:PTR-G010",
        "missing_evidence:PTR-G020",
        "missing_evidence:PTR-G030",
        "missing_evidence:PTR-G040",
        "missing_evidence:PTR-G050",
        "missing_evidence:PTR-G060",
        "missing_evidence:PTR-G070",
        "missing_evidence:PTR-G080",
        "missing_evidence:PTR-G090",
        "missing_evidence:PTR-G100",
        "phase2_failed",
    }


# ---------------------------------------------------------------------------
# Happy path phases
# ---------------------------------------------------------------------------


def test_closeout_three_phases_and_candidate(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    objective_before = paths["objective"].read_text(encoding="utf-8")
    reconciler = _make_reconciler(recon_mod, paths)
    result = reconciler.closeout()

    assert result["passed"] is True
    assert result["closeout_passed"] is True
    assert result["operator_commit_required"] is True
    assert result["repository_written"] is False
    assert result["phase_count"] == 3
    assert paths["candidate"].is_file()
    assert paths["lifecycle"].is_file()
    assert paths["status"].is_file()
    # Protected objective heap is untouched.
    assert paths["objective"].read_text(encoding="utf-8") == objective_before

    candidate = paths["candidate"].read_text(encoding="utf-8")
    assert "operator_commit_required: true" in candidate
    for goal_id in ALL_GOAL_IDS:
        assert f"## {goal_id}" in candidate
        # Final states should be verified in the candidate.
        # Status lines appear as "- Status: verified_complete"
    assert candidate.count("verified_complete") >= len(ALL_GOAL_IDS)

    phases = [item["phase"] for item in result["receipts"]]
    assert "phase_1_provisional" in phases
    assert "phase_2_verify_g010_g100" in phases
    assert "phase_3_verify_g110_g000" in phases
    assert "candidate_handoff" in phases

    # Phase one receipt must not verify.
    phase1 = next(item for item in result["receipts"] if item["phase"] == "phase_1_provisional")
    for transition in phase1["goal_transitions"]:
        assert transition["state"] != "verified_complete" or not transition.get("changed")

    # Phase two verifies children only.
    phase2 = next(
        item for item in result["receipts"] if item["phase"] == "phase_2_verify_g010_g100"
    )
    verified_children = set(phase2["details"]["verified_child_goal_ids"])
    assert set(CHILD_GOAL_IDS) <= verified_children
    for transition in phase2["goal_transitions"]:
        assert transition["goal_id"] in CHILD_GOAL_IDS

    # Phase three verifies G110 then G000.
    phase3 = next(
        item for item in result["receipts"] if item["phase"] == "phase_3_verify_g110_g000"
    )
    order = [item["goal_id"] for item in phase3["goal_transitions"] if item.get("changed")]
    if "PTR-G110" in order and "PTR-G000" in order:
        assert order.index("PTR-G110") < order.index("PTR-G000")

    assert result["goal_states"]["PTR-G000"] == "verified_complete"
    assert result["goal_states"]["PTR-G110"] == "verified_complete"
    for goal_id in CHILD_GOAL_IDS:
        assert result["goal_states"][goal_id] == "verified_complete"


def test_phase_one_only_provisional(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(recon_mod, paths)
    goals = recon_mod.parse_objective_goals(paths["objective"].read_text(encoding="utf-8"))
    states = {goal.goal_id: goal.status for goal in goals}
    receipt = reconciler._phase_one_provisional(goals=goals, states=states)
    assert receipt.passed is True
    for goal_id, state in states.items():
        assert state in {
            "provisionally_complete",
            "blocked",
            "verified_complete",
        }
        if state == "verified_complete":
            # Must not have been transitioned by phase one.
            assert not any(
                item["goal_id"] == goal_id and item.get("changed")
                for item in receipt.goal_transitions
            )


# ---------------------------------------------------------------------------
# Bindings, replay, resume, reopen, optional gaps
# ---------------------------------------------------------------------------


def test_every_refresh_recomputes_bindings(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(recon_mod, paths)
    goals = recon_mod.parse_objective_goals(paths["objective"].read_text(encoding="utf-8"))
    states = {goal.goal_id: "provisionally_complete" for goal in goals}
    first = reconciler._recompute_all_bindings(
        goals=goals,
        states=states,
        repository_tree="tree-aaa",
        objective_revision="rev-1",
    )
    second = reconciler._recompute_all_bindings(
        goals=goals,
        states=states,
        repository_tree="tree-aaa",
        objective_revision="rev-1",
    )
    assert first == second
    # Changing inputs must recompute digests.
    third = reconciler._recompute_all_bindings(
        goals=goals,
        states=states,
        repository_tree="tree-bbb",
        objective_revision="rev-1",
    )
    assert third != first
    for goal_id in first:
        assert first[goal_id]["binding_digest"] != third[goal_id]["binding_digest"]


def test_bounded_replay_converges(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(recon_mod, paths)
    result = reconciler.closeout()
    assert result["passed"] is True
    # A second run with clean state also converges (idempotent handoff).
    reconciler2 = _make_reconciler(recon_mod, paths, writer_id="second-writer")
    result2 = reconciler2.closeout()
    assert result2["passed"] is True


def test_interruption_resumes_safely(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    writer_id = "resume-writer"
    reconciler = _make_reconciler(recon_mod, paths, writer_id=writer_id)
    # Seed a checkpoint as if phase one completed.
    goals = recon_mod.parse_objective_goals(paths["objective"].read_text(encoding="utf-8"))
    states = {goal.goal_id: "provisionally_complete" for goal in goals}
    reconciler._save_checkpoint(
        phase=recon_mod.ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
        states=states,
        bindings={},
        fence_revision=0,
    )
    result = reconciler.resume()
    assert result["passed"] is True
    assert result["goal_states"]["PTR-G000"] == "verified_complete"


def test_mutation_reopens_ancestors_and_dependents(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    goals = recon_mod.parse_objective_goals(paths["objective"].read_text(encoding="utf-8"))
    states = {goal.goal_id: "verified_complete" for goal in goals}
    transitions = recon_mod.reopen_affected_goals(
        goals,
        contradicted_goal_ids=["PTR-G100"],
        states=states,
    )
    reopened_ids = {item["goal_id"] for item in transitions if item["changed"]}
    # Direct goal.
    assert "PTR-G100" in reopened_ids
    # Ancestor root.
    assert "PTR-G000" in reopened_ids
    # Dependent final gate depends on G100.
    assert "PTR-G110" in reopened_ids
    assert states["PTR-G100"] == "reopened"
    assert states["PTR-G000"] == "reopened"
    assert states["PTR-G110"] == "reopened"


def test_closeout_applies_contradiction_then_reconverges(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        injected_contradictions=["PTR-G050"],
    )
    result = reconciler.closeout()
    assert result["passed"] is True
    # After reconvergence every goal is verified again.
    for goal_id in ALL_GOAL_IDS:
        assert result["goal_states"][goal_id] == "verified_complete"
    assert "PTR-G050" in result.get("reopened_goal_ids", []) or any(
        "PTR-G050" in str(item) for item in result.get("receipts", [])
    )


def test_missing_optional_services_are_nonterminal_gaps(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        optional_services={
            "groth16": False,
            "provekit": False,
            "snarkjs": False,
            "ipfs": False,
            "shared_cache": False,
        },
    )
    result = reconciler.closeout()
    assert result["passed"] is True
    gaps = result["optional_gaps"]
    assert gaps
    for gap in gaps:
        assert gap["terminal"] is False
        assert gap["blocks_tests"] is False
        assert gap["blocks_supervisor"] is False
        assert gap["action"] == "retain_typed_gap_and_continue_tests"


def test_candidate_requires_explicit_operator_commit(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(recon_mod, paths)
    result = reconciler.closeout()
    assert result["operator_commit_required"] is True
    handoff = result["handoff"]
    assert handoff["operator_commit_required"] is True
    candidate = paths["candidate"].read_text(encoding="utf-8")
    assert "Operator commit required: true" in candidate or (
        "operator_commit_required: true" in candidate
    )
    # Live objective remains active (not operator-committed).
    live = paths["objective"].read_text(encoding="utf-8")
    assert "- Status: active" in live
    assert live.count("verified_complete") == 0


def test_validation_failure_blocks_phase_two(recon_mod: Any, tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    reconciler = _make_reconciler(
        recon_mod,
        paths,
        validation_runner=lambda: {"passed": False, "error": "boom"},
    )
    with pytest.raises(recon_mod.CloseoutRefusal) as exc:
        reconciler.closeout()
    assert exc.value.reason_code in {"validation_failed", "phase2_failed"}


def test_fence_compare_and_swap_conflict(recon_mod: Any, tmp_path: Path) -> None:
    fence_path = tmp_path / "fence.json"
    fence = recon_mod.ObjectiveCloseoutFence(fence_path=fence_path, writer_id="w1")
    fence.acquire()
    try:
        with pytest.raises(recon_mod.ConcurrentWriterError):
            fence.compare_and_swap(expected_revision=999)
        new_rev = fence.compare_and_swap(expected_revision=0)
        assert new_rev == 1
    finally:
        fence.release()


def test_main_closeout_success_exit_code(
    recon_mod: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Report-only on a ready board returns 0 without writing outputs.
    paths_ready = _write_fixture(tmp_path)
    code = recon_mod.main(
        [
            "--repo-root",
            str(paths_ready["repo"]),
            "--objective-path",
            str(paths_ready["objective"]),
            "--todo-path",
            str(paths_ready["todo"]),
            "--gate-path",
            str(paths_ready["gate"]),
            "--evidence-path",
            str(paths_ready["evidence"]),
            "--lifecycle-projection-path",
            str(paths_ready["lifecycle"]),
            "--candidate-objective-path",
            str(paths_ready["candidate"]),
            "--supervisor-health-input-path",
            str(paths_ready["health"]),
            "--status-path",
            str(paths_ready["status"]),
            "--phase-count",
            "3",
            "--report-only",
        ]
    )
    assert code == 0


def test_subprocess_module_entrypoint(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, open_tasks=True)
    env = dict(os.environ)
    env["IPFS_TEST_PROOF_REUSE_MODE"] = "off"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(paths["repo"]),
            "--objective-path",
            str(paths["objective"]),
            "--todo-path",
            str(paths["todo"]),
            "--gate-path",
            str(paths["gate"]),
            "--evidence-path",
            str(paths["evidence"]),
            "--lifecycle-projection-path",
            str(paths["lifecycle"]),
            "--candidate-objective-path",
            str(paths["candidate"]),
            "--supervisor-health-input-path",
            str(paths["health"]),
            "--status-path",
            str(paths["status"]),
            "--phase-count",
            "3",
            "--report-only",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["mode"] == "report_only"
    assert "open_tasks" in payload.get("reason_codes", []) or (payload.get("passed") is False)
