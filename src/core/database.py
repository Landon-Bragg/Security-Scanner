"""
Database models and connection management
"""
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import String, Text, DateTime, Boolean, Integer, JSON, Enum as SQLEnum
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum

from src.core.config import settings


# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base model for all database models"""
    pass


class SeverityLevel(str, enum.Enum):
    """Severity levels for security findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingType(str, enum.Enum):
    """Types of security findings"""
    SECRET = "secret"
    VULNERABILITY = "vulnerability"
    MALWARE = "malware"
    SUSPICIOUS_CODE = "suspicious_code"
    LICENSE_ISSUE = "license_issue"


class FindingStatus(str, enum.Enum):
    """Status of security findings"""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Repository(Base):
    """Repository model"""
    __tablename__ = "repositories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_scanned: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SecurityFinding(Base):
    """Security finding model"""
    __tablename__ = "security_findings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(Integer, index=True)
    finding_type: Mapped[FindingType] = mapped_column(SQLEnum(FindingType), index=True)
    severity: Mapped[SeverityLevel] = mapped_column(SQLEnum(SeverityLevel), index=True)
    status: Mapped[FindingStatus] = mapped_column(SQLEnum(FindingStatus), default=FindingStatus.OPEN, index=True)
    
    # Finding details
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    
    # Secret-specific fields
    secret_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entropy_score: Mapped[float | None] = mapped_column(nullable=True)
    
    # Vulnerability-specific fields
    cve_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    package_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    affected_versions: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Additional metadata
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScanJob(Base):
    """Scan job tracking"""
    __tablename__ = "scan_jobs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(Integer, index=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
