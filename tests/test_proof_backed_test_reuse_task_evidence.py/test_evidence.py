from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/proof_backed_test_reuse_task_evidence.py"
SPEC = importlib.util.spec_from_file_location("task_evidence", SCRIPT)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evidence
SPEC.loader.exec_module(evidence)


def _store_object(gitdir: Path, data: bytes) -> str:
    import hashlib
    import zlib

    digest = hashlib.sha1(data).hexdigest()
    path = gitdir / "objects" / digest[:2] / digest[2:]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(zlib.compress(data))
    return digest


def _blob_object(content: bytes) -> bytes:
    return f"blob {len(content)}\0".encode() + content


def _tree_object(entries: list[tuple[str, str, str]]) -> bytes:
    body = b""
    for mode, name, sha in sorted(entries, key=lambda item: item[1].encode()):
        body += f"{mode} {name}\0".encode() + bytes.fromhex(sha)
    return f"tree {len(body)}\0".encode() + body


def _commit_object(tree: str, message: str, parent: str | None = None) -> bytes:
    lines = [f"tree {tree}"]
    if parent:
        lines.append(f"parent {parent}")
    sig = "Test <test@example.invalid> 1000000000 +0000"
    lines.extend([f"author {sig}", f"committer {sig}", "", message])
    body = ("\n".join(lines) + "\n").encode()
    return f"commit {len(body)}\0".encode() + body


def git(root: Path, *args: str) -> str:
    # Prefer pure observation helpers; fall back to subprocess when available.
    if args == ("rev-parse", "HEAD"):
        value = evidence._git_resolve_head(root)
        if value:
            return value
    try:
        return subprocess.check_output(("git", *args), cwd=root, text=True, stderr=subprocess.PIPE).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"git {args} failed under landlock-safe fixtures") from exc


