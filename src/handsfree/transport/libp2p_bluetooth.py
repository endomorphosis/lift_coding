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
import inspect
import json
import os
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Protocol

from handsfree.transport import DEFAULT_PROTOCOL, MessageHandler

PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0
PROTOCOL_ID = "/handsfree/bluetooth/1.0.0"
CHAT_PROTOCOL_ID = "/handsfree/chat/1.0.0"
MAX_FRAME_BYTES = 16 * 1024
RUNTIME_STREAM_PROTOCOL_ID = "/handsfree/runtime-stream/1.0.0"

EnvelopeKind = Literal["handshake", "message", "ack", "error"]


def _new_session_id() -> str:
    return secrets.token_hex(8)


def _new_message_id() -> str:
    return secrets.token_hex(8)


def _new_nonce() -> str:
    return secrets.token_hex(12)


def _new_resume_token() -> str:
    return secrets.token_hex(10)


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
    resume_token: str | None = None
    protocol_id: str = PROTOCOL_ID
    capabilities: tuple[str, ...] = ()


@dataclass(slots=True)
class BluetoothProtocolStream:
    """Adapter-facing protocol stream bound to a Bluetooth-backed session."""

    peer_ref: str
    peer_id: str
    session_id: str
    protocol: str
    resume_token: str | None = None
    runtime_stream: Any | None = None
    inbound_payloads: list[bytes] = field(default_factory=list)
    outbound_payloads: list[bytes] = field(default_factory=list)
    inbound_message_ids: list[str] = field(default_factory=list)
    acked_message_ids: list[str] = field(default_factory=list)
    runtime_message_index: int = 0
    outbound_message_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LocalPeerIdentity:
    """Runtime identity derived from py-libp2p bootstrap helpers."""

    peer_id: str
    key_type: str
    host_enabled: bool
    muxer: str | None = None
    transport_protocols: tuple[str, ...] = ()


@dataclass(slots=True)
class PersistedTransportSessionCursor:
    """Persisted runtime session cursor for peer/session resume."""

    peer_id: str
    peer_ref: str
    session_id: str
    resume_token: str
    capabilities: tuple[str, ...] = ()
    updated_at_ms: int | None = None


class TransportSessionStore(Protocol):
    """Persistence boundary for transport session cursors."""

    def load_all(self) -> dict[str, PersistedTransportSessionCursor]:
        ...

    def save(self, cursor: PersistedTransportSessionCursor) -> None:
        ...

    def delete(self, peer_id: str) -> None:
        ...


class InMemoryTransportSessionStore:
    """Process-local transport session cursor store."""

    def __init__(self) -> None:
        self._cursors: dict[str, PersistedTransportSessionCursor] = {}

    def load_all(self) -> dict[str, PersistedTransportSessionCursor]:
        return dict(self._cursors)

    def save(self, cursor: PersistedTransportSessionCursor) -> None:
        self._cursors[cursor.peer_id] = cursor

    def delete(self, peer_id: str) -> None:
        self._cursors.pop(peer_id, None)


