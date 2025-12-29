"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from src.main import app
from src.core.database import Base, get_db
from src.core.config import settings


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_secret_content():
    """Sample file content with secrets for testing"""
    return """
import os

# AWS credentials
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# GitHub token
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"

# Database connection
DB_URL = "postgresql://admin:SuperSecret123@db.example.com:5432/mydb"

# API keys
API_KEY = "sk_test_51234567890abcdefghijklmnopqrstuvwxyz"
STRIPE_KEY = "sk_live_51234567890abcdefghijklmnopqrstuvwxyz"

# Private key
PRIVATE_KEY = '''-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890...
-----END RSA PRIVATE KEY-----'''

# Safe content
app_name = "MyApp"
version = "1.0.0"
"""


@pytest.fixture
def sample_push_event():
    """Sample GitHub push event"""
    return {
        "event_type": "push",
        "repository": "testuser/testrepo",
        "sender": "testuser",
        "payload": {
            "ref": "refs/heads/main",
            "repository": {
                "id": 12345,
                "name": "testrepo",
                "full_name": "testuser/testrepo",
                "owner": {"login": "testuser"},
                "private": False,
                "description": "Test repository",
                "stargazers_count": 10,
                "language": "Python",
            },
            "commits": [
                {
                    "id": "abc123def456",
                    "message": "Add new feature",
                    "author": {"name": "Test User", "email": "test@example.com"},
                    "added": ["new_file.py"],
                    "modified": ["existing_file.py"],
                    "removed": [],
                }
            ],
        },
    }
