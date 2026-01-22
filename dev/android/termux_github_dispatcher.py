#!/usr/bin/env python3

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class DispatchHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/dispatch":
            _json_response(self, 404, {"error": "not_found"})
            return

        github_token = os.getenv("GITHUB_TOKEN")
        dispatch_repo = os.getenv("DISPATCH_REPO")
        if not github_token:
            _json_response(self, 400, {"error": "missing_env", "detail": "GITHUB_TOKEN not set"})
            return
        if not dispatch_repo or "/" not in dispatch_repo:
            _json_response(
                self,
                400,
                {
                    "error": "missing_env",
                    "detail": "DISPATCH_REPO not set (expected 'owner/repo')",
                },
            )
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            _json_response(self, 400, {"error": "invalid_json"})
            return

        title = body.get("title")
        issue_body = body.get("body", "")
        labels = body.get("labels")

        if not title or not isinstance(title, str):
            _json_response(self, 400, {"error": "invalid_request", "detail": "title is required"})
            return

        owner, repo = dispatch_repo.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"

        payload: dict[str, Any] = {"title": title, "body": issue_body}
        if isinstance(labels, list) and all(isinstance(x, str) for x in labels):
            payload["labels"] = labels

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "handsfree-termux-dispatcher",
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, headers=headers, json=payload)

            if resp.status_code >= 400:
                _json_response(
                    self,
                    resp.status_code,
                    {
                        "error": "github_error",
                        "status": resp.status_code,
                        "detail": resp.text,
                    },
                )
                return

            data = resp.json()
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "issue_url": data.get("html_url"),
                    "issue_number": data.get("number"),
                    "repo": dispatch_repo,
                },
            )
        except Exception as e:
            _json_response(self, 500, {"error": "exception", "detail": str(e)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep output minimal for Termux.
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal GitHub issue dispatch server for Termux")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), DispatchHandler)
    print(f"[termux-dispatcher] listening on http://{args.host}:{args.port}")
    print("[termux-dispatcher] POST /dispatch  {title, body?, labels?}")
    server.serve_forever()


if __name__ == "__main__":
    main()
