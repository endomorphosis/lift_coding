"""Native HTTP and Profile E/libp2p bindings for a Profile H seller.

Embedding services construct this adapter from their one durable control plane.
The HTTP app can be mounted by any ASGI server; the JSON-RPC handler can be
installed on a libp2p stream or included in an existing MCP request router.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .control_plane import PROFILE_H_METHODS, ProfileHControlPlane
from .errors import ProfileHError
from .http import ProfileHHttpApp


class ProfileHTransportAdapter:
    """Bind one seller authority to native HTTP and JSON-RPC listeners."""

    def __init__(self, control_plane: ProfileHControlPlane, *, max_body_bytes: int = 1_048_576) -> None:
        self.control_plane = control_plane
        self.http = ProfileHHttpApp(control_plane, max_body_bytes=max_body_bytes)

    async def libp2p(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Handle one decoded Profile E JSON-RPC request.

        Framing belongs to the host listener. Seller failures are returned as
        JSON-RPC errors with their stable Profile H code retained in ``data``.
        """
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or request_id is None:
            return self._error(request_id, -32600, "invalid JSON-RPC request")
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(method, str) or not isinstance(params, Mapping):
            return self._error(request_id, -32600, "method and object params are required")
        if method not in PROFILE_H_METHODS:
            return self._error(request_id, -32601, f"unsupported Profile H method: {method}")
        try:
            result = await self.control_plane.dispatch(method, params)
        except ProfileHError as error:
            return self._error(request_id, -32070, str(error), {
                "code": error.code,
                "retryable": error.retryable,
            })
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(
        request_id: Any, code: int, message: str, data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data:
            error["data"] = dict(data)
        return {"jsonrpc": "2.0", "id": request_id, "error": error}


__all__ = ["ProfileHTransportAdapter"]
