"""Governed two-owned-peer pubsub exchange. HTTP publish ACK is accepted only, never delivery."""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import sys
import threading
import time
import uuid
from pathlib import Path

from owned_pubsub_peers import load_owned_pubsub

SDK_PATH = "external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py"
BRIDGE_PATH = "scripts/svf_backends/native_pubsub_backend.py"
SERVICE_PATH = "scripts/svf_backends/native_kit_service.py"
FIELDS = {"fixture_scope", "topic", "message_id", "message", "dry_run", "correlation_id"}
FORBIDDEN = {"api_url", "argv", "path", "url", "command", "repo_path", "node_id", "peer_id"}
_LOCK = threading.Lock()
_CACHE = {}
_SDK = None
_ROOT = None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(root: Path, relative: str) -> str:
    return _sha((root / relative).read_bytes())


def bind(root: Path) -> None:
    global _SDK, _ROOT
    root = Path(root).resolve()
    kit = str(root / "external/ipfs_kit")
    if kit not in sys.path:
        sys.path.insert(0, kit)
    import ipfs_kit_py.assurance.pinned_pubsub as sdk
    if not hasattr(sdk, "LivePinnedPubsubAdapter"):
        raise RuntimeError("pinned pubsub adapter missing")
    _SDK, _ROOT = sdk, root


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _strict_json(raw: bytes):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("pubsub_frame_invalid")
            value[key] = item
        return value
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("pubsub_frame_invalid")))


def _multibase(value: str) -> bytes:
    if type(value) is not str or not 1 < len(value) <= 16384:
        raise ValueError("pubsub_frame_invalid")
    prefix, text = value[0], value[1:]
    if prefix not in "uUmM":
        raise ValueError("pubsub_frame_invalid")
    url, padded = prefix in "uU", prefix in "UM"
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" + ("-_" if url else "+/")
    if (not padded and "=" in text) or any(ch not in alphabet and ch != "=" for ch in text):
        raise ValueError("pubsub_frame_invalid")
    try:
        data = base64.b64decode(text + ("" if padded else "=" * ((-len(text)) % 4)), altchars=b"-_" if url else None, validate=True)
    except Exception as exc:
        raise ValueError("pubsub_frame_invalid") from exc
    expected = (base64.urlsafe_b64encode(data) if url else base64.b64encode(data)).decode()
    if text != (expected if padded else expected.rstrip("=")):
        raise ValueError("pubsub_frame_invalid")
    return data


def _decode(raw: bytes, *, sender: str, topic: str, data: bytes) -> None:
    if type(raw) is not bytes or not 0 < len(raw) <= 16384 or b"\x00" in raw:
        raise ValueError("pubsub_frame_invalid")
    frame = _strict_json(raw)
    if type(frame) is not dict or not {"from", "data", "seqno", "topicIDs"} <= set(frame) or set(frame) - {"from", "data", "seqno", "topicIDs", "signature", "key"}:
        raise ValueError("pubsub_frame_invalid")
    if frame["from"] != sender or type(frame["topicIDs"]) is not list or len(frame["topicIDs"]) != 1:
        raise ValueError("pubsub_frame_mismatch")
    if _multibase(frame["topicIDs"][0]).decode("utf-8") != topic or not 1 <= len(_multibase(frame["seqno"])) <= 32:
        raise ValueError("pubsub_frame_mismatch")
    if _multibase(frame["data"]) != data:
        raise ValueError("pubsub_frame_mismatch")


def _validate(args: dict, allowed: list) -> tuple:
    if type(args) is not dict or FORBIDDEN & set(args) or set(args) != FIELDS:
        raise ValueError("pubsub_arguments_rejected")
    scope, topic, message_id, message, dry_run, correlation = (args["fixture_scope"], args["topic"], args["message_id"], args["message"], args["dry_run"], args["correlation_id"])
    if scope not in allowed:
        raise ValueError("pubsub_scope_rejected")
    if dry_run is not False:
        raise ValueError("pubsub_preview_rejected")
    if type(topic) is not str or __import__("re").fullmatch(r"svf\.pubsub\.[0-9a-f]{32}", topic) is None:
        raise ValueError("pubsub_topic_rejected")
    try:
        if type(message_id) is not str or str(uuid.UUID(message_id)) != message_id:
            raise ValueError("pubsub_message_id_rejected")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("pubsub_message_id_rejected") from exc
    if type(message) is not str:
        raise ValueError("pubsub_message_rejected")
    data = message.encode("utf-8")
    if not 1 <= len(data) <= 4096:
        raise ValueError("pubsub_message_rejected")
    if type(correlation) is not str or __import__("re").fullmatch(r"[A-Za-z0-9:_-]{1,128}", correlation) is None:
        raise ValueError("pubsub_correlation_rejected")
    return topic, message_id, data, correlation


def _wait_peer(client, topic: str, node_id: str, deadline: float, cancel: threading.Event) -> None:
    while time.monotonic() < deadline:
        if node_id in client.pubsub_peers(topic, deadline=deadline, cancel_event=cancel):
            return
        time.sleep(0.05)
    raise TimeoutError("pubsub peer not ready")


