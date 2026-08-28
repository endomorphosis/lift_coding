"""The PCSM objective-refill fail-closed transition is exact and sealed."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = (
    ROOT
    / "scripts"
    / "run_agent_supervisor_proof_carrying_semantic_minification.py"
)
GENERATOR = (
    ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py"
)
VALIDATOR = (
    ROOT / "scripts/validate_proof_carrying_semantic_minification_board.py"
)


def _load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_operator():
    return _load_path("pcsm_objective_refill_fail_closed_operator", OPERATOR)


def _git_bytes(head: str, path: str | Path) -> bytes:
    relative = Path(path).as_posix()
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _module_from_source(name: str, source: bytes, path: Path):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _reseal_payload(operator, payload: dict[str, object]) -> None:
    body = dict(payload)
    body.pop("receipt_id", None)
    payload["receipt_id"] = operator._identity(body)


def _operator_gate_fixture(operator, monkeypatch: pytest.MonkeyPatch):
    checkpoint = "1" * 40
    checkpoint_tree = "2" * 40
    base = "3" * 40
    sealed = "4" * 40
    artifact = "5" * 40
    current = "6" * 40
    prior_artifact = "7" * 40
    prior_receipt_id = "sha256:" + "8" * 64
    relative_operator = Path(operator.__file__).resolve().relative_to(
        operator.ROOT
    ).as_posix()
    receipt_relative = (
        operator.OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "scripts/generate_proof_carrying_semantic_minification_board.py",
        relative_operator,
        "scripts/validate_proof_carrying_semantic_minification_board.py",
        "test/test_pcsm_objective_refill_fail_closed_transition.py",
    ]
    pending = (
        "PENDING_"
        + "OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"objective refill fail-closed operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    payload: dict[str, object] = {
        "schema": operator.OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_SCHEMA,
        "reason": "disable_unadmitted_objective_refill_fail_closed",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "prior_artifact_commit": prior_artifact,
            "database_projection_callback_identity_transition_receipt_id": (
                prior_receipt_id
            ),
            "changed_receipts": [],
        },
        "repair_base": {
            "source_head": base,
            "repository_tree_id": "base-tree",
            "parent": checkpoint,
            "operator_identity": operator._identity(base_operator),
            "config_identity": "sha256:" + "9" * 64,
            "generator_identity": "sha256:" + "a" * 64,
            "validator_identity": "sha256:" + "b" * 64,
            "changed_paths": base_paths,
        },
        "sealed_source": {
            "source_head": sealed,
            "repository_tree_id": "sealed-tree",
            "parent": base,
            "operator_identity": operator._identity(sealed_operator),
            "changed_paths": [relative_operator],
        },
        "source_forest": [],
        "disabled_refill_contract": {},
        "nonpromotion_contract": {},
        "validations": [],
        "post_integration_canonical_validation": {},
        "historical_receipts_preserved": True,
        "database_projection_callback_identity_receipt_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
        "manual_worktree_mutation": False,
    }
    _reseal_payload(operator, payload)
    state = {
        "payload": payload,
        "base_paths": list(base_paths),
        "base_parents": [checkpoint],
        "sealed_paths": [relative_operator],
        "sealed_parents": [base],
        "artifact_paths": [receipt_relative],
        "artifact_status": [f"A\t{receipt_relative}"],
        "artifact_parents": [sealed],
    }

    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_ARTIFACT_COMMIT",
        prior_artifact,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_RECEIPT_ID",
        prior_receipt_id,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_BASE_COMMIT",
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
            and path == operator.OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_PATH
        ):
            return receipt_bytes()
        raise AssertionError((head, path))

    monkeypatch.setattr(operator, "_git_blob_at", git_blob_at)

    def lines(values: list[str]) -> str:
        return "\n".join(values) + ("\n" if values else "")

    def git(*arguments, **_kwargs):
        command = tuple(arguments)
        mapping = {
            ("show", "-s", "--format=%P", base): lambda: " ".join(
                state["base_parents"]
            ),
            (
                "diff",
                "--name-only",
                f"{checkpoint}..{base}",
            ): lambda: lines(state["base_paths"]),
            ("show", "-s", "--format=%P", sealed): lambda: " ".join(
                state["sealed_parents"]
            ),
            (
                "diff",
                "--name-only",
                f"{base}..{sealed}",
            ): lambda: lines(state["sealed_paths"]),
            (
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            ): artifact + "\n",
            ("show", "-s", "--format=%P", artifact): lambda: " ".join(
                state["artifact_parents"]
            ),
            (
                "diff",
                "--name-only",
                f"{sealed}..{artifact}",
            ): lambda: lines(state["artifact_paths"]),
            (
                "diff",
                "--name-status",
                f"{sealed}..{artifact}",
            ): lambda: lines(state["artifact_status"]),
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


def test_static_config_accepts_only_exact_paired_boolean_transition() -> None:
    operator = _load_operator()
    bootstrap = json.loads(
        _git_bytes(
            operator.OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_HEAD,
            "config/proof_carrying_semantic_minification_v1_supervisor.json",
        )
    )
    current = copy.deepcopy(bootstrap)
    current["objective_refill_enabled"] = False
    current["objective_goal_refinement_enabled"] = False

    assert operator._verified_objective_refill_static_config_transition(
        bootstrap, current
    ) is True
    assert operator._verified_objective_refill_static_config_transition(
        bootstrap, bootstrap
    ) is False

    unpaired = copy.deepcopy(current)
    unpaired["objective_goal_refinement_enabled"] = True
    with pytest.raises(operator.OperatorError, match="exact paired transition"):
        operator._verified_objective_refill_static_config_transition(
            bootstrap, unpaired
        )

    non_boolean = copy.deepcopy(current)
    non_boolean["objective_refill_enabled"] = 0
    with pytest.raises(operator.OperatorError, match="exact booleans"):
        operator._verified_objective_refill_static_config_transition(
            bootstrap, non_boolean
        )

    unrelated = copy.deepcopy(current)
    unrelated["merge_retry_budget"] += 1
    with pytest.raises(operator.OperatorError, match="outside the admitted"):
        operator._verified_objective_refill_static_config_transition(
            bootstrap, unrelated
        )


def test_static_transition_and_successor_receipt_have_exact_parity() -> None:
    operator = _load_operator()
    receipt: dict[str, object] = {
        "schema": operator.OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_SCHEMA,
        "reason": "test-only-valid-identity",
    }
    receipt["receipt_id"] = operator._identity(receipt)
    transition = {"receipt": receipt}

    assert operator._verified_objective_refill_transition_parity(
        transition_required=False,
        transition={},
    ) == ""
    assert operator._verified_objective_refill_transition_parity(
        transition_required=True,
        transition=transition,
    ) == receipt["receipt_id"]
    with pytest.raises(operator.OperatorError, match="successor receipt differ"):
        operator._verified_objective_refill_transition_parity(
            transition_required=True,
            transition={},
        )
    with pytest.raises(operator.OperatorError, match="successor receipt differ"):
        operator._verified_objective_refill_transition_parity(
            transition_required=False,
            transition=transition,
        )


def test_operator_gate_rejects_payload_schema_and_receipt_id_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)

    state["payload"]["unbound_note"] = "outside the receipt schema"
    _reseal_payload(operator, state["payload"])
    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_objective_refill_fail_closed_operator_descendant(
            **kwargs
        )

    state["payload"].pop("unbound_note")
    _reseal_payload(operator, state["payload"])
    state["payload"]["receipt_id"] = "sha256:" + "0" * 64
    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_objective_refill_fail_closed_operator_descendant(
            **kwargs
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_base_path",
        "multiple_base_parents",
        "multiple_sealed_parents",
        "multiple_artifact_parents",
        "non_add_receipt",
    ],
)
def test_operator_gate_accepts_only_exact_b_s_a_shapes(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    operator = _load_operator()
    kwargs, state, artifact = _operator_gate_fixture(operator, monkeypatch)

    verified = operator._verified_objective_refill_fail_closed_operator_descendant(
        **kwargs
    )
    assert verified["artifact_commit"] == artifact

    if mutation == "foreign_base_path":
        state["base_paths"].append("scripts/foreign.py")
    elif mutation == "multiple_base_parents":
        state["base_parents"].append("9" * 40)
    elif mutation == "multiple_sealed_parents":
        state["sealed_parents"].append("9" * 40)
    elif mutation == "multiple_artifact_parents":
        state["artifact_parents"].append("9" * 40)
    elif mutation == "non_add_receipt":
        receipt_path = state["artifact_paths"][0]
        state["artifact_status"] = [f"M\t{receipt_path}"]
    else:  # pragma: no cover - the parametrization is closed above.
        raise AssertionError(mutation)

    with pytest.raises(operator.OperatorError, match="(delta|artifact commit) changed"):
        operator._verified_objective_refill_fail_closed_operator_descendant(
            **kwargs
        )


def test_checkpoint_binds_exact_nine_receipts_and_prior_seal() -> None:
    operator = _load_operator()
    checkpoint = operator.OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_HEAD
    prior_artifact = operator.OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_ARTIFACT_COMMIT
    expected = {
        "PCSM-066.json": (
            "bce73d98b75152707617bcd9ca67e27894fc704e6fdf0fba6107a201037cfa71"
        ),
        "PCSM-067.json": (
            "09274373cf2f947de5f0d3857dc0a150fe7e589b7ccd563044e980af3858aa7b"
        ),
        "PCSM-068.json": (
            "c8b49cbb1b01ff8242c434987a337ae74537129477877bc9e3b0718f44295b54"
        ),
        "PCSM-071.json": (
            "47d72c785e2543fffe22b688c2d46fe88399917c5376ab5c0d78c3fd0d17f85d"
        ),
        "PCSM-072.json": (
            "95b11da462105de2f62e2ce16f039fc47b43c366b61d602ea4731a811364c0fe"
        ),
        "PCSM-073.json": (
            "3fd4eab09c047dbf967f938089147c8fb4a32111c439234df018f67c4ff42e7d"
        ),
        "PCSM-074.json": (
            "0b88c46ba4f6326cbd0a1f9e395019739223095d01dafbc53b509f944e315752"
        ),
        "PCSM-075.json": (
            "4594a7bbd5d80e0cead7bcc1e6e965b645059a28b50547e56350b62a5441ce16"
        ),
        "PCSM-076.json": (
            "cce51ce588321e9fd488dca982ae9f930b6c320f46f321b53f16d7b939158728"
        ),
    }
    prefix = "artifacts/proof_carrying_semantic_minification/receipts/"
    expected_paths = [prefix + name for name in expected]
    tree = subprocess.run(
        ["git", "rev-parse", f"{checkpoint}^{{tree}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-status", f"{prior_artifact}..{checkpoint}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()

    assert checkpoint == "f50c905534c94aa23289b7e8f4d8fc96f8896dcd"
    assert tree == "dafe6456f45dc32c6de8737a7327be40c0ddbdb1"
    assert tree == operator.OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_TREE
    assert changed == [f"A\t{path}" for path in expected_paths]
    for path, digest in zip(expected_paths, expected.values(), strict=True):
        assert hashlib.sha256(_git_bytes(checkpoint, path)).hexdigest() == digest

    prior_path = (
        "artifacts/proof_carrying_semantic_minification/handoff/"
        "supervisor-restart-database-projection-callback-identity-transition.json"
    )
    prior_bytes = _git_bytes(prior_artifact, prior_path)
    assert _git_bytes(checkpoint, prior_path) == prior_bytes
    assert hashlib.sha256(prior_bytes).hexdigest() == (
        "993be35843d8d76f8cd427f6d21d295e00963ca75b636e771fc586248eb32031"
    )
    assert json.loads(prior_bytes)["receipt_id"] == (
        operator.OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_RECEIPT_ID
    )


def test_only_refill_configuration_changes_protected_board_generation() -> None:
    operator = _load_operator()
    generator = _load_path("pcsm_objective_refill_generator", GENERATOR)
    validator = _load_path("pcsm_objective_refill_validator", VALIDATOR)
    checkpoint = operator.OBJECTIVE_REFILL_FAIL_CLOSED_CHECKPOINT_HEAD
    checkpoint_config_bytes = _git_bytes(
        checkpoint,
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
    )
    expected_config_bytes = checkpoint_config_bytes.replace(
        b'"objective_refill_enabled": true,',
        b'"objective_refill_enabled": false,',
        1,
    ).replace(
        b'"objective_goal_refinement_enabled": true,',
        b'"objective_goal_refinement_enabled": false,',
        1,
    )
    assert (
        ROOT
        / "config/proof_carrying_semantic_minification_v1_supervisor.json"
    ).read_bytes() == expected_config_bytes
    config = json.loads(
        (
            ROOT
            / "config/proof_carrying_semantic_minification_v1_supervisor.json"
        ).read_bytes()
    )
    generated_config = generator.render_config()
    validator_source = inspect.getsource(validator.validate)

    for field in (
        "objective_refill_enabled",
        "objective_goal_refinement_enabled",
    ):
        assert config[field] is False
        assert generated_config[field] is False
        assert f'config.get("{field}") is not False' in validator_source

    checkpoint_generator = _module_from_source(
        "pcsm_checkpoint_objective_refill_generator",
        _git_bytes(checkpoint, GENERATOR.relative_to(ROOT)),
        GENERATOR,
    )
    assert generator.render_plan() == checkpoint_generator.render_plan()
    assert generator.render_plan() == generator.PLAN_PATH.read_text(encoding="utf-8")

    immutable_paths = (
        generator.PLAN_PATH,
        generator.BOARD_PATH,
        generator.OBJECTIVES_PATH,
    )
    for path in immutable_paths:
        assert path.read_bytes() == _git_bytes(checkpoint, path.relative_to(ROOT))


def test_predecessor_and_restart_receipts_propagate_exact_successor() -> None:
    operator = _load_operator()
    predecessor_operator = inspect.getsource(
        operator._verified_database_projection_callback_identity_operator_descendant
    )
    predecessor_transition = inspect.getsource(
        operator._verified_database_projection_callback_identity_transition
    )
    full_transition = inspect.getsource(
        operator._verified_objective_refill_fail_closed_transition
    )
    admission = inspect.getsource(operator._owner_restart_admission)
    owner_receipt = inspect.getsource(operator._owner_restart_receipt)

    successor = "_verified_objective_refill_fail_closed"
    assert successor + "_operator_descendant" in predecessor_operator
    assert successor + "_transition" in predecessor_transition
    assert "if not exact_database_projection_callback_identity_source" in (
        predecessor_transition
    )
    assert "_verified_objective_refill_static_config_transition" in full_transition
    assert '"disabled_refill_contract"' in full_transition
    assert '"nonpromotion_contract"' in full_transition
    old_field = "database_projection_callback_identity_transition_receipt_id"
    new_field = "objective_refill_fail_closed_transition_receipt_id"
    assert old_field in full_transition
    assert old_field in admission
    assert old_field in owner_receipt
    assert new_field in admission
    assert new_field in owner_receipt


def test_configured_launch_plan_omits_objective_refill_scan() -> None:
    operator = _load_operator()
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        configured_board_launch_plan,
    )

    board, _config = operator._load_config(operator.DEFAULT_CONFIG)
    plan = configured_board_launch_plan(
        board,
        implement=True,
        detach=False,
        duration_seconds=float("inf"),
    )

    assert "--common-arg=--objective-refill-scan" not in plan["argv"]


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

    verified = operator._verified_objective_refill_fail_closed_transition(
        board=board,
        current_head=current_head,
        current_config=current_config,
        current_source_identities=current_source_identities,
        prior_artifact_commit=(
            operator.OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_ARTIFACT_COMMIT
        ),
        prior_transition_receipt_id=(
            operator.OBJECTIVE_REFILL_FAIL_CLOSED_PRIOR_RECEIPT_ID
        ),
    )
    receipt_path = (
        operator.OBJECTIVE_REFILL_FAIL_CLOSED_TRANSITION_PATH.relative_to(ROOT)
    )
    artifact_commit = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            receipt_path.as_posix(),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()

    assert len(artifact_commit) == 1
    assert verified["artifact_commit"] == artifact_commit[0]
    assert verified["receipt"]["receipt_id"].startswith("sha256:")
