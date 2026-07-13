"""ASGI boundary for the MCP++ Profile H seller control plane.

The seller runtime deliberately has no HTTP dependency. This adapter provides
the normative Profile H REST routes for Hypercorn, FastAPI, and plain ASGI
hosts while retaining the same control-plane dispatch used on libp2p.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl

from .control_plane import ProfileHControlPlane
from .errors import ProfileHError


class ProfileHHttpApp:
    """Expose a :class:`ProfileHControlPlane` as a small, strict ASGI app."""

    def __init__(self, control_plane: ProfileHControlPlane, *, max_body_bytes: int = 1_048_576) -> None:
        if max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        self.control_plane = control_plane
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Mapping[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope.get("type") != "http":
            return
        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        query = dict(parse_qsl(bytes(scope.get("query_string", b"")).decode("utf-8"), keep_blank_values=True))
        try:
            body = await self._body(receive)
            payload = self._json_body(body, method)
            status, headers, result = await self.handle(method, path, query, payload)
        except ProfileHError as error:
            status, headers, result = self._error(error)
        except ValueError as error:
            status, headers, result = 400, {}, {
                "code": "H_REQUEST_MISMATCH", "message": str(error), "retryable": False,
            }
        await self._send(send, status, headers, result)

    async def handle(
        self,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        """Route one validated HTTP request; useful to framework route adapters."""
        params = dict(query or {})
        params.update(dict(payload or {}))
        operation, route_params = self._route(method.upper(), path)
        params.update(route_params)
        result = await self.control_plane.dispatch(operation, params)
        headers: dict[str, str] = {"cache-control": "no-store"}
        if operation == "mcp++/payments/catalog":
            catalog_cid = result.get("signedCatalogCid") or result.get("catalogCid")
            if isinstance(catalog_cid, str) and catalog_cid:
                headers["etag"] = '"' + catalog_cid.replace('"', "") + '"'
        return 200, headers, result

    async def _body(self, receive: Any) -> bytes:
        chunks: list[bytes] = []
        size = 0
        while True:
            event = await receive()
            if event.get("type") == "http.disconnect":
                raise ValueError("request disconnected")
            chunk = event.get("body", b"")
            size += len(chunk)
            if size > self.max_body_bytes:
                raise ValueError("Profile H request body exceeds configured limit")
            chunks.append(chunk)
            if not event.get("more_body"):
                return b"".join(chunks)

    @staticmethod
    def _json_body(body: bytes, method: str) -> Mapping[str, Any]:
        if not body:
            return {}
        if method == "GET":
            raise ValueError("GET Profile H routes do not accept a request body")
        try:
            value = json.loads(body)
        except json.JSONDecodeError as error:
            raise ValueError("Profile H request body must be JSON") from error
        if not isinstance(value, Mapping):
            raise ValueError("Profile H request body must be a JSON object")
        return value

    @staticmethod
    def _route(method: str, path: str) -> tuple[str, dict[str, str]]:
        fixed = {
            ("GET", "/mcp/payments/profile"): "mcp++/payments/profile",
            ("GET", "/mcp/payments/catalog"): "mcp++/payments/catalog",
            ("POST", "/mcp/payments/quote"): "mcp++/payments/quote",
            ("POST", "/mcp/payments/verify"): "mcp++/payments/verify",
            ("POST", "/mcp/payments/settle"): "mcp++/payments/settle",
            ("POST", "/mcp/payments/refunds"): "mcp++/payments/refund/request",
            ("POST", "/mcp/payments/reconcile"): "mcp++/payments/reconcile",
        }
        operation = fixed.get((method, path))
        if operation:
            return operation, {}
        variable = (
            ("/mcp/payments/receipts/", "mcp++/payments/receipt/get", "receipt_cid"),
            ("/mcp/payments/entitlements/", "mcp++/payments/entitlement/get", "entitlement_cid"),
            ("/mcp/payments/usage/", "mcp++/payments/usage/get", "usage_cid"),
        )
        if method == "GET":
            for prefix, name, key in variable:
                if path.startswith(prefix) and path[len(prefix):]:
                    return name, {key: path[len(prefix):]}
        raise ProfileHError("H_METHOD_NOT_SUPPORTED", "unknown Profile H HTTP route")

    @staticmethod
    def _error(error: ProfileHError) -> tuple[int, dict[str, str], dict[str, Any]]:
        status = {
            "H_PAYMENT_POLICY_DENIED": 403,
            "H_EVIDENCE_NOT_FOUND": 404,
            "H_METHOD_NOT_SUPPORTED": 404,
            "H_REQUEST_MISMATCH": 400,
            "H_INVALID_PAYMENT_MESSAGE": 400,
            "H_PAYMENT_REQUIRED": 402,
            "H_PAYMENT_DECLINED": 402,
            "H_QUOTE_EXPIRED": 409,
            "H_PAYMENT_REPLAY": 409,
            "H_RECONCILIATION_REQUIRED": 503,
            "H_FACILITATOR_UNAVAILABLE": 503,
        }.get(error.code, 422)
        return status, {"cache-control": "no-store"}, error.as_dict()

    @staticmethod
    async def _send(send: Any, status: int, headers: Mapping[str, str], result: Mapping[str, Any]) -> None:
        body = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        raw_headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]
        raw_headers.extend((str(name).lower().encode("ascii"), str(value).encode("utf-8")) for name, value in headers.items())
        await send({"type": "http.response.start", "status": status, "headers": raw_headers})
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    async def _lifespan(receive: Any, send: Any) -> None:
        while True:
            event = await receive()
            if event.get("type") == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif event.get("type") == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return


__all__ = ["ProfileHHttpApp"]
