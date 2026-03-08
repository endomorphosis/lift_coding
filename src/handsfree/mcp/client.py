"""Minimal MCP++ client scaffold."""

from __future__ import annotations

import json
import logging
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .models import MCPRunStatus, MCPServerConfig, MCPToolInvocationResult

logger = logging.getLogger(__name__)


class MCPClientError(RuntimeError):
    """Base exception for MCP client failures."""


class MCPConfigurationError(MCPClientError):
    """Raised when an MCP provider is selected but not configured."""


class MCPClient:
    """Small HTTP client for MCP++-style servers."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._initialized = False
        self._request_id = 0
        self._process: subprocess.Popen[str] | None = None

    def validate_configuration(self) -> None:
        """Ensure required configuration is present before making requests."""
        if self.config.transport == "stdio":
            if not self.config.command:
                raise MCPConfigurationError(
                    f"MCP stdio command is not configured for server family '{self.config.server_family}'"
                )
            return
        if not self.config.endpoint:
            raise MCPConfigurationError(
                f"MCP endpoint is not configured for server family '{self.config.server_family}'"
            )

    def handshake(self) -> dict[str, Any]:
        """Perform MCP initialize once and cache the result."""
        if self._initialized:
            return {"status": "already_initialized"}

        result = self._rpc_request(
            "initialize",
            {
                "protocolVersion": self.config.protocol_version,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "mcp++": {
                        "profiles": ["handsfree", "agent"],
                    },
                },
                "clientInfo": {
                    "name": self.config.client_name,
                    "version": self.config.client_version,
                },
            },
        )
        self._initialized = True
        return result

    def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        correlation_id: str,
    ) -> MCPToolInvocationResult:
        """Invoke a tool on the remote MCP server."""
        self.handshake()
        response = self._rpc_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments | {"correlation_id": correlation_id},
            },
            method_path_fallback=True,
        )
        result = response.get("result", response)
        content = result.get("content", []) if isinstance(result, dict) else []
        normalized_output = self._normalize_tool_output(result, content)
        return MCPToolInvocationResult(
            request_id=str(response.get("id")) if "id" in response else None,
            run_id=result.get("run_id"),
            status=str(result.get("status", "completed" if not result.get("run_id") else "running")),
            tool_name=str(result.get("tool_name", tool_name)),
            output=result.get("output", normalized_output) if isinstance(result, dict) else normalized_output,
            raw_response=response,
            content=content if isinstance(content, list) else [],
        )

    def list_tools(self) -> list[dict[str, Any]]:
        """List tools exposed by the remote MCP server."""
        self.handshake()
        response = self._rpc_request(
            "tools/list",
            {},
            method_path_fallback=True,
        )
        result = response.get("result", response)
        tools = result.get("tools", []) if isinstance(result, dict) else []
        return [tool for tool in tools if isinstance(tool, dict)]

    def get_run_status(self, run_id: str, correlation_id: str | None = None) -> MCPRunStatus:
        """Fetch the current status for a remote MCP run."""
        self.handshake()
        response = self._rpc_request(
            "runs/status",
            {
                "run_id": run_id,
                "correlation_id": correlation_id,
            },
        )
        result = response.get("result", response)
        return MCPRunStatus(
            run_id=str(result.get("run_id", run_id)),
            status=str(result.get("status", "running")),
            message=result.get("message"),
            output=result.get("output", {}) or {},
            raw_response=response,
        )

    def cancel_run(self, run_id: str, correlation_id: str | None = None) -> dict[str, Any]:
        """Cancel a remote MCP run."""
        self.handshake()
        return self._rpc_request(
            "runs/cancel",
            {
                "run_id": run_id,
                "correlation_id": correlation_id,
            },
        )

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        self.validate_configuration()
        base = self.config.endpoint.rstrip("/")
        url = f"{base}{path}"
        if query:
            query = {k: v for k, v in query.items() if v is not None}
            if query:
                url = f"{url}?{urllib.parse.urlencode(query)}"
        return url

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config.auth_secret:
            headers["Authorization"] = f"Bearer {self.config.auth_secret}"
        return headers

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        return self._request_json("POST", path, data=data)

    def _get_json(self, path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_json("GET", path, query=query)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        data: bytes | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path, query=query)
        request = urllib.request.Request(
            url=url,
            data=data,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_s) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise MCPClientError(
                f"MCP request failed with HTTP {exc.code} for {self.config.server_family}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise MCPClientError(
                f"MCP request failed for {self.config.server_family}: {exc.reason}"
            ) from exc

        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            logger.debug("Invalid MCP JSON response body: %s", body)
            raise MCPClientError(
                f"MCP response for {self.config.server_family} was not valid JSON"
            ) from exc

    def _rpc_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        method_path_fallback: bool = False,
    ) -> dict[str, Any]:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        if self.config.transport == "stdio":
            response = self._stdio_rpc_request(payload)
            if "error" in response:
                error = response["error"] or {}
                raise MCPClientError(
                    f"MCP {method} failed for {self.config.server_family}: "
                    f"{error.get('message', error)}"
                )
            return response

        try:
            response = self._post_json(self.config.rpc_path, payload)
        except MCPClientError as exc:
            if not method_path_fallback or "HTTP 404" not in str(exc):
                raise
            method_path = f"{self.config.rpc_path.rstrip('/')}/{method}"
            response = self._post_json(method_path, payload)

        if "error" in response:
            error = response["error"] or {}
            raise MCPClientError(
                f"MCP {method} failed for {self.config.server_family}: "
                f"{error.get('message', error)}"
            )

        return response

    def _normalize_tool_output(
        self,
        result: dict[str, Any] | Any,
        content: list[dict[str, Any]] | Any,
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            return {"result": result}

        for key in ("output", "structuredContent"):
            value = result.get(key)
            if isinstance(value, dict):
                return value

        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "text":
                    continue
                text = item.get("text")
                if not isinstance(text, str):
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed

        return {"result": result}

    def _ensure_stdio_process(self) -> subprocess.Popen[str]:
        self.validate_configuration()
        if self._process is not None and self._process.poll() is None:
            return self._process

        assert self.config.command is not None
        self._process = subprocess.Popen(
            [self.config.command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        return self._process

    def _stdio_rpc_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        process = self._ensure_stdio_process()
        if process.stdin is None or process.stdout is None:
            raise MCPClientError(
                f"MCP stdio process for {self.config.server_family} does not expose pipes"
            )

        body = json.dumps(payload)
        frame = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        try:
            process.stdin.write(frame)
            process.stdin.flush()
        except OSError as exc:
            raise MCPClientError(
                f"Failed writing to MCP stdio process for {self.config.server_family}: {exc}"
            ) from exc

        expected_id = payload["id"]
        while True:
            response = self._read_stdio_message(process)
            if response.get("id") == expected_id:
                return response
            if "method" in response and "id" not in response:
                logger.debug("Ignoring MCP notification from %s: %s", self.config.server_family, response)
                continue

    def _read_stdio_message(self, process: subprocess.Popen[str]) -> dict[str, Any]:
        assert process.stdout is not None
        headers: dict[str, str] = {}

        while True:
            line = process.stdout.readline()
            if line == "":
                stderr_output = ""
                if process.stderr is not None:
                    try:
                        stderr_output = process.stderr.read()
                    except OSError:
                        stderr_output = ""
                raise MCPClientError(
                    f"MCP stdio process for {self.config.server_family} closed unexpectedly: {stderr_output}"
                )

            stripped = line.strip()
            if not stripped:
                break

            if ":" not in stripped:
                raise MCPClientError(
                    f"Malformed MCP stdio header from {self.config.server_family}: {stripped}"
                )
            key, value = stripped.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        content_length = headers.get("content-length")
        if content_length is None:
            raise MCPClientError(
                f"MCP stdio response from {self.config.server_family} missing Content-Length"
            )

        try:
            length = int(content_length)
        except ValueError as exc:
            raise MCPClientError(
                f"Invalid Content-Length from {self.config.server_family}: {content_length}"
            ) from exc

        body = process.stdout.read(length)
        if len(body) != length:
            raise MCPClientError(
                f"Incomplete MCP stdio response from {self.config.server_family}"
            )

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise MCPClientError(
                f"MCP stdio response for {self.config.server_family} was not valid JSON"
            ) from exc
