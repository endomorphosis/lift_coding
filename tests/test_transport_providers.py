"""Tests for transport provider selection and libp2p bluetooth wrapper behavior."""

import inspect
import sys
import threading
import time
from json import dumps, loads
from unittest.mock import MagicMock

import pytest
import trio


@pytest.fixture
def mock_libp2p_runtime(monkeypatch):
    monkeypatch.setitem(sys.modules, "libp2p", MagicMock())


def test_get_transport_provider_default_stub():
    from handsfree.transport import get_transport_provider
    from handsfree.transport.stub_provider import StubTransportProvider

    provider = get_transport_provider()
    assert isinstance(provider, StubTransportProvider)


def test_get_transport_provider_libp2p_fallback(monkeypatch):
    monkeypatch.setenv("HANDSFREE_TRANSPORT_PROVIDER", "libp2p_bluetooth")

    from handsfree.transport import libp2p_bluetooth

    def raise_import_error(name: str):
        raise ImportError(name)

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", raise_import_error)

    from handsfree.transport import get_transport_provider
    from handsfree.transport.stub_provider import StubTransportProvider

    provider = get_transport_provider()
    assert isinstance(provider, StubTransportProvider)


def test_libp2p_transport_send_and_receive(mock_libp2p_runtime):
    from handsfree.transport import DEFAULT_PROTOCOL
    from handsfree.transport.libp2p_bluetooth import (
        InMemoryBluetoothTransportAdapter,
        Libp2pBluetoothTransport,
        decode_transport_payload,
    )

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None
            self.started = False

        def start(self) -> None:
            self.started = True

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler):
            self._handler = handler

        def emit(self, peer_ref: str, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(peer_ref, frame)

    driver = FakeBluetoothDriver()
    adapter = InMemoryBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver, transport_adapter=adapter)
    transport.start()
    assert driver.started is True

    received: list[tuple[str, bytes]] = []
    transport.register_handler(lambda peer_id, payload: received.append((peer_id, payload)))

    transport.send("peerA", b"hello")
    assert len(driver.frames) == 2

    handshake_peer_ref, handshake_frame = driver.frames[0]
    message_peer_ref, message_frame = driver.frames[1]
    assert handshake_peer_ref == "peerA"
    assert message_peer_ref == "peerA"
    assert ("peerA", transport._sessions["peerA"].session_id) in adapter.connections

    driver.emit("peerA", handshake_frame)
    driver.emit("peerA", message_frame)
    assert received == [("peerA", b"hello")]
    assert len(driver.frames) == 3

    ack_peer_ref, ack_frame = driver.frames[2]
    assert ack_peer_ref == "peerA"
    assert loads(ack_frame.decode("utf-8"))["kind"] == "ack"
    assert ("peerA", transport._sessions["peerA"].session_id) in adapter.connections

    message_envelope = loads(message_frame.decode("utf-8"))
    wrapped_payload = decode_transport_payload(message_envelope["payload_b64"])
    protocol_wrapper = loads(wrapped_payload.decode("utf-8"))
    assert protocol_wrapper["protocol"] == DEFAULT_PROTOCOL


