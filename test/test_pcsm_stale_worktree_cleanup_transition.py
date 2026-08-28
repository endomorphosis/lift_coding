"""The PCSM stale-cleanup source transition is exact and descendant-safe."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "scripts" / "run_agent_supervisor_proof_carrying_semantic_minification.py"


def _load_operator():
    spec = importlib.util.spec_from_file_location(
        "pcsm_stale_cleanup_operator",
        OPERATOR,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _transition_fixture(operator, monkeypatch: pytest.MonkeyPatch):
    prior_artifact = "a" * 40
    checkpoint_head = "b" * 40
    base_commit = "c" * 40
    sealed_head = "d" * 40
    artifact_commit = "e" * 40
    current_head = "f" * 40
    old_accelerator = "1" * 40
    receipt_path = (
        "artifacts/proof_carrying_semantic_minification/receipts/PCSM-019.json"
    )
    transition_path = (
        operator.STALE_WORKTREE_CLEANUP_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    operator_path = Path(operator.__file__).resolve()
    config_path = operator.ROOT / "config" / "fixture.json"
    validator_path = operator.ROOT / "scripts" / "fixture_validator.py"
    board = SimpleNamespace(
        config_path=config_path,
        validator_path=Path("scripts/fixture_validator.py"),
        path=lambda value: operator.ROOT / value,
    )

    prior_config = {
        "max_task_attempts": 3,
        "source_binding": {
            "ipfs_accelerate_planning_revision": old_accelerator,
            "ipfs_accelerate_planning_tree": "2" * 40,
        },
    }
    base_config = json.loads(json.dumps(prior_config))
    base_config["source_binding"]["ipfs_accelerate_planning_revision"] = (
        operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
    )
    base_config["source_binding"]["ipfs_accelerate_planning_tree"] = (
        operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
    )
    prior_config_bytes = json.dumps(prior_config, sort_keys=True).encode()
    base_config_bytes = json.dumps(base_config, sort_keys=True).encode()
    prior_operator = b"sealed blocked-retry operator\n"
    pending = b"PENDING_STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT"
    base_operator = b"cleanup transition operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base_commit.encode(), 1)
    validator = b"validator\n"
    receipt_blob = b'{"task":"PCSM-019"}\n'
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "test/test_pcsm_stale_worktree_cleanup_transition.py",
    ]
    nested_paths = [
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py",
        "test/api/test_agent_supervisor_implementation_daemon_runner.py",
    ]
    validations = [
        {
            "cwd": "external/ipfs_accelerate",
            "command": [
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/test_agent_supervisor_implementation_daemon_runner.py::"
                "test_stale_worktree_cleanup_delegates_protected_dirty_checkout",
                "test/api/test_agent_supervisor_incremental_runtime.py::"
                "test_completed_rescued_dead_pool_workspace_retires_in_three_passes",
            ],
            "outcome": "passed",
            "summary": "2 passed",
        },
        {
            "cwd": ".",
            "command": [
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_stale_worktree_cleanup_transition.py",
            ],
            "outcome": "passed",
            "summary": "3 passed",
        },
        {
            "cwd": ".",
            "command": [
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ],
            "outcome": "passed",
            "summary": "70 tasks, 96 packages, no warnings",
        },
    ]
    payload = {
        "schema": operator.STALE_WORKTREE_CLEANUP_TRANSITION_SCHEMA,
        "reason": "delegate_daemon_stale_worktree_cleanup_to_supervisor",
        "prior_checkpoint": {
            "source_head": checkpoint_head,
            "repository_tree_id": "checkpoint-tree",
            "prior_artifact_commit": prior_artifact,
            "descendant_repair_receipt_id": "sha256:" + "3" * 64,
            "blocked_retry_batch_receipt_id": "sha256:" + "4" * 64,
            "changed_receipts": [
                {
                    "path": receipt_path,
                    "bytes_id": operator._identity(receipt_blob),
                }
            ],
        },
        "repair_base": {
            "source_head": base_commit,
            "repository_tree_id": "base-tree",
            "parent": checkpoint_head,
            "operator_identity": operator._identity(base_operator),
            "config_identity": operator._identity(base_config_bytes),
            "validator_identity": operator._identity(validator),
            "accelerator_head": operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD,
            "accelerator_tree": operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE,
            "changed_paths": base_paths,
            "nested_changed_paths": nested_paths,
        },
        "sealed_source": {
            "source_head": sealed_head,
            "repository_tree_id": "sealed-tree",
            "parent": base_commit,
            "operator_identity": operator._identity(sealed_operator),
            "changed_paths": [
                "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py"
            ],
        },
        "safety_policy": {
            "daemon_stale_cleanup_action": "detect_and_delegate",
            "destructive_cleanup_authority": "supervisor_worktree_reconciliation",
            "daemon_stale_cleanup_may_remove_worktree": False,
            "daemon_stale_cleanup_may_delete_branch": False,
            "dirty_bytes_require_rescue_before_retirement": True,
            "peer_active_state_requires_preservation": True,
        },
        "validations": validations,
        "historical_receipts_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
    }
    payload["receipt_id"] = operator._identity(payload)
    receipt_bytes = json.dumps(payload, sort_keys=True).encode()

    state = {
        "checkpoint_paths": [receipt_path],
        "nested_paths": list(nested_paths),
    }
    commit_trees = {
        checkpoint_head: "checkpoint-tree",
        base_commit: "base-tree",
        sealed_head: "sealed-tree",
        operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD: (
            operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
        ),
    }
    monkeypatch.setattr(
        operator,
        "STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT",
        base_commit,
    )
    monkeypatch.setattr(
        operator,
        "_git_commit_tree",
        lambda commit, **_kwargs: commit_trees[str(commit)],
    )
    monkeypatch.setattr(operator, "_git_is_ancestor", lambda *_args, **_kwargs: None)

    def git(*args, **_kwargs):
        values = tuple(str(item) for item in args)
        if values[:2] == ("diff", "--name-only"):
            revision = values[2]
            if revision == f"{prior_artifact}..{checkpoint_head}":
                return "\n".join(state["checkpoint_paths"])
            if revision == f"{checkpoint_head}..{base_commit}":
                return "\n".join(base_paths)
            if revision == f"{base_commit}..{sealed_head}":
                return base_paths[2]
            if revision == f"{sealed_head}..{artifact_commit}":
                return transition_path
        if values[:3] == ("show", "-s", "--format=%P"):
            return {
                base_commit: checkpoint_head,
                sealed_head: base_commit,
                artifact_commit: sealed_head,
            }[values[3]]
        if values[:1] == ("ls-tree",):
            return (
                f"160000 commit {old_accelerator}\texternal/ipfs_accelerate"
                if values[1] == checkpoint_head
                else "160000 commit "
                f"{operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD}"
                "\texternal/ipfs_accelerate"
            )
        if values[:3] == ("log", "--diff-filter=A", "--format=%H"):
            return artifact_commit
        raise AssertionError(f"unexpected git call: {values}")

    monkeypatch.setattr(operator, "_git", git)

    def blob_at(*, head, path, **_kwargs):
        relative = Path(path).relative_to(operator.ROOT).as_posix()
        blobs = {
            (checkpoint_head, receipt_path): receipt_blob,
            (checkpoint_head, config_path.relative_to(operator.ROOT).as_posix()): (
                prior_config_bytes
            ),
            (checkpoint_head, operator_path.relative_to(operator.ROOT).as_posix()): (
                prior_operator
            ),
            (checkpoint_head, validator_path.relative_to(operator.ROOT).as_posix()): (
                validator
            ),
            (base_commit, operator_path.relative_to(operator.ROOT).as_posix()): (
                base_operator
            ),
            (base_commit, config_path.relative_to(operator.ROOT).as_posix()): (
                base_config_bytes
            ),
            (base_commit, validator_path.relative_to(operator.ROOT).as_posix()): (
                validator
            ),
            (sealed_head, operator_path.relative_to(operator.ROOT).as_posix()): (
                sealed_operator
            ),
            (artifact_commit, transition_path): receipt_bytes,
        }
        return blobs[(str(head), relative)]

    monkeypatch.setattr(operator, "_git_blob_at", blob_at)

    def tracked(path, *, head):
        assert head == current_head
        relative = Path(path).relative_to(operator.ROOT).as_posix()
        return {
            transition_path: receipt_bytes,
            config_path.relative_to(operator.ROOT).as_posix(): base_config_bytes,
            operator_path.relative_to(operator.ROOT).as_posix(): sealed_operator,
            validator_path.relative_to(operator.ROOT).as_posix(): validator,
        }[relative]

    monkeypatch.setattr(operator, "_tracked_bytes", tracked)

    def run(command, **_kwargs):
        if command[1:4] == ["show", "-s", "--format=%P"]:
            return subprocess.CompletedProcess(
                command,
                0,
                old_accelerator + "\n",
                "",
            )
        if command[1:3] == ["diff", "--name-only"]:
            return subprocess.CompletedProcess(
                command,
                0,
                "\n".join(state["nested_paths"]) + "\n",
                "",
            )
        raise AssertionError(f"unexpected subprocess call: {command}")

    monkeypatch.setattr(operator.subprocess, "run", run)
    kwargs = {
        "board": board,
        "current_head": current_head,
        "current_config": base_config,
        "current_source_identities": {
            "config": operator._identity(base_config_bytes),
            "operator": operator._identity(sealed_operator),
            "validator": operator._identity(validator),
        },
        "prior_artifact_commit": prior_artifact,
        "prior_descendant_repair_receipt_id": "sha256:" + "3" * 64,
        "prior_batch_receipt_id": "sha256:" + "4" * 64,
        "prior_config_bytes": prior_config_bytes,
        "prior_operator_bytes": prior_operator,
        "prior_validator_bytes": validator,
    }
    return kwargs, state, artifact_commit, sealed_head


def test_bootstrap_broker_verifier_binds_exact_cleanup_operator_descendant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    historical_head = "a" * 40
    blocked_retry_base = "b" * 40
    blocked_retry_head = "c" * 40
    transition_base = "d" * 40
    transition_head = "e" * 40
    current_head = "f" * 40
    transition_tree = "transition-tree"
    operator_path = Path(operator.__file__).resolve()
    relative_operator = operator_path.relative_to(operator.ROOT).as_posix()
    historical_operator = b"historical bootstrap-broker operator\n"
    blocked_retry_operator = b"sealed blocked-retry operator\n"
    pending = b"PENDING_STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT"
    transition_base_operator = b"cleanup transition operator " + pending + b"\n"
    transition_operator = transition_base_operator.replace(
        pending,
        transition_base.encode(),
        1,
    )

    descendant = {
        "schema": operator.CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_SCHEMA,
        "repair_base": {"source_head": blocked_retry_base},
        "sealed_source": {
            "source_head": blocked_retry_head,
            "operator_identity": operator._identity(blocked_retry_operator),
        },
    }
    descendant["receipt_id"] = operator._identity(descendant)
    transition = {
        "schema": operator.STALE_WORKTREE_CLEANUP_TRANSITION_SCHEMA,
        "reason": "delegate_daemon_stale_worktree_cleanup_to_supervisor",
        "prior_checkpoint": {
            "descendant_repair_receipt_id": descendant["receipt_id"],
        },
        "repair_base": {
            "source_head": transition_base,
            "operator_identity": operator._identity(transition_base_operator),
        },
        "sealed_source": {
            "source_head": transition_head,
            "repository_tree_id": transition_tree,
            "parent": transition_base,
            "operator_identity": operator._identity(transition_operator),
            "changed_paths": [relative_operator],
        },
    }
    transition["receipt_id"] = operator._identity(transition)
    state = {
        "transition_bytes": json.dumps(transition, sort_keys=True).encode(),
    }
    descendant_bytes = json.dumps(descendant, sort_keys=True).encode()

    monkeypatch.setattr(
        operator,
        "CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD",
        historical_head,
    )
    monkeypatch.setattr(
        operator,
        "CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT",
        blocked_retry_base,
    )
    monkeypatch.setattr(
        operator,
        "STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT",
        transition_base,
    )

    def tracked(path, *, head):
        assert head == current_head
        if Path(path) == operator.CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH:
            return descendant_bytes
        if Path(path) == operator.STALE_WORKTREE_CLEANUP_TRANSITION_PATH:
            return state["transition_bytes"]
        raise AssertionError(f"unexpected tracked path: {path}")

    monkeypatch.setattr(operator, "_tracked_bytes", tracked)

    def blob_at(*, head, path, **_kwargs):
        assert Path(path) == operator_path
        return {
            historical_head: historical_operator,
            blocked_retry_head: blocked_retry_operator,
            transition_base: transition_base_operator,
            transition_head: transition_operator,
        }[str(head)]

    monkeypatch.setattr(operator, "_git_blob_at", blob_at)
    monkeypatch.setattr(
        operator,
        "_git_commit_tree",
        lambda commit, **_kwargs: (
            transition_tree
            if str(commit) == transition_head
            else pytest.fail(f"unexpected commit tree: {commit}")
        ),
    )

    def git(*args, **_kwargs):
        values = tuple(str(item) for item in args)
        if values == ("show", "-s", "--format=%P", transition_head):
            return transition_base
        if values == (
            "diff",
            "--name-only",
            f"{transition_base}..{transition_head}",
        ):
            return relative_operator
        raise AssertionError(f"unexpected git call: {values}")

    monkeypatch.setattr(operator, "_git", git)
    ancestry: list[tuple[str, str]] = []
    monkeypatch.setattr(
        operator,
        "_git_is_ancestor",
        lambda ancestor, descendant, **_kwargs: ancestry.append(
            (str(ancestor), str(descendant))
        ),
    )
    kwargs = {
        "expected_historical_operator": historical_operator,
        "historical_operator_identity": operator._identity(historical_operator),
        "current_head": current_head,
        "operator_path": operator_path,
    }

    operator._verified_bootstrap_broker_operator_descendant(
        current_operator=transition_operator,
        **kwargs,
    )

    assert ancestry == [
        (blocked_retry_base, current_head),
        (transition_head, current_head),
    ]
    with pytest.raises(
        operator.OperatorError,
        match="stale-worktree cleanup operator delta changed",
    ):
        operator._verified_bootstrap_broker_operator_descendant(
            current_operator=transition_operator + b"foreign delta\n",
            **kwargs,
        )

    tampered_transition = dict(transition)
    tampered_transition["unbound_note"] = "not covered by the receipt identity"
    state["transition_bytes"] = json.dumps(
        tampered_transition,
        sort_keys=True,
    ).encode()
    with pytest.raises(
        operator.OperatorError,
        match="stale-worktree cleanup operator delta changed",
    ):
        operator._verified_bootstrap_broker_operator_descendant(
            current_operator=transition_operator,
            **kwargs,
        )


def test_stale_cleanup_transition_accepts_exact_receipt_descendants_and_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, _state, artifact_commit, sealed_head = _transition_fixture(
        operator,
        monkeypatch,
    )

    verified = operator._verified_stale_worktree_cleanup_transition(**kwargs)

    assert verified["artifact_commit"] == artifact_commit
    assert verified["sealed_source_head"] == sealed_head
    assert verified["accelerator_head"] == (
        operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
    )


def test_stale_cleanup_transition_rejects_nonreceipt_checkpoint_descendant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact_commit, _sealed_head = _transition_fixture(
        operator,
        monkeypatch,
    )
    state["checkpoint_paths"].append("scripts/unsealed_runtime_change.py")

    with pytest.raises(
        operator.OperatorError,
        match="non-receipt or unbound descendants",
    ):
        operator._verified_stale_worktree_cleanup_transition(**kwargs)


def test_stale_cleanup_transition_rejects_nested_delta_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact_commit, _sealed_head = _transition_fixture(
        operator,
        monkeypatch,
    )
    state["nested_paths"].append("ipfs_accelerate_py/foreign.py")

    with pytest.raises(operator.OperatorError, match="nested delta changed"):
        operator._verified_stale_worktree_cleanup_transition(**kwargs)
