"""Peer-to-peer transport abstraction for handset/glasses communication."""

import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)

DEFAULT_PROTOCOL = "/handsfree/app/1.0.0"


class TransportProvider(Protocol):
    """Protocol for transport providers."""

    def start(self) -> None:
        """Initialize transport resources."""
        ...

    def register_handler(self, handler: "MessageHandler") -> None:
        """Register callback for inbound peer messages."""
        ...

    def send(self, peer_id: str, payload: bytes) -> None:
        """Send a binary payload to a peer."""
        ...

    def register_protocol_handler(self, protocol: str, handler: "MessageHandler") -> None:
        """Register a protocol-scoped inbound message handler."""
        ...

    def send_protocol_message(self, peer_id: str, protocol: str, payload: bytes) -> None:
        """Send a protocol-scoped binary payload to a peer."""
        ...


class MessageHandler(Protocol):
    """Callback type for inbound peer messages."""

    def __call__(self, peer_id: str, payload: bytes) -> None:
        ...


def get_transport_provider() -> TransportProvider:
    """Get the configured transport provider.

    Environment variables:
        HANDSFREE_TRANSPORT_PROVIDER: Provider type (default: "stub").
            Supported values: "stub", "libp2p_bluetooth"
    """
    provider_type = os.environ.get("HANDSFREE_TRANSPORT_PROVIDER", "stub").lower()

    if provider_type == "stub":
        return _stub_fallback()
    if provider_type == "libp2p_bluetooth":
        try:
            from handsfree.db.connection import init_db
            from handsfree.db.transport_session_cursors import DuckDBTransportSessionStore
            from handsfree.transport.libp2p_bluetooth import Libp2pBluetoothTransport

            provider = Libp2pBluetoothTransport(
                session_store=DuckDBTransportSessionStore(lambda: init_db())
            )
            provider.start()
            return provider
        except ImportError as exc:
            logger.warning(
                "libp2p bluetooth transport unavailable (%s); falling back to stub provider",
                exc,
            )
        except Exception as exc:
            logger.error(
                "Failed to initialize libp2p bluetooth transport (%s); "
                "falling back to stub provider",
                exc,
            )
    else:
        logger.warning("Unknown transport provider '%s', falling back to stub", provider_type)

    return _stub_fallback()


def _stub_fallback() -> TransportProvider:
    from handsfree.transport.stub_provider import StubTransportProvider

    return StubTransportProvider()