def test_libp2p_transport_validates_inputs(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

    class FakeBluetoothDriver:
        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            pass

        def set_frame_handler(self, handler) -> None:
            pass

    transport = Libp2pBluetoothTransport(bluetooth_driver=FakeBluetoothDriver())
    transport.start()

    with pytest.raises(ValueError, match="peer_id cannot be empty"):
        transport.send("", b"hello")

    with pytest.raises(ValueError, match="payload cannot be empty"):
        transport.send("peerA", b"")


def test_libp2p_transport_rejects_unsupported_protocol_version(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        PROTOCOL_MAJOR,
        ProtocolVersionError,
    )

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

        def emit(self, peer_ref: str, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(peer_ref, frame)

    driver = FakeBluetoothDriver()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver)
    transport.start()
    transport.send("peerA", b"hello")

    _, handshake_frame = driver.frames[0]
    envelope = loads(handshake_frame.decode("utf-8"))
    envelope["version_major"] = PROTOCOL_MAJOR + 1
    invalid_frame = dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")

    with pytest.raises(ProtocolVersionError, match="Unsupported protocol major version"):
        driver.emit("peerA", invalid_frame)


def test_libp2p_transport_replays_ack_for_duplicate_message(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

        def emit(self, peer_ref: str, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(peer_ref, frame)

    driver = FakeBluetoothDriver()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver)
    transport.start()

    received: list[tuple[str, bytes]] = []
    transport.register_handler(lambda peer_id, payload: received.append((peer_id, payload)))

    transport.send("peerA", b"hello")
    _, handshake_frame = driver.frames[0]
    _, message_frame = driver.frames[1]

    driver.emit("peerA", handshake_frame)
    driver.emit("peerA", message_frame)
    driver.emit("peerA", message_frame)

    assert received == [("peerA", b"hello")]
    assert len(driver.frames) == 4
    assert loads(driver.frames[2][1].decode("utf-8"))["kind"] == "ack"
    assert loads(driver.frames[3][1].decode("utf-8"))["kind"] == "ack"


def test_libp2p_transport_routes_protocol_messages(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

        def emit(self, peer_ref: str, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(peer_ref, frame)

    driver = FakeBluetoothDriver()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver)
    transport.start()

    default_received: list[tuple[str, bytes]] = []
    protocol_received: list[tuple[str, bytes]] = []
    transport.register_handler(lambda peer_id, payload: default_received.append((peer_id, payload)))
    transport.register_protocol_handler(
        "/handsfree/chat/1.0.0",
        lambda peer_id, payload: protocol_received.append((peer_id, payload)),
    )

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")
    _, handshake_frame = driver.frames[0]
    _, message_frame = driver.frames[1]

    driver.emit("peerA", handshake_frame)
    driver.emit("peerA", message_frame)

    assert protocol_received == [("peerA", b"chat-hello")]
    assert default_received == []


def test_runtime_transport_adapter_bootstraps_local_identity(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        RuntimeBluetoothTransportAdapter,
    )

    class FakeBluetoothDriver:
        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            pass

        def set_frame_handler(self, handler) -> None:
            pass

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            class FakeHost:
                @staticmethod
                def get_id():
                    return "12D3KooWHostPeerId"

            return FakeHost()

        @staticmethod
        def get_default_muxer():
            return "YAMUX"

        @staticmethod
        def get_supported_transport_protocols():
            return ["/tcp", "/quic"]

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    adapter = RuntimeBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(
        bluetooth_driver=FakeBluetoothDriver(),
        transport_adapter=adapter,
    )
    transport.start()

    identity = transport.get_local_identity()
    assert identity is not None
    assert identity.peer_id == "12D3KooWHostPeerId"
    assert identity.host_enabled is True
    assert identity.muxer == "YAMUX"
    assert identity.transport_protocols == ("/tcp", "/quic")
    assert adapter.host is not None


def test_protocol_routing_adapter_binds_outbound_streams(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
    )

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    driver = FakeBluetoothDriver()
    adapter = ProtocolRoutingBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver, transport_adapter=adapter)
    transport.start()

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")

    session = transport._sessions["peerA"]
    assert (session.peer_ref, session.session_id, "/handsfree/chat/1.0.0") in adapter.streams


def test_protocol_routing_adapter_delivers_inbound_stream_payloads(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
    )

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

        def emit(self, peer_ref: str, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(peer_ref, frame)

    driver = FakeBluetoothDriver()
    adapter = ProtocolRoutingBluetoothTransportAdapter()
    delivered: list[tuple[str, bytes]] = []
    adapter.register_protocol_stream_handler(
        "/handsfree/chat/1.0.0",
        lambda stream, payload: delivered.append((stream.protocol, payload)),
    )
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver, transport_adapter=adapter)
    transport.start()

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")
    _, handshake_frame = driver.frames[0]
    _, message_frame = driver.frames[1]

    driver.emit("peerA", handshake_frame)
    driver.emit("peerA", message_frame)

    assert delivered == [("/handsfree/chat/1.0.0", b"chat-hello")]


def test_protocol_routing_adapter_cleans_up_streams_on_close(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
    )

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    driver = FakeBluetoothDriver()
    adapter = ProtocolRoutingBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver, transport_adapter=adapter)
    transport.start()

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")

    session = transport._sessions["peerA"]
    stream_key = (session.peer_ref, session.session_id, "/handsfree/chat/1.0.0")
    connection_key = (session.peer_ref, session.session_id)

    assert stream_key in adapter.streams
    assert connection_key in adapter.connections

    adapter.close(session.peer_ref, session.session_id)

    assert stream_key not in adapter.streams
    assert connection_key not in adapter.connections


def test_protocol_routing_adapter_registers_runtime_host_protocol_handler(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import ProtocolRoutingBluetoothTransportAdapter

    registered_handlers: dict[str, object] = {}

    class FakeHost:
        def set_stream_handler(self, protocol, handler) -> None:
            registered_handlers[protocol] = handler

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    adapter = ProtocolRoutingBluetoothTransportAdapter()
    delivered: list[tuple[str, str, bytes]] = []
    adapter.register_protocol_stream_handler(
        "/handsfree/chat/1.0.0",
        lambda stream, payload: delivered.append((stream.peer_id, stream.protocol, payload)),
    )

    identity = adapter.bootstrap_runtime(FakeRuntime)
    assert identity is not None
    assert "/handsfree/chat/1.0.0" in registered_handlers
    assert inspect.iscoroutinefunction(registered_handlers["/handsfree/chat/1.0.0"])

    class FakeRuntimeStream:
        peer_id = "runtime-peer-A"
        payload = b"runtime-chat"

    trio.run(registered_handlers["/handsfree/chat/1.0.0"], FakeRuntimeStream())
    assert delivered == [("runtime-peer-A", "/handsfree/chat/1.0.0", b"runtime-chat")]


def test_protocol_routing_adapter_opens_runtime_host_streams(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
        decode_transport_payload,
    )

    opened_streams: list[tuple[str, tuple[str, ...]]] = []
    written_payloads: list[bytes] = []

    class FakeRuntimeStream:
        def __init__(self, peer_id: str, protocol: str) -> None:
            self.peer_id = peer_id
            self.protocol = protocol

        async def write(self, payload: bytes) -> None:
            written_payloads.append(payload)

    class FakeHost:
        async def new_stream(self, peer_id, protocols):
            protocol_tuple = tuple(protocols)
            opened_streams.append((peer_id, protocol_tuple))
            return FakeRuntimeStream(peer_id, protocol_tuple[0])

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    driver = FakeBluetoothDriver()
    adapter = ProtocolRoutingBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver, transport_adapter=adapter)
    transport.start()

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")

    session = transport._sessions["peerA"]
    stream = adapter.streams[(session.peer_ref, session.session_id, "/handsfree/chat/1.0.0")]

    assert opened_streams == [("peerA", ("/handsfree/chat/1.0.0",))]
    assert stream.runtime_stream is not None
    assert stream.runtime_stream.peer_id == "peerA"
    assert stream.outbound_payloads == [b"chat-hello"]
    assert len(stream.outbound_message_ids) == 1
    written_frame = loads(written_payloads[0].decode("utf-8"))
    assert written_frame["kind"] == "message"
    assert written_frame["message_id"] == stream.outbound_message_ids[0]
    assert written_frame["session_id"] == session.session_id
    assert written_frame["protocol"] == "/handsfree/chat/1.0.0"
    assert written_frame["resume_token"] == session.resume_token
    assert decode_transport_payload(written_frame["payload_b64"]) == b"chat-hello"


def test_protocol_routing_adapter_reuses_bound_runtime_stream(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
        decode_transport_payload,
    )

    opened_streams: list[tuple[str, tuple[str, ...]]] = []
    written_payloads: list[bytes] = []

    class FakeRuntimeStream:
        peer_id = "peerA"

        async def write(self, payload: bytes) -> None:
            written_payloads.append(payload)

    class FakeHost:
        async def new_stream(self, peer_id, protocols):
            opened_streams.append((peer_id, tuple(protocols)))
            return FakeRuntimeStream()

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    transport = Libp2pBluetoothTransport(
        bluetooth_driver=FakeBluetoothDriver(),
        transport_adapter=ProtocolRoutingBluetoothTransportAdapter(),
    )
    transport.start()

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"first")
    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"second")

    session = transport._sessions["peerA"]
    stream = transport._transport_adapter.streams[
        (session.peer_ref, session.session_id, "/handsfree/chat/1.0.0")
    ]

    assert opened_streams == [("peerA", ("/handsfree/chat/1.0.0",))]
    assert stream.outbound_payloads == [b"first", b"second"]
    assert len(stream.outbound_message_ids) == 2
    decoded_payloads = [
        decode_transport_payload(loads(payload.decode("utf-8"))["payload_b64"])
        for payload in written_payloads
    ]
    assert decoded_payloads == [b"first", b"second"]
    decoded_frames = [loads(payload.decode("utf-8")) for payload in written_payloads]
    assert [frame["session_id"] for frame in decoded_frames] == [session.session_id, session.session_id]
    assert [frame["protocol"] for frame in decoded_frames] == [
        "/handsfree/chat/1.0.0",
        "/handsfree/chat/1.0.0",
    ]
    assert [frame["resume_token"] for frame in decoded_frames] == [
        session.resume_token,
        session.resume_token,
    ]


