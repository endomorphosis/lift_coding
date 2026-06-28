"""Tests for ipfs_accelerate_py MCP++ CID-native execution and UCAN delegation.

Verifies Profile B (CID artifacts, Event DAG) and Profile C (UCAN delegation chain
with signature verification) implementations.
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'ipfs_accelerate'))


class TestCIDComputation:
    """Test CID computation utility."""

    def test_compute_cid_deterministic(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import compute_cid
        cid1 = compute_cid({"hello": "world"})
        cid2 = compute_cid({"hello": "world"})
        assert cid1 == cid2
        assert cid1.startswith("bafy")

    def test_compute_cid_different_data(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import compute_cid
        cid1 = compute_cid({"a": 1})
        cid2 = compute_cid({"a": 2})
        assert cid1 != cid2


class TestProfileB:
    """Test CID-Native Execution (Profile B)."""

    def test_intent_object_creation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import IntentObject
        intent = IntentObject(method="run_model", params={"model": "bert"})
        assert intent.cid.startswith("bafy")
        assert intent.method == "run_model"
        assert intent.params == {"model": "bert"}

    def test_decision_object_creation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import DecisionObject
        decision = DecisionObject(intent_cid="bafy123", authorized=True, reason="open_access")
        assert decision.cid.startswith("bafy")
        assert decision.authorized is True

    def test_receipt_object_creation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import ReceiptObject
        receipt = ReceiptObject(intent_cid="bafy1", decision_cid="bafy2", result={"output": "hello"})
        assert receipt.success is True
        assert receipt.result == {"output": "hello"}

    def test_receipt_with_error(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import ReceiptObject
        receipt = ReceiptObject(intent_cid="bafy1", decision_cid="bafy2", error="timeout")
        assert receipt.success is False

    def test_execution_envelope(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import IntentObject, DecisionObject, ReceiptObject, ExecutionEnvelope
        intent = IntentObject(method="infer", params={})
        decision = DecisionObject(intent_cid=intent.cid, authorized=True)
        receipt = ReceiptObject(intent_cid=intent.cid, decision_cid=decision.cid, result="ok")
        envelope = ExecutionEnvelope(intent=intent, decision=decision, receipt=receipt)
        assert envelope.cid.startswith("bafy")
        d = envelope.to_dict()
        assert d["intent"]["method"] == "infer"
        assert d["decision"]["authorized"] is True
        assert d["receipt"]["result"] == "ok"

    def test_event_dag_append_and_frontier(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import EventDAG, DAGEvent
        dag = EventDAG()
        e1 = DAGEvent(cid="cid1", event_type="intent")
        e2 = DAGEvent(cid="cid2", event_type="decision", parent_cids=["cid1"])
        dag.append(e1)
        dag.append(e2)
        frontier = dag.frontier()
        assert len(frontier) == 1
        assert frontier[0].cid == "cid2"

    def test_event_dag_provenance(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import EventDAG, DAGEvent
        dag = EventDAG()
        dag.append(DAGEvent(cid="root", event_type="intent"))
        dag.append(DAGEvent(cid="mid", event_type="decision", parent_cids=["root"]))
        dag.append(DAGEvent(cid="leaf", event_type="receipt", parent_cids=["mid"]))
        chain = dag.provenance("leaf")
        cids = [e.cid for e in chain]
        assert "leaf" in cids
        assert "mid" in cids
        assert "root" in cids


class TestProfileC:
    """Test UCAN Delegation (Profile C)."""

    def test_capability_covers(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import Capability
        cap = Capability(resource="mcp://tool/run_model", ability="invoke")
        assert cap.covers("mcp://tool/run_model", "invoke") is True
        assert cap.covers("mcp://tool/run_model", "read") is False
        assert cap.covers("mcp://tool/other", "invoke") is False

    def test_capability_wildcard(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import Capability
        cap = Capability(resource="*", ability="*")
        assert cap.covers("mcp://tool/anything", "invoke") is True

    def test_delegation_creation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import Delegation, Capability
        d = Delegation(
            issuer="did:key:z123",
            audience="did:key:z456",
            capabilities=[Capability(resource="mcp://tool/*", ability="invoke")],
            expiry=time.time() + 3600,
        )
        assert d.cid.startswith("bafy")
        assert d.is_expired() is False
        assert d.has_capability("mcp://tool/run_model", "invoke") is True

    def test_delegation_expired(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import Delegation
        d = Delegation(issuer="a", audience="b", expiry=time.time() - 100)
        assert d.is_expired() is True

    def test_evaluator_can_invoke(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import DelegationEvaluator, Delegation, Capability
        evaluator = DelegationEvaluator()
        d = Delegation(
            issuer="did:key:root",
            audience="did:key:user",
            capabilities=[Capability(resource="mcp://tool/infer", ability="invoke")],
            expiry=time.time() + 3600,
        )
        evaluator.add(d)
        ok, reason = evaluator.can_invoke(d.cid, "mcp://tool/infer", "invoke")
        assert ok is True
        assert reason == "authorized"

    def test_evaluator_denies_wrong_resource(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import DelegationEvaluator, Delegation, Capability
        evaluator = DelegationEvaluator()
        d = Delegation(
            issuer="did:key:root",
            audience="did:key:user",
            capabilities=[Capability(resource="mcp://tool/infer", ability="invoke")],
        )
        evaluator.add(d)
        ok, reason = evaluator.can_invoke(d.cid, "mcp://tool/other", "invoke")
        assert ok is False

    def test_evaluator_revocation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import DelegationEvaluator, Delegation, Capability
        evaluator = DelegationEvaluator()
        d = Delegation(
            issuer="did:key:root",
            audience="did:key:user",
            capabilities=[Capability(resource="*", ability="*")],
        )
        evaluator.add(d)
        evaluator.revoke(d.cid)
        ok, reason = evaluator.can_invoke(d.cid, "mcp://tool/infer", "invoke")
        assert ok is False
        assert "revoked" in reason

    def test_delegation_chain(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import DelegationEvaluator, Delegation, Capability
        evaluator = DelegationEvaluator()
        root = Delegation(
            issuer="did:key:root",
            audience="did:key:mid",
            capabilities=[Capability(resource="mcp://tool/*", ability="*")],
        )
        leaf = Delegation(
            issuer="did:key:mid",
            audience="did:key:user",
            capabilities=[Capability(resource="mcp://tool/infer", ability="invoke")],
            proof_cids=[root.cid],
        )
        evaluator.add(root)
        evaluator.add(leaf)
        ok, reason = evaluator.can_invoke(leaf.cid, "mcp://tool/infer", "invoke", actor="did:key:user")
        assert ok is True


class TestExecuteWithEnvelope:
    """Test high-level execute_with_envelope helper."""

    @pytest.mark.asyncio
    async def test_execute_open_access(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import execute_with_envelope

        async def mock_executor(method, params):
            return {"result": f"executed {method}"}

        envelope = await execute_with_envelope(
            method="run_model", params={"model": "bert"},
            executor_fn=mock_executor,
        )
        assert envelope.receipt.success is True
        assert envelope.receipt.result == {"result": "executed run_model"}
        assert envelope.decision.authorized is True

    @pytest.mark.asyncio
    async def test_execute_unauthorized(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import execute_with_envelope

        # Using a non-existent delegation CID should fail
        envelope = await execute_with_envelope(
            method="run_model", params={},
            delegation_cid="nonexistent_cid",
            executor_fn=lambda m, p: None,
        )
        assert envelope.receipt.success is False
        assert "Unauthorized" in (envelope.receipt.error or "")

    @pytest.mark.asyncio
    async def test_execute_with_valid_delegation(self):
        from ipfs_accelerate_py.mcplusplus_module.cid_ucan import (
            execute_with_envelope, Delegation, Capability, get_evaluator,
        )

        evaluator = get_evaluator()
        d = Delegation(
            issuer="did:key:root",
            audience="did:key:user",
            capabilities=[Capability(resource="mcp://tool/run_model", ability="invoke")],
        )
        evaluator.add(d)

        async def mock_executor(method, params):
            return "success"

        envelope = await execute_with_envelope(
            method="run_model", params={},
            requester="did:key:user",
            delegation_cid=d.cid,
            executor_fn=mock_executor,
        )
        assert envelope.receipt.success is True
        assert envelope.receipt.result == "success"
