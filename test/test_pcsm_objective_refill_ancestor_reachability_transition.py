"""The PCSM objective-refill ancestor reachability repair is exact."""

from __future__ import annotations

import ast
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
TEST_RELATIVE = (
    "test/test_pcsm_objective_refill_ancestor_reachability_transition.py"
)
PRIOR_RECEIPT_RELATIVE = (
    "artifacts/proof_carrying_semantic_minification/handoff/"
    "supervisor-restart-objective-refill-fail-closed-transition.json"
)
PRIOR_RECEIPT_BYTES_ID = (
    "sha256:0c29b51a34c03d932d5498e08a9441acfd48087c30a132989773ad906410ed96"
)


def _load_operator():
    spec = importlib.util.spec_from_file_location(
        "pcsm_objective_refill_ancestor_reachability_operator",
        OPERATOR,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_bytes(head: str, path: str | Path) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{Path(path).as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _reseal_payload(operator, payload: dict[str, object]) -> None:
    body = dict(payload)
    body.pop("receipt_id", None)
    payload["receipt_id"] = operator._identity(body)


def _authority_guard_code(function) -> object:
    """Compile the actual authority guard statements for behavioral tests."""

    parsed = ast.parse(inspect.getsource(function))
    definition = parsed.body[0]
    assert isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef))
    for index, statement in enumerate(definition.body):
        if not isinstance(statement, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name)
            and target.id == "immutable_source_names"
            for target in statement.targets
        ):
            fragment = definition.body[index : index + 3]
            assert len(fragment) == 3
            assert isinstance(fragment[1], ast.If)
            assert isinstance(fragment[2], ast.For)
            module = ast.fix_missing_locations(
                ast.Module(body=fragment, type_ignores=[])
            )
            return compile(module, str(OPERATOR), "exec")
    raise AssertionError("immutable authority guard is absent")


def _assert_exact_child_mapping(
    function,
    *,
    child_mapping: str,
    child_verifier: str,
) -> None:
    """Bind the nonempty mapping to the exact verified successor call."""

    parsed = ast.parse(inspect.getsource(function))
    definition = parsed.body[0]
    assert isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef))
    initialized_empty = False
    assigned_by_verifier = False
    for node in ast.walk(definition):
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == child_mapping
            for target in targets
        ):
            continue
        if isinstance(value, ast.Dict) and not value.keys:
            initialized_empty = True
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == child_verifier
        ):
            assigned_by_verifier = True
    assert initialized_empty
    assert assigned_by_verifier


