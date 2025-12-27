"""
Security findings endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from src.core.database import get_db, SecurityFinding, Repository, FindingType, SeverityLevel, FindingStatus
from src.api.schemas import FindingResponse, FindingStats, RepositoryStats

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[FindingResponse])
async def list_findings(
    db: AsyncSession = Depends(get_db),
    finding_type: Optional[FindingType] = None,
    severity: Optional[SeverityLevel] = None,
    status: Optional[FindingStatus] = None,
    repository_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List security findings with filters
    
    Args:
        finding_type: Filter by finding type
        severity: Filter by severity level
        status: Filter by status
        repository_id: Filter by repository
        days: Number of days to look back
        limit: Maximum number of results
        offset: Pagination offset
    """
    # Build query
    query = select(SecurityFinding)
    
    # Apply filters
    filters = []
    
    if finding_type:
        filters.append(SecurityFinding.finding_type == finding_type)
    
    if severity:
        filters.append(SecurityFinding.severity == severity)
    
    if status:
        filters.append(SecurityFinding.status == status)
    
    if repository_id:
        filters.append(SecurityFinding.repository_id == repository_id)
    
    # Date filter
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    filters.append(SecurityFinding.discovered_at >= cutoff_date)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by severity and date
    severity_order = {
        SeverityLevel.CRITICAL: 0,
        SeverityLevel.HIGH: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 3,
        SeverityLevel.INFO: 4
    }
    
    query = query.order_by(
        SecurityFinding.discovered_at.desc()
    ).limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    findings = result.scalars().all()
    
    return [FindingResponse.model_validate(finding) for finding in findings]


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific finding by ID
    """
    result = await db.execute(
        select(SecurityFinding).where(SecurityFinding.id == finding_id)
    )
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    return FindingResponse.model_validate(finding)


@router.get("/stats/summary", response_model=FindingStats)
async def get_finding_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """
    Get summary statistics for findings
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total findings
    total_result = await db.execute(
        select(func.count(SecurityFinding.id))
        .where(SecurityFinding.discovered_at >= cutoff_date)
    )
    total = total_result.scalar() or 0
    
    # By severity
    severity_result = await db.execute(
        select(
            SecurityFinding.severity,
            func.count(SecurityFinding.id)
        )
        .where(SecurityFinding.discovered_at >= cutoff_date)
        .group_by(SecurityFinding.severity)
    )
    by_severity = {severity.value: count for severity, count in severity_result.all()}
    
    # By type
    type_result = await db.execute(
        select(
            SecurityFinding.finding_type,
            func.count(SecurityFinding.id)
        )
        .where(SecurityFinding.discovered_at >= cutoff_date)
        .group_by(SecurityFinding.finding_type)
    )
    by_type = {ftype.value: count for ftype, count in type_result.all()}
    
    # By status
    status_result = await db.execute(
        select(
            SecurityFinding.status,
            func.count(SecurityFinding.id)
        )
        .where(SecurityFinding.discovered_at >= cutoff_date)
        .group_by(SecurityFinding.status)
    )
    by_status = {status.value: count for status, count in status_result.all()}
    
    return FindingStats(
        total_findings=total,
        by_severity=by_severity,
        by_type=by_type,
        by_status=by_status,
        period_days=days
    )


@router.get("/stats/repositories", response_model=List[RepositoryStats])
async def get_repository_stats(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get repositories with most findings
    """
    result = await db.execute(
        select(
            Repository.full_name,
            Repository.id,
            func.count(SecurityFinding.id).label('finding_count'),
            func.max(SecurityFinding.discovered_at).label('last_finding')
        )
        .join(SecurityFinding, SecurityFinding.repository_id == Repository.id)
        .group_by(Repository.id, Repository.full_name)
        .order_by(func.count(SecurityFinding.id).desc())
        .limit(limit)
    )
    
    stats = []
    for row in result.all():
        stats.append(RepositoryStats(
            repository_name=row.full_name,
            repository_id=row.id,
            finding_count=row.finding_count,
            last_finding=row.last_finding
        ))
    
    return stats


@router.patch("/{finding_id}/status")
async def update_finding_status(
    finding_id: int,
    status: FindingStatus,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of a finding
    """
    result = await db.execute(
        select(SecurityFinding).where(SecurityFinding.id == finding_id)
    )
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    finding.status = status
    finding.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(finding)
    
    logger.info(
        "Updated finding status",
        finding_id=finding_id,
        new_status=status.value
    )
    
    return FindingResponse.model_validate(finding)
