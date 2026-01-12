"""Replay a webhook fixture into a local backend.

Usage:
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
    --event-type pull_request
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
    --delivery-id my-test-001

The script will:
- Infer X-GitHub-Event from filename if not provided
  (e.g., pull_request.opened.json -> pull_request)
- Generate a unique delivery ID if not provided
- Send the webhook to http://localhost:8080/v1/webhooks/github
"""

import argparse
import json
import pathlib
import sys
import urllib.request
import uuid


def infer_event_type_from_filename(filename: str) -> str:
    """Infer GitHub event type from fixture filename.

    Example: pull_request.opened.json -> pull_request
    """
    name = pathlib.Path(filename).stem
    # Get first part before the dot (e.g., "pull_request" from "pull_request.opened")
    return name.split(".")[0]


def main():
    parser = argparse.ArgumentParser(description="Replay a GitHub webhook fixture to local backend")
    parser.add_argument(
        "fixture_path",
        help="Path to webhook fixture JSON file",
    )
    parser.add_argument(
        "--event-type",
        "-e",
        help="GitHub event type (inferred from filename if not provided)",
    )
    parser.add_argument(
        "--delivery-id",
        "-d",
        help="GitHub delivery ID (generated if not provided)",
    )
    parser.add_argument(
        "--url",
        "-u",
        default="http://localhost:8080/v1/webhooks/github",
        help="Webhook endpoint URL (default: http://localhost:8080/v1/webhooks/github)",
    )
    parser.add_argument(
        "--signature",
        "-s",
        default="dev",
        help="Signature value (default: dev)",
    )

    args = parser.parse_args()

    path = pathlib.Path(args.fixture_path)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))

    # Infer event type from filename if not provided
    event_type = args.event_type or infer_event_type_from_filename(path.name)

    # Generate delivery ID if not provided
    delivery_id = args.delivery_id or f"replay-{uuid.uuid4()}"

    print("Replaying webhook:")
    print(f"  File: {path}")
    print(f"  Event type: {event_type}")
    print(f"  Delivery ID: {delivery_id}")
    print(f"  URL: {args.url}")

    req = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": event_type,
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": args.signature,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"\nResponse: {resp.status}")
            response_body = resp.read().decode("utf-8")
            if response_body:
                print(json.dumps(json.loads(response_body), indent=2))
        return 0
    except urllib.error.HTTPError as e:
        print(f"\nError: {e.code} {e.reason}")
        error_body = e.read().decode("utf-8")
        if error_body:
            try:
                print(json.dumps(json.loads(error_body), indent=2))
            except json.JSONDecodeError:
                print(error_body)
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
