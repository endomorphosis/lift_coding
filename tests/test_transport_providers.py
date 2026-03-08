"""Tests for transport provider selection and libp2p bluetooth wrapper behavior."""

import sys
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
    monkeypatch.delitem(sys.modules, "libp2p", raising=False)

    from handsfree.transport import get_transport_provider
    from handsfree.transport.stub_provider import StubTransportProvider

    provider = get_transport_provider()
    assert isinstance(provider, StubTransportProvider)


def test_libp2p_transport_send_and_receive(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

    class FakeBluetoothDriver:
        def __init__(self):
            self.frames: list[bytes] = []
            self._handler = None

        def send_frame(self, frame: bytes) -> None:
            self.frames.append(frame)

        def set_frame_handler(self, handler):
            self._handler = handler

        def emit(self, frame: bytes) -> None:
            assert self._handler is not None
            self._handler(frame)

    driver = FakeBluetoothDriver()
    transport = Libp2pBluetoothTransport(bluetooth_driver=driver)
    transport.start()

    received: list[tuple[str, bytes]] = []
    transport.register_handler(lambda peer_id, payload: received.append((peer_id, payload)))

    transport.send("peerA", b"hello")
    assert len(driver.frames) == 1

    driver.emit(driver.frames[0])
    assert received == [("peerA", b"hello")]


def test_libp2p_transport_validates_inputs(mock_libp2p_runtime):
    from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

    class FakeBluetoothDriver:
        def send_frame(self, frame: bytes) -> None:
            pass

        def set_frame_handler(self, handler) -> None:
            pass

    transport = Libp2pBluetoothTransport(bluetooth_driver=FakeBluetoothDriver())
    transport.start()

    with pytest.raises(ValueError, match="peer_id cannot be empty"):
        transport.send("", b"hello")

    with pytest.raises(ValueError, match="payload cannot be empty"):
        transport.send("peerA", b"")
