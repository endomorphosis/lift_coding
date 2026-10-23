"""Run actual signed preparation, symbolic admission and reviewed context once.

Only a fresh Git copy of public Bottle/instruction is inspected. Signing APIs
own their new private keys; this driver never reads or exports key bodies.
No model, provider, target import, task verifier, training or prover executes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(path, value):
    path.write_bytes(wire(value))


def main(args):
    output = args.output.absolute()
    output.mkdir(exist_ok=False, mode=0o755)
    os.umask(0o022)
    repository = output / "repository"
    repository.mkdir(mode=0o755)
    # All database names are NEW within this exact qualification namespace.
    os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(output / "fresh-native-metadata.duckdb")
    os.environ.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
    os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(output / "fresh-orchestration")
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    def refuse_network(*unused_args, **unused_kwargs):
        raise AssertionError("public context qualification cannot connect to a network")
    socket.socket.connect = socket.socket.connect_ex = refuse_network
    started = time.monotonic()
    receipt = {"schema": "actual-admitted-public-nomination-context@1", "qualified": False,
        "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
        "target_module_imports": 0, "official_task_verifier_invocations": 0,
        "admission_or_hydration_stubs": False, "private_key_bodies_read_or_exported": False,
        "existing_owner_database_read": False, "events": []}
    def event(label):
        row = {"stage": label, "seconds": round(time.monotonic() - started, 3)}
        receipt["events"].append(row)
        print(json.dumps(row), flush=True)
    try:
        source = args.source.read_bytes()
        instruction_raw = args.instruction.read_bytes()
        assert sha(source) == "761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba"
        assert sha(instruction_raw) == "89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a"
        (repository / "bottle.py").write_bytes(source)
        instruction = output / "instruction.txt"
        instruction.write_bytes(instruction_raw)
        for argv in (["git", "init", "-q"], ["git", "add", "bottle.py"],
                     ["git", "-c", "user.name=Public fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "Public Bottle baseline"]):
            subprocess.run(argv, cwd=repository, check=True, capture_output=True)
        from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
        from benchmarks.agent_supervisor.container_coding.terminal_initial_context import load_initial_context
        from benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract import build_terminal_public_intent_profile
        from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier import prepare_code_retrieval_frontier
        from ipfs_accelerate_py.agent_supervisor.runtime import code_source_inspection as reader
        from ipfs_accelerate_py.agent_supervisor.runtime.intent_source_nomination import build_intent_source_nomination, REVIEW_SCHEMA
        from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
        from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
        from ipfs_accelerate_py.agent_supervisor.runtime.task_context_bundle import load_task_context_nomination
        profile = build_terminal_public_intent_profile(source_text=instruction_raw.decode())
        contract_path = output / "reviewed-intent-contract.json"
        emit(contract_path, profile["contract"])
        state = output / "private-owner-state"
        event("prepare-public-source-and-independent-domain-declarations")
        prepared = prep.prepare(repository=repository, instruction=instruction, state=state,
            disable_intent_autoencoder=True, intent_requirement_contract=contract_path)
        manifest_before = sha(wire(prepared["manifest"]))
        event("real-initial-native-AST-lexical-semantic-empty-world-context")
        initial = prep.initial_context(state=state, train_autoencoder=False)
        event("real-symbolic-plan-and-signed-admission-no-provider")
        planned = prep.plan(state, provider_callable=None)
        assert planned["qualified"], planned.get("failure")
        assert planned["provider_calls"] == 0 and planned["planning_strategy"] == "intent_symbolic"
        admission = json.loads((state / "admission.json").read_bytes())
        verified = prep.local.verify_local_benchmark_admission(admission, initial=True)
        task = verified["graph"].tasks[0]
        loaded = load_initial_context(state=state, prepared=prepared, require_empty_owner=False)
        with IntentRepository(state / "intent.duckdb", install_schema=False) as intent:
            projection = intent.plan_projection(task_cids=[task.task_cid])
        tasks = projection["tasks"]
        assert len(tasks) == 1 and tasks[0]["status"] == "ready"
        task_revision = str(tasks[0]["revision"])
        metadata = loaded["descriptor"]["metadata"]
        event("bind-separate-authored-review-to-current-task-and-initial-index")
        frontier = prepare_code_retrieval_frontier(repository=repository,
            task_cid=task.task_cid, task_id=task.task_key, task_revision=task_revision,
            repository_id=loaded["descriptor"]["repository_id"], tree_id=loaded["semantic"]["scope_cid"],
            source_artifact=metadata["Code retrieval artifact"], source_sha256=metadata["Code retrieval sha256"],
            output=repository / ".runtime/review-binding-frontier")
        fm = frontier["metadata"]
        with public_replay_without_metadata():
            evidence = reader._capture_native_evidence(repository,
                fm["Code retrieval frontier artifact"], fm["Code retrieval frontier sha256"],
                task.task_key, task.task_cid,
                metadata["Code retrieval artifact"], metadata["Code retrieval sha256"])
        generic = build_intent_source_nomination(contract=prepared["intent_requirement_contract"],
            source_text=prepared["query"], task_id=task.task_key, task_cid=task.task_cid,
            task_revision=task_revision, repository_id=evidence["spec"]["repository_id"],
            tree_id=evidence["spec"]["tree_id"], snapshot=evidence["snapshot"], source_by_path=evidence["sources"])
        def requirement(statement):
            rows = [row["native_requirement"]["requirement_id"] for row in generic["requirements"]
                    if statement in row["native_requirement"]["statement_ids"]]
            assert len(rows) == 1
            return rows[0]
        review = {"schema": REVIEW_SCHEMA, "bindings": generic["bindings"],
            "review_ref": "authored:admitted-public-header-source-exploration@1",
            "selectors": [{"requirement_id": requirement(statement), "path": "bottle.py", "qualified_symbol": symbol}
                for symbol, statement in [("bottle._hkey", "public-bottle:statement:invalid-input-error"),
                    ("bottle._hval", "public-bottle:statement:invalid-input-error"),
                    ("bottle.HeaderDict", "public-bottle:statement:identify-bottle")]]}
        review_path = output / "authored-source-review.json"
        emit(review_path, review)
        # Only now is the separately authored review valid for the current task/index.
        event("real-admitted-context-with-reviewed-source-attachment")
        context = prep.context(state=state, source_nomination_review=review_path,
            source_nomination_review_sha256=sha(wire(review)))
        bundle = context["context_bundle"]
        nominated = load_task_context_nomination(repository=repository,
            artifact=bundle["artifact"], expected_sha256=bundle["sha256"],
            task_id=task.task_key, task_cid=task.task_cid)
        assert nominated["Code source nomination artifact"] == context["source_nomination"]["artifact"]
        assert nominated["Code source nomination sha256"] == context["source_nomination"]["sha256"]
        assert sha(wire(prep._load_prepared(state)["manifest"])) == manifest_before
        assert (repository / "bottle.py").read_bytes() == source
        assert prepared["query"].encode() == instruction_raw
        emit(output / "public-context-result.json", context)
        emit(output / "public-nomination-metadata.json", nominated)
        receipt.update(qualified=True, repository=str(repository), state=str(state),
            task_id=task.task_key, task_cid=task.task_cid, task_revision=task_revision,
            symbolic_plan_admission_qualified=True, planning_provider_calls=planned["provider_calls"],
            signed_manifest_unchanged=True, original_bottle_and_literal_instruction_unchanged=True,
            context_attachment_scope=context["source_nomination_attachment_scope"],
            symbolic_planner_current_facts_added=context["symbolic_planner_current_facts_added"],
            context_bundle=bundle, source_nomination=context["source_nomination"],
            nomination_metadata=nominated, native_index_id=initial["index_id"],
            all_task_requirements_residual=True, reviewed_selectors_authenticate_task_meaning=False,
            source_semantics_verified=False, task_completed=False, official_reward=None,
            installed_worker_qualified=False, automatic_router_consumption_qualified=False,
            model_convergence_proved=False, provider_total_token_savings_established=False)
        event("qualified-actual-admission-and-context")
    except Exception as exc:
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)[:2048]}
        raise
    finally:
        socket.socket.connect, socket.socket.connect_ex = original_connect, original_connect_ex
        receipt["seconds"] = time.monotonic() - started
        emit(output / "qualification.json", receipt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("output", "source", "instruction"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())
