"""py-libp2p inspired Bluetooth transport wrapper.

This module intentionally keeps the layering close to the Berty v1 shape:
- native Bluetooth driver bridge
- versioned transport envelopes
- peer session state
- optional py-libp2p runtime bootstrap

The current implementation is still a transport foundation, not a full custom
py-libp2p transport. It defines the contract that native Bluetooth adapters can
target while preserving libp2p-friendly concepts such as peer identity,
protocol IDs, stream/session separation, and explicit version negotiation.
"""

from __future__ import annotations

import base64
import importlib
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol

from handsfree.transport import DEFAULT_PROTOCOL, MessageHandler

PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0
PROTOCOL_ID = "/handsfree/bluetooth/1.0.0"
CHAT_PROTOCOL_ID = "/handsfree/chat/1.0.0"
MAX_FRAME_BYTES = 16 * 1024

EnvelopeKind = Literal["handshake", "message", "ack", "error"]


def _new_session_id() -> str:
    return secrets.token_hex(8)


def _new_message_id() -> str:
    return secrets.token_hex(8)


def _new_nonce() -> str:
    return secrets.token_hex(12)


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


class BluetoothDriver(Protocol):
    """Abstraction for handset Bluetooth frame transport."""

    def start(self) -> None:
        """Initialize native Bluetooth transport resources."""
        ...

    def send_frame(self, peer_ref: str, frame: bytes) -> None:
        """Send a frame over the Bluetooth driver."""
        ...

    def set_frame_handler(self, handler: FrameHandler) -> None:
        """Set callback invoked for each inbound frame."""
        ...


@dataclass(slots=True)
class BluetoothTransportConnection:
    """Adapter-facing connection state for a Bluetooth-backed libp2p session."""

    peer_ref: str
    peer_id: str
    session_id: str
    protocol_id: str = PROTOCOL_ID
    capabilities: tuple[str, ...] = ()


@dataclass(slots=True)
class LocalPeerIdentity:
    """Runtime identity derived from py-libp2p bootstrap helpers."""

    peer_id: str
    key_type: str
    host_enabled: bool
    muxer: str | None = None
    transport_protocols: tuple[str, ...] = ()


class BluetoothTransportAdapter(Protocol):
    """Boundary that can later be mapped onto a real py-libp2p transport."""

    def bootstrap_runtime(self, runtime: Any) -> LocalPeerIdentity | None:
        """Initialize local libp2p identity/runtime state."""
        ...

    def open_outbound(self, connection: BluetoothTransportConnection) -> None:
        """Prepare an outbound Bluetooth-backed libp2p session."""
        ...

    def accept_inbound(self, connection: BluetoothTransportConnection) -> None:
        """Register an inbound Bluetooth-backed libp2p session."""
        ...

    def close(self, peer_ref: str, session_id: str) -> None:
        """Tear down an established session."""
        ...


class FrameHandler(Protocol):
    """Callback type for inbound Bluetooth frames."""

    def __call__(self, peer_ref: str, frame: bytes) -> None:
        ...


class SessionState(str, Enum):
    """Lifecycle states for a peer session."""

    NEW = "new"
    HANDSHAKING = "handshaking"
    ESTABLISHED = "established"
    DEGRADED = "degraded"
    CLOSED = "closed"


class TransportEnvelopeError(ValueError):
    """Raised when a frame cannot be decoded or validated."""


class ProtocolVersionError(TransportEnvelopeError):
    """Raised when a peer speaks an unsupported protocol version."""


@dataclass(slots=True)
class PeerEnvelope:
    """Versioned transport frame exchanged over the Bluetooth driver."""

    kind: EnvelopeKind
    peer_id: str
    session_id: str
    protocol_id: str = PROTOCOL_ID
    version_major: int = PROTOCOL_MAJOR
    version_minor: int = PROTOCOL_MINOR
    message_id: str = field(default_factory=_new_message_id)
    timestamp_ms: int = field(default_factory=_timestamp_ms)
    nonce: str = field(default_factory=_new_nonce)
    payload_b64: str | None = None
    acked_message_id: str | None = None
    capabilities: list[str] | None = None
    error_code: str | None = None
    error_detail: str | None = None


