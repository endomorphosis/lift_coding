"""Independently authored offline packets, portable without a native workspace."""

import copy
import importlib.util
import json
import math
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "apalache_receiver_test", Path(__file__).parent / "apalache_admission_controls/receiver.py"
)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def fixture(valid):
    model = "MODULE authored\nSafety == " + ("TRUE" if valid else "FALSE") + "\n"
    config, tlc = (
        "INIT Init\nNEXT Next\nINVARIANT Safety\n",
        "SPECIFICATION Spec\nINVARIANT Safety\n",
    )
    return {
        "schema_version": "tla-generated-artifact/v1",
        "interface_version": "TLABackend@1",
        "model_text": model,
        "model_digest": r.sha(model.encode()),
        "apalache_config_text": config,
        "apalache_config_digest": r.sha(config.encode()),
        "tlc_config_text": tlc,
        "tlc_config_digest": r.sha(tlc.encode()),
        "artifact_digest": r.sha(("authored-artifact-" + str(valid)).encode()),
        "bounded": True,
        "unbounded_proof": False,
    }


def wire(label, valid, provider, fi, life):
    module = {
        "schema_version": "state-module-binding/v2",
        "interface": "StateModuleBinding@2",
        "artifact_digest": fi["artifact_digest"],
        "model_digest": fi["model_digest"],
        "module_name": "BoundedCounter",
        "source_document_id": "authored",
        "source_kind": "state_transition",
        "source_map_size": 0,
    }
    config = {
        "schema_version": "state-config-binding/v2",
        "interface": "StateConfigBinding@2",
        "provider": provider,
        "config_kind": "apalache_cfg" if provider == "apalache" else "tlc_cfg",
        "configuration_digest": fi[
            "apalache_config_digest" if provider == "apalache" else "tlc_config_digest"
        ],
        "configuration_text": fi[
            "apalache_config_text" if provider == "apalache" else "tlc_config_text"
        ].strip(),
    }
    bounds = {
        "schema_version": "state-bounds-binding/v2",
        "finite_state": False,
        "finite_trace_only": True,
        "step_bounded": True,
        "max_steps": 3,
    }
    properties = {
        "schema_version": "state-property-binding/v2",
        "primary_property": "Safety",
        "checked_safety": ["Safety"],
        "checked_liveness": [],
    }
    trace = (
        ""
        if valid
        else life["output_files"].get(
            "apalache-run/violation.tla", "State 1: n=0\nState 2: n=1\nState 3: n=2\n"
        )
    )
    states = [] if valid or provider == "apalache" else [{"index": i} for i in (1, 2, 3)]
    notes = (
        ["counterexample contained no parseable State blocks"]
        if provider == "apalache" and not valid
        else []
    )
    raw_ce = (
        None
        if valid
        else {
            "schema_version": "tla-counterexample/v1",
            "raw": trace,
            "replay_notes": notes,
            "replayed": True,
            "source": "checker_counterexample_file" if provider == "apalache" else "stdout_stderr",
            "states": states,
        }
    )
    receipt = {
        "schema_version": "tla-model-check-receipt/v1",
        "artifact_digest": fi["artifact_digest"],
        "bounded": True,
        "capability": {},
        "checked_liveness_properties": [],
        "checked_safety_properties": ["Safety"],
        "command": life["command"],
        "configuration_digest": config["configuration_digest"],
        "configuration_text": fi["apalache_config_text" if provider == "apalache" else "tlc_config_text"],
        "counterexample": raw_ce,
        "elapsed_ms": 10,
        "executable": life["command"][0],
        "fairness_limitations": [],
        "jvm_available": True,
        "model_digest": fi["model_digest"],
        "output_truncated": False,
        "reason": "authored recorded disposition",
        "receipt_id": "authored-receipt",
        "returncode": life["returncode"],
        "status": "satisfied" if valid else "violated",
        "stderr": "",
        "stdout": life["stdout"],
        "timeout_seconds": 30.0,
        "tool": provider,
        "tool_version": "0.58.3",
        "unbounded_proof": False,
    }
    ce = {
        "schema_version": "state-counterexample-binding/v2",
        "interface": "StateCounterexampleBinding@2",
        "bindings_complete": True,
        "bounds": bounds,
        "config": config,
        "module": module,
        "property": "Safety",
        "property_name": "Safety",
        "property_binding": properties,
        "raw_trace": trace.strip(),
        "replay_notes": notes,
        "replay_outcome": "clean_no_counterexample" if valid else "replayed",
        "replayed": not valid,
        "source": "" if valid else "checker_counterexample_file",
        "state_count": len(states),
        "states": states,
        "status": "clean_no_counterexample" if valid else "replayed",
    }
    evidence = {
        "schema_version": "state-provider-evidence/v2",
        "interface": "StateProviderEvidence@2",
        "authority_ceiling": "bounded",
        "authorizes_universal_proof": False,
        "available": True,
        "bindings_complete": True,
        "bounds": bounds,
        "capability": {},
        "claim_model_check": True,
        "claim_other_provider_capability": False,
        "claim_proof": False,
        "claim_theorem": False,
        "confidence": 0.0,
        "config": config,
        "content_digest": "d" * 64,
        "counterexample": ce,
        "counterexample_status": ce["status"],
        "diagnostics": [],
        "disposition": "satisfied" if valid else "counterexample",
        "evidence_id": "authored-evidence",
        "external_tool_proof": True,
        "fallback_output_present": False,
        "fluent_text_present": False,
        "is_proved": False,
        "is_theorem_authority": False,
        "metadata": {},
        "mock_output_present": False,
        "mode": "engine",
        "model_check_established": True,
        "module": module,
        "proof_established": False,
        "properties": properties,
        "provider": provider,
        "receipt": copy.deepcopy(receipt),
        "request_digest": "b" * 64,
        "request_id": "req:" + label,
        "result_authority": "model_check",
        "result_status": receipt["status"],
        "role": "authority",
        "semantics": {
            "schema_version": "state-semantics-binding/v2",
            "finite_state": False,
            "liveness": False,
            "fairness": False,
            "step_bounded": True,
            "safety": True,
        },
        "source_ref_ids": [],
        "theorem_established": False,
        "translation_ceiling": "bounded",
    }
    evidence["receipt"]["timeout_seconds"] = 30
    result = {"schema_version": "typed-backend-result/v1", "status": receipt["status"], "authority": "model_check"}
    outcome = {
        "schema_version": "state-execution-result/v2",
        "interface": "StateExecutionResult@2",
        "counterexample_status": ce["status"],
        "disposition": evidence["disposition"],
        "evidence": evidence,
        "outcome": {
            "artifacts": {
                k: v
                for k, v in fi.items()
                if k not in ("model_text", "apalache_config_text", "tlc_config_text")
            },
            "interface_version": "ApalacheBackend@1" if provider == "apalache" else "TLCBackend@1",
            "receipt": receipt,
            "request_digest": "c" * 64,
            "result": result,
        },
        "provider": provider,
        "request_digest": "b" * 64,
        "request_id": "req:" + label,
        "result": copy.deepcopy(result),
    }
    witness = (
        None
        if valid or provider != "apalache"
        else {
            "path": "apalache-run/violation.tla",
            "sha256": r.sha(trace.encode()),
            "raw_state_values": ["0", "1", "2"],
            "parsed_state_count": 0,
            "scope": "authored raw witness only",
        }
    )
    return outcome, witness


