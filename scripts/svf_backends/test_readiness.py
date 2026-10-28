"""Finite admission tests; authored transports never establish live readiness."""
from __future__ import annotations

import base64
import hashlib
import json
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import common
import scheduler_job


class ReadinessTests(unittest.TestCase):
    def native_fixture(self, root, *, change=None):
        """Authored response fixture; this cannot establish live readiness."""
        files={"sdk_source_sha256":"external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py",
               "backend_source_sha256":"scripts/svf_backends/native_accelerate_backend.py",
               "service_source_sha256":"scripts/svf_backends/native_accelerate_service.py"}
        for name in files.values():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# authored unit fixture\n')
        hashes={key:common.sha((root/path).read_bytes()) for key,path in files.items()}
        class Client:
            def health(self, origin=None):
                value=({"backend":"native_python","upstream_available":True,"native_endpoint":"http://127.0.0.1:18313"} if origin is None else {
                    "native_python_backend":True,"source_contract_current":True,"owner":"ipfs_accelerate_py","device":"cpu",
                    "offline":True,"simulated":False,"echo_fallback":False,**hashes})
                return value
            def catalog(self,_names):pass
            def call(self, tool, args):
                if tool=='list_models':return {"models":[{"id":"gpt2"}]}
                provenance={**hashes,"sdk_class":"ipfs_accelerate_py.inference_backend_manager.InferenceBackendManager",
                    "sdk_method":"execute_task","generated_token_count":1,"correlation_id":"svf-readiness:"+'a'*32,
                    "offline":True,"external_provider_called":False}
                value={"native_provenance":provenance,"generated_token_count":1,"generated_token_ids":[42],"inference_executed":True,
                    "queue_used":False,"execution_semantics":"synchronous_completed_execution","status":"completed","model_id":"gpt2",
                    "generated_text":" authored-fixture","output":"short test aaaaaaaa authored-fixture",
                    "job_id":"00000000-0000-0000-0000-000000000001","task_id":"00000000-0000-0000-0000-000000000001"}
                if tool=='job_status':value.update(read_from_execution_record=True);provenance['sdk_method']='completed_execution_record'
                if change:change(tool,value)
                return value
        return Client()

    def test_native_readiness_requires_current_sources_actual_tokens_and_same_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=common.native_accelerate_qualification(self.native_fixture(Path(tmp)),Path(tmp),'a'*32)
            self.assertTrue(result['inference_executed']);self.assertFalse(result['queue_used'])
            self.assertTrue(result['readback_verified'])

    def test_native_health_flag_alone_and_echo_or_changed_readback_never_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);client=self.native_fixture(root)
            original=client.health;client.health=lambda origin=None:original(origin) if origin is None else {'status':'ok','native_python_backend':True}
            with self.assertRaises(common.ReadinessError):common.native_accelerate_qualification(client,root,'a'*32)
            for mutate in [lambda tool,row:row.update(generated_token_count=0) if tool=='run_inference_job' else None,
                           lambda tool,row:row.update(output='changed') if tool=='job_status' else None,
                           lambda tool,row:row['native_provenance'].update(sdk_source_sha256='0'*64) if tool=='run_inference_job' else None]:
                with self.assertRaises(common.ReadinessError):common.native_accelerate_qualification(self.native_fixture(root,change=mutate),root,'a'*32)

    def test_legacy_accelerator_health_keeps_original_queue_path(self):
        client=type('Legacy',(),{'health':lambda self:{'status':'ok','backend':'legacy'}})()
        self.assertIsNone(common.native_accelerate_qualification(client,Path('/unused'),'a'*32))

    def test_raw_cid_binds_exact_bytes(self):
        # Independently cross-checked with the native Node cidForBytes helper.
        self.assertEqual(common.raw_cid(b"hello"), "bafkreibm6jg3ux5qumhcn2b3flc3tyu6dmlb4xa7u5bf44yegnrjhc4yeq")
        self.assertNotEqual(common.raw_cid(b"hello"), common.raw_cid(b"hello\n"))

    def test_only_bounded_credential_free_loopback_endpoints(self):
        self.assertEqual(common.endpoint("http://127.0.0.1:18014/mcp"), "http://127.0.0.1:18014")
        for value in ["https://127.0.0.1:18014", "http://example.com:18014", "http://127.0.0.1:80",
                      "http://user:password@127.0.0.1:18014", "http://127.0.0.1:18014/other",
                      "http://127.0.0.1:18014?target=other"]:
            with self.subTest(value=value), self.assertRaises(common.ReadinessError):
                common.endpoint(value)

    def envelope(self, owner="ipfs_kit_py", tool="ipfs_cat", payload=None):
        return {"receipt": {"adapter": "swissknife-ipfs-" + common.OWNERS[owner] + "-compat", "tool": tool, "status": "ok"},
                "content": [{"type": "json", "json": payload if payload is not None else {"bytes_base64": "aGVsbG8="}}]}

    def test_health_and_success_flags_cannot_replace_tool_result_binding(self):
        for value in [{"status": "ok"}, {"success": True}, {"content": []}]:
            with self.subTest(value=value), self.assertRaises(common.ReadinessError):
                common.tool_payload(value, "ipfs_kit_py", "ipfs_cat")

    def test_owner_tool_and_preview_boundaries(self):
        value = self.envelope()
        self.assertEqual(common.tool_payload(value, "ipfs_kit_py", "ipfs_cat")["bytes_base64"], "aGVsbG8=")
        for owner, tool in [("ipfs_datasets_py", "ipfs_cat"), ("ipfs_kit_py", "files_read")]:
            with self.assertRaises(common.ReadinessError):
                common.tool_payload(value, owner, tool)
        value["receipt"]["execution_mode"] = "validated_preview"
        with self.assertRaises(common.ReadinessError):
            common.tool_payload(value, "ipfs_kit_py", "ipfs_cat")

    def test_nested_backend_errors_fail_despite_outer_ok(self):
        for payload in [{"result": {"status": "error"}}, {"ok": False}, {"success": False}, {"error": "missing owner"}]:
            with self.subTest(payload=payload), self.assertRaises(common.ReadinessError):
                common.tool_payload(self.envelope(payload=payload), "ipfs_kit_py", "ipfs_cat")

    def test_fixture_bytes_and_cid_are_independently_recomputed(self):
        class Client:
            def catalog(self, _names): pass
            def call(self, tool, _args):
                return {"cid": common.raw_cid(b"expected"), "stored": True} if tool == "ipfs_add" else {
                    "cid": common.raw_cid(b"expected"), "bytes_base64": base64.b64encode(b"tampered").decode(), "verified": True}
        with self.assertRaisesRegex(common.ReadinessError, "retrieval differs"):
            common.store_fixture(Client(), Path("fixture.json"), b"expected")

    def test_fixture_upload_uses_inline_bytes_and_explicit_real_readback(self):
        calls = []
        fixture = b'[{"text":"genuine inline fixture"}]'
        cid = common.raw_cid(fixture)
        class Client:
            def catalog(self, names):
                self_names = ["ipfs_add", "ipfs_cat"]
                if names != self_names:
                    raise AssertionError(names)
            def call(self, tool, args):
                calls.append((tool, args))
                if tool == "ipfs_add":
                    if args != {"content": fixture.decode(), "dry_run": False}:
                        raise AssertionError("upload must not grant host filesystem reads")
                    return {"cid": cid, "stored": True}
                if tool == "ipfs_cat":
                    if args != {"cid": cid, "dry_run": False}:
                        raise AssertionError("readback must execute the native owner")
                    return {"cid": cid, "bytes_base64": base64.b64encode(fixture).decode()}
                raise AssertionError(tool)
        actual = common.store_fixture(Client(), Path("/never/read/fixture.json"), fixture)
        self.assertEqual([name for name, _ in calls], ["ipfs_add", "ipfs_cat"])
        self.assertEqual(actual, {"cid": cid, "sha256": hashlib.sha256(fixture).hexdigest(),
                                 "size_bytes": len(fixture), "real_bytes_verified": True})

    def test_foreign_announcements_block_before_any_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary); announce = cache / "ipfs_accelerate_py/task_p2p_announce.json"
            announce.parent.mkdir(); announce.write_text('{}')
            with self.assertRaisesRegex(common.ReadinessError, "announcement"):
                common.require_local_queue_routing({b"XDG_CACHE_HOME": bytes(cache)})
            common.require_local_queue_routing({b"XDG_CACHE_HOME": bytes(cache), b"IPFS_ACCELERATE_PY_TASK_P2P_ANNOUNCE_FILE": b"0"})
            with self.assertRaisesRegex(common.ReadinessError, "remote task"):
                common.require_local_queue_routing({b"IPFS_ACCELERATE_PY_TASK_P2P_REMOTE_MULTIADDR": b"peer"})

    def test_scoped_paths_refuse_traversal_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "foreign").symlink_to("/tmp", target_is_directory=True)
            for name in ["../outside", "foreign/data.json"]:
                with self.subTest(name=name), self.assertRaises(common.ReadinessError):
                    common.confined(root, name)

    def test_normal_venv_executable_final_symlink_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / ".venv/bin/python"; binary.parent.mkdir(parents=True)
            binary.symlink_to(sys.executable)
            self.assertEqual(common.native_python(root, {"python": ".venv/bin/python"}), binary)

    def test_scheduler_hook_computes_real_output_from_admitted_bytes(self):
        data = b"actual controlled bytes"; nonce = "a" * 32
        task = {"task_type": "svf.sha256", "payload": {"prompt": json.dumps({"nonce": nonce, "bytes_base64": base64.b64encode(data).decode()})}}
        result = scheduler_job.hash_fixture(task)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(result["output"], result["sha256"])
        self.assertEqual(result["nonce"], nonce)
        task["payload"]["prompt"] = json.dumps({"nonce": nonce, "bytes_base64": base64.b64encode(b"changed").decode()})
        self.assertNotEqual(scheduler_job.hash_fixture(task)["output"], result["output"])

    def test_scheduler_rejects_other_tasks_and_oversized_data(self):
        for task in [{"task_type": "shell", "payload": {}}, {"task_type": "svf.sha256", "payload": {"prompt": json.dumps({"nonce": "a" * 32, "bytes_base64": base64.b64encode(b"x" * 4097).decode()})}}]:
            with self.subTest(task_type=task["task_type"]), self.assertRaises(ValueError):
                scheduler_job.hash_fixture(task)

    def test_missing_owner_without_ensure_does_not_launch_or_fabricate_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "listener_identity", return_value=None), patch.object(common.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(common.ReadinessError, "missing"):
                    common.ensure_service(root, "http://127.0.0.1:18014", "ipfs_kit_py", root, {}, False)
                launch.assert_not_called()

    def test_completed_queue_flags_cannot_replace_usable_matched_job_output(self):
        data = b"fixture"; nonce = "a" * 32; digest = hashlib.sha256(data).hexdigest()
        row = {"task_id": "job", "status": "completed", "assigned_worker": "owned-worker",
               "result": {"operation": "sha256", "nonce": nonce, "size_bytes": len(data), "sha256": digest, "output": digest}}
        common.verify_scheduler_result(row, "job", "owned-worker", nonce, data)
        for field, value in [("status", "running"), ("task_id", "foreign"), ("assigned_worker", "foreign")]:
            wrong = json.loads(json.dumps(row)); wrong[field] = value
            with self.subTest(field=field), self.assertRaises(common.ReadinessError):
                common.verify_scheduler_result(wrong, "job", "owned-worker", nonce, data)
        for field, value in [("output", None), ("nonce", "b" * 32), ("sha256", "0" * 64), ("size_bytes", 999)]:
            wrong = json.loads(json.dumps(row)); wrong["result"][field] = value
            with self.subTest(field=field), self.assertRaises(common.ReadinessError):
                common.verify_scheduler_result(wrong, "job", "owned-worker", nonce, data)

    def test_rpc_retains_original_bytes_and_refuses_correlation_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = {"pid": 1, "start_ticks": "123", "owner": "ipfs_kit_py"}
            with patch.object(common, "listener_identity", return_value=identity):
                client = common.Transport(root, "http://127.0.0.1:18014", "ipfs_kit_py", root)
                raw = b'{"jsonrpc":"2.0","id":"wrong","result":{"tools":[]}}'
                client.opener = type("Opener", (), {"open": lambda *_a, **_k: io.BytesIO(raw)})()
                with self.assertRaisesRegex(common.ReadinessError, "correlation"):
                    client.rpc("tools/list", {})
                record = client.records[0]
                self.assertEqual((root / record["response_path"]).read_bytes(), raw)
                self.assertEqual(record["response_sha256"], hashlib.sha256(raw).hexdigest())

    def test_rpc_owner_restart_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(common, "listener_identity", side_effect=[{"pid": 1}, {"pid": 2}]):
                client = common.Transport(root, "http://127.0.0.1:18014", "ipfs_kit_py", root)
                with self.assertRaisesRegex(common.ReadinessError, "changed before"):
                    client.rpc("tools/list", {})
                self.assertEqual(list(root.iterdir()), [])

    def test_redirects_cannot_escape_loopback_owner(self):
        with self.assertRaisesRegex(common.ReadinessError, "redirects"):
            common.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://foreign.example")


if __name__ == "__main__":
    unittest.main()
