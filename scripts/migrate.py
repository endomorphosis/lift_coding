#!/usr/bin/env python3
"""Database migration script for HandsFree.

Usage:
    python scripts/migrate.py [--db-path PATH]
"""

import argparse
import sys
from pathlib import Path

# Add src to path so we can import handsfree
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from handsfree.db import init_db


def main() -> int:
    """Run database migrations."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to database file (default: data/handsfree.db or DUCKDB_PATH env var)",
    )

    args = parser.parse_args()

    try:
        print("Running migrations...")
        conn = init_db(db_path=args.db_path)
        print("Migrations completed successfully")
        print(f"Database: {args.db_path or 'data/handsfree.db'}")
        conn.close()
        return 0
    except Exception as e:
        print(f"Error running migrations: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
