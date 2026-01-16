#!/usr/bin/env python3
"""CLI tool for managing API keys.

This script provides a simple command-line interface for managing API keys
in the HandsFree Dev Companion system.

Usage:
    python scripts/manage_api_keys.py create USER_ID [--label LABEL]
    python scripts/manage_api_keys.py list USER_ID [--include-revoked]
    python scripts/manage_api_keys.py revoke USER_ID KEY_ID
    python scripts/manage_api_keys.py delete USER_ID KEY_ID

Environment Variables:
    DUCKDB_PATH: Path to the DuckDB database file (default: data/handsfree.db)
"""

import argparse
import sys

from handsfree.db.api_keys import (
    create_api_key,
    delete_api_key,
    get_api_keys_by_user,
    revoke_api_key,
)
from handsfree.db.connection import init_db


def cmd_create(args):
    """Create a new API key."""
    db = init_db()
    plaintext_key, api_key = create_api_key(db, args.user_id, label=args.label)

    print("✅ API key created successfully!")
    print(f"\nKey ID: {api_key.id}")
    print(f"User ID: {api_key.user_id}")
    print(f"Label: {api_key.label or '(none)'}")
    print(f"Created: {api_key.created_at}")
    print("\n⚠️  API Key (save this - it will not be shown again):")
    print(f"   {plaintext_key}")
    print()


def cmd_list(args):
    """List API keys for a user."""
    db = init_db()
    keys = get_api_keys_by_user(db, args.user_id, include_revoked=args.include_revoked)

    if not keys:
        print("No API keys found for this user.")
        return

    print(f"API keys for user {args.user_id}:\n")
    for key in keys:
        status = "❌ REVOKED" if key.revoked_at else "✅ ACTIVE"
        print(f"{status} | ID: {key.id}")
        print(f"           Label: {key.label or '(none)'}")
        print(f"           Created: {key.created_at}")
        if key.last_used_at:
            print(f"           Last used: {key.last_used_at}")
        if key.revoked_at:
            print(f"           Revoked: {key.revoked_at}")
        print()


def cmd_revoke(args):
    """Revoke an API key."""
    db = init_db()
    result = revoke_api_key(db, args.key_id)

    if result is None:
        print(f"❌ Error: API key {args.key_id} not found.")
        sys.exit(1)

    if result.user_id != args.user_id:
        print(f"❌ Error: API key {args.key_id} does not belong to user {args.user_id}.")
        sys.exit(1)

    print(f"✅ API key {args.key_id} revoked successfully.")


def cmd_delete(args):
    """Delete an API key permanently."""
    db = init_db()

    # Confirm deletion
    print(f"⚠️  WARNING: This will permanently delete API key {args.key_id}.")
    print("   This action cannot be undone.")
    if not args.yes:
        response = input("   Continue? (yes/no): ")
        if response.lower() != "yes":
            print("   Cancelled.")
            return

    success = delete_api_key(db, args.key_id)

    if not success:
        print(f"❌ Error: API key {args.key_id} not found.")
        sys.exit(1)

    print(f"✅ API key {args.key_id} deleted successfully.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage API keys for HandsFree Dev Companion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("user_id", help="User ID (UUID)")
    create_parser.add_argument("--label", help="Optional label for the key")

    # List command
    list_parser = subparsers.add_parser("list", help="List API keys for a user")
    list_parser.add_argument("user_id", help="User ID (UUID)")
    list_parser.add_argument(
        "--include-revoked",
        action="store_true",
        help="Include revoked keys in the list",
    )

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("user_id", help="User ID (UUID)")
    revoke_parser.add_argument("key_id", help="API key ID (UUID)")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an API key permanently")
    delete_parser.add_argument("user_id", help="User ID (UUID)")
    delete_parser.add_argument("key_id", help="API key ID (UUID)")
    delete_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute command
    commands = {
        "create": cmd_create,
        "list": cmd_list,
        "revoke": cmd_revoke,
        "delete": cmd_delete,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
