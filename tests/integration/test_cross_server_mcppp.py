"""Cross-server integration test for MCP++ profiles across both repos.

Verifies that ipfs_datasets_py and ipfs_accelerate_py implement compatible
MCP++ protocol behavior across all 5 profiles:
- Profile A: IDL interface descriptors
- Profile B: CID-native execution envelopes
- Profile C: UCAN delegation chains
- Profile D: Temporal deontic policy
- Profile E: P2P transport (wire format)
"""

import pytest
import re
import time
import sys
import os
import importlib
import importlib.util

# Base directory for external sources
_ext_dir = os.path.join(os.path.dirname(__file__), '..', '..')
_ACC_MCPPP = os.path.join(_ext_dir, 'external', 'ipfs_accelerate', 'ipfs_accelerate_py', 'mcplusplus_module')
_DS_DIR = os.path.join(_ext_dir, 'external', 'ipfs_datasets')

# Datasets can use sys.path
sys.path.insert(0, _DS_DIR)


def _load_acc_module(name: str, filename: str):
    """Load an accelerate mcplusplus module directly from file to avoid sys.path conflicts."""
    full_name = f"_acc_mcppp.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    # Ensure parent package exists in sys.modules for relative imports
    if "_acc_mcppp" not in sys.modules:
        import types
        pkg = types.ModuleType("_acc_mcppp")
        pkg.__path__ = [_ACC_MCPPP]
        pkg.__package__ = "_acc_mcppp"
        sys.modules["_acc_mcppp"] = pkg
    filepath = os.path.join(_ACC_MCPPP, filename)
    spec = importlib.util.spec_from_file_location(
        full_name, filepath,
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "_acc_mcppp"
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load cid_ucan since interface_descriptor imports from it via relative import
_load_acc_module("cid_ucan", "cid_ucan.py")


class TestProfileAInterop:
    """Profile A: Both repos produce compatible interface descriptors."""

    def test_datasets_interface_descriptor(self):
        from ipfs_datasets_py.mcp_server.interface_descriptor import InterfaceDescriptor
        iface = InterfaceDescriptor(
            name="test-datasets", namespace="ipfs.datasets", version="1.0.0",
            methods=[],
        )
        # Datasets uses .interface_cid property
        cid = iface.interface_cid
        assert cid is not None and len(cid) > 0
        d = iface.to_dict()
        assert "interface_cid" in d
        assert d["name"] == "test-datasets"

    def test_accelerate_interface_descriptor(self):
        mod = _load_acc_module("interface_descriptor", "interface_descriptor.py")
        iface = mod.InterfaceDescriptor(
            name="test-accelerate", version="1.0.0",
            methods=[mod.MethodDescriptor(name="infer", description="Run inference")],
        )
        assert re.match(r"^b[a-z2-7]{58}$", iface.cid)  # real CIDv1 base32
        d = iface.to_dict()
        assert d["name"] == "test-accelerate"
        assert len(d["methods"]) == 1

    def test_accelerate_repository_preloaded(self):
        mod = _load_acc_module("interface_descriptor", "interface_descriptor.py")
        repo = mod.get_interface_repository()
        interfaces = repo.list_all()
        assert len(interfaces) >= 3  # taskqueue, workflow, hardware
        names = [i.name for i in interfaces]
        assert "ipfs-accelerate-p2p-taskqueue" in names
        assert "ipfs-accelerate-hardware" in names


class TestProfileBInterop:
    """Profile B: Both repos produce compatible CID-native execution."""

    def test_datasets_cid_artifacts(self):
        from ipfs_datasets_py.mcp_server.cid_artifacts import IntentObject, artifact_cid
        intent = IntentObject(
            interface_cid="bafy-test", tool="search",
            input_cid=str(artifact_cid({"query": "hello"})),
        )
        assert hasattr(intent, 'cid')

    @pytest.mark.asyncio
    async def test_accelerate_execution_envelope(self):
        mod = _load_acc_module("cid_ucan", "cid_ucan.py")

        async def mock_exec(method, params):
            return {"result": "ok"}

        envelope = await mod.execute_with_envelope(
            method="infer", params={"model": "bert"}, executor_fn=mock_exec,
        )
        assert envelope.receipt.success
        assert re.match(r"^b[a-z2-7]{58}$", envelope.cid)  # real CIDv1 base32
        d = envelope.to_dict()
        assert "intent" in d and "decision" in d and "receipt" in d

    def test_cross_repo_cid_equivalence(self):
        """Same artifact must yield identical, spec-conformant CIDs in both repos."""
        import re
        from ipfs_datasets_py.mcp_server.cid_artifacts import artifact_cid
        from ipfs_datasets_py.mcp_server.interface_descriptor import cids_equivalent
        mod = _load_acc_module("cid_ucan", "cid_ucan.py")
        cid_pat = re.compile(r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|baf[a-z0-9]{56})$")
        data = {"query": "hello", "n": 1}
        acc_cid = mod.compute_cid(data)
        ds_cid = str(artifact_cid(data))
        # Both conform to the canonical MCP++ CID regex...
        assert cid_pat.match(acc_cid), acc_cid
        assert cid_pat.match(ds_cid), ds_cid
        # ...and are byte-identical for identical content (true interop)
        assert acc_cid == ds_cid
        assert mod.cids_equivalent(acc_cid, ds_cid)
        assert cids_equivalent(acc_cid, ds_cid)


class TestProfileCInterop:
    """Profile C: UCAN delegation chains are compatible across repos."""

    def test_datasets_delegation(self):
        from ipfs_datasets_py.mcp_server.ucan_delegation import (
            Delegation, Capability, DelegationEvaluator,
        )
        evaluator = DelegationEvaluator()
        d = Delegation(
            cid="test-cid-123",
            issuer="did:key:zAlice",
            audience="did:key:zBob",
            capabilities=[Capability(resource="mcp://tool/search", ability="invoke")],
            expiry=time.time() + 3600,
        )
        evaluator.add(d)
        ok, reason = evaluator.can_invoke(
            "test-cid-123", "mcp://tool/search", "invoke"
        )
        assert ok is True

    def test_accelerate_delegation(self):
        mod = _load_acc_module("cid_ucan", "cid_ucan.py")
        evaluator = mod.DelegationEvaluator()
        d = mod.Delegation(
            issuer="did:key:zAlice",
            audience="did:key:zBob",
            capabilities=[mod.Capability(resource="mcp://tool/infer", ability="invoke")],
            expiry=time.time() + 3600,
        )
        evaluator.add(d)
        ok, reason = evaluator.can_invoke(d.cid, "mcp://tool/infer", "invoke")
        assert ok is True

    def test_cross_repo_resource_format(self):
        """Both repos use mcp://tool/{name} resource format."""
        from ipfs_datasets_py.mcp_server.ucan_delegation import Capability as DsCap
        acc_mod = _load_acc_module("cid_ucan", "cid_ucan.py")

        ds_cap = DsCap(resource="mcp://tool/search", ability="invoke")
        acc_cap = acc_mod.Capability(resource="mcp://tool/search", ability="invoke")

        assert ds_cap.matches("mcp://tool/search", "invoke")
        assert acc_cap.covers("mcp://tool/search", "invoke")


class TestProfileDInterop:
    """Profile D: Temporal policy evaluation works in both repos."""

    def test_datasets_policy_evaluation(self):
        from ipfs_datasets_py.mcp_server.temporal_policy import (
            PolicyEvaluator, PolicyObject, PolicyClause, make_simple_permission_policy,
        )
        policy = make_simple_permission_policy("alice", "search")
        evaluator = PolicyEvaluator()
        evaluator.register_policy(policy)
        # The datasets evaluator needs an IntentObject
        from ipfs_datasets_py.mcp_server.cid_artifacts import IntentObject, artifact_cid
        intent = IntentObject(
            interface_cid="bafy-test", tool="search",
            input_cid=str(artifact_cid({"q": "test"})),
        )
        decision = evaluator.evaluate(intent, policy, actor="alice")
        assert decision.decision == "allow"

    def test_accelerate_policy_evaluation(self):
        mod = _load_acc_module("temporal_policy", "temporal_policy.py")
        policy = mod.make_permission_policy("test", "alice", ["infer", "run_model"])
        evaluator = mod.PolicyEvaluator()
        evaluator.register(policy)
        decision = evaluator.evaluate("infer", actor="alice", policy_cid=policy.cid)
        assert decision.allowed is True
        assert decision.verdict == "allow"

    def test_accelerate_prohibition(self):
        mod = _load_acc_module("temporal_policy", "temporal_policy.py")
        evaluator = mod.PolicyEvaluator()
        evaluator.register(mod.make_permission_policy("allow-all", "*", ["*"]))
        evaluator.register(mod.make_prohibition_policy("block-delete", actions=["delete_model"]))
        decision = evaluator.evaluate("delete_model", actor="anyone")
        assert decision.allowed is False


class TestProfileEInterop:
    """Profile E: P2P wire format is compatible across repos."""

    def test_datasets_p2p_message_format(self):
        from ipfs_datasets_py.mcp_server.p2p_libp2p_transport import P2PMessage
        msg = P2PMessage(
            msg_type="request", method="search",
            params={"query": "IPFS datasets"}, msg_id="req_1",
        )
        encoded = msg.encode()
        decoded = P2PMessage.decode(encoded)
        assert decoded.method == "search"
        assert decoded.params == {"query": "IPFS datasets"}

    def test_accelerate_p2p_message_format(self):
        mod = _load_acc_module("p2p_transport", "p2p_transport.py")
        msg = mod.P2PMessage(
            msg_type="request", method="infer",
            params={"model": "bert"}, msg_id="req_2",
        )
        encoded = msg.encode()
        decoded = mod.P2PMessage.decode(encoded)
        assert decoded.method == "infer"
        assert decoded.params == {"model": "bert"}

    def test_cross_repo_wire_compatibility(self):
        """Messages encoded by one repo can be decoded by the other."""
        from ipfs_datasets_py.mcp_server.p2p_libp2p_transport import P2PMessage as DsMsg
        acc_mod = _load_acc_module("p2p_transport", "p2p_transport.py")
        AccMsg = acc_mod.P2PMessage

        # Datasets encodes, Accelerate decodes
        ds_msg = DsMsg(msg_type="request", method="search", params={"q": "test"}, msg_id="x1")
        encoded = ds_msg.encode()
        acc_decoded = AccMsg.decode(encoded)
        assert acc_decoded.method == "search"
        assert acc_decoded.params == {"q": "test"}

        # Accelerate encodes, Datasets decodes
        acc_msg = AccMsg(msg_type="response", method="infer", result={"output": "hello"}, msg_id="x2")
        encoded2 = acc_msg.encode()
        ds_decoded = DsMsg.decode(encoded2)
        assert ds_decoded.result == {"output": "hello"}
        assert ds_decoded.msg_type == "response"

    def test_protocol_id_matches(self):
        from ipfs_datasets_py.mcp_server.p2p_libp2p_transport import MCP_P2P_PROTOCOL as ds_proto
        acc_mod = _load_acc_module("p2p_transport", "p2p_transport.py")
        acc_proto = acc_mod.MCP_P2P_PROTOCOL
        assert ds_proto == acc_proto == "/mcp+p2p/1.0.0"


class TestDispatchPipeline:
    """Test that the dispatch pipeline enforces UCAN + Policy."""

    def test_full_pipeline_with_delegation(self):
        from ipfs_datasets_py.mcp_server.dispatch_pipeline import make_full_pipeline
        pipeline = make_full_pipeline()
        # Without leaf_cid, delegation stage should pass
        result = pipeline.run({"tool": "search", "actor": "alice"})
        assert result.allowed is True

    def test_full_pipeline_missing_tool(self):
        from ipfs_datasets_py.mcp_server.dispatch_pipeline import make_full_pipeline
        pipeline = make_full_pipeline()
        result = pipeline.run({"tool": "", "actor": "alice"})
        assert result.allowed is False


class TestSpecConformance:
    """Both servers' Profile A descriptors validate against the canonical
    Mcp-Plus-Plus spec so third parties can interoperate."""

    @staticmethod
    def _spec_model():
        spec_dir = os.path.join(_ext_dir, "Mcp-Plus-Plus", "tests-py")
        if spec_dir not in sys.path:
            sys.path.insert(0, spec_dir)
        from validators.models import InterfaceDescriptor as Spec
        return Spec

    def test_accelerate_descriptor_conforms_to_spec(self):
        Spec = self._spec_model()
        mod = _load_acc_module("interface_descriptor", "interface_descriptor.py")
        iface = mod.InterfaceDescriptor(
            name="conf", namespace="acc", version="1.0.0",
            methods=[mod.MethodDescriptor(name="infer")], tags=["ml"],
        )
        Spec(**iface.to_dict())  # raises if non-conformant

    def test_datasets_descriptor_conforms_to_spec(self):
        Spec = self._spec_model()
        from ipfs_datasets_py.mcp_server.interface_descriptor import (
            InterfaceDescriptor, MethodSignature,
        )
        iface = InterfaceDescriptor(
            name="conf", namespace="ds", version="1.0.0",
            methods=[MethodSignature(name="load")],
        )
        Spec(**iface.to_dict())  # raises if non-conformant

    def test_dag_event_wire_shapes_conform(self):
        spec_dir = os.path.join(_ext_dir, "Mcp-Plus-Plus", "tests-py")
        if spec_dir not in sys.path:
            sys.path.insert(0, spec_dir)
        from validators.models import DAGEvent
        c = "bafkreifxone36h5jwjwulvkf27le3lmwon7jz65tzo27luipw55q7tcevu"
        # accelerate-style: epoch float timestamp, generic payload
        DAGEvent.model_validate({"event_cid": c, "event_type": "envelope",
                                 "parents": [], "timestamp": 1782680000.0,
                                 "payload": {"method": "infer"}})
        # datasets-style: ISO timestamp, CID-bundle payload
        DAGEvent.model_validate({"event_cid": c, "event_type": "envelope",
                                 "parents": [], "timestamp": "2026-06-28T00:00:00Z",
                                 "payload": {"intent_cid": c, "receipt_cid": c}})

    def test_delegation_wire_shapes_conform(self):
        spec_dir = os.path.join(_ext_dir, "Mcp-Plus-Plus", "tests-py")
        if spec_dir not in sys.path:
            sys.path.insert(0, spec_dir)
        from validators.models import Delegation
        c = "bafkreifxone36h5jwjwulvkf27le3lmwon7jz65tzo27luipw55q7tcevu"
        # accelerate-style: full-name fields, single proof_cid, signed
        Delegation.model_validate({"cid": c, "issuer": "did:key:zAlice",
                                   "audience": "did:key:zBob",
                                   "capabilities": [{"resource": "mcp://tool/infer", "ability": "invoke"}],
                                   "expiry": 1782680000, "proof_cid": c, "signature": "s"})
        # datasets-style: full-name fields, proof bundle CID
        Delegation.model_validate({"cid": c, "issuer": "did:key:zAlice",
                                   "audience": "did:key:zBob",
                                   "capabilities": [{"resource": "mcp://tool/search", "ability": "invoke"}],
                                   "expiry": 1782680000, "proof_cid": c})
