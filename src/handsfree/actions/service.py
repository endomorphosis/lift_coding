"""Shared execution for direct and confirmed side-effect actions."""

from dataclasses import dataclass, field
from typing import Any

import duckdb
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from handsfree.db.action_logs import write_action_log
from handsfree.models import ActionResult, CommandResponse, CommandStatus, ParsedIntent
from handsfree.policy import PolicyDecision, evaluate_action_policy


def _format_execution_mode(mode: str | None) -> str:
    if not mode:
        return "unknown"
    return "live mode" if mode == "api_live" else mode


@dataclass
class DirectActionRequest:
    """Configuration for processing a direct side-effect action request."""

    endpoint: str
    action_type: str
    execution_action_type: str | None
    pending_action_type: str
    repo: str
    pr_number: int
    action_payload: dict[str, Any]
    log_request: dict[str, Any]
    pending_summary: str
    idempotency_key: str | None = None
    anomaly_request_data: dict[str, Any] = field(default_factory=dict)
    policy_kwargs: dict[str, Any] = field(default_factory=dict)
    always_require_confirmation: bool = False


@dataclass
class DirectActionProcessResult:
    """Detailed result for shared direct-action orchestration."""

    action_result: ActionResult | None = None
    http_response: JSONResponse | None = None
    pending_token: str | None = None
    pending_expires_at: Any | None = None
    pending_summary: str | None = None
    policy_reason: str | None = None


def process_direct_action_request_detailed(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    request: DirectActionRequest,
    idempotency_store: dict[str, ActionResult],
) -> DirectActionProcessResult:
    """Process a direct side-effect action and preserve pending metadata."""
    cached = _get_cached_action_result(conn, request.idempotency_key, idempotency_store)
    if cached is not None:
        return DirectActionProcessResult(action_result=cached)

    target = f"{request.repo}#{request.pr_number}"
    rate_limit_result = _check_rate_limit(conn, user_id, request.action_type)
    if not rate_limit_result.allowed:
        write_action_log(
            conn,
            user_id=user_id,
            action_type=request.action_type,
            ok=False,
            target=target,
            request=request.log_request,
            result={"error": "rate_limited", "message": rate_limit_result.reason},
            idempotency_key=request.idempotency_key,
        )
        _log_anomaly(
            conn,
            user_id=user_id,
            action_type=request.action_type,
            reason="rate_limited",
            target=target,
            request_data=request.anomaly_request_data,
        )
        return DirectActionProcessResult(
            http_response=JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "error": "rate_limited",
                        "message": rate_limit_result.reason,
                        "retry_after": rate_limit_result.retry_after_seconds,
                    }
                },
                headers={"Retry-After": str(rate_limit_result.retry_after_seconds)}
                if rate_limit_result.retry_after_seconds
                else {},
            )
        )

    policy_result = evaluate_action_policy(
        conn,
        user_id,
        request.repo,
        request.action_type,
        **request.policy_kwargs,
    )
    if policy_result.decision == PolicyDecision.DENY:
        try:
            write_action_log(
                conn,
                user_id=user_id,
                action_type=request.action_type,
                ok=False,
                target=target,
                request=request.log_request,
                result={"error": "policy_denied", "message": policy_result.reason},
                idempotency_key=request.idempotency_key,
            )
        except ValueError:
            pass
        _log_anomaly(
            conn,
            user_id=user_id,
            action_type=request.action_type,
            reason="policy_denied",
            target=target,
            request_data=request.anomaly_request_data,
        )
        raise HTTPException(
            status_code=403,
            detail={"error": "policy_denied", "message": policy_result.reason},
        )

    needs_confirmation = (
        request.always_require_confirmation
        or policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION
    )
    if needs_confirmation:
        return _create_pending_direct_action(
            conn=conn,
            user_id=user_id,
            request=request,
            policy_reason=policy_result.reason,
            idempotency_store=idempotency_store,
        )

    if not request.execution_action_type:
        raise HTTPException(
            status_code=500,
            detail={"error": "misconfigured_action", "message": "Direct execution is not configured"},
        )

    result = execute_direct_action(
        conn=conn,
        user_id=user_id,
        action_type=request.execution_action_type,
        action_payload=request.action_payload,
        idempotency_key=request.idempotency_key,
    )
    _store_action_result(
        conn=conn,
        key=request.idempotency_key,
        user_id=user_id,
        endpoint=request.endpoint,
        result=result,
        idempotency_store=idempotency_store,
    )
    return DirectActionProcessResult(action_result=result)