@dataclass(slots=True)
class PeerSession:
    """Runtime session state for a remote peer."""

    peer_id: str
    peer_ref: str
    session_id: str
    state: SessionState = SessionState.NEW
    capabilities: tuple[str, ...] = ()
    last_message_id: str | None = None
    last_acked_message_id: str | None = None
    seen_message_ids: set[str] = field(default_factory=set)


class InMemoryBluetoothTransportAdapter:
    """Minimal adapter that records session openings until a real py-libp2p transport exists."""

    def __init__(self) -> None:
        self.connections: dict[tuple[str, str], BluetoothTransportConnection] = {}
        self.local_identity: LocalPeerIdentity | None = None

    def bootstrap_runtime(self, runtime: Any) -> LocalPeerIdentity | None:
        return self.local_identity

    def open_outbound(self, connection: BluetoothTransportConnection) -> None:
        self.connections[(connection.peer_ref, connection.session_id)] = connection

    def accept_inbound(self, connection: BluetoothTransportConnection) -> None:
        self.connections[(connection.peer_ref, connection.session_id)] = connection

    def close(self, peer_ref: str, session_id: str) -> None:
        self.connections.pop((peer_ref, session_id), None)


class RuntimeBluetoothTransportAdapter(InMemoryBluetoothTransportAdapter):
    """Adapter that bootstraps local peer identity from a py-libp2p runtime."""

    def __init__(self) -> None:
        super().__init__()
        self.host: Any | None = None
        self.key_pair: Any | None = None

    def bootstrap_runtime(self, runtime: Any) -> LocalPeerIdentity | None:
        if self.local_identity is not None:
            return self.local_identity

        generate_identity = getattr(runtime, "generate_new_ed25519_identity", None)
        generate_peer_id = getattr(runtime, "generate_peer_id_from", None)
        if generate_identity is None or generate_peer_id is None:
            return None

        self.key_pair = generate_identity()
        peer_id = str(generate_peer_id(self.key_pair))

        host_enabled = False
        host = None
        new_host = getattr(runtime, "new_host", None)
        if new_host is not None:
            try:
                host = new_host(key_pair=self.key_pair)
            except TypeError:
                host = new_host(self.key_pair)
            host_enabled = host is not None

        self.host = host
        muxer = None
        get_default_muxer = getattr(runtime, "get_default_muxer", None)
        if get_default_muxer is not None:
            try:
                muxer = str(get_default_muxer())
            except Exception:
                muxer = None

        transport_protocols: tuple[str, ...] = ()
        get_supported_transport_protocols = getattr(runtime, "get_supported_transport_protocols", None)
        if get_supported_transport_protocols is not None:
            try:
                transport_protocols = tuple(str(item) for item in get_supported_transport_protocols())
            except Exception:
                transport_protocols = ()

        self.local_identity = LocalPeerIdentity(
            peer_id=peer_id,
            key_type=type(self.key_pair).__name__,
            host_enabled=host_enabled,
            muxer=muxer,
            transport_protocols=transport_protocols,
        )
        return self.local_identity


