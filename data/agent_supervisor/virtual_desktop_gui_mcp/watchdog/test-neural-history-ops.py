"""Pure parser/admission tamper cases; synthetic fixtures grant no GUI evidence."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
verifier = load("neural_history_verifier_tests", "verify-neural-history-repair.py")
admission = load("neural_history_admission_tests", "admit-neural-history-repair.py")
REAL_ROOT = Path("/home/barberb/lift_coding")
IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=")


def browser_fixture(directory):
    archive = directory / "archive"; images = archive / "canonical"; images.mkdir(parents=True)
    report = {"schema": "swissknife.vdg-neural-photoshop-history-smoke.v1", "source_sha256": verifier.SOURCES[verifier.APP],
      "source_path": str(directory / verifier.APP), "project_root": str(directory / "swissknife"),
      "candidate_module_override": False, "route_interception": False, "canonical_source_sha256": verifier.SOURCES[verifier.APP],
      "passed": True, "viewport": {"width": 720, "height": 540}, "results": [],
      "gui_acceptance": False, "work_complete": False, "completion_authority": False, "owned_resources_closed": True,
      "owned_resources": {"server_pid": 1001, "browser_pid": 1002, "server_alive_after_cleanup": False, "browser_alive_after_cleanup": False},
      "screenshot_sha256": {}}
    for transport_index, transport in enumerate(verifier.TRANSPORTS):
        profile = {"transport_profile": transport, "source_transport": transport, "generation_transport": transport,
          "actual_post_count": 3, "trusted_confirmations": 3, "source_cid_verified": True, "generation_preview_only": True,
          "local_panel_collapse_reopen": True, "local_style_dismissal": ["Escape", "backdrop", "Cancel"],
          "pending_style_close_reopen": True, "later_generic_confirmation": True, "history_states": [], "page_errors": [], "observations": []}
        for label, expanded in zip(("initial", "bound", "expanded", "collapsed", "reopened"), (False, False, True, False, False)):
            profile["history_states"].append({"label": label, "selector": verifier.SELECTOR, "expanded": str(expanded).lower(),
              "accessible_name": f"{'Collapse' if expanded else 'Expand'} history panel", "content_visible": expanded, "actual_control_count": 1})
        for index, (tool, owner, binding) in enumerate(zip(("ipfs_cat", "run_inference_job", "ipfs_cat"),
              ("ipfs_kit_py", "ipfs_accelerate_py", "ipfs_kit_py"), ("retrieve_content", "run_inference_job", "retrieve_content"))):
            key = transport_index * 3 + index
            profile["observations"].append({"method": "POST", "route": "/mcp/tools/call", "app_id": "neural-photoshop",
              "binding_id": f"neural-photoshop.{owner}.{binding}", "owner": owner, "tool_id": tool, "transport": transport,
              "correlation_id": f"desktop:neural-photoshop.synthetic-unit-{key}", "policy_outcome": "require_confirmation",
              "dry_run": True, "outcome": "executed", "receipt_id": "b" + chr(97 + key) * 58, "event_dag_cid": "b" + chr(104 + key) * 58})
        report["results"].append(profile)
        for name in ("history-initial", "history-bound", "history-expanded", "history-collapsed", "history-reopened", "style-before-close", "gateway-confirmation", "layout"):
            path = images / f"{transport}-{name}.png"; path.write_bytes(IMAGE)
            report["screenshot_sha256"][path.name] = verifier.sha(path)
    return report, archive


class CanonicalReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="r20-ops-unit-", dir="/storage/hf_cache/barberb-vdg-evidence-20261022/r20-neural-history-source")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.report, self.archive = browser_fixture(self.root)

    def test_valid_synthetic_parser_fixture_has_six_distinct_observations(self):
        self.assertEqual(len(verifier.verify_report(self.report, self.archive, self.root)), 6)

    def test_browser_semantic_tampering_is_rejected(self):
        changes = {
          "candidate": lambda r: r.update(candidate_module_override=True),
          "route_mock": lambda r: r.update(route_interception=True),
          "source": lambda r: r.update(source_sha256="0" * 64),
          "canonical_source": lambda r: r.update(canonical_source_sha256="0" * 64),
          "source_path": lambda r: r.update(source_path="/tmp/candidate.js"),
          "authority": lambda r: r.update(gui_acceptance=True),
          "resource": lambda r: r["owned_resources"].update(browser_alive_after_cleanup=True),
          "boolean_pid": lambda r: r["owned_resources"].update(server_pid=True),
          "missing_profile": lambda r: r["results"].pop(),
          "wrong_profile": lambda r: r["results"][1].update(transport_profile="http"),
          "transport": lambda r: r["results"][1].update(source_transport="unsupported"),
          "unconfirmed": lambda r: r["results"][0].update(trusted_confirmations=2),
          "posts": lambda r: r["results"][0].update(actual_post_count=2),
          "page_error": lambda r: r["results"][0].update(page_errors=["actual error"]),
          "no_preview": lambda r: r["results"][0].update(generation_preview_only=False),
          "no_reopen": lambda r: r["results"][0].update(pending_style_close_reopen=False),
          "history_missing": lambda r: r["results"][0]["history_states"].pop(),
          "history_alias": lambda r: r["results"][0]["history_states"][0].update(selector='button[aria-label="Expand history panel"]'),
          "history_state": lambda r: r["results"][0]["history_states"][2].update(expanded="false"),
          "history_action": lambda r: r["results"][0]["history_states"][0].update(accessible_name="Collapse history panel"),
          "history_visibility": lambda r: r["results"][0]["history_states"][2].update(content_visible=False),
          "history_duplicate": lambda r: r["results"][0]["history_states"][0].update(actual_control_count=2),
          "wrong_tool": lambda r: r["results"][0]["observations"][0].update(tool_id="ipfs_ls"),
          "wrong_binding": lambda r: r["results"][0]["observations"][1].update(binding_id="other"),
          "auto_consent": lambda r: r["results"][0]["observations"][0].update(policy_outcome="allow"),
          "not_preview": lambda r: r["results"][0]["observations"][1].update(dry_run=False),
          "missing_receipt": lambda r: r["results"][0]["observations"][0].update(receipt_id=""),
          "reused_receipt": lambda r: r["results"][0]["observations"][2].update(receipt_id=r["results"][0]["observations"][0]["receipt_id"]),
          "reused_correlation": lambda r: r["results"][0]["observations"][2].update(correlation_id=r["results"][0]["observations"][0]["correlation_id"]),
          "missing_image": lambda r: r["screenshot_sha256"].pop("http-history-expanded.png"),
          "image_path_escape": lambda r: r["screenshot_sha256"].update({"../outside.png": "0" * 64}),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                report = copy.deepcopy(self.report); change(report)
                with self.assertRaises(ValueError): verifier.verify_report(report, self.archive, self.root)

    def test_actual_image_byte_or_symlink_tampering_is_rejected(self):
        image = self.archive / "canonical/http-history-expanded.png"
        original = image.read_bytes(); image.write_bytes(b"bad")
        with self.assertRaises(ValueError): verifier.verify_report(self.report, self.archive, self.root)
        image.unlink(); target = self.root / "outside.png"; target.write_bytes(original); image.symlink_to(target)
        with self.assertRaises(ValueError): verifier.verify_report(self.report, self.archive, self.root)

    def test_unpinned_preflight_cannot_run_units_or_pass(self):
        previous = verifier.REVIEWED_PREFLIGHT_SHA256
        try:
            verifier.REVIEWED_PREFLIGHT_SHA256 = None
            with self.assertRaisesRegex(ValueError, "not pinned"):
                verifier.verify_ready_proof()
        finally:
            verifier.REVIEWED_PREFLIGHT_SHA256 = previous



class PreservationAndAdmissionTests(unittest.TestCase):
    def test_node_entrypoint_parser_rejects_argument_data_and_keeps_preloads(self):
        cases = [
            (["node", "run-vdg-family.mjs", "--capture-only"], "run-vdg-family.mjs"),
            (["node", "--import", "tsx", "run-vdg-family.mjs"], "run-vdg-family.mjs"),
            (["node", "--require=preload", "run-vdg-family.mjs"], "run-vdg-family.mjs"),
            (["node", "--", "run-vdg-family.mjs"], "run-vdg-family.mjs"),
            (["node", "other.js", "--evidence-path", "run-vdg-family.mjs"], "other.js"),
            (["node", "--eval", "console.log(1)", "run-vdg-family.mjs"], None),
            (["python", "--evidence-path", "run-vdg-family.mjs"], None),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv): self.assertEqual(admission.node_script(argv), expected)

    def test_exact_eight_cell_reuse_and_tampering(self):
        cells = {cell: {"input_fingerprint": "a" * 64, "run_id": cell.replace("/", "-") + "-unit", "report_sha256": "b" * 64} for cell in verifier.COMPLETED_CELLS}
        live = {"fingerprints": {cell: "a" * 64 for cell in verifier.UNAFFECTED}, "acquisitions": cells}
        record = {"schema": "swissknife.vdg-neural-history-preservation.v2", "before_app_sha256": verifier.OLD_APP_SHA256,
          "after_app_sha256": verifier.SOURCES[verifier.APP], "gui_acceptance": False, "work_complete": False, "completion_authority": False,
          "cells": {cell: {"before_input_fingerprint": "a" * 64, "after_input_fingerprint": "a" * 64,
              "run_id": cells.get(cell, {}).get("run_id"), "report_sha256": cells.get(cell, {}).get("report_sha256")} for cell in verifier.UNAFFECTED}}
        verifier.verify_preservation(record, live)
        for field in ["before_input_fingerprint", "after_input_fingerprint", "run_id", "report_sha256"]:
            changed = copy.deepcopy(record); changed["cells"][next(iter(cells))][field] = "tampered"
            with self.subTest(field=field), self.assertRaises(ValueError): verifier.verify_preservation(changed, live)
        changed = copy.deepcopy(record); changed["cells"].pop(next(iter(cells)))
        with self.assertRaises(ValueError): verifier.verify_preservation(changed, live)
        changed = copy.deepcopy(record); changed["cells"]["vdg-local/libp2p"] = copy.deepcopy(next(iter(record["cells"].values())))
        with self.assertRaises(ValueError): verifier.verify_preservation(changed, live)
        changed = copy.deepcopy(record); changed["local_libp2p_checkpoint"] = {"row_count": 1}
        with self.assertRaises(ValueError): verifier.verify_preservation(changed, live)

    def test_actual_local_repair_excludes_all_four_changed_cells(self):
        expected = {f"vdg-{family}/{transport}" for family in ("storage", "datasets", "network", "control")
                    for transport in ("http", "libp2p")}
        self.assertEqual(verifier.UNAFFECTED, expected)
        self.assertEqual(verifier.COMPLETED_CELLS, expected)
        self.assertEqual(len(expected), 8)
        self.assertTrue(all(not key.startswith(("vdg-local/", "vdg-accelerate/")) for key in expected))

    def test_actual_current_pending_batch_plan_preserves_every_status_without_mutation(self):
        board = (REAL_ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md").read_text()
        result, before, after = admission.build_admission(board, root=REAL_ROOT)
        self.assertTrue(result["admitted"])
        self.assertTrue(all(before[task]["status"] == after[task]["status"] for task in before))
        self.assertEqual(board, (REAL_ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md").read_text())

    def test_completed_batch_is_refused_without_rewriting_history(self):
        board = (REAL_ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md").read_text()
        head, tail = board.split("## VDG-039-R01 ", 1)
        block, remainder = tail.split("\n## ", 1)
        block = block.replace("- Status: pending", "- Status: completed", 1)
        fixture = head + "## VDG-039-R01 " + block + "\n## " + remainder
        with self.assertRaisesRegex(ValueError, "remain pending"):
            admission.build_admission(fixture, root=REAL_ROOT)

    def test_pending_batch_adds_only_one_task_and_original_batch_dependency(self):
        board = (REAL_ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md").read_text()
        result, before, after = admission.build_admission(board, root=REAL_ROOT)
        self.assertTrue(result["admitted"]); self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[admission.REPAIR]["implementation_timeout_seconds"], "1800")
        self.assertEqual(after[admission.REPAIR]["resource_class"], "cpu-small")
        self.assertEqual(after[admission.REPAIR]["status"], "pending")
        self.assertEqual(after[admission.REPAIR]["depends_on"], "VDG-013-R19")
        self.assertEqual(after["VDG-039-R01"]["status"], "pending")
        self.assertEqual(after["VDG-033-R03"], before["VDG-033-R03"])
        repeated, _, _ = admission.build_admission(result["todo_text"], root=REAL_ROOT)
        self.assertFalse(repeated["admitted"]); self.assertEqual(repeated["todo_text"], result["todo_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
