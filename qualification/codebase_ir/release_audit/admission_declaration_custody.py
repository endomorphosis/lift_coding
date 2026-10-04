#!/usr/bin/env python3
"""Audit released admission declarations and recorded test history as inert data."""
from __future__ import annotations

import argparse
import re
import stat
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import finite_proof_toolchain_custody as transport
import portable_archive as archive
import portable_evidence_children as capsule
import portable_review as portable
import release_matrix as matrix

INPUT_SCHEMA = "codebase-ir-admission-declaration-custody-input@1"
REPORT_SCHEMA = "codebase-ir-admission-declaration-custody@1"
CUSTODY_SCHEMA = "codebase-ir-admission-declaration-selected-custody@1"
EVIDENCE_ID = "behavioral-repository-admission"
PROFILE = "released-test-declarations@1"
RUNS = (
    "rpi014-behavioral-first-tests", "rpi014-behavioral-second-tests",
    "rpi014-behavioral-third-tests", "rpi014-behavioral-fourth-tests",
    "rpi014-behavioral-fifth-tests", "rpi014-behavioral-sixth-tests",
    "rpi014032-joined-tests", "rpi014-final-08-tests", "rpi014-final09-tests",
)
SELECTED = ("README.md", "producer-sources.json", "qualification.json",
            *(stem + suffix for stem in RUNS for suffix in (".log", ".xml")))
MUTATIONS = ("authority", "model", "snapshot_fact", "snapshot_requirement", "retained_blob", "match_meaning")
OWNER_CASE = "test_actual_v2_gate_reopens_native_owners_and_worker_without_private_keys"
MUTATION_CASE = "test_resigned_mutations_cannot_invent_current_proof_or_planning_meaning"
FINAL_CASES = (OWNER_CASE, *(MUTATION_CASE + "[" + name + "]" for name in MUTATIONS),
               "test_missing_native_source_database_is_not_recreated",
               "test_dirty_dependency_before_dispatch_refuses_signed_snapshot",
               "test_dependency_change_during_private_write_fails_worker_without_completion")
SOURCE_PATHS = (
    "ipfs_accelerate_py/agent_supervisor/runtime/repository_behavioral_admission.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/repository_behavioral_runner.py",
    "test/integration/test_repository_behavioral_admission.py",
)
FALSE_FLAGS = (*capsule.FALSE_FLAGS, "signature_envelope_custody_verified",
    "signed_admission_bindings_complete", "signature_authentication_performed",
    "owner_authorization_authenticated", "historical_checker_execution_authenticated",
    "recorded_controls_replayed", "native_task_population_verified",
    "live_admission_eligibility_verified", "proof_reuse_eligibility_qualified",
    "source_semantics_verified", "owner_sources_imported", "model_off_execution_authenticated",
    "training_absence_certified", "full_daemon_lifecycle_custody_verified",
    "producer_source_bodies_retained")
MAX_INPUT_BYTES = transport.MAX_INPUT_BYTES
MAX_CASES = 32
MAX_XML_NODES = 256
MAX_XML_DEPTH = 8


def spec(raw):
    matrix.need(len(raw) <= MAX_INPUT_BYTES, "input byte ceiling reached")
    value = matrix.document(raw)
    matrix.fields(value, {"schema", "custody_capsule_manifest", "evidence_id", "selected_profile"}, "admission input")
    matrix.need(value["schema"] == INPUT_SCHEMA and value["evidence_id"] == EVIDENCE_ID
                and value["selected_profile"] == PROFILE, "closed admission profile required")
    pin = value["custody_capsule_manifest"]
    matrix.fields(pin, {"path", "sha256", "size_bytes"}, "capsule descriptor")
    matrix.need(matrix.exact_hex(pin["sha256"]) and type(pin["size_bytes"]) is int
                and 0 <= pin["size_bytes"] <= capsule.MAX_CAPSULE_MANIFEST_BYTES,
                "bounded exact capsule pin required")
    return value


