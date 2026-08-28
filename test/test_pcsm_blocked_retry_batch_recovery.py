"""Current-head PCSM blocked retries are exact, scoped, and replayable."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "scripts" / "run_agent_supervisor_proof_carrying_semantic_minification.py"
ALIASES = ("PCSM-013", "PCSM-016", "PCSM-017", "PCSM-018")


def _load_operator():
    spec = importlib.util.spec_from_file_location("pcsm_batch_operator", OPERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _batch_fixture(operator, monkeypatch: pytest.MonkeyPatch):
    expectations = {}
    entries = []
    for index, alias in enumerate(ALIASES):
        source_revision = 8 if alias == "PCSM-013" else 4
        attempt_number = 2 if alias == "PCSM-013" else 1
        task_cid = f"cid:{alias.lower()}"
        route = {
            "task_alias": alias,
            "task_cid": task_cid,
            "policy_id": "policy:current-head",
            "task_revision": 1,
        }
        receipt = {
            "operation": "database_portal_terminal_failure",
            "reason": operator.CURRENT_HEAD_BLOCKED_RETRY_TERMINAL_REASON,
            "retryable": False,
            "control_expected_status": "in_progress",
            "control_expected_revision": source_revision - 1,
            "attempt_id": f"attempt:{index}",
            "claim_id": f"claim:{index}",
            "lease_id": f"lease:{index}",
            "owner_session_id": f"owner:{index}",
            "attempt_number": attempt_number,
            "fencing_token": index + 1,
            "fence_epoch": index + 1,
            "execution_route_binding": route,
            "execution_route_policy_id": route["policy_id"],
            "execution_route_origin_revision": route["task_revision"],
        }
        task_body = {"task": alias, "completion_receipt": receipt}
        body_id = operator._identity(task_body)
        receipt_id = operator._identity(receipt)
        expectations[alias] = {
            "task_cid": task_cid,
            "source_revision": source_revision,
            "source_attempt_number": attempt_number,
            "source_task_body_id": body_id,
            "source_completion_receipt_id": receipt_id,
        }
        incident = operator.CURRENT_HEAD_BLOCKED_RETRY_INCIDENT_EXPECTATIONS[
            alias
        ]
        lane_index = incident["lane_index"]
        portal_attempt_id = incident["portal_attempt_id"]
        attempt_root = (
            operator.RUNTIME_RELATIVE
            / "state"
            / f"lane-{lane_index}"
            / f"pcsm_lane_{lane_index}_database_portal_attempts"
            / portal_attempt_id
        )
        sidecar_evidence = {
            "schema": operator.CURRENT_HEAD_BLOCKED_RETRY_BATCH_EVIDENCE_SCHEMA,
            "task_alias": alias,
            "task_cid": task_cid,
            "lane_index": lane_index,
            "portal_attempt_id": portal_attempt_id,
            "portal_attempt_relative_path": attempt_root.as_posix(),
            "database_attempt_binding_path": (
                attempt_root / "database-attempt-binding.json"
            ).as_posix(),
            "database_attempt_binding_bytes_id": "sha256:" + "a" * 64,
            "database_attempt_binding_id": "sha256:" + "b" * 64,
            "protected_path_incident_path": (
                attempt_root / "implementation-protected-path-incident.json"
            ).as_posix(),
            "protected_path_incident_bytes_id": "sha256:" + "c" * 64,
            "protected_path_incident_identity": "sha256:" + "d" * 64,
            "projected_portal_task_cid": f"portal:{alias.lower()}",
            "projected_portal_task_key": f"task/v1/{index:064x}",
            "portal_implementation_attempt": 1,
            "attempt_identity": {
                field: receipt[field]
                for field in (
                    "attempt_id",
                    "attempt_number",
                    "claim_id",
                    "lease_id",
                    "owner_session_id",
                    "fencing_token",
                    "fence_epoch",
                )
            },
            "rescue_commit": incident["rescue_commit"],
            "merge_commit": incident["merge_commit"],
        }
        entries.append(
            {
                "schema": operator.CURRENT_HEAD_BLOCKED_RETRY_BATCH_ENTRY_SCHEMA,
                "task_alias": alias,
                "task_cid": task_cid,
                "source_status": "blocked",
                "source_revision": source_revision,
                "target_status": "retrying",
                "target_revision": source_revision + 1,
                "source_task_body": task_body,
                "source_task_body_id": body_id,
                "source_completion_receipt_id": receipt_id,
                "max_task_attempts_before": attempt_number,
                "max_task_attempts_after": attempt_number + 1,
                "started_at_ms": 1_787_900_000_000 + index,
                "retry_not_before_ms": 1_787_900_000_000 + index,
                "sidecar_evidence": sidecar_evidence,
                "sidecar_evidence_id": operator._identity(sidecar_evidence),
            }
        )
    monkeypatch.setattr(
        operator,
        "CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS",
        expectations,
    )
    body = {
        "schema": operator.CURRENT_HEAD_BLOCKED_RETRY_BATCH_SCHEMA,
        "operation": operator.CURRENT_HEAD_BLOCKED_RETRY_BATCH_OPERATION,
        "source_head": "a" * 40,
        "repository_tree_id": "b" * 40,
        "entries": entries,
    }
    body["batch_receipt_id"] = operator._identity(body)
    return body


def _reseal(operator, batch):
    batch.pop("batch_receipt_id", None)
    batch["batch_receipt_id"] = operator._identity(batch)
    return batch


def test_current_head_batch_verifier_rejects_stale_duplicate_and_foreign_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    batch = _batch_fixture(operator, monkeypatch)

    verified = operator._verified_current_head_blocked_retry_batch(
        batch,
        sealed_source_head="a" * 40,
        sealed_source_tree="b" * 40,
        current_attempt_limit=3,
    )
    assert [entry["task_alias"] for entry in verified["entries"]] == list(ALIASES)
    expected_body = operator._current_head_blocked_retry_expected_task_body(
        entry=verified["entries"][0],
        batch_receipt_id=verified["batch_receipt_id"],
    )
    requirement = expected_body["fresh_portal_revalidation_requirement"]
    assert requirement["task_cid"] == verified["entries"][0]["task_cid"]
    assert requirement["operator_handoff_receipt_id"] == verified[
        "batch_receipt_id"
    ]
    assert requirement["sidecar_evidence_id"] == verified["entries"][0][
        "sidecar_evidence_id"
    ]
    assert expected_body["completion_receipt"]["fresh_attempt_number"] == 3

    with pytest.raises(operator.OperatorError, match="seal is invalid"):
        operator._verified_current_head_blocked_retry_batch(
            batch,
            sealed_source_head="c" * 40,
            sealed_source_tree="b" * 40,
            current_attempt_limit=3,
        )

    duplicate = copy.deepcopy(batch)
    duplicate["entries"][3] = copy.deepcopy(duplicate["entries"][2])
    _reseal(operator, duplicate)
    with pytest.raises(operator.OperatorError, match="complete and ordered"):
        operator._verified_current_head_blocked_retry_batch(
            duplicate,
            sealed_source_head="a" * 40,
            sealed_source_tree="b" * 40,
            current_attempt_limit=3,
        )

    foreign = copy.deepcopy(batch)
    foreign["entries"][0]["source_task_body"]["task"] = "foreign"
    foreign["entries"][0]["source_task_body_id"] = operator._identity(
        foreign["entries"][0]["source_task_body"]
    )
    _reseal(operator, foreign)
    with pytest.raises(operator.OperatorError, match="predecessor is not exact"):
        operator._verified_current_head_blocked_retry_batch(
            foreign,
            sealed_source_head="a" * 40,
            sealed_source_tree="b" * 40,
            current_attempt_limit=3,
        )

    with pytest.raises(operator.OperatorError, match="PCSM-013.*predecessor"):
        operator._verified_current_head_blocked_retry_batch(
            batch,
            sealed_source_head="a" * 40,
            sealed_source_tree="b" * 40,
            current_attempt_limit=2,
        )


def test_blocked_retry_batch_validates_all_then_applies_in_alias_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    batch = _batch_fixture(operator, monkeypatch)
    observed = []

    def apply_one(**kwargs):
        observed.append(
            (kwargs["entry"]["task_alias"], kwargs["blocked_retry_state"])
        )
        return {
            "task_alias": kwargs["entry"]["task_alias"],
            "post_recovery_requirement": (
                operator.CURRENT_HEAD_BLOCKED_RETRY_POST_RECOVERY_REQUIREMENT
            ),
        }

    monkeypatch.setattr(
        operator,
        "_apply_current_head_blocked_retry_entry",
        apply_one,
    )
    states = {
        "PCSM-013": "command_replay_required",
        "PCSM-016": "command_replay_required",
        "PCSM-017": "pending_apply",
        "PCSM-018": "pending_apply",
    }
    result = operator._apply_current_head_blocked_retry_batch(
        server=object(),
        board=object(),
        handoff=batch,
        sealed_source_head="a" * 40,
        sealed_source_tree="b" * 40,
        current_attempt_limit=3,
        blocked_retry_states=states,
    )
    assert observed == [(alias, states[alias]) for alias in ALIASES]
    assert result["recovery_count"] == 4
    assert result["post_recovery_requirement"] == (
        "fresh_portal_claim_and_current_head_revalidation"
    )

    observed.clear()
    invalid_states = dict(states)
    invalid_states["PCSM-018"] = "unverified"
    with pytest.raises(operator.OperatorError, match="states are not exact"):
        operator._apply_current_head_blocked_retry_batch(
            server=object(),
            board=object(),
            handoff=batch,
            sealed_source_head="a" * 40,
            sealed_source_tree="b" * 40,
            current_attempt_limit=3,
            blocked_retry_states=invalid_states,
        )
    assert observed == []


def test_blocked_retry_entry_scopes_revokes_and_requires_fresh_portal_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    batch = _batch_fixture(operator, monkeypatch)
    entry = batch["entries"][0]
    grants = []
    revoked = []
    recovered = []

    class FakeClient:
        def __init__(self, **_kwargs):
            self.generation_reads = 0

        def attach(self, *_args, **_kwargs):
            return None

        def load_generation(self):
            revision = 10 + self.generation_reads
            self.generation_reads += 1
            return SimpleNamespace(
                generation=1,
                fence_epoch=1,
                revision=revision,
                to_dict=lambda: {
                    "generation": 1,
                    "fence_epoch": 1,
                    "revision": revision,
                },
            )

        def recover_blocked_task_retry(self, **kwargs):
            recovered.append(kwargs)
            expected_body = operator._current_head_blocked_retry_expected_task_body(
                entry=entry,
                batch_receipt_id=batch["batch_receipt_id"],
            )
            requirement_id = expected_body[
                "fresh_portal_revalidation_requirement"
            ]["requirement_id"]
            route = entry["source_task_body"]["completion_receipt"][
                "execution_route_binding"
            ]
            result_body = {
                "schema": operator.TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA,
                "operation": operator.HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND,
                "task_cid": entry["task_cid"],
                "attempt_id": kwargs["terminal_receipt"]["attempt_id"],
                "attempt_number": kwargs["terminal_receipt"]["attempt_number"],
                "fresh_attempt_number": entry["max_task_attempts_after"],
                "task_revision": entry["target_revision"],
                "queue_revision": 1,
                "retry_not_before_ms": entry["retry_not_before_ms"],
                "source_completion_receipt_id": entry[
                    "source_completion_receipt_id"
                ],
                "operator_handoff_receipt_id": batch["batch_receipt_id"],
                "sidecar_evidence_id": entry["sidecar_evidence_id"],
                "max_task_attempts_before": entry["max_task_attempts_before"],
                "max_task_attempts_after": entry["max_task_attempts_after"],
                "attempt_refunded": False,
                "execution_route_binding_cid": operator._semantic_identity(
                    {"task_execution_route_binding": route}
                ),
                "execution_route_policy_id": route["policy_id"],
                "execution_route_origin_revision": route["task_revision"],
                "store_revision_before": 10,
                "fresh_portal_revalidation_requirement_id": requirement_id,
            }
            digest = "a" * 64
            return SimpleNamespace(
                outcome=SimpleNamespace(value="accepted"),
                changed=True,
                conflict_kind=None,
                result=result_body,
                command_id=f"cmd:blocked-retry-recovery:{digest}",
                idempotency_key=f"executor-blocked-retry-recovery:{digest}",
                result_digest=operator._identity(result_body),
                generation=1,
                fence_epoch=1,
                revision=11,
                to_dict=lambda: {"result": result_body},
            )

        def close(self):
            return None

    import ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client as client_module

    monkeypatch.setattr(client_module, "QuackStateClient", FakeClient)

    def issue(**kwargs):
        grants.append(kwargs)
        return "token", SimpleNamespace(grant_id="grant:one")

    server = SimpleNamespace(
        identity=SimpleNamespace(
            process_birth_id="birth:one",
            server_id="server:one",
            generation=1,
            fence_epoch=1,
        ),
        issue_typed_client_grant_record=issue,
        revoke_typed_client_grant=lambda grant_id: revoked.append(grant_id),
        typed_command_socket_path=lambda: Path("/tmp/not-opened"),
    )
    board = SimpleNamespace(
        resolved_database_program=lambda: SimpleNamespace(
            store_generation="store:one",
            quack_endpoint="quack://127.0.0.1:9999",
        )
    )
    result = operator._apply_current_head_blocked_retry_entry(
        server=server,
        board=board,
        batch_receipt_id=batch["batch_receipt_id"],
        entry=entry,
        blocked_retry_state="pending_apply",
    )

    assert len(grants) == 1
    assert grants[0]["allowed_command_operations"] == (
        "task.blocked.retry.recover",
    )
    assert grants[0]["entity_scopes"] == {"task_cid": entry["task_cid"]}
    assert revoked == ["grant:one"]
    assert recovered[0]["require_fresh_portal_revalidation"] is True
    assert result["post_recovery_requirement"] == (
        "fresh_portal_claim_and_current_head_revalidation"
    )
    assert result["fresh_portal_revalidation_requirement_id"].startswith(
        "baguqeera"
    )


def test_blocked_retry_database_states_validate_mixed_prefix_before_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    batch = _batch_fixture(operator, monkeypatch)
    recovered_alias = "PCSM-013"
    tasks = {}
    for entry in batch["entries"]:
        alias = entry["task_alias"]
        if alias == recovered_alias:
            body = operator._current_head_blocked_retry_expected_task_body(
                entry=entry,
                batch_receipt_id=batch["batch_receipt_id"],
            )
            status = "retrying"
            revision = entry["target_revision"]
        else:
            body = copy.deepcopy(entry["source_task_body"])
            status = "blocked"
            revision = entry["source_revision"]
        tasks[alias] = SimpleNamespace(
            task_alias=alias,
            task_cid=entry["task_cid"],
            status=status,
            revision=revision,
            body=body,
        )

    class Source:
        def get_task(self, alias):
            return tasks[alias]

        def get_queue_entry(self, _task_cid):
            return None

        def validate_retrying_task_cooldown(
            self,
            task_cid,
            *,
            expected_attempt_identity,
            expected_reason,
            expected_delay_ms,
        ):
            entry = next(
                item for item in batch["entries"] if item["task_cid"] == task_cid
            )
            assert expected_attempt_identity["attempt_id"].startswith("attempt:")
            assert expected_reason == operator.HANDOFF_REPAIR_BLOCKED_RETRY_REASON
            assert expected_delay_ms == 0
            return SimpleNamespace(
                attempt=entry["max_task_attempts_before"],
                retry_not_before_ms=entry["retry_not_before_ms"],
                selection_penalty=0,
                consecutive_failures=entry["max_task_attempts_before"],
                state="released",
                reason=operator.HANDOFF_REPAIR_BLOCKED_RETRY_REASON,
            )

    states, projections = operator._current_head_blocked_retry_database_states(
        Source(),
        batch,
    )
    assert states == {
        alias: (
            "command_replay_required"
            if alias == recovered_alias
            else "pending_apply"
        )
        for alias in ALIASES
    }
    assert [item["task_alias"] for item in projections] == list(ALIASES)

    tasks["PCSM-018"].body = {"completion_receipt": {"foreign": True}}
    with pytest.raises(operator.OperatorError, match="PCSM-018.*post-command"):
        operator._current_head_blocked_retry_database_states(Source(), batch)