class Libp2pBluetoothTransport:
    """Transport that wraps Bluetooth driver frames with libp2p-style peer envelopes."""

    def __init__(
        self,
        bluetooth_driver: BluetoothDriver | None = None,
        transport_adapter: BluetoothTransportAdapter | None = None,
    ) -> None:
        self._bluetooth_driver = bluetooth_driver
        self._handler: MessageHandler | None = None
        self._protocol_handlers: dict[str, MessageHandler] = {}
        self._runtime: Any = None
        self._sessions: dict[str, PeerSession] = {}
        self._transport_adapter = transport_adapter or InMemoryBluetoothTransportAdapter()
        self._local_identity: LocalPeerIdentity | None = None

    def start(self) -> None:
        """Initialize py-libp2p runtime and wire Bluetooth callbacks."""
        self._runtime = _load_py_libp2p_runtime()
        self._local_identity = self._transport_adapter.bootstrap_runtime(self._runtime)
        if self._bluetooth_driver is not None:
            self._bluetooth_driver.start()
            self._bluetooth_driver.set_frame_handler(self._handle_inbound_frame)

    def register_handler(self, handler: MessageHandler) -> None:
        """Register callback for inbound peer messages."""
        self._handler = handler

    def register_protocol_handler(self, protocol: str, handler: MessageHandler) -> None:
        """Register callback for inbound protocol-scoped messages."""
        if not protocol:
            raise ValueError("protocol cannot be empty")
        self._protocol_handlers[protocol] = handler

    def get_local_identity(self) -> LocalPeerIdentity | None:
        """Return the local py-libp2p identity snapshot when available."""
        return self._local_identity

    def send(self, peer_id: str, payload: bytes) -> None:
        """Send payload to peer over wrapped Bluetooth driver."""
        self.send_protocol_message(peer_id, DEFAULT_PROTOCOL, payload)

    def send_protocol_message(self, peer_id: str, protocol: str, payload: bytes) -> None:
        """Send a protocol-scoped payload to peer over wrapped Bluetooth driver."""
        if not peer_id:
            raise ValueError("peer_id cannot be empty")
        if not protocol:
            raise ValueError("protocol cannot be empty")
        if not payload:
            raise ValueError("payload cannot be empty")
        if self._bluetooth_driver is None:
            raise RuntimeError("Bluetooth driver is not configured for libp2p transport")

        session = self._ensure_outbound_session(peer_id)
        envelope = PeerEnvelope(
            kind="message",
            peer_id=peer_id,
            session_id=session.session_id,
            payload_b64=_encode_payload(_encode_protocol_message(protocol, payload)),
        )
        session.last_message_id = envelope.message_id
        self._send_envelope(peer_ref=session.peer_ref, envelope=envelope)

    def _ensure_outbound_session(self, peer_id: str) -> PeerSession:
        existing = self._sessions.get(peer_id)
        if existing is not None and existing.state in {
            SessionState.HANDSHAKING,
            SessionState.ESTABLISHED,
        }:
            return existing

        session = PeerSession(
            peer_id=peer_id,
            peer_ref=peer_id,
            session_id=_new_session_id(),
            state=SessionState.HANDSHAKING,
            capabilities=_runtime_capabilities(self._runtime),
        )
        self._sessions[peer_id] = session
        self._transport_adapter.open_outbound(
            BluetoothTransportConnection(
                peer_ref=session.peer_ref,
                peer_id=session.peer_id,
                session_id=session.session_id,
                capabilities=session.capabilities,
            )
        )
        handshake = PeerEnvelope(
            kind="handshake",
            peer_id=peer_id,
            session_id=session.session_id,
            capabilities=list(session.capabilities),
        )
        self._send_envelope(peer_ref=session.peer_ref, envelope=handshake)
        session.state = SessionState.ESTABLISHED
        return session

    def _handle_inbound_frame(self, peer_ref: str, frame: bytes) -> None:
        envelope = _decode_envelope(frame)
        session = self._sessions.get(envelope.peer_id)

        if envelope.kind == "handshake":
            session = PeerSession(
                peer_id=envelope.peer_id,
                peer_ref=peer_ref,
                session_id=envelope.session_id,
                state=SessionState.ESTABLISHED,
                capabilities=tuple(envelope.capabilities or ()),
            )
            self._sessions[envelope.peer_id] = session
            self._transport_adapter.accept_inbound(
                BluetoothTransportConnection(
                    peer_ref=peer_ref,
                    peer_id=envelope.peer_id,
                    session_id=envelope.session_id,
                    capabilities=session.capabilities,
                )
            )
            return

        if session is None or session.session_id != envelope.session_id:
            raise TransportEnvelopeError(
                f"Unknown or mismatched session for peer '{envelope.peer_id}'"
            )

        if envelope.kind == "message":
            if envelope.message_id in session.seen_message_ids:
                ack = PeerEnvelope(
                    kind="ack",
                    peer_id=envelope.peer_id,
                    session_id=envelope.session_id,
                    acked_message_id=envelope.message_id,
                )
                self._send_envelope(peer_ref=peer_ref, envelope=ack)
                return

            session.seen_message_ids.add(envelope.message_id)
            protocol, payload = _decode_protocol_message(_decode_payload(envelope.payload_b64))
            session.last_message_id = envelope.message_id
            handler = self._protocol_handlers.get(protocol)
            if handler is not None:
                handler(envelope.peer_id, payload)
            elif self._handler is not None:
                self._handler(envelope.peer_id, payload)
            ack = PeerEnvelope(
                kind="ack",
                peer_id=envelope.peer_id,
                session_id=envelope.session_id,
                acked_message_id=envelope.message_id,
            )
            self._send_envelope(peer_ref=peer_ref, envelope=ack)
            return

        if envelope.kind == "ack":
            session.last_acked_message_id = envelope.acked_message_id
            return

        if envelope.kind == "error":
            session.state = SessionState.DEGRADED
            return

        raise TransportEnvelopeError(f"Unsupported envelope kind '{envelope.kind}'")

    def _send_envelope(self, peer_ref: str, envelope: PeerEnvelope) -> None:
        if self._bluetooth_driver is None:
            raise RuntimeError("Bluetooth driver is not configured for libp2p transport")
        frame = _encode_envelope(envelope)
        self._bluetooth_driver.send_frame(peer_ref, frame)


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


