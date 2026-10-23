#!/usr/bin/env python3
"""Review explicitly selected public admitted dispatch runs without native calls.

Public inputs are supplied historical evidence, never live grants or leases.
The six-case qualification excludes the still-open authentic nonce replay case.
Optional token replay uses the pinned offline tiktoken reference implementation;
it is deliberately not an independently implemented token algorithm.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

AB = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("public_dispatch_campaign_data_verifier",
    AB / "verify_public_dispatch_evidence.py")
_DATA = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DATA)
VerificationError = _DATA.VerificationError
need = _DATA.need
canonical = _DATA.canonical
digest = _DATA.digest
structured_cid = _DATA.structured_cid
read_json = _DATA.read_json
read_bytes = _DATA.read_bytes
REQUIRED_CASES = frozenset(("baseline", "stale-head", "swapped-allocation",
    "modified-artifact", "disconnect", "exceeded-budget"))
TOTAL_KEYS = frozenset(("events", "model_calls", "retry_calls", "expansion_calls",
    "new_content_bytes", "new_content_tokens", "rendered_input_bytes", "rendered_input_tokens"))
POLICY_CEILINGS = {"max_events": 2, "max_model_calls": 2, "max_retry_calls": 1,
    "max_expansion_calls": 0, "max_new_content_bytes": 1_000_000,
    "max_rendered_input_bytes": 1_000_000, "max_new_content_tokens": 100_000,
    "max_rendered_input_tokens": 100_000, "max_payload_bytes": 256_000}
FALSE_CEILINGS = {**_DATA.FALSE_AUTHORITY, "production_admitted": False,
    "global_task_budget_enforced": False, "durable_budget_resume_supported": False,
    "full_supervisor_entrypoint_used": False, "full_task_satisfaction": False,
    "Terminal_Bench_harness_used": False, "provider_billing_savings_measured": False,
    "source_body_executed": False}
BPE_SHA = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
BPE_BYTES = 3_613_922
VOCABULARY_SHA = "a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f"
DEFAULT_BPE = AB / "public-tokenizer-cache/fb374d419588a4632f3f557e76b4b70aebbca790"
DEFAULT_TOKENIZER = AB.parent / "terminal-token-pairing-20261012-01/pinned-host-tokenizer"


def same(left, right, label):
    need(canonical(left) == canonical(right), label + " differs")


def integer(value, *, maximum=(1 << 63) - 1):
    need(type(value) is int and 0 <= value <= maximum, "bounded exact nonnegative integer required")


def zero(value, label):
    need(type(value) is int and value == 0, label + " must be exact integer zero")


def pin(path):
    path = Path(path)
    raw = read_bytes(path)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def check_pin(row, *, selected_path=None):
    _DATA.closed(row, {"path", "bytes", "sha256"}, "original artifact pin")
    path = Path(row["path"])
    need(path.is_absolute() and path.resolve(strict=True) == path,
         "canonical explicitly pinned file required")
    if selected_path is not None:
        need(path == Path(selected_path), "pinned artifact is outside selected evidence root")
    same(pin(path), row, "original public artifact hash/length")
    return dict(row)


def verify_public_exports(result, public_dir):
    public = Path(public_dir).resolve(strict=True)
    rows = result["public_exports"]
    need(type(rows) is list and 1 <= len(rows) <= 128, "bounded explicit public export inventory required")
    names, verified, total = set(), [], 0
    for row in rows:
        path = Path(row["path"])
        need(path.parent == public and re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", path.name)
             and path.name not in names, "duplicate or foreign public export path")
        names.add(path.name)
        verified.append(check_pin(row, selected_path=public / path.name))
        total += row["bytes"]
    need(total <= 64 * 1024 * 1024, "public export inventory exceeds campaign byte bound")
    for declared in (result["actual_summary"]["public_files"], result["owner_execution"]["public_files"]):
        need(type(declared) is list and len(declared) == len(set(declared)) and set(declared) == names,
             "declared public export inventory coverage differs")
    return verified


def verify_budget(state, case):
    need(case in REQUIRED_CASES, "explicit reviewed campaign case required")
    need(state["schema"] == "terminal-semantic-context-budget@1" and state["closed"] is True
         and state["accounting"] == "conservative_reserved_local_materialization_cost_no_refunds",
         "original conservative closed local budget required")
    _DATA.verify_cid(state, "snapshot_cid")
    need(state["binding_cid"] == structured_cid(state["binding"])
         and state["policy_cid"] == structured_cid(state["policy"]), "original budget binding/policy CID differs")
    same(state["tokenizer"], {"library": "tiktoken", "version": "0.13.0", "encoding": "o200k_base",
        "bpe_sha256": BPE_SHA, "vocabulary_sha256": VOCABULARY_SHA, "fallback": False, "offline": True},
        "original retained offline tokenizer declaration")
    for key in ("execution_authority", "proof_authority", "completion_authority", "current_owner_verified",
                "serialized_live_authority", "convergence_proved", "global_task_budget_enforced",
                "durable_budget_resume_supported"):
        if key in state:
            need(state[key] is False, "budget snapshot cannot promote live/global/semantic authority")
    zero(state["provider_calls"], "budget provider calls")
    policy, totals, records = state["policy"], state["totals"], state["records"]
    _DATA.closed(policy, {"schema", *POLICY_CEILINGS}, "finite local budget policy")
    need(policy["schema"] == "terminal-semantic-context-budget-policy@1", "budget policy schema differs")
    for key, limit in POLICY_CEILINGS.items():
        integer(policy[key], maximum=limit)
    _DATA.closed(totals, TOTAL_KEYS, "original cumulative budget totals")
    for key in TOTAL_KEYS:
        integer(totals[key]); need(totals[key] <= policy["max_" + key], "original budget total exceeds signed policy")
    need(type(records) is list, "original budget event records required")
    if case == "exceeded-budget":
        need(records == [] and all(value == 0 for value in totals.values()), "budget denial retained an unauthorized event")
        return {"totals": dict(totals), "record_status": None, "event_cid": None,
                "event": None, "policy": policy}
    need(len(records) == 1, "one complete original charged coding event required")
    row, = records
    _DATA.closed(row, {"event", "status"}, "original budget record")
    expected_status = "committed" if case == "baseline" else "aborted"
    need(row["status"] == expected_status, "original coding reservation did not retain expected committed/aborted charge")
    event = row["event"]
    _DATA.verify_cid(event, "event_cid")
    need(event["schema"] == "terminal-semantic-context-budget-event@1" and event["kind"] == "initial"
         and type(event["sequence"]) is int and event["sequence"] == 1
         and event["binding_cid"] == state["binding_cid"] and event["history_event_ids"] == []
         and event["previous_event_cid"] is None and event["retry_of"] is None
         and event["expansion_request"] is None and event["expansion_response"] is None,
         "original initial event/history/budget binding differs")
    for key in ("new_content", "rendered_input"):
        _DATA.closed(event[key], {"text", "bytes", "sha256", "tokens"}, "complete charged input")
        integer(event[key]["tokens"]); integer(event[key]["bytes"])
        same({name: event[key][name] for name in ("bytes", "sha256")}, _DATA.measure(event[key]["text"]),
             "charged complete input bytes/hash")
    expected = {"events": 1, "model_calls": 1, "retry_calls": 0, "expansion_calls": 0,
        "new_content_bytes": event["new_content"]["bytes"], "new_content_tokens": event["new_content"]["tokens"],
        "rendered_input_bytes": event["rendered_input"]["bytes"], "rendered_input_tokens": event["rendered_input"]["tokens"]}
    same(totals, expected, "original nonrefunding event totals")
    return {"totals": dict(totals), "record_status": expected_status,
            "event_cid": event["event_cid"], "event": event, "policy": policy}


def verify_resources(resources):
    for key in ("active_child_lease_count", "active_lease_count", "active_root_lease_count",
                "allocated_child_process_slots", "allocated_gpu_memory_mb", "allocated_unified_memory_mb",
                "waiting_request_count"):
        zero(resources[key], "final resources " + key)
    for value in resources["allocated"].values():
        zero(value, "final resource allocation")
    for lane in resources["lanes"].values():
        for value in lane["allocated"].values():
            zero(value, "final lane allocation")
    counters = resources["counters"]
    integer(counters["acquisitions_total"]); integer(counters["releases_total"])
    need(counters["acquisitions_total"] == counters["releases_total"], "resource acquisition/release count differs")


def verify_stop(start, stop, cleanup, manifest):
    manifest_id = "sha256:" + digest(canonical(manifest, signing=True))
    for operation, value in (("start", start), ("stop", stop)):
        need(value["operation"] == operation and value["status"] == "succeeded" and value["error"] is None
             and value["policy_id"] == value["objective_id"] == manifest_id
             and value["idempotency_key"] == manifest["run_id"] + ":" + operation + (":0" if operation == "start" else ":1")
             and value["tree_id"] == manifest["baseline_tree_id"]
             and value["caller"] == manifest["local_admission"]["manifest"]["binding"]["identity"],
             "native START/STOP protected launch differs")
    native = start["data"]["new_process_identity"]
    need(native["run_id"] == manifest["run_id"] and native["configuration_root"] == manifest_id
         and native["cwd"] == manifest["repository_root"], "actual START process configuration differs")
    need(stop["data"]["old_tree_fenced"] is True and stop["data"]["new_process_identity"] is None,
         "original native STOP failed to fence old process tree")
    worker = stop["data"]["isolated_worker_cleanup"]
    need(type(worker["returncode"]) is int and worker["returncode"] == 0 and worker["single_worker"] is True
         and worker["worker_uid"] == 1001, "original isolated worker STOP cleanup failed")
    same(worker["namespaces"], manifest["checked_observer_budget_scope"]["boundary"]["namespaces"],
         "STOP original worker namespaces")
    need(cleanup["STOP_called"] is True and cleanup["closed"] is True and cleanup["native_runtime_created"] is True
         and cleanup["errors"] == [], "original native cleanup remains incomplete")
    zero(cleanup["remaining_owner_processes"], "remaining native owner processes")
    zero(cleanup["final_worker_cleanup_returncode"], "final worker cleanup returncode")
    same(cleanup["stop"], stop, "original cleanup STOP receipt")
    return {"run_id": manifest["run_id"], "start_stop_bound": True, "old_tree_fenced": True}


def assess_coverage(case_reports):
    need(type(case_reports) is list and len(case_reports) <= len(REQUIRED_CASES), "bounded selected campaign cases required")
    names = [value["case"] for value in case_reports]
    need(len(names) == len(set(names)) and set(names) <= REQUIRED_CASES, "duplicate or unreviewed selected case")
    return set(names) == REQUIRED_CASES and all(value["qualified"] is True for value in case_reports)


def reference_token_replay(packets, expected, *, bpe_file=DEFAULT_BPE, tokenizer_root=DEFAULT_TOKENIZER):
    """Replay the sealed offline reference; no independent-algorithm claim."""
    raw = read_bytes(bpe_file)
    need(len(raw) == BPE_BYTES and digest(raw) == BPE_SHA, "exact retained offline o200k BPE bytes required")
    ranks = {}
    for line in raw.splitlines():
        spelling, ordinal = line.split()
        token = base64.b64decode(spelling, validate=True)
        need(token not in ranks, "duplicate retained BPE spelling")
        ranks[token] = int(ordinal)
    need(len(ranks) == len(set(ranks.values())) == 199998, "exact reviewed BPE vocabulary required")
    pattern = "|".join([
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r"\p{N}{1,3}", r" ?[^\s\p{L}\p{N}]+[\r\n/]*", r"\s*[\r\n]+", r"\s+(?!\S)", r"\s+",
    ])
    special = {"<|endoftext|>": 199999, "<|endofprompt|>": 200018}
    vocabulary = hashlib.sha256(canonical({"name": "o200k_base", "pattern": pattern,
                                          "special_tokens": special}))
    for spelling, ordinal in sorted(ranks.items(), key=lambda item: item[1]):
        vocabulary.update(ordinal.to_bytes(4, "big")); vocabulary.update(len(spelling).to_bytes(4, "big"))
        vocabulary.update(spelling)
    need(vocabulary.hexdigest() == VOCABULARY_SHA, "retained reference vocabulary/pattern/special table differs")
    root = Path(tokenizer_root).resolve(strict=True)
    sys.path.insert(0, str(root)); sys.dont_write_bytecode = True
    need(importlib.metadata.version("tiktoken") == "0.13.0", "pinned reference tiktoken version required")
    import tiktoken
    import tiktoken.core
    import tiktoken._tiktoken
    software_pins = []
    for module in (tiktoken, tiktoken.core, tiktoken._tiktoken):
        source = Path(module.__file__).resolve(strict=True)
        need(source.is_relative_to(root), "reference tokenizer loaded from another supplied environment")
        software_pins.append(pin(source))
    encoding = tiktoken.Encoding("o200k_base", pat_str=pattern, mergeable_ranks=ranks, special_tokens=special)
    measures = {}
    for name, packet in packets.items():
        text = packet.decode("utf-8")
        encoded = encoding.encode(text, allowed_special=set(), disallowed_special=())
        need(encoding.decode(encoded) == text, "offline reference token replay was not lossless")
        measures[name] = {"bytes": len(packet), "sha256": digest(packet), "tokens": len(encoded)}
        same(measures[name], expected[name], "offline reference token replay " + name)
    return {"offline_reference_token_replay_verified": True,
            "token_algorithm_independently_implemented": False, "measures": measures,
            "bpe": pin(Path(bpe_file).resolve(strict=True)), "reference_software": software_pins,
            "vocabulary_sha256": VOCABULARY_SHA}


def verify_command_receipt(path, expected_argv, *, empty_stdout=False):
    row = read_json(path)
    same(row["argv"], expected_argv, "exact owned disposal command")
    need(type(row["returncode"]) is int and row["returncode"] == 0 and row["timed_out"] is False
         and row["freeze_error"] is None and row["owned_cleanup_only"] is True,
         "exact owned disposal command failed")
    for stream in ("stdout", "stderr"):
        check_pin(row[stream], selected_path=Path(path).with_suffix("." + stream))
    if empty_stdout:
        zero(row["stdout"]["bytes"], "removed container listing bytes")


def verify_case(case, selected, *, replay_tokens=True, bpe_file=DEFAULT_BPE, tokenizer_root=DEFAULT_TOKENIZER):
    need(case in REQUIRED_CASES, "explicit selected case required")
    selected = Path(selected).resolve(strict=True)
    if selected.is_file():
        need(selected.name == "result.json", "only explicit original result.json may select a case")
        actual = selected.parent
    else:
        actual = selected if (selected / "result.json").is_file() else selected / "actual-start-01"
    actual = actual.resolve(strict=True)
    public, result_path = actual / "public", actual / "result.json"
    result = read_json(result_path)
    need(result["schema"] == "admitted-budget-actual-owner-invocation@1" and result["qualified"] is True
         and result["owner_execution"]["qualified"] is True and result["owner_execution"]["failure"] is None,
         "original actual owner invocation did not qualify")
    summary = read_json(public / "summary.json")
    same(summary, result["actual_summary"], "original public summary")
    need(summary["case"] == case and re.fullmatch(re.escape(case) + r"-[0-9]{2,4}", summary["run_tag"]),
         "selected case/original run tag differs")
    need(summary["native_admitted_benchmark_runtime_START_used"] is True
         and type(summary["actual_native_START_calls"]) is int and summary["actual_native_START_calls"] == 1,
         "every selected case requires its own single actual admitted START")
    for value in (result, summary):
        zero(value["provider_calls"], "actual provider calls"); zero(value["training_steps"], "actual training steps")
        need(value["source_body_executed"] is False, "source execution ceiling violated")
    for key in FALSE_CEILINGS:
        if key in summary:
            need(summary[key] is False, "public summary exceeds declared qualification ceiling")
    need(summary["worker_JSON_emitter_independently_proved"] is False, "native log ownership cannot prove JSON emitter")
    exports = verify_public_exports(result, public)
    freeze = check_pin(result["runtime_freeze"])
    manifest, signature = read_json(public / "native-launch-manifest.json"), read_json(public / "native-launch-signature.json")
    _DATA.verify_signature(manifest, signature)
    same(read_json(public / "native-admission.json"), manifest["local_admission"], "public native admission")
    need(manifest["coordination_attempt_safety_cap"] == 1
         and type(manifest["coordination_attempt_safety_cap"]) is int,
         "native campaign has an unsupported attempt allowance")
    budget_state = read_json(public / "final-budget-state.json")
    budget = verify_budget(budget_state, case)
    same(budget["policy"], manifest["checked_observer_budget_scope"]["budget_policy"], "signed native budget policy")
    same(budget_state["binding"], manifest["checked_observer_budget_scope"]["budget_binding"], "signed original budget binding")
    if budget["event"] is not None:
        preparation = read_json(public / "native-budget-preparation.json")
        _DATA.verify_cid(preparation, "preparation_cid")
        same(preparation["event"], budget["event"], "original prepared and finally retained coding event")
        need(preparation["basis"]["task_cid"] == manifest["checked_observer_budget_scope"]["task_cid"],
             "original charged event preparation belongs to another signed task")
        same(summary["whole_coding_input"], {key: budget["event"]["rendered_input"][key] for key in ("bytes", "sha256", "tokens")},
             "public declared complete coding input")
        same(summary["new_content"], {key: budget["event"]["new_content"][key] for key in ("bytes", "sha256", "tokens")},
             "public declared new coding content")
    start_stop = verify_stop(read_json(public / "native-START.json"), read_json(public / "native-STOP.json"),
                             read_json(public / "native-cleanup.json"), manifest)
    verify_resources(summary["resources_after"])
    owner_cleanup = read_json(public / "outer-owner-cleanup.json")
    need(owner_cleanup["errors"] == [] and owner_cleanup["original_budget_closed"] is True
         and owner_cleanup["scope_closed"] is True, "original owner cleanup remains incomplete")
    close = read_json(public / "checked-context-dispatch-broker-close-receipt.json")
    for key in ("broker_closed", "socket_removed", "thread_joined", "isolated_cleanup_checked", "git_metadata_custody_closed"):
        need(close[key] is True, "original broker cleanup is incomplete")
    records = read_json(public / "broker-signed-dispatch-evidence-after-close.json")
    materials = read_json(public / "broker-dispatch-evidence-materials-after-close.json")
    dispatch = _DATA.verify_public_bundle(public, records, materials, allow_incomplete=case != "baseline")
    for record in records:
        need(record["payload"]["task"]["attempt_number"] == 1, "another native attempt entered selected scope")
    observations = read_json(public / "broker-observations-after-close.json")
    if case == "baseline":
        need(dispatch["complete_dispatch_join_verified"] is True and len(records) == 2
             and [row["payload"]["phase"] for row in records] == ["wrapper_released", "worker_released"]
             and summary["actual_native_worker_observer_invocations"] == 1
             and summary["original_owner_budget_committed"] is True, "baseline lacks its single signed actual observer")
        need(not any(row["status"] in ("refused", "evidence_unavailable") for row in observations),
             "baseline retained a dispatch/signing refusal")
        commit = read_json(public / "native-budget-commit.json")
        _DATA.verify_cid(commit, "commit_cid")
        need(commit["local_reservation_committed"] is True and commit["event_cid"] == budget["event_cid"]
             and commit["context_cid"] == _DATA.structured_cid(manifest["checked_observer_budget_scope"]),
             "original reservation commit task/event/context differs")
        observed = read_json(public / "native-observation.json")
        observation_raw = canonical(observed)
        need(commit["observation_json"].encode("utf-8") == observation_raw
             and commit["observation_sha256"] == digest(observation_raw)
             and type(commit["observation_bytes"]) is int and commit["observation_bytes"] == len(observation_raw),
             "original budget commit parsed observation differs")
    else:
        control, qualification = read_json(public / "native-fault-control.json"), read_json(public / "native-fault-refusal-qualification.json")
        need(control["case"] == qualification["case"] == case and control["triggered"] is True
             and qualification["qualified"] is True, "actual selected fault control did not qualify")
        for key in ("authority_substituted", "claim_or_fence_mutated", "deadline_extended"):
            need(control[key] is False, "fault control replaced authority or extended deadline")
        zero(control["worker_callbacks"], "fault control worker callbacks")
        zero(control["provider_calls"], "fault control provider calls")
        zero(summary["actual_native_worker_observer_invocations"], "fault actual worker observers")
        need(summary["original_owner_budget_committed"] is False and close["worker_birth_observed"] is False,
             "fault committed or authorized a worker")
        need(not any(row["status"] == "spawned" or row.get("wrapper_birth_observed") is True
                     or row.get("worker_birth_observed") is True for row in observations),
             "fault retained an authorized wrapper or worker birth")
        need(all(row["payload"]["phase"] == "prepared" and row["payload"]["kernel"]["wrapper"] is None
                 and row["payload"]["kernel"]["worker"] is None for row in records),
             "fault signed an unauthorized birth/release")
        refusals = [row for row in observations if row["status"] == "refused"]
        need(len(refusals) == 1, "one original actual broker refusal required")
        same(qualification["original_broker_refusal"], refusals[0], "original fault refusal")
        same(qualification["original_budget_totals"], budget["totals"], "fault conservative retained totals")
        need(qualification["wrapper_birth_observed"] is False and qualification["worker_birth_observed"] is False,
             "fault qualification promotes a birth")
        if case == "exceeded-budget":
            need(refusals[0]["error_type"] == "SemanticContextBudgetExceeded"
                 and qualification["budget_rejected_before_reservation"] is True
                 and qualification["conservative_charge_retained"] is False, "native budget denial was not pre-reservation")
        else:
            same(control["charged_totals"], budget["totals"], "fault initial charge")
            need(control["charged_event_cid"] == budget["event_cid"]
                 and qualification["conservative_charge_retained"] is True,
                 "uncertain/refused native dispatch refunded original event")
        if case == "disconnect":
            need(control["exact_pidfd_used"] is True and control["original_channel_closed_by_real_peer_exit"] is True
                 and close["ambiguous_birth_possible"] is True
                 and refusals[0]["unacknowledged_child_birth_possible"] is True,
                 "disconnect lost original peer or conservative possible-birth state")
    disposal = result["container_disposal"]
    need(disposal["container_absent"] is True and disposal["only_exact_owned_container_removed"] is True,
         "original owned container disposal is incomplete")
    zero(disposal["stop_returncode"], "owned container stop returncode")
    zero(disposal["remove_returncode"], "owned container remove returncode")
    zero(result["outer_worker_cleanup_returncode"], "outer worker cleanup returncode")
    identity = read_json(actual / "container-identity.json")
    same(identity["argv"], ["docker", "inspect", "--format", "{{.Id}}", result["container"]], "original owned container lookup")
    need(identity["returncode"] == 0 and type(identity["returncode"]) is int
         and identity["timed_out"] is False and identity["freeze_error"] is None,
         "original owned container lookup failed")
    check_pin(identity["stdout"], selected_path=actual / "container-identity.stdout")
    container_id = read_bytes(actual / "container-identity.stdout").decode("ascii").strip()
    need(re.fullmatch(r"[0-9a-f]{64}", container_id), "exact original container ID required")
    need(container_id == manifest["checked_observer_budget_scope"]["boundary"]["container_id"],
         "disposed container differs from original signed worker boundary")
    verify_command_receipt(actual / "outer-worker-cleanup.json", ["docker", "exec", "--user", "supervisor", container_id,
        "/usr/bin/sudo", "-n", "-u", "benchmarkworker", "--", "/opt/ipfs-supervisor/bin/worker-entry", "--cleanup"])
    verify_command_receipt(actual / "container-stop.json", ["docker", "stop", "--time", "10", container_id])
    verify_command_receipt(actual / "container-remove.json", ["docker", "rm", container_id])
    verify_command_receipt(actual / "container-absence.json", ["docker", "ps", "-aq", "--filter", "id=" + container_id], empty_stdout=True)
    token_review = {"offline_reference_token_replay_verified": False, "token_algorithm_independently_implemented": False}
    if case == "baseline" and replay_tokens:
        event = budget["event"]
        packets = {"complete_coding_input": read_bytes(public / "native-complete-input.txt"),
                   "new_content": event["new_content"]["text"].encode("utf-8")}
        expected = {"complete_coding_input": {key: event["rendered_input"][key] for key in ("bytes", "sha256", "tokens")},
                    "new_content": {key: event["new_content"][key] for key in ("bytes", "sha256", "tokens")}}
        token_review = reference_token_replay(packets, expected, bpe_file=bpe_file, tokenizer_root=tokenizer_root)
    return {"case": case, "run_tag": summary["run_tag"], "qualified": True,
        "result": pin(result_path), "runtime_freeze": freeze, "public_exports": exports,
        "actual_native_START_calls": 1, "start_stop": start_stop, "budget": {key: value for key, value in budget.items() if key != "event"},
        "dispatch_review": dispatch, "container_id": container_id, "owned_container_absent": True,
        "resources_empty": True, "token_review": token_review, **FALSE_CEILINGS}


def verify_campaign(selected, *, replay_tokens=True, bpe_file=DEFAULT_BPE, tokenizer_root=DEFAULT_TOKENIZER):
    need(type(selected) is dict and 1 <= len(selected) <= len(REQUIRED_CASES)
         and set(selected) <= REQUIRED_CASES, "explicit reviewed selected case roots required")
    reports = [verify_case(case, selected[case], replay_tokens=replay_tokens, bpe_file=bpe_file,
                           tokenizer_root=tokenizer_root) for case in sorted(selected)]
    need(len({row["container_id"] for row in reports}) == len(reports), "selected cases reused an owned container")
    need(len({row["start_stop"]["run_id"] for row in reports}) == len(reports), "selected cases reused a native START run")
    need(len({row["runtime_freeze"]["sha256"] for row in reports}) == 1, "selected campaign uses different source freezes")
    qualified = assess_coverage(reports)
    return {"schema": "independent-public-dispatch-campaign-review@1", "qualified": qualified,
        "required_cases": sorted(REQUIRED_CASES), "selected_cases": sorted(selected),
        "missing_cases": sorted(REQUIRED_CASES - set(selected)), "case_reports": reports,
        "actual_native_START_calls": len(reports), "nonce_replay_live_qualified": False,
        "nonce_replay_status": "open; no authentic live replay case selected",
        "selected_six_case_coverage_complete": qualified, "full_dispatch_fault_matrix_complete": False,
        "supplied_public_inputs_are_trust_inputs": True,
        "token_algorithm_independently_implemented": False, **FALSE_CEILINGS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True, metavar="NAME=ROOT_OR_RESULT")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--skip-reference-token-replay", action="store_true")
    parser.add_argument("--bpe-file", type=Path, default=DEFAULT_BPE)
    parser.add_argument("--tokenizer-root", type=Path, default=DEFAULT_TOKENIZER)
    args = parser.parse_args(argv)
    try:
        selected = {}
        for value in args.case:
            name, location = value.split("=", 1)
            need(name not in selected, "duplicate explicitly selected case")
            selected[name] = Path(location)
        result = verify_campaign(selected, replay_tokens=not args.skip_reference_token_replay,
                                 bpe_file=args.bpe_file, tokenizer_root=args.tokenizer_root)
        status = 0 if result["qualified"] else 1
    except (VerificationError, OSError, KeyError, IndexError, ValueError, TypeError, UnicodeError, ImportError) as error:
        result = {"schema": "independent-public-dispatch-campaign-review@1", "qualified": False,
                  "error_type": type(error).__name__, "reason": str(error), **FALSE_CEILINGS}
        status = 1
    raw = json.dumps(result, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    if args.report is not None:
        fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    sys.stdout.buffer.write(raw)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