def test_protocol_routing_adapter_closes_runtime_stream_on_close(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
    )

    close_calls: list[str] = []

    class FakeRuntimeStream:
        async def close(self) -> None:
            close_calls.append("closed")

    class FakeHost:
        async def new_stream(self, peer_id, protocols):
            return FakeRuntimeStream()

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    adapter = ProtocolRoutingBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(
        bluetooth_driver=FakeBluetoothDriver(),
        transport_adapter=adapter,
    )
    transport.start()
    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")

    session = transport._sessions["peerA"]
    adapter.close(session.peer_ref, session.session_id)

    assert close_calls == ["closed"]


def test_protocol_routing_adapter_reads_inbound_runtime_stream_payloads(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
        RUNTIME_STREAM_PROTOCOL_ID,
    )

    inbound_event = threading.Event()
    transport_event = threading.Event()
    delivered: list[bytes] = []
    transport_delivered: list[tuple[str, bytes]] = []
    written_payloads: list[bytes] = []

    class FakeRuntimeStream:
        peer_id = "peerA"

        def __init__(self) -> None:
            self._reads = [
                (
                    "runtime-outbound-1",
                    b'{"acked_message_id":"runtime-outbound-1","kind":"ack","protocol_id":"/handsfree/runtime-stream/1.0.0"}',
                ),
                ("runtime-msg-1", b"runtime-inbound"),
                ("runtime-msg-1", b"runtime-inbound"),
                b"",
            ]

        async def read(self, size=None) -> bytes:
            return self._reads.pop(0) if self._reads else b""

        async def write(self, payload: bytes) -> None:
            written_payloads.append(payload)

        async def close(self) -> None:
            return None

    class FakeHost:
        async def new_stream(self, peer_id, protocols):
            return FakeRuntimeStream()

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    adapter = ProtocolRoutingBluetoothTransportAdapter()
    adapter.register_protocol_stream_handler(
        "/handsfree/chat/1.0.0",
        lambda stream, payload: (delivered.append(payload), inbound_event.set()),
    )
    transport = Libp2pBluetoothTransport(
        bluetooth_driver=FakeBluetoothDriver(),
        transport_adapter=adapter,
    )
    transport.start()
    transport.register_protocol_handler(
        "/handsfree/chat/1.0.0",
        lambda peer_id, payload: (
            transport_delivered.append((peer_id, payload)),
            transport_event.set(),
        ),
    )

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"chat-hello")

    assert inbound_event.wait(timeout=1.0)
    assert transport_event.wait(timeout=1.0)
    session = transport._sessions["peerA"]
    stream = adapter.streams[(session.peer_ref, session.session_id, "/handsfree/chat/1.0.0")]
    adapter.close(session.peer_ref, session.session_id)

    assert delivered == [b"runtime-inbound"]
    assert stream.inbound_payloads == [b"runtime-inbound"]
    assert stream.inbound_message_ids == ["runtime-msg-1"]
    assert stream.acked_message_ids == ["runtime-outbound-1", "runtime-msg-1"]
    assert transport_delivered == [("peerA", b"runtime-inbound")]
    assert session.last_acked_message_id == "runtime-outbound-1"
    assert len(written_payloads) >= 2
    ack_frame = loads(written_payloads[-1].decode("utf-8"))
    assert ack_frame == {
        "acked_message_id": "runtime-msg-1",
        "kind": "ack",
        "protocol": "/handsfree/chat/1.0.0",
        "protocol_id": RUNTIME_STREAM_PROTOCOL_ID,
        "resume_token": session.resume_token,
        "session_id": session.session_id,
    }


