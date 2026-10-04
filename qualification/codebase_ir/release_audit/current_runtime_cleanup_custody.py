"""Reconcile retained runtime15 cleanup, source metadata and trial custody."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
import xml.etree.ElementTree as ET
from collections import Counter
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-current-runtime-cleanup-custody-input@1"
SCHEMA = "codebase-ir-current-runtime-cleanup-custody@1"
PROFILE = "retained-current-runtime15-cleanup@1"
PUBLIC_ANCHOR = "fb7664d68f863de982e12361014296cdaf668ea2bc22fa20d16a313e3452d040"
MAX_FILE = 10 * 1024 * 1024
MAX_BYTES = 24 * 1024 * 1024
MAX_FILES = 48
MAX_MANIFEST = 256 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_SECONDS = 120
TRUE_FLAGS = (
    "current_runtime_cleanup_custody_produced", "recorded_cleanup_bindings_reconciled",
    "recorded_test_identity_populations_reconciled", "failed_trial_receipts_preserved",
    "declared_source_generation_metadata_reconciled", "recorded_costs_reconciled",
    "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed", "owner_sources_imported",
    "owner_database_opened", "profile_keys_read", "git_executable_invoked",
    "network_access_performed", "signature_authentication_performed",
    "producer_authentication_verified", "historical_process_origin_authenticated",
    "current_resource_cleanup_verified", "current_live_eligibility_verified",
    "selected_source_bodies_replayed", "full_dependency_custody_qualified",
    "checkpoint_state_reconstructed", "whole_current_runtime_qualified",
    "external_effect_absence_qualified", "training_absence_certified",
    "unique_cpu_time_measured", "total_elapsed_wall_time_measured",
    "proof_authority_qualified", "production_acceptance_requalified",
)
FIXED_ROLES = (
    "machine_review", "historical_review", "current_worker_result", "container_result",
    "cleanup_receipt", "independent_worker_audit", "selected_source_receipt",
    "source_reader_guard", "worker_stdout", "native_lifecycle", "execution_scope_before",
    "execution_scope_after", "authored_verification",
)
ROLES = (*FIXED_ROLES[:9], *(f"current_successful_xml_{i:02}" for i in range(6)),
         *(f"prior_successful_xml_{i:02}" for i in range(14)), *(f"failed_xml_{i:02}" for i in range(2)),
         *FIXED_ROLES[9:])
BINDING_ROLES = ("machine_review", "historical_review", "current_worker_result", "container_result",
                 "cleanup_receipt", "independent_worker_audit", "selected_source_receipt", "authored_verification")
LOCAL_RECORDS = {
    "native_lifecycle": "native/native-lifecycle.json",
    "execution_scope_before": "native/execution-scope-before.json",
    "execution_scope_after": "native/execution-scope-after-stop.json",
    "authored_verification": "native/authored-worker-receipt-verification.json",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def bounded_canonical(value, maximum):
    chunks, size = [], 0
    for token in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).iterencode(value):
        raw = token.encode()
        require(size + len(raw) + 1 <= maximum, "serialized report allocation bound")
        chunks.append(raw)
        size += len(raw)
    return b"".join(chunks) + b"\n"


def document(raw, *, allow_list=False):
    depth, quoted, escape, containers = 0, False, False, 0
    for token in raw:
        if quoted:
            if escape:
                escape = False
            elif token == 92:
                escape = True
            elif token == 34:
                quoted = False
        elif token == 34:
            quoted = True
        elif token in (91, 123):
            depth += 1
            containers += 1
            require(depth <= 32 and containers <= 100000, "JSON structure allocation bound")
        elif token in (93, 125):
            depth -= 1
            require(depth >= 0, "JSON nesting mismatch")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        result = int(token)
        require(abs(result) <= 2**63 - 1, "JSON integer magnitude bound")
        return result

    def floating(token):
        require(len(token) <= 64, "JSON float allocation bound")
        result = float(token)
        require(math.isfinite(result), "nonfinite JSON number")
        return result

    def constant(_):
        raise ValueError("nonfinite JSON number")

    result = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_int=integer, parse_float=floating, parse_constant=constant)
    require(type(result) is dict or allow_list and type(result) is list, "JSON object required")
    pending, count = [(result, 0)], 0
    while pending:
        value, level = pending.pop()
        count += 1
        require(count <= 600000 and level <= 32, "JSON value allocation bound")
        if type(value) is str:
            require(len(value) <= 1024 * 1024 and "\x00" not in value, "bounded JSON text required")
        elif type(value) is dict:
            pending.extend((key, level + 1) for key in value)
            pending.extend((child, level + 1) for child in value.values())
        elif type(value) is list:
            pending.extend((child, level + 1) for child in value)
    return result


def exact_int(value, maximum=2**63 - 1):
    require(type(value) is int and 0 <= value <= maximum, "bounded exact integer required")
    return value


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e9,
            "bounded recorded number required")
    return value


def digest(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "SHA-256 required")
    return value


def lexical_path(value, *, absolute=True):
    require(type(value) is str and 0 < len(value) <= 8192 and "\x00" not in value, "bounded lexical path required")
    path = Path(value)
    require(path.is_absolute() is absolute and ".." not in path.parts and str(path) == value,
            "canonical lexical path required")
    if not absolute:
        require(value != ".", "nonempty relative member required")
    return path


def descriptor(value):
    require(type(value) is dict and set(value) == {"path", "sha256", "size_bytes"}, "closed file descriptor required")
    lexical_path(value["path"])
    digest(value["sha256"])
    exact_int(value["size_bytes"], MAX_FILE)
    return dict(value)


def declared_pin(root, value):
    require(type(value) is dict and set(value) == {"path", "sha256", "bytes"}, "closed declared descriptor required")
    return descriptor({"path": str(root / lexical_path(value["path"], absolute=False)),
                       "sha256": value["sha256"], "size_bytes": value["bytes"]})


class Capture:
    """Read only selected regular files, with a separate bounded copy cache."""

    def __init__(self, relocated_sources=None, *, started=None):
        self.remap = relocated_sources
        self.files, self.logical, self.total = {}, {}, 0
        self.started = time.monotonic() if started is None else started

    def deadline(self):
        require(time.monotonic() - self.started <= MAX_SECONDS, "custody deadline")

    @staticmethod
    def raw(path, maximum):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical nonsymlink file required")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, "bounded regular file required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(maximum + 1)
            after, current = os.fstat(fd), path.lstat()

            def identity(row):
                return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

            require(identity(before) == identity(after) == identity(current) and len(raw) == before.st_size,
                    "file changed during bounded read")
            return raw
        finally:
            os.close(fd)

    def read(self, path, pin=None, *, mapped=True, maximum=MAX_FILE):
        self.deadline()
        logical = lexical_path(str(path))
        if self.remap is not None and mapped:
            require(str(logical) in self.remap, "explicit relocated member unavailable")
            physical = lexical_path(self.remap[str(logical)])
        else:
            physical = logical
        limit = maximum if pin is None else descriptor(pin)["size_bytes"]
        require(limit <= maximum, "preallocation file bound")
        if physical not in self.files:
            require(len(self.files) < MAX_FILES and self.total + limit <= MAX_BYTES, "preallocation aggregate bound")
            self.files[physical] = self.raw(physical, limit)
            self.total += len(self.files[physical])
        raw = self.files[physical]
        if pin is not None:
            require(len(raw) == pin["size_bytes"] and sha256(raw).hexdigest() == pin["sha256"], "selected raw pin mismatch")
        self.logical[str(logical)] = physical
        return raw

    def stable(self):
        rows = []
        for path, raw in self.files.items():
            self.deadline()
            require(self.raw(path, len(raw)) == raw, "previously captured body changed")
            rows.append({"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw), "unchanged": True})
        return {"unchanged": True, "files": rows}


def selected_bindings(pins, docs):
    machine, historical, audit = (docs[r] for r in ("machine_review", "historical_review", "independent_worker_audit"))
    require(machine["schema"] == "codebase-source-delta-current-runtime-review@1", "machine review schema")
    machine_path = lexical_path(pins["machine_review"]["path"])
    tail = Path("external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_delta_runtime_review.json")
    require(machine_path.parts[-len(tail.parts):] == tail.parts, "machine review location")
    workspace = machine_path.parents[4]
    namespace = lexical_path(str(workspace / machine["current_runtime_namespace"]))
    require(namespace == workspace / "artifacts/codebase_ir_terminal_bench/inventory-resume-worker-qualification-20261003-15",
            "exact selected runtime namespace")
    expected = {"machine_review": pins["machine_review"]}

    def add(role, declared, *, root=workspace):
        expected[role] = declared_pin(root, declared)

    for role, value in (
        ("historical_review", machine["historical_resume_worker_review"]),
        ("current_worker_result", machine["native_current_runtime"]["result"]),
        ("container_result", machine["container_closure"]["result"]),
        ("cleanup_receipt", machine["explicit_owner_worktree_cleanup"]["receipt"]),
        ("independent_worker_audit", machine["current_runtime_independent_audit"]["report"]),
        ("selected_source_receipt", machine["frozen_candidate"]["receipt"]),
        ("source_reader_guard", machine["source_reader_guards"]["report"]),
    ):
        add(role, value)
    add("worker_stdout", machine["current_runtime_independent_audit"]["actual_worker_stdout"], root=namespace)
    for prefix, rows, population in (("current_successful_xml", machine["tests"], 6),
                                     ("prior_successful_xml", historical["tests"], 14),
                                     ("failed_xml", machine["failed_tests"], 2)):
        require(type(rows) is list and len(rows) == population, "complete declared trial population")
        for index, row in enumerate(rows):
            add(f"{prefix}_{index:02}", row["junit"])
    for role, relative in LOCAL_RECORDS.items():
        value = audit["observed_artifact_pins"][relative]
        require(type(value) is dict and set(value) == {"bytes", "sha256"}, "closed local audit descriptor")
        expected[role] = descriptor({"path": str(namespace / relative), "sha256": value["sha256"], "size_bytes": value["bytes"]})
    require(expected == pins and len({row["path"] for row in pins.values()}) == 35, "complete exact selected raw bindings")
    return workspace, namespace


def xml_receipt(raw, declared):
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "XML declarations refused")
    parser = ET.XMLPullParser(events=("start", "end"))
    depth, nodes = 0, 0
    for offset in range(0, len(raw), 4096):
        parser.feed(raw[offset:offset + 4096])
        for event, _ in parser.read_events():
            if event == "start":
                depth += 1
                nodes += 1
                require(depth <= 8 and nodes <= 16384, "XML structure allocation bound")
            else:
                depth -= 1
    parser.close()
    root = ET.fromstring(raw)
    require(root.tag == "testsuites" and all(row.tag == "testsuite" for row in root), "JUnit root/suite shape")
    cases, summaries, totals = [], [], Counter()
    for suite in root:
        counts = {}
        for key in ("tests", "errors", "failures", "skipped"):
            token = suite.attrib[key]
            require(re.fullmatch(r"0|[1-9][0-9]{0,3}", token) is not None, "exact XML count")
            counts[key] = exact_int(int(token), 4096)
        require(len(suite) == counts["tests"] and all(case.tag == "testcase" for case in suite), "XML case population")
        outcomes = Counter(child.tag for case in suite for child in case)
        require(set(outcomes) <= {"error", "failure", "skipped", "system-out", "system-err", "properties"} and outcomes["error"] == counts["errors"]
                and outcomes["failure"] == counts["failures"] and outcomes["skipped"] == counts["skipped"], "XML outcome counts")
        for case in suite:
            require(set(case.attrib) <= {"classname", "name", "time"} and {"classname", "name"} <= set(case.attrib), "closed XML case")
            name, classname = case.attrib["name"], case.attrib["classname"]
            require(0 < len(name) <= 8192 and 0 < len(classname) <= 8192 and "\x00" not in name + classname, "bounded case identity")
            normalized = "api." + classname.split(".test.api.", 1)[1] if ".test.api." in classname else classname
            cases.append({"classname": classname, "normalized_classname": normalized, "name": name,
                          "outcomes": [child.tag for child in case if child.tag in ("error", "failure", "skipped")]})
        totals.update(counts)
        summaries.append({**counts, "seconds": number(float(suite.attrib["time"]))})
    require(len(cases) <= 4096, "XML receipt case allocation bound")
    grouped = {}
    for row in cases:
        grouped.setdefault((row["classname"], row["name"]), []).append(row["outcomes"])
    for outcomes in grouped.values():
        require(len(outcomes) == 1 or len(outcomes) == 2 and sorted(outcomes) == [["error"], ["failure"]],
                "duplicate XML identity without distinct failure/cleanup error")
    for key in ("tests", "errors", "failures", "skipped"):
        require(totals[key] == exact_int(declared[key]), "declared XML counts differ")
    require(math.isclose(sum(row["seconds"] for row in summaries), number(declared["seconds"]), abs_tol=1e-9), "declared XML cost differs")
    return {"suites": summaries, "cases": cases, "executions": len(cases), "seconds": declared["seconds"],
            "identity_rule": "classname + complete name; replace entire isolated prefix through .test.api. with api."}


def source_metadata(receipt, machine, audit, workspace):
    require(set(receipt) == {"schema", "scope", "qualification_pending", "elapsed_seconds", "counts", "core_pins", "selected_sources"}
            and receipt["schema"] == "inventory-current-runtime-selected-source-snapshot@1"
            and receipt["qualification_pending"] is True, "closed selected source receipt scope")
    require(receipt["scope"] == machine["frozen_candidate"]["scope"] and receipt["core_pins"] == machine["frozen_candidate"]["core_pins"]
            and number(receipt["elapsed_seconds"]) == number(machine["frozen_candidate"]["seconds"]), "source metadata review binding")
    repos = {"ipfs_accelerate": (9574, 271242470), "ipfs_datasets": (8466, 175475852), "ipfs_kit": (1341, 34509493)}
    require(set(receipt["selected_sources"]) == set(receipt["counts"]) == set(repos), "complete source metadata owners")
    count, size, core = 0, 0, {}
    require(type(receipt["core_pins"]) is dict and len(receipt["core_pins"]) == 4, "four selected core declarations")
    for repo, expected in repos.items():
        rows = receipt["selected_sources"][repo]
        require(type(rows) is list and count + len(rows) <= 20000, "source metadata population bound")
        keys, repo_bytes = set(), 0
        for row in rows:
            require(type(row) is dict and set(row) == {"path", "relative", "sha256", "bytes"}, "closed source metadata entry")
            relative = lexical_path(row["relative"], absolute=False)
            require(row["path"] == str(workspace / "external" / repo / relative), "source metadata owner/path mismatch")
            digest(row["sha256"])
            require(row["relative"] not in keys, "duplicate source metadata membership")
            keys.add(row["relative"])
            repo_bytes += exact_int(row["bytes"], 2**31)
            if repo == "ipfs_accelerate" and row["relative"] in receipt["core_pins"]:
                core[row["relative"]] = {"bytes": row["bytes"], "sha256": row["sha256"]}
        actual = {"files": len(rows), "bytes": repo_bytes}
        require(actual == receipt["counts"][repo] == machine["frozen_candidate"]["counts"][repo]
                and (len(rows), repo_bytes) == expected, "source metadata aggregate differs")
        count += len(rows)
        size += repo_bytes
    require(core == receipt["core_pins"], "selected core metadata differs")
    generation = audit["selected_generation"]
    require(exact_int(generation["files"]) == count == 19381 and exact_int(generation["bytes"]) == size == 481227815
            and generation["full_transitive_dependency_attestation"] is False and generation["mutable_working_checkout_qualified"] is False,
            "audit source generation declaration scope")
    outer = machine["current_runtime_independent_audit"]["selected_generation"]
    require({key: generation[key] for key in outer} == outer, "machine/audit selected generation differs")
    return {"files": count, "bytes": size, "counts": receipt["counts"], "core_pins": core,
            "producers_cid": generation["producers_cid"], "qualification_pending_preserved": True,
            "scope": "Declared metadata identities only; source bodies and process origin not independently replayed",
            "source_bodies_read": 0, "process_origin_authenticated": False}


def reconcile(docs, bodies, workspace):
    machine, historical, audit, result, container, lifecycle, verification, guard = (
        docs[role] for role in ("machine_review", "historical_review", "independent_worker_audit",
                               "current_worker_result", "container_result", "native_lifecycle", "authored_verification", "source_reader_guard"))
    require(result["schema"] == "codebase-inventory-resume-native-qualification@1"
            and historical["schema"] == "repository-proof-index-inventory-resume-worker-review@1", "selected runtime/history schema")
    require(audit["schema"] == "inventory-resume-worker-independent-audit@1" and audit["qualified"] is True
            and audit["authority"] == "none" and audit["native_jobs_executed"] == audit["native_owner_databases_opened"] == audit["training_steps"] == 0,
            "independent audit scope promoted")
    for key in ("native_jobs_executed", "native_owner_databases_opened", "training_steps"):
        exact_int(audit[key], 0)
    require(machine["production_open_tasks"] == 32 and type(machine["production_open_tasks"]) is int
            and all(machine[key] is False for key in ("384d_qualified", "cuda_qualified", "proof_authority", "production_default_activated",
                "production_task_status_changed", "source_execution_attested", "scan_execution_attested", "numerical_reuse_authorized_by_source_delta")),
            "machine production/authority scope promoted")
    native = machine["native_current_runtime"]
    for key in native:
        if key != "result":
            require(result[key] == native[key] and type(result[key]) is type(native[key]), "machine/native result binding differs: " + key)
    require(result["qualified"] is True and result["worker_launched"] is True and result["native_task_statuses"] ==
            {"INVENTORY-OFFSET": "completed", "INVENTORY-TYPE": "completed"}, "complete recorded native task outcomes")
    require(result["bootstrap_errors"] == [] and exact_int(result["remaining_processes"], 0) == 0, "recorded native cleanup population")
    for key in ("provider_calls", "post_setup_fit_attempt_count", "new_scan_pages_created", "known_actual_setup_epochs"):
        exact_int(result[key], 0)
    require(exact_int(result["inherited_actual_setup_epochs"]) == 2 and result["unknown_fitting_epochs"] is False
            and result["numerical_before"] == result["numerical_after"], "recorded numerical summary differs")
    for key in ("start", "stop", "bootstrap_errors", "worker_launched", "remaining_processes", "residual_task", "observed_worker_allocations", "task_observations"):
        require(lifecycle[key] == result[key], "native lifecycle binding differs")
    for name in ("start", "stop"):
        operation = result[name]
        require(operation["schema"] == "ipfs_accelerate_py/agent-supervisor/operation-result@1"
                and operation["operation"] == name and operation["status"] == "succeeded" and operation["error"] is None,
                "recorded native START/STOP unsuccessful")
    require(result["start"]["tree_id"] == result["stop"]["tree_id"] and result["stop"]["data"]["old_tree_fenced"] is True,
            "recorded STOP does not bind original tree")
    stop = result["stop"]["data"]["isolated_worker_cleanup"]
    require(stop["schema"] == "isolated-worker-stop-observation@1" and stop["single_worker"] is True
            and exact_int(stop["returncode"], 0) == 0 and exact_int(stop["worker_uid"]) == 1001
            and stop["completion_authority"] is False, "recorded isolated cleanup scope")
    allocations = result["observed_worker_allocations"]
    cleanup = docs["cleanup_receipt"]
    require(type(allocations) is list and len(allocations) == 1 and type(cleanup) is list and len(cleanup) == 1,
            "one complete original cleanup allocation")
    require(set(cleanup[0]) == {"allocation", "decision", "scope"} and cleanup[0]["allocation"] == allocations[0]
            and cleanup[0]["scope"] == "explicit owner fixture cleanup after native STOP"
            and cleanup[0]["decision"]["allowed"] is True and cleanup[0]["decision"]["record"] is None
            and cleanup[0]["decision"]["reason"] == "no_lifecycle_record", "recorded explicit cleanup allocation differs")
    require(machine["explicit_owner_worktree_cleanup"]["git_worktrees_administration_absent"] is True,
            "recorded owner administration cleanup absent")
    before, after = docs["execution_scope_before"], docs["execution_scope_after"]
    require(before == after and bodies["execution_scope_before"] == bodies["execution_scope_after"]
            and set(before) == {"binding", "payload"}, "original execution binding changed across STOP")
    payload = before["payload"]
    require(payload["task_population_preserved"] is True and payload["inventory_features_are_advisory"] is True
            and payload["removed_task_cids"] == [] and payload["current_facts"] == []
            and all(payload[key] is False for key in ("completion_authority", "proof_authority", "publication_authority",
                                                     "production_activation", "task_omission_authority")), "execution scope authority/population differs")
    require(verification == result["authored_worker_receipt"], "recorded authored verification differs")
    require(verification["verified"] is True and all(verification[key] is False for key in (
        "completion_authority", "proof_authority", "process_origin_attested", "native_registry_opened",
        "native_inventory_freshness_verified_here", "private_evidence_epoch_verified_here")), "authored receipt scope promoted")
    lines = bodies["worker_stdout"].splitlines()
    require(len(lines) <= 256 and all(len(line) <= 65536 for line in lines), "worker log population bound")
    worker = audit["worker"]
    for key in ("actual_stdout_observation", "actual_boundary_stdout_observation"):
        observed = verification[key]
        line = exact_int(observed["line"], len(lines))
        require(line > 0 and document(lines[line - 1]) == observed["receipt"] == worker[key]["receipt"], "actual worker stdout binding differs")
        log = observed["log"]
        require(log["sha256"] == sha256(bodies["worker_stdout"]).hexdigest() and exact_int(log["bytes"]) == len(bodies["worker_stdout"]), "worker log pin differs")
    boundary = verification["actual_boundary_stdout_observation"]["receipt"]
    authored = verification["actual_stdout_observation"]["receipt"]
    require(exact_int(boundary["uid"]) == exact_int(boundary["euid"]) == exact_int(authored["uid"]) == 1001
            and exact_int(boundary["pid"]) == exact_int(authored["pid"]) == machine["current_runtime_independent_audit"]["actual_worker_pid_in_namespace"],
            "recorded worker identity differs")
    for value in (boundary, authored):
        exact_int(value["provider_calls"], 0)
        exact_int(value["training_steps"], 0)
    require(authored["completion_authority"] is False and authored["proof_authority"] is False
            and boundary["boundary"]["completion_authority"] is False, "worker authority promoted")
    for key in machine["container_closure"]:
        if key != "result":
            require(container[key] == machine["container_closure"][key], "container review binding differs")
    require(container["schema"] == "inventory-resume-worker-offline-container-execution@1" and exact_int(container["returncode"], 0) == 0
            and container["container_removed"] is True and container["host_reservation_released"] is True
            and container["network"] == "none" and container["privileged"] is False
            and container["original_selected_source_changes_after_execution"] == [], "recorded container closure differs")
    require(boundary["boundary"]["container_id"] == container["container_id"] and boundary["boundary"]["image_id"] == container["image_id"],
            "actual worker/container generation differs")
    require(result["final_resources"] == audit["lifecycle"]["native_final_resources"] == {"active_lease_count": 0, "waiting_request_count": 0}, "native resource drain differs")
    host = container["host_resources_after_cleanup"]
    require(host == audit["lifecycle"]["host_final_resources"] and all(exact_int(host[key], 0) == 0 for key in
            ("active_lease_count", "active_child_lease_count", "active_root_lease_count", "waiting_request_count")), "host resource drain differs")
    require(audit["primary_archive"]["preserved"] is True and exact_int(audit["primary_archive"]["passes"]) == 2
            and audit["primary_archive"]["ending_inventory_cid"] == machine["current_runtime_independent_audit"]["archive_inventory_cid"], "recorded archive endpoints differ")
    require(worker["post_stop_receipt_gate_independently_replayed"] is True and worker["current_owner_registry_reopened"] is False,
            "audit post-STOP scope differs")
    test_groups, populations, receipt_costs = {}, {}, {}
    for prefix, rows in (("current_successful_xml", machine["tests"]), ("prior_successful_xml", historical["tests"]), ("failed_xml", machine["failed_tests"])):
        receipts = [xml_receipt(bodies[f"{prefix}_{i:02}"], row) for i, row in enumerate(rows)]
        if prefix != "failed_xml":
            require(all(case["outcomes"] == [] for receipt in receipts for case in receipt["cases"]), "successful receipt has adverse case")
        test_groups[prefix] = receipts
        populations[prefix] = {(case["normalized_classname"], case["name"]) for receipt in receipts for case in receipt["cases"]}
        receipt_costs[prefix] = sum(number(row["seconds"]) for row in receipts)
    old, new, failed = (populations[key] for key in ("prior_successful_xml", "current_successful_xml", "failed_xml"))
    counts = {"prior_distinct": len(old), "new_successful_distinct": len(new), "overlap_prior": len(new & old),
              "new_unique": len(new - old), "combined_distinct": len(new | old),
              "new_successful_executions": sum(row["executions"] for row in test_groups["current_successful_xml"])}
    require(counts == {"prior_distinct": 835, "new_successful_distinct": 252, "overlap_prior": 175,
                      "new_unique": 77, "combined_distinct": 912, "new_successful_executions": 278}, "exact recorded regression population differs")
    require(all(type(machine["test_accounting"][key]) is int and machine["test_accounting"][key] == value for key, value in counts.items()), "machine test identity accounting differs")
    require(exact_int(historical["distinct_pytest_cases"]) == 835 and machine["failed_tests"][1]["failures"] == 8
            and machine["failed_tests"][0]["failures"] == 4 and machine["failed_tests"][0]["errors"] == 3,
            "historical failed constructor outcomes differ")
    require(guard["schema"] == "codebase-source-delta-independent-reader-guards@1" and guard["qualified"] is True
            and exact_int(guard["test_count"]) == 54 and all(exact_int(guard[key], 0) == 0 for key in ("errors", "failures", "skips", "pytest_cases", "native_training_epochs"))
            and guard["native_execution_attested"] is False and guard["source_execution_attested"] is False, "stdlib population promoted into pytest/native")
    require(type(guard["cases"]) is list and len(guard["cases"]) == 54
            and all(type(row) is dict and set(row) == {"id", "status"} and type(row["id"]) is str
                    and 0 < len(row["id"]) <= 8192 and row["status"] == "passed" for row in guard["cases"])
            and len({row["id"] for row in guard["cases"]}) == 54, "distinct separate stdlib case population")
    costs = machine["costs"]
    require(costs["do_not_add_nested_phase_times"] is True
            and number(costs["native_current_runtime_seconds"]) == number(result["recorded_seconds"]) == number(audit["lifecycle"]["native_recorded_seconds"])
            and number(costs["outer_current_runtime_seconds"]) == number(container["elapsed_seconds"]) == number(audit["lifecycle"]["container_total_seconds"])
            and number(costs["current_runtime_independent_audit_seconds"]) == number(audit["recorded_seconds"])
            and math.isclose(number(costs["pytest_failed_receipt_seconds"]), receipt_costs["failed_xml"], abs_tol=1e-9)
            and math.isclose(number(costs["pytest_successful_receipt_seconds"]), receipt_costs["current_successful_xml"], abs_tol=1e-9), "recorded nested cost accounting differs")
    require(math.isclose(receipt_costs["failed_xml"], 105.036, abs_tol=1e-9)
            and math.isclose(number(machine["test_accounting"]["failed_junit_seconds_separate"]), 105.036, abs_tol=1e-9), "failed receipt cost lost")
    source = source_metadata(docs["selected_source_receipt"], machine, audit, workspace)
    return {"test_accounting": counts, "test_receipts": test_groups,
            "failed_trial_distinct_identities": len(failed), "failed_trial_executions": sum(row["executions"] for row in test_groups["failed_xml"]),
            "stdlib_reader_case_count": 54, "stdlib_cases_in_pytest_total": 0,
            "recorded_costs": {"native_seconds": result["recorded_seconds"], "outer_seconds": container["elapsed_seconds"],
                "independent_audit_seconds": audit["recorded_seconds"], "successful_JUnit_seconds": receipt_costs["current_successful_xml"],
                "failed_JUnit_seconds": receipt_costs["failed_xml"], "nested_times_summed": False},
            "declared_source_generation": source, "recorded_native_task_statuses": result["native_task_statuses"],
            "recorded_cleanup": {"allocation": allocations[0], "worker_uid": boundary["uid"], "worker_pid_in_namespace": boundary["pid"],
                "container_id": container["container_id"], "image_id": container["image_id"], "start_status": result["start"]["status"],
                "stop_status": result["stop"]["status"], "original_scope_bytes_unchanged": True,
                "explicit_cleanup_scope": cleanup[0]["scope"], "authority_authenticated": False},
            "historical_generation_frontiers": {"scan_pages_inherited": result["inherited_scan_pages"], "setup_epochs_inherited": 2,
                "new_scan_pages_recorded": 0, "new_setup_epochs_recorded": 0,
                "numerical_summary_equality_only": True, "checkpoint_reconstruction_performed": False,
                "historical_native13_endpoint_disclosure_preserved": machine["limitations"][-1]}}


def population(root, expected):
    require(root.is_absolute() and root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode), "canonical output directory required")
    files, dirs, pending = set(), set(), [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                require(len(files) < MAX_FILES and len(dirs) <= 1, "output population bound")
                if stat.S_ISDIR(info.st_mode):
                    require(relative == "retained", "unexpected output directory")
                    dirs.add(relative)
                    pending.append(Path(entry.path))
                else:
                    require(stat.S_ISREG(info.st_mode) and relative in expected, "unexpected nonregular/output file")
                    files.add(relative)
    require(files == expected and dirs == {"retained"}, "exact output population required")
    return {"file_count": len(files), "directory_count": len(dirs)}


def audit(manifest_path, output, *, relocated_sources=None):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture(relocated_sources)
    manifest_raw = capture.read(manifest_path, mapped=False, maximum=MAX_MANIFEST)
    spec = document(manifest_raw)
    require(set(spec) == {"schema", "selected_profile", "selected_files"} and spec["schema"] == INPUT_SCHEMA
            and spec["selected_profile"] == PROFILE, "closed selected manifest profile")
    rows = spec["selected_files"]
    require(type(rows) is list and len(rows) == 35 and all(type(row) is dict and set(row) == {"role", "path", "sha256", "size_bytes"} for row in rows), "closed selected manifest population")
    require([row["role"] for row in rows] == list(ROLES), "complete fixed ordered selected roles")
    pins = {row["role"]: descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")}) for row in rows}
    if relocated_sources is not None:
        require(type(relocated_sources) is dict and set(relocated_sources) == {row["path"] for row in pins.values()}
                and len(set(relocated_sources.values())) == 35, "exact explicit relocation population")
    machine_pin = pins["machine_review"]
    tail = Path("external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_delta_runtime_review.json")
    machine_path = lexical_path(machine_pin["path"])
    require(machine_path.parts[-len(tail.parts):] == tail.parts and machine_pin["sha256"] == PUBLIC_ANCHOR,
            "independently pinned machine review required")
    bodies = {"machine_review": capture.read(machine_pin["path"], machine_pin)}
    docs = {"machine_review": document(bodies["machine_review"])}
    workspace = machine_path.parents[4]
    for role, declared in (("historical_review", docs["machine_review"]["historical_resume_worker_review"]),
                           ("independent_worker_audit", docs["machine_review"]["current_runtime_independent_audit"]["report"])):
        require(pins[role] == declared_pin(workspace, declared), "independent header raw binding differs")
        bodies[role] = capture.read(pins[role]["path"], pins[role])
        docs[role] = document(bodies[role])
    workspace, _ = selected_bindings(pins, docs)
    for role, pin in pins.items():
        if role not in bodies:
            bodies[role] = capture.read(pin["path"], pin)
        if role not in docs and role in FIXED_ROLES and role != "worker_stdout":
            docs[role] = document(bodies[role], allow_list=role == "cleanup_receipt")
    findings = reconcile(docs, bodies, workspace)
    forbidden = {manifest_path.parent, *(path.parent for path in capture.files)}
    require(not output.exists() and not output.is_symlink() and output.resolve(strict=False) == output
            and not any(output == folder or output.is_relative_to(folder) for folder in forbidden), "fresh output outside input scopes required")
    capture.deadline()
    output.mkdir(parents=True)
    (output / "retained").mkdir()
    retained = Capture(started=capture.started)
    files = []

    def retain(relative, raw):
        path = output / relative
        with path.open("xb") as stream:
            stream.write(raw)
        path.chmod(0o444)
        pin = {"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
        require(retained.read(path, pin) == raw, "written retained copy differs")
        return pin

    inputs = [("input_manifest", str(manifest_path), manifest_raw), *((role, pins[role]["path"], bodies[role]) for role in sorted(pins))]
    for index, (role, original, raw) in enumerate(inputs):
        relative = f"retained/{index:03}.bytes"
        files.append({**retain(relative, raw), "role": role, "relative_path": relative, "original_path": original})
    nested = {"schema": "codebase-ir-current-runtime-cleanup-selected-custody@1", "status": "passed",
              "manifest_sha256": sha256(manifest_raw).hexdigest(), "selected_profile": PROFILE,
              "selected_files": pins, "retained_files": files, "selected_unique_file_count": 35,
              "selected_input_bytes": sum(map(len, bodies.values())), **{flag: False for flag in FALSE_FLAGS}}
    nested_pin = retain("selected_custody.json", bounded_canonical(nested, MAX_REPORT))
    expected = {row["relative_path"] for row in files} | {"selected_custody.json"}
    input_stability, copy_stability = capture.stable(), retained.stable()
    before = population(output, expected)
    report = {"schema": SCHEMA, "status": "passed", "selected_profile": PROFILE,
              "manifest_sha256": sha256(manifest_raw).hexdigest(),
              **{role + "_sha256": pins[role]["sha256"] for role in BINDING_ROLES},
              "selected_file_count": 35, "selected_input_bytes": sum(map(len, bodies.values())),
              "new_native_jobs_launched": 0, "additional_attempted_training_epochs": 0, "source_bodies_read": 0,
              "zero_count_scope": "Work performed by this custody receiver; historical native declarations retain their own scope",
              **findings, "selected_files": pins, "selected_custody": nested_pin, "retained_files": files,
              "input_stability": input_stability, "retained_copy_stability": copy_stability,
              "retained_population_before_report": before, "explicit_relocated_input_map_used": relocated_sources is not None,
              "scope": "Selected historical receipt/test/cost and source metadata consistency; no live or authenticated execution authority",
              "bounds": {"file_bytes": MAX_FILE, "first_capture_bytes": MAX_BYTES, "copy_capture_bytes": MAX_BYTES,
                  "read_files_per_cache": MAX_FILES, "manifest_bytes": MAX_MANIFEST, "main_report_bytes": MAX_REPORT,
                  "deadline_seconds": MAX_SECONDS, "source_metadata_rows": 20000, "XML_cases": 4096,
                  "XML_nodes": 16384, "XML_depth": 8, "JSON_depth": 32, "JSON_containers": 100000, "JSON_values": 600000},
              **{flag: True for flag in TRUE_FLAGS}, **{flag: False for flag in FALSE_FLAGS}}
    report_raw = bounded_canonical(report, MAX_REPORT)
    report_path = output / "current_runtime_cleanup_custody.json"
    with report_path.open("xb") as stream:
        stream.write(report_raw)
    require(Capture.raw(report_path, MAX_REPORT) == report_raw, "written main report differs")
    capture.stable()
    retained.stable()
    population(output, expected | {report_path.name})
    require(Capture.raw(output / "selected_custody.json", nested_pin["size_bytes"]) == canonical(nested), "late local nested report differs")
    require(Capture.raw(report_path, MAX_REPORT) == report_raw, "late main report differs")
    population(output, expected | {report_path.name})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.manifest, args.output)
    print(json.dumps({key: report[key] for key in ("status", "selected_file_count", "selected_input_bytes", "test_accounting")}))


if __name__ == "__main__":
    main()
