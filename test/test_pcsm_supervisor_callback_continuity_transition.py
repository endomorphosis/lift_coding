"""The PCSM supervisor callback-continuity transition is fail-closed."""

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
        "pcsm_supervisor_callback_continuity_operator",
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
        operator.SUPERVISOR_CALLBACK_CONTINUITY_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_supervisor_callback_continuity_transition.py",
    ]
    pending = (
        "PENDING_"
        + "SUPERVISOR_CALLBACK_CONTINUITY_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"supervisor callback continuity operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    payload = {
        "schema": (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_TRANSITION_SCHEMA
        ),
        "reason": (
            "preserve_terminal_callback_and_live_supervisor_generation_continuity"
        ),
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "prior_artifact_commit": (
                "c2f40b62eae073798c24adedcb0484b47393dee8"
            ),
            "database_lifecycle_identity_transition_receipt_id": (
                "sha256:3f94f1eee5297d02dde7fcebd54e6afc40423534514caf6e"
                "565368ddbb58997f"
            ),
            "changed_receipts": [],
            "authority_snapshot": {},
        },
        "repair_base": {
            "source_head": base,
            "repository_tree_id": "base-tree",
            "parent": checkpoint,
            "operator_identity": operator._identity(base_operator),
            "config_identity": "sha256:" + "7" * 64,
            "validator_identity": "sha256:" + "8" * 64,
            "accelerator_head": (
                operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_HEAD
            ),
            "accelerator_tree": (
                operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_TREE
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
        "continuity_contracts": {},
        "incident_evidence": {},
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
        "SUPERVISOR_CALLBACK_CONTINUITY_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "SUPERVISOR_CALLBACK_CONTINUITY_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "SUPERVISOR_CALLBACK_CONTINUITY_TRANSITION_BASE_COMMIT",
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
            == operator.SUPERVISOR_CALLBACK_CONTINUITY_TRANSITION_PATH
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
        operator._verified_supervisor_callback_continuity_operator_descendant(
            **kwargs
        )
    )
    assert verified["artifact_commit"] == artifact

    state["base_paths"].append("scripts/foreign.py")
    with pytest.raises(operator.OperatorError, match="operator delta changed"):
        operator._verified_supervisor_callback_continuity_operator_descendant(
            **kwargs
        )


def test_transition_payload_rejects_unbound_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)
    state["payload"]["unbound_note"] = "outside the receipt schema"

    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_supervisor_callback_continuity_operator_descendant(
            **kwargs
        )


def test_checkpoint_binds_exact_seventeen_receipts() -> None:
    operator = _load_operator()
    checkpoint = operator.SUPERVISOR_CALLBACK_CONTINUITY_CHECKPOINT_HEAD
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
            "c2f40b62eae073798c24adedcb0484b47393dee8.." + checkpoint,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    expected = {
        "PCSM-027.json": "5836b2f76182b9ad83005068c81888464d9b2ee7f2a3099ace2bbf3b450f5772",
        "PCSM-028.json": "3631475bf96bac744a6d3bb9bf048ab39c98408a996eb2bd6a66805769882b3f",
        "PCSM-030.json": "c588061ebbd0b388c4c7b2b8301d8ba3f4b3af97594607428cd8a6c13727f10f",
        "PCSM-031.json": "66abc17a7b60b77192514283602a375f343263567845107bd4215bb53df46005",
        "PCSM-032.json": "9f8ec42636058fcafb5f0e24dfb5875444d3704a4bcfb2cc222d6ed314b79859",
        "PCSM-033.json": "636d832015c044126b50ca096d3571a8be33981949c25284071dff05a970e50b",
        "PCSM-035.json": "756e46f6c443eba954c4e938bdbcd1eee6c4f71a2142d0b8b030c3cde2557b4c",
        "PCSM-043.json": "df38e5f5340fa38aa383037b8326f98eca6f2f04ab31fd6d4e708fb33edc42e2",
        "PCSM-044.json": "db5e0de909216bdb8785d2a99026c5952823db2b68633f88eb3ed4e81ee85c3c",
        "PCSM-045.json": "a9acba8f9e46e0ea0e76d74da4e1610dd1b8251b74460358b36b8c6a4fedfa0f",
        "PCSM-051.json": "72a29f5dcd1726156635321afa2cd8ded6a7887eeb75fc38468e8b6be26ce24f",
        "PCSM-052.json": "bcbace9e94e819f09b273988576e4df5b5e955e8b201f7aea59b7c4e5f7c5eea",
        "PCSM-053.json": "15c2ba77680ffcb2ebc96ed263c9ccb6a54825e5a51351a3ae53c4327433cca1",
        "PCSM-054.json": "039c3e7cf1da3ef1356f81fa3c345413f6046ba811cdc2178ab66d5b9ab6f7be",
        "PCSM-055.json": "3588a01a67fef53357d97e0a4e7d44c321b3cbf6a9b40b53c201459abc81a715",
        "PCSM-056.json": "79e6f818ff38a6d65bb32bfc0a4c406a189c1db77333170abde880e33cea7a22",
        "PCSM-057.json": "451a2ff3afdfa4ed4d0bafb4cde060a3ed81e29a329619bb6d3eca98c5474315",
    }
    prefix = "artifacts/proof_carrying_semantic_minification/receipts/"
    expected_paths = [prefix + name for name in expected]

    assert tree == operator.SUPERVISOR_CALLBACK_CONTINUITY_CHECKPOINT_TREE
    assert paths == expected_paths
    for path, digest in zip(expected_paths, expected.values(), strict=True):
        payload = subprocess.run(
            ["git", "show", f"{checkpoint}:{path}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(payload).hexdigest() == digest


def test_nested_continuity_chain_has_exact_parents_trees_and_paths() -> None:
    operator = _load_operator()
    repository = ROOT / "external/ipfs_accelerate"
    chain = [
        (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ROUTE_HEAD,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ROUTE_TREE,
            operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_supervisor.py",
                "test/api/"
                "test_agent_supervisor_reconciliation_auto_unblock.py",
            ],
        ),
        (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_GUARD_HEAD,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_GUARD_TREE,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ROUTE_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_supervisor.py",
                "test/api/"
                "test_implementation_supervisor_control_plane_pool_lease.py",
            ],
        ),
        (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_STATUS_GAP_HEAD,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_STATUS_GAP_TREE,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_GUARD_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/runtime/"
                "multi_supervisor_runner.py",
                "test/api/"
                "test_agent_supervisor_multi_supervisor_generation_status.py",
                "test/api/test_agent_supervisor_multi_supervisor_shutdown.py",
            ],
        ),
        (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_CHECKOUT_REPAIR_HEAD,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_CHECKOUT_REPAIR_TREE,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_STATUS_GAP_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_supervisor.py",
                "test/api/"
                "test_implementation_supervisor_control_plane_pool_lease.py",
            ],
        ),
        (
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_HEAD,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_TREE,
            operator.SUPERVISOR_CALLBACK_CONTINUITY_CHECKOUT_REPAIR_HEAD,
            [
                "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
                "implementation_supervisor.py",
                "test/api/"
                "test_implementation_supervisor_control_plane_pool_lease.py",
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
            f"{operator.DATABASE_LIFECYCLE_IDENTITY_ACCELERATOR_HEAD}.."
            f"{operator.SUPERVISOR_CALLBACK_CONTINUITY_ACCELERATOR_HEAD}",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    assert aggregate == [
        "ipfs_accelerate_py/agent_supervisor/runtime/"
        "multi_supervisor_runner.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_supervisor.py",
        "test/api/test_agent_supervisor_multi_supervisor_generation_status.py",
        "test/api/test_agent_supervisor_multi_supervisor_shutdown.py",
        "test/api/test_agent_supervisor_reconciliation_auto_unblock.py",
        "test/api/"
        "test_implementation_supervisor_control_plane_pool_lease.py",
    ]


def test_predecessor_and_restart_receipts_propagate_exact_successor() -> None:
    operator = _load_operator()
    predecessor_operator = inspect.getsource(
        operator._verified_database_lifecycle_identity_operator_descendant
    )
    predecessor_transition = inspect.getsource(
        operator._verified_database_lifecycle_identity_transition
    )
    admission = inspect.getsource(operator._owner_restart_admission)
    owner_receipt = inspect.getsource(operator._owner_restart_receipt)

    assert "_verified_supervisor_callback_continuity_operator_descendant" in (
        predecessor_operator
    )
    assert "_verified_supervisor_callback_continuity_transition" in (
        predecessor_transition
    )
    assert "if not exact_database_lifecycle_source" in predecessor_transition
    field = "supervisor_callback_continuity_transition_receipt_id"
    assert field in admission
    assert field in owner_receipt
