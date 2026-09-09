"""A source transition preserves the admitted board and historical seal."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SPEC = importlib.util.spec_from_file_location(
    "pcpr_operator_test",
    Path(__file__).parents[1]
    / "run_agent_supervisor_proof_carrying_platform_qualification_and_release.py",
)
OPERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPERATOR)


def fixture(tmp_path):
    config = dict(
        taskboard_path="todo.md",
        objectives_path="objectives.md",
        plan_path="plan.md",
        authority_policy={"duckdb": True},
        source_binding={"old": "seal"},
    )
    path = tmp_path / OPERATOR.DEFAULT_CONFIG
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({**config, "source_binding": {"new": "descendant"}}))
    for name in ("todo.md", "objectives.md", "plan.md"):
        (tmp_path / name).write_bytes(b"immutable program")
    receipt = dict(
        source_head="old",
        source_forest=dict(portfolio={"head": "old"}, repositories=[]),
    )
    forest = dict(portfolio={"head": "new"}, repositories=[])

    def git(*argv, **kwargs):
        return json.dumps(config) if argv[1].endswith(".json") else b"immutable program"

    return receipt, forest, git, path


def test_clean_descendant_keeps_historical_task_program(tmp_path):
    receipt, forest, git, _ = fixture(tmp_path)
    with (
        patch.object(OPERATOR, "ROOT", tmp_path),
        patch.object(OPERATOR, "_git", git),
        patch.object(
            OPERATOR.subprocess, "run", return_value=SimpleNamespace(returncode=0)
        ),
    ):
        OPERATOR._validate_descendant_source(receipt, forest)
    assert receipt["source_head"] == "old"


@pytest.mark.parametrize("changed", ["policy", "tasks", "ancestry"])
def test_requalification_rejects_widened_or_unrelated_source(tmp_path, changed):
    receipt, forest, git, path = fixture(tmp_path)
    if changed == "policy":
        config = json.loads(path.read_text())
        config["authority_policy"]["duckdb"] = False
        path.write_text(json.dumps(config))
    elif changed == "tasks":
        (tmp_path / "todo.md").write_text("different work")
    with (
        patch.object(OPERATOR, "ROOT", tmp_path),
        patch.object(OPERATOR, "_git", git),
        patch.object(
            OPERATOR.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=int(changed == "ancestry")),
        ),
    ):
        with pytest.raises(OPERATOR.OperatorError):
            OPERATOR._validate_descendant_source(receipt, forest)


@pytest.mark.parametrize("drift", ["", "owner", "tasks"])
def test_native_status_consumes_dbapi_rows_and_rejects_identity_drift(
    tmp_path, monkeypatch, drift
):
    import sys

    identity = dict(
        server_id="s1",
        process_birth_id="b1",
        database_uuid="u1",
        generation=2,
        fence_epoch=2,
    )
    state = dict(task_cid="t1", task_alias="PCPR-096", status="completed", revision=4)
    paths = dict(
        owner=tmp_path,
        owner_status=tmp_path / "owner.json",
        database=tmp_path / "state.duckdb",
    )
    (tmp_path / "token").write_text("test-token")
    receipt = {"database_task_source_receipt": {"task_cids": ["t1"]}}

    class Cursor:
        def __init__(self, rows):
            self.description = [(key,) for key in rows[0]] if rows else []
            self.rows = [tuple(row.values()) for row in rows]

        def fetchall(self):
            return self.rows

    class Client:
        def __init__(self, **kwargs):
            self.identity = {**identity, "generation": 9 if drift == "owner" else 2}

        def execute_operation(self, operation, parameters):
            if operation == "executor_control_snapshot":
                return Cursor([{"tasks_json": json.dumps([state])}])
            if operation == "executor_task_projection_page":
                return Cursor(
                    [{**state, "task_cid": "wrong" if drift == "tasks" else "t1"}]
                )
            return Cursor([])

        def completion_progress_snapshot(self, cids):
            return {"completion_projection": {"task_states": [state]}}

        def close(self):
            pass

    module = SimpleNamespace(
        STATUS_BOOTSTRAP_CLIENT_ID="reader",
        TYPED_STATE_OWNER_TOKEN_FILENAME="token",
        TYPED_STATE_OWNER_SOCKET_FILENAME="socket",
        TypedStateOwnerConnection=Client,
        compact_default_owner_socket_path=lambda *a, **k: tmp_path / "socket",
    )
    monkeypatch.setitem(
        sys.modules,
        "ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner",
        module,
    )
    board = SimpleNamespace(
        board_namespace="namespace",
        resolved_database_program=lambda: SimpleNamespace(
            store_generation="generation-2"
        ),
    )
    monkeypatch.setattr(OPERATOR, "_load_config", lambda _: (board, {}))
    monkeypatch.setattr(OPERATOR, "_runtime_paths", lambda _: paths)
    monkeypatch.setattr(OPERATOR, "_assert_materialized_source", lambda _: receipt)
    monkeypatch.setattr(OPERATOR, "_json_object", lambda _: {"identity": identity})
    monkeypatch.setattr(OPERATOR, "_source_forest", lambda: {"head": "source"})
    if drift:
        with pytest.raises(OPERATOR.OperatorError):
            OPERATOR.authoritative_status(tmp_path / "config")
    else:
        result = OPERATOR.authoritative_status(tmp_path / "config")
        assert result["tasks"] == [state]
        assert result["authoritative_task_observation"] is True
        assert result["completion_authority"] is False
