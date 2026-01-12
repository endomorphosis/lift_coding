"""Replay a webhook fixture into a local backend.

Usage:
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json
"""

import json
import pathlib
import sys
import urllib.request


def main():
    if len(sys.argv) != 2:
        print("Usage: python dev/replay_webhook.py <path-to-json>")
        raise SystemExit(2)

    path = pathlib.Path(sys.argv[1])
    payload = json.loads(path.read_text(encoding="utf-8"))

    req = urllib.request.Request(
        "http://localhost:8080/v1/webhooks/github",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "dev",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(resp.status, resp.read().decode("utf-8"))
    except Exception as e:
        print("Error:", e)
        raise


if __name__ == "__main__":
    main()
