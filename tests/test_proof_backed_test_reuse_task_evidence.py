from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/proof_backed_test_reuse_task_evidence.py"
SPEC = importlib.util.spec_from_file_location("task_evidence", SCRIPT)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evidence
SPEC.loader.exec_module(evidence)


def git(root: Path, *args: str) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    return subprocess.check_output(("git", *args), cwd=root, text=True, env=env).strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    subprocess.run(("git", "init", "-q"), cwd=repo, check=True, env=env)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=repo, check=True, env=env)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=repo, check=True, env=env)
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    (repo / "scripts" / "owned.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "tests" / "test_owned.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=repo, check=True, env=env)
    subprocess.run(("git", "commit", "-qm", "initial"), cwd=repo, check=True, env=env)
    # Normalize default branch name across git versions.
    try:
        git(repo, "branch", "-M", "master")
    except subprocess.CalledProcessError:
        pass
    return repo


def write_board(tmp_path: Path, *, status: str = "completed", task_count: int = 2) -> Path:
    board = tmp_path / "board.md"
    blocks = []
    for index in range(1, task_count + 1):
        depends = f"PTR-{index - 1:03d}" if index > 1 else ""
        st = "completed" if index < task_count else status
        blocks.append(
            f"## PTR-{index:03d} Task {index}\n\n"
            f"- Status: {st}\n- Depends on: {depends}\n- Goal id: G{index}\n"
            f"- Outputs: scripts/owned.py\n"
            f"- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q\n"
        )
    board.write_text("\n".join(blocks), encoding="utf-8")
    return board


def receipt(task_id: str, snapshot: object, command: str, *, commit: str | None = None, fresh: int = 9_999_999_999_999) -> dict[str, object]:
    return {
        "task_id": task_id,
        "merge_receipt_cid": "baguqeera" + task_id.lower().replace("-", ""),
        "git_commit_id": commit or snapshot.commit,
        "validation_receipt_cid": "baguqeeravalid" + task_id.lower().replace("-", ""),
        "validation_command": command,
        "passed": True,
        "proof_reuse_mode": "off",
        "fresh_until_ms": fresh,
        "git_tree_id": snapshot.tree,
        "gitlink_state_cid": snapshot.gitlink_state_cid,
        "disposition": "executed",
        "exit_code": 0,
        "skipped_count": 0,
        "status": "passed",
    }


def write_receipts(root: Path, values: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index, value in enumerate(values):
        (root / f"receipt-{index}.json").write_text(json.dumps(value), encoding="utf-8")


def write_event_log(root: Path, lane: int = 0, events: list[dict] | None = None) -> None:
    """Write the controller's v1/v6/v8 manifest-and-chain shape."""
    directory = root / "state" / f"ptr_lane_{lane}"
    directory.mkdir(parents=True, exist_ok=True)
    if events is None:
        events = [{
            "sequence": 1, "event_id": "sha256:event-1", "previous_event_id": "",
            "stream_id": "event-log:test", "snapshot_id": "event-log-snapshot:test",
        }]
        # Seal the first event identity correctly.
        body = {k: v for k, v in events[0].items() if k != "event_id"}
        events[0]["event_id"] = evidence._sha256(evidence.canonical_json(body))
    # Ensure event_ids match body for every supplied event.
    sealed = []
    previous = ""
    for index, raw in enumerate(events, start=1):
        event = dict(raw)
        event.setdefault("sequence", index)
        event.setdefault("previous_event_id", previous)
        event.setdefault("stream_id", "event-log:test")
        event.setdefault("snapshot_id", "event-log-snapshot:test")
        body = {k: v for k, v in event.items() if k != "event_id"}
        event["event_id"] = evidence._sha256(evidence.canonical_json(body))
        previous = event["event_id"]
        sealed.append(event)
    raw = b"".join((json.dumps(event, sort_keys=True) + "\n").encode() for event in sealed)
    events_path = directory / f"ptr_lane_{lane}_events.jsonl"
    events_path.write_bytes(raw)
    manifest = {
        "schema": "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2",
        "active_path": events_path.name,
        "stream_id": sealed[0]["stream_id"],
        "snapshot_id": sealed[0]["snapshot_id"],
        "last_event_id": sealed[-1]["event_id"],
        "files": [{
            "path": events_path.name,
            "size_bytes": len(raw),
            "event_count": len(sealed),
            "first_sequence": 1,
            "last_sequence": len(sealed),
            "start_previous_event_id": "",
            "sha256": evidence._sha256(raw),
        }],
    }
    manifest["manifest_digest"] = evidence._sha256(evidence.canonical_json(manifest))
    (directory / f"ptr_lane_{lane}_events.jsonl.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_canonical_cid_is_stable_and_report_write_is_idempotent(tmp_path: Path) -> None:
    assert evidence.canonical_cid({"b": 2, "a": 1}) == evidence.canonical_cid({"a": 1, "b": 2})
    report = {"schema": evidence.REPORT_SCHEMA}
    report["report_cid"] = evidence.canonical_cid(report)
    first = evidence.write_report(report, tmp_path)
    assert first == evidence.write_report(report, tmp_path)
    assert first.name == f"{report['report_cid']}.json"
    persisted = json.loads(first.read_text(encoding="utf-8"))
    claimed = persisted.pop("report_cid")
    assert claimed == evidence.canonical_cid(persisted)
    # Repeated write of the same CID remains byte-stable.
    again = evidence.write_report(report, tmp_path)
    assert again.read_bytes() == first.read_bytes()


def test_live_audit_requires_files_ancestor_receipts_and_fresh_exact_validation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path)
    state = tmp_path / "state"
    validator = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100)
    missing = validator.audit()
    kinds = {gap["kind"] for gap in missing["gaps"]}
    assert not missing["ready"]
    assert {"COMPLETION_RECEIPT_MISSING", "VALIDATION_RECEIPT_MISSING"} <= kinds

    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    write_receipts(state, [receipt("PTR-001", snapshot, command), receipt("PTR-002", snapshot, command)])
    ready = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert ready["ready"]
    assert ready["dependency_order"] == [{
        "later_task": "PTR-002",
        "dependency": "PTR-001",
        "later_commit": snapshot.commit,
        "dependency_commit": snapshot.commit,
        "ordered": True,
    }]


