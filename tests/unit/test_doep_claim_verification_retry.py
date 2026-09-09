from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py"


def module():
    spec = importlib.util.spec_from_file_location("doep_retry_test", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def row():
    return {
        "task_alias": "DOEP-011", "task_cid": "sha256:task", "status": "blocked", "revision": 24,
        "body_json": json.dumps({"title": "Preserved task", "completion_receipt": {
            "operation": "database_portal_terminal_failure", "reason": "post-merge completion recovery seed failed claim verification",
            "retryable": False, "control_expected_status": "in_progress", "control_expected_revision": 23,
            "attempt_number": 78, "attempt_id": "attempt:historical",
        }}),
    }


def material(m, value):
    return m._claim_verification_retry_material(value, task_alias="DOEP-011", task_cid="sha256:task", expected_revision=24, source_head="a" * 40)


def test_retry_preserves_historical_body_and_requires_fresh_validation():
    m = module()
    value = row()
    before = copy.deepcopy(value)
    body, terminal, evidence = material(m, value)
    assert value == before
    assert body == json.loads(value["body_json"])
    assert body["completion_receipt"] == terminal
    assert evidence["fresh_attempt_number"] == 79
    assert evidence["require_fresh_portal_revalidation"] is True
    assert evidence["attempt_refunded"] is False
    assert evidence["historical_completion_evidence_accepted"] is False


@pytest.mark.parametrize("field,value", [("status", "quarantined"), ("status", "completed"), ("status", "in_progress"), ("revision", 25), ("task_alias", "DOEP-031"), ("task_cid", "foreign")])
def test_retry_refuses_other_task_or_terminal_state(field, value):
    m = module()
    data = row()
    data[field] = value
    with pytest.raises(m.HandoffError, match="exact blocked authority"):
        material(m, data)


@pytest.mark.parametrize("field,value", [("reason", "portal_provider_failed"), ("retryable", True), ("control_expected_revision", 22), ("control_expected_status", "todo"), ("attempt_number", True), ("attempt_number", 0), ("operation", "database_completion")])
def test_retry_refuses_unqualified_terminal_receipt(field, value):
    m = module()
    data = row()
    body = json.loads(data["body_json"])
    body["completion_receipt"][field] = value
    data["body_json"] = json.dumps(body)
    with pytest.raises(m.HandoffError, match="exact blocked authority"):
        material(m, data)
