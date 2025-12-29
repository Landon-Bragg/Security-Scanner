"""
GitHub webhook endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import structlog

from src.core.config import settings
from src.core.redis_client import redis_stream_client

logger = structlog.get_logger()
router = APIRouter()


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """
    Verify GitHub webhook signature

    Args:
        payload: Request payload
        signature: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid
    """
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GitHub webhook secret not configured, skipping verification")
        return True

    if not signature:
        return False

    # GitHub sends signature as 'sha256=<signature>'
    algorithm, expected_signature = signature.split("=")

    if algorithm != "sha256":
        return False

    mac = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256
    )

    return hmac.compare_digest(mac.hexdigest(), expected_signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: Optional[str] = Header(None),
):
    """
    GitHub webhook endpoint

    Receives and processes GitHub webhook events
    """
    # Get raw payload for signature verification
    payload = await request.body()

    # Verify signature
    if not verify_github_signature(payload, x_hub_signature_256):
        logger.warning("Invalid GitHub webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    event_data = await request.json()

    logger.info(
        "Received GitHub webhook",
        event_type=x_github_event,
        repository=event_data.get("repository", {}).get("full_name"),
    )

    # Route event to appropriate stream
    stream_name = None

    if x_github_event == "push":
        stream_name = redis_stream_client.STREAM_PUSH_EVENTS
    elif x_github_event == "pull_request":
        stream_name = redis_stream_client.STREAM_PR_EVENTS
    elif x_github_event == "release":
        stream_name = redis_stream_client.STREAM_RELEASE_EVENTS
    elif x_github_event == "security_advisory":
        stream_name = redis_stream_client.STREAM_SECURITY_ADVISORIES

    if stream_name:
        # Publish to Redis stream
        await redis_stream_client.publish_event(
            stream_name=stream_name,
            event_data={
                "event_type": x_github_event,
                "repository": event_data.get("repository", {}).get("full_name", ""),
                "sender": event_data.get("sender", {}).get("login", ""),
                "payload": event_data,
            },
        )

        logger.info(
            "Published event to stream", event_type=x_github_event, stream=stream_name
        )
    else:
        logger.debug("Ignored unsupported event type", event_type=x_github_event)

    return {"status": "accepted", "event": x_github_event}


@router.get("/github/test")
async def test_webhook():
    """
    Test endpoint to verify webhook setup
    """
    return {
        "message": "GitHub webhook endpoint is ready",
        "webhook_url": "/api/v1/webhooks/github",
        "supported_events": ["push", "pull_request", "release", "security_advisory"],
    }
