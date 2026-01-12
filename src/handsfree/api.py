"""FastAPI application for HandsFree Dev Companion API."""

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from handsfree.db.webhook_events import get_db_webhook_store
from handsfree.webhooks import normalize_github_event, verify_github_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HandsFree Dev Companion API",
    version="1.0.0",
    description="API for hands-free developer assistant",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/v1/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> JSONResponse:
    """Handle GitHub webhook events.

    Verifies signature, checks for replay, stores event, and normalizes payload.

    Args:
        request: FastAPI request object
        x_github_event: GitHub event type header
        x_github_delivery: GitHub delivery ID header
        x_hub_signature_256: GitHub signature header

    Returns:
        202 Accepted response with event ID

    Raises:
        400 Bad Request if signature invalid or duplicate delivery
    """
    store = get_db_webhook_store()

    # Check for duplicate delivery (replay protection)
    if store.is_duplicate_delivery(x_github_delivery):
        logger.warning("Duplicate delivery detected: %s", x_github_delivery)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate delivery ID",
        )

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature (dev mode: secret=None allows 'dev' signature)
    # In production, get secret from environment/config
    webhook_secret = None  # Dev mode
    signature_ok = verify_github_signature(body, x_hub_signature_256, webhook_secret)

    if not signature_ok:
        logger.error(
            "Signature verification failed for delivery %s",
            x_github_delivery,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from e

    # Store raw event
    event_id = store.store_event(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        payload=payload,
        signature_ok=signature_ok,
    )

    # Normalize event (if supported)
    normalized = normalize_github_event(x_github_event, payload)
    if normalized:
        logger.info(
            "Normalized event: type=%s, action=%s",
            x_github_event,
            normalized.get("action"),
        )
        # In a full implementation, normalized events would update inbox/notifications
        # For now, just log them

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"event_id": event_id, "message": "Webhook accepted"},
    )


@app.post("/v1/command")
def submit_command(body: dict[str, Any]):
    """Stub for command submission endpoint."""
    return {
        "spoken_text": "Command received (stub)",
        "needs_confirmation": False,
    }


@app.post("/v1/commands/confirm")
def confirm_command(body: dict[str, Any]):
    """Stub for command confirmation endpoint."""
    return {"status": "confirmed"}


@app.get("/v1/inbox")
def get_inbox():
    """Stub for inbox endpoint."""
    return {"items": []}


@app.post("/v1/actions/request-review")
def request_review(body: dict[str, Any]):
    """Stub for request review action."""
    return {"status": "ok"}


@app.post("/v1/actions/rerun-checks")
def rerun_checks(body: dict[str, Any]):
    """Stub for rerun checks action."""
    return {"status": "ok"}
