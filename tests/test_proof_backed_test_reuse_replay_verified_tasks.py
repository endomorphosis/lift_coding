"""Unit tests for PTR-167 verified-history replay onto reachable gitlinks."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/proof_backed_test_reuse_replay_verified_tasks.py"


@pytest.fixture(scope="module")
def replay():
    ns = runpy.run_path(str(SCRIPT))
    return ns


def git(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    return subprocess.check_output(("git", *args), cwd=cwd, text=True, env=env).strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    subprocess.run(("git", "init", "-q"), cwd=path, check=True, env=env)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=path, check=True, env=env)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=path, check=True, env=env)
    try:
        git(path, "branch", "-M", "master")
    except subprocess.CalledProcessError:
        pass
    return path


def commit_all(path: Path, message: str) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    # Clones do not inherit identity; set it on every commit path.
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=path, check=True, env=env)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=path, check=True, env=env)
    subprocess.run(("git", "add", "-A"), cwd=path, check=True, env=env)
    subprocess.run(("git", "commit", "-qm", message), cwd=path, check=True, env=env)
    return git(path, "rev-parse", "HEAD")


def make_outer_with_submodules(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Build an outer repo with datasets/kit/accelerate gitlinks."""

    outer = init_repo(tmp_path / "outer")
    pins: dict[str, str] = {}
    for name in ("ipfs_accelerate", "ipfs_datasets", "ipfs_kit"):
        sub = init_repo(tmp_path / "subs" / name)
        pkg = sub / f"{name}_py"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(f"# {name}\n", encoding="utf-8")
        (pkg / "owned.py").write_text(f"value = '{name}'\n", encoding="utf-8")
        # datasets/kit carry bootstrap-like surfaces used by completed tasks
        if name != "ipfs_accelerate":
            (sub / "conftest.py").write_text("# bootstrap\n", encoding="utf-8")
        commit = commit_all(sub, f"initial {name}")
        pins[f"external/{name}"] = commit
        dest = outer / "external" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        # git submodule add via clone from local path
        env = os.environ.copy()
        env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
        env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
        env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
        env.setdefault("GIT_TEMPLATE_DIR", "")
        subprocess.run(
            ("git", "clone", "-q", str(sub), str(dest)),
            check=True,
            env=env,
        )
        subprocess.run(("git", "add", f"external/{name}"), cwd=outer, check=True, env=env)
    # dated immutable historical records
    docs = outer / "implementation_plan" / "docs"
    docs.mkdir(parents=True)
    for rel in (
        "46-proof-backed-test-reuse-integration-pins-2026-08-04.md",
        "46-proof-backed-test-reuse-closeout-summary-2026-08-04.json",
        "46-proof-backed-test-reuse-closeout-report-only-2026-08-04.json",
    ):
        (docs / rel).write_text(f"historical {rel}\n", encoding="utf-8")
    board = docs / "46-proof-backed-test-reuse.todo.md"
    board.write_text(
        "## PTR-161 Bootstrap datasets\n\n"
        "- Status: completed\n"
        "- Outputs: external/ipfs_datasets/conftest.py, external/ipfs_datasets/ipfs_datasets_py/owned.py\n"
        "- Validation: IPFS_TEST_PROOF_REUSE_MODE=off true\n"
        "- Goal id: PTR-G130\n\n"
        "## PTR-162 Bootstrap kit\n\n"
        "- Status: completed\n"
        "- Outputs: external/ipfs_kit/conftest.py, external/ipfs_kit/ipfs_kit_py/owned.py\n"
        "- Validation: IPFS_TEST_PROOF_REUSE_MODE=off true\n"
        "- Goal id: PTR-G130\n\n"
        "## PTR-167 Replay\n\n"
        "- Status: todo\n"
        "- Outputs: scripts/proof_backed_test_reuse_replay_verified_tasks.py\n"
        "- Validation: IPFS_TEST_PROOF_REUSE_MODE=off true\n"
        "- Goal id: PTR-G140\n",
        encoding="utf-8",
    )
    commit_all(outer, "outer with gitlinks")
    return outer, pins


