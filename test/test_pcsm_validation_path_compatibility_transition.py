"""The PCSM validation-path transition is exact and fail-closed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = (
    ROOT
    / "scripts"
    / "run_agent_supervisor_proof_carrying_semantic_minification.py"
)


def _load_operator():
    spec = importlib.util.spec_from_file_location(
        "pcsm_validation_path_operator",
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
        operator.VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_validation_path_compatibility_transition.py",
    ]
    pending = (
        "PENDING_" + "VALIDATION_PATH_COMPATIBILITY_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"validation path operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    payload = {
        "schema": operator.VALIDATION_PATH_COMPATIBILITY_TRANSITION_SCHEMA,
        "reason": "restore_declared_agent_supervisor_validation_path",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "prior_artifact_commit": (
                "9b056251a42aac444478745b3ccb73e3507215e8"
            ),
            "stale_worktree_cleanup_transition_receipt_id": (
                "sha256:4d86e1fa4452a720859175d2e228dd09f50f92159577154f"
                "96ade16cb6e5e0b7"
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
            "accelerator_head": operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "accelerator_tree": operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE,
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
        "validation_surface": {},
        "validations": [],
        "historical_receipts_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
    }
    payload["receipt_id"] = operator._identity(payload)
    state = {
        "payload": payload,
        "base_paths": list(base_paths),
    }

    monkeypatch.setattr(
        operator,
        "VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "VALIDATION_PATH_COMPATIBILITY_TRANSITION_BASE_COMMIT",
        base,
    )

    def receipt_bytes() -> bytes:
        return json.dumps(state["payload"], sort_keys=True).encode()

    monkeypatch.setattr(
        operator,
        "_tracked_bytes",
        lambda path, **_kwargs: receipt_bytes(),
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
        if head == artifact and path == (
            operator.VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH
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
    monkeypatch.setattr(operator, "_git_is_ancestor", lambda *_args, **_kwargs: None)
    kwargs = {
        "current_operator": sealed_operator,
        "current_head": current,
        "operator_path": Path(operator.__file__).resolve(),
    }
    return kwargs, state, artifact


def test_operator_descendant_accepts_only_the_direct_sealed_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, artifact = _operator_gate_fixture(operator, monkeypatch)

    verified = operator._verified_validation_path_compatibility_operator_descendant(
        **kwargs
    )
    assert verified["artifact_commit"] == artifact

    state["base_paths"].append("scripts/foreign.py")
    with pytest.raises(
        operator.OperatorError,
        match="operator delta changed",
    ):
        operator._verified_validation_path_compatibility_operator_descendant(
            **kwargs
        )


def test_transition_payload_rejects_unbound_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)
    state["payload"]["unbound_note"] = "outside the receipt schema"

    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_validation_path_compatibility_operator_descendant(
            **kwargs
        )


def _full_transition_fixture(operator, monkeypatch: pytest.MonkeyPatch):
    checkpoint = operator.VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD
    base = "a" * 40
    sealed = "b" * 40
    artifact = "c" * 40
    current = "d" * 40
    prior_artifact = "9b056251a42aac444478745b3ccb73e3507215e8"
    prior_transition_id = (
        "sha256:4d86e1fa4452a720859175d2e228dd09f50f92159577154f"
        "96ade16cb6e5e0b7"
    )
    config_path = operator.ROOT / "config/fixture.json"
    validator_path = operator.ROOT / "scripts/fixture_validator.py"
    taskboard_path = Path("implementation_plan/fixture_tasks.md")
    objectives_path = Path("implementation_plan/fixture_objectives.md")
    plan_path = Path("implementation_plan/fixture_plan.md")
    board = SimpleNamespace(
        config_path=config_path,
        validator_path=Path("scripts/fixture_validator.py"),
        taskboard_path=taskboard_path,
        objectives_path=objectives_path,
        plan_path=plan_path,
        path=lambda value: operator.ROOT / value,
    )
    source_paths = operator._restart_source_paths(board)
    prior_config = {
        "max_task_attempts": 3,
        "source_binding": {
            "accelerator_planning_revision": "legacy-head",
            "accelerator_planning_tree": "legacy-tree",
            "ipfs_accelerate_planning_revision": (
                operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
            ),
            "ipfs_accelerate_planning_tree": (
                operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
            ),
        },
    }
    base_config = json.loads(json.dumps(prior_config))
    base_config["source_binding"]["ipfs_accelerate_planning_revision"] = (
        operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
    )
    base_config["source_binding"]["ipfs_accelerate_planning_tree"] = (
        operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE
    )
    prior_config_bytes = json.dumps(prior_config, sort_keys=True).encode()
    base_config_bytes = json.dumps(base_config, sort_keys=True).encode()
    prior_operator = b"stale cleanup sealed operator\n"
    base_operator = b"validation compatibility base operator\n"
    sealed_operator = b"validation compatibility sealed operator\n"
    validator = b"board validator\n"
    transition_test = b"focused transition test\n"
    static_bytes = {
        name: f"{name} source\n".encode()
        for name in ("taskboard", "objectives", "plan", "generator")
    }
    receipt_blobs = {
        "PCSM-020.json": b"receipt 020\n",
        "PCSM-021.json": b"receipt 021\n",
        "PCSM-022.json": b"receipt 022\n",
    }
    fixed_identities = {
        prior_config_bytes: (
            "sha256:5f4222672c5da4a409fdd8428d8de588126848a986dbd4a8"
            "ec0ff9435bb0000a"
        ),
        prior_operator: (
            "sha256:c6fcfa916619bd6692f0299d9988671ae67c1e83c4bb45640"
            "d3c84218534bf72"
        ),
        validator: (
            "sha256:57e3b957019ef0ee20cee5d2f50a7bfb5b1172ea8ee04db8"
            "9a3426d28a290e89"
        ),
        receipt_blobs["PCSM-020.json"]: (
            "sha256:88c0bfe17eed6e9f01cc9d14832f8d23de31e436ab31a8e0"
            "a3d732f59a10b695"
        ),
        receipt_blobs["PCSM-021.json"]: (
            "sha256:6a4a3a64ddc6ed552a3c3fcecf5931ec3a396e02c91a813a"
            "8e793341ae071127"
        ),
        receipt_blobs["PCSM-022.json"]: (
            "sha256:b7fe0f17fcc708f1e09f65de233c00b4019f037b08937502a"
            "2fcc88dd67b14d2"
        ),
    }
    real_identity = operator._identity

    def identity(value):
        if isinstance(value, bytes) and value in fixed_identities:
            return fixed_identities[value]
        return real_identity(value)

    monkeypatch.setattr(operator, "_identity", identity)

    checkpoint_receipts = [
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                f"PCSM-{number}.json"
            ),
            "bytes_id": fixed_identities[receipt_blobs[f"PCSM-{number}.json"]],
        }
        for number in ("020", "021", "022")
    ]
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "test/test_pcsm_validation_path_compatibility_transition.py",
    ]
    nested_paths = [
        "ipfs_accelerate_py/agent_supervisor/tests/"
        "proof_carrying_semantic_minification/test_structured_decoding.py",
        "test/agent_supervisor/pcsm",
    ]
    product_root = (
        "ipfs_accelerate_py/agent_supervisor/tests/"
        "proof_carrying_semantic_minification"
    )
    validations = [
        {
            "cwd": ".",
            "command": [
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_accelerate/test/agent_supervisor",
            ],
            "outcome": "passed",
            "summary": "11 passed in 0.10s",
        },
        {
            "cwd": ".",
            "command": [
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_validation_path_compatibility_transition.py",
            ],
            "outcome": "passed",
            "summary": "4 passed in 0.08s",
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
        "schema": operator.VALIDATION_PATH_COMPATIBILITY_TRANSITION_SCHEMA,
        "reason": "restore_declared_agent_supervisor_validation_path",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": (
                operator.VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE
            ),
            "prior_artifact_commit": prior_artifact,
            "stale_worktree_cleanup_transition_receipt_id": prior_transition_id,
            "changed_receipts": checkpoint_receipts,
        },
        "repair_base": {
            "source_head": base,
            "repository_tree_id": "base-tree",
            "parent": checkpoint,
            "operator_identity": identity(base_operator),
            "config_identity": identity(base_config_bytes),
            "validator_identity": identity(validator),
            "accelerator_head": operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "accelerator_tree": operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE,
            "changed_paths": base_paths,
            "nested_changed_paths": nested_paths,
        },
        "sealed_source": {
            "source_head": sealed,
            "repository_tree_id": "sealed-tree",
            "parent": base,
            "operator_identity": identity(sealed_operator),
            "changed_paths": [
                "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py"
            ],
        },
        "validation_surface": {
            "declared_command": validations[0]["command"],
            "declared_path": "external/ipfs_accelerate/test/agent_supervisor",
            "nested_bridge_path": "test/agent_supervisor/pcsm",
            "nested_bridge_kind": "relative_directory_symlink",
            "nested_bridge_target": (
                "../../ipfs_accelerate_py/agent_supervisor/tests/"
                "proof_carrying_semantic_minification"
            ),
            "product_test_root": product_root,
            "minimum_collected_tests": 11,
            "taskboard_validation_changed": False,
            "generator_validation_changed": False,
        },
        "validations": validations,
        "historical_receipts_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
        "receipt_id": "sha256:" + "e" * 64,
    }
    gate = {
        "receipt": payload,
        "receipt_bytes": b"receipt\n",
        "artifact_commit": artifact,
        "base_commit": base,
        "base_operator": base_operator,
        "sealed_source_head": sealed,
        "sealed_source_tree": "sealed-tree",
        "expected_operator": sealed_operator,
    }
    monkeypatch.setattr(
        operator,
        "_verified_validation_path_compatibility_operator_descendant",
        lambda **_kwargs: gate,
    )
    transition_test_path = (
        operator.ROOT / "test/test_pcsm_validation_path_compatibility_transition.py"
    )
    tracked = {
        config_path: base_config_bytes,
        Path(operator.__file__).resolve(): sealed_operator,
        validator_path: validator,
        transition_test_path: transition_test,
        **{source_paths[name]: value for name, value in static_bytes.items()},
    }
    monkeypatch.setattr(
        operator,
        "_tracked_bytes",
        lambda path, **_kwargs: tracked[path],
    )

    checkpoint_blobs = {
        config_path: prior_config_bytes,
        Path(operator.__file__).resolve(): prior_operator,
        validator_path: validator,
        **{source_paths[name]: value for name, value in static_bytes.items()},
    }

    def git_blob_at(*, head, path, field):
        del field
        if head == checkpoint and path in checkpoint_blobs:
            return checkpoint_blobs[path]
        if head == checkpoint and path.name in receipt_blobs:
            return receipt_blobs[path.name]
        if head == base and path == config_path:
            return base_config_bytes
        if head == base and path == validator_path:
            return validator
        if head == base and path == transition_test_path:
            return transition_test
        raise AssertionError((head, path))

    monkeypatch.setattr(operator, "_git_blob_at", git_blob_at)
    monkeypatch.setattr(
        operator,
        "_git_commit_tree",
        lambda commit, **_kwargs: {
            checkpoint: operator.VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE,
            operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD: (
                operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE
            ),
        }[commit],
    )
    monkeypatch.setattr(operator, "_git_is_ancestor", lambda *_args, **_kwargs: None)

    checkpoint_paths = "\n".join(item["path"] for item in checkpoint_receipts) + "\n"

    def git(*arguments, **_kwargs):
        command = tuple(arguments)
        if command == (
            "diff",
            "--name-only",
            f"{prior_artifact}..{checkpoint}",
        ):
            return checkpoint_paths
        if command in {
            ("ls-tree", base, "--", "external/ipfs_accelerate"),
            ("ls-tree", current, "--", "external/ipfs_accelerate"),
        }:
            return (
                "160000 commit "
                f"{operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}"
                "\texternal/ipfs_accelerate\n"
            )
        raise AssertionError(command)

    monkeypatch.setattr(operator, "_git", git)
    state = {"bridge_mode": "120000"}
    bridge_path = "test/agent_supervisor/pcsm"
    product_module = f"{product_root}/test_structured_decoding.py"

    def nested_git(_repository, *arguments, binary=False):
        command = tuple(arguments)
        if command == (
            "show",
            "-s",
            "--format=%P",
            operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
        ):
            return operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD + "\n"
        if command == (
            "diff",
            "--name-only",
            f"{operator.STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD}.."
            f"{operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}",
        ):
            return "\n".join(nested_paths) + "\n"
        tree_entries = {
            (
                "ls-tree",
                operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
                "--",
                bridge_path,
            ): (
                f"{state['bridge_mode']} blob "
                "302b67f7129dcafc103c6414e027f8b67f541b0d\t"
                f"{bridge_path}\n"
            ),
            (
                "ls-tree",
                operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
                "--",
                "test/agent_supervisor",
            ): "040000 tree 1\ttest/agent_supervisor\n",
            (
                "ls-tree",
                operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
                "--",
                product_root,
            ): f"040000 tree 2\t{product_root}\n",
            (
                "ls-tree",
                operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
                "--",
                product_module,
            ): (
                "100644 blob c25192cb06f20469093e9fc53e4e35d0c1ae171e\t"
                f"{product_module}\n"
            ),
        }
        if command in tree_entries:
            return tree_entries[command]
        if command == (
            "show",
            f"{operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}:"
            f"{bridge_path}",
        ):
            assert binary
            return (
                b"../../ipfs_accelerate_py/agent_supervisor/tests/"
                b"proof_carrying_semantic_minification"
            )
        if command == (
            "show",
            f"{operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}:"
            f"{product_module}",
        ):
            assert binary
            return b"def test_contract(): pass\n"
        raise AssertionError(command)

    monkeypatch.setattr(operator, "_git_in_repository", nested_git)
    current_identities = {
        "config": identity(base_config_bytes),
        "operator": identity(sealed_operator),
        "validator": identity(validator),
        **{name: identity(value) for name, value in static_bytes.items()},
    }
    kwargs = {
        "board": board,
        "current_head": current,
        "current_config": base_config,
        "current_source_identities": current_identities,
        "prior_artifact_commit": prior_artifact,
        "prior_transition_receipt_id": prior_transition_id,
        "prior_config_bytes": prior_config_bytes,
        "prior_operator_bytes": prior_operator,
        "prior_validator_bytes": validator,
    }
    return kwargs, state, artifact


def test_full_transition_accepts_exact_config_nested_path_and_validations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, _state, artifact = _full_transition_fixture(operator, monkeypatch)

    verified = operator._verified_validation_path_compatibility_transition(
        **kwargs
    )

    assert verified["artifact_commit"] == artifact
    assert verified["accelerator_head"] == (
        operator.VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
    )


def test_full_transition_rejects_non_symlink_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _full_transition_fixture(operator, monkeypatch)
    state["bridge_mode"] = "100644"

    with pytest.raises(operator.OperatorError, match="nested path contract changed"):
        operator._verified_validation_path_compatibility_transition(**kwargs)
