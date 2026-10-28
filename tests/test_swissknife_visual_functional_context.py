"""Bounded app context keeps complete edits and checks omitted source hashes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm


class NativeEmbeddingContextTests(unittest.TestCase):
    def setUp(self):
        self.case = RepairContextTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.names = ["swissknife/web/js/main-simple.js", "swissknife/web/js/all-app-backend-status.js"]
        self.source = ('for (const output of scope.querySelectorAll("output[data-gateway-status]")) {\n'
                       'group.dataset.nativeOperationDetails = "true";\n'
                       'group.style.cssText = "grid-column:1 / -1;flex:0 0 auto;min-width:0;max-width:100%";\n'
                       'parent.append(group);\n'
                       'group.querySelector("[data-native-operation-body]").append(output);\n}\n')
        self.case.write(self.names[0], '<div class="window-content">\n<div class="window-app-content">\n'
                        '<div id="${windowId}-content">\n'
                        '<div class="live-tool-gateway-host" id="${windowId}-gateway"></div>\n')
        self.case.write(self.names[1], self.source)
        self.case.task["execution_inputs"] = self.names

    def test_exact_declared_embedding_lines_are_bounded_and_full_hash_fenced(self):
        context, sources = worker._repair_native_embedding_context(self.case.task, self.case.targets)
        self.assertLessEqual(len(json.dumps(context, indent=2).encode()), 1500)
        self.assertEqual(sources, [worker.artifact(self.case.root / name) for name in self.names])
        self.assertIn('data-native-operation-body', json.dumps(context))
        self.assertIn('flex:0 0 auto', json.dumps(context))
        self.assertIn('not observed/computed layout or edit permission', context['authority'])
        for record in context['sources']:
            self.assertEqual({key: record[key] for key in ('path', 'sha256', 'bytes')}, worker.artifact(self.case.root / record['path']))
            actual = (self.case.root / record['path']).read_text().splitlines()
            for line, content in record['lines']:
                self.assertEqual(actual[line - 1].strip(), content)

    def test_undeclared_external_mounts_are_not_added(self):
        self.case.task['execution_inputs'] = []
        context, sources = worker._repair_native_embedding_context(self.case.task, [])
        self.assertIsNone(context)
        self.assertEqual(sources, [])

    def test_ambiguous_anchor_is_not_guessed(self):
        self.case.write(self.names[1], self.source + '\nparent.append(group);\n')
        context, _ = worker._repair_native_embedding_context(self.case.task, self.case.targets)
        self.assertNotIn('parent.append(group);', [content for record in context['sources'] for _line, content in record['lines']])

    def test_context_bound_refuses_instead_of_truncating_exact_source_or_identity(self):
        with self.assertRaisesRegex(ValueError, 'native embedding source context exceeds'):
            worker._repair_native_embedding_context(self.case.task, self.case.targets, byte_budget=64)

    def test_layout_repair_receives_embedding_even_without_css_and_midcall_change_is_refused(self):
        self.case.visual_failure()
        def invoke(*_args, **kwargs):
            context = json.loads((self.case.root / kwargs['input_paths'][0]).read_text())
            self.assertIn('native_embedding_context', context)
            self.assertNotIn('shared_stylesheet_context', context)
            self.assertEqual(kwargs['predicted_files'], self.case.targets)
            self.case.write(self.names[1], self.source + '// concurrent native mount change\n')
            return {'success': True}
        with patch('swissknife_visual_functional_phase_budget.admit', return_value=None):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.case.call(invoke)

    def test_nonlayout_repair_does_not_add_mount_context(self):
        def invoke(*_args, **kwargs):
            context = json.loads((self.case.root / kwargs['input_paths'][0]).read_text())
            self.assertNotIn('native_embedding_context', context)
            return {'success': True}
        self.case.call(invoke)

    def test_adaptive_css_shrinks_without_losing_mounts_complete_targets_or_fences(self):
        css = list(self.case.shared_css())
        self.case.task['execution_inputs'] += self.names
        self.case.write(self.names[1], self.source)
        self.case.visual_failure()
        original = worker._repair_inputs
        attempts, contexts = [], []
        def select(*args):
            contexts.append(json.loads(args[3].read_text())['native_embedding_context'])
            attempts.append(1)
            if len(attempts) == 1:
                raise llm.ModelContextBudgetError(args[-1] + 2048, args[-1])
            return original(*args)
        def invoke(*_args, **kwargs):
            context = json.loads((self.case.root / kwargs['input_paths'][0]).read_text())
            self.assertEqual(context['native_embedding_context'], contexts[0])
            self.assertEqual(set(kwargs['predicted_files']), set(self.case.targets))
            for name in self.case.targets:
                self.assertIn(name, kwargs['input_paths'])
            self.assertEqual(context['shared_stylesheet_context']['sources'], [worker.artifact(self.case.root / name) for name in css])
            return {'success': True}
        with patch.object(worker, '_repair_inputs', side_effect=select), patch('swissknife_visual_functional_phase_budget.admit', return_value=None):
            self.case.call(invoke)
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(context == contexts[0] for context in contexts))


class RepairContextTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        root_patch = patch.object(worker, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.metadata = ["swissknife/src/services/apps/virtual-desktop-app-manifest.ts",
                         "swissknife/src/services/apps/all-app-executable-backend-contract.ts"]
        self.targets = ["swissknife/web/js/main-simple.js", "swissknife/test/e2e/functional-workflows/demo.json"]
        self.write(self.targets[0], "// actual full editable source\n" * 6200)
        self.write(self.targets[1], '{"fixture_scope":"svf-context-demo"}\n')
        for name in self.metadata:
            self.write(name, "// unrelated global catalogue entry\n" * 1400)
        self.write("swissknife/docs/visual-functional-driver-contract.md", "Readonly input scenario grammar.\n")
        self.profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional",
                        "humanPlanPath": "plan.md", "taskSpecPath": "tasks.json", "appContractPath": "contracts.json",
                        "llm": {"repairReadPolicy": "inline_only", "repairReasoningEffort": "low"}}
        self.task = {"task_id": "SVF-133", "kind": "verify", "app_id": "demo", "title": "Check real source",
                     "edit_paths": self.targets, "context_paths": self.metadata}
        self.write("profile.json", json.dumps(self.profile))
        self.write("tasks.json", json.dumps({"tasks": [self.task]}))
        self.write("contracts.json", json.dumps({"apps": [{"app_id": "demo", "title": "Only this app"}]}))
        self.output = self.root / self.profile["runtimeRoot"] / "tasks/SVF-133/repair.json"
        self.output.parent.mkdir(parents=True)

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def call(self, callback):
        with patch.object(llm, "invoke_task_model", side_effect=callback), patch.object(llm, "validate_model_receipt"):
            return worker.model("profile.json", self.task, "repair", [*self.metadata, *self.targets], [], self.output)

    def test_large_readonly_catalogues_use_app_contract_without_truncating_edits(self):
        def invoke(*_args, **kwargs):
            inputs = kwargs["input_paths"]
            context = json.loads((self.root / inputs[0]).read_text())
            self.assertEqual(context["app_contract"]["app_id"], "demo")
            omitted = context["omitted_repository_metadata"]
            self.assertEqual({item["path"] for item in omitted}, set(self.metadata))
            for item in omitted:
                self.assertEqual(item["sha256"], worker.sha(self.root / item["path"]))
                self.assertNotIn(item["path"], inputs)
            self.assertEqual({item["path"] for item in context["complete_edit_targets"]}, set(self.targets))
            for name in self.targets:
                self.assertIn(name, inputs)
            self.assertEqual(kwargs["predicted_files"], self.targets)
            inline = [{"path": name, "content": (self.root / name).read_text()} for name in inputs]
            self.assertLess(len(json.dumps(inline, ensure_ascii=False).encode()), 262144)
            return {"success": True}
        self.call(invoke)

    def test_metadata_is_retained_in_full_when_it_is_an_edit_target(self):
        self.write(self.targets[0], "// small source\n")
        self.task["edit_paths"] = [*self.targets, self.metadata[0]]
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertIn(self.metadata[0], kwargs["input_paths"])
            self.assertNotIn(self.metadata[0], {item["path"] for item in context["omitted_repository_metadata"]})
            self.assertIn(self.metadata[0], {item["path"] for item in context["complete_edit_targets"]})
            return {"success": True}
        self.call(invoke)

    def native_sources(self):
        self.write("swissknife/web/js/live-tool-gateway.js", "export async function invokeNativeTool(container, appId, bindingId, options = {}) {}\n")
        self.write("swissknife/web/js/apps/network-native-tools.js", "export async function invokeNetworkNativeTool(container, appId, tool, payload, trigger = null) {}\n")

    def shared_css(self):
        self.write(self.targets[0], '<div class="demo-container chat-sidebar"></div>\n')
        names = ["swissknife/web/css/apps.css", "swissknife/web/css/other.css"]
        self.write(names[0], '/* unrelated head */\n' * 200 + '.demo-container { display:flex; flex-direction:column; }\n'
                   + '@media(max-width:768px) { .chat-sidebar { flex: 1 1 220px; content: "}"; } }\n')
        self.write(names[1], '.foreign-container { display:grid; }\n')
        self.task["execution_inputs"] = names
        return names

    def visual_failure(self):
        self.profile["llm"].update(provider="grok_cli", model="grok-4.7", allowLocalFallback=False,
                                   allowCrossProviderFallback=False)
        self.write("profile.json", json.dumps(self.profile))
        path = self.output.parent / "visual-review.json"
        path.write_text(json.dumps({"schema": llm.RECEIPT_SCHEMA, "task_id": self.task["task_id"], "mode": "review",
                                    "success": True, "response": {"decision": "needs_changes",
                                    "findings": [{"description": "Desktop toolbar is below the sidebar."}]}}))
        worker.remember_execution_failure(self.profile, self.task, ValueError("visual layout failed"),
                                          stage="verification", review_output=path)

    def test_shared_css_preserves_exact_late_rules_and_conditional_context(self):
        names = self.shared_css()
        value, sources = worker._repair_stylesheet_context(self.task, self.targets)
        self.assertTrue(value["excerpt_only"])
        self.assertEqual([record["path"] for record in sources], names)
        rules = value["rules"]
        self.assertIn('.demo-container { display:flex; flex-direction:column; }', rules[0]["content"])
        self.assertGreater(rules[0]["start_line"], 120)
        conditional = next(rule for rule in rules if "chat-sidebar" in rule["matched_tokens"])
        self.assertEqual(conditional["conditions"], ["@media(max-width:768px)"])
        self.assertIn('content: "}"', conditional["content"])
        self.assertNotIn("foreign-container", json.dumps(rules))

    def test_shared_css_bound_prioritizes_app_collision_without_truncating_rules(self):
        names = self.shared_css()
        path = self.root / names[0]
        path.write_text('.chat-sidebar { color: red; }\n' * 250 + '\n.demo-container { flex-direction:column; }\n')
        value, _sources = worker._repair_stylesheet_context(self.task, self.targets, byte_budget=4096)
        self.assertLessEqual(len(json.dumps(value, ensure_ascii=False).encode()), 4096)
        self.assertGreater(value["omitted_rule_count"], 0)
        self.assertIn('.demo-container { flex-direction:column; }', value["rules"][0]["content"])
        self.assertTrue(all(rule["content"].endswith("}") for rule in value["rules"]))

    def test_shared_css_order_uses_actual_desktop_document_and_hash_fences_it(self):
        names = self.shared_css()
        page = "swissknife/web/index.html"
        self.write(page, '<link rel="stylesheet" href="/css/other.css"><link rel="stylesheet" href="/css/apps.css">')
        self.task["execution_inputs"].append(page)
        value, sources = worker._repair_stylesheet_context(self.task, self.targets)
        actual_rule = next(rule for rule in value["rules"] if rule["path"] == names[0])
        self.assertEqual(actual_rule["stylesheet_order"], 1)
        self.assertEqual(value["stylesheet_order_document"], worker.artifact(self.root / page))
        self.assertIn(worker.artifact(self.root / page), sources)
        self.write(page, '<link rel="stylesheet" href="/css/apps.css">')
        with self.assertRaisesRegex(ValueError, "changed"):
            worker.check_artifacts(sources)

    def test_visual_repair_receives_readonly_css_and_refuses_midcall_changes(self):
        names = self.shared_css()
        self.visual_failure()
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            css = context["shared_stylesheet_context"]
            self.assertEqual(css["sources"][0], worker.artifact(self.root / names[0]))
            self.assertEqual(kwargs["predicted_files"], self.targets)
            self.assertTrue(all(name in kwargs["input_paths"] for name in self.targets))
            with (self.root / names[0]).open("a") as handle:
                handle.write('.demo-container { flex-direction:row; }\n')
            return {"success": True}
        with patch("swissknife_visual_functional_phase_budget.admit", return_value=None):
            with self.assertRaisesRegex(ValueError, "changed"):
                self.call(invoke)

    def test_nonvisual_repair_does_not_spend_context_on_shared_css(self):
        self.shared_css()
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertNotIn("shared_stylesheet_context", context)
            return {"success": True}
        self.call(invoke)

    def test_driver_layout_failure_receives_css_before_any_visual_review(self):
        names = self.shared_css()
        self.profile["llm"].update(provider="grok_cli", model="grok-4.7", allowLocalFallback=False,
                                   allowCrossProviderFallback=False)
        self.write("profile.json", json.dumps(self.profile))
        attempt = self.output.parent / "verification/attempt-unit-layout"
        attempt.mkdir(parents=True)
        diagnostic = {"schema": "swissknife.visual-functional-workflow-failure.v1", "app_id": self.task["app_id"],
            "error": {"code": "POSTCONDITION_FAILED", "details": {
                "operator": "equals", "actual": ["primary_content_outside_app_window"], "expected": [],
                "context": {"phase": "backend_proof", "probe": {"kind": "backend_result"}}}},
            "phase": "backend_proof", "step": None, "artifacts": [], "actual_desktop": False,
            "functional_acceptance": "not_evaluated", "work_complete": False, "completion_authority": False}
        (attempt / "failure.json").write_text(json.dumps(diagnostic))
        worker.remember_execution_failure(self.profile, self.task, ValueError("layout failed before review"),
                                          stage="workflow", attempt=attempt)
        retained = worker.load_execution_failure(self.profile, self.task)
        self.assertNotIn("visual_review", retained["failure"])
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            css = context["shared_stylesheet_context"]
            self.assertEqual(css["sources"][0], worker.artifact(self.root / names[0]))
            self.assertIn(".demo-container { display:flex; flex-direction:column; }", json.dumps(css))
            self.assertEqual(kwargs["predicted_files"], self.targets)
            self.assertTrue(all(name in kwargs["input_paths"] for name in self.targets))
            return {"success": True}
        self.call(invoke)

    def test_layout_context_requires_exact_typed_driver_violation_not_backend_or_error_text(self):
        def failure(actual, *, code="POSTCONDITION_FAILED", expected=None, schema=None):
            return {"error": {"message": "primary_content_outside_app_window"}, "diagnostic": {
                "schema": schema or "swissknife.visual-functional-workflow-failure.v1",
                "error": {"code": code, "details": {"operator": "equals", "actual": actual,
                                                      "expected": [] if expected is None else expected}}}}
        for flag in worker._DRIVER_LAYOUT_VIOLATIONS:
            with self.subTest(flag=flag):
                self.assertTrue(worker._repair_needs_stylesheet_context(failure([flag])))
        invalid = [None, {}, failure([]), failure(0), failure("primary_content_outside_app_window"),
                   failure(["primary_content_outside_app_window_extra"]),
                   failure(["primary_content_outside_app_window"], code="BACKEND_EVIDENCE_MISSING"),
                   failure(["primary_content_outside_app_window"], expected=["different"]),
                   failure(["primary_content_outside_app_window"], schema="owner.response"),
                   failure(["primary_content_outside_app_window", {"untrusted": True}])]
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(worker._repair_needs_stylesheet_context(value))

    def test_small_visual_repair_retains_default_12k_css_without_adaptation(self):
        names = self.shared_css()
        with (self.root / names[0]).open("a") as source:
            source.write('.chat-sidebar { padding: 1px; }\n' * 500)
        self.visual_failure()
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            size = len(json.dumps(context["shared_stylesheet_context"], ensure_ascii=False).encode())
            self.assertGreater(size, 8192)
            self.assertLessEqual(size, 12288)
            return {"success": True}
        with patch.object(worker, "_repair_stylesheet_context", wraps=worker._repair_stylesheet_context) as css, \
                patch("swissknife_visual_functional_phase_budget.admit", return_value=None):
            self.call(invoke)
        self.assertEqual(css.call_count, 1)
        self.assertEqual(css.call_args.kwargs["byte_budget"], 12288)

    def test_css_budget_rebuild_preserves_complete_edits_and_all_readonly_identities(self):
        names = self.shared_css()
        with (self.root / names[0]).open("a") as source:
            source.write('.chat-sidebar { padding: 1px; }\n' * 500)
        self.visual_failure()
        original = worker._repair_inputs
        selections = []
        def select(*args):
            selections.append(1)
            if len(selections) == 1:
                raise llm.ModelContextBudgetError(args[-1] + 4096, args[-1])
            return original(*args)
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            css = context["shared_stylesheet_context"]
            self.assertLessEqual(len(json.dumps(css, ensure_ascii=False).encode()), 12288 - 4096 - 1024)
            self.assertEqual(css["sources"], [worker.artifact(self.root / name) for name in names])
            self.assertGreater(css["omitted_rule_count"], 0)
            self.assertIn('.demo-container { display:flex; flex-direction:column; }', css["rules"][0]["content"])
            self.assertEqual(kwargs["predicted_files"], self.targets)
            self.assertTrue(all(name in kwargs["input_paths"] for name in self.targets))
            return {"success": True}
        with patch.object(worker, "_repair_inputs", side_effect=select), \
                patch("swissknife_visual_functional_phase_budget.admit", return_value=None):
            self.call(invoke)
        self.assertEqual(len(selections), 2)

    def test_css_budget_rebuild_refuses_source_change_before_provider(self):
        names = self.shared_css()
        self.visual_failure()
        calls = []
        def select(*args):
            with (self.root / names[0]).open("a") as source:
                source.write('.demo-container { color: changed; }\n')
            raise llm.ModelContextBudgetError(args[-1] + 1024, args[-1])
        with patch.object(worker, "_repair_inputs", side_effect=select):
            with self.assertRaisesRegex(ValueError, "stylesheet source identity changed"):
                self.call(lambda *_args, **_kwargs: calls.append(1))
        self.assertEqual(calls, [])

    def test_css_budget_retry_is_bounded_and_never_retries_a_provider_call(self):
        self.shared_css()
        self.visual_failure()
        selections, calls = [], []
        def select(*args):
            selections.append(1)
            raise llm.ModelContextBudgetError(args[-1] + 1024, args[-1])
        with patch.object(worker, "_repair_inputs", side_effect=select):
            with self.assertRaises(llm.ModelContextBudgetError):
                self.call(lambda *_args, **_kwargs: calls.append(1))
        self.assertEqual(len(selections), 3)
        self.assertEqual(calls, [])

    def test_css_budget_identity_floor_fails_closed_without_provider(self):
        self.shared_css()
        self.visual_failure()
        calls = []
        def select(*args):
            raise llm.ModelContextBudgetError(args[-1] + 11200, args[-1])
        with patch.object(worker, "_repair_inputs", side_effect=select):
            with self.assertRaisesRegex(ValueError, "stylesheet identity exceeds"):
                self.call(lambda *_args, **_kwargs: calls.append(1))
        self.assertEqual(calls, [])

    def test_authoring_context_preserves_exact_binding_policy_and_canonical_esm_api(self):
        self.native_sources()
        roles = [{"owner": "ipfs_kit_py", "bindings": [
            {"binding_id": "demo.read", "exact_tool_candidates": ["node_id"], "policy_class": "read",
             "mutates_remote_state": False, "transports": ["http"]},
            {"binding_id": "demo.retrieve", "exact_tool_candidates": ["ipfs_cat"], "policy_class": "write",
             "mutates_remote_state": True, "transports": ["http", "libp2p"]}]}]
        self.write("contracts.json", json.dumps({"apps": [{"app_id": "demo", "backend_roles": roles}]}))
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertEqual(context["app_contract"]["backend_roles"], roles)
            native = context["scenario_input_contract"]
            for fragment in ["import {invokeNativeTool}", "../live-tool-gateway.js", "never window/global",
                             "Ungoverned read/media_capture has NO dialog", "Never infer policy from tool name",
                             "NOT a binding ID", "does not forward executionMode"]:
                self.assertIn(fragment, native["instruction"])
            self.assertEqual(len(native["native_sources"]), 2)
            for item in native["native_sources"]:
                self.assertEqual(item, worker.artifact(self.root / item["path"]))
                self.assertNotIn(item["path"], kwargs["predicted_files"])
            self.assertEqual({r["path"] for r in context["complete_edit_targets"]}, set(self.targets))
            return {"success": True}
        self.call(invoke)

    def test_native_api_readonly_source_change_invalidates_repair_without_edit_authority(self):
        self.native_sources()
        def invoke(*_args, **kwargs):
            self.write("swissknife/web/js/live-tool-gateway.js", "// concurrent gateway change\n")
            return {"success": True}
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.call(invoke)

    def test_qualified_dataset_fixture_hash_is_context_and_readonly_source_fence(self):
        name = "data/agent_supervisor/swissknife_visual_functional/backends/fixtures/model-catalog-test.json"
        source=self.write(name,'[{"model":"gpt2"}]')
        self.write('fixtures.json',json.dumps({'inference_model':'gpt2','notes_collection':'svf-notes-'+'a'*32,'dataset_file':name}))
        self.profile['workflowFixturesPath']='fixtures.json';self.write('profile.json',json.dumps(self.profile))
        def invoke(*_args, **kwargs):
            context=json.loads((self.root/kwargs['input_paths'][0]).read_text())
            self.assertEqual(context['qualified_workflow_inputs']['dataset_source'],worker.artifact(source))
            source.write_text('[{"model":"changed-under-owner"}]')
            return {'success':True}
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.call(invoke)

    def test_omitted_readonly_source_change_still_invalidates_the_call(self):
        def invoke(*_args, **_kwargs):
            (self.root / self.metadata[0]).write_text("// foreign update\n")
            return {"success": True}
        with self.assertRaises(ValueError):
            self.call(invoke)

    def test_inline_only_never_truncates_an_edit_target_to_fit(self):
        self.write(self.targets[0], "x" * 250001)
        calls = []
        with self.assertRaises(llm.ModelContextBudgetError):
            self.call(lambda *args, **kwargs: calls.append(kwargs))
        self.assertEqual(calls, [])

    def test_visual_review_findings_survive_projection_without_native_telemetry(self):
        name = str((self.output.parent / "visual-review.json").relative_to(self.root))
        response = {"decision": "needs_changes", "summary": "Focus indicator blends into background",
                    "findings": [{"severity": "major", "description": "Table columns overlap"}], "edits": []}
        self.write(name, json.dumps({"schema": llm.RECEIPT_SCHEMA, "mode": "review", "success": True,
                                    "response": response, "native_observation": {"telemetry": "UNRELATED_TELEMETRY" * 5000}}))
        self.metadata = [name]
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertEqual(context["projected_review_sources"], [worker.artifact(self.root / name)])
            self.assertNotIn(name, kwargs["input_paths"])
            projections = [json.loads((self.root / path).read_text()) for path in kwargs["input_paths"]
                           if Path(path).name.startswith("review-context-")]
            self.assertEqual(len(projections), 1)
            self.assertEqual(projections[0]["response"], response)
            self.assertNotIn("UNRELATED_TELEMETRY", json.dumps(projections))
            return {"success": True}
        self.call(invoke)

    def test_reachable_adapter_without_upstream_evidence_is_not_ready(self):
        self.profile["backends"] = {"ipfs_kit_py": "http://127.0.0.1:18316"}
        task = {"task_id": "SVF-011", "kind": "backend-audit", "edit_paths": []}
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self): return b'{"status":"running"}'
        with patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), \
                patch.object(worker.urllib.request, "urlopen", return_value=Response()):
            receipt = worker.execute("profile.json", self.profile, {"tasks": []}, task)
        observed = receipt["detail"]["observations"][0]
        self.assertIs(observed["upstream_ready"], False)
        self.assertEqual(observed["upstream_status"], "unverified")
        self.assertEqual(receipt["detail"]["degraded_owners"], ["ipfs_kit_py"])

    def test_runtime_invalid_positive_checkpoint_cannot_launch_browser_actions(self):
        self.write(self.targets[1], json.dumps({"phases": {"primary_result": [
            {"op": "assert", "checkpoint_id": "positive_backend_bytes", "probe": {"kind": "count", "selector": "img"},
             "operator": "equals", "expected": 1}]}}))
        with patch.object(worker, "run") as run:
            with self.assertRaisesRegex(ValueError, "checkpoint_id is only error_observed"):
                worker.workflow(self.profile, self.task, self.output.parent / "verification")
        run.assert_not_called()

    def test_command_recovery_supplies_current_failure_once_with_or_without_packet_copy(self):
        self.task.update(task_id="SVF-035", kind="command", app_id=None)
        self.profile["llm"].update(provider="grok_cli", model="grok-4.7", temperature=0,
                                   allowLocalFallback=False, allowCrossProviderFallback=False)
        self.write("profile.json", json.dumps(self.profile))
        self.write("tasks.json", json.dumps({"tasks": [self.task]}))
        self.write("contracts.json", json.dumps({"apps": [{"app_id": "demo", "title": "Only this app", "disposition": "operational"}]}))
        self.output = self.root / self.profile["runtimeRoot"] / "tasks/SVF-035/repair.json"
        self.output.parent.mkdir(parents=True)
        failure = {"schema": worker.EXECUTION_FAILURE_SCHEMA, "task_id": "SVF-035",
                   "task_context_sha256": worker.failure_task_context(self.task),
                   "task_spec_sha256": worker.stable(self.task), "source_sha256": worker.repair_target_hashes(self.task),
                   "stage": "command", "error": {"code": "AssertionError", "message": "EXACT_SHARED_RENDERER_FAILURE"},
                   "work_complete": False, "completion_authority": False}
        failure_path = worker.execution_failure_path(self.profile, self.task)
        failure_path.write_text(json.dumps(failure))
        key = str(failure_path.relative_to(self.root))
        copy_path = self.write(str((self.output.parent / "recovery-feedback/failure.json").relative_to(self.root)), failure_path.read_text())
        for included in (False, True):
            with self.subTest(immutable_failure_copy=included):
                recovery = {"source_before": worker.repair_target_hashes(self.task), "feedback_inputs":
                    {key: {**worker.artifact(copy_path), "included": True}} if included else {}}
                inputs = [*self.targets, *([str(copy_path.relative_to(self.root))] if included else [])]
                captured = []
                def invoke(*_args, **kwargs):
                    context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
                    self.assertEqual("latest_execution_failure" in context, not included)
                    if not included:
                        self.assertEqual(context["latest_execution_failure"]["failure"]["error"], failure["error"])
                    bodies = [(self.root / name).read_text() for name in kwargs["input_paths"]]
                    self.assertEqual(sum(body.count("EXACT_SHARED_RENDERER_FAILURE") for body in bodies), 1)
                    captured.append(context)
                    return {"success": True}
                with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
                    worker.model("profile.json", self.task, "repair", inputs, [], self.output, recovery_context=recovery)
                self.assertEqual(len(captured), 1)


if __name__ == "__main__":
    unittest.main()