def authored(ident):
    """A closed authored packet family; all execution labels are invented."""
    source = {"/captured/source-" + str(i): r.sha(str(i).encode()) for i in range(80)}
    config = {"total_cpu_slots": 4, "total_memory_mb": 9830, "total_child_process_slots": 4}
    docs = {
        "fixtures": {"valid": fixture(True), "invalid": fixture(False)},
        "request_audit": [],
        "launch_audit": [],
        "lifecycle_audit": [],
        "environment_audit": [],
        "control_audit": {"boundaries": [], "triggers": [], "phase_budgets": []},
        "scheduler_config": {"schema": "codebase-saved-scheduler-config@1", "config": config},
        "command_result": {
            "after": copy.deepcopy(source),
            "before": source,
            "argv": ["/python", "/captured/driver.py"],
            "cwd": "/historical",
            "env_overrides": {},
            "freeze_sha256": "f" * 64,
            "returncode": 0 if ident.startswith("accepted") else 1,
            "seconds": 1.5,
        },
    }
    result = {
        "schema": "apalache-resource-admission-benchmark@1",
        "status": "passed" if ident.startswith("accepted") else "failed",
        "audit_sha256": {},
        "checks": {
            "owned_work_drained": True,
            "shared_config_unchanged": True,
            "sources_stable": True,
        },
        "child_usage": {},
        "controls": [],
        "elapsed_seconds": 1.0,
        "launches": 0,
        "lifecycles": 0,
        "mixed_cases": [],
        "native_lifecycles": 0,
        "packaged_native_entries": [],
        "phase_counts": {},
        "prelaunch_lifecycles": 0,
        "runs": [],
        "runtime": {"pid": 77, "boot_id": "authored-boot"},
        "scope": "authored receiver conformance only",
        "shared_after": {"config": config, "owned_active_leases": 0, "owned_waiting_requests": 0},
        "shared_before": {"config": config},
        "shared_pool_compatibility": {},
        "smoke": ident == "accepted_smoke",
        "source_pins_after": copy.deepcopy(source),
        "source_pins_before": source,
        "tool_files_after": {"/recorded/apalache-mc": "a" * 64},
        "tool_files_before": {"/recorded/apalache-mc": "a" * 64},
        "tool_selection": {},
    }
    if ident == "capacity_failed":
        result["error"] = "unexpected Apalache phases/lifecycles"
    else:
        result["dispatches"] = []
    if ident == "resource_failed":
        result["error"] = "interrupted operation published a model result"
    if ident in ("resource_failed", "accepted_full"):
        result.update(mixed_dispatch={}, mixed_elapsed_seconds=0.2)
    if ident == "accepted_full":
        result["mixed_overlap_required"] = False
    docs["result"] = result

    def add_phase(
        label,
        phase,
        valid=True,
        provider="apalache",
        prelaunch=False,
        resource=False,
        cancelled=False,
    ):
        fi = docs["fixtures"]["valid" if valid else "invalid"]
        case = label + ":constructor" if phase == "setup" else label
        argv = (
            ["/recorded/java", "-version"]
            if phase == "setup"
            else ["/recorded/apalache-mc", "version"]
            if phase == "help" and provider == "apalache"
            else ["/recorded/tlc", "-help"]
            if phase == "help"
            else [
                "/recorded/apalache-mc",
                "check",
                "--config-file=apalache-runtime.json",
                "--run-dir=apalache-run",
                "--out-dir=apalache-out",
                "--smt-solver=z3",
                "--config=apalache.cfg",
                "--length=3",
                "--inv=Safety",
                "--no-deadlock",
                "BoundedCounter.tla",
            ]
            if provider == "apalache"
            else ["/recorded/tlc", "-config", "BoundedCounter.cfg", "BoundedCounter.tla"]
        )
        apalache = phase != "setup" and provider == "apalache"
        memory = 512 if apalache else 256
        inputs = (
            {}
            if phase != "model"
            else {
                "BoundedCounter.tla": fi["model_text"].encode(),
                "apalache.cfg" if provider == "apalache" else "BoundedCounter.cfg": fi[
                    "apalache_config_text" if provider == "apalache" else "tlc_config_text"
                ].encode(),
            }
        )
        if phase == "model" and provider == "apalache":
            inputs["apalache-runtime.json"] = b"{}\n"
        outputs = (
            [
                "apalache-run/counterexample.tla",
                "apalache-run/violation.tla",
                "apalache-run/example.tla",
            ]
            if apalache and phase == "model"
            else []
        )
        limits = {
            "cpu_seconds": 1.0,
            "enforce_file_size_limit": True,
            "max_argument_bytes": 65536,
            "max_arguments": 256,
            "max_environment_bytes": 131072,
            "max_file_bytes": 64 * 1024**2 if apalache else None,
            "max_input_bytes": 4096,
            "max_output_bytes": 65536,
            "max_output_files": 64,
            "max_path_bytes": 512,
            "max_workspace_bytes": 128 * 1024**2 if apalache else 1024**2,
            "memory_bytes": 4 * 1024**3,
            "resident_memory_bytes": memory * 1024**2,
            "termination_grace_seconds": 0.25,
            "timeout_seconds": 1.0,
        }
        req = {
            "argv": argv,
            "case": case,
            "input_bytes": {k: len(v) for k, v in inputs.items()},
            "input_sha256": {k: r.sha(v) for k, v in inputs.items()},
            "limits": limits,
            "output_paths": outputs,
        }
        docs["request_audit"].append(req)
        pid = len(docs["request_audit"]) + 100
        out = {k: False for k in r.LIFE_FLAGS}
        out.update(
            workspace_cleaned=True,
            command=argv,
            elapsed_seconds=0.1,
            error="",
            interface_version="bounded-tool-runner/v1",
            output_files={},
            pid=pid,
            returncode=12
            if not valid and phase == "model"
            else 1
            if provider == "tlc" and phase == "help"
            else 0,
            runtime="jvm",
            stderr="",
            stdout="0.58.3\n" if apalache and phase == "help" else "authored recorded output",
            termination_reason="normal",
        )
        if apalache and phase == "model" and not valid:
            out["output_files"] = {
                "apalache-run/violation.tla": "State0 == n = 0\nState1 == n = 1\nState2 == n = 2\n"
            }
        if prelaunch:
            out.update(
                pid=None,
                returncode=None,
                timed_out=True,
                stdout="",
                error="resource admission timed out: resource lease unavailable",
                termination_reason="timeout",
            )
        if resource:
            out.update(
                returncode=-9,
                resource_exhausted=True,
                termination_reason="resource_limit",
                output_files={},
            )
        if cancelled:
            out.update(
                returncode=-15,
                cancelled=True,
                process_tree_terminated=True,
                termination_reason="cancelled",
                output_files={},
            )
        life = {
            "case": case,
            "request": {
                "argv": argv,
                "input_file_count": len(inputs),
                "java_option_environment_absent": True,
                "max_output_bytes": 65536,
                "memory_bytes": 4 * 1024**3,
                "output_path_count": len(outputs),
                "resident_memory_bytes": memory * 1024**2,
                "stdin_is_empty": True,
                "timeout_seconds": 1.0,
            },
            "result": out,
            "shared_backoff_after": {},
        }
        docs["lifecycle_audit"].append(life)
        if not prelaunch:
            lease = {
                "acquired_at": 10.0,
                "cancelled": False,
                "child_process_slots": 3 if apalache else 1,
                "cpu_slots": 1,
                "expires_at": 20.0,
                "gpu_memory_mb": 0,
                "heartbeat_at": 10.0,
                "lane": "validation",
                "lease_id": "recorded-lease-" + str(pid),
                "lease_key": "inert historical label",
                "memory_mb": memory,
                "owner_birth_marker": "inert",
                "owner_boot_id": "authored-boot",
                "owner_pid": 77,
                "parent_lease_id": None,
                "request_id": "native-prover:jvm",
                "requires_gpu": False,
                "sequence": pid,
                "unified_memory_mb": 0,
                "wait_seconds": 0.0,
            }
            file_size = limits["max_file_bytes"] or limits["max_workspace_bytes"]
            launch = {
                "argv": [
                    "/usr/bin/prlimit",
                    "--core=0:0",
                    f"--fsize={file_size}:{file_size}",
                    "--cpu=1:1",
                    "--as=4294967296:4294967296",
                    "--",
                ]
                + argv,
                "at_monotonic": 10.0,
                "case": case,
                "launch_lease_id": lease["lease_id"],
                "owned_leases": [lease],
                "root_allocations": {
                    "child_process_slots": lease["child_process_slots"],
                    "cpu_slots": 1,
                    "memory_mb": memory,
                },
                "thread": 1,
                "waiting": 0,
            }
            docs["launch_audit"].append(launch)
            if apalache:
                docs["environment_audit"].append(
                    {
                        "case": case,
                        "phase": phase,
                        "foreign_configuration_environment_absent": True,
                        "private_home_and_tmpdir": True,
                        "jvm_args": "-Xms16m -Xmx256m -Xss1m -XX:ActiveProcessorCount=1 -XX:MaxMetaspaceSize=128m -XX:ReservedCodeCacheSize=64m -XX:-UsePerfData -Duser.home=.",
                        "jvm_gc_args": "-XX:+UseSerialGC",
                    }
                )
        docs["control_audit"]["phase_budgets"].append(
            {
                "at_monotonic": 10.0,
                "case": label,
                "deadline": 12.0,
                "phase": phase,
                "remaining_seconds": 1.9999,
                "request_timeout_seconds": 1.0,
            }
        )
        return out

    def add_case(label, valid, provider="apalache", route="engine"):
        add_phase(label, "setup", valid, provider)
        model = add_phase(label, "model", valid, provider)
        add_phase(label, "help", valid, provider)
        outcome, witness = wire(
            label, valid, provider, docs["fixtures"]["valid" if valid else "invalid"], model
        )
        return {
            "case": label,
            "elapsed_seconds": 0.1,
            "phase_count": 3,
            "provider": provider,
            "raw_witness": witness,
            "result": outcome,
            "route": route,
            "valid": valid,
        }

    widths = (
        [1, 2] if ident == "capacity_failed" else [1] if ident == "accepted_smoke" else [1, 2, 4]
    )
    for width in widths:
        cases = [
            add_case(f"parallel:{width}:{route}:{valid}", valid, route=route)
            for route in (("engine",) if ident == "accepted_smoke" else ("engine", "helper"))
            for valid in (True, False)
        ]
        batch = {"cases": cases, "workers": width, "elapsed_seconds": 0.2}
        if ident != "capacity_failed":
            batch.update(
                requested_workers=width,
                effective_workers=1,
                dispatch={"requested_workers": width, "effective_workers": 1},
            )
        result["runs"].append(batch)
    if ident == "capacity_failed":
        for route in ("engine", "helper"):
            for valid in (True, False):
                label = f"parallel:4:{route}:{valid}"
                for phase in ("setup", "model", "help"):
                    add_phase(
                        label,
                        phase,
                        valid,
                        prelaunch=route == "engine" and not valid and phase == "help",
                    )
    elif ident != "accepted_smoke":
        result["mixed_cases"] = [
            add_case(f"mixed:{provider}:{valid}", valid, provider)
            for valid in (True, False)
            for provider in ("apalache", "tlc")
        ]
        for kind in (
            "pre_setup_cancel",
            "live_model_cancel",
            "after_model_cancel",
            "live_model_deadline",
        ):
            label = "control:" + kind
            phases = [] if kind == "pre_setup_cancel" else ["setup", "model"]
            model = None
            for phase in phases:
                model = add_phase(
                    label,
                    phase,
                    False,
                    resource=ident == "resource_failed"
                    and kind == "live_model_deadline"
                    and phase == "model",
                    cancelled=kind in ("live_model_cancel", "live_model_deadline")
                    and phase == "model"
                    and not (ident == "resource_failed" and kind == "live_model_deadline"),
                )
            boundaries, triggers = [], []
            if kind == "after_model_cancel":
                boundaries = [
                    {
                        "case": label,
                        "kind": "after_actual_completed_model",
                        "at_monotonic": 10.2,
                        "pid": model["pid"],
                        "returncode": 12,
                        "workspace_cleaned": True,
                    }
                ]
            elif kind == "live_model_cancel":
                triggers = [
                    {
                        "case": label,
                        "boundary": "immediately_after_actual_probe_popen",
                        "at_monotonic": 10.0,
                        "pid": model["pid"],
                        "observed_live": True,
                    }
                ]
            elif kind == "live_model_deadline":
                boundaries = [
                    {
                        "case": label,
                        "kind": "actual_live_model_before_deadline",
                        "at_monotonic": 10.0,
                        "pid": model["pid"],
                        "deadline": 12.0,
                        "observed_live": True,
                    }
                ]
            docs["control_audit"]["boundaries"].extend(boundaries)
            docs["control_audit"]["triggers"].extend(triggers)
            if ident == "resource_failed" and kind == "live_model_deadline":
                continue
            timed = kind == "live_model_deadline"
            result["controls"].append(
                {
                    "kind": kind,
                    "case": label,
                    "boundaries": boundaries,
                    "live_triggers": triggers,
                    "deadline_scope": "authored recorded startup only",
                    "elapsed_seconds": 0.1,
                    "native_stop_flags": "outer type retained separately",
                    "operation_timeout_ms": 300 if timed else 5000,
                    "phase_count": len(phases),
                    "phases": phases,
                    "result_published": False,
                    "interruption": {
                        "type": "ProofOperationTimeout" if timed else "ProofOperationCancelled",
                        "kind": "timeout" if timed else "cancelled",
                        "phase": "native execution",
                        "timeout_ms": 300 if timed else 5000,
                        "elapsed_ms": 300 if timed else 0,
                    },
                }
            )
    result.update(
        launches=len(docs["launch_audit"]),
        native_lifecycles=len(docs["launch_audit"]),
        lifecycles=len(docs["lifecycle_audit"]),
        prelaunch_lifecycles=1 if ident == "capacity_failed" else 0,
        phase_counts={"setup": 12, "model": 12, "help": 12}
        if ident == "capacity_failed"
        else {"setup": 2, "model": 2, "help": 2}
        if ident == "accepted_smoke"
        else {"setup": 19, "model": 19, "help": 16},
    )
    for role in (
        "request_audit",
        "launch_audit",
        "lifecycle_audit",
        "control_audit",
        "environment_audit",
    ):
        result["audit_sha256"][r.LEAVES[role]] = r.sha(r.canonical(docs[role]))
    if ident != "capacity_failed":
        result["dispatches"] = [batch["dispatch"] for batch in result["runs"]]
        if ident in ("resource_failed", "accepted_full"):
            result["mixed_dispatch"] = {"requested_workers": 4, "effective_workers": 1}
            result["dispatches"].append(result["mixed_dispatch"])
    return docs


