"""The PCSM database-lifecycle identity transition is exact and fail-closed."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = (
    ROOT
    / "scripts"
    / "run_agent_supervisor_proof_carrying_semantic_minification.py"
)


def _load_operator():
    spec = importlib.util.spec_from_file_location(
        "pcsm_database_lifecycle_identity_operator",
        OPERATOR,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operator_gate_fixture(operator, monkeypatch: pytest.MonkeyPatch):
    checkpoint = "1" * 40
    checkpoint_tree = "2" * 40
    base = "3" * 40
    sealed = "4" * 40
    artifact = "5" * 40
    current = "6" * 40
    relative_operator = Path(operator.__file__).resolve().relative_to(
        operator.ROOT
    ).as_posix()
    receipt_relative = (
        operator.DATABASE_LIFECYCLE_IDENTITY_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_database_lifecycle_identity_transition.py",
    ]
    pending = (
        "PENDING_"
        + "DATABASE_LIFECYCLE_IDENTITY_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"database lifecycle identity operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    payload = {
        "schema": operator.DATABASE_LIFECYCLE_IDENTITY_TRANSITION_SCHEMA,
        "reason": "bind_distinct_database_and_portal_lifecycle_identities",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "prior_artifact_commit": (
                "7ce3772ae606c6f8a15dc25a434dd97df929cfde"
            ),
            "database_watchdog_activity_transition_receipt_id": (
                "sha256:8c1b0ed9fbc29f3116ac670405019df3d3ef1f51eb144f5f"
                "6e9dca64e5e873f0"
            ),
            "changed_receipts": [],
        },
        "repair_base": {
            "source_head": base,
            "repository_tree_id": "base-tree",
            "parent": checkpoint,
            "operator_identity": operator._identity(base_operator),
            "config_identity": "sha256:" + "7" * 64,
            "validator_identity": "sha256:" + "8" * 64,
            "accelerator_head": (
                operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_HEAD
            ),
            "accelerator_tree": (
                operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_TREE
            ),
            "changed_paths": base_paths,
            "nested_changed_paths": [],
        },
        "sealed_source": {
            "source_head": sealed,
            "repository_tree_id": "sealed-tree",
            "parent": base,
            "operator_identity": operator._identity(sealed_operator),
            "changed_paths": [relative_operator],
        },
        "watchdog_identity_contract": {},
        "completed_rescue_cleanup_identity_contract": {},
        "validations": [],
        "historical_receipts_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
        "manual_worktree_mutation": False,
    }
    payload["receipt_id"] = operator._identity(payload)
    state = {"payload": payload, "base_paths": list(base_paths)}

    monkeypatch.setattr(
        operator,
        "DATABASE_LIFECYCLE_IDENTITY_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "DATABASE_LIFECYCLE_IDENTITY_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "DATABASE_LIFECYCLE_IDENTITY_TRANSITION_BASE_COMMIT",
        base,
    )

    def receipt_bytes() -> bytes:
        return json.dumps(state["payload"], sort_keys=True).encode()

    monkeypatch.setattr(
        operator,
        "_tracked_bytes",
        lambda _path, **_kwargs: receipt_bytes(),
    )
    monkeypatch.setattr(
        operator,
        "_git_commit_tree",
        lambda commit, **_kwargs: {
            checkpoint: checkpoint_tree,
            base: "base-tree",
            sealed: "sealed-tree",
        }[commit],
    )

    def git_blob_at(*, head, path, field):
        del field
        if head == base:
            return base_operator
        if head == sealed:
            return sealed_operator
        if (
            head == artifact
            and path == operator.DATABASE_LIFECYCLE_IDENTITY_TRANSITION_PATH
        ):
            return receipt_bytes()
        raise AssertionError((head, path))

    monkeypatch.setattr(operator, "_git_blob_at", git_blob_at)

    def git(*arguments, **_kwargs):
        command = tuple(arguments)
        mapping = {
            ("show", "-s", "--format=%P", base): checkpoint,
            (
                "diff",
                "--name-only",
                f"{checkpoint}..{base}",
            ): lambda: "\n".join(state["base_paths"]) + "\n",
            ("show", "-s", "--format=%P", sealed): base,
            (
                "diff",
                "--name-only",
                f"{base}..{sealed}",
            ): relative_operator + "\n",
            (
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            ): artifact + "\n",
            ("show", "-s", "--format=%P", artifact): sealed,
            (
                "diff",
                "--name-only",
                f"{sealed}..{artifact}",
            ): receipt_relative + "\n",
        }
        value = mapping[command]
        return value() if callable(value) else value

    monkeypatch.setattr(operator, "_git", git)
    monkeypatch.setattr(
        operator,
        "_git_is_ancestor",
        lambda *_args, **_kwargs: None,
    )
    kwargs = {
        "current_operator": sealed_operator,
        "current_head": current,
        "operator_path": Path(operator.__file__).resolve(),
    }
    return kwargs, state, artifact


def test_operator_descendant_accepts_only_direct_b_s_a_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, artifact = _operator_gate_fixture(operator, monkeypatch)

    verified = (
        operator._verified_database_lifecycle_identity_operator_descendant(
            **kwargs
        )
    )
    assert verified["artifact_commit"] == artifact

    state["base_paths"].append("scripts/foreign.py")
    with pytest.raises(operator.OperatorError, match="operator delta changed"):
        operator._verified_database_lifecycle_identity_operator_descendant(
            **kwargs
        )


def test_transition_payload_rejects_unbound_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)
    state["payload"]["unbound_note"] = "outside the receipt schema"

    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_database_lifecycle_identity_operator_descendant(
            **kwargs
        )


def test_checkpoint_binds_exact_six_receipts() -> None:
    operator = _load_operator()
    checkpoint = operator.DATABASE_LIFECYCLE_IDENTITY_CHECKPOINT_HEAD
    tree = subprocess.run(
        ["git", "rev-parse", f"{checkpoint}^{{tree}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    paths = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "7ce3772ae606c6f8a15dc25a434dd97df929cfde.." + checkpoint,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    expected = {
        "PCSM-022.json": (
            "a5212cc3c155b4e73edb7da41271e061f20665786196c27217aa1a38a51cb001"
        ),
        "PCSM-024.json": (
            "72b9869c58612b1a6a014f785a70286a24a418745cb440da7646abf4516c8d32"
        ),
        "PCSM-025.json": (
            "fa1cd495342b314476ce8f01025a49c5bbd57af09f64abc481f5135316ca25b8"
        ),
        "PCSM-041.json": (
            "769c976924565b9faeb13c962d405da360b37832fc1435be48dc7ad7cb98d3b6"
        ),
        "PCSM-042.json": (
            "dc5c2e351aa436c7ee214b6045c15f8a386b03d5026bf195e04ceaf86eee8eab"
        ),
        "PCSM-050.json": (
            "fae4dae308bcf1e5dfb5176c56e32734cc1ffb1524b903af2713f3495d773477"
        ),
    }
    expected_paths = [
        "artifacts/proof_carrying_semantic_minification/receipts/" + name
        for name in expected
    ]

    assert tree == operator.DATABASE_LIFECYCLE_IDENTITY_CHECKPOINT_TREE
    assert paths == expected_paths
    for name, digest in expected.items():
        payload = subprocess.run(
            ["git", "show", f"{checkpoint}:" + expected_paths[list(expected).index(name)]],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(payload).hexdigest() == digest


def test_nested_identity_delta_has_exact_parent_tree_and_paths() -> None:
    operator = _load_operator()
    repository = ROOT / "external/ipfs_accelerate"
    head = operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_HEAD
    tree = subprocess.run(
        ["git", "rev-parse", f"{head}^{{tree}}"],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    parents = subprocess.run(
        ["git", "show", "-s", "--format=%P", head],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip().split()
    watchdog = operator.DATABASE_LIFECYCLE_IDENTITY_WATCHDOG_HEAD
    watchdog_tree = subprocess.run(
        ["git", "rev-parse", f"{watchdog}^{{tree}}"],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    watchdog_parents = subprocess.run(
        ["git", "show", "-s", "--format=%P", watchdog],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip().split()
    watchdog_paths = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{operator.DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD}..{watchdog}",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    cleanup_paths = subprocess.run(
        ["git", "diff", "--name-only", f"{watchdog}..{head}"],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    paths = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{operator.DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD}..{head}",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()

    assert tree == operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_TREE
    assert parents == [watchdog]
    assert watchdog_tree == operator.DATABASE_LIFECYCLE_IDENTITY_WATCHDOG_TREE
    assert watchdog_parents == [
        operator.DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD
    ]
    assert watchdog_paths == [
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_supervisor.py",
        "test/api/"
        "test_implementation_supervisor_control_plane_pool_lease.py",
    ]
    assert cleanup_paths == [
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "database_portal_bridge.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_supervisor.py",
        "test/api/test_agent_supervisor_reconciliation_auto_unblock.py",
    ]
    assert paths == [
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "database_portal_bridge.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_supervisor.py",
        "test/api/test_agent_supervisor_reconciliation_auto_unblock.py",
        "test/api/"
        "test_implementation_supervisor_control_plane_pool_lease.py",
    ]


def test_predecessor_and_restart_receipts_propagate_exact_successor() -> None:
    operator = _load_operator()
    predecessor_operator = inspect.getsource(
        operator._verified_database_watchdog_activity_operator_descendant
    )
    predecessor_transition = inspect.getsource(
        operator._verified_database_watchdog_activity_transition
    )
    admission = inspect.getsource(operator._owner_restart_admission)
    owner_receipt = inspect.getsource(operator._owner_restart_receipt)

    assert "_verified_database_lifecycle_identity_operator_descendant" in (
        predecessor_operator
    )
    assert "_verified_database_lifecycle_identity_transition" in (
        predecessor_transition
    )
    assert "if not exact_database_watchdog_source" in predecessor_transition
    field = "database_lifecycle_identity_transition_receipt_id"
    assert field in admission
    assert field in owner_receipt
