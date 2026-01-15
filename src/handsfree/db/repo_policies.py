"""Repository policies persistence module.

Manages repository-level policy configuration for actions.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass
class RepoPolicy:
    """Represents a repository policy configuration."""

    id: str
    user_id: str
    repo_full_name: str
    allow_merge: bool
    allow_rerun: bool
    allow_request_review: bool
    allow_comment: bool
    require_confirmation: bool
    require_checks_green: bool
    required_approvals: int
    created_at: datetime
    updated_at: datetime


def get_repo_policy(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
) -> RepoPolicy | None:
    """Get policy for a specific user and repository.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        repo_full_name: Full repository name (owner/name).

    Returns:
        RepoPolicy if found, None otherwise.
    """
    result = conn.execute(
        """
        SELECT id, user_id, repo_full_name, allow_merge, allow_rerun, 
               allow_request_review, allow_comment, require_confirmation, require_checks_green,
               required_approvals, created_at, updated_at
        FROM repo_policies
        WHERE user_id = ? AND repo_full_name = ?
        """,
        [user_id, repo_full_name],
    ).fetchone()

    if not result:
        return None

    return RepoPolicy(
        id=str(result[0]),
        user_id=str(result[1]),
        repo_full_name=result[2],
        allow_merge=result[3],
        allow_rerun=result[4],
        allow_request_review=result[5],
        allow_comment=result[6],
        require_confirmation=result[7],
        require_checks_green=result[8],
        required_approvals=result[9],
        created_at=result[10],
        updated_at=result[11],
    )


def create_or_update_repo_policy(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
    allow_merge: bool = False,
    allow_rerun: bool = True,
    allow_request_review: bool = True,
    allow_comment: bool = True,
    require_confirmation: bool = True,
    require_checks_green: bool = True,
    required_approvals: int = 1,
) -> RepoPolicy:
    """Create or update a repository policy.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        repo_full_name: Full repository name (owner/name).
        allow_merge: Allow merge actions (default: False).
        allow_rerun: Allow rerun actions (default: True).
        allow_request_review: Allow request review actions (default: True).
        allow_comment: Allow comment actions (default: True).
        require_confirmation: Require user confirmation (default: True).
        require_checks_green: Require all checks to pass (default: True).
        required_approvals: Number of required approvals (default: 1).

    Returns:
        Created or updated RepoPolicy object.
    """
    existing = get_repo_policy(conn, user_id, repo_full_name)
    now = datetime.now(UTC)

    if existing:
        # Update existing policy
        conn.execute(
            """
            UPDATE repo_policies
            SET allow_merge = ?, allow_rerun = ?, allow_request_review = ?,
                allow_comment = ?, require_confirmation = ?, require_checks_green = ?,
                required_approvals = ?, updated_at = ?
            WHERE user_id = ? AND repo_full_name = ?
            """,
            [
                allow_merge,
                allow_rerun,
                allow_request_review,
                allow_comment,
                require_confirmation,
                require_checks_green,
                required_approvals,
                now,
                user_id,
                repo_full_name,
            ],
        )
        policy_id = existing.id
    else:
        # Create new policy
        policy_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO repo_policies
            (id, user_id, repo_full_name, allow_merge, allow_rerun,
             allow_request_review, allow_comment, require_confirmation, require_checks_green,
             required_approvals, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                policy_id,
                user_id,
                repo_full_name,
                allow_merge,
                allow_rerun,
                allow_request_review,
                allow_comment,
                require_confirmation,
                require_checks_green,
                required_approvals,
                now,
                now,
            ],
        )

    return RepoPolicy(
        id=policy_id,
        user_id=user_id,
        repo_full_name=repo_full_name,
        allow_merge=allow_merge,
        allow_rerun=allow_rerun,
        allow_request_review=allow_request_review,
        allow_comment=allow_comment,
        require_confirmation=require_confirmation,
        require_checks_green=require_checks_green,
        required_approvals=required_approvals,
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )


def get_default_policy() -> RepoPolicy:
    """Get the default policy for repositories without explicit configuration.

    Returns:
        Default RepoPolicy with conservative settings.
    """
    now = datetime.now(UTC)
    return RepoPolicy(
        id="default",
        user_id="default",
        repo_full_name="default",
        allow_merge=False,
        allow_rerun=True,
        allow_request_review=True,
        allow_comment=True,
        require_confirmation=True,
        require_checks_green=True,
        required_approvals=1,
        created_at=now,
        updated_at=now,
    )
