"""Cross-repo single-source guard.

The swissknife dashboard manifest must equal the ipfs_kit_py MCP++ server's
generated registry, so the four surfaces (python/cli/mcp/js dashboard) cannot
drift. Fails CI if either repo is regenerated without resyncing the other.
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
    assert dashboard == server, (
        "swissknife dashboard manifest drifted; run generate.render_manifest() "
        "in ipfs_kit and resync swissknife src/services/ipfs/mcp-ipfs-kit-tools-manifest.json"
    )