def selected_custody(value, capture):
    pin = value["custody_capsule_manifest"]
    header_path = matrix.canonical(pin["path"])
    matrix.need(header_path.name == capsule.CAPSULE_FILENAME, "capsule header filename differs")
    root = header_path.parent
    header_raw = capture.read(header_path, pin["sha256"], pin["size_bytes"])
    cap, selected, _ = capsule.inventory(header_raw, pin["sha256"])
    used = set()

    def body(descriptor):
        matrix.need(descriptor == selected.get(descriptor["path"]), "descriptor/capsule pin differs")
        transport.selected_seals(root, {descriptor["path"]})
        raw = capture.read(root / descriptor["path"], descriptor["sha256"], descriptor["size_bytes"])
        used.add(descriptor["path"])
        return raw

    source_raw, prior_raw = body(cap["source_manifest"]), body(cap["source_report"])
    source, prior = matrix.document(source_raw), matrix.document(prior_raw)
    capsule.prior_report(prior, source_raw)
    scopes = capsule.original_scopes(source, cap["original_inputs"])
    repos = [{k: row[k] for k in ("name", "commit", "package_roots")} for row in source["repositories"]]
    matrix.need(repos == cap["repositories"], "capsule/source repositories differ")
    views = {row["relative_path"]: capsule.descriptor_from(row) for row in cap["retained_views"]}
    matrix.need(len(views) == len(cap["retained_views"]), "duplicate retained view")
    ledger_raw = body(views["inputs/ledger.json"])
    ledger = matrix.document(ledger_raw)
    matrix.validate_ledger(ledger)
    matrix.need(matrix.sha(ledger_raw) == source["ledger"]["sha256"] == prior["ledger_sha256"], "ledger pin differs")
    parents = [row for row in prior["manifests"] if row["id"] == EVIDENCE_ID]
    matrix.need(len(parents) == 1, "one admission parent required")
    parent = parents[0]
    parent_raw = body(views["manifests/" + EVIDENCE_ID + ".json"])
    matrix.need(parent["disposition"] == "expanded" and matrix.sha(parent_raw) == parent["sha256"]
                == parent["expected_sha256"] == ledger["evidence"][EVIDENCE_ID]["sha256"], "parent pin differs")
    schema, declarations = children.explicit_files(parent_raw)
    matrix.need(schema == "closed-local-evidence-manifest@1" and declarations is not None,
                "closed local admission child policy required")
    matrix.need(len(declarations) == len(SELECTED) and {row["path"] for row in declarations} == set(SELECTED),
                "exact21 declared admission children required")
    repo = [row for row in source["repositories"] if row["name"] == parent["repository"]]
    matrix.need(len(repo) == 1 and repo[0]["commit"] == parent["commit"]
                and source["ledger"]["repository"] == parent["repository"], "same immutable repository scope required")
    objects = transport.SelectedObjects({**repo[0], "root": str(root / "repository_roots" / parent["repository"])},
                                        capture, cap["objects"], body)
    ledger_identity, committed_ledger = objects.blob(source["ledger"]["path"])
    parent_identity, committed_parent = objects.blob(parent["path"])
    matrix.need(committed_ledger == ledger_raw and committed_parent == parent_raw
                and parent_identity["git_blob"] == parent["git_blob"], "immutable ledger/parent proof differs")
    bodies, memberships = {}, []
    matrix.need(len(parent["children"]) == len(SELECTED), "exact prior child population required")
    matrix.need(sum(row["bytes"] for row in declarations) <= transport.MAX_READ_BYTES // 2,
                "selected child byte reservation exceeded")
    for relative in SELECTED:
        ds = [row for row in declarations if row["path"] == relative]
        ms = [row for row in parent["children"] if row["declared_relative_path"] == relative]
        matrix.need(len(ds) == len(ms) == 1, "unique explicit child membership required")
        declaration, member = ds[0], ms[0]
        matrix.need(member["disposition"] == "verified" and member["repository"] == parent["repository"]
                    and member["commit"] == parent["commit"] and member["sha256"] == member["expected_sha256"] == declaration["sha256"]
                    and type(member["size_bytes"]) is int and member["size_bytes"] == member["expected_size_bytes"] == declaration["bytes"]
                    and member["path"] == str(PurePosixPath(parent["path"]).parent / relative), "child declarations/scope differ")
        view = views["children/" + member["repository"] + "/" + member["commit"] + "/" + member["path"]]
        matrix.need(view["sha256"] == member["sha256"] and view["size_bytes"] == member["size_bytes"], "child view pin differs")
        raw = body(view)
        identity, committed = objects.blob(member["path"])
        matrix.need(raw == committed and identity["git_blob"] == member["git_blob"], "immutable child bytes differ")
        bodies[relative] = raw
        memberships.append({"declared_relative_path": relative, "repository": member["repository"], "commit": member["commit"],
            "evidence_path": member["path"], "sha256": matrix.sha(raw), "size_bytes": len(raw), "git_blob": identity["git_blob"],
            "raw_cid": transport.raw_cid(raw), "retained_view": view["path"]})
    matrix.need(objects.used == set(objects.store), "unused selected Git object refused")
    return {"root": root, "cap": cap, "used": used, "objects": objects, "scopes": scopes,
        "ledger_sha256": matrix.sha(ledger_raw), "release_commit": parent["commit"], "source_child_report_sha256": matrix.sha(prior_raw),
        "parent": {k: parent[k] for k in ("repository", "commit", "path", "sha256", "size_bytes", "git_blob")},
        "ledger_git_blob": ledger_identity["git_blob"], "bodies": bodies, "memberships": memberships}


