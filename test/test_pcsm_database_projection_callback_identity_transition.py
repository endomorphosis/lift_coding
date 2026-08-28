"""The PCSM database projection/callback identity transition is fail-closed."""

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
        "pcsm_database_projection_callback_identity_operator",
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
        operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_database_projection_callback_identity_transition.py",
    ]
    pending = (
        "PENDING_"
        + "DATABASE_PROJECTION_CALLBACK_IDENTITY_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"database projection callback operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    payload = {
        "schema": (
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_TRANSITION_SCHEMA
        ),
        "reason": "stamp_projection_progress_and_normalize_sealed_callback_cid",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "prior_artifact_commit": (
                "28dc01c5377a5e1e964453cd79f7a95bd0ae06fa"
            ),
            "supervisor_callback_continuity_transition_receipt_id": (
                "sha256:29f4c4adf68f09ec4e6577214dbcce788f203a188e77e211"
                "7c32f89996402cab"
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
                operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_HEAD
            ),
            "accelerator_tree": (
                operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_TREE
            ),
            "changed_paths": base_paths,
            "nested_changed_paths": [],
            "nested_commits": [],
        },
        "sealed_source": {
            "source_head": sealed,
            "repository_tree_id": "sealed-tree",
            "parent": base,
            "operator_identity": operator._identity(sealed_operator),
            "changed_paths": [relative_operator],
        },
        "projection_progress_contract": {},
        "callback_cid_normalization_contract": {},
        "incident_evidence": {},
        "validations": [],
        "post_integration_canonical_validation": {},
        "historical_receipts_preserved": True,
        "supervisor_callback_continuity_receipt_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
        "manual_worktree_mutation": False,
    }
    payload["receipt_id"] = operator._identity(payload)
    state = {"payload": payload, "base_paths": list(base_paths)}

    monkeypatch.setattr(
        operator,
        "DATABASE_PROJECTION_CALLBACK_IDENTITY_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "DATABASE_PROJECTION_CALLBACK_IDENTITY_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "DATABASE_PROJECTION_CALLBACK_IDENTITY_TRANSITION_BASE_COMMIT",
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
            and path
            == operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_TRANSITION_PATH
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
        operator._verified_database_projection_callback_identity_operator_descendant(
            **kwargs
        )
    )
    assert verified["artifact_commit"] == artifact

    state["base_paths"].append("scripts/foreign.py")
    with pytest.raises(operator.OperatorError, match="operator delta changed"):
        operator._verified_database_projection_callback_identity_operator_descendant(
            **kwargs
        )


def test_transition_payload_rejects_unbound_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)
    state["payload"]["unbound_note"] = "outside the receipt schema"

    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_database_projection_callback_identity_operator_descendant(
            **kwargs
        )