def _encode_envelope(envelope: PeerEnvelope) -> bytes:
    frame = json.dumps(asdict(envelope), separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(frame) > MAX_FRAME_BYTES:
        raise TransportEnvelopeError("Envelope exceeds maximum Bluetooth frame size")
    return frame


def _decode_envelope(frame: bytes) -> PeerEnvelope:
    if len(frame) > MAX_FRAME_BYTES:
        raise TransportEnvelopeError("Envelope exceeds maximum Bluetooth frame size")
    try:
        data = json.loads(frame.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise TransportEnvelopeError("Envelope frame is not valid UTF-8 data") from exc
    except json.JSONDecodeError as exc:
        raise TransportEnvelopeError("Envelope frame is not valid JSON data") from exc

    if not isinstance(data, dict):
        raise TransportEnvelopeError("Envelope frame must decode to a JSON object")

    version_major = data.get("version_major")
    version_minor = data.get("version_minor")
    if version_major != PROTOCOL_MAJOR:
        raise ProtocolVersionError(
            f"Unsupported protocol major version '{version_major}', expected '{PROTOCOL_MAJOR}'"
        )
    if not isinstance(version_minor, int) or version_minor < 0:
        raise TransportEnvelopeError("Envelope version_minor must be a non-negative integer")

    kind = data.get("kind")
    if kind not in {"handshake", "message", "ack", "error"}:
        raise TransportEnvelopeError("Envelope kind is invalid or unsupported")

    peer_id = data.get("peer_id")
    session_id = data.get("session_id")
    protocol_id = data.get("protocol_id")
    message_id = data.get("message_id")
    nonce = data.get("nonce")
    timestamp_ms = data.get("timestamp_ms")
    if not isinstance(peer_id, str) or not peer_id:
        raise TransportEnvelopeError("Envelope peer_id must be a non-empty string")
    if not isinstance(session_id, str) or not session_id:
        raise TransportEnvelopeError("Envelope session_id must be a non-empty string")
    if protocol_id != PROTOCOL_ID:
        raise TransportEnvelopeError(f"Envelope protocol_id must be '{PROTOCOL_ID}'")
    if not isinstance(message_id, str) or not message_id:
        raise TransportEnvelopeError("Envelope message_id must be a non-empty string")
    if not isinstance(nonce, str) or not nonce:
        raise TransportEnvelopeError("Envelope nonce must be a non-empty string")
    if not isinstance(timestamp_ms, int) or timestamp_ms <= 0:
        raise TransportEnvelopeError("Envelope timestamp_ms must be a positive integer")

    payload_b64 = data.get("payload_b64")
    acked_message_id = data.get("acked_message_id")
    capabilities = data.get("capabilities")
    error_code = data.get("error_code")
    error_detail = data.get("error_detail")

    if kind == "message" and not isinstance(payload_b64, str):
        raise TransportEnvelopeError("Message envelope requires payload_b64")
    if kind == "ack" and not isinstance(acked_message_id, str):
        raise TransportEnvelopeError("Ack envelope requires acked_message_id")
    if kind == "handshake" and capabilities is not None:
        if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
            raise TransportEnvelopeError("Handshake capabilities must be a list of strings")
    if kind == "error" and not isinstance(error_code, str):
        raise TransportEnvelopeError("Error envelope requires error_code")
    if error_detail is not None and not isinstance(error_detail, str):
        raise TransportEnvelopeError("Envelope error_detail must be a string when present")

    return PeerEnvelope(
        kind=kind,
        peer_id=peer_id,
        session_id=session_id,
        protocol_id=protocol_id,
        version_major=version_major,
        version_minor=version_minor,
        message_id=message_id,
        timestamp_ms=timestamp_ms,
        nonce=nonce,
        payload_b64=payload_b64,
        acked_message_id=acked_message_id,
        capabilities=capabilities,
        error_code=error_code,
        error_detail=error_detail,
    )


def _encode_payload(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


def _decode_payload(payload_b64: str | None) -> bytes:
    if not isinstance(payload_b64, str) or not payload_b64:
        raise TransportEnvelopeError("Envelope payload_b64 must be a non-empty string")
    try:
        return base64.b64decode(payload_b64.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise TransportEnvelopeError("Envelope payload_b64 is not valid ASCII base64 data") from exc


def _encode_protocol_message(protocol: str, payload: bytes) -> bytes:
    if not protocol:
        raise TransportEnvelopeError("Protocol wrapper requires a non-empty protocol")
    wrapped = {
        "protocol": protocol,
        "payload_b64": base64.b64encode(payload).decode("ascii"),
    }
    return json.dumps(wrapped, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_protocol_message(payload: bytes) -> tuple[str, bytes]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return DEFAULT_PROTOCOL, payload

    if not isinstance(data, dict):
        return DEFAULT_PROTOCOL, payload

    protocol = data.get("protocol")
    payload_b64 = data.get("payload_b64")
    if not isinstance(protocol, str) or not protocol:
        return DEFAULT_PROTOCOL, payload
    if not isinstance(payload_b64, str) or not payload_b64:
        raise TransportEnvelopeError("Protocol wrapper payload_b64 must be a non-empty string")
    try:
        return protocol, base64.b64decode(payload_b64.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise TransportEnvelopeError("Protocol wrapper payload_b64 is not valid ASCII base64 data") from exc


def encode_chat_message_payload(text: str, sender_peer_id: str | None = None) -> bytes:
    """Encode a HandsFree chat protocol payload."""
    if not text:
        raise TransportEnvelopeError("Chat payload text cannot be empty")
    payload: dict[str, Any] = {"type": "chat", "text": text}
    if sender_peer_id:
        payload["sender_peer_id"] = sender_peer_id
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode_chat_message_payload(payload: bytes) -> dict[str, Any]:
    """Decode a HandsFree chat protocol payload."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransportEnvelopeError("Chat payload is not valid UTF-8 JSON data") from exc
    if not isinstance(data, dict):
        raise TransportEnvelopeError("Chat payload must decode to a JSON object")
    if data.get("type") != "chat":
        raise TransportEnvelopeError("Chat payload type must be 'chat'")
    text = data.get("text")
    if not isinstance(text, str) or not text:
        raise TransportEnvelopeError("Chat payload text must be a non-empty string")
    return data


def _runtime_capabilities(runtime: Any) -> tuple[str, ...]:
    capabilities = ["bluetooth-driver-bridge", "handshake-v1", "ack-v1", "session-adapter-v1"]
    if getattr(runtime, "new_host", None) is not None:
        capabilities.append("py-libp2p-host")
    if getattr(runtime, "generate_new_ed25519_identity", None) is not None:
        capabilities.append("ed25519")
    if getattr(runtime, "get_default_muxer", None) is not None:
        capabilities.append(f"muxer:{str(runtime.get_default_muxer()).lower()}")
    return tuple(capabilities)


def encode_transport_envelope(envelope: PeerEnvelope) -> bytes:
    """Public wrapper for encoding a transport envelope."""
    return _encode_envelope(envelope)


def decode_transport_envelope(frame: bytes) -> PeerEnvelope:
    """Public wrapper for decoding a transport envelope."""
    return _decode_envelope(frame)


def decode_transport_payload(payload_b64: str | None) -> bytes:
    """Public wrapper for decoding a message payload."""
    return _decode_payload(payload_b64)


def decode_transport_message(payload_b64: str | None) -> tuple[str, bytes]:
    """Public wrapper for decoding a protocol-scoped transport message."""
    return _decode_protocol_message(_decode_payload(payload_b64))


def encode_transport_message(protocol: str, payload: bytes) -> str:
    """Public wrapper for encoding a protocol-scoped message payload as base64."""
    return _encode_payload(_encode_protocol_message(protocol, payload))