def _take(subscription, sender: str, topic: str, data: bytes) -> bytes:
    try:
        while True:
            raw = next(subscription)["raw_frame"]
            _decode(raw, sender=sender, topic=topic, data=data)
            return raw
    except StopIteration as exc:
        raise RuntimeError("pubsub_receive_missing") from exc


def _exchange(record: dict, *, correlation_id: str, replayed: bool) -> dict:
    root = _ROOT
    provenance = {
        "schema": "swissknife.native-kit-pubsub-execution.v1", "owner": "ipfs_kit_py",
        "sdk_class": "ipfs_kit_py.assurance.pinned_pubsub.LivePinnedPubsubAdapter", "sdk_method": "pubsub_publish",
        "sdk_source_sha256": _file_sha(root, SDK_PATH), "bridge_source_sha256": _file_sha(root, BRIDGE_PATH),
        "service_source_sha256": _file_sha(root, SERVICE_PATH), "sdk_request_id": record["request_id"],
        "sdk_operation_id": record["operation_id"], "transport": "http", "simulated": False, "cache_fallback": False,
        "effect_kind": "EXTERNAL_NOTIFY", "durable": False, "state": "ACCEPTED", "correlation_id": correlation_id,
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "work_complete": False, "completion_authority": False,
    }
    return {
        "schema": "swissknife.native-pubsub-exchange.v1", "backend": "ipfs_kit_py.assurance.pinned_pubsub:live-kubo-http",
        "success": True, "accepted": True, "durable": False, "delivery_state": "delivered", "replayed": replayed,
        "message_id": record["message_id"], "topic": record["topic"], "message_sha256": record["message_sha256"],
        "sender_peer_id": record["sender_peer_id"], "receiver_peer_id": record["receiver_peer_id"],
        "receiver_frame_base64": record["receiver_frame_base64"], "ack_frame_base64": record["ack_frame_base64"],
        "native_provenance": provenance,
    }


def _deliver(topic: str, message_id: str, data: bytes) -> dict:
    if _SDK is None or _ROOT is None:
        raise RuntimeError("pubsub backend is not bound")
    config = load_owned_pubsub(_ROOT)
    peers = config["peers"]
    deadline = time.monotonic() + 12
    cancel = threading.Event()
    clients, subs = [], []
    try:
        for peer in peers:
            client = _SDK.LivePinnedPubsubAdapter(api_url=peer["api_url"], timeout=10)
            if client.simulated or client._transport is not None or client.transport_kind != "http" or client.live_provider is not True:
                raise RuntimeError("injected or simulated pubsub transports are forbidden")
            clients.append(client)
        clients[0].swarm_connect(peers[1]["swarm_multiaddr"], deadline=deadline, cancel_event=cancel)
        received = clients[1].subscribe(topic, deadline=deadline, cancel_event=cancel, max_frames=4, max_bytes=65536)
        acked = clients[0].subscribe(topic + ".ack", deadline=deadline, cancel_event=cancel, max_frames=4, max_bytes=65536)
        subs.extend((received.__enter__(), acked.__enter__()))
        _wait_peer(clients[0], topic, peers[1]["node_id"], deadline, cancel)
        published = clients[0].pubsub_publish(topic, data, deadline=deadline, cancel_event=cancel)
        if published.get("accepted") is not True or published.get("durable") is not False or published.get("state") != "ACCEPTED" or published.get("effect_kind") != "EXTERNAL_NOTIFY":
            raise RuntimeError("pubsub publish was not accepted-only")
        receiver_raw = _take(subs[0], peers[0]["node_id"], topic, data)
        ack = _canonical({"schema": "swissknife.pubsub-ack.v1", "message_id": message_id, "topic": topic, "message_sha256": _sha(data),
                          "sender_peer_id": peers[1]["node_id"], "receiver_peer_id": peers[0]["node_id"]})
        _wait_peer(clients[1], topic + ".ack", peers[0]["node_id"], deadline, cancel)
        clients[1].pubsub_publish(topic + ".ack", ack, deadline=deadline, cancel_event=cancel)
        ack_raw = _take(subs[1], peers[1]["node_id"], topic + ".ack", ack)
        return {"message_id": message_id, "topic": topic, "message_sha256": _sha(data), "sender_peer_id": peers[0]["node_id"],
                "receiver_peer_id": peers[1]["node_id"], "receiver_frame_base64": base64.b64encode(receiver_raw).decode(),
                "ack_frame_base64": base64.b64encode(ack_raw).decode(), "request_id": published["request_id"], "operation_id": published["operation_id"]}
    finally:
        cancel.set()
        for sub in subs:
            sub.close()
        for client in clients:
            client.close()


def publish_exchange(args: dict) -> dict:
    if _ROOT is None:
        raise RuntimeError("pubsub backend is not bound")
    allowed = load_owned_pubsub(_ROOT)["allowed_fixture_scopes"]
    topic, message_id, data, correlation = _validate(args, allowed)
    digest = _sha(data)
    with _LOCK:
        existing = _CACHE.get(message_id)
        if existing is not None:
            if existing["topic"] != topic or existing["message_sha256"] != digest:
                raise ValueError("pubsub_message_identity_conflict")
            return _exchange(existing, correlation_id=correlation, replayed=True)
        record = _deliver(topic, message_id, data)
        _CACHE[message_id] = record
        return _exchange(record, correlation_id=correlation, replayed=False)