def test_final_checkpoint_binds_only_receipts_and_prior_transition() -> None:
    operator = _load_operator()
    checkpoint = operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_CHECKPOINT_HEAD
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
            "28dc01c5377a5e1e964453cd79f7a95bd0ae06fa.." + checkpoint,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    expected = {
        "PCSM-034.json": "6c36cc8c78ac2a33c9659bb5ca08df23523b9012357e7a231db21ccb8d9c025e",
        "PCSM-036.json": "fb15bc6896aecfd7474979f5be8ba4d02b255c823b9b8e78d0ff4723bb0e67d4",
        "PCSM-046.json": "f48ebb2498e6541c767b138aed324967a1523636897d3a4e493b5945f33642cf",
        "PCSM-047.json": "a765a7ca3538e3c3420ed096ddcb3ea42902f35f7cdb99c942473a9d5c5fe86a",
        "PCSM-060.json": "96f3a73030606eff771ed4799ba4928ff23cd1792d84b9b149fcb91c0c21c71d",
        "PCSM-061.json": "19b3d03e174fdbd47660422cac94d81315fa16349267ca60c9bcb713cdebb833",
        "PCSM-062.json": "3050321e15513c3605afefbfa21d00c7f85da2201ed44fb329f3ce8a55c651b7",
        "PCSM-063.json": "e8469fe01517fb37fc08951a287b0c4e69b447a23b5c63faca0bba7cc0696fc2",
        "PCSM-064.json": "a553c00b323ebf9b121105b31260aa4486aacae24fc866be6bdd017f69d90ca9",
        "PCSM-065.json": "797f24853ebee3ccad3638e8f71c27ef4dcdc06d13fafbc8659cf28b7d9c4ea8",
        "PCSM-070.json": "94e6611fab37fd69c54dd0d9b4483f9f8ed8a31e6f0c58908a229f1d59938847",
    }
    prefix = "artifacts/proof_carrying_semantic_minification/receipts/"
    expected_paths = [prefix + name for name in expected]

    assert tree == operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_CHECKPOINT_TREE
    assert paths == expected_paths
    for path, digest in zip(expected_paths, expected.values(), strict=True):
        payload = subprocess.run(
            ["git", "show", f"{checkpoint}:{path}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(payload).hexdigest() == digest

    prior_path = (
        "artifacts/proof_carrying_semantic_minification/handoff/"
        "supervisor-restart-callback-continuity-transition.json"
    )
    prior = json.loads(
        subprocess.run(
            [
                "git",
                "show",
                "28dc01c5377a5e1e964453cd79f7a95bd0ae06fa:" + prior_path,
            ],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
    )
    assert prior["receipt_id"] == (
        "sha256:29f4c4adf68f09ec4e6577214dbcce788f203a188e77e211"
        "7c32f89996402cab"
    )


def test_nested_transition_has_exact_parents_trees_and_paths() -> None:
    operator = _load_operator()
    repository = ROOT / "external/ipfs_accelerate"
    chain = [
        (
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_PROJECTION_HEAD,
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_PROJECTION_TREE,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_daemon.py",
                "test/api/"
                "test_agent_supervisor_database_implementation_daemon.py",
                "test/api/test_agent_supervisor_worker_watchdog.py",
            ],
        ),
        (
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_HEAD,
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_TREE,
            operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_PROJECTION_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_daemon.py",
                "test/api/test_agent_supervisor_merge_train.py",
            ],
        ),
    ]
    for head, expected_tree, parent, expected_paths in chain:
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
        paths = subprocess.run(
            ["git", "diff", "--name-only", f"{parent}..{head}"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        assert tree == expected_tree
        assert parents == [parent]
        assert paths == expected_paths

    aggregate = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_HEAD}.."
            f"{operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_HEAD}",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    assert aggregate == [
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_daemon.py",
        "test/api/test_agent_supervisor_database_implementation_daemon.py",
        "test/api/test_agent_supervisor_merge_train.py",
        "test/api/test_agent_supervisor_worker_watchdog.py",
    ]


def test_predecessor_and_restart_receipts_propagate_exact_successor() -> None:
    operator = _load_operator()
    predecessor_operator = inspect.getsource(
        operator._verified_supervisor_callback_continuity_operator_descendant
    )
    predecessor_transition = inspect.getsource(
        operator._verified_supervisor_callback_continuity_transition
    )
    admission = inspect.getsource(operator._owner_restart_admission)
    owner_receipt = inspect.getsource(operator._owner_restart_receipt)

    successor = "_verified_database_projection_callback_identity"
    assert successor + "_operator_descendant" in predecessor_operator
    assert successor + "_transition" in predecessor_transition
    assert "if not exact_supervisor_callback_continuity_source" in (
        predecessor_transition
    )
    old_field = "supervisor_callback_continuity_transition_receipt_id"
    new_field = "database_projection_callback_identity_transition_receipt_id"
    assert old_field in admission
    assert old_field in owner_receipt
    assert new_field in admission
    assert new_field in owner_receipt


def test_transition_binds_exact_generation_46_and_controlled_stop_evidence() -> None:
    operator = _load_operator()
    transition = inspect.getsource(
        operator._verified_database_projection_callback_identity_transition
    )
    incident_evidence = transition.split(
        "expected_incidents = ", 1
    )[1].split("if dict(projection_contract)", 1)[0]

    assert '"task_alias": "PCSM-036"' in incident_evidence
    assert '"task_alias": "PCSM-060"' not in incident_evidence
    assert '"post_stop_observation"' in incident_evidence
    assert '"active_queue_entry_count": 0' in incident_evidence
    assert '"queue_entry_count": 0' not in incident_evidence
    assert '"task_state_mutation": False' in incident_evidence
    assert '"terminal_quiescence": False' in incident_evidence


def test_current_transition_receipt_passes_exact_read_only_verifier() -> None:
    operator = _load_operator()
    board, current_config = operator._load_config(operator.DEFAULT_CONFIG)
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    source_paths = operator._restart_source_paths(board)
    current_source_identities = {
        name: operator._identity(operator._tracked_bytes(path, head=current_head))
        for name, path in source_paths.items()
    }
    prior_base = "30153934f36656cb54bbfeb3b748504b072e13f2"
    prior_seal = "ab716c7b2c873758e84f0a7e17abb4acb0fa5c28"

    verified = operator._verified_database_projection_callback_identity_transition(
        board=board,
        current_head=current_head,
        current_config=current_config,
        current_source_identities=current_source_identities,
        prior_artifact_commit="28dc01c5377a5e1e964453cd79f7a95bd0ae06fa",
        prior_transition_receipt_id=(
            "sha256:29f4c4adf68f09ec4e6577214dbcce788f203a188e77e211"
            "7c32f89996402cab"
        ),
        prior_config_bytes=operator._git_blob_at(
            head=prior_base,
            path=board.config_path,
            field="prior transition config",
        ),
        prior_operator_bytes=operator._git_blob_at(
            head=prior_seal,
            path=Path(operator.__file__).resolve(),
            field="prior transition operator",
        ),
        prior_validator_bytes=operator._git_blob_at(
            head=prior_base,
            path=board.path(board.validator_path),
            field="prior transition validator",
        ),
    )

    assert verified["artifact_commit"] == current_head
    assert verified["accelerator_head"] == (
        operator.DATABASE_PROJECTION_CALLBACK_IDENTITY_ACCELERATOR_HEAD
    )
    assert verified["receipt"]["receipt_id"].startswith("sha256:")