def authored_top():
    focused = ET.Element("testsuites")
    suite = ET.SubElement(focused, "testsuite")
    for i in range(424):
        ET.SubElement(
            suite,
            "testcase",
            classname="authored.control",
            name=r.REGISTRY_NAME if i == 0 else "authored-" + str(i),
        )
    diagnostic = ET.Element("testsuites")
    suite = ET.SubElement(diagnostic, "testsuite")
    case = ET.SubElement(suite, "testcase", classname="authored.control", name=r.REGISTRY_NAME)
    ET.SubElement(case, "failure").text = "registry result error: " + r.REGISTRY_ERROR
    source = "def test_all_default_execution_routes_reserve_actual_apalache_profile(route):\n    if route == 'registry':\n        assert result.status.value == 'error'\n        assert result.diagnostics == (\"AttributeError: type object 'ResultStatus' has no attribute 'TIMEOUT'\",)\n"
    return {
        "focused_xml": ET.tostring(focused),
        "registry_diagnostic_xml": ET.tostring(diagnostic),
        "registry_test_source": source.encode(),
    }


def authored_files(root):
    inputs = root / "inputs"
    inputs.mkdir()
    top = authored_top()
    q = {key: None for key in r.QUALIFICATION_FIELDS}
    q.update(
        schema="apalache-execution-admission-qualification@1",
        status="passed_partial_scope",
        artifact_sha256={},
        total_native_phases=60,
        total_native_phases_across_all_attempts=161,
        total_lifecycles_across_all_attempts=162,
        native_success_cases=18,
        operation_stop_controls=4,
        focused_tests=424,
        selected_tests=1708,
        new_admission_tests=47,
        new_cache_replay=False,
        new_codebase_smt_execution=False,
        test_counts_summed=False,
        production_tasks_closed=[],
    )
    manifest = {
        "schema": r.INPUT_SCHEMA,
        "fixture_origin": "retained_apalache_admission_receipts",
        "attempts": [],
    }
    anchors = {}

    def put(name, raw):
        path = inputs / name
        path.write_bytes(raw)
        return {"path": str(path), "sha256": r.sha(raw), "size_bytes": len(raw)}

    for role, raw in top.items():
        manifest[role] = put(role + ".bin", raw)
        q["artifact_sha256"][r.TOP[role]] = r.sha(raw)
    for ident in r.IDS:
        docs = authored(ident)
        item, anchors[ident] = {"id": ident}, {}
        for role in r.ROLES:
            raw = r.canonical(docs[role])
            item[role] = put(ident + "-" + role + ".json", raw)
            native_name = (
                r.DIRECTORIES[ident] + "-command-result.json"
                if role == "command_result"
                else r.DIRECTORIES[ident] + "/" + r.LEAVES[role]
            )
            q["artifact_sha256"][native_name] = r.sha(raw)
            if role in ("result", "command_result"):
                anchors[ident][role] = r.sha(raw)
        if ident.startswith("accepted"):
            q["native_smoke" if ident == "accepted_smoke" else "native_full"] = {
                "result": r.DIRECTORIES[ident] + "/result.json",
                "native_phases": docs["result"]["launches"],
                "success_cases": 2 if ident == "accepted_smoke" else 16,
                "controls": 0 if ident == "accepted_smoke" else 4,
                "phase_counts": docs["result"]["phase_counts"],
            }
        manifest["attempts"].append(item)
    q_raw = r.canonical(q)
    manifest["qualification"] = put("qualification.json", q_raw)
    path = inputs / "manifest.json"
    path.write_bytes(r.canonical(manifest))
    return path, r.sha(q_raw), anchors