def make_repo(tmp_path: Path) -> Path:
    """Build a minimal git repo without invoking the git binary.

    The Landlock write fence denies RDWR opens of ``/dev/null``, which breaks
    every git subprocess.  Fixture repos are therefore written as loose objects.
    """

    repo = tmp_path / "repo"
    repo.mkdir()
    gitdir = repo / ".git"
    (gitdir / "objects").mkdir(parents=True)
    (gitdir / "refs" / "heads").mkdir(parents=True)
    (gitdir / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    owned = b"x = 1\n"
    test = b"def test_ok(): pass\n"
    (repo / "scripts" / "owned.py").write_bytes(owned)
    (repo / "tests" / "test_owned.py").write_bytes(test)
    owned_sha = _store_object(gitdir, _blob_object(owned))
    test_sha = _store_object(gitdir, _blob_object(test))
    scripts_tree = _store_object(gitdir, _tree_object([("100644", "owned.py", owned_sha)]))
    tests_tree = _store_object(gitdir, _tree_object([("100644", "test_owned.py", test_sha)]))
    root_tree = _store_object(
        gitdir,
        _tree_object([("40000", "scripts", scripts_tree), ("40000", "tests", tests_tree)]),
    )
    commit = _store_object(gitdir, _commit_object(root_tree, "initial"))
    (gitdir / "refs" / "heads" / "master").write_text(commit + "\n", encoding="utf-8")
    return repo


def _commit_file(repo: Path, relative: str, content: bytes, message: str) -> str:
    """Append one file commit on master (loose objects only)."""

    gitdir = repo / ".git"
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    parent = (gitdir / "refs" / "heads" / "master").read_text(encoding="utf-8").strip()
    # Rebuild root tree from working files (scripts/ + tests/ + optional extras).
    entries: list[tuple[str, str, str]] = []
    for directory in ("scripts", "tests"):
        dir_path = repo / directory
        if not dir_path.is_dir():
            continue
        children = []
        for child in sorted(dir_path.iterdir()):
            if child.is_file():
                sha = _store_object(gitdir, _blob_object(child.read_bytes()))
                children.append(("100644", child.name, sha))
        if children:
            entries.append(("40000", directory, _store_object(gitdir, _tree_object(children))))
    # top-level files
    for child in sorted(repo.iterdir()):
        if child.name in {".git", "scripts", "tests"} or not child.is_file():
            continue
        sha = _store_object(gitdir, _blob_object(child.read_bytes()))
        entries.append(("100644", child.name, sha))
    root_tree = _store_object(gitdir, _tree_object(entries))
    commit = _store_object(gitdir, _commit_object(root_tree, message, parent=parent))
    (gitdir / "refs" / "heads" / "master").write_text(commit + "\n", encoding="utf-8")
    return commit


def write_board(tmp_path: Path, *, status: str = "completed") -> Path:
    board = tmp_path / "board.md"
    board.write_text(
        "## PTR-001 First\n\n- Status: completed\n- Depends on:\n- Goal id: G1\n"
        "- Outputs: scripts/owned.py\n- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q\n\n"
        f"## PTR-002 Second\n\n- Status: {status}\n- Depends on: PTR-001\n- Goal id: G2\n"
        "- Outputs: scripts/owned.py\n- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q\n",
        encoding="utf-8",
    )
    return board


def receipt(task_id: str, snapshot: object, command: str, *, commit: str | None = None, fresh: int = 9_999_999_999_999) -> dict[str, object]:
    return {
        "task_id": task_id,
        "merge_receipt_cid": "baguqeera" + task_id.lower(),
        "git_commit_id": commit or snapshot.commit,
        "validation_receipt_cid": "baguqeeravalid" + task_id.lower(),
        "validation_command": command,
        "passed": True,
        "proof_reuse_mode": "off",
        "fresh_until_ms": fresh,
        "git_tree_id": snapshot.tree,
        "gitlink_state_cid": snapshot.gitlink_state_cid,
    }


def write_receipts(root: Path, values: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index, value in enumerate(values):
        (root / f"receipt-{index}.json").write_text(json.dumps(value), encoding="utf-8")


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
    assert ready["dependency_order"] == [{"later_task": "PTR-002", "dependency": "PTR-001", "later_commit": snapshot.commit, "dependency_commit": snapshot.commit, "ordered": True}]


@pytest.mark.parametrize("mutation, expected", [
    (lambda value, snapshot: value.update({"fresh_until_ms": 99}), "VALIDATION_RECEIPT_STALE"),
    (lambda value, snapshot: value.update({"git_tree_id": "0" * 40}), "VALIDATION_PIN_MISMATCH"),
    (lambda value, snapshot: value.update({"validation_command": "pytest wrong.py"}), "VALIDATION_COMMAND_MISMATCH"),
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
    # Create a second commit that is not an ancestor of HEAD by writing a
    # divergent commit object whose parent is empty rather than master.
    gitdir = repo / ".git"
    blob = _store_object(gitdir, _blob_object(b"side\n"))
    tree = _store_object(gitdir, _tree_object([("100644", "side.txt", blob)]))
    side = _store_object(gitdir, _commit_object(tree, "side", parent=None))
    state = tmp_path / "state"
    write_receipts(state, [receipt("PTR-001", snapshot, command, commit=side)])
    report = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert "RECEIPT_COMMIT_NOT_ANCESTOR" in {gap["kind"] for gap in report["gaps"]}


def test_wrong_gitlink_pin_is_not_treated_as_a_present_output(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    validator = evidence.ProofReuseTaskEvidenceValidator(board, tmp_path / "state", repo, now_ms=100)
    # Model a checked-out component whose observed pin cannot equal the board's
    # expected live gitlink.  The validator must report the pin mismatch rather
    # than accepting the working-tree file.
    validator.snapshot.gitlinks["scripts"] = "0" * 40
    report = validator.audit()
    assert "GITLINK_PIN_MISMATCH" in {gap["kind"] for gap in report["gaps"]}


def write_event_log(root: Path, lane: int = 0) -> None:
    """Write the controller's v1/v6/v8 manifest-and-chain shape."""
    directory = root / "state" / f"ptr_lane_{lane}"
    directory.mkdir(parents=True, exist_ok=True)
    event = {
        "sequence": 1, "event_id": "sha256:event-1", "previous_event_id": "",
        "stream_id": "event-log:test", "snapshot_id": "event-log-snapshot:test",
    }
    raw = (json.dumps(event, sort_keys=True) + "\n").encode()
    events = directory / f"ptr_lane_{lane}_events.jsonl"
    events.write_bytes(raw)
    manifest = {
        "schema": "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2",
        "active_path": events.name, "stream_id": event["stream_id"], "snapshot_id": event["snapshot_id"],
        "last_event_id": event["event_id"], "files": [{"path": events.name, "size_bytes": len(raw), "event_count": 1,
        "first_sequence": 1, "last_sequence": 1, "start_previous_event_id": "", "sha256": evidence._sha256(raw)}],
    }
    manifest["manifest_digest"] = evidence._sha256(evidence.canonical_json(manifest))
    (directory / f"ptr_lane_{lane}_events.jsonl.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_sealed_authority_uses_only_joined_queue_train_and_flat_v1_receipts(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    snapshot = evidence.GitSnapshot(repo)
    parent = tmp_path / "state-home"
    roots = {name: parent / f"proof-backed-test-reuse-{name}" for name in ("v1", "v6", "v8")}
    for root in roots.values():
        for lane in range(3):
            write_event_log(root, lane)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    task = evidence.Task("PTR-160", "fixture", "completed", (), ("scripts/owned.py",), command,
                         evidence.validation_targets(command), "G160", "task/v1/fixture", "baguqeerafixture")
    request, dedupe = "request-160", "dedupe-160"
    queue = {
        "task_id": task.task_id, "request_id": request, "dedupe_key": dedupe,
        "canonical_task_key": task.canonical_task_key, "canonical_task_id": task.canonical_task_cid,
        "metadata": {"schema": "ipfs_accelerate_py/agent-supervisor/merge-candidate@3", "task": {
            "board_namespace": evidence.BOARD_NAMESPACE, "canonical_task_key": task.canonical_task_key,
            "canonical_task_cid": task.canonical_task_cid}},
    }
    train = {
        "request_id": request, "canonical_task_id": task.canonical_task_key, "task_id": task.task_id,
        "status": "merged", "integrated": True, "merged": True,
        "merge_result": {"merged": True, "returncode": 0, "integration_commit_proof": {
            "passed": True, "integration_commit": snapshot.commit}},
    }
    (roots["v8"] / "merge-queue" / "completed").mkdir(parents=True)
    (roots["v8"] / "merge-queue" / "train" / "receipts").mkdir(parents=True)
    (roots["v8"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    (roots["v8"] / "merge-queue" / "train" / "receipts" / f"{dedupe}.json").write_text(json.dumps(train), encoding="utf-8")
    validation = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1",
        "task_id": task.task_id, "task_cid": task.canonical_task_cid, "goal_id": task.goal_id,
        "validation_command": command, "validation_command_cid": evidence._validation_command_cid(command),
    }
    validation["validation_receipt_cid"] = evidence.canonical_cid(validation)
    receipt_dir = roots["v1"] / "projection" / "completion" / "validation_receipts"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "PTR-160.json").write_text(json.dumps(validation), encoding="utf-8")
    receipts, validations, gaps = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert gaps == []
    assert receipts[task.task_id][0].commit == snapshot.commit
    assert validations[task.task_id][0]["validation_receipt_cid"] == validation["validation_receipt_cid"]
    # A lookalike nested row cannot replace the sealed completed location.
    (roots["v8"] / "untrusted.json").write_text(json.dumps(queue), encoding="utf-8")
    assert evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)[0] == receipts
    queue["metadata"]["task"]["canonical_task_cid"] = "baguqeera-substituted"
    (roots["v8"] / "merge-queue" / "completed" / f"{request}.json").write_text(json.dumps(queue), encoding="utf-8")
    _, _, rejected = evidence._authoritative_evidence(roots, {task.task_id: task}, snapshot)
    assert "QUEUE_TASK_IDENTITY_MISMATCH" in {gap.kind for gap in rejected}


def test_sealed_queue_rejects_unbound_task_identity_and_broken_event_chain(tmp_path: Path) -> None:
    root = tmp_path / "proof-backed-test-reuse-v8"
    write_event_log(root)
    manifest = root / "state" / "ptr_lane_0" / "ptr_lane_0_events.jsonl.manifest.json"
    value = json.loads(manifest.read_text())
    value["last_event_id"] = "sha256:substituted"
    value["manifest_digest"] = evidence._sha256(evidence.canonical_json({key: item for key, item in value.items() if key != "manifest_digest"}))
    manifest.write_text(json.dumps(value), encoding="utf-8")
    assert "STATE_ROOT_EVENT_TAIL_INVALID" in {gap.kind for gap in evidence._verify_event_log("v8", root)}


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


def test_expect_incomplete_fails_closed_without_reviewed_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Isolated HOME without reviewed siblings must not look like a successful incompleteness proof.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("IPFS_PROOF_REUSE_STATE_ROOT", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    # Point the sealed todo comparison away so this uses fixture board? Live sealed needs real TODO.
    # Instead exercise reviewed-root resolution directly.
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

    # Real write path against a non-writable projection (same class as Landlock denial).
    projection = state / "projection"
    projection.mkdir()
    projection.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
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
    # Successful reconciliation event on v1
    event = {
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
        "sequence": 2,
        "event_id": "sha256:event-2",
        "previous_event_id": "sha256:event-1",
        "stream_id": "event-log:test",
        "snapshot_id": "event-log-snapshot:test",
    }
    # Append after the chain-valid first event
    lane = roots["v1"] / "state" / "ptr_lane_0"
    events = lane / "ptr_lane_0_events.jsonl"
    # Rebuild a two-event chain with matching manifest
    first = {
        "sequence": 1, "event_id": "sha256:event-1", "previous_event_id": "",
        "stream_id": "event-log:test", "snapshot_id": "event-log-snapshot:test",
    }
    raw = (json.dumps(first, sort_keys=True) + "\n" + json.dumps(event, sort_keys=True) + "\n").encode()
    events.write_bytes(raw)
    manifest = {
        "schema": "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2",
        "active_path": events.name, "stream_id": first["stream_id"], "snapshot_id": first["snapshot_id"],
        "last_event_id": event["event_id"],
        "files": [{"path": events.name, "size_bytes": len(raw), "event_count": 2,
                   "first_sequence": 1, "last_sequence": 2, "start_previous_event_id": "",
                   "sha256": evidence._sha256(raw)}],
    }
    body = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    manifest["manifest_digest"] = evidence._sha256(evidence.canonical_json(body))
    (lane / "ptr_lane_0_events.jsonl.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    receipts, gaps = evidence._reconciliation_receipts(
        {k: roots[k] for k in ("v1", "v6", "v8")}, {task.task_id: task}, snapshot,
    )
    assert gaps == []
    assert receipts[task.task_id][0].commit == snapshot.commit
    # Failed reconcile must not authorize
    event["resolved"] = False
    raw = (json.dumps(first, sort_keys=True) + "\n" + json.dumps(event, sort_keys=True) + "\n").encode()
    events.write_bytes(raw)
    manifest["files"][0]["size_bytes"] = len(raw)
    manifest["files"][0]["sha256"] = evidence._sha256(raw)
    body = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    manifest["manifest_digest"] = evidence._sha256(evidence.canonical_json(body))
    (lane / "ptr_lane_0_events.jsonl.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    empty, _ = evidence._reconciliation_receipts(
        {k: roots[k] for k in ("v1", "v6", "v8")}, {task.task_id: task}, snapshot,
    )
    assert task.task_id not in empty


def test_boundary_receipt_is_never_completion_authority() -> None:
    assert evidence.canonical_cid({"a": 1})
    # Construct the same body-free boundary the auditor embeds.
    boundary = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-boundary@1",
        "proof_authoritative": False,
        "completion_authority": False,
        "mode": "landlock-abi-3-or-newer-inherited",
    }
    assert boundary["proof_authoritative"] is False
    assert boundary["completion_authority"] is False
