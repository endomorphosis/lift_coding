"""Runtime dependency binding must preserve task scope and completed history."""
import copy
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_swissknife_visual_functional_plan as plan


class SourceClosureTests(unittest.TestCase):
    def test_fresh_build_uses_the_isolated_owned_kubo_endpoints(self):
        import json
        contracts = (plan.ROOT / plan.CONTRACTS).read_bytes()
        with tempfile.TemporaryDirectory() as name:
            fresh = Path(name)
            target = fresh / plan.CONTRACTS
            target.parent.mkdir(parents=True)
            target.write_bytes(contracts)
            (fresh / "config").mkdir()
            (fresh / plan.STEM).parent.mkdir(parents=True)
            original_root = plan.ROOT
            try:
                plan.ROOT = fresh
                built = plan.build()
            finally:
                plan.ROOT = original_root
            self.assertEqual(built["apps"], 45)
            profile = json.loads((fresh / plan.PROFILE).read_text())
            self.assertEqual(profile["backendReadiness"]["kuboApi"], "http://127.0.0.1:5031")
            self.assertEqual(profile["backendReadiness"]["ipfsGateway"], "http://127.0.0.1:8092")
            self.assertEqual(profile["llm"]["model"], "grok-4.7")
            self.assertFalse(profile["llm"]["allowCrossProviderFallback"])

    def test_r12_storage_and_owned_kubo_are_readonly_inputs_only(self):
        additions = ['external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/storage_pressure.py', 'scripts/svf_backends/owned_kubo_watchdog.py', 'config/swissknife_visual_functional_ipfs_watchdog.json', 'config/systemd/swissknife-visual-functional-native-ipfs.service', 'config/systemd/swissknife-visual-functional-ipfs-watchdog.service']
        completed = {"task_id": "SVF-OLD", "execution_inputs": ["historical.py"],
                     "edit_paths": ["old.js"], "recovery_edit_paths": ["old.js"]}
        pending = {"task_id": "SVF-NEW", "execution_inputs": ["worker.py"],
                   "edit_paths": ["app.js"], "predicted_files": ["app.js"],
                   "recovery_edit_paths": ["app.js"], "semantic_failure_limit": 6,
                   "semantic_recovery_limit": 2, "acceptance": "Original actual result",
                   "execution_validation": [{"argv": ["original-validator"]}]}
        original = {"tasks": [completed, pending], "goals": [{"goal_id": "G"}]}
        before = copy.deepcopy(original)
        result = plan.bind_runtime_sources(original, [], ["SVF-OLD"])
        self.assertEqual(original, before)
        self.assertEqual(result["tasks"][0], completed)
        self.assertEqual(result["goals"], before["goals"])
        current = result["tasks"][1]
        self.assertTrue(set(additions) <= set(current["execution_inputs"]))
        for key in pending:
            if key != "execution_inputs":
                self.assertEqual(current[key], pending[key])
        for key in ("edit_paths", "predicted_files", "recovery_edit_paths"):
            self.assertTrue(set(additions).isdisjoint(current[key]))
        self.assertEqual(plan.bind_runtime_sources(result, [], ["SVF-OLD"]), result)

    def test_observation_sdk_sources_bind_only_unfinished_contracts(self):
        old = {"task_id": "SVF-OLD", "execution_inputs": ["historical.py"], "edit_paths": ["old.js"]}
        new = {"task_id": "SVF-NEW", "execution_inputs": ["worker.py"], "edit_paths": ["app.js"],
               "semantic_recovery_limit": 2, "acceptance": "Actual measurements and original validator"}
        value = plan.bind_runtime_sources({"tasks": [old, new]}, [], ["SVF-OLD"])
        self.assertEqual(value["tasks"][0], old)
        for key in ("edit_paths", "semantic_recovery_limit", "acceptance"):
            self.assertEqual(value["tasks"][1][key], new[key])
        self.assertTrue({"scripts/svf_backends/native_accelerate_observation.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/health.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/metrics.py"}
            <= set(value["tasks"][1]["execution_inputs"]))

    def test_launch_alias_is_declared_as_regular_source_without_changing_acceptance_or_history(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            alias = "swissknife/web/js/apps/launch.js"
            real = "swissknife/web/js/apps/implementation.js"
            target = root / real
            target.parent.mkdir(parents=True)
            target.write_text("export class ActualApp {}\n")
            (root / alias).symlink_to("implementation.js")
            completed = {"task_id": "SVF-OLD", "edit_paths": [alias], "context_paths": [alias]}
            pending = {"task_id": "SVF-NEW", "edit_paths": [alias, "scenario.json"],
                       "predicted_files": [alias, "scenario.json"], "recovery_edit_paths": [alias],
                       "context_paths": [alias], "execution_inputs": [alias, real],
                       "checks": [["node", "--check", alias]], "acceptance": "Actual result and visual gate",
                       "semantic_recovery_limit": 2, "execution_validation": [{"argv": ["original-validator"]}]}
            spec = {"tasks": [completed, pending], "goals": [{"goal_id": "G"}]}
            before = copy.deepcopy(spec)
            value = plan.canonicalize_app_source_paths(spec, ["SVF-OLD"], root=root)
            self.assertEqual(spec, before)
            self.assertEqual(value["tasks"][0], completed)
            current = value["tasks"][1]
            for key in ("edit_paths", "predicted_files", "recovery_edit_paths", "context_paths", "execution_inputs"):
                self.assertNotIn(alias, current[key])
                self.assertIn(real, current[key])
            self.assertEqual(current["execution_inputs"], [real])
            self.assertEqual(current["checks"], [["node", "--check", real]])
            for key in ("acceptance", "semantic_recovery_limit", "execution_validation"):
                self.assertEqual(current[key], pending[key])
            self.assertEqual(value["goals"], before["goals"])
            self.assertEqual(plan.canonicalize_app_source_paths(value, ["SVF-OLD"], root=root), value)

    def test_launch_alias_cannot_expand_app_edit_authority_outside_implementation_directory(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            alias = root / "swissknife/web/js/apps/launch.js"
            alias.parent.mkdir(parents=True)
            private = root / "unrelated.py"
            private.write_text("private = True\n")
            alias.symlink_to(private)
            with self.assertRaisesRegex(ValueError, "inside the app directory"):
                plan.canonicalize_app_source_paths({"tasks": [{"task_id": "SVF-NEW",
                    "edit_paths": [alias.relative_to(root).as_posix()]}]}, root=root)

    def test_global_stylesheets_loaded_by_the_real_desktop_are_retry_inputs(self):
        class Stylesheets(HTMLParser):
            paths = set()
            def handle_starttag(self, tag, attrs):
                row = dict(attrs)
                if tag == "link" and row.get("rel") == "stylesheet" and row.get("href", "").startswith("/css/"):
                    self.paths.add("swissknife/web" + row["href"])
        page = Stylesheets()
        page.feed((plan.ROOT / "swissknife/web/index.html").read_text())
        self.assertIn("swissknife/web/css/strudel.css", page.paths)
        self.assertEqual(page.paths - set(plan.RUNTIME_SOURCE_INPUTS), set())

    def test_shared_remediation_has_own_scope_without_reopening_completed_acceptance(self):
        completed = {"task_id": "SVF-OLD", "kind": "verify", "status": "ready",
                     "dependencies": ["SVF-122"], "edit_paths": ["app.js"],
                     "semantic_recovery_limit": 2}
        pending = {"task_id": "SVF-NEW", "kind": "verify", "dependencies": ["SVF-122"],
                   "edit_paths": ["notes.js"], "acceptance": "Real semantic result",
                   "execution_validation": [{"argv": ["original-validator"]}],
                   "semantic_recovery_limit": 2}
        spec = {"tasks": [completed, pending], "goals": [{"goal_id": "SVF-G030"}]}
        before = copy.deepcopy(spec)
        result = plan.register_shared_desktop_recovery(spec, ["SVF-OLD"])
        self.assertEqual(spec, before)
        self.assertEqual(result["goals"], before["goals"])
        by_id = {task["task_id"]: task for task in result["tasks"]}
        self.assertEqual(by_id["SVF-OLD"], completed)
        self.assertEqual(by_id["SVF-NEW"], {**pending, "dependencies": ["SVF-122", "SVF-035"]})
        shared = by_id["SVF-035"]
        self.assertEqual(shared["goal_id"], "SVF-G030")
        self.assertEqual(shared["edit_paths"], ["swissknife/web/js/main-simple.js",
                                              "swissknife/web/js/all-app-backend-status.js"])
        protected_test = shared["checks"][0][-1]
        self.assertIn(protected_test, shared["execution_inputs"])
        self.assertNotIn(protected_test, shared["recovery_edit_paths"])
        self.assertEqual(plan.register_shared_desktop_recovery(result, ["SVF-OLD"]), result)

    def test_readonly_closure_is_idempotent_and_preserves_completed_objects(self):
        completed = {"task_id": "SVF-OLD", "app_id": "retired-app", "execution_inputs": ["historical.py"], "edit_paths": ["old.js"]}
        pending = {"task_id": "SVF-NEW", "app_id": "demo", "execution_inputs": ["worker.py"], "edit_paths": ["app.js"]}
        original = {"tasks": [completed, pending], "goals": [{"goal_id": "G1"}]}
        before = copy.deepcopy(original)
        apps = [{"app_id": "demo", "source_paths": ["web/js/apps/demo.js"]}]
        result = plan.bind_runtime_sources(original, apps, ["SVF-OLD"])
        self.assertEqual(original, before)
        self.assertEqual(result["tasks"][0], completed)
        self.assertEqual(result["tasks"][1]["edit_paths"], pending["edit_paths"])
        self.assertEqual(result["goals"], original["goals"])
        sources = result["tasks"][1]["execution_inputs"]
        self.assertIn("swissknife/web/js/apps/demo.js", sources)
        self.assertTrue(set(plan.RUNTIME_SOURCE_INPUTS) <= set(sources))
        self.assertEqual(plan.bind_runtime_sources(result, apps, ["SVF-OLD"]), result)

    def test_outside_app_sources_are_refused(self):
        for name in ("../private.py", "/tmp/private.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                plan.bind_runtime_sources({"tasks": [{"task_id": "SVF-NEW", "app_id": "demo"}]},
                                          [{"app_id": "demo", "source_paths": [name]}])

    def test_failure_feedback_binds_only_pending_verifiers_and_preserves_completed(self):
        old = {"task_id": "SVF-OLD", "kind": "verify", "semantic_recovery_inputs": ["historical.py"]}
        current = {"task_id": "SVF-NEW", "kind": "verify", "semantic_recovery_inputs": ["worker.py"],
                   "semantic_recovery_limit": 2, "edit_paths": ["app.js"], "acceptance": "Actual bytes"}
        spec = {"tasks": [old, current, {"task_id": "SVF-LOCAL", "kind": "repair"}]}
        original = copy.deepcopy(spec)
        result = plan.bind_failure_feedback(spec, ["SVF-OLD"])
        self.assertEqual(spec, original)
        self.assertEqual(result["tasks"][0], old)
        pending = result["tasks"][1]
        self.assertEqual(pending["semantic_recovery_inputs"], ["worker.py",
            plan.RUNTIME + "/tasks/SVF-NEW/last-execution-failure.json"])
        for key in ("semantic_recovery_limit", "edit_paths", "acceptance"):
            self.assertEqual(pending[key], current[key])
        self.assertEqual(plan.bind_failure_feedback(result, ["SVF-OLD"]), result)
        self.assertEqual(result["tasks"][2], spec["tasks"][2])

    def test_r7_native_source_closure_and_defaults_preserve_other_task_contracts(self):
        expected = {"scripts/swissknife_visual_functional_blocked.py",
            "scripts/svf_backends/native_accelerate_backend.py", "scripts/svf_backends/native_accelerate_service.py",
            "swissknife/scripts/ipfs-accelerate-native-forwarder.cjs", "swissknife/scripts/all-tools-evidence-lib.cjs",
            "config/systemd/swissknife-visual-functional-native-accelerate.service",
            "config/systemd/swissknife-visual-functional-accelerate-facade.service",
            "config/systemd/swissknife-visual-functional-notes-datasets.service",
            "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py",
            "external/ipfs_datasets/ipfs_datasets_py/vector_stores/management_engine.py",
            "external/ipfs_datasets/ipfs_datasets_py/vector_stores/duckdb_store.py",
            "scripts/svf_backends/notes_fixture.py", plan.WORKFLOW_FIXTURES}
        self.assertTrue(expected <= set(plan.RUNTIME_SOURCE_INPUTS))
        self.assertEqual(plan.NOTES_INDEXES_DIRECTORY, plan.RUNTIME + "/backends/services/notes-datasets/indexes")
        self.assertEqual(plan.DEFAULT_BACKENDS, {"ipfs_kit_py":"http://127.0.0.1:18316",
            "ipfs_datasets_py":"http://127.0.0.1:18312", "ipfs_accelerate_py":"http://127.0.0.1:18315"})
        pending = {"task_id":"SVF-NEW", "kind":"verify", "edit_paths":["app.js"],
                   "acceptance":"Exact useful result", "semantic_recovery_limit":2,
                   "execution_validation":[{"argv":["python3","original-validator.py"]}]}
        result = plan.bind_runtime_sources({"tasks":[pending]}, [])
        self.assertEqual(result["plan_revision"],plan.RUNTIME_REVISION)
        for key in pending:
            self.assertEqual(result["tasks"][0][key],pending[key])
        self.assertEqual(plan.bind_failure_feedback(result)["plan_revision"],plan.RUNTIME_REVISION)


if __name__ == "__main__":
    unittest.main()
