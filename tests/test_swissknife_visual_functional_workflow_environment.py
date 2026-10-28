"""Workflow backend environment reaches authored children; no browser/service calls."""
from __future__ import annotations

import json
import base64
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_worker as worker


class WorkflowEnvironmentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        root_patch = patch.object(worker, "ROOT", self.root);root_patch.start();self.addCleanup(root_patch.stop)
        self.profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional", "appContractPath": "contracts.json",
                        "backends": {"ipfs_kit_py": "http://127.0.0.1:18314", "ipfs_datasets_py": "http://127.0.0.1:13002/",
                                     "ipfs_accelerate_py": "http://127.0.0.1:13003/mcp"}}
        self.task = {"task_id": "SVF-099", "app_id": "demo"}
        self.directory = self.root / self.profile["runtimeRoot"] / "tasks/SVF-099/verification"

    def test_real_workflow_child_sees_configured_endpoints_over_stale_inheritance_and_retains_path(self):
        runner = self.root / "swissknife/scripts/run-visual-functional-workflow.mjs"
        runner.parent.mkdir(parents=True)
        runner.write_text("import fs from 'node:fs';import path from 'node:path';\n"
            "const args=process.argv.slice(2),out=args[args.indexOf('--output-dir')+1];\n"
            "const keys=['SWISSKNIFE_IPFS_KIT_MCP_URL','SWISSKNIFE_IPFS_DATASETS_MCP_URL','SWISSKNIFE_IPFS_ACCELERATE_MCP_URL','PATH','SVF_ENV_UNIT_MARKER'];\n"
            "fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify(Object.fromEntries(keys.map(k=>[k,process.env[k]]))));\n"
            "fs.writeFileSync(path.join(out,'workflow.json'),JSON.stringify({artifacts:[]}));\n")
        original_path = os.environ.get("PATH", "")
        with patch.dict(os.environ, {"SWISSKNIFE_IPFS_KIT_MCP_URL": "http://127.0.0.1:8014/mcp", "SVF_ENV_UNIT_MARKER": "preserved"}), \
                patch.object(worker, "validate_workflow"):
            files, checks = worker.workflow(self.profile, self.task, self.directory)
            self.assertEqual(os.environ["SWISSKNIFE_IPFS_KIT_MCP_URL"], "http://127.0.0.1:8014/mcp")
        observed = json.loads((files[0].parent / "observed.json").read_text())
        self.assertEqual(observed, {"SWISSKNIFE_IPFS_KIT_MCP_URL": "http://127.0.0.1:18314/mcp",
            "SWISSKNIFE_IPFS_DATASETS_MCP_URL": "http://127.0.0.1:13002/mcp", "SWISSKNIFE_IPFS_ACCELERATE_MCP_URL": "http://127.0.0.1:13003/mcp",
            "PATH": original_path, "SVF_ENV_UNIT_MARKER": "preserved"})
        self.assertEqual(checks[0]["configured_backend_endpoints"]["ipfs_kit_py"], observed["SWISSKNIFE_IPFS_KIT_MCP_URL"])

    def test_legacy_run_without_env_preserves_inherited_environment(self):
        script = self.root / "read_environment.py";script.write_text("import os,json;print(json.dumps({'marker':os.environ.get('SVF_ENV_UNIT_MARKER'),'path':os.environ.get('PATH')}))")
        with patch.dict(os.environ, {"SVF_ENV_UNIT_MARKER": "legacy"}):
            result = worker.run(["python3", str(script)])
        self.assertEqual(json.loads(result["output_tail"]), {"marker": "legacy", "path": os.environ.get("PATH")})
        self.assertNotIn("configured_backend_endpoints", result)

    def test_qualified_owner_fixture_file_reaches_the_actual_child(self):
        name = "config/workflow-fixtures.json"
        p = self.root / name; p.parent.mkdir()
        values = {"inference_model": "gpt2", "notes_collection": "svf-notes-" + "a" * 32}
        p.write_text(json.dumps(values))
        runner = self.root / "swissknife/scripts/run-visual-functional-workflow.mjs"
        runner.parent.mkdir(parents=True)
        runner.write_text("import fs from 'node:fs';import path from 'node:path';"
            "const a=process.argv.slice(2),out=a[a.indexOf('--output-dir')+1];"
            "fs.writeFileSync(path.join(out,'received.json'),fs.readFileSync(process.env.SWISSKNIFE_VDG_PAYLOAD_FIXTURES));"
            "fs.writeFileSync(path.join(out,'workflow.json'),JSON.stringify({artifacts:[]}));")
        with patch.object(worker, "validate_workflow"):
            files, _ = worker.workflow({**self.profile, "workflowFixturesPath": name}, self.task, self.directory)
        self.assertEqual(json.loads((files[0].parent / "received.json").read_text()), values)

    def test_unknown_or_nonisolated_fixture_values_fail_before_browser(self):
        p = self.root / "fixtures.json"
        for values in [{"inference_model": "external-model", "notes_collection": "default"},
                       {"inference_model": "gpt2", "notes_collection": "svf-notes-" + "a" * 32, "api_key": "private"}]:
            p.write_text(json.dumps(values))
            with patch.object(worker, "run") as spawn:
                with self.assertRaises(ValueError):
                    worker.workflow({**self.profile, "workflowFixturesPath": "fixtures.json"}, self.task, self.directory)
                spawn.assert_not_called()

    def test_optional_owner_cids_and_catalog_file_are_exact_typed_fixture_inputs(self):
        catalog = "data/agent_supervisor/swissknife_visual_functional/backends/fixtures/model-catalog-test.json"
        path = self.root / catalog;path.parent.mkdir(parents=True);path.write_text('[{"model":"gpt2"}]')
        cid = 'b' + base64.b32encode(b'\x01\x55\x12\x20' + hashlib.sha256(b'authored fixture').digest()).decode().lower().rstrip('=')
        values = {"inference_model":"gpt2", "notes_collection":"svf-notes-"+'a'*32,
                  "artifact_cids":{"file-manager":cid,"github":cid}, "dataset_file":catalog,
                  "dataset_cid":cid, "gateway":"http://127.0.0.1:8091"}
        (self.root/'fixtures.json').write_text(json.dumps(values))
        self.assertEqual(worker.workflow_fixtures({"workflowFixturesPath":"fixtures.json",'backendReadiness':{'ipfsGateway':'http://127.0.0.1:8091'}})[1], values)

    def test_optional_fixture_paths_cids_and_content_fail_closed_before_browser(self):
        catalog = "data/agent_supervisor/swissknife_visual_functional/backends/fixtures/model-catalog-test.json"
        path = self.root / catalog;path.parent.mkdir(parents=True);path.write_text('[{"model":"gpt2"}]')
        values = {"inference_model":"gpt2", "notes_collection":"svf-notes-"+'a'*32}
        variants = [{"artifact_cids":{"unknown-app":"b"+'a'*58}}, {"artifact_cids":{"github":"QmUnqualified"}},
                    {"artifact_cids":{"github":'b'+base64.b32encode(b'\x01\x70\x12\x20'+b'a'*32).decode().lower().rstrip('=')}},
                    {"dataset_file":"elsewhere/model-catalog.json"}, {"dataset_file":catalog.replace('model-catalog-test','../model-catalog-test')},
                    {"dataset_file":catalog.replace('-test','-missing')}, {"dataset_file":str(path)}]
        variants += [{"dataset_cid":"b"+'a'*58}, {"gateway":"http://127.0.0.1:8091"},
                     {"dataset_cid":"b"+'a'*58,"gateway":"http://external.example:8091"},
                     {"dataset_cid":"b"+'a'*58,"gateway":"http://127.0.0.1:8091"}]
        fixture=self.root/'fixtures.json'
        for extra in variants:
            fixture.write_text(json.dumps({**values, **extra}))
            with self.subTest(extra=extra), patch.object(worker,'run')as spawn:
                with self.assertRaises(ValueError):worker.workflow({**self.profile,'workflowFixturesPath':'fixtures.json'},self.task,self.directory)
                spawn.assert_not_called()
        fixture.write_text(json.dumps({**values,'dataset_file':catalog}))
        for content in ['null','[]','{bad','{"x":NaN}','{"x":1,"x":2}','['+'1,'*40000+'0]']:
            path.write_text(content)
            with self.subTest(content=content[:30]), self.assertRaises(ValueError):worker.workflow_fixtures({'workflowFixturesPath':'fixtures.json'})
        path.unlink();target=self.root/'catalog.json';target.write_text('[1]');path.symlink_to(target)
        with self.assertRaises(ValueError):worker.workflow_fixtures({'workflowFixturesPath':'fixtures.json'})

    def test_owned_replacement_gateway_is_registered_and_profile_exact(self):
        cid = 'b' + base64.b32encode(b'\x01\x55\x12\x20' + hashlib.sha256(b'owned gateway fixture').digest()).decode().lower().rstrip('=')
        values = {"inference_model":"gpt2", "notes_collection":"svf-notes-"+'a'*32,
                  "dataset_cid":cid, "gateway":"http://127.0.0.1:8092"}
        path = self.root/'fixtures.json';path.write_text(json.dumps(values))
        profile = {"workflowFixturesPath":"fixtures.json", "backendReadiness":{"ipfsGateway":"http://127.0.0.1:8092"}}
        self.assertEqual(worker.workflow_fixtures(profile)[1], values)
        with self.assertRaises(ValueError):
            worker.workflow_fixtures({**profile,"backendReadiness":{"ipfsGateway":"http://127.0.0.1:8091"}})
        for origin in ['http://127.0.0.1:8093','http://external.example:8092','http://user:password@127.0.0.1:8092','https://127.0.0.1:8092','http://127.0.0.1:8092/extra']:
            path.write_text(json.dumps({**values,"gateway":origin}))
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                worker.workflow_fixtures({**profile,"backendReadiness":{"ipfsGateway":origin}})

    def test_incomplete_or_unsafe_backend_configuration_fails_before_spawning(self):
        variants = [{"ipfs_kit_py": "http://127.0.0.1:18314"}]
        for value in ["https://127.0.0.1:18314", "http://external.example:18314", "http://user:secret@127.0.0.1:18314",
                      "http://127.0.0.1:18314/mcp?token=secret", "http://127.0.0.1:18314/mcp#fragment", "http://127.0.0.1:0", "http://127.0.0.1:18314/other"]:
            variants.append({**self.profile["backends"], "ipfs_kit_py": value})
        for backends in variants:
            with self.subTest(backends=backends), patch.object(worker, "run") as spawn:
                with self.assertRaises(ValueError):
                    worker.workflow({**self.profile, "backends": backends}, self.task, self.directory)
                spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