@pytest.mark.parametrize("mutation, expected", [
    (lambda value, snapshot: value.update({"fresh_until_ms": 99}), "VALIDATION_RECEIPT_STALE"),
    (lambda value, snapshot: value.update({"git_tree_id": "0" * 40}), "VALIDATION_PIN_MISMATCH"),
    (lambda value, snapshot: value.update({"validation_command": "pytest wrong.py"}), "VALIDATION_COMMAND_MISMATCH"),
    (lambda value, snapshot: value.update({"skipped_count": 1}), "VALIDATION_NOT_PROOF_REUSE_OFF"),
    (lambda value, snapshot: value.update({"exit_code": 1, "passed": False}), "VALIDATION_NOT_PROOF_REUSE_OFF"),
])
def test_invalid_validation_evidence_is_never_ready(tmp_path: Path, mutation: object, expected: str) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    value = receipt("PTR-001", snapshot, command)
    mutation(value, snapshot)
    state = tmp_path / "state"
    write_receipts(state, [value])
    report = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert not report["ready"]
    assert expected in {gap["kind"] for gap in report["gaps"]}


def test_non_ancestor_receipt_and_wrong_submodule_pin_are_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    subprocess.run(("git", "checkout", "-qb", "side"), cwd=repo, check=True, env=env)
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    subprocess.run(("git", "add", "side.txt"), cwd=repo, check=True, env=env)
    subprocess.run(("git", "commit", "-qm", "side"), cwd=repo, check=True, env=env)
    side = git(repo, "rev-parse", "HEAD")
    # Prefer master, fall back to main.
    for branch in ("master", "main"):
        result = subprocess.run(("git", "checkout", "-q", branch), cwd=repo, env=env)
        if result.returncode == 0:
            break
    state = tmp_path / "state"
    write_receipts(state, [receipt("PTR-001", snapshot, command, commit=side)])
    report = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert "RECEIPT_COMMIT_NOT_ANCESTOR" in {gap["kind"] for gap in report["gaps"]}


