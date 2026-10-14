"""B4: live two-host MCP++ session over real py-libp2p (loopback).

Two MCPp2pNode hosts from ipfs_accelerate_py.mcplusplus_module (the repos'
own Profile E transport) are started on 127.0.0.1 with ephemeral ports.
The client connects to the server through the node's own bootstrap-connect
path, then, over the /mcp+p2p/1.0.0 stream protocol:

  1. requests the server's interface descriptor (Profile A descriptor,
     CID-addressed, built with the repo's interface_descriptor module);
  2. calls a tool ("tools/call") presenting a UCAN delegation minted with
     the repo's cid_ucan module — the server evaluates it with
     DelegationEvaluator.can_invoke before executing and returns an
     execution receipt (ReceiptObject CID);
  3. negative controls: a delegation for the wrong resource, and a call
     with no delegation, must both be refused by the server.

Evidence is written to p2p-session-evidence.json next to this script.
This is a same-machine two-host session: real libp2p transport (TCP +
Noise + yamux via py-libp2p), not a mock and not an in-process call.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MCPPP_P2P_MDNS", "0")

import trio  # noqa: E402

from ipfs_accelerate_py.mcplusplus_module.cid_ucan import (  # noqa: E402
    Capability,
    Delegation,
    DelegationEvaluator,
    ReceiptObject,
)
from ipfs_accelerate_py.mcplusplus_module.interface_descriptor import (  # noqa: E402
    InterfaceDescriptor,
    MethodDescriptor,
)
from ipfs_accelerate_py.mcplusplus_module.p2p_transport import (  # noqa: E402
    MCP_P2P_PROTOCOL,
    MCPp2pNode,
)

HERE = Path(__file__).resolve().parent
EVIDENCE_PATH = HERE / "p2p-session-evidence.json"

DESCRIPTOR = InterfaceDescriptor(
    name="gap-pass-echo-service",
    namespace="mcp++",
    version="1.0.0",
    description="Echo tool service used for the live two-host Profile E session.",
    methods=[
        MethodDescriptor(
            name="mcp/interface",
            description="Return this service's interface descriptor.",
            output_schema={"type": "object"},
        ),
        MethodDescriptor(
            name="tools/call",
            description="Invoke a tool with a UCAN delegation.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"},
                    "delegation": {"type": "object"},
                },
                "required": ["name", "delegation"],
            },
            output_schema={"type": "object"},
        ),
    ],
)


def build_evaluator() -> DelegationEvaluator:
    return DelegationEvaluator()


async def main() -> dict:
    evidence: dict = {
        "session": "two-host loopback libp2p, MCPp2pNode (ipfs_accelerate_py.mcplusplus_module)",
        "protocol": MCP_P2P_PROTOCOL,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    evaluator = build_evaluator()
    server_state: dict = {}

    async def server_handler(method: str, params: dict):
        if method == "mcp/interface":
            return {
                "descriptor": DESCRIPTOR.to_dict(),
                "protocol": MCP_P2P_PROTOCOL,
                "peer_id": server_state["peer_id"],
            }
        if method == "tools/call":
            raw = params.get("delegation")
            if not raw:
                raise RuntimeError("delegation required")
            delegation = Delegation(
                issuer=raw["issuer"],
                audience=raw["audience"],
                capabilities=[
                    Capability(resource=c["resource"], ability=c["ability"])
                    for c in raw.get("capabilities", [])
                ],
                expiry=raw.get("expiry", 0),
                not_before=raw.get("not_before", 0),
                proof_cids=raw.get("proof_cids", []),
                cid=raw.get("cid", ""),
            )
            evaluator.add(delegation)
            resource = f"tools/{params.get('name', '')}"
            authorized, reason = evaluator.can_invoke(
                delegation.cid, resource, "invoke", actor=delegation.audience
            )
            if not authorized:
                raise RuntimeError(f"UCAN delegation refused: {reason}")
            result = {
                "echo": params.get("arguments", {}),
                "served_by": server_state["peer_id"],
                "sender_peer_id": params.get("_sender_peer_id", ""),
            }
            receipt = ReceiptObject(
                intent_cid=delegation.cid,
                decision_cid=delegation.cid,
                result=result,
                executor=server_state["peer_id"],
            )
            return {
                "result": result,
                "authorized": authorized,
                "authorization_reason": reason,
                "delegation_cid": delegation.cid,
                "receipt_cid": receipt.cid,
                "output_cid": receipt.output_cid,
            }
        raise RuntimeError(f"unknown method {method}")

    async with trio.open_nursery() as nursery:
        server = MCPp2pNode(listen_addrs=["/ip4/127.0.0.1/tcp/0"], bootstrap_peers=[])
        server.set_tool_handler(server_handler)
        await server.start(nursery)
        server_state["peer_id"] = server.peer_id
        evidence["server"] = {
            "peer_id": server.peer_id,
            "multiaddrs": server.multiaddrs,
            "operational": bool(getattr(server, "_operational", False)),
        }

        client = MCPp2pNode(listen_addrs=["/ip4/127.0.0.1/tcp/0"], bootstrap_peers=[])
        await client.start(nursery)
        evidence["client"] = {
            "peer_id": client.peer_id,
            "multiaddrs": client.multiaddrs,
            "operational": bool(getattr(client, "_operational", False)),
        }

        # The host's listen registration can land just after start()
        # returns; poll briefly for the bound addresses.
        for _ in range(120):
            if server.multiaddrs:
                break
            await trio.sleep(0.25)
        evidence["server"]["multiaddrs_after_poll"] = server.multiaddrs
        server_addr = server.multiaddrs[0]
        if "/p2p/" not in server_addr:
            server_addr = f"{server_addr}/p2p/{server.peer_id}"
        evidence["dial_addr"] = server_addr
        connected = await client._connect_bootstrap(server_addr)
        evidence["connected"] = bool(connected)
        evidence["client_connected_peers"] = [p.peer_id for p in client.connected_peers]
        if not connected:
            raise RuntimeError("client could not connect to server")

        # 1) Descriptor exchange over the wire.
        descriptor_reply = await client.call_tool(server.peer_id, "mcp/interface", {})
        evidence["descriptor"] = descriptor_reply["descriptor"]
        evidence["descriptor_cid"] = descriptor_reply["descriptor"]["cid"]

        # 2) UCAN-gated tool call.
        client_did = f"did:p2p:{client.peer_id}"
        server_did = f"did:p2p:{server.peer_id}"
        delegation = Delegation(
            issuer=server_did,
            audience=client_did,
            capabilities=[Capability(resource="tools/echo", ability="invoke")],
            expiry=time.time() + 600,
        )
        evidence["delegation"] = delegation.to_dict()
        tool_reply = await client.call_tool(
            server.peer_id,
            "tools/call",
            {
                "name": "echo",
                "arguments": {"message": "hello over real libp2p"},
                "delegation": delegation.to_dict(),
            },
        )
        evidence["tool_call"] = tool_reply

        # 3a) Negative control: delegation for the wrong resource.
        wrong = Delegation(
            issuer=server_did,
            audience=client_did,
            capabilities=[Capability(resource="tools/other", ability="invoke")],
            expiry=time.time() + 600,
        )
        try:
            await client.call_tool(
                server.peer_id,
                "tools/call",
                {"name": "echo", "arguments": {}, "delegation": wrong.to_dict()},
            )
            evidence["negative_control_wrong_resource"] = {"refused": False}
        except RuntimeError as error:
            evidence["negative_control_wrong_resource"] = {
                "refused": True,
                "error": str(error),
            }

        # 3b) Negative control: no delegation at all.
        try:
            await client.call_tool(server.peer_id, "tools/call", {"name": "echo", "arguments": {}})
            evidence["negative_control_no_delegation"] = {"refused": False}
        except RuntimeError as error:
            evidence["negative_control_no_delegation"] = {
                "refused": True,
                "error": str(error),
            }

        await client.stop()
        await server.stop()
        nursery.cancel_scope.cancel()

    evidence["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return evidence


if __name__ == "__main__":
    result = trio.run(main)
    EVIDENCE_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "connected": result["connected"],
        "descriptor_cid": result["descriptor_cid"],
        "tool_authorized": result["tool_call"]["authorized"],
        "receipt_cid": result["tool_call"]["receipt_cid"],
        "wrong_resource_refused": result["negative_control_wrong_resource"]["refused"],
        "no_delegation_refused": result["negative_control_no_delegation"]["refused"],
    }, indent=2))
    sys.exit(0)
