"""Debug: reproduce the invoke-mcp-libp2p.py session steps with full errors."""
import sys, traceback
sys.path.insert(0, "/home/hatch/workspace/lift_coding/swissknife/scripts")
sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_accelerate")
from ipfs_accelerate_py.mcplusplus_module.p2p.libp2p_runtime import patch_libp2p_compatibility
patch_libp2p_compatibility()

import trio
import importlib.util
spec = importlib.util.spec_from_file_location("helper", "/home/hatch/workspace/lift_coding/swissknife/scripts/invoke-mcp-libp2p.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

ADDR = "/ip4/127.0.0.1/tcp/9114/p2p/12D3KooWH7VkctUeKnWt5nWHmHRGuuf457Ls3MeUzyz5VKTTSPfY"

async def main():
    async with helper.libp2p_client_host() as host:
        print("client host up:", host.get_id())
        stream = await helper.open_profile_e_stream(host, ADDR)
        print("stream open")
        client = helper.ProfileEJsonRpcClient(stream)
        init = await client.request("initialize", {
            "protocolVersion": helper.MCP_PROTOCOL_VERSION,
            "capabilities": {"experimental": {"mcp++/mcp-idl": True, "mcp++/cid-envelope": True, "mcp++/ucan": True, "mcp++/event-dag": True, "mcp++/p2p-transport": True}},
            "clientInfo": {"name": "debug", "version": "1.0.0"},
        })
        print("initialize ok:", str(init.get("result"))[:200])
        ifaces = await client.request("interfaces/list", {})
        print("interfaces ok:", str(ifaces.get("result"))[:200])
        ident = await client.request("mcp++/ucan/identity", {
            "audience": "did:key:z6MkvAUPBCMQzakz16QeKSg68XSeewjGUvpzUjxQGD33qwKu",
            "nonce": "audit2-manual-nonce-0003",
            "transport": "libp2p",
        })
        print("identity ok:", str(ident.get("result"))[:200])
        call = await client.request("tools/call", {"name": "node_id", "arguments": {"scope": "audit2.manual", "limit": 1}})
        print("tools/call ok:", str(call.get("result"))[:300])
        await client.close()

try:
    trio.run(main)
except BaseException:
    traceback.print_exc()
    # ExceptionGroup: print sub-exceptions
    pass #
    def walk(e, depth=0):
        print("  " * depth, type(e).__name__, str(e)[:300])
        for sub in getattr(e, "exceptions", []):
            walk(sub, depth + 1)
    walk(sys.exc_info()[1])
