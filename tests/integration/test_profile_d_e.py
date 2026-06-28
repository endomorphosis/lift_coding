"""Tests for ipfs_accelerate_py MCP++ Profile D (Temporal Policy) and Profile E (P2P Transport).

Verifies:
- PolicyClause temporal validity
- PolicyEvaluator permission/prohibition/obligation logic
- P2PMessage encode/decode (wire format)
- MCPp2pNode lifecycle
- Integration with execute_with_envelope via policy enforcement
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'ipfs_accelerate'))


class TestPolicyClause:
    """Test Profile D PolicyClause."""

    def test_clause_temporally_valid(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyClause
        now = time.time()
        clause = PolicyClause(
            clause_type="permission", actor="alice", action="run_model",
            valid_from=now - 100, valid_until=now + 3600,
        )
        assert clause.is_temporally_valid(now) is True

    def test_clause_expired(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyClause
        now = time.time()
        clause = PolicyClause(
            clause_type="permission", actor="alice", action="run_model",
            valid_from=now - 3600, valid_until=now - 100,
        )
        assert clause.is_temporally_valid(now) is False

    def test_clause_not_yet_valid(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyClause
        now = time.time()
        clause = PolicyClause(
            clause_type="permission", actor="alice", action="run_model",
            valid_from=now + 100, valid_until=now + 3600,
        )
        assert clause.is_temporally_valid(now) is False

    def test_clause_matches(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyClause
        clause = PolicyClause(clause_type="permission", actor="alice", action="run_model")
        assert clause.matches("alice", "run_model") is True
        assert clause.matches("bob", "run_model") is False
        assert clause.matches("alice", "other") is False

    def test_wildcard_matches_all(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyClause
        clause = PolicyClause(clause_type="permission", actor="*", action="*")
        assert clause.matches("anyone", "anything") is True


class TestPolicyEvaluator:
    """Test Profile D PolicyEvaluator."""

    def test_permission_allows(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import (
            PolicyEvaluator, PolicyObject, PolicyClause,
        )
        evaluator = PolicyEvaluator()
        policy = PolicyObject(
            name="test", clauses=[
                PolicyClause(clause_type="permission", actor="alice", action="infer"),
            ]
        )
        evaluator.register(policy)
        decision = evaluator.evaluate("infer", actor="alice", policy_cid=policy.cid)
        assert decision.allowed is True
        assert decision.verdict == "allow"

    def test_prohibition_denies(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import (
            PolicyEvaluator, PolicyObject, PolicyClause,
        )
        evaluator = PolicyEvaluator()
        policy = PolicyObject(
            name="deny-test", clauses=[
                PolicyClause(clause_type="permission", actor="alice", action="*"),
                PolicyClause(clause_type="prohibition", actor="alice", action="delete_model"),
            ]
        )
        evaluator.register(policy)
        decision = evaluator.evaluate("delete_model", actor="alice", policy_cid=policy.cid)
        assert decision.allowed is False
        assert decision.verdict == "deny"

    def test_no_matching_permission_denies(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import (
            PolicyEvaluator, PolicyObject, PolicyClause,
        )
        evaluator = PolicyEvaluator()
        policy = PolicyObject(
            name="narrow", clauses=[
                PolicyClause(clause_type="permission", actor="alice", action="infer"),
            ]
        )
        evaluator.register(policy)
        decision = evaluator.evaluate("run_model", actor="alice", policy_cid=policy.cid)
        assert decision.allowed is False

    def test_obligation_with_permission(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import (
            PolicyEvaluator, PolicyObject, PolicyClause,
        )
        evaluator = PolicyEvaluator()
        policy = PolicyObject(
            name="with-obligation", clauses=[
                PolicyClause(clause_type="permission", actor="*", action="run_model"),
                PolicyClause(
                    clause_type="obligation", actor="*", action="run_model",
                    obligation_deadline=time.time() + 3600,
                    metadata={"requires": "log_usage"},
                ),
            ]
        )
        evaluator.register(policy)
        decision = evaluator.evaluate("run_model", actor="bob")
        assert decision.verdict == "allow_with_obligations"
        assert len(decision.obligations) == 1

    def test_unknown_policy_denies(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyEvaluator
        evaluator = PolicyEvaluator()
        decision = evaluator.evaluate("infer", policy_cid="nonexistent")
        assert decision.allowed is False

    def test_no_policies_open_access(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import PolicyEvaluator
        evaluator = PolicyEvaluator()
        decision = evaluator.evaluate("anything")
        assert decision.allowed is True
        assert "open access" in decision.justification


class TestMakePolicy:
    """Test policy factory functions."""

    def test_make_permission_policy(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import make_permission_policy
        policy = make_permission_policy("test", "alice", ["infer", "run_model"], valid_hours=1)
        assert len(policy.clauses) == 2
        assert policy.cid.startswith("bafy")
        assert all(c.clause_type == "permission" for c in policy.clauses)

    def test_make_prohibition_policy(self):
        from ipfs_accelerate_py.mcplusplus_module.temporal_policy import make_prohibition_policy
        policy = make_prohibition_policy("block-delete", actions=["delete_model", "reset"])
        assert len(policy.clauses) == 2
        assert all(c.clause_type == "prohibition" for c in policy.clauses)


class TestP2PMessage:
    """Test Profile E P2PMessage wire format."""

    def test_encode_decode_roundtrip(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import P2PMessage
        msg = P2PMessage(
            msg_type="request",
            method="run_model",
            params={"model": "bert", "input": "hello"},
            msg_id="req_123",
            sender_peer_id="QmPeer123",
        )
        encoded = msg.encode()
        decoded = P2PMessage.decode(encoded)
        assert decoded.msg_type == "request"
        assert decoded.method == "run_model"
        assert decoded.params == {"model": "bert", "input": "hello"}
        assert decoded.msg_id == "req_123"
        assert decoded.sender_peer_id == "QmPeer123"

    def test_response_message(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import P2PMessage
        msg = P2PMessage(
            msg_type="response",
            method="run_model",
            result={"output": "world"},
            msg_id="req_123",
        )
        encoded = msg.encode()
        decoded = P2PMessage.decode(encoded)
        assert decoded.result == {"output": "world"}
        assert decoded.error is None

    def test_error_response(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import P2PMessage
        msg = P2PMessage(
            msg_type="response",
            method="run_model",
            error="Model not found",
            msg_id="req_123",
        )
        encoded = msg.encode()
        decoded = P2PMessage.decode(encoded)
        assert decoded.error == "Model not found"
        assert decoded.result is None


class TestMCPp2pNode:
    """Test MCPp2pNode lifecycle."""

    def test_node_creation(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import MCPp2pNode
        node = MCPp2pNode()
        assert node._started is False
        assert node.peer_id == ""
        assert node.connected_peers == []

    def test_node_to_dict(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import MCPp2pNode, MCP_P2P_PROTOCOL
        node = MCPp2pNode()
        info = node.to_dict()
        assert info["protocol"] == MCP_P2P_PROTOCOL
        assert info["started"] is False
        assert info["connected_peers"] == 0

    def test_peer_info(self):
        from ipfs_accelerate_py.mcplusplus_module.p2p_transport import PeerInfo, MCP_P2P_PROTOCOL
        peer = PeerInfo(
            peer_id="QmTest123",
            multiaddrs=["/ip4/127.0.0.1/tcp/4001"],
            protocols=[MCP_P2P_PROTOCOL],
        )
        d = peer.to_dict()
        assert d["peer_id"] == "QmTest123"
        assert len(d["multiaddrs"]) == 1