class PacketTests(unittest.TestCase):
    def test_independent_population_and_failure_goldens(self):
        summaries = [r.reconcile_attempt(ident, authored(ident)) for ident in r.IDS]
        self.assertEqual([x["native_phase_count"] for x in summaries], [35, 54, 6, 54])
        self.assertEqual([x["lifecycle_count"] for x in summaries], [36, 54, 6, 54])
        self.assertEqual([x["completed_case_count"] for x in summaries], [8, 16, 2, 16])
        self.assertEqual([len(x["unreturned_operation_phases"]) for x in summaries], [12, 2, 0, 0])
        self.assertEqual([x["completed_stop_control_count"] for x in summaries], [0, 3, 0, 4])
        self.assertIs(summaries[0]["failed_case_return_value_available"], False)
        self.assertIs(summaries[1]["failed_case_return_value_available"], False)

    def test_empty_states_keep_legacy_flag_without_new_replay(self):
        report = r.reconcile_attempt("accepted_smoke", authored("accepted_smoke"))
        invalid = report["completed_cases"][1]
        self.assertEqual(invalid["recorded_result"]["evidence"]["counterexample"]["states"], [])
        self.assertIs(invalid["raw_witness"]["legacy_replayed_recorded"], True)
        self.assertIs(invalid["counterexample_replay_qualified"], False)
        self.assertEqual(invalid["raw_witness"]["raw_labels"], [0, 1, 2])

    def test_coherent_internal_mutations_refuse(self):
        controls = r.mutation_controls([(x, authored(x)) for x in r.IDS])
        self.assertEqual(len(controls), 30)
        self.assertTrue(all(x["refused"] for x in controls))

    def test_resource_stop_is_not_deadline(self):
        d = authored("resource_failed")
        row = next(
            x
            for x in d["lifecycle_audit"]
            if x["case"] == "control:live_model_deadline" and "check" in x["request"]["argv"]
        )
        row["result"].update(timed_out=True, termination_reason="timeout")
        with self.assertRaisesRegex(r.Refusal, "not accepted wall timeout"):
            r.reconcile_attempt("resource_failed", d)

    def test_prelaunch_pid_never_invented(self):
        d = authored("capacity_failed")
        row = next(x for x in d["lifecycle_audit"] if x["result"]["pid"] is None)
        row["result"]["pid"] = 1
        with self.assertRaisesRegex(r.Refusal, "prelaunch refusal"):
            r.reconcile_attempt("capacity_failed", d)

    def test_future_saved_config_version_refused(self):
        d = authored("accepted_full")
        d["scheduler_config"]["schema"] = "codebase-saved-scheduler-config@2"
        with self.assertRaisesRegex(r.Refusal, "shared configuration"):
            r.reconcile_attempt("accepted_full", d)

    def test_bool_root_reservation_is_not_integer(self):
        d = authored("accepted_full")
        d["launch_audit"][0]["root_allocations"]["cpu_slots"] = True
        with self.assertRaisesRegex(r.Refusal, "undercount"):
            r.reconcile_attempt("accepted_full", d)

    def test_whole_pool_foreign_difference_preserved(self):
        d = authored("accepted_smoke")
        d["launch_audit"][0]["root_allocations"].update(
            cpu_slots=2, memory_mb=4352, child_process_slots=2
        )
        s = r.reconcile_attempt("accepted_smoke", d)["phases"][0]
        self.assertEqual(
            s["recorded_foreign_allocation_difference"],
            {"cpu_slots": 1, "memory_mb": 4096, "child_process_slots": 1},
        )
        self.assertIs(s["foreign_ownership_authenticated"], False)

    def test_boundary_pid_coherently_rebound_refuses(self):
        d = authored("accepted_full")
        d["control_audit"]["boundaries"][0]["pid"] = 999
        d["result"]["controls"][2]["boundaries"][0]["pid"] = 999
        with self.assertRaisesRegex(r.Refusal, "PID identity"):
            r.reconcile_attempt("accepted_full", d)

    def test_per_operation_order_refused(self):
        d = authored("accepted_full")
        d["request_audit"][0], d["request_audit"][1] = d["request_audit"][1], d["request_audit"][0]
        with self.assertRaisesRegex(r.Refusal, "phase ordering"):
            r.reconcile_attempt("accepted_full", d)

    def test_tlc_help_is_separate_descriptive_exit(self):
        s = r.reconcile_attempt("accepted_full", authored("accepted_full"))
        phases = [x for x in s["phases"] if x["case"] == "mixed:tlc:True"]
        self.assertEqual([x["lifecycle"]["result"]["returncode"] for x in phases], [0, 1])
        self.assertIs(s["completed_cases"][-3]["mixed_tlc_fixture_body_available"], False)

    def test_registry_error_remains_controlled_diagnostic(self):
        d = authored_top()
        result = r.registry_controls(
            d["focused_xml"], d["registry_diagnostic_xml"], d["registry_test_source"]
        )
        self.assertEqual(result["recorded_registry_status"], "error")
        self.assertIs(result["native_registry_result_available"], False)
        self.assertIs(result["registry_native_success_qualified"], False)

    def test_registry_assertion_success_forgery(self):
        d = authored_top()
        changed = d["registry_test_source"].replace(b"== 'error'", b"== 'satisfied'")
        with self.assertRaisesRegex(r.Refusal, "ERROR expectation"):
            r.registry_controls(d["focused_xml"], d["registry_diagnostic_xml"], changed)

    def test_registry_diagnostic_missing(self):
        d = authored_top()
        with self.assertRaisesRegex(r.Refusal, "ERROR diagnostic"):
            r.registry_controls(
                d["focused_xml"],
                d["registry_diagnostic_xml"].replace(b"TIMEOUT", b"OTHER"),
                d["registry_test_source"],
            )

    def test_registry_xml_entity_refusal(self):
        with self.assertRaisesRegex(r.Refusal, "inert XML"):
            r.registry_controls(b'<!DOCTYPE x [<!ENTITY a "x">]><x/>', b"<x/>", b"")

    def test_utf16_xml_cannot_bypass_entity_boundary(self):
        with self.assertRaises((r.Refusal, UnicodeError)):
            r.registry_controls('<!DOCTYPE x [<!ENTITY a "x">]><x/>'.encode("utf-16"), b"<x/>", b"")

    def test_bool_module_source_map_size_refuses(self):
        docs = authored("accepted_smoke")
        case = docs["result"]["runs"][0]["cases"][0]["result"]
        case["evidence"]["module"]["source_map_size"] = False
        case["evidence"]["counterexample"]["module"]["source_map_size"] = False
        with self.assertRaisesRegex(r.Refusal, "module/config"):
            r.reconcile_attempt("accepted_smoke", docs)