def decimal_text(value):
    matrix.need(type(value) is str and re.fullmatch(r"[0-9]{1,6}(?:\.[0-9]{1,9})?", value) is not None,
                "bounded nonnegative decimal text required")
    return Decimal(value)


def xml_run(raw):
    matrix.need(len(raw) <= transport.MAX_PAYLOAD_BYTES and b"<!" not in raw,
                "XML declarations/entities/comments outside closed profile")
    text = raw.decode("utf-8")
    matrix.need("\x00" not in text and re.match(r"<\?xml version=['\"]1\.0['\"] encoding=['\"]utf-8['\"]\?>", text) is not None,
                "closed UTF-8 XML encoding required")
    # Depth/count limits are enforced during streaming parse, before building a tree.
    parser, depth, count = ET.XMLPullParser(events=("start", "end")), 0, 0
    for position in range(0, len(text), 1024):
        parser.feed(text[position:position + 1024])
        for event, _ in parser.read_events():
            depth += 1 if event == "start" else -1
            if event == "start":
                count += 1
            matrix.need(0 <= depth <= MAX_XML_DEPTH and count <= MAX_XML_NODES, "XML structure bounds reached")
    parser.close()
    root = ET.fromstring(raw)
    matrix.need(root.tag == "testsuites" and root.attrib == {"name": "pytest tests"} and len(root) == 1,
                "one closed pytest suite required")
    suite = root[0]
    matrix.need(suite.tag == "testsuite" and set(suite.attrib) == {"name", "errors", "failures", "skipped", "tests", "time", "timestamp", "hostname"}
                and suite.attrib["name"] == "pytest", "closed pytest suite fields required")
    totals = {}
    for key in ("tests", "failures", "errors", "skipped"):
        text = suite.attrib[key]
        matrix.need(re.fullmatch(r"0|[1-9][0-9]?", text) is not None and int(text) <= MAX_CASES, "bounded canonical pytest count required")
        totals[key] = int(text)
    decimal_text(suite.attrib["time"])
    matrix.need(len(suite) == totals["tests"], "declared/case population differs")
    cases, seen = [], set()
    for case in suite:
        matrix.need(case.tag == "testcase" and set(case.attrib) == {"classname", "name", "time"}
                    and case.attrib["classname"] == "integration.test_repository_behavioral_admission"
                    and len(case.attrib["name"]) <= 256 and case.attrib["name"] not in seen and len(case) <= 1,
                    "closed unique pytest case required")
        seen.add(case.attrib["name"])
        decimal_text(case.attrib["time"])
        outcome = "passed"
        message = None
        if len(case):
            child = case[0]
            matrix.need(child.tag in {"error", "failure", "skipped"} and set(child.attrib) == {"message"}
                        and len(child) == 0 and len(child.attrib["message"]) <= 4096, "closed pytest outcome required")
            outcome, message = child.tag, child.attrib["message"]
        cases.append({"name": case.attrib["name"], "recorded_outcome": outcome, "recorded_seconds": case.attrib["time"],
                      "diagnostic_message": message, "execution_authenticated": False})
    matrix.need(all(sum(row["recorded_outcome"] == tag for row in cases) == totals[key]
                    for key, tag in (("failures", "failure"), ("errors", "error"), ("skipped", "skipped"))),
                "pytest outcome counts differ")
    return {**totals, "recorded_seconds": suite.attrib["time"], "cases": cases}


