"""Loss-aware native IntentIR family declarations and bounded Lean checks.

This module does not establish a translation's meaning, execute source code,
discharge an original task, or prove a neural objective converges. Combined
documents are disjoint unions: no relation between separately authored clauses
is invented. Lean checks the native uninterpreted declarations' syntax/types.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parent
DATASETS = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10" / "datasets" / "ipfs_datasets_py"
LEAN = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
FAMILIES = ("dcec", "tdfol", "event_calculus", "frame_logic", "datalog", "horn_chc",
            "transition_system", "higher_order", "concurrency", "cryptographic_protocol")
SCHEMA = "terminal-native-intent-family-projections@1"
LEAN_SCHEMA = "terminal-native-intent-declaration-lean@1"
LEAN_MEMORY_MB = 1024
LEAN_PROFILE = "direct-installed-lean-native-generated-declarations-single-thread-rss1024MiB@2"
AUTHORITY = {"proof_authority": False, "execution_authority": False,
    "completion_authority": False, "omission_authority": False,
    "source_semantics_verified": False, "original_task_satisfaction": False,
    "source_model_equivalence_proved": False, "convergence_proved": False}
FALSE_SOURCE = 'def deliberatelyIllTyped : Nat := "not a natural number"\n'
# An unresolved native lifecycle keeps its actual child reservation charged.
_UNRESOLVED_NATIVE = []


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _wire(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _need(depth <= 64 and count <= 500_000, "bounded inert JSON required")
        if type(item) is dict:
            _need(all(type(key) is str for key in item), "exact JSON keys required")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        else:
            _need(type(item) in (str, bool, int, float, type(None)), "exact inert JSON values required")
            _need(type(item) is not float or math.isfinite(item), "finite JSON required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("utf-8")
    _need(len(raw) <= 32 * 1024**2, "bounded projection report required")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _finish(value):
    value["report_sha256"] = _sha(_wire(value))
    return value


def _read(path, maximum=64 * 1024**2):
    from intent_io import read
    return read(path, maximum)


def _write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _pin(path, maximum=64 * 1024**2):
    raw = _read(path, maximum)
    return {"path": str(path), "sha256": _sha(raw), "bytes": len(raw)}


def _namespace(digest, kind, identity):
    return "joined:" + kind + ":" + _sha((digest + "\0" + identity).encode())


def _combine(task_id, descriptors):
    from ipfs_datasets_py.logic.intent_ir import schema
    from ipfs_datasets_py.logic.intent_ir.decoder import decode_intent_ir
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    _need(type(descriptors) is list and 1 <= len(descriptors) <= 128,
          "bounded nonempty native clause documents required per task")
    sources, statements, actions, edges, entries, terminals, tags, mappings = [], [], [], [], [], [], set(), []
    seen = set()
    for descriptor in descriptors:
        _need(type(descriptor) is dict and set(descriptor) == {"document", "canonical_sha256"},
              "closed native candidate document descriptor required")
        doc = decode_intent_ir(descriptor["document"])
        digest = _sha(canonical_intent_ir_bytes(doc))
        _need(digest == descriptor["canonical_sha256"] and digest not in seen,
              "native document identity mismatch or duplicate clause")
        seen.add(digest)
        maps = {kind: {getattr(row, field): _namespace(digest, kind, getattr(row, field)) for row in rows}
            for kind, field, rows in (("source", "ref_id", doc.sources),
                ("statement", "statement_id", doc.statements), ("action", "action_id", doc.actions),
                ("edge", "edge_id", doc.control_edges))}
        sources += [replace(row, ref_id=maps["source"][row.ref_id]) for row in doc.sources]
        statements += [replace(row, statement_id=maps["statement"][row.statement_id],
            source_ref_ids=tuple(maps["source"][ref] for ref in row.source_ref_ids)) for row in doc.statements]
        actions += [replace(row, action_id=maps["action"][row.action_id],
            source_ref_ids=tuple(maps["source"][ref] for ref in row.source_ref_ids),
            precondition_ids=tuple(maps["statement"][ref] for ref in row.precondition_ids),
            effect_ids=tuple(maps["statement"][ref] for ref in row.effect_ids),
            verification_ids=tuple(maps["statement"][ref] for ref in row.verification_ids)) for row in doc.actions]
        edges += [replace(row, edge_id=maps["edge"][row.edge_id],
            source_action_id=maps["action"][row.source_action_id],
            target_action_id=maps["action"][row.target_action_id],
            guard_statement_id=maps["statement"][row.guard_statement_id] if row.guard_statement_id else "",
            source_ref_ids=tuple(maps["source"][ref] for ref in row.source_ref_ids)) for row in doc.control_edges]
        entries += [maps["action"][ref] for ref in doc.entry_action_ids]
        terminals += [maps["action"][ref] for ref in doc.terminal_action_ids]
        tags.update(doc.tags)
        mappings.append({"original_document_id": doc.document_id, "canonical_sha256": digest,
            "identities": [{"kind": kind, "original": old, "combined": new}
                for kind in sorted(maps) for old, new in sorted(maps[kind].items())]})
    combined = schema.IntentIRDocument(document_id="terminal-clause-union:" + _sha(task_id.encode()),
        title="Disjoint union of explicitly authored clause candidates for " + task_id,
        intent_kind=schema.IntentKind.DECLARATIVE, sources=tuple(sources), statements=tuple(statements),
        actions=tuple(actions), control_edges=tuple(edges), entry_action_ids=tuple(entries),
        terminal_action_ids=tuple(terminals), tags=tuple(sorted(tags | {"disjoint-clause-union", "candidate-only"})))
    combined = decode_intent_ir(combined.to_dict())
    return combined, sorted(mappings, key=lambda row: row["canonical_sha256"])


def build_logic_projections(*, inventories):
    from clause_inventory import validate_instruction_inventory
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    from ipfs_datasets_py.logic.intent_ir.formalize.extended_projections import (
        project_intent_families, validate_intent_family_report)
    _need(type(inventories) is list and 1 <= len(inventories) <= 16, "bounded task inventories required")
    binding = _sha(_wire(inventories))
    task_ids = [row.get("task_id") for row in inventories if type(row) is dict]
    _need(len(task_ids) == len(inventories) and all(type(task) is str and
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", task) for task in task_ids)
        and len(set(task_ids)) == len(task_ids), "unique canonical task identities required")
    for inventory in inventories:
        instruction = inventory.get("instruction")
        _need(type(instruction) is dict and type(instruction.get("text")) is str,
              "complete inventory instruction body required")
        validate_instruction_inventory(inventory, task_id=inventory["task_id"],
            instruction=instruction["text"].encode("utf-8"))
    tasks = []
    for inventory in sorted(inventories, key=lambda row: row["task_id"]):
        document, mapping = _combine(inventory["task_id"], inventory["native_intent_documents"])
        report = project_intent_families(document, requested_families=list(FAMILIES))
        validate_intent_family_report(report, document)
        _need(set(row["family_id"] for row in report["projections"]) == set(FAMILIES),
              "all requested family frontiers must remain visible")
        tasks.append({"task_id": inventory["task_id"], "inventory_sha256": _sha(_wire(inventory)),
            "original_documents": inventory["native_intent_documents"], "identity_mapping": mapping,
            "combined_document": document.to_dict(),
            "combined_document_sha256": _sha(canonical_intent_ir_bytes(document)),
            "family_report": report, "combination_semantics": "disjoint_union_without_new_relations",
            "whole_original_instruction_formalized": False, **AUTHORITY})
    return _finish({"schema": SCHEMA, "inventories_sha256": binding,
        "requested_families": list(FAMILIES), "tasks": tasks,
        "task_count": len(tasks), "training_steps": 0, "provider_calls": 0,
        "external_backend_calls": 0, "declaration_projection_only": True,
        "all_original_requirements_proved": False, **AUTHORITY})


def validate_logic_projections(report, *, inventories):
    expected = build_logic_projections(inventories=inventories)
    _need(_wire(report) == _wire(expected), "native family report differs from exact corpus/document replay")
    return report


def producer_paths():
    """Named public producer inventory, not a loaded transitive closure claim."""
    from ipfs_datasets_py.logic.intent_ir.formalize.extended_projections import projection_producer_pins
    names = set(projection_producer_pins()) | {
        "ipfs_datasets_py.logic.intent_ir.schema", "ipfs_datasets_py.logic.intent_ir.decoder",
        "ipfs_datasets_py.logic.intent_ir.canonicalize", "ipfs_datasets_py.logic.intent_ir.formalize.compiler",
        "ipfs_datasets_py.logic.intent_ir.formalize.typed_compiler",
        "ipfs_datasets_py.logic.formalization.autoencoder.domain_targets",
        "ipfs_datasets_py.logic.formalization.compiler", "ipfs_datasets_py.logic.formalization.samples",
        "ipfs_datasets_py.logic.formalization.views", "ipfs_datasets_py.logic.families.models",
        "ipfs_datasets_py.logic.families.registry", "ipfs_datasets_py.logic.families.namespaces",
        "ipfs_datasets_py.logic.backends.process", "ipfs_datasets_py.logic.ir_core.claims",
        "ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_ir"}
    paths = []
    for name in sorted(names):
        path = Path(importlib.import_module(name).__file__).resolve()
        _need(path.is_relative_to(DATASETS), "native projection producer must be in pinned datasets")
        paths.append(path)
    paths += [LEAN, Path("/usr/bin/prlimit")]
    return sorted(set(paths))


def _lease_check(lease):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLease
    _need(type(lease) is ResourceLease and lease.owner_pid == os.getpid()
        and not lease.released and not lease.cancelled, "current original native resource lease required")
    _need(lease._scheduler.state_path == Path("/tmp") / ("ipfs-datasets-resource-scheduler-" + str(os.getuid()) + ".json")
        and lease._scheduler.config.proof_safety_enabled is True
        and lease._scheduler.config.proof_recovery_enabled is False,
        "original shared proof-safe resource scheduler required")


def _environment():
    return {"PATH": str(LEAN.parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}


def _limits():
    from ipfs_datasets_py.logic.backends.process import ToolRunLimits
    return ToolRunLimits(timeout_seconds=25, cpu_seconds=25,
        resident_memory_bytes=LEAN_MEMORY_MB * 1024**2, max_input_bytes=1024**2,
        max_output_bytes=262144, max_workspace_bytes=16 * 1024**2)


def _limit_record():
    return {"timeout_seconds": 25, "cpu_seconds": 25, "resident_memory_bytes": LEAN_MEMORY_MB * 1024**2,
        "max_input_bytes": 1024**2, "max_output_bytes": 262144, "max_workspace_bytes": 16 * 1024**2}


def _run_lean(*, source, label, output, lease, expected_success):
    from ipfs_datasets_py.logic.backends.process import (SubprocessExecutor, ProcessInvocation,
        ToolRuntime, OwnedToolCleanupError)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    _lease_check(lease)
    raw_source = source.encode("utf-8")
    _need(0 < len(raw_source) <= 1024**2, "bounded generated Lean declarations required")
    source_path = output / (label + ".lean")
    _write(source_path, raw_source)
    before = _pin(LEAN)
    executor_path = Path(importlib.import_module("ipfs_datasets_py.logic.backends.process").__file__).resolve()
    executor_pin = _pin(executor_path)
    prlimit_pin = _pin(Path("/usr/bin/prlimit"))
    temporary = tempfile.TemporaryDirectory(prefix="intent-lean-", dir=str(output))
    workspace = Path(temporary.name)
    (workspace / "IntentProjection.lean").write_bytes(raw_source)
    command = (str(LEAN), "-j", "1", "IntentProjection.lean")
    environment = _environment()
    child = lease.acquire_child(lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=LEAN_MEMORY_MB,
        child_process_slots=1, timeout=20, request_id="terminal-intent-declaration:" + label)
    result, cleaned, unresolved, handle = None, False, False, None
    def retain_unresolved():
        nonlocal unresolved
        if not unresolved:
            temporary._finalizer.detach()
            _UNRESOLVED_NATIVE.append((handle, child, lease, temporary))
            unresolved = True
    try:
        _lease_check(child)
        invocation = ProcessInvocation(argv=command, runtime=ToolRuntime.NATIVE,
            cwd=workspace, environment=environment, stdin=None, limits=_limits(), owned_process_observation=True)
        try:
            result = SubprocessExecutor().execute(invocation,
                cancellation=lambda: lease.released or lease.cancelled or child.released or child.cancelled)
        except OwnedToolCleanupError as error:
            handle = error.cleanup_handle
            try:
                handle.attach_workspace(temporary)
                observation = handle.retry_cleanup()
                cleaned = observation.cleanup_confirmed
            finally:
                if not cleaned:
                    retain_unresolved()
            raise
        _need(result.native_cleanup_handle is not None and result.native_lifecycle is not None,
              "original native sampled lifecycle observation required")
        handle = result.native_cleanup_handle
        try:
            handle.attach_workspace(temporary)
            observation = handle.retry_cleanup()
            cleaned = observation.cleanup_confirmed
        finally:
            if not cleaned:
                retain_unresolved()
        if not cleaned:
            retain_unresolved()
        _need(cleaned, "native process/workspace cleanup incomplete; child reservation retained")
    finally:
        if not unresolved:
            if result is None or result.native_cleanup_handle is None:
                temporary.cleanup()
            child.release()
    after = _pin(LEAN)
    stdout = result.stdout.decode("utf-8", errors="strict") if type(result.stdout) is bytes else result.stdout
    stderr = result.stderr.decode("utf-8", errors="strict") if type(result.stderr) is bytes else result.stderr
    bounded = not any((result.timed_out, result.cancelled, result.output_truncated,
        result.resource_exhausted, result.workspace_limit_exceeded, result.error))
    valid = result.returncode == 0 and bounded and before == after and cleaned
    rejected = result.returncode is not None and result.returncode != 0 and bounded and before == after and cleaned
    report = {"schema": "terminal-native-intent-lean-process@1", "label": label,
        "source": _pin(source_path, 1024**2), "requested_command": list(command),
        "actual_invocation_command": list(invocation.argv), "native_resource_wrapper": "original SubprocessExecutor prlimit",
        "executable": before, "executable_after": after, "executor": executor_pin, "prlimit": prlimit_pin,
        "environment": environment, "inherited_environment": False,
        "limits": _limit_record(),
        "child_resource_request": {"cpu_slots": 1, "memory_mb": LEAN_MEMORY_MB, "child_process_slots": 1},
        "native_shared_child_lease_used": True, "lean_threads": 1,
        "native_lifecycle": observation.to_dict(), "pid": result.pid, "returncode": result.returncode,
        "stdout": stdout, "stderr": stderr, "timed_out": result.timed_out, "cancelled": result.cancelled,
        "output_truncated": result.output_truncated, "resource_exhausted": result.resource_exhausted,
        "workspace_limit_exceeded": result.workspace_limit_exceeded, "error": result.error,
        "elapsed_seconds": result.elapsed_seconds, "backend_executed": result.pid is not None,
        "workspace_cleaned": cleaned, "expected_success": expected_success,
        "status": "passed" if valid else "rejected" if rejected else "inconclusive",
        "matches_expectation": valid if expected_success else rejected, **AUTHORITY}
    _write(output / (label + "-process.json"), _wire(report))
    return report


def _lean_sources(projections):
    fields = {"schema", "inventories_sha256", "requested_families", "tasks", "task_count", "training_steps",
        "provider_calls", "external_backend_calls", "declaration_projection_only", "all_original_requirements_proved",
        "report_sha256", *AUTHORITY}
    _need(type(projections) is dict and set(projections) == fields and projections.get("schema") == SCHEMA,
          "closed native declaration projections required")
    from ipfs_datasets_py.logic.intent_ir.formalize.lean_projection import project_lean_family
    from ipfs_datasets_py.logic.intent_ir.formalize.projection_contracts import canonical_bytes
    from ipfs_datasets_py.logic.intent_ir.canonicalize import canonical_intent_ir_bytes
    _need(projections.get("report_sha256") == _sha(_wire({k: v for k, v in projections.items() if k != "report_sha256"}))
        and all(projections.get(key) is False for key in AUTHORITY)
        and projections.get("requested_families") == list(FAMILIES)
        and all(type(projections[key]) is int and projections[key] == 0
            for key in ("training_steps", "provider_calls", "external_backend_calls"))
        and projections["declaration_projection_only"] is True
        and projections["all_original_requirements_proved"] is False
        and type(projections["inventories_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", projections["inventories_sha256"]),
        "closed projection scope or identity differs")
    tasks = projections.get("tasks")
    _need(type(tasks) is list and 1 <= len(tasks) <= 16 and type(projections["task_count"]) is int
        and projections.get("task_count") == len(tasks),
          "bounded nonempty task projection inventory required")
    identities = [task.get("task_id") for task in tasks if type(task) is dict]
    _need(len(identities) == len(tasks)
        and all(type(identity) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identity)
                for identity in identities), "canonical compiler task identities required")
    _need(len(set(identities)) == len(identities), "unique compiler task identities required")
    selected = []
    for task in projections["tasks"]:
        task_fields = {"task_id", "inventory_sha256", "original_documents", "identity_mapping", "combined_document",
            "combined_document_sha256", "family_report", "combination_semantics", "whole_original_instruction_formalized",
            *AUTHORITY}
        _need(set(task) == task_fields and all(task[key] is False for key in AUTHORITY)
            and task["whole_original_instruction_formalized"] is False
            and task["combination_semantics"] == "disjoint_union_without_new_relations"
            and type(task["inventory_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", task["inventory_sha256"]),
            "closed candidate-only task projection required")
        combined, mapping = _combine(task["task_id"], task["original_documents"])
        _need(_wire(task["combined_document"]) == _wire(combined.to_dict())
            and _wire(task["identity_mapping"]) == _wire(mapping)
            and task["combined_document_sha256"] == _sha(canonical_intent_ir_bytes(combined)),
            "exact native disjoint document union and identity mapping required")
        from ipfs_datasets_py.logic.intent_ir.formalize.extended_projections import validate_intent_family_report
        validate_intent_family_report(task["family_report"], task["combined_document"])
        _need(task["family_report"]["requested_families"] == list(FAMILIES),
              "compiler must retain all requested family frontiers")
        expected = project_lean_family(task["combined_document"])
        native = [row for row in task["family_report"]["projections"] if row["family_id"] == "higher_order"]
        _need(len(native) == 1 and canonical_bytes(native[0]) == canonical_bytes(expected)
            and expected["status"] != "unsupported", "exact nonempty regenerated native Lean declaration required")
        selected.append((task["task_id"], expected["representation"]["source"], True))
    selected.append(("false-type-control", FALSE_SOURCE, False))
    return selected


def compile_lean_projections(projections, *, output, lease):
    """Compile exactly native-generated declarations using installed Lean -j1.

    The native Lake convenience helper is intentionally not invoked: its default
    runner assigns HOME and does not enforce the required single-thread argv.
    This is a direct compiler receipt, never relabeled a native Lake receipt.
    """
    _lease_check(lease)
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and not output.exists() and output.parent.is_dir(),
        "fresh canonical owned Lean output directory required")
    sources = _lean_sources(projections)
    output.mkdir(mode=0o700)
    checks = [_run_lean(source=source, label=label, output=output, lease=lease,
        expected_success=expected) for label, source, expected in sources]
    report = _finish({"schema": LEAN_SCHEMA, "projections_sha256": _sha(_wire(projections)),
        "profile": LEAN_PROFILE,
        "lake_convenience_helper_used": False, "checks": checks,
        "positive_compiles": sum(row["expected_success"] and row["status"] == "passed" for row in checks),
        "false_type_controls_rejected": sum(not row["expected_success"] and row["status"] == "rejected" for row in checks),
        "qualified": all(row["matches_expectation"] for row in checks),
        "syntax_typecheck_only": True, "theorems_proved": [],
        "training_steps": 0, "provider_calls": 0, **AUTHORITY})
    _write(output / "report.json", _wire(report))
    validate_lean_evidence(report, projections=projections, output=output)
    return report


def validate_lean_evidence(report, *, projections, output):
    """Check retained historical process evidence; never restore dispatch rights."""
    root_fields = {"schema", "projections_sha256", "profile", "lake_convenience_helper_used", "checks",
        "positive_compiles", "false_type_controls_rejected", "qualified", "syntax_typecheck_only",
        "theorems_proved", "training_steps", "provider_calls", "report_sha256", *AUTHORITY}
    _need(type(report) is dict and set(report) == root_fields and report.get("schema") == LEAN_SCHEMA,
          "direct native declaration Lean evidence required")
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and output.is_dir(), "canonical owned retained Lean directory required")
    _need(report["profile"] == LEAN_PROFILE
        and type(report["training_steps"]) is int and report["training_steps"] == 0
        and type(report["provider_calls"]) is int and report["provider_calls"] == 0,
        "closed direct compiler profile and zero model activity required")
    _need(report.get("report_sha256") == _sha(_wire({k: v for k, v in report.items() if k != "report_sha256"}))
        and report.get("projections_sha256") == _sha(_wire(projections)), "Lean evidence projection or report binding differs")
    sources = _lean_sources(projections)
    checks = report["checks"]
    _need(type(checks) is list and len(checks) == len(sources), "complete positive/control process inventory required")
    births = set()
    for check, (label, source, expected) in zip(checks, sources):
        check_fields = {"schema", "label", "source", "requested_command", "actual_invocation_command",
            "native_resource_wrapper", "executable", "executable_after", "executor", "prlimit", "environment",
            "inherited_environment", "limits", "child_resource_request", "native_shared_child_lease_used",
            "lean_threads", "native_lifecycle", "pid", "returncode", "stdout", "stderr", "timed_out",
            "cancelled", "output_truncated", "resource_exhausted", "workspace_limit_exceeded", "error",
            "elapsed_seconds", "backend_executed", "workspace_cleaned", "expected_success", "status",
            "matches_expectation", *AUTHORITY}
        _need(type(check) is dict and set(check) == check_fields
            and check["schema"] == "terminal-native-intent-lean-process@1", "closed native compiler process receipt required")
        _need(type(check["pid"]) is int and check["pid"] > 0
            and type(check["returncode"]) is int and type(check["lean_threads"]) is int
            and type(check["elapsed_seconds"]) in (int, float) and not isinstance(check["elapsed_seconds"], bool)
            and math.isfinite(check["elapsed_seconds"]) and 0 <= check["elapsed_seconds"] <= 30
            and all(type(check[field]) is str for field in ("stdout", "stderr", "error")),
            "exact bounded compiler result types required")
        _need(_wire(check) == _read(output / (label + "-process.json"), 1024**2), "retained compiler receipt changed")
        _need(check["label"] == label and check["expected_success"] is expected
            and check["source"] == _pin(output / (label + ".lean"), 1024**2)
            and _read(output / (label + ".lean"), 1024**2) == source.encode(), "compiler source differs from regenerated declaration/control")
        expected_producers = {"executable": LEAN,
            "executor": Path(importlib.import_module("ipfs_datasets_py.logic.backends.process").__file__).resolve(),
            "prlimit": Path("/usr/bin/prlimit")}
        for field, path in expected_producers.items():
            _need(_wire(check[field]) == _wire(_pin(path)), "actual compiler/runtime producer bytes changed")
        command = [str(LEAN), "-j", "1", "IntentProjection.lean"]
        _need(check["requested_command"] == check["actual_invocation_command"] == command
            and check["executable"] == check["executable_after"] and check["environment"] == _environment()
            and check["inherited_environment"] is False and check["lean_threads"] == 1,
            "exact single-thread compiler command/environment required")
        _need(_wire(check["limits"]) == _wire(_limit_record())
            and check["native_resource_wrapper"] == "original SubprocessExecutor prlimit",
            "closed finite compiler resource bounds required")
        lifecycle = check["native_lifecycle"]
        lifecycle_fields = {"schema", "parent", "leader", "observed_descendants", "leader_reaped",
            "descendant_tracking_complete", "group_scan_complete", "remaining_group_members",
            "remaining_tracked_descendants", "readers", "stdin_writer", "workspace", "observation_errors",
            "ownership_is_sampled", "kernel_containment_attested", "cleanup_confirmed"}
        _need(type(lifecycle) is dict and set(lifecycle) == lifecycle_fields
            and lifecycle["schema"] == "native-owned-tool-lifecycle@1"
            and lifecycle["ownership_is_sampled"] is True and lifecycle["kernel_containment_attested"] is False
            and lifecycle["descendant_tracking_complete"] is True and lifecycle["group_scan_complete"] is True,
            "closed sampled native lifecycle required")
        def exact_identity(value, fields):
            return type(value) is dict and set(value) == set(fields) and all(type(item) is int and item > 0 for item in value.values())
        identity_fields = ("pid", "birth_ticks", "parent_pid", "process_group_id", "session_id")
        _need(exact_identity(lifecycle["parent"], ("pid", "birth_ticks"))
            and exact_identity(lifecycle["leader"], identity_fields)
            and type(lifecycle["observed_descendants"]) is list
            and all(exact_identity(identity, identity_fields) for identity in lifecycle["observed_descendants"])
            and _wire(lifecycle["readers"]) == _wire({"started": 2, "joined": 2})
            and _wire(lifecycle["stdin_writer"]) == _wire({"started": 0, "joined": 0})
            and type(lifecycle["workspace"]) is dict and set(lifecycle["workspace"]) == {"device", "inode", "removed"}
            and type(lifecycle["workspace"]["device"]) is int and lifecycle["workspace"]["device"] >= 0
            and type(lifecycle["workspace"]["inode"]) is int and lifecycle["workspace"]["inode"] > 0,
            "exact historical process, pipe and workspace identities required")
        leader = lifecycle["leader"]
        _need(leader["parent_pid"] == lifecycle["parent"]["pid"]
            and leader["process_group_id"] == leader["session_id"] == leader["pid"],
            "native compiler must have its own sampled process session")
        birth = (leader["pid"], leader["birth_ticks"])
        _need(leader["pid"] == check["pid"] and type(leader["birth_ticks"]) is int and leader["birth_ticks"] > 0
            and birth not in births and lifecycle["cleanup_confirmed"] is True
            and lifecycle["leader_reaped"] is True and lifecycle["workspace"]["removed"] is True
            and lifecycle["observation_errors"] == [] and lifecycle["remaining_group_members"] == []
            and lifecycle["remaining_tracked_descendants"] == [], "complete distinct historical native process cleanup required")
        births.add(birth)
        _need(check["native_shared_child_lease_used"] is True and check["backend_executed"] is True
            and check["workspace_cleaned"] is True and check["matches_expectation"] is True
            and _wire(check["child_resource_request"]) == _wire({"cpu_slots": 1, "memory_mb": LEAN_MEMORY_MB, "child_process_slots": 1})
            and all(check[key] is False for key in ("timed_out", "cancelled", "output_truncated", "resource_exhausted", "workspace_limit_exceeded"))
            and check["error"] == "" and all(check.get(key) is False for key in AUTHORITY),
            "bounded compiler observation or authority differs")
        if expected:
            _need(check["status"] == "passed" and check["returncode"] == 0, "native generated declarations did not typecheck")
        else:
            _need(check["status"] == "rejected" and check["returncode"] != 0
                and "type mismatch" in check["stdout"].lower(), "genuine literal type-error control required")
    _need(type(report["positive_compiles"]) is int and report["positive_compiles"] == len(sources) - 1
        and type(report["false_type_controls_rejected"]) is int and report["false_type_controls_rejected"] == 1
        and report["qualified"] is True and report["syntax_typecheck_only"] is True
        and report["theorems_proved"] == [] and report["lake_convenience_helper_used"] is False
        and all(report.get(key) is False for key in AUTHORITY), "Lean compilation scope or qualification differs")
    _need(_read(output / "report.json", 8 * 1024**2) == _wire(report), "retained complete Lean report changed")
    return report
