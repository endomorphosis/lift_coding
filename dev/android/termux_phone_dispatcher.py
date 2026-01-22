#!/usr/bin/env python3
"""Termux Phone Dispatcher

A tiny HTTP server intended to run on an Android phone via Termux.

Implements:
- POST /dispatch  {"title": str, "body": str?, "labels": [str]?}

It creates a GitHub issue in DISPATCH_REPO using GITHUB_TOKEN.

Why this exists:
- lets you keep GitHub tokens on the phone
- lets the mobile app call a LAN-local endpoint (see mobile/src/api/phoneDispatcher.js)

Environment:
- GITHUB_TOKEN: GitHub token with repo scope (or fine-grained token with Issues:write on target repo)
- DISPATCH_REPO: owner/repo
- DISPATCHER_SHARED_SECRET: optional shared secret; if set, requests must include header X-Handsfree-Dispatcher-Secret
- PORT: optional, default 8765

Run:
  python termux_phone_dispatcher.py

"""

from __future__ import annotations

import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON")


def create_issue(repo_full_name: str, token: str, title: str, body: str, labels: list[str]) -> dict:
    if "/" not in repo_full_name:
        raise ValueError(
            f"Invalid DISPATCH_REPO format; expected 'owner/repo' but got {repo_full_name!r}"
        )
    owner, repo = repo_full_name.split("/", 1)
    if not owner or not repo:
        raise ValueError(
            f"Invalid DISPATCH_REPO format; expected 'owner/repo' but got {repo_full_name!r}"
        )
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels

    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "handsfree-termux-dispatcher",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error: {e.code} {detail}")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            _json_response(self, 200, {"ok": True})
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/dispatch":
            _json_response(self, 404, {"error": "not found"})
            return

        shared_secret = os.environ.get("DISPATCHER_SHARED_SECRET", "").strip()
        if shared_secret:
            provided = (self.headers.get("X-Handsfree-Dispatcher-Secret") or "").strip()
            if not secrets.compare_digest(provided, shared_secret):
                _json_response(self, 401, {"error": "Unauthorized"})
                return

        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo = os.environ.get("DISPATCH_REPO", "").strip()
        if not token or not repo:
            _json_response(
                self,
                400,
                {"error": "Missing env vars: set GITHUB_TOKEN and DISPATCH_REPO"},
            )
            return

        try:
            payload = _read_json(self)
        except ValueError as e:
            _json_response(self, 400, {"error": str(e)})
            return

        title = str(payload.get("title") or "").strip()
        body = str(payload.get("body") or "")
        labels = payload.get("labels") or []
        if not isinstance(labels, list):
            labels = []
        labels = [str(x) for x in labels if str(x).strip()]

        if not title:
            _json_response(self, 400, {"error": "Missing required field: title"})
            return

        try:
            issue = create_issue(repo, token, title, body, labels)
        except Exception as e:
            _json_response(self, 500, {"error": str(e)})
            return

        _json_response(
            self,
            200,
            {
                "number": issue.get("number"),
                "url": issue.get("html_url"),
                "api_url": issue.get("url"),
            },
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep Termux output readable.
        sys.stdout.write("[dispatcher] " + (format % args) + "\n")


def main() -> int:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8765"))

    httpd = HTTPServer((host, port), Handler)
    print(f"[dispatcher] listening on http://{host}:{port}")
    print("[dispatcher] endpoints: GET /health, POST /dispatch")
    if os.environ.get("DISPATCHER_SHARED_SECRET", "").strip():
        print("[dispatcher] auth: X-Handsfree-Dispatcher-Secret required")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