def test_canonical_cid_stable(replay) -> None:
    assert replay["canonical_cid"]({"b": 2, "a": 1}) == replay["canonical_cid"]({"a": 1, "b": 2})
    assert replay["canonical_cid"]({"a": 1}).startswith("b")


def test_plan_schema_and_policy_forbid_synthesis(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    assert plan.schema == "VerifiedTaskReplayPlan@1"
    assert plan.policy["synthesize_history"] is False
    assert plan.policy["synthesize_evidence"] is False
    assert plan.policy["synthesize_completion"] is False
    assert plan.policy["waive_unrecoverable"] is False
    assert plan.plan_cid
    # Sealing is byte-stable.
    again = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    assert again.plan_cid == plan.plan_cid


def test_three_pins_fetchable_and_exact(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    report = reconciler.reconcile(plan, map_path=tmp_path / "map.json")
    for path in replay["GITLINK_PATHS"]:
        pin = report["three_pins"][path]
        assert pin["fetchable"] is True
        assert pin["exact_outer_gitlink"] is True
        assert pin["commit"] == pins[path]


def test_blob_digests_recorded_for_completed_outputs(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    assert plan.blob_mappings
    assert all(item.verified and item.blob_sha256.startswith("sha256:") for item in plan.blob_mappings)
    paths = {item.path for item in plan.blob_mappings}
    assert "external/ipfs_datasets/conftest.py" in paths
    assert "external/ipfs_kit/conftest.py" in paths


def test_unreachable_historical_pin_is_rebased_not_waived(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    # Fabricate a historical pin that does not exist in the object store.
    fake = {
        "external/ipfs_accelerate": pins["external/ipfs_accelerate"],
        "external/ipfs_datasets": "0" * 40,
        "external/ipfs_kit": pins["external/ipfs_kit"],
    }
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=fake,
    )
    datasets = next(m for m in plan.commit_mappings if m.repository == "external/ipfs_datasets")
    assert datasets.old_reachable is False
    assert datasets.new_reachable is True
    assert datasets.disposition == "rebased_to_reachable"
    # Unreachable historical pin alone is not waived as success for old identity.
    assert datasets.old_commit == "0" * 40


def test_blob_digest_mismatch_reopens_owner(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    # Create an alternate historical commit with different content for datasets.
    datasets = outer / "external/ipfs_datasets"
    old = pins["external/ipfs_datasets"]
    (datasets / "conftest.py").write_text("# changed\n", encoding="utf-8")
    new_commit = commit_all(datasets, "mutate conftest")
    # Outer gitlink still names `old` (unchanged index); historical pin is the
    # mutated commit.  Both are reachable; blob digests must disagree.
    fake = dict(pins)
    fake["external/ipfs_datasets"] = new_commit
    git(datasets, "checkout", "-q", old)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=fake,
    )
    reasons = {gap.reason for gap in plan.unrecoverable}
    assert "BLOB_DIGEST_MISMATCH" in reasons
    owners = {gap.task_id for gap in plan.unrecoverable if gap.reason == "BLOB_DIGEST_MISMATCH"}
    assert "PTR-161" in owners


def test_missing_output_reopens_owning_task(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    board = outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
    board.write_text(
        board.read_text(encoding="utf-8")
        + "\n## PTR-999 Missing surface\n\n"
        "- Status: completed\n"
        "- Outputs: external/ipfs_datasets/does_not_exist.py\n"
        "- Validation: IPFS_TEST_PROOF_REUSE_MODE=off true\n"
        "- Goal id: PTR-G140\n",
        encoding="utf-8",
    )
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(todo=board, historical_pins=pins)
    assert any(
        gap.task_id == "PTR-999" and gap.reason == "OUTPUT_BLOB_MISSING_AT_PUBLISHED_COMMIT"
        for gap in plan.unrecoverable
    )


def test_immutable_66_task_records_required(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    target = outer / "implementation_plan/docs/46-proof-backed-test-reuse-integration-pins-2026-08-04.md"
    target.unlink()
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    assert any(gap.reason == "IMMUTABLE_HISTORICAL_RECORD_MISSING" for gap in plan.unrecoverable)


def test_reconcile_writes_static_map_without_approvals(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    map_path = tmp_path / "replay-map-v5.json"
    report = reconciler.reconcile(plan, map_path=map_path)
    assert map_path.is_file()
    loaded = json.loads(map_path.read_text(encoding="utf-8"))
    assert loaded["schema"] == "ipfs_accelerate_py/proof-backed-test-reuse-replay-map@5"
    assert loaded["interface"] == "VerifiedTaskReplayPlan@1"
    assert loaded["immutable_66_task_records"]["mutable"] is False
    assert loaded["map_cid"] == report["map_cid"]
    # Map does not embed operator approvals.
    assert "approvals" not in loaded
    assert plan.policy.get("approvals_required_for_publication") is False
    # Datasets/kit exact pins are always recorded as published confirmations.
    assert loaded["publication"]["datasets_and_kit_published"] is True
    repos = {item["repository"] for item in loaded["publication"]["applied_gitlinks"]}
    assert "external/ipfs_datasets" in repos
    assert "external/ipfs_kit" in repos
    assert all(
        item["action"].startswith("confirm_exact")
        for item in loaded["publication"]["applied_gitlinks"]
    )


def test_trusted_receipts_observed_not_synthesized(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    state = tmp_path / "proof-backed-test-reuse-v9"
    completed = state / "merge-queue" / "completed"
    train = state / "merge-queue" / "train" / "receipts"
    completed.mkdir(parents=True)
    train.mkdir(parents=True)
    commit = pins["external/ipfs_datasets"]
    request, dedupe = "req-161", "dedupe-161"
    queue = {
        "task_id": "PTR-161",
        "request_id": request,
        "dedupe_key": dedupe,
        "status": "completed",
        "canonical_task_id": "task/v1/fixture-161",
    }
    train_body = {
        "request_id": request,
        "task_id": "PTR-161",
        "status": "merged",
        "integrated": True,
        "merge_result": {
            "returncode": 0,
            "integration_commit_proof": {"passed": True, "integration_commit": commit},
        },
    }
    (completed / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    (train / f"{dedupe}.json").write_text(json.dumps(train_body), encoding="utf-8")
    # Untrusted lookalike outside completed/train must not authorize.
    (state / "forged.json").write_text(
        json.dumps({"task_id": "PTR-161", "git_commit_id": commit, "merge_receipt_cid": "x"}),
        encoding="utf-8",
    )
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        state_root=state,
        historical_pins=pins,
    )
    assert len(plan.receipts_observed) == 1
    assert plan.receipts_observed[0]["task_id"] == "PTR-161"
    assert plan.receipts_observed[0]["schema"] == "CompletedTaskArtifactReceipt@1"


def test_apply_gitlinks_stages_exact_pins(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    reconciler = replay["ReachableGitlinkReconciler"](outer)
    plan = reconciler.build_plan(
        todo=outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        historical_pins=pins,
    )
    report = reconciler.reconcile(
        plan, apply_gitlinks=True, map_path=tmp_path / "map.json",
    )
    applied = {item["repository"] for item in report["publication"]["applied_gitlinks"]}
    assert "external/ipfs_datasets" in applied
    assert "external/ipfs_kit" in applied


def test_main_writes_map_and_requires_three_pins(replay, tmp_path: Path) -> None:
    outer, pins = make_outer_with_submodules(tmp_path)
    map_path = tmp_path / "out.json"
    code = replay["main"](
        [
            "--repo-root",
            str(outer),
            "--todo",
            str(outer / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"),
            "--map-path",
            str(map_path),
            "--json",
        ]
    )
    # main uses HISTORICAL_66_PINS by default which won't match fixture pins'
    # "old" side, but current pins are fetchable/exact so exit 0.
    assert code == 0
    assert map_path.is_file()
    body = json.loads(map_path.read_text(encoding="utf-8"))
    assert body["schema"] == "ipfs_accelerate_py/proof-backed-test-reuse-replay-map@5"


def test_completed_task_artifact_receipt_schema_guard(replay) -> None:
    with pytest.raises(ValueError):
        replay["CompletedTaskArtifactReceipt"](
            schema="wrong",
            task_id="PTR-1",
            commit="a" * 40,
            receipt_cid="x",
            source="y",
        )
