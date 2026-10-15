#!/usr/bin/env python3
"""Read-only four-way presentation census from retained public producer inputs.

No runtime dispatch, source changes, reindexing, provider calls or containers.
Only this script and a new content-free result belong to the exploration.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.metadata
import inspect
import io
import json
from pathlib import Path
import subprocess
import sys

FROZEN_HEAD = "4c49239351126303035b0521e9ba71d3bf20e576"
TASKS = ("tune-mjcf", "llm-inference-batching-scheduler")
MODES = ("semantic", "query-reference", "common-bindings", "common-bindings+query-reference")
MAX_BYTES = 2_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("bounded regular retained artifact required")
    return path.read_bytes()


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def require(check):
    if not check:
        raise ValueError("retained identity or exact restoration check failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tokenizer-cache", type=Path)
    args = parser.parse_args()
    source, retained = args.source.resolve(strict=True), args.retained.resolve(strict=True)
    require(git_head(source) == FROZEN_HEAD and not args.output.exists())
    sys.path.insert(0, str(source))
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        from ipfs_accelerate_py.agent_supervisor.runtime import semantic_router_translation as native
        from ipfs_accelerate_py.agent_supervisor.runtime import semantic_metadata_view as metadata
        from ipfs_accelerate_py.agent_supervisor.runtime import semantic_query_reference as query
        from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner as runner
        from ipfs_accelerate_py.agent_supervisor.runtime import coding_reply_contract as reply
        from ipfs_accelerate_py.agent_supervisor.runtime import semantic_context_runtime as context
        from ipfs_accelerate_py.agent_supervisor.runtime import supervisor_meta_index as meta_index
        from ipfs_accelerate_py.agent_supervisor.semantic_state import datasets_adapter
        from ipfs_accelerate_py.agent_supervisor.context import context_contracts
        from benchmarks.agent_supervisor.container_coding import terminal_source_view_experiment as counters
        from ipfs_datasets_py.logic.software_contracts.semantic_state import models as dataset_models

    modules = (native, metadata, query, runner, reply, context, meta_index, datasets_adapter,
               context_contracts, counters, dataset_models)
    code = {module.__name__: {"path": str(Path(inspect.getfile(module)).resolve()),
        "sha256": sha(read(inspect.getfile(module)))} for module in modules}
    require(all(source in Path(row["path"]).parents for name, row in code.items()
                if not name.startswith("ipfs_datasets_py.")))
    counter, tokenizer = counters.local_token_counter(args.tokenizer_cache)
    overall_raw = read(retained / "qualification.json")
    overall = json.loads(overall_raw)
    require(counter is not None and tokenizer == overall["local_tokenizer"])
    result = {"schema": "terminal-query-metadata-composition-census@1", "candidate_only": True,
        "runtime_dispatch_qualified": False, "provider_calls": 0, "containers_started": 0,
        "reindexing_performed": False, "operational_freshness_established": False,
        "hidden_task_material_read": False, "prompt_or_source_text_exported": False,
        "provider_usage_tokens": None, "task_solved": None, "completion_authority": False,
        "source_commit": FROZEN_HEAD, "source_code_bindings": code,
        "script_sha256": sha(read(__file__)), "python_version": sys.version.split()[0],
        "tiktoken_version": importlib.metadata.version("tiktoken"), "local_tokenizer": tokenizer,
        "retained_qualification_sha256": sha(overall_raw), "tasks": [],
        "measurement_scope": "Complete historical coding user input: exact production workspace advisory and ordinary reply instructions. Separate native output schema, provider framing, reasoning and tools excluded.",
        "limitations": ["No policy compatibility or provider-dispatch qualification is implied.",
            "Metadata composition is currently refused by runtime policy; rows are pure codec candidates.",
            "Local o200k proxy counts are not provider usage, billing or total-session savings.",
            "Identical retained public source selection only; no signed planning or Doctor/public appendix experiment.",
            "Historical replay verifies retained evidence without establishing current source freshness."]}

    for task in TASKS:
        directory = retained / task
        tracked = {name: read(directory / name) for name in (
            "qualification.json", "native-context-input.json", "legacy-receipt.json", "reference-receipt.json")}
        qualification = json.loads(tracked["qualification.json"])
        legacy = json.loads(tracked["legacy-receipt.json"])
        reference = json.loads(tracked["reference-receipt.json"])
        prompt = canonical(json.loads(tracked["native-context-input.json"]))
        row = {"task_name": task, "arms": [], "retained_artifact_sha256": {
            key: sha(value) for key, value in tracked.items()}, "candidate_only": True}
        result["tasks"].append(row)
        try:
            require(sha(prompt) == qualification["native_prompt_sha256"] == legacy["native_prompt_sha256"])
            require(sha(tracked["native-context-input.json"]) == qualification["native_context_input_sha256"])
            require(qualification["qualified"] is True and overall["qualified"] is True)
            require(legacy["semantic_translation"] is not None and legacy.get("public_instruction") is None
                and legacy.get("doctor_residual_context") is None
                and legacy.get("source_view_policy") is None and legacy.get("tool_output_policy") is None)
            workspace = Path(legacy["workspace"])
            require(workspace == directory / "allocated-worktree" and not workspace.exists())
            with meta_index.public_replay_without_metadata(), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                encoded = native.replay_semantic_router_prompt_for_audit(prompt=prompt,
                    repository=directory / "repository", transport_schema=native.TRANSPORT_SCHEMA)
            require(encoded.freshness_checked is False and encoded.table.translation_cid
                    == legacy["semantic_translation"]["translation_cid"])
            table = encoded.table.to_dict()
            row.update(source_manifest_sha256=sha(canonical(table["source_manifest"])),
                source_manifest=table["source_manifest"], translation_cid=encoded.table.translation_cid,
                semantic_root_cid=table["semantic_root_cid"], scope_cid=table["scope_cid"],
                semantic_artifact_sha256=table["semantic_sha256"],
                workspace_binding_sha256=sha(str(workspace)), historical_workspace_absent=True)
            artifact = directory / "repository" / table["semantic_artifact"]
            artifact_raw = read(artifact)
            require(sha(artifact_raw) == qualification["canonical_payload_sha256"])

            for mode in MODES:
                arm = {"mode": mode, "candidate_only": True, "runtime_dispatch_qualified": False}
                row["arms"].append(arm)
                try:
                    wire = encoded.provider_prompt
                    metadata_view = query_view = None
                    if mode.startswith("common-bindings"):
                        metadata_view = metadata.project_semantic_metadata_view(wire)
                        wire = metadata_view.provider_prompt
                    if "query-reference" in mode:
                        query_view = query.project_semantic_query_reference(provider_prompt=wire)
                        wire = query_view.provider_prompt
                    restored = wire
                    if query_view is not None:
                        restored = query.restore_semantic_query_reference(provider_prompt=restored, receipt=query_view.receipt)
                    if metadata_view is not None:
                        require(restored == metadata_view.provider_prompt)
                        restored = metadata.restore_semantic_metadata_view(provider_prompt=restored, receipt=metadata_view.receipt)
                    require(restored == encoded.provider_prompt)
                    model, advisory = runner.render_model_prompt(prompt=wire, purpose="coding",
                        workspace=workspace, semantic_transport=True)
                    model, reply_receipt = reply.apply_coding_reply_contract(model_prompt=model,
                        mode="ordinary-completion@1", purpose="coding", provider="codex_cli")
                    require(sha(advisory) == legacy["workspace_advisory_sha256"]
                            and len(advisory.encode()) == legacy["workspace_advisory_bytes"])
                    arm.update(status="measured", exact_semantic_transport_restored=True,
                        full_input_sha256=sha(model), full_input_bytes=len(model.encode()),
                        full_input_proxy_tokens=counter(model), router_sha256=sha(wire), router_bytes=len(wire.encode()),
                        workspace_advisory_sha256=sha(advisory), workspace_advisory_bytes=len(advisory.encode()),
                        ordinary_reply_instruction_sha256=reply_receipt["instruction_sha256"],
                        ordinary_reply_instruction_bytes=reply_receipt["instruction_bytes"],
                        excluded_native_output_schema_sha256=reply_receipt["native_output_schema_sha256"],
                        excluded_native_output_schema_bytes=reply_receipt["native_output_schema_bytes"],
                        query_reference_count=query_view.receipt["reference_count"] if query_view else 0,
                        query_receipt_sha256=sha(query_view.receipt_json) if query_view else None,
                        metadata_receipt_sha256=sha(metadata_view.receipt_json) if metadata_view else None,
                        shared_metadata_field_paths=metadata_view.receipt["shared_field_paths"] if metadata_view else [])
                    if mode in ("semantic", "query-reference"):
                        expected = legacy if mode == "semantic" else reference
                        expected_arm = qualification["arms"][0 if mode == "semantic" else 1]
                        require(arm["full_input_sha256"] == expected["model_prompt_sha256"] == expected_arm["full_input_sha256"]
                            and arm["full_input_bytes"] == expected["model_prompt_bytes"] == expected_arm["full_input_bytes"]
                            and arm["full_input_proxy_tokens"] == expected_arm["full_input_proxy_tokens"]
                            and sha(wire) == expected["router_prompt_sha256"]
                            and len(wire.encode()) == expected["router_prompt_bytes"])
                        require(all(expected["coding_reply_contract"][key] == value
                            for key, value in reply_receipt.items() if key != "response_validated"))
                        if query_view:
                            require(query_view.receipt == expected["query_reference_view"])
                        arm["retained_full_input_and_counts_exact"] = True
                except (ValueError, TypeError, KeyError) as error:
                    arm.update(status="refused", reason_code=getattr(error, "code", "exact_composition_or_binding_refused"),
                        error_type=type(error).__name__, full_input_bytes=None, full_input_proxy_tokens=None)

            by_mode = {arm["mode"]: arm for arm in row["arms"]}
            for arm in row["arms"]:
                if arm["status"] != "measured":
                    continue
                arm["changes_vs"] = {}
                for baseline in ("semantic", "query-reference"):
                    base = by_mode[baseline]
                    if base["status"] == "measured":
                        arm["changes_vs"][baseline] = {"bytes": arm["full_input_bytes"] - base["full_input_bytes"],
                            "proxy_tokens": arm["full_input_proxy_tokens"] - base["full_input_proxy_tokens"]}
            row["retained_baselines_exact"] = all(by_mode[mode].get("retained_full_input_and_counts_exact") is True
                for mode in ("semantic", "query-reference"))
            row["all_four_measured_and_restored"] = all(arm["status"] == "measured" for arm in row["arms"])
            row["retained_artifacts_unchanged"] = (all(read(directory / name) == raw for name, raw in tracked.items())
                and read(artifact) == artifact_raw)
        except (ValueError, TypeError, KeyError, OSError) as error:
            row.update(status="refused", reason_code=getattr(error, "code", "retained_input_replay_refused"),
                error_type=type(error).__name__, retained_baselines_exact=False)
    result["code_bindings_unchanged"] = all(sha(read(row["path"])) == row["sha256"] for row in code.values())
    result["frozen_head_unchanged"] = git_head(source) == FROZEN_HEAD
    result["retained_qualification_unchanged"] = read(retained / "qualification.json") == overall_raw
    result["observations_valid"] = (result["code_bindings_unchanged"] and result["frozen_head_unchanged"]
        and result["retained_qualification_unchanged"] and all(row.get("retained_baselines_exact") is True
        and row.get("retained_artifacts_unchanged") is True for row in result["tasks"]))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(canonical({"schema": result["schema"], "observations_valid": result["observations_valid"],
        "runtime_dispatch_qualified": False, "output": str(args.output), "tasks": [
            {"task": row["task_name"], "arms": [{key: arm.get(key) for key in (
                "mode", "status", "full_input_bytes", "full_input_proxy_tokens", "reason_code")}
                for arm in row["arms"]]} for row in result["tasks"]]}))
    return 0 if result["observations_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
