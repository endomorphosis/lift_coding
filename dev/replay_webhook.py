"""Replay a webhook fixture into a local backend.

Usage (from fixture file):
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
    --event-type pull_request
  python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
    --delivery-id my-test-001

Usage (from database):
  python dev/replay_webhook.py --from-db <event-id>
  python dev/replay_webhook.py --from-db latest
  python dev/replay_webhook.py --from-db latest --limit 5

The script will:
- Infer X-GitHub-Event from filename if not provided
  (e.g., pull_request.opened.json -> pull_request)
- Generate a unique delivery ID if not provided (or reuse from DB)
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


def replay_from_db(event_id_or_latest: str, url: str, signature: str, limit: int = 1, new_delivery_id: bool = False):
    """Replay webhook event(s) from the database.
    
    Args:
        event_id_or_latest: Event ID to replay, or 'latest' for most recent
        url: Webhook endpoint URL
        signature: Signature to use for replay
        limit: Number of events to replay when using 'latest' (default: 1)
        new_delivery_id: Generate new delivery IDs to avoid duplicate rejection
    """
    # Import here to avoid requiring dependencies when not using --from-db
    try:
        from handsfree.db import init_db
        from handsfree.db.webhook_events import get_webhook_event_by_id, get_webhook_events
    except ImportError as e:
        print(f"Error: Cannot import database modules. Make sure handsfree package is installed.")
        print(f"Details: {e}")
        return 1
    
    # Connect to database
    db = init_db()
    
    # Get event(s) from database
    events = []
    if event_id_or_latest == "latest":
        events = get_webhook_events(db, limit=limit)
        if not events:
            print("Error: No events found in database")
            return 1
    else:
        event = get_webhook_event_by_id(db, event_id_or_latest)
        if not event:
            print(f"Error: Event not found: {event_id_or_latest}")
            return 1
        events = [event]
    
    # Replay each event
    success_count = 0
    for event in events:
        event_type = event.event_type or "unknown"
        delivery_id = event.delivery_id or f"replay-{uuid.uuid4()}"
        
        # Generate new delivery ID if requested (to avoid duplicate rejection)
        if new_delivery_id:
            delivery_id = f"replay-{uuid.uuid4()}"
        
        payload = event.payload or {}
        
        print(f"\nReplaying event {event.id}:")
        print(f"  Original delivery ID: {event.delivery_id}")
        print(f"  Event type: {event_type}")
        print(f"  Delivery ID: {delivery_id}")
        print(f"  Received at: {event.received_at}")
        print(f"  URL: {url}")
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": event_type,
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": signature,
            },
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"  Response: {resp.status}")
                response_body = resp.read().decode("utf-8")
                if response_body:
                    print("  " + json.dumps(json.loads(response_body), indent=2).replace("\n", "\n  "))
                success_count += 1
        except urllib.error.HTTPError as e:
            print(f"  Error: {e.code} {e.reason}")
            error_body = e.read().decode("utf-8")
            if error_body:
                try:
                    print("  " + json.dumps(json.loads(error_body), indent=2).replace("\n", "\n  "))
                except json.JSONDecodeError:
                    print("  " + error_body)
        except Exception as e:
            print(f"  Error: {e}")
    
    db.close()
    print(f"\nReplayed {success_count}/{len(events)} events successfully")
    return 0 if success_count > 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Replay a GitHub webhook fixture to local backend")
    parser.add_argument(
        "fixture_path",
        nargs="?",
        help="Path to webhook fixture JSON file (not required with --from-db)",
    )
    parser.add_argument(
        "--from-db",
        metavar="EVENT_ID",
        help="Replay event from database by ID or 'latest' for most recent",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of events to replay when using --from-db latest (default: 1)",
    )
    parser.add_argument(
        "--new-delivery-id",
        action="store_true",
        help="Generate new delivery IDs to avoid duplicate rejection (for --from-db)",
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

    # Handle DB replay mode
    if args.from_db:
        return replay_from_db(
            args.from_db,
            args.url,
            args.signature,
            limit=args.limit,
            new_delivery_id=args.new_delivery_id,
        )

    # Handle fixture file mode
    if not args.fixture_path:
        parser.error("fixture_path is required when not using --from-db")

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