def process_direct_action_request(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    request: DirectActionRequest,
    idempotency_store: dict[str, ActionResult],
) -> ActionResult | JSONResponse:
    """Process a direct side-effect action with shared guards and caching."""
    detailed = process_direct_action_request_detailed(
        conn=conn,
        user_id=user_id,
        request=request,
        idempotency_store=idempotency_store,
    )
    if detailed.http_response is not None:
        return detailed.http_response
    if detailed.action_result is not None:
        return detailed.action_result
    raise HTTPException(
        status_code=500,
        detail={"error": "invalid_action_result", "message": "Action processing produced no result"},
    )


def execute_confirmed_action(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None = None,
    via_router_token: bool = False,
) -> CommandResponse:
    """Execute a confirmed side-effect action and return a command response."""
    if action_type == "request_review":
        return _execute_request_review(
            conn,
            user_id,
            action_payload,
            idempotency_key=idempotency_key,
            via_router_token=via_router_token,
        )
    if action_type == "rerun_checks":
        return _execute_rerun_checks(
            conn,
            user_id,
            action_payload,
            idempotency_key=idempotency_key,
        )
    if action_type == "comment":
        return _execute_comment(
            conn,
            user_id,
            action_payload,
            idempotency_key=idempotency_key,
            via_router_token=via_router_token,
        )
    if action_type == "merge":
        return _execute_merge(
            conn,
            user_id,
            action_payload,
            idempotency_key=idempotency_key,
            via_router_token=via_router_token,
        )

    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=ParsedIntent(name="confirm.unknown", confidence=0.5),
        spoken_text=f"Unknown action type: {action_type}",
    )