def test_runtime_stream_metadata_reconstitutes_session_after_local_reset(monkeypatch):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
        _encode_runtime_stream_message,
    )

    resumed_event = threading.Event()
    allow_read_event = threading.Event()
    resumed_messages: list[tuple[str, bytes]] = []
    resumed_session_id = "resumed-session-1"
    resumed_resume_token = "resume-token-1"

    class FakeRuntimeStream:
        peer_id = "peerA"

        def __init__(self) -> None:
            self._reads = [
                _encode_runtime_stream_message(
                    message_id="runtime-resume-1",
                    session_id=resumed_session_id,
                    protocol="/handsfree/chat/1.0.0",
                    resume_token=resumed_resume_token,
                    payload=b"resumed-runtime-message",
                ),
                b"",
            ]

        async def read(self, size=None) -> bytes:
            allow_read_event.wait(timeout=1.0)
            return self._reads.pop(0) if self._reads else b""

        async def write(self, payload: bytes) -> None:
            return None

        async def close(self) -> None:
            return None

    class FakeHost:
        async def new_stream(self, peer_id, protocols):
            return FakeRuntimeStream()

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    adapter = ProtocolRoutingBluetoothTransportAdapter()
    transport = Libp2pBluetoothTransport(
        bluetooth_driver=FakeBluetoothDriver(),
        transport_adapter=adapter,
    )
    transport.start()
    transport.register_protocol_handler(
        "/handsfree/chat/1.0.0",
        lambda peer_id, payload: (
            resumed_messages.append((peer_id, payload)),
            resumed_event.set(),
        ),
    )

    transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"bootstrap")
    transport._sessions.clear()
    adapter.streams.clear()

    allow_read_event.set()

    assert resumed_event.wait(timeout=1.0)
    assert resumed_messages == [("peerA", b"resumed-runtime-message")]
    assert transport._sessions["peerA"].session_id == resumed_session_id
    assert transport._sessions["peerA"].resume_token == resumed_resume_token
    deadline = time.time() + 1.0
    while (
        ("peerA", resumed_session_id, "/handsfree/chat/1.0.0") not in adapter.streams
        and time.time() < deadline
    ):
        time.sleep(0.01)
    assert ("peerA", resumed_session_id, "/handsfree/chat/1.0.0") in adapter.streams
    assert adapter.streams[("peerA", resumed_session_id, "/handsfree/chat/1.0.0")].resume_token == resumed_resume_token