def log_summary(raw, suite):
    text = raw.decode("utf-8")
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    matrix.need("\x1b" not in text, "unsupported terminal control in log")
    matches = re.findall(r"^=+ (.+?) in ([0-9]+(?:\.[0-9]+)?)s(?: \([^\n]*\))? =+$", text, re.M)
    matrix.need(len(matches) == 1, "one recorded terminal pytest result required")
    summary, seconds = matches[0]
    parts = summary.split(", ")
    counts = {}
    for part in parts:
        match = re.fullmatch(r"([0-9]{1,2}) (passed|failed|error|errors|skipped)", part)
        matrix.need(match is not None, "closed terminal pytest outcomes required")
        key = {"failed": "failure", "errors": "error"}.get(match[2], match[2])
        matrix.need(key not in counts, "duplicate terminal outcome")
        counts[key] = int(match[1])
    expected = {"passed": suite["tests"] - suite["failures"] - suite["errors"] - suite["skipped"],
                "failure": suite["failures"], "error": suite["errors"], "skipped": suite["skipped"]}
    matrix.need(counts == {key: val for key, val in expected.items() if val}, "log/XML outcome counts differ")
    collected = re.findall(r"^collected ([0-9]{1,2}) items?$", text, re.M)
    matrix.need(len(collected) == 1 and suite["tests"] <= int(collected[0]) <= MAX_CASES,
                "bounded collected/recorded case populations required")
    decimal_text(seconds)
    return {"recorded_terminal_seconds": seconds, "recorded_outcomes": counts,
            "recorded_collected_case_count": int(collected[0]),
            "collected_cases_without_retained_outcome": int(collected[0]) - suite["tests"],
            "population_scope": "Pytest collection and recorded case outcomes; no native task omission inferred.",
            "duration_recipe": "Log session and XML suite clocks are retained separately; no exact elapsed-time equivalence claim."}