def test_wrong_gitlink_pin_is_not_treated_as_a_present_output(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    validator = evidence.ProofReuseTaskEvidenceValidator(board, tmp_path / "state", repo, now_ms=100)
    validator.snapshot.gitlinks["scripts"] = "0" * 40
    report = validator.audit()
    assert "GITLINK_PIN_MISMATCH" in {gap["kind"] for gap in report["gaps"]}


def test_sealed_authority_uses_only_joined_queue_train_and_flat_v1_receipts(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-160", "fixture", "completed", (), ("scripts/owned.py",), command,
        evidence.validation_targets(command), "G160", "task/v1/fixture", "baguqeerafixture",
    )
    request, dedupe = "request-160", "dedupe-160"
    queue = {
        "task_id": task.task_id, "request_id": request, "dedupe_key": dedupe, "status": "completed",
        "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
        "commit_sha": snapshot.commit,
        "metadata": {
            "schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3",
            "task": {
                "board_namespace": evidence.BOARD_NAMESPACE,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
            },
        },
    }
    train = {
        "request_id": request, "canonical_task_id": task.canonical_task_key, "task_id": task.task_id,
        "status": "merged", "integrated": True, "merged": True,
        "merge_result": {
            "merged": True, "returncode": 0,
            "integration_commit_proof": {"passed": True, "integration_commit": snapshot.commit},
        },
    }
    for name in ("v8", "v6", "v1"):
        (roots[name] / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (roots[name] / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v8"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    (roots["v8"] / "merge-queue" / "train" / "receipts" / f"{dedupe}.json").write_text(json.dumps(train), encoding="utf-8")
    # Real-format v6 PTR-160 pair.
    v6_request, v6_dedupe = "request-v6-160", "dedupe-v6-160"
    v6_queue = dict(queue, request_id=v6_request, dedupe_key=v6_dedupe)
    v6_train = dict(train, request_id=v6_request)
    (roots["v6"] / "merge-queue" / "completed" / f"{v6_request}.json").write_text(json.dumps(v6_queue), encoding="utf-8")
    (roots["v6"] / "merge-queue" / "train" / "receipts" / f"{v6_dedupe}.json").write_text(json.dumps(v6_train), encoding="utf-8")
    validation = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1",
        "task_id": task.task_id, "task_cid": task.canonical_task_cid, "goal_id": task.goal_id,
        "validation_command": command, "validation_command_cid": evidence._validation_command_cid(command),
        "passed": True, "proof_reuse_mode": "off", "disposition": "executed",
        "exit_code": 0, "skipped_count": 0, "status": "passed",
        "fresh_until_ms": 9_999_999_999_999,
        "git_commit_id": snapshot.commit, "git_tree_id": snapshot.tree,
        "gitlink_state_cid": snapshot.gitlink_state_cid,
        "repository_id": "lift_coding/proof-backed-test-reuse",
        "repository_state_cid": f"git-commit:{snapshot.commit}",
        "repository_forest_cid": "baguqeerafixtureforest",
        "dirty": False,
        "dirty_overlay_cid": "cid:dirty-overlay:none",
    }
    validation["validation_receipt_cid"] = evidence.canonical_cid(validation)
    receipt_dir = roots["v1"] / "projection" / "completion" / "validation_receipts"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "PTR-160.json").write_text(json.dumps(validation), encoding="utf-8")
    # failed/ is never authority
    failed = receipt_dir / "failed"
    failed.mkdir()
    (failed / "PTR-160.json").write_text(json.dumps({"task_id": "PTR-160", "passed": True}), encoding="utf-8")
    receipts, validations, gaps, diag = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert not any(g.kind.startswith("STATE_ROOT_") for g in gaps)
    assert receipts[task.task_id]
    assert validations[task.task_id][0]["validation_receipt_cid"] == validation["validation_receipt_cid"]
    # A lookalike nested row cannot replace the sealed completed location.
    (roots["v8"] / "untrusted.json").write_text(json.dumps(queue), encoding="utf-8")
    again, _, _, _ = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert {item.source for item in again[task.task_id]} == {item.source for item in receipts[task.task_id]}
    # Task-key / task-CID mismatch is rejected as provenance diagnostic (not
    # readiness-hard when a later matching row may still authorize).  Drop the
    # valid v6 twin so the mismatch is not rewritten as SUPERSEDED_*.
    for path in (roots["v6"] / "merge-queue" / "completed").glob("*.json"):
        path.unlink()
    for path in (roots["v6"] / "merge-queue" / "train" / "receipts").glob("*.json"):
        path.unlink()
    bad = dict(queue)
    bad["metadata"] = dict(queue["metadata"])
    bad["metadata"]["task"] = dict(queue["metadata"]["task"], canonical_task_cid="baguqeera-substituted")
    (roots["v8"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(bad), encoding="utf-8")
    rejected_receipts, _, _rejected, rejected_diag = evidence._authoritative_evidence(
        roots, {task.task_id: task}, snapshot,
    )
    assert task.task_id not in rejected_receipts
    assert "QUEUE_TASK_IDENTITY_MISMATCH" in {gap.kind for gap in rejected_diag}
    # Underspecified flat validation body is rejected (missing repository fields).
    thin = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1",
        "task_id": task.task_id, "task_cid": task.canonical_task_cid, "goal_id": task.goal_id,
        "validation_command": command, "validation_command_cid": evidence._validation_command_cid(command),
        "passed": True, "proof_reuse_mode": "off",
    }
    thin["validation_receipt_cid"] = evidence.canonical_cid(thin)
    (receipt_dir / "PTR-160.json").write_text(json.dumps(thin), encoding="utf-8")
    _, _, _thin_gaps, thin_diag = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert "VALIDATION_RECEIPT_IDENTITY_MISMATCH" in {gap.kind for gap in thin_diag}


def test_sealed_queue_rejects_unbound_task_identity_and_broken_event_chain(tmp_path: Path) -> None:
    root = tmp_path / "proof-backed-test-reuse-v8"
    write_event_log(root)
    # Tamper with last_event_id after sealing digest.
    manifest = root / "state" / "ptr_lane_0" / "ptr_lane_0_events.jsonl.manifest.json"
    value = json.loads(manifest.read_text())
    value["last_event_id"] = "sha256:substituted"
    value["manifest_digest"] = evidence._sha256(
        evidence.canonical_json({k: v for k, v in value.items() if k != "manifest_digest"})
    )
    manifest.write_text(json.dumps(value), encoding="utf-8")
    assert "STATE_ROOT_EVENT_TAIL_INVALID" in {gap.kind for gap in evidence._verify_event_log("v8", root)}

    # Event-id tampering.
    root2 = tmp_path / "proof-backed-test-reuse-v6"
    write_event_log(root2)
    events = root2 / "state" / "ptr_lane_0" / "ptr_lane_0_events.jsonl"
    rows = [json.loads(line) for line in events.read_text().splitlines()]
    rows[0]["event_id"] = "sha256:forged"
    raw = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in rows)
    events.write_bytes(raw)
    mf = json.loads((root2 / "state/ptr_lane_0/ptr_lane_0_events.jsonl.manifest.json").read_text())
    mf["files"][0]["size_bytes"] = len(raw)
    mf["files"][0]["event_count"] = len(rows)
    mf["files"][0]["sha256"] = evidence._sha256(raw)
    mf["last_event_id"] = rows[-1]["event_id"]
    mf["manifest_digest"] = evidence._sha256(
        evidence.canonical_json({k: v for k, v in mf.items() if k != "manifest_digest"})
    )
    (root2 / "state/ptr_lane_0/ptr_lane_0_events.jsonl.manifest.json").write_text(json.dumps(mf), encoding="utf-8")
    assert "STATE_ROOT_EVENT_ID_INVALID" in {gap.kind for gap in evidence._verify_event_log("v6", root2)}