class FileTests(unittest.TestCase):
    def run_authored(self, root, before=None):
        manifest, q_anchor, anchors = authored_files(root)
        if before:
            before(manifest)
        with patch.object(r, "QUALIFICATION_ANCHOR", q_anchor), patch.object(r, "ANCHORS", anchors):
            return r.audit(manifest, root / "output")

    def test_complete_authored_file_profile_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self.run_authored(root)
            self.assertEqual(report["selected_native_phase_count"], 149)
            self.assertEqual(report["selected_lifecycle_count"], 150)
            self.assertEqual(report["accepted_native_phase_count"], 60)
            self.assertEqual(report["selected_case_count"], 42)
            self.assertEqual(report["historical_completed_stop_control_count"], 7)
            self.assertEqual(report["accepted_stop_control_count"], 4)
            self.assertEqual(report["declared_all_attempt_native_phase_count"], 161)
            self.assertEqual(len(report["retained_files"]), 41)
            self.assertEqual(len(list((root / "output").rglob("*"))), 43)
            self.assertTrue(all(report[k] is False for k in r.FALSE))
            self.assertTrue(all(type(report[k]) is int and report[k] == 0 for k in r.ZERO))
            self.assertEqual(json.loads((root / "output" / r.REPORT_NAME).read_bytes()), report)

    def test_fixed_qualification_anchor_refuses_repaired_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def mutate(manifest):
                m = json.loads(manifest.read_bytes())
                pin = m["qualification"]
                path = Path(pin["path"])
                q = json.loads(path.read_bytes())
                q["artifact_sha256"]["forged"] = "a" * 64
                raw = r.canonical(q)
                path.write_bytes(raw)
                pin.update(sha256=r.sha(raw), size_bytes=len(raw))
                manifest.write_bytes(r.canonical(m))

            with self.assertRaisesRegex(r.Refusal, "independent qualification"):
                self.run_authored(root, mutate)
            self.assertFalse((root / "output").exists())

    def test_selected_attempt_order_refused(self):
        with tempfile.TemporaryDirectory() as tmp:

            def mutate(manifest):
                m = json.loads(manifest.read_bytes())
                m["attempts"].reverse()
                manifest.write_bytes(r.canonical(m))

            with self.assertRaisesRegex(r.Refusal, "ordered selected"):
                self.run_authored(Path(tmp), mutate)

    def test_output_under_original_manifest_parent_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, q_anchor, anchors = authored_files(Path(tmp))
            with (
                patch.object(r, "QUALIFICATION_ANCHOR", q_anchor),
                patch.object(r, "ANCHORS", anchors),
            ):
                with self.assertRaisesRegex(r.Refusal, "outside inputs"):
                    r.audit(manifest, manifest.parent / "output")

    def late(self, change, wanted, after_stable=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, q_anchor, anchors = authored_files(root)
            old = r.final_fence

            def fence(capture, output, expected):
                if after_stable:
                    method = capture.stable
                    fired = False

                    def stable():
                        nonlocal fired
                        method()
                        if not fired:
                            fired = True
                            change(root, manifest, capture, output)

                    with patch.object(capture, "stable", stable):
                        return old(capture, output, expected)
                change(root, manifest, capture, output)
                return old(capture, output, expected)

            with (
                patch.object(r, "QUALIFICATION_ANCHOR", q_anchor),
                patch.object(r, "ANCHORS", anchors),
                patch.object(r, "final_fence", fence),
            ):
                with self.assertRaisesRegex((r.Refusal, OSError), wanted):
                    r.audit(manifest, root / "output")

    def test_late_original_manifest_bytes(self):
        self.late(lambda root, m, c, o: m.write_bytes(m.read_bytes() + b" "), "preallocation|drift")

    def test_late_original_packet_bytes(self):
        def change(root, manifest, capture, output):
            path = Path(json.loads(manifest.read_bytes())["attempts"][0]["result"]["path"])
            path.write_bytes(path.read_bytes() + b" ")

        self.late(change, "preallocation|drift")

    def test_late_copy_bytes(self):
        self.late(
            lambda root, m, c, o: (o / "retained/00-manifest.json").write_bytes(b"changed"), "drift"
        )

    def test_late_main_report_bytes(self):
        self.late(lambda root, m, c, o: (o / r.REPORT_NAME).write_bytes(b"changed"), "drift")

    def test_late_extra_output_after_body_reread(self):
        self.late(
            lambda root, m, c, o: (o / "unexpected").write_bytes(b"late"),
            "unexpected output",
            after_stable=True,
        )

    def test_late_nested_copy_symlink(self):
        def change(root, manifest, capture, output):
            target = output / "retained/00-manifest.json"
            target.unlink()
            target.symlink_to(manifest)

        self.late(change, "canonical")

    def test_late_nested_directory_alias(self):
        def change(root, manifest, capture, output):
            target = output / "retained"
            moved = root / "moved-retained"
            target.rename(moved)
            target.symlink_to(moved, target_is_directory=True)

        self.late(change, "canonical")

    def test_late_root_alias_after_body_reread(self):
        def change(root, manifest, capture, output):
            moved = root / "moved-output"
            output.rename(moved)
            output.symlink_to(moved, target_is_directory=True)

        self.late(change, "canonical", after_stable=True)

    def test_late_copy_fifo_refuses_without_open(self):
        def change(root, manifest, capture, output):
            target = output / "retained/00-manifest.json"
            target.unlink()
            os.mkfifo(target)

        self.late(change, "regular")


class BoundTests(unittest.TestCase):
    def test_strict_json_duplicates(self):
        with self.assertRaisesRegex(r.Refusal, "duplicate"):
            r.document(b'{"a":1,"a":2}')

    def test_strict_json_nonfinite(self):
        for raw in (b"NaN", b"Infinity", b"1e999"):
            with self.subTest(raw=raw), self.assertRaises(r.Refusal):
                r.document(raw)

    def test_strict_json_surrogates_and_giant_integer(self):
        for raw in (b'"\\ud800"', b"9" * 5000):
            with self.subTest(raw=raw), self.assertRaises(r.Refusal):
                r.document(raw)

    def test_integer_boolean_aliases(self):
        self.assertFalse(r.integer(True))
        self.assertFalse(r.number(False))
        self.assertFalse(r.number(math.inf))

    def test_declared_byte_budget_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized"
            path.write_bytes(b"12")
            with patch.object(r.os, "open", side_effect=AssertionError("must refuse before open")):
                with self.assertRaisesRegex(r.Refusal, "preallocation"):
                    r.Capture().take(
                        path, {"path": str(path), "sha256": r.sha(b"12"), "size_bytes": 1}
                    )

    def test_aggregate_budget_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet"
            path.write_bytes(b"12")
            capture = r.Capture()
            capture.total = r.MAX_TOTAL - 1
            with patch.object(r.os, "open", side_effect=AssertionError("must refuse before open")):
                with self.assertRaisesRegex(r.Refusal, "preallocation"):
                    capture.take(path)

    def test_growth_after_stat_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet"
            path.write_bytes(b"12")
            real_open = r.os.open

            def growing(*args, **kwargs):
                path.write_bytes(b"123")
                return real_open(*args, **kwargs)

            with patch.object(r.os, "open", growing):
                with self.assertRaisesRegex(r.Refusal, "descriptor identity"):
                    r.Capture().take(
                        path, {"path": str(path), "sha256": r.sha(b"12"), "size_bytes": 2}
                    )


if __name__ == "__main__":
    unittest.main()
