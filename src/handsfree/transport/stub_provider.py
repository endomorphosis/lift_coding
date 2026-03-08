"""Safe stub transport provider for local development and CI."""

from handsfree.transport import DEFAULT_PROTOCOL, MessageHandler


class StubTransportProvider:
    """In-memory no-op transport provider."""

    def __init__(self) -> None:
        self._handler: MessageHandler | None = None
        self._protocol_handlers: dict[str, MessageHandler] = {}
        self.sent_messages: list[tuple[str, bytes]] = []
        self.sent_protocol_messages: list[tuple[str, str, bytes]] = []

    def start(self) -> None:
        """Start stub transport (no-op)."""

    def register_handler(self, handler: MessageHandler) -> None:
        """Register inbound message handler."""
        self._handler = handler

    def send(self, peer_id: str, payload: bytes) -> None:
        """Record sent message for observability/testing."""
        self.sent_messages.append((peer_id, payload))

    def register_protocol_handler(self, protocol: str, handler: MessageHandler) -> None:
        """Register protocol-scoped handler in the stub provider."""
        self._protocol_handlers[protocol] = handler

    def send_protocol_message(self, peer_id: str, protocol: str, payload: bytes) -> None:
        """Record protocol-scoped message for observability/testing."""
        if not protocol:
            protocol = DEFAULT_PROTOCOL
        self.sent_protocol_messages.append((peer_id, protocol, payload))