def reconcile(bodies):
    matrix.need(set(bodies) == set(SELECTED), "closed selected body set required")
    qualification = matrix.document(bodies["qualification.json"])
    matrix.fields(qualification, {"schema", "scope", "distinct_tests", "final_passed", "final_skipped", "tests", "authority",
        "live_checks", "artifact_integrity_controls", "diagnostics", "full_daemon_evidence", "limitations"}, "qualification")
    matrix.need(qualification["schema"] == "repository-behavioral-admission-qualification@1"
                and qualification["scope"] == "explicit finite Python integer-offset, model-off, local independently signed task profile",
                "closed recorded qualification scope required")
    matrix.need(type(qualification["distinct_tests"]) is type(qualification["final_passed"]) is type(qualification["final_skipped"]) is int
                and (qualification["distinct_tests"], qualification["final_passed"], qualification["final_skipped"]) == (10, 10, 0),
                "exact final recorded counts required")
    matrix.fields(qualification["authority"], {"proof", "execution", "completion", "omission"}, "recorded authority")
    matrix.need(all(flag is False for flag in qualification["authority"].values()), "recorded authority promotion refused")
    controls = qualification["artifact_integrity_controls"]
    matrix.fields(controls, {"count", "fresh_checker_per_control", "description"}, "artifact controls")
    matrix.need(type(controls["count"]) is int and controls["count"] == 6 and controls["fresh_checker_per_control"] is False
                and type(controls["description"]) is str and 1 <= len(controls["description"]) <= 2048,
                "six reused-match controls are not six fresh checker executions")
    matrix.need(type(qualification["tests"]) is list and len(qualification["tests"]) == len(RUNS), "exact nine recorded attempts required")
    history = []
    for stem, declaration in zip(RUNS, qualification["tests"], strict=True):
        matrix.fields(declaration, {"log", "xml", "tests", "failures", "errors", "skipped", "time"}, "run declaration")
        matrix.need(declaration["log"] == stem + ".log" and declaration["xml"] == stem + ".xml", "ordered declared run membership differs")
        suite = xml_run(bodies[stem + ".xml"])
        matrix.need(all(declaration[key] == str(suite[key]) for key in ("tests", "failures", "errors", "skipped"))
                    and declaration["time"] == suite["recorded_seconds"], "qualification/XML declarations differ")
        log = log_summary(bodies[stem + ".log"], suite)
        matrix.need(log["recorded_collected_case_count"] == (21 if stem == "rpi014032-joined-tests" else 10),
                    "closed recorded collection population differs")
        history.append({"run": stem, "log_sha256": matrix.sha(bodies[stem + ".log"]),
                        "xml_sha256": matrix.sha(bodies[stem + ".xml"]), **suite, **log,
                        "recorded_scope": "Historical pytest declaration only; no replay or signer authentication."})
    final = history[-1]
    matrix.need(tuple(row["name"] for row in final["cases"]) == FINAL_CASES
                and all(row["recorded_outcome"] == "passed" for row in final["cases"]), "exact ten final recorded cases required")
    matrix.need(all(row["errors"] + row["failures"] > 0 for row in history[:-1]), "eight adverse attempts must remain adverse")
    # This public profile declares metadata and diagnostics, not full signed envelopes.
    for key, maximum in (("live_checks", 12), ("limitations", 12)):
        rows = qualification[key]
        matrix.need(type(rows) is list and 1 <= len(rows) <= maximum and len(set(rows)) == len(rows)
                    and all(type(row) is str and 1 <= len(row) <= 2048 for row in rows), "bounded recorded text list required")
    matrix.fields(qualification["diagnostics"], {"first", "third_fourth", "second_fifth_sixth_joined_eighth"}, "recorded diagnostics")
    matrix.need(all(type(row) is str and 1 <= len(row) <= 2048 for row in qualification["diagnostics"].values()), "bounded diagnostics required")
    matrix.need(qualification["full_daemon_evidence"] == "../repository-behavioral-supervision-20261002", "closed outside-scope pointer required")
    producer = matrix.document(bodies["producer-sources.json"])
    matrix.fields(producer, {"schema", "repository", "sources"}, "producer declaration")
    matrix.need(producer["schema"] == "repository-behavioral-admission-sources@1" and producer["repository"] == "accelerate"
                and type(producer["sources"]) is list and len(producer["sources"]) == 3, "three recorded source declarations required")
    sources = []
    for expected, row in zip(SOURCE_PATHS, producer["sources"], strict=True):
        matrix.fields(row, {"path", "sha256", "size_bytes"}, "producer source claim")
        matrix.need(row["path"] == expected and matrix.exact_hex(row["sha256"])
                    and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= transport.MAX_PAYLOAD_BYTES, "closed producer source pin required")
        sources.append({**row, "disposition": "source_body_not_declared_by_selected_parent", "source_bytes_read": False,
                        "producer_execution_authenticated": False})
    readme = bodies["README.md"].decode()
    matrix.need("Six re-signed artifact controls" in readme and "not six fresh checker executions" in readme,
                "README reused-checker limitation differs")
    frontiers = [
        {"role": role, "disposition": disposition, "body_retained": False, "binding_complete": False,
         "scope": "Exact21 explicitly declared selected parent children only; quoted traceback fragments are not envelope bodies."}
        for role, disposition in (
            ("task_declaration", "recorded_profile_only_missing_body"),
            ("signed_admission", "recorded_profile_only_missing_body"),
            ("signed_behavioral_handoff", "recorded_controls_only_missing_body"),
            ("proof_snapshot", "recorded_controls_only_missing_body"),
            ("retained_native_artifact_bundle", "recorded_controls_only_missing_body"),
            ("intent_match", "recorded_controls_only_missing_body"),
            ("plan", "not_declared_in_selected_public_evidence"),
            ("baseline", "not_declared_in_selected_public_evidence"),
            ("critic", "not_declared_in_selected_public_evidence"),
            ("signature_and_public_key", "not_declared_in_selected_public_evidence"),
        )]
    return {"recorded_profile": qualification["scope"], "recorded_authority": qualification["authority"],
        "recorded_run_count": len(history), "adverse_recorded_run_count": len(history) - 1,
        "recorded_case_membership_count": sum(row["tests"] for row in history), "final_recorded_test_count": len(final["cases"]),
        "collected_cases_without_retained_outcome": sum(row["collected_cases_without_retained_outcome"] for row in history),
        "resigned_control_count": controls["count"], "fresh_checker_per_control": False,
        "control_match_reuse_declaration": controls["description"], "run_history": history,
        "final_controls": [{"case": row["name"], "role": "re_signed_artifact_control" if row["name"].startswith(MUTATION_CASE)
            else "recorded_owner_or_source_fence_case", "recorded_outcome": row["recorded_outcome"],
            "fresh_checker_execution_authenticated": False, "control_replayed": False} for row in final["cases"]],
        "producer_source_claim_count": len(sources), "producer_source_claims": sources,
        "recorded_live_checks": qualification["live_checks"], "recorded_diagnostics": qualification["diagnostics"],
        "recorded_limitations": qualification["limitations"], "envelope_frontiers": frontiers,
        "lifecycle_scope": {"recorded_owner_reopen_case": OWNER_CASE, "successor_or_restart_body_custody": "outside_selected_parent",
            "full_daemon_evidence_pointer": qualification["full_daemon_evidence"], "pointer_followed": False,
            "recorded_attempt_order_is_successor_generation_order": False},
        "signed_identity_recipe": "unavailable_without_complete_signed_bodies; no CID/signature recipe inferred"}


