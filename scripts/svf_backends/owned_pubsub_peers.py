"""Read the root-owned pubsub peer registry. This module never starts or controls daemons."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path("config/swissknife_visual_functional_pubsub.json")
SCHEMA = "swissknife.owned-pubsub-peers.v1"
SCOPES = ("svf-pubsub-043", "svf-p2p-chat-g030", "svf-p2p-chat-classic")


def load_owned_pubsub(root: Path) -> dict:
    root = Path(root).resolve()
    path = (root / CONFIG).resolve()
    if not path.is_relative_to(root):
        raise ValueError("pubsub_config_path_invalid")
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict or value.get("schema") != SCHEMA or value.get("owner") != "swissknife_visual_functional":
        raise ValueError("pubsub_config_invalid")
    if value.get("allowed_fixture_scopes") != list(SCOPES):
        raise ValueError("pubsub_scope_registry_invalid")
    peers = value.get("peers")
    if type(peers) is not list or len(peers) != 2:
        raise ValueError("pubsub_peers_invalid")
    normalized = []
    for index, peer in enumerate(peers):
        role = "ab"[index]
        api = f"http://127.0.0.1:{5032 + index}"
        if type(peer) is not dict or peer.get("role") != role or peer.get("api_url") != api:
            raise ValueError("pubsub_peer_invalid")
        node = peer.get("node_id")
        swarm = f"/ip4/127.0.0.1/tcp/{40032 + index}/p2p/{node}"
        unit = f"swissknife-visual-functional-pubsub-{role}.service"
        repo = peer.get("repo_path")
        if (type(node) is not str or not node or peer.get("swarm_multiaddr") != swarm or peer.get("unit") != unit
                or type(repo) is not str or not Path(repo).is_absolute() or ".." in Path(repo).parts):
            raise ValueError("pubsub_peer_invalid")
        normalized.append({"role": role, "api_url": api, "node_id": node, "swarm_multiaddr": swarm, "unit": unit, "repo_path": repo})
    if normalized[0]["node_id"] == normalized[1]["node_id"] or normalized[0]["repo_path"] == normalized[1]["repo_path"]:
        raise ValueError("pubsub_peers_not_distinct")
    return {"allowed_fixture_scopes": list(SCOPES), "peers": normalized}
