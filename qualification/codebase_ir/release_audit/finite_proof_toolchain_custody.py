#!/usr/bin/env python3
"""Reconcile released finite proof and tool declarations without executing their payloads."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import portable_archive as archive
import portable_evidence_children as capsule
import portable_review as portable
import release_matrix as matrix

INPUT_SCHEMA = "codebase-ir-finite-proof-toolchain-custody-input@1"
REPORT_SCHEMA = "codebase-ir-finite-proof-toolchain-custody@1"
CUSTODY_SCHEMA = "codebase-ir-finite-proof-selected-custody@1"
EVIDENCE_ID = "behavioral-native-supervision"
GROUPS = ("cold-observation", "successor-observation", "finite-repair-behavioral-preview")
ROLES = {
    "source": "captured_source.py",
    "driver": "driver.py",
    "compiled": "compiled.json",
    "request": "request.json",
    "trace": "observations.json",
    "python_process": "python_process.json",
    "lean_source": "FiniteInteger.lean",
    "lean_olean": "FiniteInteger.olean",
    "lean_certificate": "lean_certificate.json",
    "lean_process": "lean_process.json",
    "tool_policy": "tool_policy.json",
    "result": "result.json",
}
MAX_INPUT_BYTES = 256 * 1024
MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_READ_FILES = 192
MAX_READ_BYTES = 16 * 1024 * 1024
MAX_SELECTED_OBJECTS = 96
MAX_RETAINED_FILES = 192
MAX_RETAINED_DIRECTORIES = 192
FALSE_FLAGS = (
    *capsule.FALSE_FLAGS,
    "native_tool_bytes_available",
    "transitive_toolchain_dependencies_attested",
    "checker_execution_authenticated",
    "kernel_proof_replayed",
    "historical_execution_environment_authenticated",
    "proof_reuse_eligibility_qualified",
    "source_semantics_verified",
    "source_execution_replayed",
    "owner_sources_imported",
    "domain_cid_recipe_qualified",
)
PROCESS_FIELDS = {
    "cancelled",
    "command",
    "elapsed_ms",
    "error",
    "interface_version",
    "limits",
    "output_truncated",
    "process_tree_terminated",
    "resource_exhausted",
    "returncode",
    "stderr",
    "stdout",
    "termination_reason",
    "timed_out",
    "unavailable",
    "workspace_cleaned",
    "workspace_limit_exceeded",
}
LIMIT_FIELDS = {
    "address_space_bytes",
    "cpu_seconds",
    "max_input_bytes",
    "max_output_bytes",
    "max_output_files",
    "max_workspace_bytes",
    "resident_memory_bytes",
    "timeout_ms",
}
RESULT_FIELDS = {
    "artifacts",
    "behavior_authority",
    "compiled_cid",
    "completion_authority",
    "contract",
    "contract_cid",
    "counterexample",
    "diagnostics",
    "domain_cid",
    "domain_inputs",
    "execution_authority",
    "head",
    "kernel_checked_model_table",
    "lean_certificate",
    "mutation_authority",
    "observations",
    "offset_clause_satisfied",
    "output",
    "profile",
    "proof_authority",
    "python_process",
    "result_cid",
    "runtime_behavior_verified",
    "runtime_observation_coverage_complete",
    "schema",
    "scope",
    "source_cid",
    "source_path",
    "source_semantics_verified",
    "source_sha256",
    "status",
    "tool_policy",
    "tool_policy_cid",
    "trace",
    "trace_cid",
    "type_clause_satisfied",
}


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def raw_cid(raw: bytes) -> str:
    return "b" + base64.b32encode(
        b"\x01\x55\x12\x20" + hashlib.sha256(raw).digest()
    ).decode().lower().rstrip("=")


def cid(value: object) -> str:
    return "b" + base64.b32encode(
        b"\x01\xa9\x02\x12\x20" + hashlib.sha256(canonical_json(value)).digest()
    ).decode().lower().rstrip("=")


def structured_cid(value: object) -> bool:
    if type(value) is not str or len(value) != 61 or not value.startswith("b"):
        return False
    try:
        raw = base64.b32decode(value[1:].upper() + "=" * ((-len(value[1:])) % 8))
    except ValueError:
        return False
    return (
        len(raw) == 37
        and raw.startswith(b"\x01\xa9\x02\x12\x20")
        and "b" + base64.b32encode(raw).decode().lower().rstrip("=") == value
    )


class Capture(matrix.Capture):
    def reserve(self, size: int):
        self.time_check()
        matrix.need(
            type(size) is int
            and 0 <= size <= MAX_PAYLOAD_BYTES
            and self.total_bytes + size <= MAX_READ_BYTES,
            "selected file/Git byte budget reached",
        )
        self.total_bytes += size

    def read(self, path: Path, digest: str | None = None, size: int | None = None) -> bytes:
        matrix.need(
            path in self.cache or len(self.cache) < MAX_READ_FILES, "selected read count reached"
        )
        if size is not None:
            matrix.need(
                type(size) is int and 0 <= size <= MAX_PAYLOAD_BYTES,
                "selected file size cap reached",
            )
        return super().read(path, digest, size)


def spec(raw: bytes) -> dict:
    matrix.need(len(raw) <= MAX_INPUT_BYTES, "input byte ceiling reached")
    value = matrix.document(raw)
    matrix.fields(
        value,
        {"schema", "custody_capsule_manifest", "evidence_id", "selected_groups"},
        "finite custody input",
    )
    matrix.need(
        value["schema"] == INPUT_SCHEMA
        and value["evidence_id"] == EVIDENCE_ID
        and value["selected_groups"] == list(GROUPS),
        "closed evidence/group policy differs",
    )
    pin = value["custody_capsule_manifest"]
    matrix.fields(pin, {"path", "sha256", "size_bytes"}, "child capsule header pin")
    matrix.need(
        matrix.exact_hex(pin["sha256"])
        and type(pin["size_bytes"]) is int
        and 0 <= pin["size_bytes"] <= capsule.MAX_CAPSULE_MANIFEST_BYTES,
        "bounded header pin required",
    )
    return value


class SelectedObjects(capsule.OfflineObjects):
    """Lazy pinned transport only; immutable commit/tree/blob checks remain inherited."""

    def __init__(self, repo: dict, capture: Capture, rows: list, body):
        self.rows, self.store, self.used, self.body = {}, {}, set(), body
        for row in rows:
            matrix.fields(
                row,
                {"repository", "oid", "kind", "path", "sha256", "size_bytes"},
                "prior Git object",
            )
            matrix.need(
                type(row["repository"]) is str
                and matrix.exact_hex(row["oid"], 40)
                and row["kind"] in {"commit", "tree", "blob"}
                and row["path"] == "git_objects/" + row["repository"] + "/" + row["oid"],
                "prior object identity/path differs",
            )
            key = row["repository"], row["oid"]
            matrix.need(key not in self.rows, "duplicate prior Git object")
            self.rows[key] = row
        super().__init__(repo, capture)

    def command(self, args: list[str], limit: int) -> bytes:
        matrix.need(
            type(args) is list and len(args) == 3 and args[0] == "cat-file",
            "closed offline transport required",
        )
        key = self.name, args[2]
        matrix.need(key in self.rows, "required selected proof object absent")
        if key not in self.store:
            matrix.need(
                len(self.store) < MAX_SELECTED_OBJECTS,
                "selected proof object ceiling reached before read",
            )
            row = self.rows[key]
            raw = self.body(capsule.descriptor_from(row))
            framed = row["kind"].encode() + b" " + str(len(raw)).encode() + b"\0" + raw
            matrix.need(
                hashlib.sha1(framed).hexdigest() == row["oid"],
                "selected object framed identity differs",
            )
            self.store[key] = {"kind": row["kind"], "raw": raw}
        return super().command(args, min(limit, MAX_PAYLOAD_BYTES))


def selected_custody(value: dict, capture: Capture) -> dict:
    header_pin = value["custody_capsule_manifest"]
    header_path = matrix.canonical(header_pin["path"])
    matrix.need(header_path.name == capsule.CAPSULE_FILENAME, "selected header filename differs")
    root = header_path.parent
    header_raw = capture.read(header_path, header_pin["sha256"], header_pin["size_bytes"])
    cap, selected, _ = capsule.inventory(header_raw, header_pin["sha256"])
    matrix.need(stat.S_IMODE(root.stat().st_mode) == 0o555, "prior capsule root seal differs")
    used = set()

    def body(pin):
        matrix.need(
            pin == selected.get(pin["path"]),
            "selected descriptor differs from pinned capsule inventory",
        )
        path = root / pin["path"]
        matrix.need(
            stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) == 0o444,
            "selected file seal differs",
        )
        for parent in path.parents:
            if parent == root:
                break
            matrix.need(
                stat.S_IMODE(parent.stat(follow_symlinks=False).st_mode) == 0o555,
                "selected directory seal differs",
            )
        raw = capture.read(path, pin["sha256"], pin["size_bytes"])
        used.add(pin["path"])
        return raw

    source_raw, report_raw = body(cap["source_manifest"]), body(cap["source_report"])
    source, report = matrix.document(source_raw), matrix.document(report_raw)
    capsule.prior_report(report, source_raw)
    scopes = capsule.original_scopes(source, cap["original_inputs"])
    repositories = [
        {key: row[key] for key in ("name", "commit", "package_roots")}
        for row in source["repositories"]
    ]
    matrix.need(cap["repositories"] == repositories, "capsule/source repository roots differ")
    views = {row["relative_path"]: capsule.descriptor_from(row) for row in cap["retained_views"]}
    matrix.need(len(views) == len(cap["retained_views"]), "duplicate retained view")
    ledger_raw = body(views["inputs/ledger.json"])
    ledger = matrix.document(ledger_raw)
    matrix.validate_ledger(ledger)
    matrix.need(
        matrix.sha(ledger_raw) == report["ledger_sha256"] == source["ledger"]["sha256"],
        "ledger source/report pin differs",
    )
    parents = [row for row in report["manifests"] if row["id"] == EVIDENCE_ID]
    matrix.need(len(parents) == 1, "one selected parent required")
    parent = parents[0]
    parent_raw = body(views["manifests/" + EVIDENCE_ID + ".json"])
    matrix.need(
        parent["disposition"] == "expanded"
        and matrix.sha(parent_raw)
        == parent["sha256"]
        == parent["expected_sha256"]
        == ledger["evidence"][EVIDENCE_ID]["sha256"],
        "parent release/ledger pin differs",
    )
    parent_schema, declarations = children.explicit_files(parent_raw)
    matrix.need(
        declarations is not None and parent_schema == "repository-evidence-files@1",
        "explicit released child policy required",
    )
    repos = [row for row in source["repositories"] if row["name"] == parent["repository"]]
    matrix.need(
        len(repos) == 1
        and repos[0]["commit"] == parent["commit"]
        and source["ledger"]["repository"] == parent["repository"],
        "same immutable repository/ledger scope required",
    )
    repo_spec = {**repos[0], "root": str(root / "repository_roots" / parent["repository"])}
    planned = []
    for group in GROUPS:
        for role, filename in ROLES.items():
            relative = group + "/" + filename
            declared = [row for row in declarations if row["path"] == relative]
            memberships = [
                row for row in parent["children"] if row["declared_relative_path"] == relative
            ]
            matrix.need(
                len(declared) == len(memberships) == 1, "exact declared child membership required"
            )
            child, declaration = memberships[0], declared[0]
            matrix.need(
                child["disposition"] == "verified"
                and child["repository"] == parent["repository"]
                and child["commit"] == parent["commit"]
                and child["sha256"] == child["expected_sha256"] == declaration["sha256"]
                and type(child["size_bytes"]) is int
                and child["size_bytes"] == child["expected_size_bytes"] == declaration["bytes"]
                and 0 <= child["size_bytes"] <= MAX_PAYLOAD_BYTES
                and child["path"] == str(PurePosixPath(parent["path"]).parent / relative),
                "released child scope/pins differ",
            )
            view = views[
                "children/" + child["repository"] + "/" + child["commit"] + "/" + child["path"]
            ]
            matrix.need(
                view["sha256"] == child["sha256"] and view["size_bytes"] == child["size_bytes"],
                "selected retained view pin differs",
            )
            planned.append({"group": group, "role": role, "child": child, "view": view})
    matrix.need(
        len(planned) == 36
        and sum(row["child"]["size_bytes"] for row in planned) <= MAX_READ_BYTES // 2,
        "selected population/byte ceiling reached before body reads",
    )
    objects = SelectedObjects(repo_spec, capture, cap["objects"], body)
    ledger_identity, committed_ledger = objects.blob(source["ledger"]["path"])
    parent_identity, committed_parent = objects.blob(parent["path"])
    matrix.need(
        committed_ledger == ledger_raw
        and committed_parent == parent_raw
        and parent_identity["git_blob"] == parent["git_blob"],
        "immutable parent/ledger proof differs",
    )
    bodies, memberships = {}, []
    for row in planned:
        child = row["child"]
        raw = body(row["view"])
        identity, committed = objects.blob(child["path"])
        matrix.need(
            committed == raw and identity["git_blob"] == child["git_blob"],
            "immutable selected child body differs",
        )
        bodies.setdefault(row["group"], {})[row["role"]] = raw
        memberships.append(
            {
                "group": row["group"],
                "role": row["role"],
                "repository": child["repository"],
                "commit": child["commit"],
                "evidence_path": child["path"],
                "declared_relative_path": child["declared_relative_path"],
                "sha256": matrix.sha(raw),
                "size_bytes": len(raw),
                "git_blob": identity["git_blob"],
                "raw_cid": raw_cid(raw),
                "retained_view": row["view"]["path"],
            }
        )
    matrix.need(objects.used == set(objects.store), "selected unused object refused")
    return {
        "root": root,
        "cap": cap,
        "selected": selected,
        "used": used,
        "objects": objects,
        "scopes": scopes,
        "ledger_sha256": matrix.sha(ledger_raw),
        "release_commit": parent["commit"],
        "parent": {
            key: parent[key]
            for key in ("repository", "commit", "path", "sha256", "size_bytes", "git_blob")
        },
        "ledger_git_blob": ledger_identity["git_blob"],
        "bodies": bodies,
        "memberships": memberships,
        "parent_declarations": declarations,
    }


def exact_integer(value: object, *, positive: bool = False) -> bool:
    return type(value) is int and (value > 0 if positive else value >= 0)


def recorded_process(value: dict, command: list[str], policy: dict, kind: str) -> dict:
    matrix.fields(value, PROCESS_FIELDS, "recorded process")
    matrix.need(
        value["command"] == command
        and value["interface_version"] == "bounded-tool-runner/v1"
        and type(value["returncode"]) is int
        and value["returncode"] == 0
        and exact_integer(value["elapsed_ms"])
        and value["termination_reason"] == "completed"
        and value["error"] == ""
        and value["stderr"] == ""
        and type(value["stdout"]) is str
        and len(value["stdout"].encode()) <= MAX_INPUT_BYTES,
        "recorded completed process command/status/type differs",
    )
    matrix.need(
        all(
            value[key] is False
            for key in (
                "cancelled",
                "output_truncated",
                "process_tree_terminated",
                "resource_exhausted",
                "timed_out",
                "unavailable",
                "workspace_limit_exceeded",
            )
        )
        and value["workspace_cleaned"] is True,
        "recorded process flag differs",
    )
    limits = value["limits"]
    matrix.fields(limits, LIMIT_FIELDS, "recorded limits")
    matrix.need(
        all(exact_integer(x, positive=True) for x in limits.values()),
        "recorded finite limits require positive integers",
    )
    declared = policy["process_limits"]
    matrix.need(
        all(
            limits[key] == declared[key]
            for key in (
                "max_input_bytes",
                "max_output_bytes",
                "max_output_files",
                "max_workspace_bytes",
            )
        )
        and all(
            limits[key] == declared[kind][key]
            for key in ("address_space_bytes", "resident_memory_bytes")
        ),
        "process limit/policy declarations differ",
    )
    return {
        "command": command,
        "limits": limits,
        "elapsed_ms": value["elapsed_ms"],
        "stdout_sha256": matrix.sha(value["stdout"].encode()),
        "recorded_returncode": value["returncode"],
        "recorded_status": value["termination_reason"],
        "execution_authenticated": False,
        "resource_enforcement_authenticated": False,
    }


def tool_policy(value: dict) -> None:
    matrix.fields(
        value,
        {
            "schema",
            "profile",
            "python",
            "lean",
            "environment",
            "process_limits",
            "dependency_scope",
            "policy_cid",
        },
        "tool policy",
    )
    matrix.need(
        value["schema"] == "codebase-finite-integer-tools@1"
        and value["profile"] == "python-integer-offset-finite@1"
        and value["policy_cid"] == cid({k: v for k, v in value.items() if k != "policy_cid"})
        and matrix.text(value["dependency_scope"]),
        "recorded tool policy identity/schema differs",
    )
    for kind in ("python", "lean"):
        tool = value[kind]
        matrix.fields(tool, {"path", "sha256", "size_bytes"}, "declared executable")
        path = tool["path"]
        matrix.need(
            type(path) is str
            and PurePosixPath(path).is_absolute()
            and PurePosixPath(path).as_posix() == path
            and ".." not in PurePosixPath(path).parts
            and matrix.exact_hex(tool["sha256"])
            and exact_integer(tool["size_bytes"], positive=True),
            "executable declaration differs",
        )
    matrix.fields(
        value["environment"],
        {"LANG", "LC_ALL", "LEAN_NUM_THREADS", "LEAN_STACK_SIZE_KB", "PATH"},
        "recorded environment",
    )
    matrix.need(
        all(matrix.text(v) for v in value["environment"].values())
        and value["environment"]["LANG"] == value["environment"]["LC_ALL"] == "C"
        and value["environment"]["LEAN_NUM_THREADS"] == "1"
        and value["environment"]["LEAN_STACK_SIZE_KB"].isdigit(),
        "recorded environment profile differs",
    )
    limits = value["process_limits"]
    matrix.fields(
        limits,
        {
            "lean",
            "python",
            "lean_arguments",
            "max_input_bytes",
            "max_output_bytes",
            "max_output_files",
            "max_workspace_bytes",
            "memory_control",
        },
        "recorded policy limits",
    )
    matrix.need(
        limits["lean_arguments"] == ["-j", "1", "-o", "FiniteInteger.olean", "FiniteInteger.lean"]
        and matrix.text(limits["memory_control"])
        and all(
            exact_integer(limits[k], positive=True)
            for k in (
                "max_input_bytes",
                "max_output_bytes",
                "max_output_files",
                "max_workspace_bytes",
            )
        ),
        "recorded policy limit declarations differ",
    )
    for kind in ("python", "lean"):
        matrix.fields(
            limits[kind], {"address_space_bytes", "resident_memory_bytes"}, "memory declaration"
        )
        matrix.need(
            all(exact_integer(v, positive=True) for v in limits[kind].values()),
            "positive memory declarations required",
        )


def reconcile(group: str, raw: dict[str, bytes]) -> dict:
    docs = {
        role: matrix.document(body)
        for role, body in raw.items()
        if role not in {"source", "driver", "lean_source", "lean_olean"}
    }
    result, request, trace, compiled = (
        docs[role] for role in ("result", "request", "trace", "compiled")
    )
    certificate, process, policy = (
        docs[role] for role in ("lean_certificate", "lean_process", "tool_policy")
    )
    matrix.fields(result, RESULT_FIELDS, "finite observation result")
    matrix.need(
        result["schema"] == "codebase-finite-integer-observation@1"
        and result["status"] == "observed"
        and result["profile"] == "python-integer-offset-finite@1",
        "finite observation schema/status/profile differs",
    )
    matrix.need(
        result["result_cid"]
        == cid({key: value for key, value in result.items() if key != "result_cid"}),
        "result structured identity differs",
    )
    matrix.need(
        all(
            result[key] is False
            for key in (
                "behavior_authority",
                "completion_authority",
                "execution_authority",
                "mutation_authority",
                "proof_authority",
                "runtime_behavior_verified",
                "source_semantics_verified",
            )
        ),
        "recorded finite authority upgraded",
    )
    for key in (
        "kernel_checked_model_table",
        "runtime_observation_coverage_complete",
        "type_clause_satisfied",
        "offset_clause_satisfied",
    ):
        matrix.need(type(result[key]) is bool, "exact recorded observation Boolean required")
    artifacts = result["artifacts"]
    matrix.fields(artifacts, set(ROLES) - {"result"}, "complete selected artifact roles")
    output = result["output"]
    matrix.need(
        type(output) is str
        and PurePosixPath(output).is_absolute()
        and PurePosixPath(output).as_posix() == output
        and ".." not in PurePosixPath(output).parts
        and PurePosixPath(output).name == group,
        "original output label differs",
    )
    for role, descriptor in artifacts.items():
        matrix.fields(
            descriptor, {"path", "sha256", "size_bytes", "cid"}, "recorded artifact descriptor"
        )
        matrix.need(
            descriptor["path"] == output + "/" + ROLES[role]
            and descriptor["sha256"] == matrix.sha(raw[role])
            and type(descriptor["size_bytes"]) is int
            and descriptor["size_bytes"] == len(raw[role])
            and descriptor["cid"] == raw_cid(raw[role]),
            "artifact raw CID/SHA/size or role path differs",
        )
    matrix.fields(
        request,
        {"domain_cid", "function_name", "inputs", "source_cid", "source_sha256"},
        "finite request",
    )
    matrix.fields(
        trace,
        {
            "domain_cid",
            "exception_type",
            "inputs",
            "observations",
            "python",
            "schema",
            "source_cid",
            "source_sha256",
            "status",
        },
        "finite trace",
    )
    matrix.need(
        trace["schema"] == "codebase-finite-integer-trace@1"
        and trace["status"] == "complete"
        and trace["exception_type"] is None,
        "recorded trace disposition differs",
    )
    domain = request["inputs"]
    matrix.need(
        type(domain) is list
        and 1 <= len(domain) <= 128
        and all(type(v) is int for v in domain)
        and len(set(domain)) == len(domain)
        and domain == trace["inputs"] == result["domain_inputs"],
        "bounded finite domain differs",
    )
    matrix.need(
        structured_cid(request["domain_cid"])
        and request["domain_cid"] == trace["domain_cid"] == result["domain_cid"],
        "domain reference differs",
    )
    source = raw_cid(raw["source"])
    matrix.need(
        request["source_cid"] == trace["source_cid"] == result["source_cid"] == source
        and request["source_sha256"]
        == trace["source_sha256"]
        == result["source_sha256"]
        == matrix.sha(raw["source"]),
        "captured source byte identities differ",
    )
    observations = trace["observations"]
    matrix.need(
        type(observations) is list and len(observations) == len(domain),
        "recorded observation population differs",
    )
    for expected_input, row in zip(domain, observations, strict=True):
        matrix.fields(row, {"input", "input_type", "output", "output_type"}, "recorded finite row")
        matrix.need(
            type(row["input"]) is int
            and type(row["output"]) is int
            and row["input"] == expected_input
            and row["input_type"] == row["output_type"] == "int",
            "recorded finite row type/order differs",
        )
    matrix.need(
        result["trace"] == trace
        and result["observations"] == observations
        and result["trace_cid"] == cid(trace),
        "trace structured identity/embedded body differs",
    )
    matrix.fields(
        compiled,
        {
            "assumptions",
            "behavior_authority",
            "body_offset",
            "compilation",
            "contract",
            "contract_cid",
            "kernel_checked",
            "parser",
            "profile",
            "revision",
            "schema",
            "source_binding",
            "source_cid",
        },
        "compiled observation",
    )
    matrix.need(
        compiled["schema"] == "codebase-integer-offset-compilation@1"
        and compiled["source_cid"] == source
        and compiled["source_binding"]["content_sha256"] == matrix.sha(raw["source"])
        and result["compiled_cid"] == cid(compiled)
        and compiled["contract_cid"] == result["contract_cid"] == cid(compiled["contract"])
        and compiled["contract"] == result["contract"]
        and compiled["behavior_authority"] is False
        and compiled["kernel_checked"] is False
        and type(compiled["body_offset"]) is int,
        "compiled/source/contract identity or authority differs",
    )
    matrix.need(
        type(compiled["assumptions"]) is list
        and 1 <= len(compiled["assumptions"]) <= 32
        and all(matrix.text(v) for v in compiled["assumptions"]),
        "recorded assumption list differs",
    )
    matrix.fields(
        compiled["contract"],
        {"function_name", "offset", "parameter", "path", "profile", "schema"},
        "recorded finite contract",
    )
    matrix.need(
        type(compiled["contract"]["offset"]) is int
        and request["function_name"] == compiled["contract"]["function_name"]
        and result["source_path"] == compiled["contract"]["path"],
        "finite request/contract selector differs",
    )
    failures = [
        {
            "input": row["input"],
            "observed_output": row["output"],
            "required_output": row["input"] + compiled["contract"]["offset"],
        }
        for row in observations
        if row["output"] != row["input"] + compiled["contract"]["offset"]
    ]
    matrix.need(
        result["offset_clause_satisfied"] is (not failures)
        and result["counterexample"] == (failures[0] if failures else None),
        "recorded table disposition/counterexample differs",
    )
    tool_policy(policy)
    matrix.need(
        result["tool_policy"] == policy and result["tool_policy_cid"] == policy["policy_cid"],
        "embedded tool policy differs",
    )
    matrix.fields(
        certificate,
        {
            "domain_cid",
            "olean_cid",
            "process",
            "schema",
            "scope",
            "source_cid",
            "theorems",
            "tool",
            "trace_cid",
            "version_process",
        },
        "finite Lean certificate",
    )
    matrix.need(
        certificate["schema"] == "codebase-finite-integer-table-certificate@1"
        and certificate["domain_cid"] == request["domain_cid"]
        and certificate["trace_cid"] == cid(trace)
        and certificate["source_cid"] == raw_cid(raw["lean_source"])
        and certificate["olean_cid"] == raw_cid(raw["lean_olean"])
        and certificate["tool"] == policy["lean"]
        and certificate == result["lean_certificate"]
        and matrix.text(certificate["scope"]),
        "certificate bodies or scoped identities differ",
    )
    matrix.fields(process, {"process", "version_process"}, "separate Lean process")
    matrix.need(
        process == {key: certificate[key] for key in process},
        "embedded and separate Lean receipts differ",
    )
    lean_process = recorded_process(
        process["process"],
        [policy["lean"]["path"], *policy["process_limits"]["lean_arguments"]],
        policy,
        "lean",
    )
    version_process = recorded_process(
        process["version_process"], [policy["lean"]["path"], "--version"], policy, "lean"
    )
    matrix.need(
        process["process"]["stdout"] == ""
        and re.fullmatch(r"Lean \(version [^\n]{1,512}\)\n", process["version_process"]["stdout"])
        is not None,
        "recorded Lean output/version format differs",
    )
    python_process = recorded_process(
        docs["python_process"],
        [policy["python"]["path"], "-I", "-S", "driver.py"],
        policy,
        "python",
    )
    matrix.need(
        result["python_process"] == docs["python_process"]
        and matrix.document(docs["python_process"]["stdout"].encode()) == trace,
        "recorded Python stdout and trace differ",
    )
    matrix.fields(
        trace["python"],
        {"cache_tag", "executable", "implementation", "version"},
        "recorded Python version",
    )
    matrix.need(
        trace["python"]["executable"] == policy["python"]["path"]
        and all(matrix.text(v) for v in trace["python"].values()),
        "Python executable/version declarations differ",
    )
    lean_text = raw["lean_source"].decode("utf-8")
    imports = re.findall(r"^[ \t]*import ([A-Za-z][A-Za-z0-9_.]*)$", lean_text, flags=re.M)
    matrix.need(
        imports == ["Init"] and len(re.findall(r"^[ \t]*import\b", lean_text, flags=re.M)) == 1,
        "closed finite Lean import profile differs",
    )
    names = re.findall(r"^theorem ([A-Za-z][A-Za-z0-9_]*)\b", lean_text, flags=re.M)
    matrix.need(
        certificate["theorems"]
        == names
        == [
            "domain_coverage",
            "recorded_integer_types",
            "observed_body_offset",
            "offset_clause" if result["offset_clause_satisfied"] else "offset_counterexample",
        ],
        "declared theorem labels differ from retained text",
    )
    return {
        "group": group,
        "recorded_status": result["status"],
        "source_sha256": matrix.sha(raw["source"]),
        "lean_source_sha256": matrix.sha(raw["lean_source"]),
        "lean_olean_sha256": matrix.sha(raw["lean_olean"]),
        "domain_inputs": domain,
        "domain_cid_claim": request["domain_cid"],
        "domain_cid_recipe_qualified": False,
        "trace_cid": cid(trace),
        "compiled_cid": cid(compiled),
        "contract_cid": result["contract_cid"],
        "result_cid": result["result_cid"],
        "tool_policy_cid": policy["policy_cid"],
        "recorded_type_clause_satisfied": result["type_clause_satisfied"],
        "recorded_offset_clause_satisfied": result["offset_clause_satisfied"],
        "recorded_kernel_checked_model_table": result["kernel_checked_model_table"],
        "recorded_counterexample": result["counterexample"],
        "recorded_table_clauses_reconciled": True,
        "recorded_scope": result["scope"],
        "original_output_label": result["output"],
        "certificate_scope": certificate["scope"],
        "assumptions": compiled["assumptions"],
        "declared_imports": imports,
        "theorem_labels": names,
        "tool_declarations": {
            kind: {
                **policy[kind],
                "custody_disposition": "not_retained_in_selected_public_manifest",
                "bytes_read": False,
                "execution_authenticated": False,
            }
            for kind in ("python", "lean")
        },
        "recorded_environment": policy["environment"],
        "recorded_memory_control": policy["process_limits"]["memory_control"],
        "recorded_dependency_scope": policy["dependency_scope"],
        "recorded_versions": {
            "lean": process["version_process"]["stdout"],
            "python": trace["python"],
        },
        "process_declarations": {
            "lean": lean_process,
            "lean_version": version_process,
            "python": python_process,
        },
        "source_semantics_verified": False,
        "kernel_proof_replayed": False,
        "proof_reuse_eligibility_qualified": False,
    }


def selected_seals(root: Path, files: set[str]) -> None:
    matrix.need(stat.S_IMODE(root.stat().st_mode) == 0o555, "selected capsule root seal drift")
    for relative in files:
        path = root / relative
        matrix.canonical(str(path))
        info = path.stat(follow_symlinks=False)
        matrix.need(
            stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o444,
            "selected file seal drift",
        )
        for parent in path.parents:
            if parent == root:
                break
            matrix.need(
                stat.S_IMODE(parent.stat(follow_symlinks=False).st_mode) == 0o555,
                "selected directory seal drift",
            )


def output_population(root: Path, expected: set[str], capture: Capture) -> dict:
    files, directories, pending = set(), set(), [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                capture.time_check()
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(info.st_mode):
                    matrix.need(len(files) < MAX_RETAINED_FILES, "retained file count reached")
                    files.add(relative)
                else:
                    matrix.need(
                        stat.S_ISDIR(info.st_mode) and len(directories) < MAX_RETAINED_DIRECTORIES,
                        "retained nonregular/directory count refused",
                    )
                    directories.add(relative)
                    pending.append(Path(entry.path))
    planned_dirs = {
        parent.as_posix()
        for relative in expected
        for parent in Path(relative).parents
        if parent != Path(".")
    }
    matrix.need(
        files == expected and directories == planned_dirs, "retained exact population differs"
    )
    return {"file_count": len(files), "directory_count": len(directories)}


def audit(manifest: Path, output: Path) -> dict:
    manifest = matrix.canonical(str(manifest))
    capture = Capture()
    matrix.need(
        manifest.stat().st_size <= MAX_INPUT_BYTES, "input byte ceiling reached before allocation"
    )
    raw = capture.read(manifest)
    value = spec(raw)
    custody = selected_custody(value, capture)
    groups = [reconcile(group, custody["bodies"][group]) for group in GROUPS]
    for group in groups:
        for declaration in group["tool_declarations"].values():
            matching = [
                row["path"]
                for row in custody["parent_declarations"]
                if row["sha256"] == declaration["sha256"]
                and row["bytes"] == declaration["size_bytes"]
            ]
            matrix.need(
                not matching,
                "executable bytes declared by parent require a separately supported custody profile",
            )
            declaration["selected_parent_digest_match_count"] = 0
            declaration["unavailable_scope"] = "selected_parent_explicit_children"
    matrix.need(
        not any(
            PurePosixPath(row["path"]).name in {"Init.lean", "Init.olean", "Init.ilean"}
            for row in custody["parent_declarations"]
        ),
        "compiled Init custody requires a separately supported profile",
    )
    protected = [manifest.parent, custody["root"], *custody["scopes"]]
    for group in groups:
        protected.append(Path(group["original_output_label"]))
        for tool in group["tool_declarations"].values():
            protected.append(Path(tool["path"]).parent)
    capsule.fresh(output, protected)
    output.mkdir(exist_ok=False)
    output = matrix.canonical(str(output), directory=True)
    retained = Capture()
    pins = []

    def copy(relative, body):
        archive.name(relative)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(body)
        pin = portable.pin(relative, body)
        retained.read(target, pin["sha256"], pin["size_bytes"])
        pins.append(pin)
        return pin

    copy("retained/input.json", raw)
    copy(
        "retained/capsule_manifest.json", capture.cache[custody["root"] / capsule.CAPSULE_FILENAME]
    )
    for relative in sorted(custody["used"]):
        copy("retained/custody/" + relative, capture.cache[custody["root"] / relative])
    selected_receipt = {
        "schema": CUSTODY_SCHEMA,
        "status": "passed",
        "custody_capsule_manifest_sha256": value["custody_capsule_manifest"]["sha256"],
        "ledger_sha256": custody["ledger_sha256"],
        "release_commit": custody["release_commit"],
        "parent": custody["parent"],
        "ledger_git_blob": custody["ledger_git_blob"],
        "artifact_memberships": custody["memberships"],
        "selected_git_objects": [
            {
                **custody["objects"].rows[key],
                "retained_as": "retained/custody/" + custody["objects"].rows[key]["path"],
            }
            for key in sorted(custody["objects"].used)
        ],
        "selected_artifact_bindings_reconciled": True,
        "git_object_verification_performed": True,
        **{flag: False for flag in FALSE_FLAGS},
    }
    nested_pin = copy("selected_custody.json", matrix.json_bytes(selected_receipt))
    nested = {
        "path": str(output / nested_pin["path"]),
        "sha256": nested_pin["sha256"],
        "size_bytes": nested_pin["size_bytes"],
    }
    expected = {pin["path"] for pin in pins}
    before = output_population(output, expected, retained)
    input_stability = capture.stability()
    copy_stability = retained.stability()
    matrix.need(
        input_stability["unchanged"] is True and copy_stability["unchanged"] is True,
        "selected original/copy drift refused",
    )
    hashes = {row["sha256"] for row in custody["memberships"]}
    dependency_frontiers = [
        {
            "kind": "lean_compiled_import",
            "name": "Init",
            "group_memberships": list(GROUPS),
            "disposition": "not_retained_in_selected_public_manifest",
            "transitive_inventory_available": False,
        },
        {
            "kind": "python_standard_library",
            "name": "ambient Python standard library",
            "group_memberships": list(GROUPS),
            "disposition": "not_transitively_attested",
            "transitive_inventory_available": False,
        },
        {
            "kind": "native_shared_libraries",
            "name": "ambient shared libraries and launcher runtime",
            "group_memberships": list(GROUPS),
            "disposition": "not_transitively_attested",
            "transitive_inventory_available": False,
        },
        {
            "kind": "native_executable",
            "name": "python",
            "group_memberships": list(GROUPS),
            "disposition": "not_retained_in_selected_public_manifest",
            "transitive_inventory_available": False,
        },
        {
            "kind": "native_executable",
            "name": "lean",
            "group_memberships": list(GROUPS),
            "disposition": "not_retained_in_selected_public_manifest",
            "transitive_inventory_available": False,
        },
    ]
    report = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "manifest_sha256": matrix.sha(raw),
        "custody_capsule_manifest_sha256": value["custody_capsule_manifest"]["sha256"],
        "ledger_sha256": custody["ledger_sha256"],
        "release_commit": custody["release_commit"],
        "scope": "Selected released finite proof/artifact/tool declarations and offline Git custody; no tool execution, dependency closure, runtime or proof reuse qualification.",
        "expansion_policy": children.POLICY,
        "group_count": len(groups),
        "artifact_membership_count": len(custody["memberships"]),
        "unique_body_count": len(hashes),
        "selected_artifact_bytes": sum(row["size_bytes"] for row in custody["memberships"]),
        "selected_git_object_count": len(custody["objects"].used),
        "groups": groups,
        "artifact_memberships": custody["memberships"],
        "dependency_frontiers": dependency_frontiers,
        "tool_declarations": [
            {"group": group["group"], "declarations": group["tool_declarations"]}
            for group in groups
        ],
        "recorded_versions": [
            {"group": group["group"], "versions": group["recorded_versions"]} for group in groups
        ],
        "dependency_frontier_count": len(dependency_frontiers),
        "unattested_dependency_category_count": len(dependency_frontiers),
        "domain_cid_recipe_qualified": False,
        "input_files_unchanged": True,
        "finite_proof_toolchain_custody_inventory_produced": True,
        "selected_artifact_bindings_reconciled": True,
        "git_object_verification_performed": True,
        "selected_custody": nested,
        "input_stability": input_stability,
        "retained_copy_stability": copy_stability,
        "retained_files": pins,
        "retained_before": before,
        "bounds": {
            "max_input_bytes": MAX_INPUT_BYTES,
            "max_payload_bytes": MAX_PAYLOAD_BYTES,
            "max_read_files": MAX_READ_FILES,
            "max_read_bytes": MAX_READ_BYTES,
            "max_selected_git_objects": MAX_SELECTED_OBJECTS,
            "max_retained_files": MAX_RETAINED_FILES,
            "max_retained_directories": MAX_RETAINED_DIRECTORIES,
            "max_seconds": matrix.MAX_SECONDS,
            "max_object_commands": matrix.MAX_COMMANDS,
            "aggregate_first_capture_and_git_read_bytes": capture.total_bytes,
            "stability_policy": "Equal-size sequential rereads; no atomic or execution authentication claim.",
        },
        **{flag: False for flag in FALSE_FLAGS},
    }
    report["retained_after"] = output_population(output, expected, retained)
    matrix.need(
        capture.stability()["unchanged"] is True and retained.stability()["unchanged"] is True,
        "late selected input/copy/receipt drift refused",
    )
    selected_seals(custody["root"], custody["used"] | {capsule.CAPSULE_FILENAME})
    output_population(output, expected, retained)
    target = output / "finite_proof_toolchain_custody.json"
    with target.open("xb") as stream:
        stream.write(matrix.json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.manifest.absolute(), args.output.absolute())
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
        print("finite proof/toolchain custody refused: " + str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "group_count": report["group_count"],
                "artifact_membership_count": report["artifact_membership_count"],
                "dependency_frontier_count": report["dependency_frontier_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
