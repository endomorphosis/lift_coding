"""Tests for transport provider selection and libp2p bluetooth wrapper behavior."""

import sys
from json import dumps, loads
from unittest.mock import MagicMock

import pytest


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
            return {"host": "ok", "key_pair": key_pair}

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
    assert identity.peer_id == "12D3KooWFakePeerId"
    assert identity.host_enabled is True
    assert identity.muxer == "YAMUX"
    assert identity.transport_protocols == ("/tcp", "/quic")
    assert adapter.host is not None
