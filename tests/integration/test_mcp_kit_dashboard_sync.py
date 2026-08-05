"""Cross-repo single-source guard.

SwissKnife dashboard tools must not invent entries outside the ipfs_kit_py
MCP++ server registry. Server may be ahead of the checked-in dashboard pin;
that is reported as residual drift without failing the required gate.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))


def test_dashboard_manifest_matches_server_registry():
    from ipfs_kit_py.mcp_server.js_sdk import generate

    candidates = [
        ROOT / "swissknife" / "src" / "services" / "ipfs" / "mcp-ipfs-kit-tools-manifest.json",
        ROOT / "swissknife" / "src" / "services" / "mcp-ipfs-kit-tools-manifest.json",
    ]
    dash = next((path for path in candidates if path.exists()), None)
    assert dash is not None, f"dashboard manifest missing; tried {candidates}"
    server = json.loads(generate.render_manifest())
    dashboard = json.loads(dash.read_text())

    server_tools = server.get("tools") or []
    dashboard_tools = dashboard.get("tools") or []
    assert server_tools, "server registry produced no tools"
    assert dashboard_tools, "dashboard manifest has no tools"

    server_names = {tool.get("name") for tool in server_tools if isinstance(tool, dict)}
    dashboard_names = {tool.get("name") for tool in dashboard_tools if isinstance(tool, dict)}
    extra = sorted(name for name in dashboard_names if name not in server_names)
    assert not extra, f"dashboard has tools not in server registry: {extra}"
    # Required coverage: dashboard still lists a substantial shared surface.
    overlap = server_names & dashboard_names
    assert len(overlap) >= min(20, len(server_names)), (
        f"dashboard/server tool overlap too small: {len(overlap)}"
    )
    missing = sorted(server_names - dashboard_names)
    if missing:
        print(f"note: server ahead of dashboard pin; missing tools: {missing}")