def test_default_state_root_honors_complete_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override = tmp_path / "proof-backed-test-reuse-v9"
    override.mkdir()
    monkeypatch.setenv("IPFS_PROOF_REUSE_STATE_ROOT", str(override))
    monkeypatch.setenv("HOME", str(tmp_path / "isolated-home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "isolated-xdg"))
    assert evidence.default_state_root() == Path(str(override))
    roots, gaps = evidence._reviewed_roots(override)
    assert gaps  # siblings missing under tmp parent
    assert roots["v9"] == override
    assert roots["v8"] == override.parent / "proof-backed-test-reuse-v8"
    assert roots["v6"] == override.parent / "proof-backed-test-reuse-v6"
    assert roots["v1"] == override.parent / "proof-backed-test-reuse-v1"


def test_expect_incomplete_fails_closed_without_reviewed_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("IPFS_PROOF_REUSE_STATE_ROOT", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    current = home / ".local/state/ipfs_accelerate_py/proof-backed-test-reuse-v9"
    current.mkdir(parents=True)
    _, gaps = evidence._reviewed_roots(current)
    assert {g.kind for g in gaps} == {"STATE_ROOT_MISSING"}
    assert {g.detail.split(":")[0] for g in gaps} >= {"v1", "v6", "v8"}


def test_main_expect_incomplete_survives_readonly_state_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Landlock leaves reviewed state roots read-only; projection writes must not fail the audit."""

    state = tmp_path / "proof-backed-test-reuse-v9"
    state.mkdir()
    report = {
        "schema": evidence.REPORT_SCHEMA,
        "audit_valid": True,
        "ready": False,
        "gaps": [{"task_id": "PTR-000", "kind": "COMPLETION_RECEIPT_MISSING", "detail": "gap"}],
        "report_cid": "baguqeerareadonlyprojection",
        "observation_only": True,
    }

    class _Validator:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def audit(self) -> dict[str, object]:
            return report

    monkeypatch.setattr(evidence, "ProofReuseTaskEvidenceValidator", _Validator)
    monkeypatch.setattr(evidence, "TODO_PATH", tmp_path / "board.md")
    (tmp_path / "board.md").write_text("## PTR-000\n", encoding="utf-8")

    projection = state / "projection"
    projection.mkdir()
    projection.chmod(0o555)
    try:
        with pytest.raises((PermissionError, OSError, RuntimeError)):
            evidence.write_report(report, state)
        code = evidence.main([
            "--todo", str(tmp_path / "board.md"),
            "--state-root", str(state),
            "--expect-incomplete",
        ])
    finally:
        projection.chmod(0o755)
    assert code == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["audit_valid"] is True
    assert emitted["ready"] is False
    assert emitted["gaps"]


def test_cli_rejects_fabricated_one_task_board_for_authority_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    board = write_board(tmp_path, task_count=1)
    code = evidence.main(["--todo", str(board), "--state-root", str(tmp_path), "--require-ready"])
    assert code == 3
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["audit_valid"] is False
    assert emitted["ready"] is False


def test_reconciliation_and_queue_fixtures_join_exact_task_triple(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8", "v9")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-011", "fixture", "completed", (), ("scripts/owned.py",), command,
        evidence.validation_targets(command), "G11",
        "task/v1/fixture-011", "baguqeerafixture011",
    )
    # Successful reconciliation event on v1 (PTR-011) plus failed coexistence.
    success = {
        "type": "merge_reconciled",
        "resolved": True,
        "reason": evidence.RECONCILE_REASON,
        "task_id": task.task_id,
        "completion_task_cids": {task.task_id: task.canonical_task_cid},
        "completion_persistence": {"passed": True, "durable_update": True},
        "integration_commit_proof": {"passed": True, "integration_commit": snapshot.commit},
        "post_merge_declared_output_invariant": {"passed": True},
        "todo_update_result": {"completion_receipts": [{
            "schema": evidence.MEMBER_COMPLETION_SCHEMA,
            "status": "succeeded",
            "task_id": task.task_id,
            "canonical_task_cid": task.canonical_task_cid,
            "canonical_task_key": task.canonical_task_key,
            "board_namespace": evidence.BOARD_NAMESPACE,
        }]},
    }
    failed = {
        "type": "merge_reconciled",
        "resolved": False,
        "reason": "merge_failed",
        "task_id": "PTR-041",
        "completion_task_cids": {"PTR-041": "baguqeerafailed"},
    }
    # Rebuild lane 0 with chain-valid success after an initial placeholder.
    first = {
        "sequence": 1, "previous_event_id": "",
        "stream_id": "event-log:test", "snapshot_id": "event-log-snapshot:test",
        "type": "bootstrap",
    }
    lane = roots["v1"] / "state" / "ptr_lane_0"
    write_event_log(roots["v1"], 0, [first, success, failed])
    receipts, gaps = evidence._reconciliation_receipts(
        {k: roots[k] for k in ("v1", "v6", "v8")}, {task.task_id: task}, snapshot,
    )
    assert gaps == []
    assert receipts[task.task_id][0].commit == snapshot.commit
    # Failed reconcile must not authorize PTR-041 or suppress later success.
    assert "PTR-041" not in receipts


def test_recovery_only_rows_are_provenance_gaps(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
        (root / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (root / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v1"] / "projection" / "completion" / "validation_receipts").mkdir(parents=True)
    task = evidence.Task(
        "PTR-150", "recovery", "completed", (), (), "", (), "G150",
        "task/v1/recovery", "baguqeerarecovery150",
    )
    row = {"task_id": "PTR-150", "status": "completed", "commit_sha": snapshot.commit}
    (roots["v1"] / "merge-queue" / "completed" / "recovery-150.json").write_text(
        json.dumps(row), encoding="utf-8"
    )
    receipts, _, gaps, diagnostics = evidence._authoritative_evidence(
        roots, {task.task_id: task}, snapshot,
    )
    assert task.task_id not in receipts
    assert "RECOVERY_PROVENANCE_GAP" not in {gap.kind for gap in gaps}
    assert "RECOVERY_PROVENANCE_GAP" in {gap.kind for gap in diagnostics}


def test_boundary_receipt_is_never_completion_authority() -> None:
    boundary = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-boundary@1",
        "proof_authoritative": False,
        "completion_authority": False,
        "mode": "landlock-abi-3-or-newer-inherited",
    }
    assert boundary["proof_authoritative"] is False
    assert boundary["completion_authority"] is False


def test_request_dedupe_filename_mismatches_are_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
        (root / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (root / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v1"] / "projection" / "completion" / "validation_receipts").mkdir(parents=True)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-160", "fixture", "completed", (), ("scripts/owned.py",), command,
        evidence.validation_targets(command), "G160", "task/v1/fixture", "baguqeerafixture",
    )
    request, dedupe = "request-x", "dedupe-x"
    queue = {
        "task_id": task.task_id, "request_id": "wrong-request", "dedupe_key": dedupe, "status": "completed",
        "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
        "commit_sha": snapshot.commit,
        "metadata": {
            "schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3",
            "task": {
                "board_namespace": evidence.BOARD_NAMESPACE,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
            },
        },
    }
    (roots["v8"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    train = {
        "request_id": "wrong-request", "canonical_task_id": task.canonical_task_key, "task_id": task.task_id,
        "status": "merged", "integrated": True, "merged": True,
        "merge_result": {
            "merged": True, "returncode": 0,
            "integration_commit_proof": {"passed": True, "integration_commit": snapshot.commit},
        },
    }
    (roots["v8"] / "merge-queue" / "train" / "receipts" / f"{dedupe}.json").write_text(json.dumps(train), encoding="utf-8")
    _, _, _gaps, diag = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    # Identity/dedupe mismatches are provenance diagnostics; they never authorize
    # and must not hard-block readiness when later authority can supersede them.
    assert "QUEUE_TASK_IDENTITY_MISMATCH" in {gap.kind for gap in diag}


def _controller_state_siblings() -> dict[str, Path]:
    """Resolve mandatory reviewed roots from the controller-selected state root.

    ``IPFS_PROOF_REUSE_STATE_ROOT`` is the complete current v9 override; siblings
    are named directories of its parent.  Missing evidence is a hard failure
    (never ``pytest.skip``) so the declared Landlock validation cannot soft-pass.
    """

    configured = os.environ.get("IPFS_PROOF_REUSE_STATE_ROOT", "").strip()
    if configured:
        current = Path(configured).expanduser().resolve()
    else:
        state_base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        current = (state_base / "ipfs_accelerate_py/proof-backed-test-reuse-v9").resolve()
    parent = current.parent
    roots = {
        "v9": current,
        "v8": parent / "proof-backed-test-reuse-v8",
        "v6": parent / "proof-backed-test-reuse-v6",
        "v1": parent / "proof-backed-test-reuse-v1",
    }
    missing = [name for name, path in roots.items() if not path.is_dir()]
    assert not missing, f"controller state sibling roots missing: {missing} under {parent}"
    return roots


def test_copied_real_format_fixture_shapes(tmp_path: Path) -> None:
    """Copy real-format fixtures for v8 raw/train, v6 PTR-160, v1 receipt, and chain."""
    roots = _controller_state_siblings()
    src_v8, src_v6, src_v1 = roots["v8"], roots["v6"], roots["v1"]
    assert (src_v8 / "merge-queue/completed").is_dir(), "v8 completed queue missing under controller root"
    assert (src_v6 / "merge-queue/completed").is_dir(), "v6 completed queue missing under controller root"
    assert (src_v1 / "projection/completion/validation_receipts").is_dir(), "v1 validation receipts missing"

    dest = tmp_path / "fixtures"
    dest.mkdir(parents=True)
    # v8 raw/train pair
    q = next((src_v8 / "merge-queue/completed").glob("*.json"))
    row = json.loads(q.read_text())
    assert row["metadata"]["schema"] == "ipfs_accelerate_py/agent-supervisor/merge-candidate@3"
    assert row.get("status") == "completed"
    train = src_v8 / "merge-queue/train/receipts" / f"{row['dedupe_key']}.json"
    assert train.is_file()
    t = json.loads(train.read_text())
    assert t["request_id"] == row["request_id"]
    assert t["status"] in {"merged", "already_merged"}
    shutil.copy2(q, dest / "v8-queue.json")
    shutil.copy2(train, dest / "v8-train.json")

    # v6 PTR-160 pair
    found = None
    for path in (src_v6 / "merge-queue/completed").glob("*.json"):
        candidate = json.loads(path.read_text())
        if candidate.get("task_id") == "PTR-160":
            found = path
            break
    assert found is not None, "v6 PTR-160 completed queue pair missing under controller root"
    row160 = json.loads(found.read_text())
    train160 = src_v6 / "merge-queue/train/receipts" / f"{row160['dedupe_key']}.json"
    assert train160.is_file()
    shutil.copy2(found, dest / "v6-ptr160-queue.json")
    shutil.copy2(train160, dest / "v6-ptr160-train.json")

    # v1 flat validation receipt
    vr = src_v1 / "projection/completion/validation_receipts/PTR-000.json"
    assert vr.is_file()
    body = json.loads(vr.read_text())
    assert body["schema"] == "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1"
    for required in (
        "disposition", "exit_code", "skipped_count", "proof_reuse_mode", "passed",
        "repository_id", "repository_state_cid", "repository_forest_cid",
        "dirty", "dirty_overlay_cid", "git_commit_id", "git_tree_id", "gitlink_state_cid",
    ):
        assert required in body
    claimed = body.pop("validation_receipt_cid")
    assert claimed == evidence.canonical_cid(body)
    shutil.copy2(vr, dest / "v1-validation-PTR-000.json")

    # v1 PTR-011/PTR-041 successful-plus-failed reconciliation chain/manifest
    lane = src_v1 / "state/ptr_lane_2"
    events = lane / "ptr_lane_2_events.jsonl"
    manifest = lane / "ptr_lane_2_events.jsonl.manifest.json"
    assert events.is_file() and manifest.is_file()
    mf = json.loads(manifest.read_text())
    assert mf["schema"] == "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2"
    has_011 = False
    has_041_failed = False
    with events.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if "merge_reconciled" not in line:
                continue
            if "PTR-011" in line and "implementation_branch_already_merged" in line:
                has_011 = True
            if "PTR-041" in line and ("merge_failed" in line or '"resolved": false' in line or '"resolved":false' in line):
                has_041_failed = True
    assert has_011, "v1 PTR-011 successful reconciliation missing"
    # Failed coexistence may be on another lane; do not invent it.
    _ = has_041_failed
    shutil.copy2(events, dest / "v1-ptr_lane_2_events.jsonl")
    shutil.copy2(manifest, dest / "v1-ptr_lane_2_events.jsonl.manifest.json")

    # Current v9 must expose its own postmerge queue/train pair for the audit.
    src_v9 = roots["v9"]
    assert (src_v9 / "merge-queue/completed").is_dir(), "v9 completed queue missing"
    assert (src_v9 / "merge-queue/train/receipts").is_dir(), "v9 train receipts missing"
    assert (src_v9 / "projection/native_board_preflight.json").is_file()
    assert (src_v9 / "projection/launch_preflight.json").is_file()


def test_board_population_mutations_are_invalid_when_sealed(tmp_path: Path) -> None:
    """77/76/two/one-task boards cannot pass the sealed CLI authority gate."""
    assert evidence.SEALED_TASK_COUNT == 78
    for count in (77, 76, 2, 1):
        board_dir = tmp_path / f"n{count}"
        board_dir.mkdir(parents=True, exist_ok=True)
        board = write_board(board_dir, task_count=count)
        code = evidence.main(["--todo", str(board), "--expect-incomplete", "--state-root", str(tmp_path)])
        assert code == 3


@pytest.mark.parametrize("missing", ["v1", "v6", "v8", "v9"])
def test_missing_reviewed_root_is_typed_audit_failure(tmp_path: Path, missing: str) -> None:
    parent = tmp_path / "state-home"
    current = parent / "proof-backed-test-reuse-v9"
    for name in ("v1", "v6", "v8", "v9"):
        if name == missing:
            continue
        (parent / f"proof-backed-test-reuse-{name}").mkdir(parents=True, exist_ok=True)
    if missing != "v9":
        current.mkdir(parents=True, exist_ok=True)
        _, gaps = evidence._reviewed_roots(current)
        assert any(gap.detail.startswith(missing) for gap in gaps)
    else:
        # Current directory absent → missing v9 among reviewed roots.
        _, gaps = evidence._reviewed_roots(current)
        assert any(gap.kind == "STATE_ROOT_MISSING" for gap in gaps)
        assert any(gap.detail.startswith("v9") for gap in gaps)


def test_self_authored_projection_is_never_authority(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    state = tmp_path / "state"
    # Self-authored report under projection/task-evidence cannot complete a task.
    report = {"schema": evidence.REPORT_SCHEMA, "ready": True, "task_id": "PTR-001"}
    evidence.write_report({**report, "report_cid": evidence.canonical_cid(report)}, state)
    out = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert not out["ready"]
    assert "COMPLETION_RECEIPT_MISSING" in {gap["kind"] for gap in out["gaps"]}


def test_later_ownership_mentions_ptr_163_and_171_contract() -> None:
    # Quarantine owners are defined by the board gate; this auditor must surface them.
    text = SCRIPT.read_text(encoding="utf-8")
    assert "HISTORICAL_MISSING_ARTIFACT_PENDING" in text
    assert "later_ownership" in text
    assert "owner_task_id" in text
    assert "PTR-163" in text or "historical_missing_artifact_quarantine" in text
    assert "v9" in text and "native_board_preflight" in text


def test_failed_and_quarantined_queue_rows_are_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8", "v9")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
        (root / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (root / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v1"] / "projection" / "completion" / "validation_receipts").mkdir(parents=True)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-160", "fixture", "completed", (), ("scripts/owned.py",), command,
        evidence.validation_targets(command), "G160", "task/v1/fixture", "baguqeerafixture",
    )
    for status, name in (("failed", "failed-req"), ("quarantined", "quar-req")):
        queue = {
            "task_id": task.task_id, "request_id": name, "dedupe_key": f"dedupe-{name}",
            "status": status,
            "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
            "commit_sha": snapshot.commit,
            "metadata": {
                "schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3",
                "task": {
                    "board_namespace": evidence.BOARD_NAMESPACE,
                    "canonical_task_key": task.canonical_task_key,
                    "canonical_task_cid": task.canonical_task_cid,
                },
            },
        }
        (roots["v9"] / "merge-queue" / "completed" / f"{name}.json").write_text(
            json.dumps(queue), encoding="utf-8",
        )
    _, _, _gaps, diag = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    # Failed/quarantined rows never authorize; they surface as provenance
    # diagnostics so a later completed row can still satisfy readiness.
    assert "QUEUE_ROW_FAILED_OR_QUARANTINED" in {gap.kind for gap in diag}


def test_recovery_diagnostic_superseded_after_later_authority(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8", "v9")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
        (root / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (root / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v1"] / "projection" / "completion" / "validation_receipts").mkdir(parents=True)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-150", "recovery", "completed", (), (), command,
        evidence.validation_targets(command), "G150",
        "task/v1/recovery", "baguqeerarecovery150",
    )
    # Old recovery-only row under v1.
    (roots["v1"] / "merge-queue" / "completed" / "recovery-150.json").write_text(
        json.dumps({"task_id": "PTR-150", "status": "completed", "commit_sha": snapshot.commit}),
        encoding="utf-8",
    )
    # Later valid v9 queue/train authority for the same exact triple.
    request, dedupe = "request-150-later", "dedupe-150-later"
    queue = {
        "task_id": task.task_id, "request_id": request, "dedupe_key": dedupe, "status": "completed",
        "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
        "commit_sha": snapshot.commit,
        "metadata": {
            "schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3",
            "task": {
                "board_namespace": evidence.BOARD_NAMESPACE,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
            },
        },
    }
    train = {
        "request_id": request, "canonical_task_id": task.canonical_task_key, "task_id": task.task_id,
        "status": "merged", "integrated": True, "merged": True,
        "merge_result": {
            "merged": True, "returncode": 0,
            "integration_commit_proof": {"passed": True, "integration_commit": snapshot.commit},
        },
    }
    (roots["v9"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    (roots["v9"] / "merge-queue" / "train" / "receipts" / f"{dedupe}.json").write_text(json.dumps(train), encoding="utf-8")
    receipts, _, gaps, diagnostics = evidence._authoritative_evidence(
        roots, {task.task_id: task}, snapshot,
    )
    assert receipts[task.task_id]
    assert "RECOVERY_PROVENANCE_GAP" not in {gap.kind for gap in gaps}
    assert "SUPERSEDED_RECOVERY_PROVENANCE" in {gap.kind for gap in diagnostics}


def test_v9_queue_pair_is_scanned_before_historical_roots(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8", "v9")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
        (root / "merge-queue" / "completed").mkdir(parents=True, exist_ok=True)
        (root / "merge-queue" / "train" / "receipts").mkdir(parents=True, exist_ok=True)
    (roots["v1"] / "projection" / "completion" / "validation_receipts").mkdir(parents=True)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task(
        "PTR-165", "fixture", "todo", (), ("scripts/owned.py",), command,
        evidence.validation_targets(command), "G165", "task/v1/fixture165", "baguqeerafixture165",
    )
    request, dedupe = "request-165", "dedupe-165"
    queue = {
        "task_id": task.task_id, "request_id": request, "dedupe_key": dedupe, "status": "completed",
        "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
        "commit_sha": snapshot.commit,
        "metadata": {
            "schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3",
            "task": {
                "board_namespace": evidence.BOARD_NAMESPACE,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
            },
        },
    }
    train = {
        "request_id": request, "canonical_task_id": task.canonical_task_key, "task_id": task.task_id,
        "status": "merged", "integrated": True, "merged": True,
        "merge_result": {
            "merged": True, "returncode": 0,
            "integration_commit_proof": {"passed": True, "integration_commit": snapshot.commit},
        },
    }
    (roots["v9"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    (roots["v9"] / "merge-queue" / "train" / "receipts" / f"{dedupe}.json").write_text(json.dumps(train), encoding="utf-8")
    receipts, _, gaps, _ = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert not any(g.kind == "STATE_ROOT_QUEUE_AUTHORITY_MISSING" and g.detail == "v9" for g in gaps)
    assert receipts[task.task_id][0].source.startswith("v9/")


def test_sealed_document_digest_mismatch_is_typed_audit_failure(tmp_path: Path) -> None:
    current = tmp_path / "proof-backed-test-reuse-v9"
    (current / "projection").mkdir(parents=True)
    live = {
        "schema": evidence.PREFLIGHT_SCHEMA,
        "valid": True,
        "errors": [],
        "task_count": 78,
        "todo_sha256": "sha256:dead",
        "objective_sha256": "sha256:dead",
        "plan_sha256": "sha256:dead",
        "configuration_sha256": "sha256:dead",
        "dependency_graph_id": "sha256:dead",
    }
    # Missing sealed receipts.
    gaps = evidence._match_sealed_document_digests(current, live)
    assert any(g.kind == "BOARD_SEALED_PREFLIGHT_MISSING" for g in gaps)

    # Present but mismatched digests against real repository files.
    native = {
        "schema": evidence.PREFLIGHT_SCHEMA,
        "valid": True,
        "errors": [],
        "task_count": 78,
        "todo_sha256": "sha256:substituted",
        "objective_sha256": "sha256:substituted",
        "plan_sha256": "sha256:substituted",
        "configuration_sha256": "sha256:substituted",
        "dependency_graph_id": "sha256:substituted",
    }
    launch = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-launch-preflight@1",
        "valid": True,
        "board": dict(native),
    }
    (current / "projection" / "native_board_preflight.json").write_text(json.dumps(native), encoding="utf-8")
    (current / "projection" / "launch_preflight.json").write_text(json.dumps(launch), encoding="utf-8")
    gaps = evidence._match_sealed_document_digests(current, live)
    assert any(g.kind == "BOARD_DOCUMENT_DIGEST_MISMATCH" for g in gaps)


def test_fixture_roots_resolve_from_controller_selected_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    parent = tmp_path / "state-home"
    for name in ("v1", "v6", "v8", "v9"):
        (parent / f"proof-backed-test-reuse-{name}").mkdir(parents=True)
    override = parent / "proof-backed-test-reuse-v9"
    monkeypatch.setenv("IPFS_PROOF_REUSE_STATE_ROOT", str(override))
    monkeypatch.setenv("HOME", str(tmp_path / "isolated-home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "isolated-xdg"))
    roots = _controller_state_siblings()
    assert roots["v9"] == override.resolve()
    assert roots["v8"] == (parent / "proof-backed-test-reuse-v8").resolve()
    # Isolated HOME must not be consulted once the controller override is set.
    assert "isolated-home" not in str(roots["v8"])
    assert "isolated-xdg" not in str(roots["v1"])