def test_file_transport_session_store_persists_cursors(tmp_path):
    from handsfree.transport.libp2p_bluetooth import (
        FileTransportSessionStore,
        PersistedTransportSessionCursor,
    )

    store = FileTransportSessionStore(tmp_path / "transport_sessions.json")
    cursor = PersistedTransportSessionCursor(
        peer_id="peerA",
        peer_ref="peerA",
        session_id="session-1",
        resume_token="resume-1",
        capabilities=("runtime",),
    )

    store.save(cursor)

    reloaded = FileTransportSessionStore(tmp_path / "transport_sessions.json").load_all()
    assert reloaded["peerA"] == cursor


def test_transport_reuses_persisted_session_cursor_across_restart(monkeypatch, tmp_path):
    from handsfree.transport import libp2p_bluetooth
    from handsfree.transport.libp2p_bluetooth import (
        FileTransportSessionStore,
        Libp2pBluetoothTransport,
        ProtocolRoutingBluetoothTransportAdapter,
    )

    class FakeRuntime:
        @staticmethod
        def generate_new_ed25519_identity():
            return object()

        @staticmethod
        def generate_peer_id_from(key_pair):
            return "12D3KooWFakePeerId"

        @staticmethod
        def new_host(key_pair=None):
            class FakeHost:
                async def new_stream(self, peer_id, protocols):
                    class FakeRuntimeStream:
                        def __init__(self, runtime_peer_id: str) -> None:
                            self.peer_id = runtime_peer_id

                        async def write(self, payload: bytes) -> None:
                            return None

                        async def close(self) -> None:
                            return None

                    return FakeRuntimeStream(peer_id)

            return FakeHost()

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[tuple[str, bytes]] = []
            self._handler = None

        def start(self) -> None:
            pass

        def send_frame(self, peer_ref: str, frame: bytes) -> None:
            self.frames.append((peer_ref, frame))

        def set_frame_handler(self, handler) -> None:
            self._handler = handler

    monkeypatch.setattr(libp2p_bluetooth.importlib, "import_module", lambda name: FakeRuntime)

    store_path = tmp_path / "transport_sessions.json"
    first_driver = FakeBluetoothDriver()
    first_transport = Libp2pBluetoothTransport(
        bluetooth_driver=first_driver,
        transport_adapter=ProtocolRoutingBluetoothTransportAdapter(),
        session_store=FileTransportSessionStore(store_path),
    )
    first_transport.start()
    first_transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"first")

    first_session = first_transport._sessions["peerA"]

    second_driver = FakeBluetoothDriver()
    second_transport = Libp2pBluetoothTransport(
        bluetooth_driver=second_driver,
        transport_adapter=ProtocolRoutingBluetoothTransportAdapter(),
        session_store=FileTransportSessionStore(store_path),
    )
    second_transport.start()
    second_transport.send_protocol_message("peerA", "/handsfree/chat/1.0.0", b"second")

    second_session = second_transport._sessions["peerA"]
    assert second_session.session_id == first_session.session_id
    assert second_session.resume_token == first_session.resume_token


def test_duckdb_transport_session_store_persists_cursors(tmp_path):
    from handsfree.db.connection import init_db
    from handsfree.db.transport_session_cursors import DuckDBTransportSessionStore
    from handsfree.transport.libp2p_bluetooth import PersistedTransportSessionCursor

    db_path = tmp_path / "transport_sessions.db"
    conn = init_db(str(db_path))
    store = DuckDBTransportSessionStore(lambda: conn)
    cursor = PersistedTransportSessionCursor(
        peer_id="peerA",
        peer_ref="peerA",
        session_id="session-db-1",
        resume_token="resume-db-1",
        capabilities=("runtime",),
        updated_at_ms=1234567890,
    )

    store.save(cursor)
    loaded = store.load_all()

    assert loaded["peerA"] == cursor
