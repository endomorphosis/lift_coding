"""Operator retry orchestration keeps queue custody and exact replay parameters."""
from contextlib import contextmanager
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py"


@pytest.fixture
def operator(tmp_path, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import legacy_verification_retry as legacy
    from ipfs_accelerate_py.agent_supervisor.merge import checkout_lock
    spec = importlib.util.spec_from_file_location("doep_legacy_retry_test", SCRIPT)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    monkeypatch.setattr(m, "ROOT", tmp_path)
    projection = tmp_path / "role/state/lane-2/attempt/task-projection.md"
    projection.parent.mkdir(parents=True); projection.write_text("retained projection")
    paths = {"root": tmp_path / "role", "state": tmp_path / "role/state",
             "evidence": tmp_path / "role/evidence", "operator_pid": tmp_path / "role/operator.pid"}
    board = SimpleNamespace(merge_target_branch="agent/doep")
    population = {"tasks": [{"task_alias": "DOEP-041", "task_cid": "task:041"}]}
    terminal = {"attempt_number": 1, "reason": legacy.REASON}
    body = {"title": "preserved task", "completion_receipt": terminal}
    row = {"task_alias": "DOEP-041", "task_cid": "task:041", "revision": 4,
           "status": "blocked", "body_json": json.dumps(body)}
    calls = []; submissions = []; active_guard = [False]; fail_after_cas = [False]
    evidence = {"schema": legacy.SCHEMA, "evidence_id": "sha256:" + "e" * 64, "require_fresh_portal_revalidation": True,
                "retained_candidate_admitted": False}
    monkeypatch.setattr(m, "_load", lambda: (board, population, paths))
    monkeypatch.setattr(m, "_pid_alive", lambda _: False)
    monkeypatch.setattr(m, "_history_source_observation", lambda: {".": {"head": "a" * 40, "tree": "b" * 40}})
    monkeypatch.setattr(m.subprocess, "run", lambda *_args, **_kw: SimpleNamespace(returncode=0, stdout="a" * 40))
    monkeypatch.setattr(checkout_lock, "checkout_repository_id", lambda root: "repository:physical")
    monkeypatch.setattr(legacy, "inspect_legacy_verification_retry", lambda *_args, **_kw: copy.deepcopy(evidence))

    @contextmanager
    def guard(**kwargs):
        assert kwargs["target_repository_id"] == "repository:physical"
        assert kwargs["target_branch"] == "agent/doep"
        calls.append("queue-held"); active_guard[0] = True
        try:
            yield {"receipt_id": "sha256:" + "q" * 64, "matching_queue_rows": 0, "guard_retained": True}
        finally:
            active_guard[0] = False; calls.append("queue-released")
    monkeypatch.setattr(legacy, "hold_legacy_retry_queue_absence", guard)

    def submit(**kwargs):
        if not submissions:
            assert active_guard[0]
            assert list(paths["evidence"].rglob("legacy-verification-*.json"))
            row.update(status="retrying", revision=5)
        else:
            assert kwargs == submissions[0], "replay must preserve the original command exactly"
        calls.append("cas"); submissions.append(copy.deepcopy(kwargs))
        if fail_after_cas[0]:
            fail_after_cas[0] = False
            raise ConnectionError("response lost after durable CAS")
        return SimpleNamespace(accepted=True, to_dict=lambda: {"accepted": True})

    client = SimpleNamespace(
        execute=lambda name, _args: [copy.deepcopy(row)] if name == "select_task_by_cid" else [],
        load_generation=lambda: SimpleNamespace(to_record=lambda: {"generation": 99}),
        recover_blocked_task_retry=submit, close=lambda: calls.append("client-closed"),
    )
    server = SimpleNamespace(start=lambda: calls.append("server-started"), ready=lambda: True,
        stop=lambda: calls.append("server-stopped"),
        revoke_typed_client_grant=lambda grant: calls.append("grant-revoked"))
    monkeypatch.setattr(m, "_build_server", lambda *_args: server)
    monkeypatch.setattr(m, "_make_blocked_retry_recovery_client",
                        lambda *_args, **_kw: (client, SimpleNamespace(grant_id="grant:041")))
    return SimpleNamespace(m=m, legacy=legacy, row=row, body=body, paths=paths, projection=projection,
        evidence=evidence, calls=calls, submissions=submissions, fail_after_cas=fail_after_cas, guard=guard)


def run(op):
    return op.m.recover_legacy_verification_timeout(task_alias="DOEP-041", expected_revision=4,
                                                   task_projection=op.projection)


def test_fresh_retry_keeps_queue_guard_through_cas_and_revokes_operator_grant(operator):
    assert run(operator) == 0
    submitted = operator.submissions[0]
    assert submitted["task_body"] == operator.body
    assert submitted["expected_task_revision"] == 4
    assert submitted["max_task_attempts_before"] == 1
    assert submitted["max_task_attempts_after"] == 2
    assert submitted["require_fresh_portal_revalidation"] is True
    assert operator.calls.index("queue-held") < operator.calls.index("cas") < operator.calls.index("queue-released")
    assert operator.calls[-3:] == ["client-closed", "grant-revoked", "server-stopped"]


def test_lost_cas_response_replays_exact_saved_authorization_without_new_retry(operator):
    operator.fail_after_cas[0] = True
    with pytest.raises(ConnectionError): run(operator)
    assert operator.row["revision"] == 5
    assert run(operator) == 0
    assert operator.submissions[0] == operator.submissions[1]
    assert operator.calls.count("queue-held") == 1
    assert operator.calls.count("server-stopped") == 2


def test_live_native_owner_prevents_recovery_server_start(operator, monkeypatch):
    monkeypatch.setattr(operator.m, "_pid_alive", lambda _: True)
    with pytest.raises(operator.m.HandoffError, match="stop the live"):
        run(operator)
    assert operator.calls == []


def test_wrong_revision_without_prior_authorization_never_submits(operator):
    operator.row["revision"] = 5
    with pytest.raises(operator.m.HandoffError, match="expected blocked revision"):
        run(operator)
    assert operator.submissions == []
    assert operator.calls[-3:] == ["client-closed", "grant-revoked", "server-stopped"]


def test_changed_history_before_cas_preserves_authorization_without_dispatch(operator, monkeypatch):
    count = [0]
    def inspect(*_args, **_kwargs):
        count[0] += 1
        return {**operator.evidence, "version": count[0]}
    monkeypatch.setattr(operator.legacy, "inspect_legacy_verification_retry", inspect)
    with pytest.raises(operator.m.HandoffError, match="history changed before CAS"):
        run(operator)
    assert operator.submissions == []
    assert list(operator.paths["evidence"].rglob("legacy-verification-*.json"))
    assert operator.calls[-3:] == ["client-closed", "grant-revoked", "server-stopped"]


def test_retained_authorization_cannot_be_modified_for_another_attempt(operator):
    operator.fail_after_cas[0] = True
    with pytest.raises(ConnectionError): run(operator)
    path = next(operator.paths["evidence"].rglob("legacy-verification-*.json"))
    saved = json.loads(path.read_text()); saved["terminal_receipt"]["attempt_number"] = 2
    path.write_text(json.dumps(saved))
    with pytest.raises(operator.m.HandoffError, match="authorization differs"):
        run(operator)
    assert len(operator.submissions) == 1


def test_source_forest_change_during_recovery_never_submits(operator, monkeypatch):
    calls = [0]
    def source():
        calls[0] += 1
        return {".": {"head": "a" * 40, "tree": "b" * 40}, "runtime": {"head": calls[0]}}
    monkeypatch.setattr(operator.m, "_history_source_observation", source)
    with pytest.raises(operator.m.HandoffError, match="source changed before CAS"):
        run(operator)
    assert operator.submissions == []
    assert operator.calls[-3:] == ["client-closed", "grant-revoked", "server-stopped"]


def test_native_operator_selects_reconciled_predecessor_and_holds_exact_guard(operator, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import legacy_quarantined_predecessor as prior
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalBridgeError

    def single(*args, **kwargs):
        raise DatabasePortalBridgeError("legacy verification retry has no single completed provider lifecycle")

    expected = {**operator.evidence, "schema": prior.SCHEMA, "predecessor_queue_settlement_required": True}
    monkeypatch.setattr(operator.legacy, "inspect_legacy_verification_retry", single)
    monkeypatch.setattr(prior, "inspect_reconciled_legacy_verification_retry", lambda *a, **k: copy.deepcopy(expected))

    @contextmanager
    def guard(**kwargs):
        assert kwargs['repository_root'] == operator.m.ROOT
        assert kwargs['evidence'] == expected
        with operator.guard(**kwargs) as receipt:
            yield {**receipt, 'matching_queue_rows': 1, 'quarantined_predecessor_unchanged': True}

    monkeypatch.setattr(prior, "hold_reconciled_legacy_retry_queue", guard)
    assert run(operator) == 0
    assert len(operator.submissions) == 1
    assert operator.calls.index('queue-held') < operator.calls.index('cas') < operator.calls.index('queue-released')
    saved = json.loads(next(operator.paths['evidence'].rglob('legacy-verification-*.json')).read_text())
    assert saved['evidence'] == expected
    assert saved['queue_evidence']['matching_queue_rows'] == 1
    assert saved['require_fresh_portal_revalidation'] is True


def test_unknown_predecessor_never_reaches_operator_cas(operator, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import legacy_quarantined_predecessor as prior
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalBridgeError

    def refuse(*args, **kwargs):
        raise DatabasePortalBridgeError('unsettled candidate history')

    monkeypatch.setattr(operator.legacy, 'inspect_legacy_verification_retry', refuse)
    monkeypatch.setattr(prior, 'inspect_reconciled_legacy_verification_retry', refuse)
    with pytest.raises(DatabasePortalBridgeError, match='unsettled candidate'):
        run(operator)
    assert operator.submissions == [] and 'queue-held' not in operator.calls
    assert operator.calls[-3:] == ['client-closed', 'grant-revoked', 'server-stopped']
