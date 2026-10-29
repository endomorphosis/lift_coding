"""Finite native gateway contracts; authored SDK fixtures never prove live IO."""
import base64
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import native_kit_service as native


class SDKFixture:
    simulated = False
    transport_kind = "http"
    def __init__(self):self.data = b" \x00\xff<svg/>\n";self.calls=[];self.fail=False;self.peer_rows=[]
    def _request(self, operation, **kwargs):self.calls.append(operation);return {"Size":len(self.data)}
    def result(self, operation):
        if self.fail:raise RuntimeError("actual dependency unavailable fixture")
        return SimpleNamespace(data=self.data,success=True,resulting_content_cid=native.cid_for(self.data),canonical_result=SimpleNamespace(request_id="fixture-request",operation_id="fixture-operation"))
    def cat(self, cid, **kwargs):self.calls.append("cat");return self.result("cat")
    def add(self, data, **kwargs):self.calls.append("add");self.data=data;return self.result("add")
    def node_id(self, **kwargs):
        self.calls.append("node_id");value=self.result("node_id");value.metadata={"ID":"12D3KooWAuthoredUnitIdentity1234567890", "Addresses":["/ip4/127.0.0.1/tcp/4001"], "addresses_reported_null":False};return value
    def swarm_peers(self, **kwargs):
        self.calls.append("swarm_peers");value=self.result("swarm_peers")
        raw={"Peers":self.peer_rows};rows=self.peer_rows if self.peer_rows is not None else []
        value.metadata={"Peers":rows, "peer_count":len(rows), "peers_reported_null":self.peer_rows is None,
                        "raw_observation":raw,"raw_observation_canonical_sha256":native.digest(json.dumps(raw,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())}
        return value


class NativeKitTests(unittest.TestCase):
    def setUp(self):
        self.backend = native.NativeKit.__new__(native.NativeKit)
        self.backend.root=native.ROOT;self.backend.kubo_api="http://127.0.0.1:5021"
        self.backend.sdk_sha256="a"*64;self.backend.client=SDKFixture()
    def test_cat_always_invokes_sdk_and_preserves_every_byte(self):
        client=self.backend.client;cid=native.cid_for(client.data)
        result=self.backend.call("ipfs_cat",{"cid":cid,"dry_run":False,"correlation_id":"fixture","fixture_scope":"svf","scope":"read","limit":1})
        payload=result["content"][0]["json"]
        self.assertEqual(base64.b64decode(payload["bytes_base64"]),client.data)
        self.assertEqual(client.calls,["/api/v0/block/stat","cat"])
        self.assertFalse(payload["native_provenance"]["cache_fallback"])
        self.assertEqual(payload["native_provenance"]["sdk_method"],"cat")
        self.backend.call("ipfs_cat",{"cid":cid})
        self.assertEqual(client.calls.count("cat"),2)
    def test_missing_native_operation_never_falls_back(self):
        self.backend.client.fail=True
        with self.assertRaises(RuntimeError):self.backend.call("ipfs_cat",{"cid":native.cid_for(self.backend.client.data)})
    def test_mismatched_native_bytes_fail_integrity(self):
        with self.assertRaises(RuntimeError):self.backend.call("ipfs_cat",{"cid":native.cid_for(b"different")})
    def test_add_invokes_sdk_and_matches_raw_cid(self):
        data=b"<svg>actual fixture</svg>\n"
        result=self.backend.call("ipfs_add",{"bytes_base64":base64.b64encode(data).decode(),"pin":False})
        payload=result["content"][0]["json"]
        self.assertEqual(payload["cid"],native.cid_for(data));self.assertTrue(payload["stored"])
        self.assertEqual(self.backend.client.calls,["add"])
    def test_previews_arbitrary_paths_and_ambiguous_payloads_are_rejected(self):
        for args in [{"content":"x","dry_run":True},{"file_path":"/etc/passwd"},{"content":"x","data":"y"},{"content":"x"*(native.MAX_ADD_BYTES+1)}]:
            with self.subTest(args=list(args)),self.assertRaises(ValueError):self.backend.call("ipfs_add",args)
        self.assertEqual(self.backend.client.calls,[])
    def test_only_pinned_loopback_kubo_configuration(self):
        for value in ["http://foreign.example:5021","http://user:secret@127.0.0.1:5021","http://127.0.0.1:5021/path"]:
            with self.assertRaises(ValueError):native.origin(value)
    def test_standard_jsonrpc_catalog_initialize_and_call(self):
        for method in ["initialize","tools/list"]:
            result=native.dispatch(self.backend,{"jsonrpc":"2.0","id":"fixture-id","method":method,"params":{}})
            self.assertEqual(result["id"],"fixture-id");self.assertIn("result",result)
        self.assertEqual([t["name"] for t in native.TOOLS],["node_id","swarm_peers","ipfs_cat","ipfs_add"])
        result=native.dispatch(self.backend,{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"ipfs_cat","arguments":{"cid":native.cid_for(self.backend.client.data)}}})
        self.assertIs(result["result"]["isError"],False)


    def test_identity_calls_public_sdk_and_retains_actual_observation(self):
        value=self.backend.call("node_id", {"dry_run":False,"scope":"registry","limit":1,"cursor":"desktop-read-only","correlation_id":"authored"})
        payload=value["content"][0]["json"]
        self.assertEqual(self.backend.client.calls,["node_id"])
        self.assertEqual(payload["ID"],payload["observation"]["ID"])
        self.assertEqual(payload["tool"],"node_id")
        self.assertEqual(payload["native_provenance"]["sdk_method"],"node_id")
        self.assertEqual(value["receipt"]["native_provenance"],payload["native_provenance"])
        raw=__import__("json").dumps(payload["observation"],sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        self.assertEqual(payload["native_provenance"]["payload_sha256"],native.digest(raw))
        self.assertNotIn("cid",payload)
    def test_genuine_empty_swarm_is_preserved_without_fabricated_peer(self):
        value=self.backend.call("swarm_peers",{})["content"][0]["json"]
        self.assertEqual(self.backend.client.calls,["swarm_peers"])
        self.assertEqual(value["Peers"],[]);self.assertEqual(value["peer_count"],0)
        self.assertEqual(value["native_provenance"]["sdk_method"],"swarm_peers")
    def test_explicit_kubo_null_is_empty_but_raw_null_and_hash_remain_bound(self):
        self.backend.client.peer_rows=None
        value=self.backend.call("swarm_peers",{})["content"][0]["json"]
        self.assertEqual(value["Peers"],[]);self.assertEqual(value["peer_count"],0)
        self.assertTrue(value["peers_reported_null"])
        self.assertEqual(value["raw_observation"],{"Peers":None})
        self.assertEqual(value["raw_observation_canonical_sha256"],native.digest(b'{"Peers":null}'))
        observed=json.dumps(value["observation"],sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        self.assertEqual(value["native_provenance"]["payload_sha256"],native.digest(observed))
    def test_missing_raw_peer_key_false_error_or_wrong_marker_cannot_become_empty(self):
        valid=self.backend.client.swarm_peers()
        for change in [{"raw_observation":{}},{"raw_observation":{"Peers":None,"error":"upstream failure"}},
                       {"peers_reported_null":True},{"raw_observation_canonical_sha256":"f"*64}]:
            metadata={**valid.metadata,**change}
            self.backend.client.swarm_peers=lambda **kwargs:SimpleNamespace(metadata=metadata,success=True)
            with self.subTest(change=change),self.assertRaises(RuntimeError):self.backend.call("swarm_peers",{})
    def test_observations_never_return_cached_or_invented_success_on_failure(self):
        self.backend.call("node_id",{})
        self.backend.client.fail=True
        with self.assertRaises(RuntimeError):self.backend.call("node_id",{})
        with self.assertRaises(RuntimeError):self.backend.call("swarm_peers",{})
        self.assertEqual(self.backend.client.calls,["node_id","node_id","swarm_peers"])
    def test_remote_peer_endpoint_and_unsupported_observation_arguments_are_refused(self):
        for tool in ["node_id","swarm_peers"]:
            for args in [{"arg":"remote-peer"},{"url":"http://foreign.example"},{"command":"ipfs id"}]:
                with self.subTest(tool=tool,args=args),self.assertRaises(ValueError):self.backend.call(tool,args)
        self.assertEqual(self.backend.client.calls,[])


if __name__=="__main__":unittest.main()
