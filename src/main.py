"""
Main FastAPI application for GitHub Security Intelligence Pipeline
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.api.routes import webhooks, findings, health
from src.core.config import settings
from src.core.database import init_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting GitHub Security Intelligence Pipeline")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down GitHub Security Intelligence Pipeline")


app = FastAPI(
    title="GitHub Security Intelligence Pipeline",
    description="Real-time security monitoring for GitHub repositories",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["findings"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GitHub Security Intelligence Pipeline API",
        "version": "1.0.0",
        "docs": "/docs"
    }
