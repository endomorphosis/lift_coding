"""Actual current-owner IntentIR/capsule/service preview and offline token comparison."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

STAGE = Path(__file__).resolve().parent
ACTUAL = STAGE / "actual-public-intent-01"
RUN = STAGE / sys.argv[1]
os.umask(0o077)
assert not RUN.exists()
RUN.mkdir(mode=0o700)
os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(RUN / "meta-index.duckdb")
os.environ["IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB"] = str(RUN / "pytest-seal.duckdb")
os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(RUN / "orchestration")
os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp/data-gym-cache"

from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import _open, _scheduler
from benchmarks.agent_supervisor.container_coding import terminal_call_intent_planning as planning
from benchmarks.agent_supervisor.container_coding import terminal_call_intent_profile as profiles
from benchmarks.agent_supervisor.container_coding import terminal_call_proof_capsule as capsules
from benchmarks.agent_supervisor.container_coding import terminal_revision_proof_cache as revisions
from benchmarks.agent_supervisor.container_coding import terminal_input_token_comparison as tokenizer
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import PlanAuthorityRoots
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured

def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()

def save(name, value):
    path = RUN / name
    with path.open("xb") as stream:
        stream.write(wire(value))
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

def retained(path):
    _, raw, guard = revisions._file(path)
    return json.loads(raw), guard

prepared, prepared_guard = retained(ACTUAL / "prepared.json")
model_record, model_guard = retained(ACTUAL / "model/result.json")
callee_proof, callee_guard = retained(Path(model_record["callee"]["native_proof"]["path"]))
head = CodebaseHead.from_dict(prepared["head"])
repository = ACTUAL / "repository"
prompt = "Under closed-caller-model@1, caller.py::twice(n) must return n + 2."
profile = profiles.build_call_intent_profile(prompt=prompt)
save("intent-profile.json", profile)
policy = {name: {"schema": "authored-call-review-policy@1", "role": name,
    "production_activated": False, "worker_allowed": False, "model_calls": 0,
    "training_allowed": False, "mutation_authority": False}
    for name in ("policy", "legal", "security", "provider", "usage", "configuration")}
policy["catalog"] = {"schema": "authored-call-review-catalog@1", "operations": [list(x) for x in planning.OPERATIONS],
    "scope": "conditional evidence review only", "completion_authority": False, "mutation_authority": False}
save("policy.json", policy)
policy_value, policy_guard = retained(RUN / "policy.json")
profile_value, profile_guard = retained(RUN / "intent-profile.json")
scheduler = _scheduler(ACTUAL / "resources.json")
connection, index = _open(ACTUAL)
observations = []

def observe_policy(_request):
    # Re-read pinned policy and native IntentIR artifacts, then independently
    # obtain the selected native head/program root. Never echo request.roots.
    policy_guard()
    profile_guard()
    current_policy = json.loads((RUN / "policy.json").read_bytes())
    current_profile = json.loads((RUN / "intent-profile.json").read_bytes())
    assert current_policy == policy_value and current_profile == profile_value
    profiles.validate_call_intent_profile(current_profile, prompt=prompt)
    current = index.observe_current(repository, expected_head=head, scheduler=scheduler)
    program = current.manifest.semantic_state.state_cid
    catalog = cid_for_structured(current_policy["catalog"])
    ir = planning.intent_root(current_profile)
    roles = lambda key: cid_for_structured(current_policy[key])
    roots = PlanAuthorityRoots(repository_id=head.repository_id, repository_root_cid=head.snapshot_cid,
        dirty_worktree_root=head.snapshot_cid, task_source_id=cid_for_structured({"intent": ir, "catalog": catalog}),
        task_source_revision=catalog, policy_root=roles("policy"), intent_ir_root=ir,
        legal_ir_root=roles("legal"), security_ir_root=roles("security"), program_root=program,
        capability_catalog_root=catalog, provider_catalog_root=roles("provider"),
        usage_policy_root=roles("usage"), configuration_root=roles("configuration"))
    observations.append(roots.to_dict())
    return roots

try:
    query = capsules.query_call_capsule_rows(output=ACTUAL / "model/metadata",
        expected_metadata=model_record["metadata"], expected_head=head.to_dict())
    basis = dict(prompt=prompt, intent_profile=profile, model_record=model_record, query=query, callee_proof=callee_proof)
    save("query.json", query)
    capsule = capsules.build_call_proof_capsule(**basis)
    save("capsule.json", capsule)
    roots = observe_policy(None)
    common = dict(index=index, repository=repository, expected_head=head, tool_policy=prepared["tool_policy"],
        policy_roots=roots, policy_observer=observe_policy, scheduler=scheduler)
    encoding = tokenizer._load_tokenizer()
    results, packets, measures = {}, {}, {}
    for representation in ("expanded", "capsule"):
        packet = planning.build_call_context_packet(representation=representation, **basis)
        normalized = planning.normalize_call_context_packet(packet, **basis)
        assert normalized == capsule
        path = RUN / (representation + "-packet.json")
        path.write_bytes(packet.encode("utf-8"))
        measures[representation] = tokenizer._measure(packet, encoding)
        result = planning.preview_current_call_intent_plan(**common, **basis)
        results[representation] = result
        save(representation + "-preview.json", result)
        packets[representation] = {"path": str(path), **measures[representation]}
    a, b = results["expanded"], results["capsule"]
    stable = ["input_snapshot_cid", "obligation_graph_cid", "candidate_portfolio_cid", "execution_plan_cid", "plan_root_cid"]
    assert all(a["native_preview"]["preview"][key] == b["native_preview"]["preview"][key] for key in stable)
    assert a["selected_task_ids"] == b["selected_task_ids"] and len(a["selected_task_ids"]) == 3
    controls = []

    def refuse(name, callback):
        try:
            callback()
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            controls.append({"name": name, "rejected": True, "error_type": type(exc).__name__, "reason": str(exc)[:500]})
        else:
            raise AssertionError("negative control accepted: " + name)

    for changed_prompt in (
        prompt.replace("n + 2", "n + 3"), prompt.replace("caller.py", "callee.py"),
        prompt + " Also accept bool.", prompt.replace("closed-caller-model@1", "python-runtime@1")):
        def changed(text=changed_prompt):
            altered = dict(basis, prompt=text, intent_profile=profiles.build_call_intent_profile(prompt=text))
            capsules.build_call_proof_capsule(**altered)
        refuse("changed-prompt:" + changed_prompt, changed)
    bad = deepcopy(capsule)
    bad["assumptions"] = {}
    bad["capsule_id"] = cid_for_structured({k: v for k, v in bad.items() if k != "capsule_id"})
    refuse("rebound-capsule-omitted-assumptions", lambda: capsules.validate_call_proof_capsule(bad, **basis))
    bad_packet = json.loads(planning.build_call_context_packet(representation="capsule", **basis))
    bad_packet["context"]["capsule"]["completion_authority"] = True
    refuse("packet-invented-completion-authority", lambda: planning.normalize_call_context_packet(wire(bad_packet).decode(), **basis))
    changed_head = deepcopy(head.to_dict())
    changed_head["generation"] += 1
    refuse("same-snapshot-wrong-native-generation", lambda: planning.preview_current_call_intent_plan(
        **dict(common, expected_head=CodebaseHead.from_dict(changed_head)), **basis))
    source = repository / "caller.py"
    original_source = source.read_bytes()
    try:
        source.write_bytes(original_source.replace(b"increment(increment(n))", b"increment(n)"))
        refuse("current-source-changed-under-proof", lambda: planning.preview_current_call_intent_plan(**common, **basis))
    finally:
        source.write_bytes(original_source)
    # Same bytes under a new inode must fail retained proof-object custody,
    # even though the detached data and SHA labels are unchanged.
    object_path = Path(model_record["caller_object"]["path"])
    old_object = object_path.read_bytes()
    held = object_path.with_name("held-original-for-negative-control.olean")
    swapped = []
    def swapping_observer(request):
        roots_now = observe_policy(request)
        if not swapped:
            object_path.rename(held)
            object_path.write_bytes(old_object)
            object_path.chmod(0o600)
            swapped.append(True)
        return roots_now
    try:
        refuse("same-byte-proof-object-replaced-during-preview", lambda: planning.preview_current_call_intent_plan(
            **dict(common, policy_observer=swapping_observer), **basis))
        assert swapped
    finally:
        if held.exists():
            object_path.unlink()
            held.rename(object_path)
    assert object_path.read_bytes() == old_object
    final = planning.preview_current_call_intent_plan(**common, **basis)
    save("final-current-preview.json", final)
    prepared_guard(); model_guard(); callee_guard(); policy_guard(); profile_guard()
    state = scheduler.snapshot()
    assert state["active_lease_count"] == state["waiting_request_count"] == 0
    summary = {"schema": "terminal-call-intent-live-experiment@1", "qualified": True,
        "head": head.to_dict(), "capsule_id": capsule["capsule_id"], "query_id": query["query_id"],
        "selected_task_ids": final["selected_task_ids"], "native_stages": final["native_preview"]["preview"]["stage_results"],
        "packets": packets, "stable_native_identity_fields": stable,
        "normalized_capsules_equal": True, "native_plan_identities_equal": True,
        "offline_input_token_reduction": measures["expanded"]["tokens"] - measures["capsule"]["tokens"],
        "offline_reduction_basis_points": 10_000 * (measures["expanded"]["tokens"] - measures["capsule"]["tokens"]) // measures["expanded"]["tokens"],
        "measurement_scope": "whole offline context packets on authored fixture; both expand against same retained current evidence",
        "provider_token_savings_measured": False, "provider_calls": 0, "training_steps": 0,
        "source_body_executed": False, "checker_invocations_during_planning": 0,
        "fresh_qualification_lean_processes": 3, "controls": controls,
        "policy_observation_count": len(observations), "resources_after": state,
        "quack_transport_used": False, "network_isolation_enforced": False,
        "runtime_behavior_verified": False, "source_origin_proved": False,
        "full_task_satisfaction": False, "convergence_proved": False,
        "production_admitted": False, "worker_launched": False}
    save("summary.json", summary)
    print(json.dumps({"qualified": True, "tokens": measures, "reduction_basis_points": summary["offline_reduction_basis_points"],
        "negative_controls": len(controls), "review_tasks": len(final["selected_task_ids"])}), flush=True)
except Exception as exc:
    save("failure.json", {"error_type": type(exc).__name__, "reason": str(exc), "qualified": False,
        "provider_calls": 0, "training_steps": 0, "source_body_executed": False})
    raise
finally:
    connection.close()