def population(root, expected, capture):
    matrix.canonical(str(root), directory=True)
    matrix.need(stat.S_ISDIR(root.stat(follow_symlinks=False).st_mode), "retained root alias refused")
    return transport.output_population(root, expected, capture)


def audit(manifest, output):
    manifest = matrix.canonical(str(manifest))
    capture = transport.Capture()
    matrix.need(manifest.stat().st_size <= MAX_INPUT_BYTES, "input ceiling reached before allocation")
    raw = capture.read(manifest)
    value = spec(raw)
    custody = selected_custody(value, capture)
    declarations = reconcile(custody["bodies"])
    capsule.fresh(output, [manifest.parent, custody["root"], *custody["scopes"]])
    output.mkdir(exist_ok=False)
    output = matrix.canonical(str(output), directory=True)
    retained, pins = transport.Capture(), []

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
    copy("retained/capsule_manifest.json", capture.cache[custody["root"] / capsule.CAPSULE_FILENAME])
    for relative in sorted(custody["used"]):
        copy("retained/custody/" + relative, capture.cache[custody["root"] / relative])
    selected = {"schema": CUSTODY_SCHEMA, "status": "passed", "parent": custody["parent"],
        "custody_capsule_manifest_sha256": value["custody_capsule_manifest"]["sha256"],
        "ledger_sha256": custody["ledger_sha256"], "release_commit": custody["release_commit"],
        "source_child_report_sha256": custody["source_child_report_sha256"], "ledger_git_blob": custody["ledger_git_blob"],
        "artifact_memberships": custody["memberships"], "selected_git_objects": [
            {**custody["objects"].rows[key], "retained_as": "retained/custody/" + custody["objects"].rows[key]["path"]}
            for key in sorted(custody["objects"].used)],
        "git_object_verification_performed": True, "selected_artifact_bindings_reconciled": True,
        **{flag: False for flag in FALSE_FLAGS}}
    nested_pin = copy("selected_custody.json", matrix.json_bytes(selected))
    expected = {pin["path"] for pin in pins}
    before = population(output, expected, retained)
    originals, copies = capture.stability(), retained.stability()
    matrix.need(originals["unchanged"] is copies["unchanged"] is True, "original/copy drift refused")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw),
        "custody_capsule_manifest_sha256": value["custody_capsule_manifest"]["sha256"],
        "ledger_sha256": custody["ledger_sha256"], "release_commit": custody["release_commit"],
        "selected_parent_sha256": custody["parent"]["sha256"], "source_child_report_sha256": custody["source_child_report_sha256"],
        "scope": "Released admission declarations, recorded pytest history and explicit missing envelope bodies; no signatures, owners, checker replay or current eligibility authenticated.",
        "expansion_policy": children.POLICY, "artifact_membership_count": len(custody["memberships"]),
        "selected_artifact_bytes": sum(row["size_bytes"] for row in custody["memberships"]),
        "selected_git_object_count": len(custody["objects"].used), "artifact_memberships": custody["memberships"], **declarations,
        "selected_custody": {"path": str(output / nested_pin["path"]), "sha256": nested_pin["sha256"], "size_bytes": nested_pin["size_bytes"]},
        "admission_declaration_custody_inventory_produced": True, "selected_artifact_bindings_reconciled": True,
        "git_object_verification_performed": True, "recorded_qualification_history_reconciled": True,
        "recorded_control_population_reconciled": True, "input_files_unchanged": True,
        "runtime_fact_count": 0, "tasks_omitted_count": 0, "additional_attempted_training_epochs": 0,
        "zero_count_scope": "Facts, omissions and work produced by this receiving audit; historical task/training absence is not certified.",
        "input_stability": originals, "retained_copy_stability": copies, "retained_files": pins, "retained_before": before,
        "bounds": {"max_input_bytes": MAX_INPUT_BYTES, "max_payload_bytes": transport.MAX_PAYLOAD_BYTES,
            "max_read_files": transport.MAX_READ_FILES, "max_read_bytes": transport.MAX_READ_BYTES,
            "max_git_objects": transport.MAX_SELECTED_OBJECTS, "max_xml_cases": MAX_CASES,
            "max_xml_nodes": MAX_XML_NODES, "max_xml_depth": MAX_XML_DEPTH,
            "max_seconds": matrix.MAX_SECONDS, "max_object_commands": matrix.MAX_COMMANDS,
            "aggregate_first_capture_and_git_read_bytes": capture.total_bytes,
            "stability_policy": "Bounded equal-size sequential rereads; no atomic transaction claim."},
        **{flag: False for flag in FALSE_FLAGS}}
    report["retained_after"] = population(output, expected, retained)
    matrix.need(capture.stability()["unchanged"] is retained.stability()["unchanged"] is True, "late original/copy/receipt drift refused")
    transport.selected_seals(custody["root"], custody["used"] | {capsule.CAPSULE_FILENAME})
    population(output, expected, retained)
    with (output / "admission_declaration_custody.json").open("xb") as stream:
        stream.write(matrix.json_bytes(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.manifest.absolute(), args.output.absolute())
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError, ET.ParseError) as exc:
        print("admission declaration custody refused: " + str(exc), file=sys.stderr)
        return 1
    print(matrix.json_bytes({"status": result["status"], "recorded_run_count": result["recorded_run_count"],
                            "final_recorded_test_count": result["final_recorded_test_count"]}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