class FileTransportSessionStore:
    """JSON-backed transport session cursor store for process restarts."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv(
            "HANDSFREE_TRANSPORT_SESSION_STORE_PATH",
            ".handsfree_transport_sessions.json",
        )
        self.path = Path(configured_path)

    def load_all(self) -> dict[str, PersistedTransportSessionCursor]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}

        cursors: dict[str, PersistedTransportSessionCursor] = {}
        for peer_id, raw in data.items():
            if not isinstance(peer_id, str) or not isinstance(raw, dict):
                continue
            session_id = raw.get("session_id")
            peer_ref = raw.get("peer_ref")
            resume_token = raw.get("resume_token")
            capabilities = raw.get("capabilities") or ()
            if not isinstance(session_id, str) or not session_id:
                continue
            if not isinstance(peer_ref, str) or not peer_ref:
                continue
            if not isinstance(resume_token, str) or not resume_token:
                continue
            if not isinstance(capabilities, (list, tuple)) or any(
                not isinstance(item, str) for item in capabilities
            ):
                capabilities = ()
            cursors[peer_id] = PersistedTransportSessionCursor(
                peer_id=peer_id,
                peer_ref=peer_ref,
                session_id=session_id,
                resume_token=resume_token,
                capabilities=tuple(capabilities),
                updated_at_ms=raw.get("updated_at_ms"),
            )
        return cursors

    def save(self, cursor: PersistedTransportSessionCursor) -> None:
        data = {
            peer_id: asdict(existing)
            for peer_id, existing in self.load_all().items()
        }
        data[cursor.peer_id] = asdict(cursor)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )

    def delete(self, peer_id: str) -> None:
        data = {
            existing_peer_id: asdict(existing)
            for existing_peer_id, existing in self.load_all().items()
            if existing_peer_id != peer_id
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )


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
    resume_token: str = field(default_factory=_new_resume_token)
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
            if host_enabled:
                get_id = getattr(host, "get_id", None)
                if get_id is not None:
                    try:
                        peer_id = str(get_id())
                    except Exception:
                        peer_id = str(peer_id)

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


class ProtocolRoutingBluetoothTransportAdapter(RuntimeBluetoothTransportAdapter):
    """Adapter that tracks protocol-bound streams in a py-libp2p-like shape."""

    def __init__(self) -> None:
        super().__init__()
        self.streams: dict[tuple[str, str, str], BluetoothProtocolStream] = {}
        self._protocol_stream_handlers: dict[str, Any] = {}
        self._runtime_inbound_handler: Any | None = None
        self._runtime_protocol_registrations: set[str] = set()
        self._runtime_stream_stop_events: dict[tuple[str, str, str], threading.Event] = {}
        self._runtime_stream_threads: dict[tuple[str, str, str], threading.Thread] = {}

    def bootstrap_runtime(self, runtime: Any) -> LocalPeerIdentity | None:
        identity = super().bootstrap_runtime(runtime)
        self._register_runtime_protocol_handlers()
        return identity

    def register_protocol_stream_handler(
        self,
        protocol: str,
        handler: Any,
    ) -> None:
        if not protocol:
            raise ValueError("protocol cannot be empty")
        self._protocol_stream_handlers[protocol] = handler
        self._register_runtime_protocol_handler(protocol)

    def set_runtime_inbound_handler(self, handler: Any) -> None:
        self._runtime_inbound_handler = handler

    def acknowledge_runtime_message(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
        message_id: str,
        emit_peer_ack: bool = False,
    ) -> None:
        stream = self.bind_protocol_stream(connection, protocol)
        if message_id not in stream.acked_message_ids:
            stream.acked_message_ids.append(message_id)
        if emit_peer_ack:
            write = getattr(stream.runtime_stream, "write", None)
            if write is not None:
                _resolve_runtime_value(
                    write(
                        _encode_runtime_stream_ack(
                            message_id=message_id,
                            session_id=connection.session_id,
                            protocol=protocol,
                            resume_token=connection.resume_token,
                        )
                    )
                )

    def bind_protocol_stream(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
    ) -> BluetoothProtocolStream:
        stream_key = (connection.peer_ref, connection.session_id, protocol)
        existing = self.streams.get(stream_key)
        if existing is not None:
            return existing

        runtime_stream = self._open_runtime_stream(connection.peer_id, protocol)
        stream = BluetoothProtocolStream(
            peer_ref=connection.peer_ref,
            peer_id=connection.peer_id,
            session_id=connection.session_id,
            protocol=protocol,
            resume_token=connection.resume_token,
            runtime_stream=runtime_stream,
        )
        self.streams[stream_key] = stream
        self._start_runtime_stream_reader(stream_key, stream)
        return stream

    def write_protocol_payload(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
        payload: bytes,
    ) -> BluetoothProtocolStream:
        stream = self.bind_protocol_stream(connection, protocol)
        stream.outbound_payloads.append(payload)
        message_id = self._next_runtime_message_id(stream)
        stream.outbound_message_ids.append(message_id)

        write = getattr(stream.runtime_stream, "write", None)
        if write is not None:
            _resolve_runtime_value(
                write(
                    _encode_runtime_stream_message(
                        message_id=message_id,
                        session_id=connection.session_id,
                        protocol=protocol,
                        resume_token=connection.resume_token,
                        payload=payload,
                    )
                )
            )
        return stream

    def deliver_inbound_protocol(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
        payload: bytes,
    ) -> None:
        stream = self.bind_protocol_stream(connection, protocol)
        stream.inbound_payloads.append(payload)
        handler = self._protocol_stream_handlers.get(protocol)
        if handler is not None:
            handler(stream, payload)

    def close(self, peer_ref: str, session_id: str) -> None:
        super().close(peer_ref, session_id)
        stale_keys = [
            key for key in self.streams
            if key[0] == peer_ref and key[1] == session_id
        ]
        for key in stale_keys:
            stream = self.streams.pop(key, None)
            if stream is not None:
                stop_event = self._runtime_stream_stop_events.pop(key, None)
                if stop_event is not None:
                    stop_event.set()
                _close_runtime_stream(stream.runtime_stream)
                worker = self._runtime_stream_threads.pop(key, None)
                if worker is not None:
                    worker.join(timeout=0.2)

    def _register_runtime_protocol_handlers(self) -> None:
        for protocol in self._protocol_stream_handlers:
            self._register_runtime_protocol_handler(protocol)

    def _register_runtime_protocol_handler(self, protocol: str) -> None:
        if self.host is None or protocol in self._runtime_protocol_registrations:
            return
        runtime_register = getattr(self.host, "set_stream_handler", None)
        if runtime_register is None:
            return

        runtime_register(protocol, self._build_runtime_protocol_handler(protocol))
        self._runtime_protocol_registrations.add(protocol)

    def _build_runtime_protocol_handler(self, protocol: str) -> Any:
        async def handle_runtime_stream(runtime_stream: Any) -> None:
            peer_id = _coerce_runtime_peer_id(runtime_stream) or "runtime-peer"
            stream = BluetoothProtocolStream(
                peer_ref=peer_id,
                peer_id=peer_id,
                session_id=_new_session_id(),
                protocol=protocol,
                resume_token=_new_resume_token(),
                runtime_stream=runtime_stream,
            )
            message_id, payload, is_ack, session_id, runtime_protocol, resume_token = _read_runtime_stream_message(runtime_stream)
            if message_id is None:
                message_id = self._next_runtime_message_id(stream)
            if not payload:
                payload = _read_runtime_stream_payload(runtime_stream)
            effective_session_id = session_id or stream.session_id
            effective_protocol = runtime_protocol or protocol
            effective_resume_token = resume_token or stream.resume_token
            stream_key = self._adopt_runtime_stream_metadata(
                (stream.peer_ref, stream.session_id, stream.protocol),
                stream,
                effective_session_id,
                effective_protocol,
                effective_resume_token,
            )
            duplicate = message_id in stream.inbound_message_ids
            if not duplicate and not is_ack:
                stream.inbound_message_ids.append(message_id)
                stream.inbound_payloads.append(payload)
            handler = self._protocol_stream_handlers.get(effective_protocol)
            if handler is not None and not duplicate and not is_ack:
                handler(stream, payload)
            if self._runtime_inbound_handler is not None and payload:
                self._runtime_inbound_handler(
                    BluetoothTransportConnection(
                        peer_ref=stream.peer_ref,
                        peer_id=stream.peer_id,
                        session_id=effective_session_id,
                        resume_token=effective_resume_token,
                    ),
                    effective_protocol,
                    payload,
                    message_id,
                    is_ack,
                )
            self.streams[stream_key] = stream

        return handle_runtime_stream

    def _open_runtime_stream(self, peer_id: str, protocol: str) -> Any | None:
        if self.host is None:
            return None

        open_stream = getattr(self.host, "new_stream", None)
        if open_stream is None:
            return None

        runtime_stream = open_stream(peer_id, [protocol])
        return _resolve_runtime_value(runtime_stream)

    def _start_runtime_stream_reader(
        self,
        stream_key: tuple[str, str, str],
        stream: BluetoothProtocolStream,
    ) -> None:
        if stream.runtime_stream is None or stream_key in self._runtime_stream_threads:
            return

        read = getattr(stream.runtime_stream, "read", None)
        if read is None:
            return

        stop_event = threading.Event()
        worker = threading.Thread(
            target=self._run_runtime_stream_reader,
            args=(stream_key, stream, stop_event),
            daemon=True,
        )
        self._runtime_stream_stop_events[stream_key] = stop_event
        self._runtime_stream_threads[stream_key] = worker
        worker.start()

    def _run_runtime_stream_reader(
        self,
        stream_key: tuple[str, str, str],
        stream: BluetoothProtocolStream,
        stop_event: threading.Event,
    ) -> None:
        while not stop_event.is_set():
            try:
                message_id, payload, is_ack, session_id, runtime_protocol, resume_token = _read_runtime_stream_message(
                    stream.runtime_stream
                )
            except Exception:
                break

            if not payload:
                break

            if message_id is None:
                message_id = self._next_runtime_message_id(stream)
            effective_session_id = session_id or stream.session_id
            effective_protocol = runtime_protocol or stream.protocol
            effective_resume_token = resume_token or stream.resume_token
            stream_key = self._adopt_runtime_stream_metadata(
                stream_key,
                stream,
                effective_session_id,
                effective_protocol,
                effective_resume_token,
            )
            duplicate = message_id in stream.inbound_message_ids
            if not duplicate and not is_ack:
                stream.inbound_payloads.append(payload)
                stream.inbound_message_ids.append(message_id)
            handler = self._protocol_stream_handlers.get(effective_protocol)
            if handler is not None and not duplicate and not is_ack:
                handler(stream, payload)
            if self._runtime_inbound_handler is not None:
                self._runtime_inbound_handler(
                    BluetoothTransportConnection(
                        peer_ref=stream.peer_ref,
                        peer_id=stream.peer_id,
                        session_id=effective_session_id,
                        resume_token=effective_resume_token,
                    ),
                    effective_protocol,
                    payload,
                    message_id,
                    is_ack,
                )

        self._runtime_stream_stop_events.pop(stream_key, None)
        self._runtime_stream_threads.pop(stream_key, None)

    def _next_runtime_message_id(self, stream: BluetoothProtocolStream) -> str:
        stream.runtime_message_index += 1
        return (
            f"runtime:{stream.peer_ref}:{stream.session_id}:{stream.protocol}:"
            f"{stream.runtime_message_index}"
        )

    def _adopt_runtime_stream_metadata(
        self,
        stream_key: tuple[str, str, str],
        stream: BluetoothProtocolStream,
        session_id: str,
        protocol: str,
        resume_token: str | None,
    ) -> tuple[str, str, str]:
        new_key = (stream.peer_ref, session_id, protocol)
        if new_key == stream_key:
            return stream_key

        self.streams.pop(stream_key, None)
        stream.session_id = session_id
        stream.protocol = protocol
        stream.resume_token = resume_token
        self.streams[new_key] = stream

        stop_event = self._runtime_stream_stop_events.pop(stream_key, None)
        if stop_event is not None:
            self._runtime_stream_stop_events[new_key] = stop_event

        worker = self._runtime_stream_threads.pop(stream_key, None)
        if worker is not None:
            self._runtime_stream_threads[new_key] = worker

        return new_key


class Libp2pBluetoothTransport:
    """Transport that wraps Bluetooth driver frames with libp2p-style peer envelopes."""

    def __init__(
        self,
        bluetooth_driver: BluetoothDriver | None = None,
        transport_adapter: BluetoothTransportAdapter | None = None,
        session_store: TransportSessionStore | None = None,
    ) -> None:
        self._bluetooth_driver = bluetooth_driver
        self._handler: MessageHandler | None = None
        self._protocol_handlers: dict[str, MessageHandler] = {}
        self._runtime: Any = None
        self._sessions: dict[str, PeerSession] = {}
        self._transport_adapter = transport_adapter or InMemoryBluetoothTransportAdapter()
        self._local_identity: LocalPeerIdentity | None = None
        self._session_store = session_store or FileTransportSessionStore()
        self._persisted_session_cursors: dict[str, PersistedTransportSessionCursor] = {}

    def start(self) -> None:
        """Initialize py-libp2p runtime and wire Bluetooth callbacks."""
        self._persisted_session_cursors = self._session_store.load_all()
        self._runtime = _load_py_libp2p_runtime()
        self._local_identity = self._transport_adapter.bootstrap_runtime(self._runtime)
        set_runtime_inbound_handler = getattr(self._transport_adapter, "set_runtime_inbound_handler", None)
        if set_runtime_inbound_handler is not None:
            set_runtime_inbound_handler(self._handle_runtime_inbound_protocol)
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
        self._bind_protocol_stream(session, protocol)
        self._write_bound_protocol_stream(session, protocol, payload)
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
        persisted_cursor = self._persisted_session_cursors.get(peer_id)
        if persisted_cursor is not None:
            session.peer_ref = persisted_cursor.peer_ref
            session.session_id = persisted_cursor.session_id
            session.resume_token = persisted_cursor.resume_token
            if persisted_cursor.capabilities:
                session.capabilities = persisted_cursor.capabilities
        self._sessions[peer_id] = session
        self._transport_adapter.open_outbound(
            BluetoothTransportConnection(
                peer_ref=session.peer_ref,
                peer_id=session.peer_id,
                session_id=session.session_id,
                resume_token=session.resume_token,
                capabilities=session.capabilities,
            )
        )
        self._persist_session_cursor(session)
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
                    resume_token=session.resume_token,
                    capabilities=session.capabilities,
                )
            )
            self._persist_session_cursor(session)
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
            self._dispatch_protocol_payload(
                session=session,
                protocol=protocol,
                payload=payload,
                message_id=envelope.message_id,
            )
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

    def _handle_runtime_inbound_protocol(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
        payload: bytes,
        message_id: str,
        is_ack: bool = False,
    ) -> None:
        session = self._sessions.get(connection.peer_id)
        if session is None or session.session_id != connection.session_id:
            session = PeerSession(
                peer_id=connection.peer_id,
                peer_ref=connection.peer_ref,
                session_id=connection.session_id,
                resume_token=connection.resume_token or _new_resume_token(),
                state=SessionState.ESTABLISHED,
                capabilities=connection.capabilities,
            )
            self._sessions[connection.peer_id] = session
            self._persist_session_cursor(session)
        else:
            session.peer_ref = connection.peer_ref
            session.session_id = connection.session_id
            if connection.resume_token:
                session.resume_token = connection.resume_token
            if connection.capabilities:
                session.capabilities = connection.capabilities
            self._persist_session_cursor(session)
        if is_ack:
            session.last_acked_message_id = message_id
            self._acknowledge_runtime_message(connection, protocol, message_id, emit_peer_ack=False)
            return
        if message_id in session.seen_message_ids:
            self._acknowledge_runtime_message(connection, protocol, message_id, emit_peer_ack=True)
            return
        session.seen_message_ids.add(message_id)
        self._dispatch_protocol_payload(
            session=session,
            protocol=protocol,
            payload=payload,
            message_id=message_id,
            deliver_adapter=False,
        )
        self._acknowledge_runtime_message(connection, protocol, message_id, emit_peer_ack=True)

    def _send_envelope(self, peer_ref: str, envelope: PeerEnvelope) -> None:
        if self._bluetooth_driver is None:
            raise RuntimeError("Bluetooth driver is not configured for libp2p transport")
        frame = _encode_envelope(envelope)
        self._bluetooth_driver.send_frame(peer_ref, frame)

    def _bind_protocol_stream(self, session: PeerSession, protocol: str) -> None:
        bind_protocol_stream = getattr(self._transport_adapter, "bind_protocol_stream", None)
        if bind_protocol_stream is None:
            return
        bind_protocol_stream(
            BluetoothTransportConnection(
                peer_ref=session.peer_ref,
                peer_id=session.peer_id,
                session_id=session.session_id,
                resume_token=session.resume_token,
                capabilities=session.capabilities,
            ),
            protocol,
        )

    def _write_bound_protocol_stream(self, session: PeerSession, protocol: str, payload: bytes) -> None:
        write_protocol_payload = getattr(self._transport_adapter, "write_protocol_payload", None)
        if write_protocol_payload is None:
            return
        write_protocol_payload(
            BluetoothTransportConnection(
                peer_ref=session.peer_ref,
                peer_id=session.peer_id,
                session_id=session.session_id,
                resume_token=session.resume_token,
                capabilities=session.capabilities,
            ),
            protocol,
            payload,
        )

    def _deliver_inbound_protocol(self, session: PeerSession, protocol: str, payload: bytes) -> None:
        deliver_inbound_protocol = getattr(self._transport_adapter, "deliver_inbound_protocol", None)
        if deliver_inbound_protocol is None:
            return
        deliver_inbound_protocol(
            BluetoothTransportConnection(
                peer_ref=session.peer_ref,
                peer_id=session.peer_id,
                session_id=session.session_id,
                resume_token=session.resume_token,
                capabilities=session.capabilities,
            ),
            protocol,
            payload,
        )

    def _dispatch_protocol_payload(
        self,
        session: PeerSession,
        protocol: str,
        payload: bytes,
        message_id: str,
        deliver_adapter: bool = True,
    ) -> None:
        if deliver_adapter:
            self._deliver_inbound_protocol(session, protocol, payload)
        session.last_message_id = message_id
        handler = self._protocol_handlers.get(protocol)
        if handler is not None:
            handler(session.peer_id, payload)
        elif self._handler is not None:
            self._handler(session.peer_id, payload)

    def _acknowledge_runtime_message(
        self,
        connection: BluetoothTransportConnection,
        protocol: str,
        message_id: str,
        emit_peer_ack: bool = False,
    ) -> None:
        acknowledge_runtime_message = getattr(self._transport_adapter, "acknowledge_runtime_message", None)
        if acknowledge_runtime_message is None:
            return
        acknowledge_runtime_message(connection, protocol, message_id, emit_peer_ack=emit_peer_ack)

    def _persist_session_cursor(self, session: PeerSession) -> None:
        cursor = PersistedTransportSessionCursor(
            peer_id=session.peer_id,
            peer_ref=session.peer_ref,
            session_id=session.session_id,
            resume_token=session.resume_token,
            capabilities=session.capabilities,
            updated_at_ms=_timestamp_ms(),
        )
        self._persisted_session_cursors[session.peer_id] = cursor
        self._session_store.save(cursor)

    def list_persisted_session_cursors(self) -> list[PersistedTransportSessionCursor]:
        """List persisted transport session cursors currently known to the transport."""
        return list(self._persisted_session_cursors.values())

    def clear_persisted_session_cursor(self, peer_id: str) -> bool:
        """Remove a persisted session cursor and any active in-memory session for a peer."""
        removed = False
        session = self._sessions.pop(peer_id, None)
        if session is not None:
            removed = True
            self._transport_adapter.close(session.peer_ref, session.session_id)
        if peer_id in self._persisted_session_cursors:
            removed = True
            self._persisted_session_cursors.pop(peer_id, None)
        self._session_store.delete(peer_id)
        return removed


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


def _coerce_runtime_peer_id(runtime_stream: Any) -> str | None:
    peer_id = getattr(runtime_stream, "peer_id", None)
    if isinstance(peer_id, str) and peer_id:
        return peer_id

    connection = getattr(runtime_stream, "connection", None)
    connection_peer_id = getattr(connection, "peer_id", None)
    if isinstance(connection_peer_id, str) and connection_peer_id:
        return connection_peer_id

    return None


def _read_runtime_stream_payload(runtime_stream: Any) -> bytes:
    payload = getattr(runtime_stream, "payload", None)
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")

    read = getattr(runtime_stream, "read", None)
    if read is None:
        return b""

    try:
        payload = read()
    except TypeError:
        return b""

    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return b""


def _read_runtime_stream_chunk(runtime_stream: Any, size: int = MAX_FRAME_BYTES) -> bytes:
    _, payload, _, _, _, _ = _read_runtime_stream_message(runtime_stream, size=size)
    return payload


def _read_runtime_stream_message(
    runtime_stream: Any,
    size: int = MAX_FRAME_BYTES,
) -> tuple[str | None, bytes, bool, str | None, str | None, str | None]:
    read = getattr(runtime_stream, "read", None)
    if read is None:
        return None, b"", False, None, None, None

    try:
        payload = read(size)
    except TypeError:
        payload = read()

    payload = _resolve_runtime_value(payload)
    if isinstance(payload, tuple) and len(payload) == 3:
        message_id, chunk, is_ack = payload
        if isinstance(message_id, str):
            return message_id, _coerce_runtime_payload_bytes(chunk), bool(is_ack), None, None, None
        return None, _coerce_runtime_payload_bytes(chunk), bool(is_ack), None, None, None
    if isinstance(payload, tuple) and len(payload) == 2:
        message_id, chunk = payload
        if isinstance(message_id, str):
            payload_bytes, is_ack, session_id, protocol, resume_token = _decode_runtime_stream_frame(chunk)
            if payload_bytes is not None:
                return message_id, payload_bytes, is_ack, session_id, protocol, resume_token
            payload_bytes = _coerce_runtime_payload_bytes(chunk)
            return message_id, payload_bytes, False, None, None, None
        payload_bytes, is_ack, session_id, protocol, resume_token = _decode_runtime_stream_frame(chunk)
        if payload_bytes is not None:
            return None, payload_bytes, is_ack, session_id, protocol, resume_token
        return None, _coerce_runtime_payload_bytes(chunk), False, None, None, None
    payload_bytes, is_ack, session_id, protocol, resume_token = _decode_runtime_stream_frame(payload)
    if payload_bytes is not None:
        return None, payload_bytes, is_ack, session_id, protocol, resume_token
    return None, _coerce_runtime_payload_bytes(payload), False, None, None, None


def _coerce_runtime_payload_bytes(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return b""


def _encode_runtime_stream_message(
    message_id: str,
    session_id: str,
    protocol: str,
    resume_token: str | None,
    payload: bytes,
) -> bytes:
    frame = {
        "kind": "message",
        "message_id": message_id,
        "protocol_id": RUNTIME_STREAM_PROTOCOL_ID,
        "session_id": session_id,
        "protocol": protocol,
        "resume_token": resume_token,
        "payload_b64": _encode_payload(payload),
    }
    return json.dumps(frame, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _encode_runtime_stream_ack(
    message_id: str,
    session_id: str,
    protocol: str,
    resume_token: str | None,
) -> bytes:
    frame = {
        "kind": "ack",
        "acked_message_id": message_id,
        "protocol_id": RUNTIME_STREAM_PROTOCOL_ID,
        "session_id": session_id,
        "protocol": protocol,
        "resume_token": resume_token,
    }
    return json.dumps(frame, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_runtime_stream_frame(payload: Any) -> tuple[bytes | None, bool, str | None, str | None, str | None]:
    raw = _coerce_runtime_payload_bytes(payload)
    if not raw:
        return None, False, None, None, None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, False, None, None, None
    if not isinstance(data, dict):
        return None, False, None, None, None
    if data.get("protocol_id") != RUNTIME_STREAM_PROTOCOL_ID:
        return None, False, None, None, None
    session_id = data.get("session_id") if isinstance(data.get("session_id"), str) else None
    protocol = data.get("protocol") if isinstance(data.get("protocol"), str) else None
    resume_token = data.get("resume_token") if isinstance(data.get("resume_token"), str) else None
    kind = data.get("kind")
    if kind == "message":
        return _decode_payload(data.get("payload_b64")), False, session_id, protocol, resume_token
    if kind == "ack":
        acked_message_id = data.get("acked_message_id")
        if isinstance(acked_message_id, str) and acked_message_id:
            return acked_message_id.encode("utf-8"), True, session_id, protocol, resume_token
    return None, False, None, None, None


def _resolve_runtime_value(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value

    try:
        trio = __import__("trio")
    except ImportError:
        return value

    async def _await_value() -> Any:
        return await value

    try:
        return trio.run(_await_value)
    except RuntimeError:
        return value


def _close_runtime_stream(runtime_stream: Any) -> None:
    if runtime_stream is None:
        return

    close = getattr(runtime_stream, "close", None)
    if close is not None:
        try:
            _resolve_runtime_value(close())
            return
        except Exception:
            pass

    reset = getattr(runtime_stream, "reset", None)
    if reset is not None:
        try:
            _resolve_runtime_value(reset())
        except Exception:
            return


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


def encode_chat_message_payload(
    text: str,
    sender_peer_id: str | None = None,
    conversation_id: str | None = None,
    priority: str | None = None,
    timestamp_ms: int | None = None,
    task_snapshot: dict[str, Any] | None = None,
) -> bytes:
    """Encode a HandsFree chat protocol payload."""
    if not text:
        raise TransportEnvelopeError("Chat payload text cannot be empty")
    payload: dict[str, Any] = {
        "type": "chat",
        "text": text,
        "timestamp_ms": timestamp_ms or _timestamp_ms(),
    }
    if sender_peer_id:
        payload["sender_peer_id"] = sender_peer_id
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if priority:
        if priority not in {"normal", "urgent"}:
            raise TransportEnvelopeError("Chat payload priority must be 'normal' or 'urgent'")
        payload["priority"] = priority
    if task_snapshot is not None:
        if not isinstance(task_snapshot, dict):
            raise TransportEnvelopeError("Chat payload task_snapshot must be an object")
        payload["task_snapshot"] = task_snapshot
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
    timestamp_ms = data.get("timestamp_ms")
    if not isinstance(timestamp_ms, int) or timestamp_ms <= 0:
        raise TransportEnvelopeError("Chat payload timestamp_ms must be a positive integer")
    priority = data.get("priority", "normal")
    if not isinstance(priority, str) or priority not in {"normal", "urgent"}:
        raise TransportEnvelopeError("Chat payload priority must be 'normal' or 'urgent'")
    task_snapshot = data.get("task_snapshot")
    if task_snapshot is not None and not isinstance(task_snapshot, dict):
        raise TransportEnvelopeError("Chat payload task_snapshot must be an object")
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
