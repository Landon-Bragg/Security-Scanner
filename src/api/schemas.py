"""
Pydantic schemas for API requests and responses
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class FindingResponse(BaseModel):
    """Response model for security finding"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    finding_type: str
    severity: str
    status: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    commit_sha: Optional[str] = None
    secret_type: Optional[str] = None
    entropy_score: Optional[float] = None
    cve_id: Optional[str] = None
    package_name: Optional[str] = None
    affected_versions: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    discovered_at: datetime
    updated_at: datetime


class FindingStats(BaseModel):
    """Statistics about findings"""

    total_findings: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    period_days: int


class RepositoryStats(BaseModel):
    """Statistics for a repository"""

    repository_name: str
    repository_id: int
    finding_count: int
    last_finding: Optional[datetime] = None


class WebhookEvent(BaseModel):
    """GitHub webhook event"""

    event_type: str
    repository: str
    sender: str
    payload: Dict[str, Any]
