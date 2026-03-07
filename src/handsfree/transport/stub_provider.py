"""Safe stub transport provider for local development and CI."""

from handsfree.transport import MessageHandler


class StubTransportProvider:
    """In-memory no-op transport provider."""

    def __init__(self) -> None:
        self._handler: MessageHandler | None = None
        self.sent_messages: list[tuple[str, bytes]] = []

    def start(self) -> None:
        """Start stub transport (no-op)."""

    def register_handler(self, handler: MessageHandler) -> None:
        """Register inbound message handler."""
        self._handler = handler

    def send(self, peer_id: str, payload: bytes) -> None:
        """Record sent message for observability/testing."""
        self.sent_messages.append((peer_id, payload))