def execute_direct_action(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> ActionResult:
    """Execute a direct side-effect action and return an action result."""
    if action_type == "request_review":
        return _execute_direct_request_review(conn, user_id, action_payload, idempotency_key)
    if action_type == "rerun":
        return _execute_direct_rerun(conn, user_id, action_payload, idempotency_key)
    if action_type == "comment":
        return _execute_direct_comment(conn, user_id, action_payload, idempotency_key)

    return ActionResult(ok=False, message=f"Unknown direct action type: {action_type}", url=None)


def _get_cached_action_result(
    conn: duckdb.DuckDBPyConnection,
    key: str | None,
    idempotency_store: dict[str, ActionResult],
) -> ActionResult | None:
    if not key:
        return None

    from handsfree.db.idempotency_keys import get_idempotency_response

    cached_response = get_idempotency_response(conn, key)
    if cached_response:
        return ActionResult(**cached_response)
    return idempotency_store.get(key)


def _store_action_result(
    conn: duckdb.DuckDBPyConnection,
    key: str | None,
    user_id: str,
    endpoint: str,
    result: ActionResult,
    idempotency_store: dict[str, ActionResult],
    audit_log_id: str | None = None,
) -> None:
    if not key:
        return

    from handsfree.db.idempotency_keys import store_idempotency_key

    store_idempotency_key(
        conn,
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        response_data=result.model_dump(mode="json"),
        audit_log_id=audit_log_id,
        expires_in_seconds=86400,
    )
    idempotency_store[key] = result


def _check_rate_limit(conn: duckdb.DuckDBPyConnection, user_id: str, action_type: str):
    from handsfree.rate_limit import check_side_effect_rate_limit

    return check_side_effect_rate_limit(conn, user_id, action_type)


def _log_anomaly(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    reason: str,
    target: str,
    request_data: dict[str, Any],
) -> None:
    from handsfree.security import check_and_log_anomaly

    check_and_log_anomaly(
        conn,
        user_id,
        action_type,
        reason,
        target=target,
        request_data=request_data,
    )


def _create_pending_direct_action(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    request: DirectActionRequest,
    policy_reason: str,
    idempotency_store: dict[str, ActionResult],
) -> DirectActionProcessResult:
    from handsfree.db.pending_actions import create_pending_action

    pending_action = create_pending_action(
        conn,
        user_id=user_id,
        summary=request.pending_summary,
        action_type=request.pending_action_type,
        action_payload=request.action_payload,
        expires_in_seconds=300,
    )
    audit_log = write_action_log(
        conn,
        user_id=user_id,
        action_type=request.action_type,
        ok=True,
        target=f"{request.repo}#{request.pr_number}",
        request=request.log_request,
        result={
            "status": "needs_confirmation",
            "token": pending_action.token,
            "reason": policy_reason,
        },
        idempotency_key=request.idempotency_key,
    )
    result = ActionResult(
        ok=False,
        message=(
            f"Confirmation required: {policy_reason}. "
            f"Use token '{pending_action.token}' to confirm."
        ),
        url=None,
    )
    _store_action_result(
        conn=conn,
        key=request.idempotency_key,
        user_id=user_id,
        endpoint=request.endpoint,
        result=result,
        idempotency_store=idempotency_store,
        audit_log_id=audit_log.id,
    )
    return DirectActionProcessResult(
        action_result=result,
        pending_token=pending_action.token,
        pending_expires_at=pending_action.expires_at,
        pending_summary=request.pending_summary,
        policy_reason=policy_reason,
    )


def _execute_request_review(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
    via_router_token: bool,
) -> CommandResponse:
    from handsfree.github.execution import execute_request_review_action

    repo = action_payload.get("repo")
    pr_number = action_payload.get("pr_number")
    reviewers = action_payload.get("reviewers", [])

    if not pr_number:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="request_review.confirmed", confidence=1.0),
            spoken_text="PR number is required for review request.",
        )

    target = f"{repo}#{pr_number}"
    reviewers_str = ", ".join(reviewers)
    github_result = execute_request_review_action(
        repo=repo,
        pr_number=pr_number,
        reviewers=reviewers,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=target,
            request={"reviewers": reviewers, "confirmed": True},
            result={
                "status": "success",
                "message": f"Review requested ({_format_execution_mode(github_result.get('mode'))})",
                "via_confirmation": True,
                "via_router_token": via_router_token,
                "github_response": github_result.get("response_data"),
            },
            idempotency_key=idempotency_key,
        )
        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="request_review.confirmed",
                confidence=1.0,
                entities={"repo": repo, "pr_number": pr_number, "reviewers": reviewers},
            ),
            spoken_text=f"Review requested from {reviewers_str} on {target}.",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="request_review",
        ok=False,
        target=target,
        request={"reviewers": reviewers, "confirmed": True},
        result={
            "status": "error",
            "message": github_result["message"],
            "via_confirmation": True,
            "via_router_token": via_router_token,
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=ParsedIntent(
            name="request_review.confirmed",
            confidence=1.0,
            entities={"repo": repo, "pr_number": pr_number, "reviewers": reviewers},
        ),
        spoken_text=f"Failed to request reviewers: {github_result['message']}",
    )


