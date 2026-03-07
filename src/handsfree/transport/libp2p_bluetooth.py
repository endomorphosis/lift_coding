"""py-libp2p inspired Bluetooth transport wrapper.

This module provides a lightweight template that mirrors the layered approach
used in Berty's network package:
- Bluetooth driver framing
- Peer envelope serialization
- libp2p runtime bootstrap (optional dependency)
"""

from __future__ import annotations

import base64
import importlib
import json
from typing import Any, Protocol

from handsfree.transport import MessageHandler


class BluetoothDriver(Protocol):
    """Abstraction for handset Bluetooth frame transport."""

    def send_frame(self, frame: bytes) -> None:
        """Send a frame over the Bluetooth driver."""
        ...

    def set_frame_handler(self, handler: FrameHandler) -> None:
        """Set callback invoked for each inbound frame."""
        ...


class FrameHandler(Protocol):
    """Callback type for inbound Bluetooth frames."""

    def __call__(self, frame: bytes) -> None:
        ...


class Libp2pBluetoothTransport:
    """Transport that wraps Bluetooth driver frames with libp2p-style peer envelopes."""

    def __init__(self, bluetooth_driver: BluetoothDriver | None = None) -> None:
        self._bluetooth_driver = bluetooth_driver
        self._handler: MessageHandler | None = None
        self._runtime: Any = None

    def start(self) -> None:
        """Initialize py-libp2p runtime and wire Bluetooth callbacks."""
        self._runtime = _load_py_libp2p_runtime()
        if self._bluetooth_driver is not None:
            self._bluetooth_driver.set_frame_handler(self._handle_inbound_frame)

    def register_handler(self, handler: MessageHandler) -> None:
        """Register callback for inbound peer messages."""
        self._handler = handler

    def send(self, peer_id: str, payload: bytes) -> None:
        """Send payload to peer over wrapped Bluetooth driver."""
        if not peer_id:
            raise ValueError("peer_id cannot be empty")
        if not payload:
            raise ValueError("payload cannot be empty")
        if self._bluetooth_driver is None:
            raise RuntimeError("Bluetooth driver is not configured for libp2p transport")

        frame = _encode_envelope(peer_id=peer_id, payload=payload)
        self._bluetooth_driver.send_frame(frame)

    def _handle_inbound_frame(self, frame: bytes) -> None:
        peer_id, payload = _decode_envelope(frame)
        if self._handler is not None:
            self._handler(peer_id, payload)


def _load_py_libp2p_runtime() -> Any:
    """Load py-libp2p module lazily.

    The implementation keeps the runtime loosely-coupled so this project can
    run in environments where py-libp2p is optional.
    """
    try:
        return importlib.import_module("libp2p")
    except ImportError as exc:
        raise ImportError(
            "py-libp2p runtime is required for HANDSFREE_TRANSPORT_PROVIDER=libp2p_bluetooth. "
            "Install the py-libp2p package before enabling this provider."
        ) from exc


def _encode_envelope(peer_id: str, payload: bytes) -> bytes:
    data = {
        "peer_id": peer_id,
        "payload_b64": base64.b64encode(payload).decode("ascii"),
    }
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_envelope(frame: bytes) -> tuple[str, bytes]:
    data = json.loads(frame.decode("utf-8"))
    peer_id = data.get("peer_id")
    payload_b64 = data.get("payload_b64")
    if not isinstance(peer_id, str) or not peer_id:
        raise ValueError("Envelope peer_id must be a non-empty string")
    if not isinstance(payload_b64, str) or not payload_b64:
        raise ValueError("Envelope payload_b64 must be a non-empty string")
    return peer_id, base64.b64decode(payload_b64.encode("ascii"))