def _run_authority_guard(
    operator,
    *,
    code: object,
    child_mapping: str,
    checkpoint_symbol: str,
    child: dict[str, object],
    drift: str,
) -> None:
    source_paths = {
        name: Path(f"fixture_{name}.md")
        for name in ("taskboard", "objectives", "plan", "generator")
    }
    checkpoint_bytes = {
        path: f"sealed {name}".encode()
        for name, path in source_paths.items()
    }
    current_bytes = dict(checkpoint_bytes)
    current_bytes[source_paths[drift]] = f"drifted {drift}".encode()
    namespace = {
        child_mapping: child,
        checkpoint_symbol: "checkpoint",
        "source_paths": source_paths,
        "current_head": "current",
        "current_source_identities": {
            name: operator._identity(current_bytes[path])
            for name, path in source_paths.items()
        },
        "_git_blob_at": lambda *, head, path, field: checkpoint_bytes[path],
        "_tracked_bytes": lambda path, **_kwargs: current_bytes[path],
        "_identity": operator._identity,
        "OperatorError": operator.OperatorError,
    }
    exec(code, namespace)


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
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_TRANSITION_PATH.relative_to(
            operator.ROOT
        ).as_posix()
    )
    base_paths = [relative_operator, TEST_RELATIVE]
    base_status = [f"M\t{relative_operator}", f"A\t{TEST_RELATIVE}"]
    sealed_paths = [relative_operator]
    sealed_status = [f"M\t{relative_operator}"]
    artifact_paths = [receipt_relative]
    artifact_status = [f"A\t{receipt_relative}"]
    pending = (
        "PENDING_"
        + "OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_TRANSITION_BASE_COMMIT"
    ).encode()
    base_operator = b"objective refill ancestor operator " + pending + b"\n"
    sealed_operator = base_operator.replace(pending, base.encode(), 1)
    base_test = b"objective refill ancestor focused test\n"
    prior_receipt_bytes = _git_bytes(
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_HEAD,
        PRIOR_RECEIPT_RELATIVE,
    )
    assert operator._identity(prior_receipt_bytes) == PRIOR_RECEIPT_BYTES_ID

    payload: dict[str, object] = {
        "schema": (
            operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_TRANSITION_SCHEMA
        ),
        "reason": "repair_ancestor_generator_reachability",
        "prior_checkpoint": {
            "source_head": checkpoint,
            "repository_tree_id": checkpoint_tree,
            "objective_refill_fail_closed_transition_receipt_id": (
                operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_PRIOR_RECEIPT_ID
            ),
            "objective_refill_fail_closed_transition_receipt_bytes_id": (
                PRIOR_RECEIPT_BYTES_ID
            ),
        },
        "repair_base": {
            "source_head": base,
            "repository_tree_id": "base-tree",
            "parent": checkpoint,
            "operator_identity": operator._identity(base_operator),
            "test_identity": operator._identity(base_test),
            "changed_paths": list(base_paths),
            "changed_status": list(base_status),
        },
        "sealed_source": {
            "source_head": sealed,
            "repository_tree_id": "sealed-tree",
            "parent": base,
            "operator_identity": operator._identity(sealed_operator),
            "changed_paths": list(sealed_paths),
            "changed_status": list(sealed_status),
        },
        "reachability_contract": {},
        "validations": [],
        "post_integration_canonical_validation": {},
        "historical_receipts_preserved": True,
        "objective_refill_fail_closed_receipt_preserved": True,
        "database_authority_preserved": True,
        "task_state_mutation": False,
        "manual_database_mutation": False,
        "manual_worktree_mutation": False,
    }
    _reseal_payload(operator, payload)
    state = {
        "payload": payload,
        "base_paths": base_paths,
        "base_status": base_status,
        "base_parents": [checkpoint],
        "sealed_paths": sealed_paths,
        "sealed_status": sealed_status,
        "sealed_parents": [base],
        "artifact_paths": artifact_paths,
        "artifact_status": artifact_status,
        "artifact_parents": [sealed],
    }

    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_HEAD",
        checkpoint,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_TREE",
        checkpoint_tree,
    )
    monkeypatch.setattr(
        operator,
        "OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_TRANSITION_BASE_COMMIT",
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
        relative = Path(path).resolve().relative_to(operator.ROOT).as_posix()
        if head == checkpoint and relative == PRIOR_RECEIPT_RELATIVE:
            return prior_receipt_bytes
        if head == base and relative == relative_operator:
            return base_operator
        if head == base and relative == TEST_RELATIVE:
            return base_test
        if head == sealed and relative == relative_operator:
            return sealed_operator
        if head == artifact and relative == receipt_relative:
            return receipt_bytes()
        raise AssertionError((head, relative))

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
            (
                "diff",
                "--name-status",
                f"{checkpoint}..{base}",
            ): lambda: lines(state["base_status"]),
            ("show", "-s", "--format=%P", sealed): lambda: " ".join(
                state["sealed_parents"]
            ),
            (
                "diff",
                "--name-only",
                f"{base}..{sealed}",
            ): lambda: lines(state["sealed_paths"]),
            (
                "diff",
                "--name-status",
                f"{base}..{sealed}",
            ): lambda: lines(state["sealed_status"]),
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


def test_operator_gate_rejects_payload_schema_and_cid_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    kwargs, state, _artifact = _operator_gate_fixture(operator, monkeypatch)

    state["payload"]["unbound_note"] = "outside the receipt schema"
    _reseal_payload(operator, state["payload"])
    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_objective_refill_ancestor_reachability_operator_descendant(
            **kwargs
        )

    state["payload"].pop("unbound_note")
    _reseal_payload(operator, state["payload"])
    state["payload"]["receipt_id"] = "sha256:" + "0" * 64
    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_objective_refill_ancestor_reachability_operator_descendant(
            **kwargs
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "base_parent",
        "base_path",
        "base_status",
        "sealed_parent",
        "sealed_path",
        "sealed_status",
        "artifact_parent",
        "artifact_path",
        "artifact_status",
    ],
)
def test_operator_gate_accepts_only_exact_b2_s2_a2_shapes(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    operator = _load_operator()
    kwargs, state, artifact = _operator_gate_fixture(operator, monkeypatch)

    verified = (
        operator._verified_objective_refill_ancestor_reachability_operator_descendant(
            **kwargs
        )
    )
    assert verified["artifact_commit"] == artifact

    if mutation == "base_parent":
        state["base_parents"].append("9" * 40)
    elif mutation == "base_path":
        state["base_paths"].append("scripts/foreign.py")
    elif mutation == "base_status":
        state["base_status"][1] = f"M\t{TEST_RELATIVE}"
    elif mutation == "sealed_parent":
        state["sealed_parents"].append("9" * 40)
    elif mutation == "sealed_path":
        state["sealed_paths"].append(TEST_RELATIVE)
    elif mutation == "sealed_status":
        state["sealed_status"][0] = f"A\t{state['sealed_paths'][0]}"
    elif mutation == "artifact_parent":
        state["artifact_parents"].append("9" * 40)
    elif mutation == "artifact_path":
        state["artifact_paths"].append("artifacts/foreign.json")
    elif mutation == "artifact_status":
        receipt_path = state["artifact_paths"][0]
        state["artifact_status"][0] = f"M\t{receipt_path}"
    else:  # pragma: no cover - the parametrization is closed above.
        raise AssertionError(mutation)

    with pytest.raises(operator.OperatorError):
        operator._verified_objective_refill_ancestor_reachability_operator_descendant(
            **kwargs
        )


def test_checkpoint_is_exact_objective_refill_artifact() -> None:
    operator = _load_operator()
    checkpoint = (
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_HEAD
    )
    tree = subprocess.run(
        ["git", "rev-parse", f"{checkpoint}^{{tree}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    receipt_bytes = _git_bytes(checkpoint, PRIOR_RECEIPT_RELATIVE)
    receipt = json.loads(receipt_bytes)

    assert checkpoint == "624cdc178df4305628c236b823853a030898ed99"
    assert tree == "4261e0ee6a5a81166ff203d4f5967f55fe055132"
    assert tree == (
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_TREE
    )
    assert "sha256:" + hashlib.sha256(receipt_bytes).hexdigest() == (
        PRIOR_RECEIPT_BYTES_ID
    )
    assert receipt["receipt_id"] == (
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_PRIOR_RECEIPT_ID
    )


@pytest.mark.parametrize(
    (
        "function_name",
        "child_mapping",
        "child_verifier",
        "checkpoint_symbol",
    ),
    [
        (
            "_verified_validation_path_compatibility_transition",
            "database_watchdog_activity_transition",
            "_verified_database_watchdog_activity_transition",
            "VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD",
        ),
        (
            "_verified_database_watchdog_activity_transition",
            "database_lifecycle_identity_transition",
            "_verified_database_lifecycle_identity_transition",
            "DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD",
        ),
        (
            "_verified_database_lifecycle_identity_transition",
            "supervisor_callback_continuity_transition",
            "_verified_supervisor_callback_continuity_transition",
            "DATABASE_LIFECYCLE_IDENTITY_CHECKPOINT_HEAD",
        ),
        (
            "_verified_supervisor_callback_continuity_transition",
            "database_projection_callback_identity_transition",
            "_verified_database_projection_callback_identity_transition",
            "SUPERVISOR_CALLBACK_CONTINUITY_CHECKPOINT_HEAD",
        ),
    ],
)
def test_ancestor_guards_preserve_authority_and_delegate_generator(
    function_name: str,
    child_mapping: str,
    child_verifier: str,
    checkpoint_symbol: str,
) -> None:
    operator = _load_operator()
    function = getattr(operator, function_name)
    source = inspect.getsource(function)
    _assert_exact_child_mapping(
        function,
        child_mapping=child_mapping,
        child_verifier=child_verifier,
    )

    unconditional = (
        'immutable_source_names = ("taskboard", "objectives", "plan")'
    )
    conditional = f"if not {child_mapping}:"
    generator = 'immutable_source_names += ("generator",)'
    assert child_verifier in source
    assert unconditional in source
    assert conditional in source
    assert generator in source
    assert source.index(unconditional) < source.index(conditional)
    assert source.index(conditional) < source.index(generator)
    assert source.index(generator) < source.index(
        "for name in immutable_source_names:"
    )
    code = _authority_guard_code(function)

    with pytest.raises(operator.OperatorError):
        _run_authority_guard(
            operator,
            code=code,
            child_mapping=child_mapping,
            checkpoint_symbol=checkpoint_symbol,
            child={},
            drift="generator",
        )
    _run_authority_guard(
        operator,
        code=code,
        child_mapping=child_mapping,
        checkpoint_symbol=checkpoint_symbol,
        child={"receipt": {"receipt_id": "sha256:" + "7" * 64}},
        drift="generator",
    )
    for protected_name in ("taskboard", "objectives", "plan"):
        with pytest.raises(operator.OperatorError):
            _run_authority_guard(
                operator,
                code=code,
                child_mapping=child_mapping,
                checkpoint_symbol=checkpoint_symbol,
                child={"receipt": {"receipt_id": "sha256:" + "7" * 64}},
                drift=protected_name,
            )


def test_transition_and_restart_receipts_propagate_exact_successor() -> None:
    operator = _load_operator()
    predecessor_operator = inspect.getsource(
        operator._verified_objective_refill_fail_closed_operator_descendant
    )
    predecessor_transition = inspect.getsource(
        operator._verified_objective_refill_fail_closed_transition
    )
    full_transition = inspect.getsource(
        operator._verified_objective_refill_ancestor_reachability_transition
    )
    admission = inspect.getsource(operator._owner_restart_admission)
    owner_receipt = inspect.getsource(operator._owner_restart_receipt)

    successor = "_verified_objective_refill_ancestor_reachability"
    nested_key = "objective_refill_ancestor_reachability_transition"
    old_field = "objective_refill_fail_closed_transition_receipt_id"
    new_field = nested_key + "_receipt_id"
    assert successor + "_operator_descendant" in predecessor_operator
    assert successor + "_transition" in predecessor_transition
    assert nested_key in predecessor_operator
    assert nested_key in predecessor_transition
    assert "if not exact_objective_refill_fail_closed_source" in (
        predecessor_transition
    )
    assert '"reachability_contract"' in full_transition
    assert old_field in full_transition
    assert old_field in admission
    assert old_field in owner_receipt
    assert new_field in admission
    assert new_field in owner_receipt


def test_current_transition_receipt_passes_exact_read_only_verifier() -> None:
    operator = _load_operator()
    receipt_path = (
        operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_TRANSITION_PATH.relative_to(
            ROOT
        )
    )
    artifact_commits = subprocess.run(
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
    if not artifact_commits:
        pytest.skip("canonical verifier is gated on the add-only A2 receipt")

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
    verified = (
        operator._verified_objective_refill_ancestor_reachability_transition(
            board=board,
            current_head=current_head,
            current_config=current_config,
            current_source_identities=current_source_identities,
            prior_artifact_commit=(
                operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_CHECKPOINT_HEAD
            ),
            prior_transition_receipt_id=(
                operator.OBJECTIVE_REFILL_ANCESTOR_REACHABILITY_PRIOR_RECEIPT_ID
            ),
        )
    )

    assert len(artifact_commits) == 1
    assert verified["artifact_commit"] == artifact_commits[0]
    assert verified["receipt"]["receipt_id"].startswith("sha256:")
