"""Qualify actual native prompt compilation and reviewed readback without providers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main(args):
    fixture = args.fixture.absolute()
    output = args.output.absolute()
    output.mkdir(mode=0o755, exist_ok=False)
    os.umask(0o022)
    started = time.monotonic()
    receipt = {"schema": "reviewed-source-native-worker-readback-qualification@1", "qualified": False,
        "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
        "target_module_imports": 0, "official_task_verifier_invocations": 0,
        "full_task_or_source_equivalence_or_convergence_proved": False,
        "provider_total_session_token_savings_established": False}
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    def refuse_network(*unused_args, **unused_kwargs):
        raise AssertionError("worker readback probe cannot connect to a network")
    socket.socket.connect = socket.socket.connect_ex = refuse_network
    try:
        qualification = json.loads((fixture / "qualification.json").read_bytes())
        assert qualification["qualified"]
        repository = Path(qualification["repository"])
        state = Path(qualification["state"])
        os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(output / "fresh-compilation-metadata.duckdb")
        os.environ.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
        os.environ["IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR"] = str(output / "fresh-orchestration")
        from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
        from ipfs_accelerate_py.agent_supervisor.runtime.task_context_bundle import load_task_context_nomination
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalTask, TodoImplementationDaemon
        from ipfs_accelerate_py.agent_supervisor.context.context_compiler import render_context_capsule
        from ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction import prepare_public_instruction_context, load_public_instruction
        from ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation import encode_semantic_router_prompt
        from ipfs_accelerate_py.agent_supervisor.runtime.verified_code_retrieval_projection import extract_verified_public_instruction_source
        from ipfs_accelerate_py.agent_supervisor.runtime.reviewed_source_nomination_context import load_reviewed_source_nomination_context, HEADER
        from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
        prepared = prep._load_prepared(state)
        admission = json.loads((state / "admission.json").read_bytes())
        verified = prep.local.verify_local_benchmark_admission(admission, initial=True)
        selected = verified["graph"].tasks[0]
        with IntentRepository(state / "intent.duckdb", install_schema=False) as intent:
            row = intent.plan_projection(task_cids=[selected.task_cid])["tasks"][0]
        assert row["status"] == "ready"
        metadata = load_task_context_nomination(repository=repository,
            artifact=qualification["context_bundle"]["artifact"], expected_sha256=qualification["context_bundle"]["sha256"],
            task_id=selected.task_key, task_cid=selected.task_cid)
        daemon_state = state.parent / ("daemon-readback-" + output.name)
        daemon_state.mkdir(mode=0o700)
        todo = daemon_state / "public-task-projection.todo.md"
        todo.write_text("# Native signed task projection qualification\n")
        daemon = TodoImplementationDaemon(todo_path=todo, state_path=daemon_state / "tasks.json",
            strategy_path=daemon_state / "strategy.json", events_path=daemon_state / "events.jsonl",
            repo_root=repository, task_header_prefix="## TB-")
        task = PortalTask(task_id=selected.task_key, title=selected.objective, status="ready",
            completion="manual", priority="P0", track="context",
            outputs=[item["path"] for item in row["outputs"]],
            validation=[shlex.join(item["argv"]) for item in row["validations"]],
            acceptance="\n".join(str(item.get("text", item.get("criterion", ""))) for item in row["acceptance"]),
            canonical_task_key=selected.task_key, canonical_task_cid=selected.task_cid,
            metadata={**metadata, "Database task cid": selected.task_cid,
                "Database task revision": str(row["revision"]), "Provider role": "deterministic-only"})
        compiled = daemon._compile_implementation_context(task, attempt=1)
        prompt = render_context_capsule(compiled.capsule)
        (output / "native-public-prompt.txt").write_text(prompt)
        assert selected.task_key == compiled.capsule.objective_id
        assert selected.task_cid == compiled.capsule.objective_revision
        if args.public_instruction_artifact is not None:
            assert args.public_instruction_sha256
            public = {"artifact": str(args.public_instruction_artifact), "sha256": args.public_instruction_sha256}
        else:
            assert not args.public_instruction_sha256
            public = prepare_public_instruction_context(repository=repository, admission=admission,
                task_cid=selected.task_cid, source_path=prep.INSTRUCTION,
                expected_source_sha256=verified["manifest"]["sources"][prep.INSTRUCTION]["sha256"])
        worktree = output / "allocated-checkout"
        if args.installed_worker:
            from benchmarks.agent_supervisor.container_coding.terminal_container_supervisor import WORKTREES
            worktree = WORKTREES / ("nomination-readback-" + output.name)
        subprocess.run(["git", "-C", str(repository), "-c", "core.hooksPath=/dev/null", "worktree", "add", "--detach", str(worktree), "HEAD"],
            check=True, capture_output=True)
        instruction, instruction_receipt = load_public_instruction(artifact=Path(public["artifact"]),
            expected_sha256=public["sha256"], task_cid=selected.task_cid, prompt=prompt,
            workspace=worktree, repository=repository, requirements_transport="compact")
        source_text = extract_verified_public_instruction_source(instruction, instruction_receipt)
        assert source_text == prepared["query"]
        semantic = encode_semantic_router_prompt(prompt=prompt, repository=repository)
        semantic_verification = {key: semantic.receipt[key] for key in (
            "task_id", "scope_cid", "semantic_root_cid", "semantic_sha256", "native_prompt_sha256", "native_prompt_bytes", "freshness_checked")}
        block, inclusion, guard = load_reviewed_source_nomination_context(prompt=prompt, repository=repository,
            source_text=source_text, instruction_receipt=instruction_receipt, semantic_verification=semantic_verification)
        assert block.startswith(HEADER) and len(block.encode()) <= 8192
        catalog = json.loads(block[len(HEADER):])
        assert len(catalog["rows"]) == 3 and len(catalog["residual_requirements"]) == 19
        assert all(item["residual"] for item in catalog["residual_requirements"])
        (output / "reviewed-catalog-block.txt").write_text(block)
        emit = {"schema": "public-reviewed-source-readback-worker-input@1", "catalog": catalog,
            "repository": str(repository), "private_owner_state": str(state),
            "original_source_sha256": sha((repository / "bottle.py").read_bytes()),
            "installed_worker": args.installed_worker}
        worker_input = output / "worker-input.json"
        worker_input.write_bytes(wire(emit))
        guard()
        if args.installed_worker:
            argv = ["/opt/ipfs-supervisor/bin/validation-worker", sys.executable, "-P", str(Path(__file__).resolve()),
                "--worker-input", str(worker_input)]
        else:
            argv = [sys.executable, "-P", str(Path(__file__).resolve()), "--worker-input", str(worker_input)]
        call = subprocess.run(argv, cwd=worktree, capture_output=True, timeout=120, env=dict(os.environ))
        (output / "worker.stdout.json").write_bytes(call.stdout)
        (output / "worker.stderr.txt").write_bytes(call.stderr)
        assert call.returncode == 0, (call.returncode, call.stderr.decode()[:1024])
        worker = json.loads(call.stdout)
        assert worker["qualified"] and worker["provider_calls"] == 0
        guard()
        receipt.update(qualified=True, native_full_daemon_context_compilation=True,
            task_projection_origin="Actual signed graph and ready native task projected into PortalTask; no daemon scheduling/claim or provider dispatch.",
            actual_signed_public_instruction_replay=True, actual_semantic_source_verification=True,
            catalog_inclusion=inclusion, complete_catalog_bytes=len(block.encode()),
            native_prompt_bytes=len(prompt.encode()), public_instruction_block_bytes=len(instruction.encode()),
            all_nineteen_requirements_residual=True, worker=worker,
            installed_worker_boundary=args.installed_worker,
            full_driver_prepare_review_resume_qualified=False,
            historical_full_input_auditor_updated_for_catalog=False,
            native_task_status="ready", task_id=selected.task_key, task_cid=selected.task_cid,
            literal_instruction_sha256=sha(source_text.encode()), context_bundle=qualification["context_bundle"])
    except Exception as exc:
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)[:2048]}
        raise
    finally:
        socket.socket.connect, socket.socket.connect_ex = original_connect, original_connect_ex
        receipt["seconds"] = time.monotonic() - started
        (output / "qualification.json").write_bytes(wire(receipt))


def worker_main(path):
    input_raw = path.read_bytes()
    supplied = json.loads(input_raw)
    catalog = supplied["catalog"]
    if supplied["installed_worker"]:
        assert os.getuid() == os.geteuid() == 1001
        try:
            fd = os.open(Path(supplied["private_owner_state"]) / "intent.duckdb", os.O_RDONLY | os.O_NOFOLLOW)
        except PermissionError:
            owner_denied = True
        else:
            os.close(fd)
            raise AssertionError("private owner state was accessible to the worker")
    else:
        owner_denied = None
    repository = Path(supplied["repository"])
    original = (repository / "bottle.py").read_bytes()
    assert sha(original) == supplied["original_source_sha256"]
    prefix = shlex.split(catalog["inspector"]["command_prefix"])
    cases = []
    responses = []
    for item, mode in [(item, "source") for item in catalog["rows"]] + [(catalog["rows"][0], "facts")]:
        argv = prefix + ["--row-id", item["row_id"], "--question", "Inspect this separately reviewed public symbol", "--mode", mode, "--max-bytes", "8192"]
        call = subprocess.run(argv, capture_output=True, timeout=30, env=dict(os.environ))
        assert call.returncode == 0 and not call.stderr, (call.returncode, call.stderr.decode()[:1024])
        value = json.loads(call.stdout)
        assert value["schema"] == "supervisor-intent-source-inspection@1"
        assert value["complete"] and value["content_complete_in_page"]
        assert len(call.stdout) <= 8192
        if mode == "source":
            span = value["bindings"]["source_span"]
            assert value["content_text"].encode() == original[span["byte_start"]:span["byte_end"]]
        else:
            assert isinstance(json.loads(value["content_text"]), dict)
        responses.append(value)
        cases.append({"symbol": item["qualified_symbol"], "mode": mode, "complete_output_bytes": len(call.stdout),
            "output_sha256": sha(call.stdout), "content_bytes": len(value["content_text"].encode()),
            "exact_source_or_canonical_fact_reconstruction": True})
    refusals = []
    for flag, wrong in [("--task-cid", "task:foreign-public-qualification"), ("--review-sha256", "0" * 64)]:
        changed = list(prefix)
        changed[changed.index(flag) + 1] = wrong
        call = subprocess.run(changed + ["--row-id", catalog["rows"][0]["row_id"], "--question", "Independent pin negative control"],
            capture_output=True, timeout=30, env=dict(os.environ))
        assert call.returncode == 2 and not call.stdout
        refusals.append({"substituted_flag": flag, "returncode": 2, "stdout_bytes": 0})
    assert (repository / "bottle.py").read_bytes() == original
    print(wire({"qualified": True, "schema": "public-reviewed-source-readback-worker@1",
        "uid": os.getuid(), "euid": os.geteuid(), "installed_worker": supplied["installed_worker"],
        "private_owner_database_open_denied_without_body_read": owner_denied,
        "exact_advertised_prefix_used": True, "independent_pin_refusals": refusals,
        "cases": cases, "responses": responses, "original_source_unchanged": True,
        "provider_calls": 0, "target_module_imports": 0}).decode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--installed-worker", action="store_true")
    parser.add_argument("--worker-input", type=Path)
    parser.add_argument("--public-instruction-artifact", type=Path)
    parser.add_argument("--public-instruction-sha256", default="")
    arguments = parser.parse_args()
    if arguments.worker_input is not None:
        worker_main(arguments.worker_input)
    else:
        assert arguments.fixture is not None and arguments.output is not None
        main(arguments)
