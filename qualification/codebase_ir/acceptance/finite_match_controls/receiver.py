"""Match explicit authored requirements to historical, inert finite tables."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import stat
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-finite-match-controls-input@1"
REPORT_SCHEMA = "codebase-ir-finite-match-controls@1"
REQUIREMENTS_SCHEMA = "codebase-ir-finite-authored-requirements@1"
ORIGIN = "independently_authored_requirements_over_retained_finite_tables"
GROUPS = ("cold-observation", "successor-observation", "finite-repair-behavioral-preview")
ROLES = ("source", "compiled", "request", "trace", "lean_source", "lean_olean", "lean_certificate", "result")
ANCHORS = {
    "prior_manifest": "5303a265baf20bbfa0b3f9bc3fd5d946cdd7e0b49fa948d2e287694d646db6fe",
    "prior_report": "a818ce74292b706e28f948e9666e3ac2cb41fbcf1356943aa71996e2bfa4fde2",
    "prior_selected_custody": "c5f58dcbcf365a5758b7e255d9801295c343396fcec5df448c192268fc0a5d62",
}
FALSE_FLAGS = (
    "native_execution_performed", "training_executed", "current_authority_claimed",
    "checker_executions_replayed", "kernel_proof_replayed", "source_execution_replayed",
    "source_semantics_verified", "runtime_behavior_verified", "producer_signatures_authenticated",
    "original_request_authenticated", "historical_execution_environment_authenticated",
    "resource_enforcement_authenticated", "domain_cid_recipe_qualified", "proof_reuse_eligibility_qualified",
    "owner_database_opened", "profile_keys_read", "native_export_adoption_qualified", "production_acceptance_qualified",
)
MAX_FILES, MAX_TOTAL, MAX_FILE = 64, 8 * 1024 * 1024, 512 * 1024
MAX_ITEMS, MAX_INTEGER = 32, 2**63 - 1


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def cid(value, raw=False):
    prefix = b"\x01\x55\x12\x20" if raw else b"\x01\xa9\x02\x12\x20"
    digest = hashlib.sha256(value if raw else canonical(value)).digest()
    return "b" + base64.b32encode(prefix + digest).decode().lower().rstrip("=")


def document(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def integer(value):
        need(len(value) <= 20, "JSON integer allocation bound")
        result = int(value)
        need(abs(result) <= MAX_INTEGER, "JSON integer bound")
        return result

    def floating(value):
        need(len(value) <= 64, "JSON float allocation bound")
        result = float(value)
        need(math.isfinite(result), "nonfinite JSON")
        return result

    def constant(_):
        raise ValueError("nonfinite JSON")

    result = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                        parse_int=integer, parse_float=floating, parse_constant=constant)
    pending, count = [(result, 0)], 0
    while pending:
        value, depth = pending.pop()
        count += 1
        need(count <= 40000 and depth <= 32, "JSON structure bound")
        if type(value) is str:
            need(len(value) <= 100000 and not any(0xD800 <= ord(c) <= 0xDFFF for c in value), "JSON string/surrogate bound")
        elif type(value) is dict:
            need(len(value) <= 256, "JSON object bound")
            pending.extend((item, depth + 1) for pair in value.items() for item in pair)
        elif type(value) is list:
            need(len(value) <= 1024, "JSON array bound")
            pending.extend((item, depth + 1) for item in value)
    return result


def keys(value, expected, label):
    need(type(value) is dict and set(value) == set(expected), label + " closed fields")


def text(value, label):
    need(type(value) is str and 0 < len(value) <= 2048, label + " bounded string")


def descriptor(value, extra=()):
    keys(value, ("path", "sha256", "size_bytes", *extra), "descriptor")
    text(value["path"], "descriptor path")
    need(type(value["sha256"]) is str and len(value["sha256"]) == 64
         and all(c in "0123456789abcdef" for c in value["sha256"]), "descriptor SHA256")
    need(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= MAX_FILE, "descriptor byte bound")


class Capture:
    def __init__(self, budget=None):
        self.cache, self.total = {}, 0
        self.budget = budget if budget is not None else {"files": 0, "bytes": 0}

    @staticmethod
    def bounded(path, limit):
        need(path.is_absolute() and path.resolve(strict=True) == path, "canonical regular input path")
        before = path.stat(follow_symlinks=False)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "regular bounded input")
        handle = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            opened = os.fstat(handle)
            need(stat.S_ISREG(opened.st_mode) and opened.st_size <= limit
                 and (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "stable bounded input descriptor")
            with os.fdopen(handle, "rb", closefd=False) as stream:
                raw = stream.read(limit + 1)
            need(len(raw) <= limit, "actual input allocation bound")
            return raw
        finally:
            os.close(handle)

    def take(self, path, pin=None):
        path = Path(path)
        if path not in self.cache:
            need(self.budget["files"] < MAX_FILES, "file allocation bound")
            limit = min(MAX_FILE, MAX_TOTAL - self.budget["bytes"], pin["size_bytes"] if pin else MAX_FILE)
            raw = self.bounded(path, limit)
            self.total += len(raw)
            self.budget["files"] += 1
            self.budget["bytes"] += len(raw)
            self.cache[path] = raw
        raw = self.cache[path]
        if pin is not None:
            need(len(raw) == pin["size_bytes"] and sha(raw) == pin["sha256"], "input raw pin")
        return raw

    def stable(self):
        rows = []
        for path, raw in self.cache.items():
            current = self.bounded(path, len(raw))
            need(current == raw, "late input/copy bytes changed")
            rows.append({"path": str(path), "sha256": sha(raw), "size_bytes": len(raw), "unchanged": True})
        return {"unchanged": True, "files": rows, "scope": "Equal-size sequential rereads; no atomic snapshot claim."}


def finite_rows(group, raw, summary):
    docs = {role: document(body) for role, body in raw.items() if role not in {"source", "lean_source", "lean_olean"}}
    compiled, request, trace, certificate, result = (docs[role] for role in ("compiled", "request", "trace", "lean_certificate", "result"))
    need(request["inputs"] == trace["inputs"] == result["domain_inputs"] == summary["domain_inputs"] == [-2, -1, 0, 1, 2], "complete native finite domain")
    need(all(type(value) is int for value in request["inputs"]), "exact finite integer domain")
    need(request["source_cid"] == trace["source_cid"] == result["source_cid"] == compiled["source_cid"] == cid(raw["source"], raw=True), "source CID binding")
    need(request["source_sha256"] == trace["source_sha256"] == result["source_sha256"] == summary["source_sha256"]
         == compiled["source_binding"]["content_sha256"] == sha(raw["source"]), "source SHA binding")
    need(compiled["contract"] == result["contract"] and compiled["contract_cid"] == result["contract_cid"] == summary["contract_cid"] == cid(compiled["contract"])
         and summary["compiled_cid"] == result["compiled_cid"] == cid(compiled), "compiled/contract CID binding")
    need(compiled["contract"]["function_name"] == request["function_name"] and compiled["contract"]["path"] == result["source_path"]
         and type(compiled["contract"]["offset"]) is int and compiled["contract"]["offset"] == 2, "supported original contract selector")
    need(compiled["assumptions"] == summary["assumptions"] and type(compiled["assumptions"]) is list
         and len(compiled["assumptions"]) == 3 and all(type(value) is str for value in compiled["assumptions"]), "complete source assumptions")
    need(trace["status"] == "complete" and trace["exception_type"] is None and result["trace"] == trace and result["observations"] == trace["observations"], "complete finite trace")
    rows = trace["observations"]
    need(type(rows) is list and len(rows) == 5, "finite trace row population")
    for value, row in zip(request["inputs"], rows, strict=True):
        keys(row, ("input", "output", "input_type", "output_type"), "finite row")
        need(type(row["input"]) is type(row["output"]) is int and row["input"] == value
             and row["input_type"] == row["output_type"] == "int", "ordered exact integer trace row")
    need(result["trace_cid"] == certificate["trace_cid"] == summary["trace_cid"] == cid(trace)
         and result["result_cid"] == summary["result_cid"] == cid({k: v for k, v in result.items() if k != "result_cid"}), "trace/result CID binding")
    need(result["lean_certificate"] == certificate and certificate["source_cid"] == cid(raw["lean_source"], raw=True)
         and certificate["olean_cid"] == cid(raw["lean_olean"], raw=True) and certificate["scope"] == summary["certificate_scope"], "separate certificate/Lean body binding")
    need(request["domain_cid"] == trace["domain_cid"] == result["domain_cid"] == certificate["domain_cid"] == summary["domain_cid_claim"], "domain reference binding")
    for role in ROLES:
        if role != "result":
            artifact = result["artifacts"][role]
            need(artifact["sha256"] == sha(raw[role]) and type(artifact["size_bytes"]) is int
                 and artifact["size_bytes"] == len(raw[role]) and artifact["cid"] == cid(raw[role], raw=True), "selected artifact role binding")
    failures = [{"input": row["input"], "observed_output": row["output"], "required_output": row["input"] + 2}
                for row in rows if row["output"] != row["input"] + 2]
    need(result["offset_clause_satisfied"] is summary["recorded_offset_clause_satisfied"] is (not failures)
         and result["counterexample"] == summary["recorded_counterexample"] == (failures[0] if failures else None), "recorded offset disposition")
    need(result["kernel_checked_model_table"] is summary["recorded_kernel_checked_model_table"] is True
         and result["type_clause_satisfied"] is summary["recorded_type_clause_satisfied"] is True, "recorded table flags")
    need(all(result[key] is False for key in ("behavior_authority", "completion_authority", "execution_authority", "mutation_authority", "proof_authority", "runtime_behavior_verified", "source_semantics_verified")), "historical support cannot become runtime authority")
    need(all(summary[key] is False for key in ("kernel_proof_replayed", "source_semantics_verified", "proof_reuse_eligibility_qualified", "domain_cid_recipe_qualified")), "unqualified prior scope")
    return {"group": group, "rows": rows, "source_sha256": sha(raw["source"]), "source_cid": request["source_cid"],
            "compiled_cid": cid(compiled), "contract_cid": compiled["contract_cid"], "trace_cid": cid(trace),
            "certificate_sha256": sha(raw["lean_certificate"]), "certificate_scope": certificate["scope"],
            "domain_cid_claim": request["domain_cid"], "assumptions": compiled["assumptions"], "contract_offset": 2}


def property_schema(value):
    need(type(value) is dict and type(value.get("kind")) is str, "property declared")
    kind = value["kind"]
    if kind in {"integer_offset", "runtime_offset"}:
        keys(value, ("kind", "offset"), "offset property")
        need(type(value["offset"]) is int and abs(value["offset"]) <= MAX_INTEGER, "exact integer property offset")
    elif kind == "integer_output":
        keys(value, ("kind",), "integer property")
    elif kind == "unavailable":
        keys(value, ("kind", "name"), "unavailable property")
        need(type(value["name"]) is str and value["name"] in {"universal_source_semantics", "checker_timeout_custody"}, "closed unavailable property")
    else:
        raise ValueError("unsupported property schema")


def match_requirements(fixture, evidence):
    keys(fixture, ("schema", "requirements", "tasks"), "authored requirement ledger")
    need(fixture["schema"] == REQUIREMENTS_SCHEMA, "authored requirement schema")
    requirements, tasks = fixture["requirements"], fixture["tasks"]
    need(type(requirements) is list and 0 < len(requirements) <= MAX_ITEMS
         and type(tasks) is list and 0 < len(tasks) <= MAX_ITEMS, "complete bounded requirement/task lists")
    ids, matched = set(), []
    for requirement in requirements:
        keys(requirement, ("id", "text", "group", "source_sha256", "compiled_cid", "assumptions", "property", "requested_domain"), "requirement")
        text(requirement["id"], "requirement ID")
        text(requirement["text"], "original requirement text")
        need(len(requirement["id"]) <= 64 and len(requirement["text"]) <= 512, "requirement authored text allocation bounds")
        need(requirement["id"] not in ids, "duplicate requirement ID")
        ids.add(requirement["id"])
        need(type(requirement["group"]) is str and requirement["group"] in evidence, "requirement group binding")
        selected = evidence[requirement["group"]]
        need(requirement["source_sha256"] == selected["source_sha256"] and requirement["compiled_cid"] == selected["compiled_cid"]
             and requirement["assumptions"] == selected["assumptions"], "requirement source/compiled/assumption binding")
        domain, prop = requirement["requested_domain"], requirement["property"]
        need(type(domain) is list and len(domain) <= MAX_ITEMS and all(type(value) is int and abs(value) <= MAX_INTEGER for value in domain)
             and domain == sorted(set(domain)), "canonical sorted unique exact integer requested domain")
        property_schema(prop)
        rows = {row["input"]: row for row in selected["rows"]}
        covered, uncovered = [value for value in domain if value in rows], [value for value in domain if value not in rows]
        applicable = "empty" if not domain else "complete" if not uncovered else "partial" if covered else "none"
        disposition, reason, counterexample = "uncovered", "requested_domain_not_fully_observed", None
        if prop["kind"] == "runtime_offset":
            disposition, reason = "runtime_deferred", "recorded_table_does_not_qualify_source_runtime"
        elif prop["kind"] == "unavailable":
            disposition, reason = "unsupported", "selected_property_evidence_unavailable"
        elif prop["kind"] == "integer_offset" and prop["offset"] != selected["contract_offset"]:
            disposition, reason = "unsupported", "property_differs_from_bound_recorded_contract"
        elif not domain:
            reason = "empty_domain_is_unknown_not_vacuous_support"
        else:
            failures = [{"input": value, "observed_output": rows[value]["output"], "required_output": value + prop["offset"]}
                        for value in covered if prop["kind"] == "integer_offset" and rows[value]["output"] != value + prop["offset"]]
            if failures:
                disposition, reason, counterexample = "recorded_refuted", "captured_finite_row_counterexample", failures[0]
            elif not uncovered:
                disposition, reason = "recorded_supported", "complete_requested_finite_rows_under_recorded_assumptions"
        matched.append({"original_requirement": requirement, "disposition": disposition, "reason": reason, "domain_applicability": applicable,
                        "covered_inputs": covered, "uncovered_inputs": uncovered, "counterexample": counterexample,
                        "selected_evidence": {key: selected[key] for key in ("group", "source_sha256", "source_cid", "compiled_cid", "contract_cid", "trace_cid", "certificate_sha256", "certificate_scope", "domain_cid_claim", "assumptions")},
                        "runtime_fact": False, "proof_reuse_eligible": False})
    conflicts = []
    for index, first in enumerate(requirements):
        for second in requirements[index + 1:]:
            if first["group"] == second["group"] and first["property"]["kind"] == second["property"]["kind"] == "integer_offset" and first["property"]["offset"] != second["property"]["offset"]:
                shared = sorted(set(first["requested_domain"]) & set(second["requested_domain"]))
                if shared:
                    conflicts.append({"requirement_ids": [first["id"], second["id"]], "shared_inputs": shared,
                                      "scope": "Authored incompatible integer offsets; no runtime/proof contradiction authority."})
    task_ids, retained_tasks, referenced = set(), [], set()
    by_id = {row["original_requirement"]["id"]: row for row in matched}
    for task in tasks:
        keys(task, ("id", "requirement_ids", "runtime_obligation"), "task")
        text(task["id"], "task ID")
        need(len(task["id"]) <= 64, "task ID allocation bound")
        need(task["id"] not in task_ids, "duplicate task ID")
        task_ids.add(task["id"])
        refs = task["requirement_ids"]
        need(type(refs) is list and 0 < len(refs) <= MAX_ITEMS and all(type(value) is str and value in ids for value in refs)
             and len(set(refs)) == len(refs), "complete unique task requirement references")
        need(task["runtime_obligation"] == "unqualified_source_runtime", "explicit task runtime residual")
        referenced.update(refs)
        retained_tasks.append({"original_task": task, "requirement_dispositions": [{"id": value, "disposition": by_id[value]["disposition"]} for value in refs],
                               "runtime_disposition": "deferred_unqualified", "execution_eligible": False})
    need(referenced == ids, "every requirement retained in task population")
    return matched, retained_tasks, conflicts


def population(root, expected):
    need(root.resolve(strict=True) == root and stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "canonical output directory root")
    files, dirs, pending = set(), set(), [root]
    wanted_dirs = {parent.as_posix() for name in expected for parent in Path(name).parents if parent != Path(".")}
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(info.st_mode):
                    need(relative in expected and len(files) < MAX_FILES, "unexpected retained output file")
                    files.add(relative)
                else:
                    need(stat.S_ISDIR(info.st_mode) and relative in wanted_dirs and len(dirs) < MAX_FILES, "unexpected retained output directory")
                    dirs.add(relative)
                    pending.append(Path(entry.path))
    need(files == expected and dirs == wanted_dirs, "exact retained output population")
    return {"file_count": len(files), "directory_count": len(dirs)}


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture()
    manifest_raw = capture.take(manifest_path)
    manifest = document(manifest_raw)
    keys(manifest, ("schema", "fixture_origin", "requirements", "prior_manifest", "prior_report", "prior_selected_custody", "groups"), "input manifest")
    need(manifest["schema"] == INPUT_SCHEMA and manifest["fixture_origin"] == ORIGIN, "independent input schema/origin")
    descriptors = []
    for role in ("requirements", *ANCHORS):
        descriptor(manifest[role])
        descriptors.append((role, manifest[role]))
    need(type(manifest["groups"]) is list and len(manifest["groups"]) == 3, "complete group input population")
    for group, expected_group in zip(manifest["groups"], GROUPS, strict=True):
        keys(group, ("group", "artifacts"), "group input")
        need(group["group"] == expected_group and type(group["artifacts"]) is list and len(group["artifacts"]) == len(ROLES), "ordered group role population")
        for value, role in zip(group["artifacts"], ROLES, strict=True):
            descriptor(value, ("role",))
            need(value["role"] == role, "ordered role input")
            descriptors.append((expected_group + "/" + role, value))
    need(len({value["path"] for _, value in descriptors}) == len(descriptors), "ambiguous input descriptor paths")
    scopes = {manifest_path.parent, *(Path(value["path"]).parent for _, value in descriptors)}
    need(not output.exists() and output.resolve(strict=False) == output
         and not any(output == scope or output.is_relative_to(scope) or scope.is_relative_to(output) for scope in scopes), "fresh output outside input scopes")
    bodies = {role: capture.take(Path(value["path"]), value) for role, value in descriptors}
    for role, expected in ANCHORS.items():
        need(sha(bodies[role]) == expected, "independent immutable prior anchor " + role)
    prior_manifest, prior, selected = (document(bodies[role]) for role in ANCHORS)
    need(prior_manifest["schema"] == "codebase-ir-finite-proof-toolchain-custody-input@1"
         and prior["schema"] == "codebase-ir-finite-proof-toolchain-custody@1" and prior["status"] == "passed"
         and selected["schema"] == "codebase-ir-finite-proof-selected-custody@1" and selected["status"] == "passed", "prior receiving schemas")
    need(prior["manifest_sha256"] == sha(bodies["prior_manifest"]) and prior["selected_custody"]["sha256"] == sha(bodies["prior_selected_custody"])
         and selected["artifact_memberships"] == prior["artifact_memberships"], "independent original input/report/selected joins")
    members = {(row["group"], row["role"]): row for row in prior["artifact_memberships"]}
    need(len(members) == len(prior["artifact_memberships"]) == 36 and [row["group"] for row in prior["groups"]] == list(GROUPS), "prior complete membership/groups")
    need(all(prior[flag] is False for flag in ("native_execution_performed", "current_authority_claimed", "kernel_proof_replayed", "source_semantics_verified", "domain_cid_recipe_qualified")), "prior authority remains unqualified")
    evidence = {}
    for group, summary in zip(manifest["groups"], prior["groups"], strict=True):
        label = group["group"]
        for value in group["artifacts"]:
            member = members[label, value["role"]]
            need(value["sha256"] == member["sha256"] and value["size_bytes"] == member["size_bytes"]
                 and cid(bodies[label + "/" + value["role"]], raw=True) == member["raw_cid"], "immutable prior member role/raw binding")
        evidence[label] = finite_rows(label, {role: bodies[label + "/" + role] for role in ROLES}, summary)
    fixture = document(bodies["requirements"])
    matched, tasks, conflicts = match_requirements(fixture, evidence)
    capture.stable()
    output.mkdir(parents=True)
    retained = Capture(capture.budget)
    retained_files = []
    for index, (original, raw) in enumerate(capture.cache.items()):
        relative = "retained/" + str(index).zfill(2) + ".bytes"
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        value = {"path": str(target), "sha256": sha(raw), "size_bytes": len(raw)}
        retained.take(target, value)
        retained_files.append({"original_path": str(original), "relative_path": relative, **value})
    expected = {row["relative_path"] for row in retained_files}
    population(output, expected)
    counts = {value: sum(row["disposition"] == value for row in matched) for value in ("recorded_supported", "recorded_refuted", "uncovered", "unsupported", "runtime_deferred")}
    report = {"schema": REPORT_SCHEMA, "status": "passed", "fixture_origin": ORIGIN, "manifest_sha256": sha(manifest_raw),
              **{role + "_sha256": sha(bodies[role]) for role in ("requirements", *ANCHORS)},
              "requirements": matched, "tasks": tasks, "authored_incompatible_pairs": conflicts,
              "group_count": 3, "retained_finite_row_count": 15, "requirement_count": len(matched), "task_count": len(tasks),
              **{key + "_count": value for key, value in counts.items()}, "runtime_residual_task_count": len(tasks),
              "authored_incompatible_pair_count": len(conflicts), "retained_files": retained_files,
              "authored_requirement_matching_conformance": True, "retained_finite_rows_reconciled": True,
              "original_requirements_and_tasks_preserved": True, "input_files_unchanged": True,
              "runtime_fact_count": 0, "tasks_omitted_count": 0, "additional_attempted_training_epochs": 0,
              **{flag: False for flag in FALSE_FLAGS},
              "scope": "Authored finite-domain requirements over historical recorded rows and exact retained assumptions. No source runtime, authenticated checker, proof reuse or production authority. Missing domain and property custody remains unknown."}
    report["input_stability"] = capture.stable()
    report["retained_copy_stability"] = retained.stable()
    report["retained_population_before_report"] = population(output, expected)
    encoded = canonical(report) + b"\n"
    need(len(encoded) <= MAX_FILE, "generated report byte bound")
    with (output / "finite_match_controls.json").open("xb") as stream:
        stream.write(encoded)
    final_expected = expected | {"finite_match_controls.json"}
    report_raw = Capture.bounded(output / "finite_match_controls.json", MAX_FILE)
    need(document(report_raw) == report, "written report roundtrip")
    capture.stable()
    retained.stable()
    population(output, final_expected)
    need(Capture.bounded(output / "finite_match_controls.json", len(report_raw)) == report_raw, "final report reread")
    population(output, final_expected)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.manifest, args.output)
    except (ValueError, OSError, RecursionError, OverflowError, KeyError, TypeError) as exc:
        parser.exit(2, "finite match receiver refused: " + str(exc) + "\n")
    print(json.dumps({"status": result["status"], "requirements": result["requirement_count"], "tasks": result["task_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
