#!/usr/bin/env python3
"""
Minimal Agent Runner CLI

A simple command-line interface for running the minimal agent task runner.
This runner processes tasks from the local database and transitions them
through their lifecycle: created -> running -> completed/failed.

Usage:
    # Enable the runner and run once
    HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --once

    # Run in continuous loop mode
    HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --loop --interval 5

    # Run with custom database path
    HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --db-path /path/to/db.duckdb

Environment Variables:
    HANDSFREE_AGENT_RUNNER_ENABLED: Must be set to 'true' to enable the runner
    HANDSFREE_DB_PATH: Path to the DuckDB database (default: handsfree.duckdb)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from handsfree.db.connection import get_connection
from handsfree.agents.runner import run_once, run_loop, is_runner_enabled

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("minimal-agent-runner")


def main():
    """Main entry point for the minimal agent runner CLI."""
    parser = argparse.ArgumentParser(
        description="Minimal agent runner for HandsFree tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: run in loop mode)",
    )
    
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in continuous loop mode",
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Loop interval in seconds (default: 5)",
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB database (default: from HANDSFREE_DB_PATH or handsfree.duckdb)",
    )
    
    args = parser.parse_args()
    
    # Check if runner is enabled
    if not is_runner_enabled():
        logger.error(
            "Agent runner is disabled. Set HANDSFREE_AGENT_RUNNER_ENABLED=true to enable."
        )
        sys.exit(1)
    
    # Set database path if provided
    if args.db_path:
        os.environ["HANDSFREE_DB_PATH"] = args.db_path
    
    # Get database connection
    try:
        conn = get_connection()
        logger.info("Connected to database: %s", os.environ.get("HANDSFREE_DB_PATH", "handsfree.duckdb"))
    except Exception as e:
        logger.error("Failed to connect to database: %s", e)
        sys.exit(1)
    
    try:
        if args.once:
            # Run once and exit
            logger.info("Running agent runner once...")
            result = run_once(conn)
            logger.info("Run completed: %s", result)
            
            # Exit with appropriate code
            if result.get("tasks_failed", 0) > 0:
                logger.warning("Some tasks failed")
                sys.exit(1)
            else:
                sys.exit(0)
        
        elif args.loop:
            # Run in continuous loop
            logger.info("Starting agent runner in loop mode (interval: %d seconds)", args.interval)
            run_loop(conn, interval_seconds=args.interval)
        
        else:
            # Default: run once
            logger.info("No mode specified, running once (use --loop for continuous mode)")
            result = run_once(conn)
            logger.info("Run completed: %s", result)
            sys.exit(0)
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
