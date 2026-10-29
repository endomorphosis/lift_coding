#!/usr/bin/env python3
"""One admitted, scoped model repair. The original producer still owns validation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from swissknife_visual_functional_llm import (
    _atomic_json, _json, _parse_json, _paths, _read, _relative, _snapshot,
    apply_validated_edits, model_call_limits, validate_edit_shapes, validate_model_receipt,
)

SCHEMA = "swissknife.visual-functional-recovery.v1"
CONTEXT_SCHEMA = "agent-supervisor/semantic-recovery-context@1"
CONTEXT_ENV = "AGENT_SUPERVISOR_RECOVERY_CONTEXT_PATH"
NAMESPACE = Path("data/agent_supervisor/swissknife_visual_functional")
HEX = re.compile(r"[0-9a-f]{64}")
MAX_FEEDBACK_CONTEXT_BYTES = 65536
# Read-only metadata identity only; this never widens edit or prompt snapshots.
CANONICAL_TASK_SPEC = "config/swissknife_visual_functional_tasks.json"
MAX_TASK_SPEC_IDENTITY_BYTES = 4 * 1024 * 1024


class RecoveryError(ValueError):
    pass


def require(value, message):
    if not value:
        raise RecoveryError(message)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def byte_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime(root: Path, profile: dict) -> Path:
    relative = Path(_relative(root, profile["runtimeRoot"]))
    require(relative.is_relative_to(NAMESPACE), "recovery runtime is outside the SVF namespace")
    return root / relative


def artifact(root: Path, path: Path) -> dict:
    name = _relative(root, path)
    data = _read(root, name, 4 * 1024 * 1024)
    return {"path": name, "sha256": byte_sha(data), "bytes": len(data)}


def read_artifact(root: Path, value: dict, scope: Path) -> bytes:
    require(type(value) is dict and set(value) == {"path", "sha256", "bytes"}, "invalid recovery artifact")
    path = root / _relative(root, value["path"])
    require(path.is_relative_to(scope) and path != scope, "recovery artifact escaped its immutable attempt")
    data = _read(root, value["path"], 4 * 1024 * 1024)
    require(type(value["bytes"]) is int and len(data) == value["bytes"] and byte_sha(data) == value["sha256"], "recovery artifact bytes changed")
    return data


def edit_paths(root: Path, profile: dict, task: dict, packet_path: str | None = None) -> list[str]:
    original = _paths(root, task.get("edit_paths", []), 128)
    require(original, "recovery has no declared edit paths")
    explicit = "recovery_edit_paths" in task
    paths = _paths(root, task["recovery_edit_paths"], 128) if explicit else original
    require(paths and set(paths) <= set(original), "recovery_edit_paths must be a nonempty exact subset of task.edit_paths")
    protected = {str(profile.get(k) or "") for k in ("todoPath", "humanPlanPath", "objectivePath", "taskSpecPath", "appContractPath")}
    protected.update({packet_path or "", "config/swissknife_visual_functional_supervisor.json",
        "scripts/swissknife_visual_functional_worker.py", "scripts/swissknife_visual_functional_llm.py",
        "scripts/swissknife_visual_functional_recovery.py", "scripts/svf_recovery_canary.py"})
    selected = []
    for name in paths:
        path = Path(name)
        parts = set(path.parts)
        scenario = path.parent == Path("swissknife/test/e2e/functional-workflows") and path.suffix == ".json"
        allowed = (name not in protected and not name.startswith(("implementation_plan/", "config/"))
                and not name.startswith("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/")
                and not name.startswith("external/ipfs_accelerate/ipfs_accelerate_py/cli_runtime/")
                and name != "external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py"
                and (scenario or not parts.intersection({"test", "tests", ".git", "model-inputs", "model-invocations"}))
                and not path.name.startswith(("test_", "validate", "check-")) and ".test." not in path.name
                and not name.endswith((".todo.md", ".objectives.md")))
        campaign = runtime(root, profile)
        absolute = root / name
        if absolute.is_relative_to(campaign):
            allowed = allowed and (not absolute.is_relative_to(campaign / "state")
                    and not absolute.is_relative_to(campaign / "tasks")
                    and path.name not in {"owned-source-hashes.json", "latest.json", "receipt.json", "status.json"})
        require(allowed or not explicit, "explicit recovery path is a protected controller, board or validator")
        if allowed:
            selected.append(name)
    require(selected, "recovery has no non-validator edit paths")
    return selected


def validate_packet(root: Path, profile: dict, task: dict, packet: dict, packet_path: str) -> list[str]:
    fields = {"schema", "task_id", "producer_contract", "qualification_fingerprint", "admission_index", "recovery_limit",
              "source_before", "feedback_inputs", "failure_summary", "requires_inherited_lease_validation",
              "observation_only", "work_complete", "completion_authority"}
    require(type(packet) is dict and not set(packet) - fields and packet.get("schema") == CONTEXT_SCHEMA
            and packet.get("task_id") == task.get("task_id") and packet.get("observation_only") is True
            and packet.get("completion_authority") is False and packet.get("work_complete", False) is False,
            "invalid admitted recovery context")
    require(HEX.fullmatch(str(packet.get("producer_contract", ""))) and HEX.fullmatch(str(packet.get("qualification_fingerprint", ""))), "invalid recovery context identity")
    index, limit = packet.get("admission_index"), packet.get("recovery_limit")
    require(type(index) is int and type(limit) is int and 1 <= index <= limit <= 2, "recovery admission exceeds its finite budget")
    require(packet.get("requires_inherited_lease_validation", True) is True, "recovery requires inherited lease validation")
    for key, bound, nullable in (("source_before", 256, True), ("feedback_inputs", 32, False)):
        values = packet.get(key)
        require(type(values) is dict and 0 < len(values) <= bound, "invalid recovery hash-bound input map")
        _paths(root, list(values), bound)
        for value in values.values():
            require(nullable and value is None or type(value) is str and HEX.fullmatch(value), "invalid recovery input SHA-256")
    summary = packet.get("failure_summary")
    require(type(summary) is dict and not set(summary) - {"semantic_failures", "attempts_started", "last_stage", "last_exit_code"}, "failure summary must be body-free")
    for key, value in summary.items():
        require((type(value) is str and key == "last_stage" and re.fullmatch(r"[a-z_]{1,64}", value))
                or type(value) is int and -255 <= value <= 100000, "invalid typed recovery failure summary")
    paths = edit_paths(root, profile, task, packet_path)
    require(set(_paths(root, task.get("edit_paths", []), 128)) <= set(packet["source_before"]), "packet omits original declared edit source hashes")
    return paths


def current_hashes(root: Path, names) -> dict:
    result = {}
    for name in names:
        relative = _relative(root, name)
        if relative == CANONICAL_TASK_SPEC and (root / relative).exists():
            # Keep exact raw-byte identity without retaining/inlining its body.
            # _read still rejects symlinks, non-regular files and growth races.
            result[name] = byte_sha(_read(root, relative, MAX_TASK_SPEC_IDENTITY_BYTES))
        else:
            # Preserve ordinary 1MiB snapshots and missing-path/ancestor checks.
            result[name] = _snapshot(root, name)["sha256"]
    return result


def unchanged(root: Path, hashes: dict) -> None:
    require(current_hashes(root, hashes) == hashes, "recovery inputs changed since admission")


def journal_admission(root: Path, profile: dict, packet: dict, packet_path: str, *, state: str,
                      source_after: dict | None = None) -> dict:
    """Trust only the newest durable admission; packet possession is insufficient."""
    path = runtime(root, profile) / "state/lane_resume_attempts.semantic-recovery.json"
    journal = _parse_json(_read(root, _relative(root, path), 4 * 1024 * 1024).decode("utf-8"))
    require(type(journal) is dict and journal.get("schema") == "agent-supervisor/semantic-recovery-journal@1"
            and type(journal.get("tasks")) is dict, "recovery journal is invalid")
    task = journal["tasks"].get(packet["task_id"])
    require(type(task) is dict and type(task.get("spent")) is int
            and task["spent"] == packet["admission_index"] <= packet["recovery_limit"] <= 2,
            "recovery packet is not the current finite journal admission")
    history = task.get("history")
    require(type(history) is list and len(history) == task["spent"] and history
            and all(type(item) is dict for item in history), "recovery journal history is invalid")
    latest = history[-1]
    require(latest.get("state") == state and latest.get("producer_contract") == packet["producer_contract"]
            and latest.get("qualification_fingerprint") == packet["qualification_fingerprint"]
            and type(latest.get("recovery_limit")) is int and latest["recovery_limit"] == packet["recovery_limit"]
            and latest.get("completion_authority") is False
            and _relative(root, latest.get("context_path", "")) == _relative(root, packet_path),
            "latest recovery journal row does not authorize this context/state")
    require(latest.get("source_before") == packet["source_before"], "journal source admission differs from packet")
    if source_after is not None:
        recorded = latest.get("source_after")
        require(type(recorded) is dict and all(name in recorded and recorded[name] == value for name, value in source_after.items()),
                "journal applied source hashes differ from recovery manifest")
    return latest


def validate_native(root: Path, receipt: dict, task: dict, paths: list[str]) -> None:
    validate_model_receipt(root, receipt, task_id=task["task_id"], mode="repair", predicted_files=paths)
    require(receipt.get("native_read_file_denied") is True and receipt.get("native_tool_allowlist") == []
            and receipt.get("native_observation", {}).get("native_grok_progress", {}).get("tool_name_counts", {}).get("read_file") == 0,
            "recovery model must use the inline-only native tool policy")
    response = receipt["response"]
    require(response.get("decision") != "blocked" and response.get("edits"), "recovery proposal contains no admitted source edits")
    recorded = {row["path"]: row.get("sha256") for row in receipt.get("input_files", []) if isinstance(row, dict)}
    for edit in response["edits"]:
        require(edit["path"] in recorded and recorded[edit["path"]] == edit["before_sha256"], "model receipt is not bound to original edit bytes")


def proposal_after(root: Path, receipt: dict, paths: list[str], before: dict, originals: dict[str, bytes]) -> dict:
    edits = receipt["response"]["edits"]
    validate_edit_shapes(root, edits, paths)
    drafts = {name: data.decode("utf-8") for name, data in originals.items()}
    for edit in edits:
        name, old, new = edit["path"], edit["old"], edit["new"]
        require(edit["before_sha256"] == before[name], "proposal does not match admission source hash")
        current = drafts[name]
        require(current == "" if old == "" else current.count(old) == 1, "proposal anchor is not exact and unique")
        drafts[name] = new if old == "" else current.replace(old, new, 1)
    changed = {name for name in drafts if any(e["path"] == name for e in edits)}
    after = {name: byte_sha(drafts[name].encode()) if name in changed else before[name] for name in before}
    require(any(before[name] != after[name] for name in paths), "recovery proposal is a no-op")
    return after


def run_recovery(root, profile, task, *, ensure_lease, check_owned, invoke_model, remember_owned) -> dict:
    root = Path(root).resolve()
    ensure_lease()
    require(profile.get("llm", {}).get("repairReadPolicy") == "inline_only", "recovery requires profile llm.repairReadPolicy inline_only")
    task_id = task.get("task_id")
    require(type(task_id) is str and re.fullmatch(r"SVF-[A-Z0-9-]{1,64}", task_id), "invalid recovery task identity")
    env_path = os.environ.get(CONTEXT_ENV)
    require(type(env_path) is str and env_path, "admitted recovery context is missing")
    packet_name = _relative(root, env_path)
    require((root / packet_name).is_relative_to(runtime(root, profile)), "recovery context is outside the SVF runtime")
    packet_bytes = _read(root, packet_name, 131072)
    packet = _parse_json(packet_bytes.decode("utf-8"))
    paths = validate_packet(root, profile, task, packet, packet_name)
    journal_admission(root, profile, packet, packet_name, state="running")
    original_paths = _paths(root, task["edit_paths"], 128)
    check_owned(paths)
    unchanged(root, packet["source_before"])
    unchanged(root, packet["feedback_inputs"])
    directory = runtime(root, profile) / "tasks" / task_id / "recovery"
    attempt = directory / ("attempt-" + uuid.uuid4().hex)
    _relative(root, attempt)
    attempt.mkdir(parents=True, exist_ok=False)
    originals, before_artifacts, feedback_artifacts = {}, {}, {}
    before = {name: packet["source_before"][name] for name in original_paths}
    for index, name in enumerate(original_paths):
        data = b"" if before[name] is None else _read(root, name, 250000)
        originals[name] = data
        target = attempt / f"before-{index}.source"
        target.write_bytes(data)
        before_artifacts[name] = artifact(root, target)
    for index, name in enumerate(packet["feedback_inputs"]):
        data = _read(root, name, 4 * 1024 * 1024)
        target = attempt / f"feedback-{index}.source"
        target.write_bytes(data)
        feedback_artifacts[name] = artifact(root, target)
    context_file = attempt / "context.json"
    context_file.write_bytes(packet_bytes)
    # Preserve feedback identity separately from its immutable local filename.
    # Controller/source inputs already have their own supplied context or source
    # qualification. Actual diagnostics must reach the model, rather than merely
    # being archived beside a body-free failure counter.
    controller_inputs = set(packet["source_before"]) | set(task.get("context_paths", []))
    controller_inputs.update(str(profile.get(key) or "") for key in (
        "todoPath", "humanPlanPath", "objectivePath", "taskSpecPath", "appContractPath"))
    feedback_context, feedback_files, feedback_bytes = {}, [], 0
    for name, value in feedback_artifacts.items():
        controller_source = Path(name).suffix.lower() in {
            ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".md"}
        included = name not in controller_inputs and not controller_source
        feedback_context[name] = {**value, "included": included,
            "reason": "task_failure_feedback" if included else "already_bound_controller_or_source"}
        if included:
            feedback_bytes += value["bytes"]
            feedback_files.append(value["path"])
    require(feedback_bytes <= MAX_FEEDBACK_CONTEXT_BYTES,
            "complete recovery failure feedback exceeds its explicit context byte budget")
    inputs = list(dict.fromkeys([*[name for name in paths if before[name] is not None],
        *task.get("context_paths", []), *feedback_files]))
    _paths(root, inputs, 64)
    budget = model_call_limits(profile, "repair", task.get("llm_limits"))["modelContextBytes"]
    # Full editable source and actual failure feedback are mandatory. Packet
    # metadata is supplied once in structured recovery_context; its immutable
    # context artifact still owns admission, replay and execution fences.
    # The trusted
    # model callback may project supporting read-only manifests to the selected
    # app before measuring its final prompt. Charging their unprojected bytes
    # here prevents that compiler from running, even when every edit target fits.
    # Preserve regular-file, UTF-8 and individual byte bounds for all inputs.
    mandatory = {*paths, *feedback_files}
    context_cost = 0
    for name in inputs:
        content = _read(root, name, 250000).decode("utf-8")
        if name in mandatory:
            context_cost += len(_json({"path": name, "content": content}).encode())
    require(context_cost + len(_json(task).encode()) + 8192 <= budget, "complete recovery sources exceed the explicit model context budget")
    context = {"schema": CONTEXT_SCHEMA, "task_id": task_id, "producer_contract": packet["producer_contract"],
        "qualification_fingerprint": packet["qualification_fingerprint"], "admission_index": packet["admission_index"],
        "recovery_limit": packet["recovery_limit"], "source_before": packet["source_before"], "failure_summary": packet["failure_summary"],
        "feedback_inputs": feedback_context,
        "edit_paths": paths,
        "read_policy": "inline_only: use complete supplied edit targets; no native tools; do not alter controllers, tests, task status or receipts",
        "observation_only": True, "completion_authority": False}
    output = attempt / "model.json"
    def fence():
        ensure_lease()
        require(_read(root, packet_name, 131072) == packet_bytes, "recovery context changed at execution fence")
        journal_admission(root, profile, packet, packet_name, state="running")
        unchanged(root, packet["feedback_inputs"])
        for name, value in feedback_artifacts.items():
            require(byte_sha(read_artifact(root, value, attempt)) == packet["feedback_inputs"][name],
                    "retained recovery feedback changed at execution fence")
    try:
        fence()
        receipt = invoke_model(inputs, output, context)
        stored = _parse_json(_read(root, output.relative_to(root).as_posix(), 4 * 1024 * 1024).decode("utf-8"))
        require(stored == receipt, "returned model receipt differs from retained invocation")
        validate_native(root, receipt, task, paths)
        model_inputs = {row["path"]: row.get("sha256") for row in receipt.get("input_files", [])
                        if isinstance(row, dict) and "path" in row}
        require(all(model_inputs.get(value["path"]) == value["sha256"]
                    for value in feedback_context.values() if value["included"]),
                "model receipt omits hash-bound recovery failure feedback")
        unchanged(root, packet["source_before"])
        unchanged(root, packet["feedback_inputs"])
        require(_read(root, packet_name, 131072) == packet_bytes, "recovery context changed during model invocation")
        expected_after = proposal_after(root, receipt, paths, before, originals)
        fence()
        check_owned(paths)
        # Lazy import avoids an eager worker/recovery cycle. The helper uses
        # this explicit root/profile and never invokes a model or browser.
        from swissknife_visual_functional_worker import apply_task_edits
        applied = apply_task_edits(root, profile, task, receipt["response"]["edits"], paths,
                                   lease_check=fence, applier=apply_validated_edits)
        remember_owned([row["path"] for row in applied["applied"]])
        after = current_hashes(root, original_paths)
        require(after == expected_after, "applied recovery source differs from its exact model proposal")
        unchanged(root, {name: value for name, value in packet["source_before"].items() if name not in paths})
        manifest = {"schema": SCHEMA, "task_id": task_id, "task_sha256": digest(task), "eligible": True,
            "approved_edit_paths": paths,
            "source_before": before, "source_after": after, "before_artifacts": before_artifacts,
            "feedback_artifacts": feedback_artifacts, "model_artifact": artifact(root, output),
            "context_artifact": artifact(root, context_file), "context_identity": {"path": packet_name, "sha256": byte_sha(packet_bytes),
                **{key: packet[key] for key in ("producer_contract", "qualification_fingerprint", "admission_index", "recovery_limit")}},
            "grants_task_completion": False, "work_complete": False, "completion_authority": False}
        _atomic_json(root, attempt / "manifest.json", manifest)
        _atomic_json(root, directory / "latest.json", manifest)
        return {**manifest, "model_path": str(output)}
    except Exception as error:
        _atomic_json(root, attempt / "failure.json", {"schema": SCHEMA, "task_id": task_id,
            "error_type": type(error).__name__, "eligible": False, "grants_task_completion": False,
            "work_complete": False, "completion_authority": False})
        raise


def _recovery_evidence(root, profile, task, *, historical: bool = False) -> dict | None:
    try:
        root = Path(root).resolve()
        require(profile.get("llm", {}).get("repairReadPolicy") == "inline_only", "recovery policy changed")
        task_id = task.get("task_id")
        require(type(task_id) is str and re.fullmatch(r"SVF-[A-Z0-9-]{1,64}", task_id), "invalid task")
        directory = runtime(root, profile) / "tasks" / task_id / "recovery"
        latest = _parse_json(_read(root, _relative(root, directory / "latest.json"), 4 * 1024 * 1024).decode("utf-8"))
        require(latest.get("schema") == SCHEMA and latest.get("task_id") == task_id and latest.get("task_sha256") == digest(task)
                and latest.get("eligible") is True and latest.get("grants_task_completion") is False
                and latest.get("work_complete") is False and latest.get("completion_authority") is False, "recovery qualification differs")
        model_path = root / _relative(root, latest["model_artifact"]["path"])
        attempt = model_path.parent
        require(attempt.parent == directory and re.fullmatch(r"attempt-[0-9a-f]{32}", attempt.name)
                and model_path.name == "model.json", "model escaped its immutable recovery attempt")
        saved = _parse_json(_read(root, _relative(root, attempt / "manifest.json"), 4 * 1024 * 1024).decode("utf-8"))
        require(saved == latest, "latest recovery pointer differs from its immutable manifest")
        packet_bytes = read_artifact(root, latest["context_artifact"], attempt)
        packet = _parse_json(packet_bytes.decode("utf-8"))
        identity = latest["context_identity"]
        paths = validate_packet(root, profile, task, packet, identity["path"])
        require(byte_sha(packet_bytes) == identity["sha256"]
                and all(packet[key] == identity[key] for key in ("producer_contract", "qualification_fingerprint", "admission_index", "recovery_limit")), "context identity differs")
        require((root / _relative(root, identity["path"])).is_relative_to(runtime(root, profile)), "original context escaped runtime")
        require(_read(root, identity["path"], 131072) == packet_bytes, "original admitted context changed")
        receipt = _parse_json(read_artifact(root, latest["model_artifact"], attempt).decode("utf-8"))
        validate_native(root, receipt, task, paths)
        original_paths = _paths(root, task["edit_paths"], 128)
        before = {name: packet["source_before"][name] for name in original_paths}
        require(before == latest["source_before"] and latest.get("approved_edit_paths") == paths
                and set(latest["before_artifacts"]) == set(original_paths), "recovery before-source set differs")
        originals = {name: read_artifact(root, value, attempt) for name, value in latest["before_artifacts"].items()}
        for name, data in originals.items():
            require(data == b"" if before[name] is None else byte_sha(data) == before[name], "retained original source bytes differ")
        require(set(latest["feedback_artifacts"]) == set(packet["feedback_inputs"]), "feedback set differs")
        for name, value in latest["feedback_artifacts"].items():
            require(byte_sha(read_artifact(root, value, attempt)) == packet["feedback_inputs"][name], "retained feedback changed")
        expected = proposal_after(root, receipt, paths, before, originals)
        require(expected == latest["source_after"] == current_hashes(root, original_paths), "recovery applied source is stale")
        journal_admission(root, profile, packet, identity["path"], state="applied", source_after=latest["source_after"])
        if not historical:
            unchanged(root, {name: value for name, value in packet["source_before"].items() if name not in paths})
        result = {**latest, "model_path": str(model_path)}
        if historical:
            result.update(evidence_only=True, eligible=False)
        return result
    except (ValueError, TypeError, KeyError, OSError, AttributeError):
        return None


def qualified_recovery(root, profile, task) -> dict | None:
    """Strict current-source admission for an original producer retry."""
    return _recovery_evidence(root, profile, task)


def historical_recovery_evidence(root, profile, task) -> dict | None:
    """Verify a completed canary's repair witness without reauthorizing work.

    Later controller/profile changes do not erase an already verified repair.
    The immutable task/model/context/feedback evidence, current applied journal
    row and every original edit source remain independently bound. This API
    never returns producer eligibility and is restricted to recovery canaries.
    """
    if task.get("recovery_canary") is not True:
        return None
    return _recovery_evidence(root, profile, task, historical=True)