def _execute_rerun_checks(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
) -> CommandResponse:
    from handsfree.github.execution import execute_rerun_action

    repo = action_payload.get("repo")
    pr_number = action_payload.get("pr_number")
    target = f"{repo}#{pr_number}"
    github_result = execute_rerun_action(
        repo=repo,
        pr_number=pr_number,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="rerun",
            ok=True,
            target=target,
            request={"confirmed": True},
            result={
                "status": "success",
                "message": f"Checks re-run ({_format_execution_mode(github_result.get('mode'))})",
                "via_confirmation": True,
                "run_id": github_result.get("run_id"),
            },
            idempotency_key=idempotency_key,
        )
        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="rerun_checks.confirmed",
                confidence=1.0,
                entities={"repo": repo, "pr_number": pr_number},
            ),
            spoken_text=f"Workflow checks re-run on {target}.",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="rerun",
        ok=False,
        target=target,
        request={"confirmed": True},
        result={
            "status": "error",
            "message": github_result["message"],
            "via_confirmation": True,
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=ParsedIntent(
            name="rerun_checks.confirmed",
            confidence=1.0,
            entities={"repo": repo, "pr_number": pr_number},
        ),
        spoken_text=f"Failed to re-run checks: {github_result['message']}",
    )


def _execute_comment(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
    via_router_token: bool,
) -> CommandResponse:
    from handsfree.github.execution import execute_comment_action

    repo = action_payload.get("repo")
    pr_number = action_payload.get("pr_number")
    comment_body = action_payload.get("comment_body", "")

    if not pr_number:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="comment.confirmed", confidence=1.0),
            spoken_text="PR number is required for comment.",
        )
    if not comment_body:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="comment.confirmed", confidence=1.0),
            spoken_text="Comment text is required.",
        )

    target = f"{repo}#{pr_number}"
    github_result = execute_comment_action(
        repo=repo,
        pr_number=pr_number,
        comment_body=comment_body,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="comment",
            ok=True,
            target=target,
            request={"comment_body": comment_body, "confirmed": True},
            result={
                "status": "success",
                "message": f"Comment posted ({_format_execution_mode(github_result.get('mode'))})",
                "via_confirmation": True,
                "via_router_token": via_router_token,
                "github_response": github_result.get("response_data"),
            },
            idempotency_key=idempotency_key,
        )
        preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="comment.confirmed",
                confidence=1.0,
                entities={"repo": repo, "pr_number": pr_number},
            ),
            spoken_text=f"Comment posted on {target}: {preview}",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="comment",
        ok=False,
        target=target,
        request={"comment_body": comment_body, "confirmed": True},
        result={
            "status": "error",
            "message": github_result["message"],
            "via_confirmation": True,
            "via_router_token": via_router_token,
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=ParsedIntent(
            name="comment.confirmed",
            confidence=1.0,
            entities={"repo": repo, "pr_number": pr_number},
        ),
        spoken_text=f"Failed to post comment: {github_result['message']}",
    )


def _execute_merge(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
    via_router_token: bool,
) -> CommandResponse:
    from handsfree.github.execution import execute_merge_action

    repo = action_payload.get("repo")
    pr_number = action_payload.get("pr_number")
    merge_method = action_payload.get("merge_method") or "squash"

    if not pr_number:
        return CommandResponse(
            status=CommandStatus.ERROR,
            intent=ParsedIntent(name="merge.confirmed", confidence=1.0),
            spoken_text="PR number is required for merge.",
        )

    target = f"{repo}#{pr_number}"
    github_result = execute_merge_action(
        repo=repo,
        pr_number=pr_number,
        merge_method=merge_method,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="merge",
            ok=True,
            target=target,
            request={"confirmed": True, "merge_method": merge_method},
            result={
                "status": "success",
                "message": f"PR merged ({_format_execution_mode(github_result.get('mode'))})",
                "via_confirmation": True,
                "via_router_token": via_router_token,
                "github_response": github_result.get("response_data"),
            },
            idempotency_key=idempotency_key,
        )
        return CommandResponse(
            status=CommandStatus.OK,
            intent=ParsedIntent(
                name="merge.confirmed",
                confidence=1.0,
                entities={
                    "repo": repo,
                    "pr_number": pr_number,
                    "merge_method": merge_method,
                },
            ),
            spoken_text=f"Merged successfully {target}.",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="merge",
        ok=False,
        target=target,
        request={"confirmed": True, "merge_method": merge_method},
        result={
            "status": "error",
            "message": github_result["message"],
            "via_confirmation": True,
            "via_router_token": via_router_token,
            "status_code": github_result.get("status_code"),
            "error_type": github_result.get("error_type"),
        },
        idempotency_key=idempotency_key,
    )
    return CommandResponse(
        status=CommandStatus.ERROR,
        intent=ParsedIntent(
            name="merge.confirmed",
            confidence=1.0,
            entities={
                "repo": repo,
                "pr_number": pr_number,
                "merge_method": merge_method,
            },
        ),
        spoken_text=f"Failed to merge: {github_result['message']}",
    )


