"""Audit exact native/catalog/literal model inputs from a fresh signed fixture.

Receipts are observational fixtures built from the real producer/renderers, not
provider transcripts or provider calls. All copies and source canaries are new
public qualification artifacts; private signing keys are never inspected.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import socket
import stat
import subprocess
import sys
import time


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def custody(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
        info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def imported_producer_join(args):
    """Join actual imported files to the independently pinned installed archive."""
    if args.runtime_manifest is None:
        assert args.runtime_manifest_sha256 is None
        return {"installed_archive_join_performed": False, "scope": "host fixture"}, lambda: None
    assert args.runtime_manifest_sha256 is not None
    manifest_path = args.runtime_manifest.absolute()
    root = manifest_path.parent
    manifest_stat = manifest_path.lstat()
    assert stat.S_ISREG(manifest_stat.st_mode) and manifest_stat.st_uid == 0
    assert manifest_stat.st_nlink == 1 and not manifest_stat.st_mode & 0o022
    assert manifest_stat.st_size < 8 * 1024 * 1024
    raw = manifest_path.read_bytes()
    assert sha(raw) == args.runtime_manifest_sha256
    manifest = json.loads(raw)
    assert manifest["runtime_python_version"] == ".".join(map(str, sys.version_info[:3]))
    records = {row["path"]: row for row in manifest["files"]}
    assert len(records) == len(manifest["files"])
    names = [
        "benchmarks.agent_supervisor.container_coding.terminal_context_audit",
        "benchmarks.agent_supervisor.container_coding.terminal_indexed_preparation",
        "ipfs_accelerate_py.agent_supervisor.runtime.reviewed_source_nomination_audit",
        "ipfs_accelerate_py.agent_supervisor.runtime.reviewed_source_nomination_context",
        "ipfs_accelerate_py.agent_supervisor.runtime.intent_source_inspection",
        "ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner",
        "ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation",
        "ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction",
        "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon",
    ]
    snapshots, joined = [], []
    for name in names:
        module = importlib.import_module(name)
        path = Path(module.__file__).absolute()
        assert path.resolve(strict=True) == path
        relative = path.relative_to(root).as_posix()
        assert relative.startswith("source/")
        parent = path.parent
        while True:
            parent_info = parent.lstat()
            assert stat.S_ISDIR(parent_info.st_mode) and parent_info.st_uid == 0 and not parent_info.st_mode & 0o022
            if parent == root:
                break
            parent = parent.parent
        expected = records[relative]
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
        assert not info.st_mode & 0o022 and info.st_size <= 4 * 1024 * 1024
        with path.open("rb") as stream:
            body = stream.read(info.st_size + 1)
        assert len(body) == info.st_size == expected["bytes"]
        assert sha(body) == expected["sha256"] and stat.S_IMODE(info.st_mode) == expected["mode"]
        snapshots.append((path, info, expected))
        joined.append({"module": name, "path": relative, "bytes": len(body), "sha256": sha(body),
            "protected_root_owned_origin": True, "actual_import_matches_archive": True})
    def guard():
        assert custody(manifest_path.lstat()) == custody(manifest_stat) and sha(manifest_path.read_bytes()) == args.runtime_manifest_sha256
        for path, info, expected in snapshots:
            assert custody(path.lstat()) == custody(info)
            with path.open("rb") as stream:
                body = stream.read(info.st_size + 1)
            assert len(body) == expected["bytes"] and sha(body) == expected["sha256"]
    return {"installed_archive_join_performed": True, "runtime_manifest_sha256": sha(raw),
        "archive_sha256": manifest["archive_sha256"], "actual_imported_producers": joined,
        "python_version": manifest["runtime_python_version"]}, guard


def main(args):
    output = args.output.absolute()
    assert output.resolve(strict=False) == output
    output.mkdir(mode=0o755, exist_ok=False)
    os.umask(0o022)
    started = time.monotonic()
    result = {"schema": "actual-reviewed-catalog-model-input-audit@1", "qualified": False,
        "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
        "target_module_imports": 0, "official_task_verifier_invocations": 0,
        "provider_transcripts_or_private_key_bodies_read": False,
        "observational_provider_free_receipts": True,
        "provider_total_session_token_savings_established": False,
        "all_nineteen_task_requirements_residual": False}
    connect, connect_ex = socket.socket.connect, socket.socket.connect_ex
    def refuse_network(*unused_args, **unused_kwargs):
        raise AssertionError("qualification cannot connect to a network")
    socket.socket.connect = socket.socket.connect_ex = refuse_network
    try:
        fixture = args.fixture.absolute()
        qualified = json.loads((fixture / "qualification.json").read_bytes())
        assert qualified["qualified"]
        repository, state = Path(qualified["repository"]), Path(qualified["state"])
        os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(output / "fresh-compilation-metadata.duckdb")
        os.environ.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
        from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
        from benchmarks.agent_supervisor.container_coding import terminal_context_audit as audit
        from ipfs_accelerate_py.agent_supervisor.runtime.task_context_bundle import load_task_context_nomination
        from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import TodoImplementationDaemon, PortalTask
        from ipfs_accelerate_py.agent_supervisor.context.context_compiler import render_context_capsule
        from ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction import prepare_public_instruction_context, load_public_instruction
        from ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation import encode_semantic_router_prompt
        from ipfs_accelerate_py.agent_supervisor.runtime.reviewed_source_nomination_context import load_reviewed_source_nomination_context
        from ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner import render_model_prompt
        from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
        from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as projection
        provenance, provenance_guard = imported_producer_join(args)
        result["imported_producer_provenance"] = provenance
        prepared = prep._load_prepared(state)
        admission = json.loads((state / "admission.json").read_bytes())
        verified = prep.local.verify_local_benchmark_admission(admission, initial=True)
        task = verified["graph"].tasks[0]
        with IntentRepository(state / "intent.duckdb", install_schema=False) as intent:
            row = intent.plan_projection(task_cids=[task.task_cid])["tasks"][0]
        assert row["status"] == "ready"
        context_raw = (state / "context-result.json").read_bytes()
        expected = json.loads(context_raw)
        assert "metadata" not in expected
        nominated = load_task_context_nomination(repository=repository,
            artifact=expected["context_bundle"]["artifact"], expected_sha256=expected["context_bundle"]["sha256"],
            task_id=task.task_key, task_cid=task.task_cid)
        private = state.parent / ("catalog-audit-" + output.name)
        private.mkdir(mode=0o700, exist_ok=False)
        todo = private / "public-projection.todo.md"
        todo.write_text("# Source-bound native projection qualification\n")
        daemon = TodoImplementationDaemon(todo_path=todo, state_path=private / "daemon-tasks.json",
            strategy_path=private / "strategy.json", events_path=private / "events.jsonl", repo_root=repository)
        portal = PortalTask(task_id=task.task_key, title=task.objective, status="ready", completion="manual",
            priority="P0", track="context", outputs=[item["path"] for item in row["outputs"]],
            validation=[shlex.join(item["argv"]) for item in row["validations"]],
            acceptance="\n".join(str(item.get("text", item.get("criterion", ""))) for item in row["acceptance"]),
            canonical_task_key=task.task_key, canonical_task_cid=task.task_cid,
            metadata={**nominated, "Database task cid": task.task_cid, "Database task revision": str(row["revision"]),
                "Provider role": "deterministic-only"})
        compiled = daemon._compile_implementation_context(portal, attempt=1)
        native = render_context_capsule(compiled.capsule)
        audit_state = private / "audit-state"
        (audit_state / "run").mkdir(parents=True, mode=0o700)
        (audit_state / "prepared.json").write_bytes((state / "prepared.json").read_bytes())
        (audit_state / "context-result.json").write_bytes(context_raw)
        (audit_state / "run/public-base-context-capsule.json").write_text(compiled.capsule.to_json())
        assert (audit_state / "context-result.json").read_bytes() == context_raw
        workspace_root = private / "allocated-worktrees"
        workspace_root.mkdir(mode=0o700)
        workspace = workspace_root / "coding"
        subprocess.run(["git", "-C", str(repository), "worktree", "add", "--detach", str(workspace), "HEAD"], check=True, capture_output=True)
        source_original = (repository / "bottle.py").read_bytes()
        public = prepare_public_instruction_context(repository=repository, admission=admission, task_cid=task.task_cid,
            source_path=prep.INSTRUCTION, expected_source_sha256=verified["manifest"]["sources"][prep.INSTRUCTION]["sha256"])
        public_text, public_receipt = load_public_instruction(artifact=Path(public["artifact"]),
            expected_sha256=public["sha256"], task_cid=task.task_cid, prompt=native, repository=repository,
            workspace=workspace, requirements_transport="compact")
        source_text = projection.extract_verified_public_instruction_source(public_text, public_receipt)
        encoded = encode_semantic_router_prompt(prompt=native, repository=repository)
        neutral = {"schema": "semantic-router-source-verification@1", "freshness_checked": True,
            **{key: encoded.receipt[key] for key in audit.SEMANTIC_BINDINGS}}
        catalog, catalog_receipt, guard = load_reviewed_source_nomination_context(prompt=native, repository=repository,
            source_text=source_text, instruction_receipt=public_receipt, semantic_verification=neutral)
        catalog_value = json.loads(catalog[catalog.index('{'):])
        residual = catalog_value["residual_requirements"]
        assert len(residual) == 19 and all(row["residual"] is True for row in residual)
        assert len({row["requirement_id"] for row in residual}) == 19
        assert all(type(row["modality"]) is str and row["modality"] for row in residual)
        assert sum(row["mandatory"] is True for row in residual) == 17
        assert sum(row["mandatory"] is False for row in residual) == 2
        assert {row["requirement_id"] for row in residual if row["mandatory"] is True} == set(public_receipt["intent_requirements"]["requirement_ids"])
        assert catalog_receipt["residual_requirement_count"] == 19
        result["all_nineteen_task_requirements_residual"] = True
        decoder = projection.decoder_command_prefix(repository=repository, source_path=public_receipt["source_path"],
            source_sha256=public_receipt["source_sha256"], native_prompt_sha256=sha(native.encode()))
        compact, current_projection = projection.project_verified_code_retrieval_prompt(prompt=native,
            repository=repository, source_text=source_text, decoder_command=decoder)
        legacy, legacy_projection = codec.project_code_retrieval_prompt(native, source_text,
            decoder_command=decoder, guidance_version=1)
        legacy_projection = {**legacy_projection, "native_verification": current_projection["native_verification"], "decoder_command": decoder}
        selections = [("expanded", native, None, "native", None),
            ("compact_v2", compact, current_projection, "native", None),
            ("legacy_v1", legacy, legacy_projection, "native", None),
            ("identifiers", encoded.provider_prompt, None, "identifiers", dict(encoded.receipt))]
        receipts, models = {}, {}
        for mode, selected, code_projection, transport, translation in selections:
            router = selected + catalog + public_text
            model, advisory = render_model_prompt(prompt=router, purpose="coding", workspace=workspace,
                semantic_transport=translation is not None,
                code_retrieval_projected=(code_projection or {}).get("selected_transport") == "compact")
            receipts[mode] = {"schema": "router-implementation-invocation@1", "phase": "coding", "purpose": "coding",
                "invocation_id": "public-audit-" + mode, "workspace": str(workspace),
                "prompt_sha256": sha(native.encode()), "prompt_bytes": len(native.encode()),
                "native_prompt_sha256": sha(native.encode()), "native_prompt_bytes": len(native.encode()),
                "router_prompt_sha256": sha(router.encode()), "router_prompt_bytes": len(router.encode()),
                "model_prompt_sha256": sha(model.encode()), "model_prompt_bytes": len(model.encode()),
                "workspace_advisory_sha256": sha(advisory.encode()), "workspace_advisory_bytes": len(advisory.encode()),
                "semantic_transport": transport, "semantic_translation": translation, "semantic_context_verification": neutral,
                "doctor_residual_context": None, "public_instruction": public_receipt,
                "code_retrieval_codec": "expanded" if code_projection is None else "compact",
                "code_retrieval_projection": code_projection, "reviewed_source_nomination_context": catalog_receipt,
                "status": "failed", "provider_call_not_made": True}
            models[mode] = {"model_bytes": len(model.encode()), "model_sha256": sha(model.encode()),
                "catalog_bytes": len(catalog.encode()), "catalog_sha256": sha(catalog.encode()),
                "public_instruction_block_bytes": len(public_text.encode()),
                "selected_retrieval_transport": (code_projection or {}).get("selected_transport", "expanded")}
            (output / (mode + "-receipt.json")).write_bytes(wire(receipts[mode]))
            (output / (mode + "-model-input.txt")).write_text(model)
        guard()
        observations = []
        result["observations"] = observations
        def collect(label, changed, retired):
            for mode, original in receipts.items():
                receipt = dict(original, invocation_id="public-" + label + "-" + mode,
                    status="copied_publication_fixture" if changed else "failed", provider_call_not_made=True)
                observed = audit.collect_terminal_context_audit(state=audit_state, receipts=[receipt],
                    workspace_root=workspace_root, timeout_seconds=30.)
                observations.append({"case": label, "mode": mode, "source_changed": changed,
                    "workspace_retired": retired, "audit": observed})
                assert observed["status"] == "verified_all_observed_model_inputs", (label, mode, observed)
        collect("current", False, False)
        subprocess.run(["git", "-C", str(repository), "worktree", "remove", "--force", str(workspace)], check=True, capture_output=True)
        assert not workspace.exists()
        collect("failed_no_publication", False, True)
        # Controlled public copied-publication canary; no task fix or target execution.
        (repository / "bottle.py").write_bytes(source_original + b"\n# Public historical audit publication canary.\n")
        assert (repository / "bottle.py").read_bytes() != source_original
        collect("copied_publication", True, True)
        negatives = []
        result["negatives"] = negatives
        for name, change in [("missing_inclusion", lambda row: row.pop("reviewed_source_nomination_context")),
                ("null_inclusion", lambda row: row.update(reviewed_source_nomination_context=None)),
                ("wrong_catalog_digest", lambda row: row["reviewed_source_nomination_context"].update(block_sha256="0" * 64)),
                ("wrong_catalog_count", lambda row: row["reviewed_source_nomination_context"].update(row_count=0))]:
            negative = deepcopy(receipts["expanded"])
            change(negative)
            observed = audit.collect_terminal_context_audit(state=audit_state, receipts=[negative], workspace_root=workspace_root, timeout_seconds=30.)
            assert observed.get("all_observed_coding_inputs_verified") is not True
            negatives.append({"case": name, "status": observed["status"], "refused_as_verified_input": True})
        result.update(actual_signed_admission_and_context=True,
            actual_native_daemon_compilation=True, genuine_context_result_bytes_unchanged=True,
            invented_top_level_metadata=False, original_signed_baseline_source_sha256=sha(source_original),
            published_source_canary_sha256=sha((repository / "bottle.py").read_bytes()),
            original_literal_instruction_sha256=sha(source_text.encode()),
            catalog_bytes=len(catalog.encode()), models=models, observations=observations, negatives=negatives,
            complete_model_inputs_are_provider_free_observational_fixtures=True,
            current_owner_or_source_freshness_proved_by_historical_audit=False,
            full_task_satisfaction_or_source_equivalence_or_convergence_proved=False,
            same_trusted_runtime_paths_required=True, cross_runtime_historical_replay_supported=False)
        provenance_guard()
        result["qualified"] = True
    except Exception as exc:
        result["qualified"] = False
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)[:2048]}
        raise
    finally:
        socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
        result["seconds"] = time.monotonic() - started
        (output / "qualification.json").write_bytes(wire(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path)
    parser.add_argument("--runtime-manifest-sha256")
    main(parser.parse_args())
