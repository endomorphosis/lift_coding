"""GitHub App installation lifecycle handling.

Manages installation creation/deletion and repository mapping for GitHub Apps.
"""

import logging
from typing import Any

import duckdb

from handsfree.db.github_connections import (
    create_github_connection,
    get_github_connections_by_user,
    update_github_connection,
)
from handsfree.db.repo_subscriptions import (
    create_repo_subscription,
    delete_repo_subscription,
    get_users_for_installation,
)

logger = logging.getLogger(__name__)

# System user ID for installations that can't be mapped to a specific user
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def handle_installation_created(
    conn: duckdb.DuckDBPyConnection,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Handle installation created event.

    Creates or updates a github_connections entry and maps repositories
    to the installation.

    Args:
        conn: Database connection.
        normalized: Normalized webhook event data.
        payload: Raw webhook payload.
    """
    installation_id = normalized.get("installation_id")
    if installation_id is None:
        logger.warning("Installation created event missing installation_id")
        return

    repositories = normalized.get("repositories", [])
    logger.info(
        "Processing installation.created: installation_id=%s, repos=%s",
        installation_id,
        repositories,
    )

    # Try to find existing users with this installation_id
    users = get_users_for_installation(conn, installation_id)

    # If no existing users, create a system-level connection
    # This will be activated when a user explicitly connects later
    if not users:
        logger.info(
            "No existing users for installation_id=%s, creating system connection",
            installation_id,
        )
        users = [SYSTEM_USER_ID]

    # For each user, create/update github_connection and map repositories
    for user_id in users:
        # Check if user already has a connection with this installation_id
        connections = get_github_connections_by_user(conn, user_id)
        existing_connection = None
        for connection in connections:
            if connection.installation_id == installation_id:
                existing_connection = connection
                break

        if existing_connection:
            # Update existing connection
            logger.info(
                "Updating existing connection for user=%s, installation_id=%s",
                user_id,
                installation_id,
            )
            update_github_connection(
                conn,
                existing_connection.id,
                installation_id=installation_id,
            )
        else:
            # Create new connection
            logger.info(
                "Creating new connection for user=%s, installation_id=%s",
                user_id,
                installation_id,
            )
            create_github_connection(
                conn,
                user_id=user_id,
                installation_id=installation_id,
            )

        # Map all repositories to this installation for this user
        for repo_full_name in repositories:
            try:
                create_repo_subscription(
                    conn,
                    user_id=user_id,
                    repo_full_name=repo_full_name,
                    installation_id=installation_id,
                )
                logger.info(
                    "Mapped repo=%s to installation_id=%s for user=%s",
                    repo_full_name,
                    installation_id,
                    user_id,
                )
            except Exception as e:
                # Subscription may already exist - that's OK
                logger.debug(
                    "Could not create subscription (may already exist): %s",
                    str(e),
                )


def handle_installation_deleted(
    conn: duckdb.DuckDBPyConnection,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Handle installation deleted event.

    Removes repository mappings for the deleted installation.
    Does not delete github_connections to preserve history.

    Args:
        conn: Database connection.
        normalized: Normalized webhook event data.
        payload: Raw webhook payload.
    """
    installation_id = normalized.get("installation_id")
    if installation_id is None:
        logger.warning("Installation deleted event missing installation_id")
        return

    repositories = normalized.get("repositories", [])
    logger.info(
        "Processing installation.deleted: installation_id=%s, repos=%s",
        installation_id,
        repositories,
    )

    # Get all users associated with this installation
    users = get_users_for_installation(conn, installation_id)

    # Remove repo subscriptions for all affected users
    for user_id in users:
        for repo_full_name in repositories:
            deleted = delete_repo_subscription(conn, user_id, repo_full_name)
            if deleted:
                logger.info(
                    "Removed repo subscription: user=%s, repo=%s",
                    user_id,
                    repo_full_name,
                )


def handle_installation_repositories_added(
    conn: duckdb.DuckDBPyConnection,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Handle installation_repositories added event.

    Maps newly added repositories to the installation.

    Args:
        conn: Database connection.
        normalized: Normalized webhook event data.
        payload: Raw webhook payload.
    """
    installation_id = normalized.get("installation_id")
    if installation_id is None:
        logger.warning("Installation repositories added event missing installation_id")
        return

    repositories_added = normalized.get("repositories_added", [])
    logger.info(
        "Processing installation_repositories.added: installation_id=%s, repos=%s",
        installation_id,
        repositories_added,
    )

    # Get all users associated with this installation
    users = get_users_for_installation(conn, installation_id)

    # If no users found, create system-level subscriptions
    if not users:
        logger.info(
            "No users for installation_id=%s, using system user",
            installation_id,
        )
        users = [SYSTEM_USER_ID]

    # Add repo subscriptions for all affected users
    for user_id in users:
        for repo_full_name in repositories_added:
            try:
                create_repo_subscription(
                    conn,
                    user_id=user_id,
                    repo_full_name=repo_full_name,
                    installation_id=installation_id,
                )
                logger.info(
                    "Added repo subscription: user=%s, repo=%s, installation_id=%s",
                    user_id,
                    repo_full_name,
                    installation_id,
                )
            except Exception as e:
                logger.debug(
                    "Could not create subscription (may already exist): %s",
                    str(e),
                )


def handle_installation_repositories_removed(
    conn: duckdb.DuckDBPyConnection,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Handle installation_repositories removed event.

    Removes repository mappings for repositories removed from the installation.

    Args:
        conn: Database connection.
        normalized: Normalized webhook event data.
        payload: Raw webhook payload.
    """
    installation_id = normalized.get("installation_id")
    if installation_id is None:
        logger.warning("Installation repositories removed event missing installation_id")
        return

    repositories_removed = normalized.get("repositories_removed", [])
    logger.info(
        "Processing installation_repositories.removed: installation_id=%s, repos=%s",
        installation_id,
        repositories_removed,
    )

    # Get all users associated with this installation
    users = get_users_for_installation(conn, installation_id)

    # Remove repo subscriptions for all affected users
    for user_id in users:
        for repo_full_name in repositories_removed:
            deleted = delete_repo_subscription(conn, user_id, repo_full_name)
            if deleted:
                logger.info(
                    "Removed repo subscription: user=%s, repo=%s",
                    user_id,
                    repo_full_name,
                )


def process_installation_event(
    conn: duckdb.DuckDBPyConnection,
    normalized: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Process installation lifecycle webhook event.

    Routes to appropriate handler based on event type and action.

    Args:
        conn: Database connection.
        normalized: Normalized webhook event data.
        payload: Raw webhook payload.
    """
    event_type = normalized.get("event_type")
    action = normalized.get("action")

    if event_type == "installation":
        if action == "created":
            handle_installation_created(conn, normalized, payload)
        elif action == "deleted":
            handle_installation_deleted(conn, normalized, payload)
    elif event_type == "installation_repositories":
        if action == "added":
            handle_installation_repositories_added(conn, normalized, payload)
        elif action == "removed":
            handle_installation_repositories_removed(conn, normalized, payload)
