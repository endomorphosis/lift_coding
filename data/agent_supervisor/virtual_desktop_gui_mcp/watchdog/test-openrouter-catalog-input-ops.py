"""Synthetic pure R23 verifier regressions; fixtures grant no GUI authority."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r23_catalog_verifier_tests", HERE / "verify-openrouter-catalog-input-repair.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=")
H = lambda value: hashlib.sha256(value).hexdigest()


def authority():
    return {"gui_acceptance": False, "work_complete": False, "completion_authority": False}


def public_fixture():
    ids = sorted([v.TARGET_MODEL, v.NEIGHBOR_MODEL] + [f"example/model-{i:03d}" for i in range(466)])
    raw = v.compact({"data": [{"id": item, "pricing": {"prompt": "0"}} for item in ids]})
    raw += b" " * (787610 - len(raw))
    descriptor = {**v.DESCRIPTOR, "raw_sha256": H(raw), "model_ids_sha256": H(v.compact(ids))}
    descriptor["local_url"] = f'/vdg-public-inputs/openrouter/{descriptor["raw_sha256"]}.json'
    provenance = {"schema": "swissknife.openrouter-observed-public-input.v1", "source_url": v.SOURCE_URL,
                  "final_url": v.SOURCE_URL, "http_status": 200, "requested_at": "2026-10-22T17:51:25+00:00",
                  **{key: descriptor[key] for key in ("raw_sha256", "raw_bytes", "model_count", "model_ids_sha256", "observed_at")},
                  "raw_filename": descriptor["raw_sha256"] + ".json", "reconstructed": False,
                  "provider_execution": False, **authority()}
    provenance_bytes = v.compact(provenance)
    descriptor["provenance_sha256"] = H(provenance_bytes)
    descriptor["provenance_url"] = f'/vdg-public-inputs/openrouter/provenance-{H(provenance_bytes)}.json'
    return ids, raw, provenance_bytes, descriptor


def metadata():
    return {"mode": "snapshot", "verified": True, "input_sha256": v.RAW_SHA256,
            "model_ids_sha256": v.MODEL_IDS_SHA256, "model_count": 468, "raw_bytes": 787610,
            "original_source": v.SOURCE_URL, "observed_at": v.OBSERVED_AT,
            "local_url": v.DESCRIPTOR["local_url"], "provenance_url": v.DESCRIPTOR["provenance_url"],
            "provenance_sha256": v.PROVENANCE_SHA256, "cache_ttl_ms": None, "stale": False,
            "error": None, "cache_age_ms": 1000}


def browser_fixture(directory, ids, raw, provenance):
    state = {"mode": "snapshot", "metadata": metadata(), "model_ids": ids, "model_count": 468,
             "favorite_ids": [], "default_model": v.NEIGHBOR_MODEL, "current_tab": "models",
             "stored": {key: "[]" for key in v.STORAGE_KEYS}, "api_key_present": False,
             "events": [], "writes": [], "dialogs": [], "selected_copies": [], "guard_checked_launches": 12}
    state["stored"]["openrouter_settings"] = json.dumps({"defaultModel": v.NEIGHBOR_MODEL})
    report = {"schema": "swissknife.openrouter-catalog-snapshot-smoke.v1", "passed": True, **authority(),
              "candidate_module_override": False, "source_sha256": v.SOURCES[v.APP],
              "canonical_source_sha256": v.SOURCES[v.APP], "canonical_source_sha256_after": v.SOURCES[v.APP],
              "canonical_source_unchanged": True, "candidate_source_unchanged": True, "descriptor": v.DESCRIPTOR,
              "flag": "1", "guard_coverage": True, "guard_source_sha256": v.SOURCES[v.GUARD],
              "source_hashes": {key: v.SOURCES[key] for key in (v.APP, v.MAIN, v.HELPER, v.COLLECTOR, v.SMOKE)},
              "posts_attempted": [], "posts_blocked": [], "external_catalog_gets": [], "page_errors": [],
              "network_observer_errors": [], "profiles": [], "input_responses": [], "module_responses": [],
              "screenshot_sha256": {}, "owned_resources_closed": True,
              "resources": {"vite_pid": 100, "chrome_pid": 101, "vite_pid_absent": True, "chrome_pid_absent": True},
              "tracked_processes": [{"pid": pid, "uid": 1003, "ppid": 1, "pgid": pid, "sid": pid,
                                      "start_tick": str(pid * 10), "same_identity_alive": False} for pid in (100, 101)]}
    report["source_hashes"]["guard_module"] = v.SOURCES[v.GUARD]
    for transport in v.TRANSPORTS:
        current = copy.deepcopy(state)
        profile = {"transport": transport, "passed": True, "initial": copy.deepcopy(current),
                   "nonunique_selectors": [], "missing_model_actions": [], "original_controls": [],
                   "actual_guard_preflight": {"schema": "swissknife.openrouter-input-preflight.v1", "checked_launches": 1,
                                              "provider_execution": False, **authority()}, "cases": []}
        profile["original_controls"] = [{"selector": v.selector(model, action)} for model in ids for action in ("favorite", "info", "try", "default")] + [{"selector": f"#other-{i}"} for i in range(9)]
        for index, (action, model) in enumerate(v.ACTIONS):
            before = copy.deepcopy(current)
            event = {"trusted": True, "model": model, "action": action, "placement": "catalog", "close": False}
            current["events"].append(event)
            if action == "favorite":
                if index == 6:
                    current["favorite_ids"].remove(model)
                else:
                    current["favorite_ids"].append(model)
                current["favorite_ids"].sort()
                current["stored"]["openrouter_favorites"] = json.dumps(current["favorite_ids"])
                current["writes"].append({"key": "openrouter_favorites", "length": len(current["stored"]["openrouter_favorites"])})
            elif action == "info":
                current["dialogs"].append("Actual fixture info " + model)
            elif action == "try":
                current["current_tab"] = "playground"
                current["default_model"] = model
            else:
                current["default_model"] = model
                current["stored"]["openrouter_settings"] = json.dumps({"defaultModel": model})
                current["writes"].extend({"key": key, "length": len(current["stored"][key])} for key in sorted(v.STORAGE_KEYS))
                current["selected_copies"] = [{"model": model, "placement": placement, "text": "✓ Default", "pressed": "true", "card_default": True}
                                               for placement in (["catalog", "favorites"] if model in current["favorite_ids"] else ["catalog"])]
            case = {"index": index, "model": model, "action": action, "selector": v.selector(model, action),
                    "click_ms": 500, "before": before, "after": copy.deepcopy(current), "trusted_events": [event]}
            for phase in ("before", "after"):
                name = f"{transport}-{index}-{phase}.png"
                (directory / name).write_bytes(IMAGE)
                report["screenshot_sha256"][name] = H(IMAGE)
                case["screenshot_" + phase] = name
            profile["cases"].append(case)
            if index == 2:
                current["current_tab"] = "models"
        profile["final_reopen"] = copy.deepcopy(current)
        profile["programmatic_refresh"] = {"method": "existing app.loadModels()", "ui_control": False,
                                           "before": metadata(), "after": metadata(), "input_response_count_before": 2,
                                           "input_response_count_after": 2}
        report["profiles"].append(profile)
        for name, content, route, expected in (("catalog", raw, v.DESCRIPTOR["local_url"], v.RAW_SHA256),
                                                ("provenance", provenance, v.DESCRIPTOR["provenance_url"], v.PROVENANCE_SHA256)):
            file = f"{transport}-actual-{name}.json"
            (directory / file).write_bytes(content)
            report["input_responses"].append({"transport": transport, "path": route, "status": 200,
                                               "intercepted": False, "sha256": expected, "bytes": len(content), "file": file})
        compiled = ('import.meta.env = {"VITE_VDG_OPENROUTER_CATALOG_SNAPSHOT":"1"};\n' + v.RAW_SHA256 + v.PROVENANCE_SHA256).encode()
        file = f"{transport}-actual-vite-module.js"
        (directory / file).write_bytes(compiled)
        report["module_responses"].append({"transport": transport, "status": 200, "original_path": "/js/apps/openrouter.js",
                                            "candidate_module_override": False, "raw_source_sha256": v.SOURCES[v.APP],
                                            "transformed_sha256": H(compiled), "actual_vite_env_injection": True,
                                            "actual_vite_snapshot_env": True, "source_selection": "canonical",
                                            "from_service_worker": False, "file": file})
    return report


def preservation_fixture():
    counts = {"storage": 193, "datasets": 137, "accelerate": 261, "network": 138, "control": 128}
    cells = {cell: {"input_fingerprint": "a" * 64, "report_sha256": "b" * 64,
                    "run_id": cell.replace("/", "-") + "-synthetic", "row_count": counts[cell.split("/")[0][4:]]} for cell in v.UNAFFECTED}
    baseline = {"schema": "swissknife.vdg-catalog-input-ten-before.v1", "source_before": {v.APP: v.OLD_APP_SHA256}, "cells": cells, **authority()}
    live = {"inventory": {"current": True}, "fingerprints": {cell: row["input_fingerprint"] for cell, row in cells.items()},
            "acquisitions": {cell: {**row, "capture_complete": True} for cell, row in cells.items()}}
    record = {"schema": "swissknife.vdg-openrouter-catalog-preservation.v1", "before_app_sha256": v.OLD_APP_SHA256,
              "after_app_sha256": v.SOURCES[v.APP], "cells": {cell: {"before_input_fingerprint": row["input_fingerprint"],
              "after_input_fingerprint": row["input_fingerprint"], "run_id": row["run_id"], "report_sha256": row["report_sha256"]} for cell, row in cells.items()}, **authority()}
    return record, live, baseline


def transition_fixture():
    def block(task, fields):
        return "## " + task + " Synthetic unit task\n\n" + "\n".join("- " + key + ": " + value for key, value in fields.items()) + "\n"
    task_ids = [*v.COMMANDS, "VDG-013-R22", *[f"VDG-800-R{i}" for i in range(57)]]
    before = "# Synthetic unit admission fixture; no execution authority\n\n"
    after = before
    for task in task_ids:
        fields = {"Status": "pending" if task in v.COMMANDS else "completed", "Depends on": "VDG-013-R22" if task == "VDG-039-R01" else "",
                  "Acceptance": "all original obligations retained", "Resource class": "cpu-browser" if task in v.COMMANDS else "cpu-small",
                  "Implementation timeout seconds": "46800" if task == "VDG-039-R01" else "1800", "Attempt count": "7", "Refusal count": "3"}
        if task in v.COMMANDS:
            fields["Deterministic command"], fields["Validation"] = v.COMMANDS[task]
        if fields["Status"] == "completed":
            fields["Completion"] = "original immutable natural completion"
        before += block(task, fields) + "\n"
        changed = dict(fields)
        if task in v.COMMANDS:
            changed["Deterministic command"] = v.WRAPPER_PREFIX + fields["Deterministic command"]
            changed["Validation"] = v.WRAPPER_PREFIX + fields["Validation"]
        if task == "VDG-039-R01":
            changed["Depends on"] += ", " + v.REPAIR
        after += block(task, changed) + "\n"
    new = {"Status": "pending", "Priority": "P0", "Track": "gate-recovery", "Depends on": "VDG-013-R22",
           "Recovery for": "VDG-039-R01", "Deterministic command": v.VERIFY_COMMAND, "Validation": v.VERIFY_COMMAND,
           "Resource class": "cpu-small", "Implementation timeout seconds": "1800", "Predicted files": v.APP,
           "Conflict policy": "Preserve all holds and original acceptance", "Acceptance": "source-bound public input repair only; all12 downstream gates remain"}
    after += block(v.REPAIR, new)
    return before, after, v.parse_board(after)[1][v.REPAIR]["fields"]


def final_go_fixture():
    _, admitted, _ = transition_fixture()
    admitted = admitted.replace("# Synthetic unit admission fixture; no execution authority\n", "# Synthetic unit admission fixture; no execution authority\n" + v.PROGRAM_NO_GO_LINE + "\n", 1)
    complete = admitted.replace("- Status: pending\n", "- Status: completed\n- Completion: lane_resume deterministic command exit 0 at 2026-10-22T23:59:00Z\n")
    current = complete.replace(v.PROGRAM_NO_GO_LINE, v.PROGRAM_GO_LINE, 1)
    acquisitions = {cell: {"family": cell.split("/")[0], "transport": cell.split("/")[1], "capture_complete": True,
                           "input_fingerprint": "a" * 64, "report_sha256": "b" * 64, "row_count": 2} for cell in v.FINAL_CELLS}
    families = {}
    for family in v.FINAL_FAMILIES:
        fresh = {"schema": "swissknife.virtual-desktop-gui-mcp-family.v1", "family": family,
                 "decision": "GO", "passed": True, "clicked": True, "gap_count": 0, "gaps": [], "gap_counts": {},
                 "reasons": [], "input_fingerprint": "c" * 64, "evidence_sources": [{"path": "synthetic", "sha256": "d" * 64}],
                 "generated_at": "2026-10-22T23:59:00Z", "work_complete": False, "completion_authority": False}
        families[family] = {"fresh": fresh, "stored": {**fresh, "generated_at": "2026-10-22T23:58:59Z"}, "stored_sha256": "e" * 64}
    aggregate = {"schema": "swissknife.virtual-desktop-gui-mcp-coverage.v1", "decision": "GO", "passed": True, "clicked": True,
                 "gap_count": 0, "gaps": [], "gap_counts": {}, "reasons": [], "repair_tasks": [], "work_complete": False,
                 "completion_authority": False, "observed_invocation_count": 0, "executed_tool_count": 0,
                 "families": [{key: record["fresh"][key] for key in ("family", "input_fingerprint", "evidence_sources", "decision", "passed", "clicked", "gap_count")} for record in families.values()],
                 "generated_at": "2026-10-22T23:59:00Z"}
    proof = {"schema": "swissknife.vdg-r23-final-go-evidence.v1", "inventory": {"current": True}, "acquisitions": acquisitions,
             "families": families, "aggregate": aggregate, "stored_aggregate": {**aggregate, "generated_at": "2026-10-22T23:58:59Z"},
             "aggregate_sha256": "f" * 64, "ledger_sha256": "1" * 64, "supervisor_log_sha256": "2" * 64,
             "lane_source_sha256": dict(v.FINAL_LANE_SOURCES), "completion_note": "lane_resume deterministic command exit 0 at 2026-10-22T23:59:00Z",
             "current_contract": "3" * 64, "producer_record": {"exit_code": 0, "contract": "3" * 64, "retry_contract": "3" * 64,
             "before": {"synthetic-source.py": "4" * 64}, "after": {"synthetic-source.py": "4" * 64}},
             "closeout_log": {"producer_segment_sha256": "5" * 64, "validator_segment_sha256": "6" * 64,
             "validator_summary": {"decision": "GO", "passed": True, "clicked": True, "gap_count": 0, "gap_counts": {},
                                   "repair_tasks": [], "observed_invocation_count": 0, "executed_tool_count": 0}}, **authority()}
    return admitted, complete, current, proof


class CanonicalAuthorityTests(unittest.TestCase):
    def test_unpinned_preflight_refuses_before_files_children_live_or_admission(self):
        with mock.patch.object(v, "REVIEWED_PREFLIGHT_SHA256", None), mock.patch.object(v.subprocess, "run") as child, mock.patch.object(v, "live_evidence") as live, mock.patch.object(v, "verify_admission") as admission:
            for required in (True, False):
                with self.subTest(required=required), self.assertRaisesRegex(ValueError, "not pinned"):
                    v.verify_ready_proof(require_admission=required)
            child.assert_not_called(); live.assert_not_called(); admission.assert_not_called()

    def test_authority_flags_always_fail_closed(self):
        for field in authority():
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.no_authority({**authority(), field: True})

    def test_tap_requires_actual_all87_outcomes_and_no_skips(self):
        def valid(count):
            return "\n".join([*[f"ok {i} - behavior" for i in range(1, count + 1)], f"1..{count}", f"# tests {count}", f"# pass {count}", "# fail 0", "# skipped 0", "# cancelled 0", "# todo 0"])
        for count in (43, 44):
            text = valid(count); v.tap(text, count)
            for corrupt in (text.replace("# skipped 0", "# skipped 1"), text.replace("ok 1 -", "not ok 1 -"), text + f"\n# pass {count}", text.replace(f"1..{count}", "1..1")):
                with self.subTest(count=count, corrupt=corrupt[-50:]), self.assertRaises(ValueError):
                    v.tap(corrupt, count)


class PublicInputTests(unittest.TestCase):
    def setUp(self):
        self.ids, self.raw, self.provenance, self.descriptor = public_fixture()
        self.patches = [mock.patch.object(v, "RAW_SHA256", H(self.raw)), mock.patch.object(v, "PROVENANCE_SHA256", H(self.provenance)),
                        mock.patch.object(v, "MODEL_IDS_SHA256", H(v.compact(self.ids))), mock.patch.object(v, "DESCRIPTOR", self.descriptor)]
        for patch in self.patches:
            patch.start(); self.addCleanup(patch.stop)

    def test_both_actual_bytes_provenance_and_complete_ids_are_required(self):
        self.assertEqual(v.verify_public_input(self.raw, self.provenance, self.descriptor), self.ids)
        self.assertEqual(len(self.raw), 787610)
        for raw, provenance in ((self.raw[:-1] + b"!", self.provenance), (self.raw, self.provenance + b" ")):
            with self.subTest(kind=len(provenance)), self.assertRaises(ValueError):
                v.verify_public_input(raw, provenance, self.descriptor)

    def test_same_count_changed_id_cannot_hide_behind468(self):
        changed = self.raw.replace(b"example/model-000", b"example/other-000", 1)
        with self.assertRaisesRegex(ValueError, "raw public"):
            v.verify_public_input(changed, self.provenance, self.descriptor)

    def test_rehashed_provenance_still_cannot_claim_execution_or_wrong_source(self):
        original = json.loads(self.provenance)
        for field, value in (("provider_execution", True), ("http_status", 201), ("final_url", "https://unreviewed.invalid"), ("reconstructed", True), ("completion_authority", True), ("observed_at", "2026-10-21T00:00:00+00:00")):
            content = v.compact({**original, field: value}); descriptor = {**self.descriptor, "provenance_sha256": H(content)}
            with self.subTest(field=field), mock.patch.object(v, "PROVENANCE_SHA256", H(content)), mock.patch.object(v, "DESCRIPTOR", descriptor), self.assertRaises(ValueError):
                v.verify_public_input(self.raw, content, descriptor)


class BrowserProofTests(unittest.TestCase):
    def setUp(self):
        PublicInputTests.setUp(self)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.report = browser_fixture(self.directory, self.ids, self.raw, self.provenance)

    def verify(self, report=None):
        return v.verify_report(self.report if report is None else report, self.directory, self.ids)

    def test_actual_full_profile_semantics_parse_but_never_grant_completion(self):
        self.assertEqual(self.verify()["actual_actions"], 20)
        self.assertEqual(len(self.report["screenshot_sha256"]), 40)

    def test_candidate_unverified_sources_or_missing_guard_are_never_canonical(self):
        for field, value in (("candidate_module_override", True), ("guard_coverage", False), ("guard_source_sha256", "0" * 64), ("flag", "0"), ("canonical_source_sha256_after", "0" * 64), ("network_observer_errors", ["response body unavailable"]), ("posts_attempted", ["provider"]), ("posts_blocked", ["provider"]), ("external_catalog_gets", ["live catalog"]), ("page_errors", ["failure"])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify({**self.report, field: value})

    def test_all_states_need_exact_model_set_mode_and_metadata(self):
        mutations = [lambda s: s.update(mode="live"), lambda s: s["metadata"].update(verified=False), lambda s: s["metadata"].update(cache_ttl_ms=600000),
                     lambda s: s["metadata"].update(input_sha256="0" * 64), lambda s: s["metadata"].update(stale=True), lambda s: s["model_ids"].__setitem__(0, "example/same-count-wrong"), lambda s: s.update(guard_checked_launches=0)]
        for mutate in mutations:
            changed = copy.deepcopy(self.report); mutate(changed["profiles"][1]["cases"][8]["after"])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.verify(changed)

    def test_every_model_action_and_all1881_controls_remain_unique(self):
        for mutation in ("missing", "duplicate", "unmatched"):
            changed = copy.deepcopy(self.report); profile = changed["profiles"][0]
            if mutation == "missing": profile["original_controls"].pop()
            elif mutation == "duplicate": profile["original_controls"][-1] = profile["original_controls"][0]
            else: profile["original_controls"][0]["selector"] = "#unrelated"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify(changed)

    def test_trusted_action_and_all_original_four_writes_are_required(self):
        for mutate in (lambda c: c["trusted_events"][0].update(trusted=False), lambda c: c["trusted_events"][0].update(action="try"), lambda c: c["after"]["writes"].pop(), lambda c: c["after"]["selected_copies"][0].update(pressed="false")):
            changed = copy.deepcopy(self.report); mutate(changed["profiles"][0]["cases"][3])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.verify(changed)

    def test_reopen_and_refresh_cannot_switch_or_refetch_catalog(self):
        for mutation in ("reopen", "refresh", "fake-ui", "guard"):
            changed = copy.deepcopy(self.report); profile = changed["profiles"][0]
            if mutation == "reopen": profile["final_reopen"]["default_model"] = v.NEIGHBOR_MODEL
            elif mutation == "refresh": profile["programmatic_refresh"]["input_response_count_after"] = 4
            elif mutation == "fake-ui": profile["programmatic_refresh"]["ui_control"] = True
            else: profile["actual_guard_preflight"]["checked_launches"] = 0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify(changed)

    def test_real_asset_response_and_compiled_module_bytes_are_bound(self):
        for field in ("input_responses", "module_responses"):
            row = self.report[field][0]; path = self.directory / row["file"]; original = path.read_bytes()
            path.write_bytes(original + b"tamper")
            with self.subTest(field=field), self.assertRaises(ValueError): self.verify()
            path.write_bytes(original)
        # Service-worker delivery is an observation, not a waiver of actual
        # transformed bytes. A true value is valid when those same bytes match.
        self.report["module_responses"][0]["from_service_worker"] = True
        self.verify()
        for field, value in (("candidate_module_override", True), ("from_service_worker", None), ("actual_vite_snapshot_env", False)):
            changed = copy.deepcopy(self.report); changed["module_responses"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.verify(changed)

    def test_png_tamper_missing_png_and_unsafe_asset_path_reject(self):
        path = self.directory / "http-0-before.png"; path.write_bytes(b"not a PNG")
        with self.assertRaises(ValueError): self.verify()
        path.write_bytes(IMAGE)
        changed = copy.deepcopy(self.report); changed["input_responses"][0]["file"] = "../escaped.json"
        with self.assertRaises(ValueError): self.verify(changed)

    def test_live_or_unfenced_owned_process_cannot_claim_cleanup(self):
        for mutate in (lambda r: r.update(owned_resources_closed=False), lambda r: r["resources"].update(chrome_pid_absent=False), lambda r: r["tracked_processes"][0].update(same_identity_alive=True), lambda r: r["tracked_processes"][0].update(start_tick="")):
            changed = copy.deepcopy(self.report); mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.verify(changed)


class PreservationTests(unittest.TestCase):
    def test_exact_ten_cells1714_rows_with_live_source_currentness(self):
        record, live, baseline = preservation_fixture()
        self.assertEqual(v.verify_preservation(record, live, baseline)["unaffected_rows_preserved"], 1714)

    def test_changed_run_report_rows_fingerprint_or_incomplete_capture_reject(self):
        for key, value in (("run_id", "changed"), ("report_sha256", "c" * 64), ("row_count", 1), ("input_fingerprint", "d" * 64), ("capture_complete", False)):
            record, live, baseline = preservation_fixture(); cell = sorted(v.UNAFFECTED)[0]
            live["acquisitions"][cell][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): v.verify_preservation(record, live, baseline)

    def test_other_scope_stale_inventory_or_manufactured_go_reject(self):
        for mutation in ("local", "stale", "authority"):
            record, live, baseline = preservation_fixture()
            if mutation == "local": record["cells"]["vdg-local/http"] = copy.deepcopy(next(iter(record["cells"].values())))
            elif mutation == "stale": live["inventory"]["current"] = False
            else: record["gui_acceptance"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): v.verify_preservation(record, live, baseline)


class TransitionTests(unittest.TestCase):
    def test_only64_to65_exact12_prefixes_and_additive_dependency_are_valid(self):
        before, after, fields = transition_fixture()
        result = v.verify_transition(before, after, expected_repair_fields=fields)
        self.assertEqual(result["guarded_command_fields"], 12)
        self.assertEqual(result["after_tasks"], 65)
        self.assertFalse(result["completion_authority"])

    def test_original_status_bounds_budget_acceptance_prose_are_immutable(self):
        before, after, _ = transition_fixture()
        for old, new in (("- Attempt count: 7", "- Attempt count: 0"), ("- Refusal count: 3", "- Refusal count: 0"),
                         ("- Implementation timeout seconds: 46800", "- Implementation timeout seconds: 50400"),
                         ("- Acceptance: all original obligations retained", "- Acceptance: weakened"),
                         ("- Status: pending", "- Status: completed"), ("Synthetic unit task", "altered prose")):
            with self.subTest(old=old), self.assertRaises(ValueError):
                v.verify_transition(before, after.replace(old, new, 1))

    def test_prefix_cannot_waive_change_or_duplicate_original_child_argv(self):
        before, after, _ = transition_fixture()
        original = v.COMMANDS["VDG-039-R01"][0]
        for replacement in (original.replace("22200", "46800"), original + " --fresh", "node arbitrary-script.mjs", v.WRAPPER_PREFIX + original):
            changed = after.replace(v.WRAPPER_PREFIX + original, v.WRAPPER_PREFIX + replacement, 1)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError): v.verify_transition(before, changed)

    def test_missing_cycles_completed_repairs_and_extra_fields_fail_closed(self):
        before, after, _ = transition_fixture()
        old = "- Depends on: VDG-013-R22, " + v.REPAIR
        variants = [after.replace(old, "- Depends on: " + v.REPAIR, 1), after.replace(old, old + ", VDG-039-R01", 1),
                    after.replace("## " + v.REPAIR + " Synthetic unit task\n\n- Status: pending", "## " + v.REPAIR + " Synthetic unit task\n\n- Status: completed"),
                    after + "\n- Completion: manually marked\n", after + "\n- Extra provider budget: 9\n"]
        for changed in variants:
            with self.subTest(tail=changed[-60:]), self.assertRaises(ValueError): v.verify_transition(before, changed)

    def test_exact_repair_template_mismatch_is_rejected(self):
        before, after, fields = transition_fixture()
        with self.assertRaisesRegex(ValueError, "template"):
            v.verify_transition(before, after, expected_repair_fields={**fields, "acceptance": "different"})

    def test_future_natural_completion_does_not_freeze_archived_admission(self):
        _, after, _ = transition_fixture()
        current = after.replace("## " + v.REPAIR + " Synthetic unit task\n\n- Status: pending", "## " + v.REPAIR + " Synthetic unit task\n\n- Status: completed\n- Completion: normal lane validation exit0")
        v.verify_current_contract(current, after)
        with self.assertRaises(ValueError): v.verify_current_contract(current.replace("- Attempt count: 7", "- Attempt count: 0", 1), after)
        with self.assertRaises(ValueError): v.verify_current_contract(current.replace("- Status: completed", "- Status: pending", 1), after)

    def test_completed_historical_completion_and_evidence_are_immutable(self):
        _, after, _ = transition_fixture()
        for original, replacement in (("- Completion: original immutable natural completion", "- Completion: fabricated rewritten history"),
                                      ("- Completion: original immutable natural completion", "- Completion: original immutable natural completion\n- Evidence: invented new authority"),
                                      ("- Status: completed", "- Status: pending")):
            changed = after.replace(original, replacement, 1)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, "Historical completed"):
                v.verify_current_contract(changed, after)


class ArchivedFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.archive = self.root / "archive"; self.failure = self.archive / "actual-failure"
        self.failure.mkdir(parents=True)
        self.pins = {}
        for name, content in (("supervisor-log-at-stop.log", b"Synthetic fixture: Test timeout of 21600000ms exceeded.\n"), ("matrix-before.json", b'{"synthetic":true}')):
            (self.failure / name).write_bytes(content); self.pins[name] = H(content)
        for transport, count, images in (("http", 2073, 4124), ("libp2p", 388, 764)):
            rows = [{"failure_reasons": []} for _ in range(count)]
            if transport == "libp2p":
                for index, action in zip(range(83, 87), ("favorite", "info", "try", "default")):
                    rows[index] = {"app_id": "openrouter", "launch_id": "openrouter", "selector": v.selector(v.OLD_MODEL, action),
                                   "clicked": False, "visibility": "not-visible", "failure_reasons": ["not-visible"], "pageerrors": [],
                                   "mcp_call_count": 0, "incomplete_mcp_call_count": 0}
            payload = {"rows": rows, "pageerrors": [], "observations": [], "image_hashes": {
                f"swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vdg/live-clicks/synthetic-{transport}/{i}.png": H(IMAGE) for i in range(images)}}
            record = {"schema": "swissknife.vdg-capture-checkpoint.v1", "target": "local", "transport": transport,
                      "input_fingerprint": "a" * 64, "capture_complete": False, "work_complete": False, "completion_authority": False,
                      "payload": payload, "payload_sha256": H(v.compact(payload))}
            name = transport + "-checkpoint.json"; content = v.compact(record)
            (self.failure / name).write_bytes(content); self.pins[name] = H(content)
        patch = mock.patch.object(v, "FAILURE_PINS", self.pins); patch.start(); self.addCleanup(patch.stop)

    def changed_checkpoint(self, transport, mutate):
        name = transport + "-checkpoint.json"; path = self.failure / name
        record = json.loads(path.read_bytes()); mutate(record)
        record["payload_sha256"] = H(v.compact(record["payload"]))
        content = v.compact(record); path.write_bytes(content); self.pins[name] = H(content)

    def test_partial_deadline_and_all_declared_pngs_remain_obligations(self):
        # Only PNG I/O is stubbed in this semantic fixture; production performs
        # the actual SHA/header check on every declared historical image.
        with mock.patch.object(v, "png") as image:
            summary = v.verify_failure(self.archive, self.root)
            self.assertEqual(image.call_count, 4124 + 764)
            self.assertFalse(summary["original_partial_captures"]["http"]["capture_complete"])
            self.assertEqual(summary["original_partial_captures"]["libp2p"]["row_failures"], 4)
            self.assertTrue(summary["precise_upstream_rename_not_established"])

    def test_actual_png_verification_error_propagates(self):
        with mock.patch.object(v, "png", side_effect=ValueError("historical PNG hash changed")), self.assertRaisesRegex(ValueError, "PNG"):
            v.verify_failure(self.archive, self.root)

    def test_rehashed_checkpoint_cannot_be_relabelled_complete_or_failure_cleared(self):
        self.changed_checkpoint("http", lambda d: d.update(capture_complete=True))
        with mock.patch.object(v, "png"), self.assertRaises(ValueError): v.verify_failure(self.archive, self.root)

    def test_missing_id_failure_identity_and_six_hour_deadline_stay_explicit(self):
        self.changed_checkpoint("libp2p", lambda d: d["payload"]["rows"][83].update(selector=v.selector(v.TARGET_MODEL, "favorite")))
        with mock.patch.object(v, "png"), self.assertRaises(ValueError): v.verify_failure(self.archive, self.root)
        path = self.failure / "supervisor-log-at-stop.log"; path.write_bytes(b"deadline removed"); self.pins[path.name] = H(path.read_bytes())
        with mock.patch.object(v, "png"), self.assertRaisesRegex(ValueError, "six-hour"): v.verify_failure(self.archive, self.root)


class AdmissionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.archive = self.root / "archive"; self.archive.mkdir()
        self.before, self.after, fields = transition_fixture()
        for name, text in (("completion-board-before-catalog-input.todo.snapshot", self.before), ("completion-board-after-catalog-input.todo.snapshot", self.after)):
            (self.root / name).write_text(text)
        self.board = self.root / "board.todo"; self.board.write_text(self.after)
        identity = {"lane_pid": 1960744, "lock_inode": 10, "lock_device": 51, "hold_sha256": "a" * 64}
        baseline = {"taskboard_sha256": H(self.before.encode()), "lifecycle_fence": identity}
        content = v.compact(baseline); (self.archive / "unaffected-ten-before.json").write_bytes(content)
        for patch in (mock.patch.object(v, "BASELINE_SHA256", H(content)), mock.patch.object(v, "BOARD", self.board)):
            patch.start(); self.addCleanup(patch.stop)
        self.receipt = {"schema": "swissknife.vdg-openrouter-catalog-admission.v1", "apply_requested": True,
                        "tasks_before": 64, "tasks_after": 65, "admission": {"admitted": True},
                        "board_before_sha256": H(self.before.encode()), "board_after_sha256": H(self.after.encode()),
                        "before_snapshot": "completion-board-before-catalog-input.todo.snapshot",
                        "after_snapshot": "completion-board-after-catalog-input.todo.snapshot", "repair_fields": fields,
                        "transition": v.verify_transition(self.before, self.after), "identity": identity,
                        "statuses_history_and_bounds_preserved": True, "guarded_command_fields": 12,
                        "exact_original_child_argv_preserved": True, **authority()}
        self.save()

    def save(self):
        (self.root / "catalog-input-admission.json").write_bytes(v.compact(self.receipt))

    def test_actual_snapshot_transition_can_survive_natural_repair_completion(self):
        self.board.write_text(self.after.replace("## " + v.REPAIR + " Synthetic unit task\n\n- Status: pending", "## " + v.REPAIR + " Synthetic unit task\n\n- Status: completed\n- Completion: naturally validated"))
        self.assertEqual(v.verify_admission(self.archive, self.root)["guarded_command_fields"], 12)

    def test_preview_unfenced_or_wrong_argv_receipt_cannot_be_admission(self):
        original = copy.deepcopy(self.receipt)
        for field, value in (("apply_requested", False), ("guarded_command_fields", 10), ("exact_original_child_argv_preserved", False), ("completion_authority", True), ("before_snapshot", "../other.todo"), ("identity", {**original["identity"], "lane_pid": 42})):
            self.receipt = {**original, field: value}; self.save()
            with self.subTest(field=field), self.assertRaises(ValueError): v.verify_admission(self.archive, self.root)

    def test_changed_immutable_snapshots_and_live_contract_tampering_reject(self):
        path = self.root / "completion-board-before-catalog-input.todo.snapshot"; path.write_text(self.before + "tamper")
        with self.assertRaises(ValueError): v.verify_admission(self.archive, self.root)
        path.write_text(self.before)
        self.board.write_text(self.after.replace("--timeout-seconds 22200", "--timeout-seconds 50400", 1))
        with self.assertRaises(ValueError): v.verify_admission(self.archive, self.root)


class FinalProgramDecisionTests(unittest.TestCase):
    def test_only_exact_final_line_after65_and_strict_actual_proof_is_allowed(self):
        admitted, complete, current, proof = final_go_fixture()
        v.verify_current_contract(complete, admitted)
        v.verify_current_contract(current, admitted, final_go_evidence=proof)
        _, tasks = v.parse_board(current)
        self.assertTrue(v.verify_final_go_evidence(proof, tasks["VDG-060"]["fields"])["natural_060_completion_verified"])

    def test_65_completed_alone_or_early_go_cannot_be_authority(self):
        admitted, _, current, proof = final_go_fixture()
        with self.assertRaisesRegex(ValueError, "evidence"):
            v.verify_current_contract(current, admitted)
        early = current.replace("- Status: completed", "- Status: pending", 1)
        with self.assertRaises(ValueError): v.verify_current_contract(early, admitted, final_go_evidence=proof)
        with mock.patch.object(v.subprocess, "run") as child, self.assertRaisesRegex(ValueError, "all65"):
            v.live_final_go_evidence(early)
        child.assert_not_called()

    def test_unrelated_header_or_task_history_changes_remain_rejected(self):
        admitted, _, current, proof = final_go_fixture()
        for changed in (current.replace(v.PROGRAM_GO_LINE, "Program decision: **GO** because the operator said so."),
                        current.replace("no execution authority", "changed scope"),
                        current.replace("- Completion: original immutable natural completion", "- Completion: rewritten old history", 1)):
            with self.subTest(change=changed[:100]), self.assertRaises(ValueError):
                v.verify_current_contract(changed, admitted, final_go_evidence=proof)

    def test_task_titles_and_unfielded_prose_are_immutable_in_both_banner_states(self):
        admitted, complete, current, proof = final_go_fixture()
        for board in (complete, current):
            for original, changed in (("## VDG-013-R22 Synthetic unit task", "## VDG-013-R22 rewritten historical title"),
                                      ("## VDG-039-R01 Synthetic unit task", "## VDG-039-R01 rewritten pending title"),
                                      ("## VDG-039-R01 Synthetic unit task\n", "## VDG-039-R01 Synthetic unit task\nunauthorized free prose\n")):
                with self.subTest(banner=board.splitlines()[1], changed=changed), self.assertRaises(ValueError):
                    v.verify_current_contract(board.replace(original, changed, 1), admitted, final_go_evidence=proof)

    def test_missing_current_capture_or_strict_family_gap_prevents_final_go(self):
        admitted, _, current, proof = final_go_fixture()
        for mutation in ("capture", "stale", "family", "family-stored", "aggregate", "aggregate-stored"):
            changed = copy.deepcopy(proof)
            if mutation == "capture": changed["acquisitions"].pop("vdg-local/libp2p")
            elif mutation == "stale": changed["inventory"]["current"] = False
            elif mutation == "family": changed["families"]["vdg-local"]["fresh"]["gap_count"] = 1
            elif mutation == "family-stored": changed["families"]["vdg-local"]["stored"]["input_fingerprint"] = "0" * 64
            elif mutation == "aggregate": changed["aggregate"]["decision"] = "no_go"
            else: changed["stored_aggregate"]["families"][0]["input_fingerprint"] = "0" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                v.verify_current_contract(current, admitted, final_go_evidence=changed)

    def test_no_invented_validator_exit_record_or_stale_producer_is_accepted(self):
        admitted, _, current, proof = final_go_fixture()
        for mutation in ("producer", "contract", "completion", "validator", "source", "hook", "manifest", "recovery-script", "hash"):
            changed = copy.deepcopy(proof)
            if mutation == "producer": changed["producer_record"]["exit_code"] = 75
            elif mutation == "contract": changed["producer_record"]["contract"] = "0" * 64
            elif mutation == "completion": changed["completion_note"] = "operator manually completed"
            elif mutation == "validator": changed["closeout_log"]["validator_summary"]["decision"] = "no_go"
            elif mutation == "source": changed["lane_source_sha256"][v.LANE_SOURCE] = "0" * 64
            elif mutation == "hook": changed["lane_source_sha256"][v.RECOVERY_MODULE] = "0" * 64
            elif mutation == "manifest": changed["lane_source_sha256"][v.CONTROL_MANIFEST] = "0" * 64
            elif mutation == "recovery-script": changed["lane_source_sha256"][v.RECOVERY_SCRIPT] = "0" * 64
            else: changed["ledger_sha256"] = None
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                v.verify_current_contract(current, admitted, final_go_evidence=changed)
        # The actual ledger has no separate successful-validation exit field.
        self.assertNotIn("validation_exit_code", proof["producer_record"])

    def test_latest_real_ordered_log_outputs_are_required(self):
        admitted, _, current, proof = final_go_fixture()
        _, tasks = v.parse_board(current); fields = tasks["VDG-060"]["fields"]
        root = Path("/synthetic-repo")
        producer = "$ " + fields["deterministic_command"] + "  # cwd=/synthetic-repo\n"
        validator = "$ " + fields["validation"] + "  # cwd=/synthetic-repo\n"
        good = producer + "closeout allowed\n" + validator + json.dumps(proof["closeout_log"]["validator_summary"]) + "\n"
        self.assertEqual(v.parse_closeout_log(good, fields, root=root)["validator_summary"]["decision"], "GO")
        for wrong in (good + producer + "closeout withheld\n", validator + "{}\n" + producer + "closeout allowed\n",
                      producer + "closeout allowed\n$ node another-command.mjs\n" + validator + "{}\n"):
            with self.subTest(log=wrong[-100:]), self.assertRaises(ValueError): v.parse_closeout_log(wrong, fields, root=root)

    def test_last_validator_summary_cannot_reuse_an_earlier_go(self):
        _, _, current, proof = final_go_fixture(); _, tasks = v.parse_board(current); fields = tasks["VDG-060"]["fields"]
        text = "$ " + fields["deterministic_command"] + "  # cwd=/synthetic\ncloseout allowed\n$ " + fields["validation"] + "  # cwd=/synthetic\n"
        text += json.dumps(proof["closeout_log"]["validator_summary"]) + '\n{"decision":"no_go","passed":false}\n'
        proof["closeout_log"] = v.parse_closeout_log(text, fields, root=Path("/synthetic"))
        with self.assertRaisesRegex(ValueError, "validator GO"):
            v.verify_final_go_evidence(proof, fields)

    def test_contract_reader_loads_only_pure_functions_without_package_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); lane = root / v.LANE_SOURCE; gate = root / v.GATE_SOURCE
            lane.parent.mkdir(parents=True)
            lane.write_text('raise RuntimeError("package initialization must not execute")\n'
                            'def _file_digest(path):\n return hashlib.sha256(path.read_bytes()).hexdigest()\n'
                            'def _declared_evidence(fields, *, repo_root, excluded):\n return {}\n'
                            'def _runtime_contract_code(code):\n return code\n'
                            'def _command_contract(fields, command, validation, *, repo_root):\n return _file_digest(repo_root / "source.py")\n')
            gate.write_text('raise RuntimeError("gate initialization must not execute")\n_SOURCE_SUFFIXES={".py"}\ndef _is_source_path(path):\n return path.suffix in _SOURCE_SUFFIXES\n')
            (root / "source.py").write_text("actual synthetic source bytes\n")
            fields = {"deterministic_command": v.WRAPPER_PREFIX + v.COMMANDS["VDG-060"][0], "validation": v.WRAPPER_PREFIX + v.COMMANDS["VDG-060"][1]}
            self.assertEqual(v.current_closeout_contract(fields, root=root), H((root / "source.py").read_bytes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