def _execute_direct_request_review(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
) -> ActionResult:
    from handsfree.github.execution import execute_request_review_action

    repo = action_payload["repo"]
    pr_number = action_payload["pr_number"]
    reviewers = action_payload["reviewers"]
    target = f"{repo}#{pr_number}"
    github_result = execute_request_review_action(
        repo=repo,
        pr_number=pr_number,
        reviewers=reviewers,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="request_review",
            ok=True,
            target=target,
            request={"reviewers": reviewers},
            result={
                "status": "success",
                "message": f"Review requested ({_format_execution_mode(github_result.get('mode'))})",
                "github_response": github_result.get("response_data"),
            },
            idempotency_key=idempotency_key,
        )
        return ActionResult(
            ok=True,
            message=github_result["message"],
            url=f"https://github.com/{repo}/pull/{pr_number}",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="request_review",
        ok=False,
        target=target,
        request={"reviewers": reviewers},
        result={
            "status": "error",
            "message": github_result["message"],
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return ActionResult(ok=False, message=f"GitHub API error: {github_result['message']}", url=None)


def _execute_direct_rerun(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
) -> ActionResult:
    from handsfree.github.execution import execute_rerun_action

    repo = action_payload["repo"]
    pr_number = action_payload["pr_number"]
    target = f"{repo}#{pr_number}"
    github_result = execute_rerun_action(repo=repo, pr_number=pr_number, user_id=user_id)

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="rerun",
            ok=True,
            target=target,
            request={},
            result={
                "status": "success",
                "message": f"Checks re-run ({_format_execution_mode(github_result.get('mode'))})",
                "run_id": github_result.get("run_id"),
            },
            idempotency_key=idempotency_key,
        )
        return ActionResult(
            ok=True,
            message=github_result["message"],
            url=f"https://github.com/{repo}/pull/{pr_number}",
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="rerun",
        ok=False,
        target=target,
        request={},
        result={
            "status": "error",
            "message": github_result["message"],
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return ActionResult(ok=False, message=f"GitHub API error: {github_result['message']}", url=None)


def _execute_direct_comment(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_payload: dict[str, Any],
    idempotency_key: str | None,
) -> ActionResult:
    from handsfree.github.execution import execute_comment_action

    repo = action_payload["repo"]
    pr_number = action_payload["pr_number"]
    comment_body = action_payload["comment_body"]
    target = f"{repo}#{pr_number}"
    github_result = execute_comment_action(
        repo=repo,
        pr_number=pr_number,
        comment_body=comment_body,
        user_id=user_id,
    )

    if github_result["ok"]:
        write_action_log(
            conn,
            user_id=user_id,
            action_type="comment",
            ok=True,
            target=target,
            request={"comment_body": comment_body},
            result={
                "status": "success",
                "message": f"Comment posted ({github_result.get('mode', 'unknown')})",
                "github_response": github_result.get("response_data"),
            },
            idempotency_key=idempotency_key,
        )
        return ActionResult(
            ok=True,
            message=github_result["message"],
            url=github_result.get("url"),
        )

    write_action_log(
        conn,
        user_id=user_id,
        action_type="comment",
        ok=False,
        target=target,
        request={"comment_body": comment_body},
        result={
            "status": "error",
            "message": github_result["message"],
            "status_code": github_result.get("status_code"),
        },
        idempotency_key=idempotency_key,
    )
    return ActionResult(ok=False, message=f"GitHub API error: {github_result['message']}", url=None)
