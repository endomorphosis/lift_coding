"""Pure campaign-verifier tests; genuine public fixtures remain read-only."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

AB = Path(__file__).resolve().parent
PUBLIC = AB / "native-qualification-baseline-02/actual-start-01/public"
CASES = ("baseline", "stale-head", "swapped-allocation", "modified-artifact",
         "disconnect", "exceeded-budget")

spec = importlib.util.spec_from_file_location(
    "independent_dispatch_campaign_test", AB / "verify_dispatch_campaign.py")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)


def read_public(name):
    return json.loads((PUBLIC / name).read_text())


def set_at(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def rehash_snapshot(state):
    state["snapshot_cid"] = v.structured_cid(
        {key: value for key, value in state.items() if key != "snapshot_cid"})


def rehash_event(state):
    event = state["records"][0]["event"]
    event["event_cid"] = v.structured_cid(
        {key: value for key, value in event.items() if key != "event_cid"})
    rehash_snapshot(state)


@pytest.fixture
def budget():
    return read_public("final-budget-state.json")


def test_original_committed_budget_retains_exact_event_and_totals(budget):
    report = v.verify_budget(budget, "baseline")
    assert report["record_status"] == "committed"
    assert report["event"] == budget["records"][0]["event"]
    assert report["event_cid"] == report["event"]["event_cid"]
    assert report["totals"] == budget["totals"]
    assert report["policy"] == budget["policy"]


@pytest.mark.parametrize("case", CASES[1:5])
def test_aborted_fault_keeps_reserved_accounting(budget, case):
    budget["records"][0]["status"] = "aborted"
    rehash_snapshot(budget)
    report = v.verify_budget(budget, case)
    assert report["record_status"] == "aborted"
    assert report["totals"]["events"] == report["totals"]["model_calls"] == 1
    assert report["totals"]["new_content_bytes"] > 0


def test_exceeded_budget_has_no_reserved_event(budget):
    budget["records"] = []
    budget["totals"] = {key: 0 for key in budget["totals"]}
    budget["policy"]["max_rendered_input_tokens"] = 1
    budget["policy_cid"] = v.structured_cid(budget["policy"])
    rehash_snapshot(budget)
    report = v.verify_budget(budget, "exceeded-budget")
    assert report["record_status"] is None
    assert report["event"] is report["event_cid"] is None
    assert not any(report["totals"].values())


@pytest.mark.parametrize("key", ["snapshot_cid", "binding_cid", "policy_cid"])
def test_budget_rejects_content_identity_substitution(budget, key):
    budget[key] = "baguqeera-forged"
    if key != "snapshot_cid":
        rehash_snapshot(budget)
    with pytest.raises(v.VerificationError):
        v.verify_budget(budget, "baseline")


@pytest.mark.parametrize("path,replacement", [
    (("closed",), False),
    (("totals", "events"), True),
    (("totals", "model_calls"), "1"),
    (("totals", "new_content_bytes"), -1),
    (("totals", "rendered_input_tokens"), 0),
    (("records", 0, "status"), "prepared"),
    (("records", 0, "event", "sequence"), 2),
    (("records", 0, "event", "binding_cid"), "foreign-binding"),
    (("records", 0, "event", "new_content", "bytes"), True),
    (("records", 0, "event", "new_content", "sha256"), "0" * 64),
])
def test_rehashed_budget_still_rejects_invalid_accounting(budget, path, replacement):
    set_at(budget, path, replacement)
    rehash_event(budget)
    with pytest.raises(v.VerificationError):
        v.verify_budget(budget, "baseline")


@pytest.mark.parametrize("key,value", [
    ("max_events", 3), ("max_model_calls", 3), ("max_retry_calls", 2),
    ("max_expansion_calls", 1), ("max_new_content_tokens", 100001),
    ("max_rendered_input_tokens", 100001), ("max_new_content_bytes", 1000001),
    ("max_rendered_input_bytes", 1000001), ("max_payload_bytes", 256001),
    ("max_model_calls", True),
])
def test_rehashed_policy_cannot_expand_campaign_ceiling(budget, key, value):
    budget["policy"][key] = value
    budget["policy_cid"] = v.structured_cid(budget["policy"])
    rehash_snapshot(budget)
    with pytest.raises(v.VerificationError):
        v.verify_budget(budget, "baseline")


@pytest.mark.parametrize("case,status", [
    ("baseline", "aborted"), ("disconnect", "committed"),
    ("exceeded-budget", "committed"), ("unrecognized", "committed"),
])
def test_budget_status_is_bound_to_exact_case(budget, case, status):
    budget["records"][0]["status"] = status
    rehash_snapshot(budget)
    with pytest.raises(v.VerificationError):
        v.verify_budget(budget, case)


@pytest.fixture
def resources():
    return read_public("summary.json")["resources_after"]


def test_released_resources_accept_nonzero_historical_counters(resources):
    assert resources["counters"]["acquisitions_total"] > 0
    assert v.verify_resources(resources) is None


@pytest.mark.parametrize("path", [
    ("allocated", "cpu_slots"), ("allocated", "memory_mb"),
    ("allocated_child_process_slots",), ("allocated_gpu_memory_mb",),
    ("allocated_unified_memory_mb",), ("active_lease_count",),
    ("active_root_lease_count",), ("active_child_lease_count",),
    ("waiting_request_count",),
    ("lanes", "validation", "allocated", "child_process_slots"),
])
def test_any_live_resource_allocation_refuses(resources, path):
    set_at(resources, path, 1)
    with pytest.raises(v.VerificationError):
        v.verify_resources(resources)


def test_unbalanced_resource_acquisitions_refuse(resources):
    resources["counters"]["releases_total"] -= 1
    with pytest.raises(v.VerificationError):
        v.verify_resources(resources)


@pytest.fixture
def lifecycle():
    return [read_public(name) for name in (
        "native-START.json", "native-STOP.json", "native-cleanup.json",
        "native-launch-manifest.json")]


def test_original_start_stop_bind_manifest_and_fence(lifecycle):
    report = v.verify_stop(*lifecycle)
    assert report == {"run_id": lifecycle[3]["run_id"],
                      "start_stop_bound": True, "old_tree_fenced": True}


@pytest.mark.parametrize("index,path,value", [
    (0, ("data", "new_process_identity", "run_id"), "foreign-run"),
    (0, ("policy_id",), "sha256:" + "0" * 64),
    (1, ("tree_id",), "foreign-tree"),
    (1, ("data", "old_tree_fenced"), False),
    (1, ("operation",), "start"),
    (2, ("STOP_called",), False),
    (2, ("remaining_owner_processes",), 1),
    (2, ("final_worker_cleanup_returncode",), 1),
    (3, ("run_id",), "foreign-run"),
])
def test_stop_rejects_foreign_identity_or_incomplete_cleanup(lifecycle, index, path, value):
    set_at(lifecycle[index], path, value)
    if index == 1:
        lifecycle[2]["stop"] = deepcopy(lifecycle[1])
    with pytest.raises(v.VerificationError):
        v.verify_stop(*lifecycle)


def test_cleanup_stop_cannot_be_a_different_receipt(lifecycle):
    lifecycle[2]["stop"]["request_id"] = "foreign-request"
    with pytest.raises(v.VerificationError):
        v.verify_stop(*lifecycle)


@pytest.fixture
def exports(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    descriptors = []
    for name, content in [("evidence.json", b'{"status":"prepared"}\n'),
                          ("input.txt", b"exact native input\n")]:
        path = public_dir / name
        path.write_bytes(content)
        descriptors.append({"path": str(path), "bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest()})
    names = [Path(row["path"]).name for row in descriptors]
    return {"public_exports": descriptors,
            "actual_summary": {"public_files": names},
            "owner_execution": {"public_files": names[:]}}, public_dir


def test_export_pins_match_exact_original_bytes(exports):
    result, public_dir = exports
    assert v.verify_public_exports(result, public_dir) == result["public_exports"]


@pytest.mark.parametrize("mutation", ["duplicate", "foreign", "hash", "size", "bool"])
def test_export_pin_substitutions_refuse(exports, mutation):
    result, public_dir = exports
    pin = result["public_exports"][0]
    if mutation == "duplicate":
        result["public_exports"].append(deepcopy(pin))
    elif mutation == "foreign":
        foreign = public_dir.parent / Path(pin["path"]).name
        foreign.write_bytes(Path(pin["path"]).read_bytes())
        pin["path"] = str(foreign)
    elif mutation == "hash":
        pin["sha256"] = "0" * 64
    elif mutation == "size":
        pin["bytes"] += 1
    else:
        pin["bytes"] = True
    with pytest.raises(v.VerificationError):
        v.verify_public_exports(result, public_dir)


def test_export_symlink_cannot_escape_public_directory(exports):
    result, public_dir = exports
    path = Path(result["public_exports"][0]["path"])
    foreign = public_dir.parent / "foreign.json"
    foreign.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(foreign)
    with pytest.raises(v.VerificationError):
        v.verify_public_exports(result, public_dir)


def coverage():
    return [{"case": case, "qualified": True} for case in CASES]


def test_coverage_requires_all_six_exact_cases():
    assert v.assess_coverage(coverage()) is True
    assert v.assess_coverage(coverage()[:-1]) is False


@pytest.mark.parametrize("qualified", [False, None, 1, "true"])
def test_coverage_cannot_promote_false_or_truthy_claims(qualified):
    reports = coverage()
    reports[0]["qualified"] = qualified
    assert v.assess_coverage(reports) is False


@pytest.mark.parametrize("case", ["baseline", "stale_head", "arbitrary"])
def test_duplicate_and_unknown_case_names_refuse(case):
    reports = coverage()
    reports.append({"case": case, "qualified": True})
    with pytest.raises(v.VerificationError):
        v.assess_coverage(reports)
