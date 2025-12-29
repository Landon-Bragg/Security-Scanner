"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from src.core.database import get_db
from src.core.redis_client import redis_stream_client

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint

    Returns service health status
    """
    health_status = {"status": "healthy", "services": {}}

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        await redis_stream_client.connect()
        await redis_stream_client.redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint

    Returns whether the service is ready to accept traffic
    """
    try:
        # Check database connection
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()

        # Check Redis connection
        await redis_stream_client.connect()
        await redis_stream_client.redis_client.ping()

        return {"ready": True}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {"ready": False, "error": str(e)}
