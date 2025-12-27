"""
Tests for API endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from src.core.database import Repository, SecurityFinding, FindingType, SeverityLevel, FindingStatus


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints"""
    
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
    
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check endpoint"""
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data


@pytest.mark.asyncio
class TestWebhookEndpoints:
    """Test webhook endpoints"""
    
    async def test_webhook_test_endpoint(self, client: AsyncClient):
        """Test webhook test endpoint"""
        response = await client.get("/api/v1/webhooks/github/test")
        assert response.status_code == 200
        
        data = response.json()
        assert "webhook_url" in data
        assert "supported_events" in data
    
    async def test_github_webhook_without_signature(self, client: AsyncClient, sample_push_event):
        """Test GitHub webhook without signature (should fail if secret is set)"""
        response = await client.post(
            "/api/v1/webhooks/github",
            json=sample_push_event["payload"],
            headers={"X-GitHub-Event": "push"}
        )
        
        # Will succeed if no webhook secret is configured
        # Will fail with 401 if secret is configured
        assert response.status_code in [200, 401]


@pytest.mark.asyncio
class TestFindingsEndpoints:
    """Test findings endpoints"""
    
    async def test_list_findings_empty(self, client: AsyncClient):
        """Test listing findings when database is empty"""
        response = await client.get("/api/v1/findings/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    async def test_list_findings_with_data(self, client: AsyncClient, test_db):
        """Test listing findings with data"""
        # Create test repository
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo",
            is_private=False
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Create test findings
        finding1 = SecurityFinding(
            repository_id=repo.id,
            finding_type=FindingType.SECRET,
            severity=SeverityLevel.HIGH,
            status=FindingStatus.OPEN,
            title="AWS Key Detected",
            description="AWS access key found in config.py",
            file_path="config.py",
            line_number=10,
            secret_type="AWS Access Key ID"
        )
        
        finding2 = SecurityFinding(
            repository_id=repo.id,
            finding_type=FindingType.SECRET,
            severity=SeverityLevel.CRITICAL,
            status=FindingStatus.OPEN,
            title="Private Key Detected",
            description="RSA private key found",
            file_path="key.pem",
            secret_type="RSA Private Key"
        )
        
        test_db.add(finding1)
        test_db.add(finding2)
        await test_db.commit()
        
        # Test listing
        response = await client.get("/api/v1/findings/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert all("id" in item for item in data)
        assert all("severity" in item for item in data)
    
    async def test_filter_findings_by_severity(self, client: AsyncClient, test_db):
        """Test filtering findings by severity"""
        # Create test data
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo"
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Add findings with different severities
        for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.LOW]:
            finding = SecurityFinding(
                repository_id=repo.id,
                finding_type=FindingType.SECRET,
                severity=severity,
                status=FindingStatus.OPEN,
                title=f"Test {severity.value}",
                description="Test finding"
            )
            test_db.add(finding)
        
        await test_db.commit()
        
        # Filter for critical only
        response = await client.get("/api/v1/findings/?severity=critical")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == "critical"
    
    async def test_get_finding_by_id(self, client: AsyncClient, test_db):
        """Test getting a specific finding"""
        # Create test data
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo"
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        finding = SecurityFinding(
            repository_id=repo.id,
            finding_type=FindingType.SECRET,
            severity=SeverityLevel.HIGH,
            status=FindingStatus.OPEN,
            title="Test Finding",
            description="Test description",
            file_path="test.py"
        )
        test_db.add(finding)
        await test_db.commit()
        await test_db.refresh(finding)
        
        # Get finding
        response = await client.get(f"/api/v1/findings/{finding.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == finding.id
        assert data["title"] == "Test Finding"
    
    async def test_get_nonexistent_finding(self, client: AsyncClient):
        """Test getting a finding that doesn't exist"""
        response = await client.get("/api/v1/findings/99999")
        assert response.status_code == 404
    
    async def test_update_finding_status(self, client: AsyncClient, test_db):
        """Test updating finding status"""
        # Create test data
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo"
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        finding = SecurityFinding(
            repository_id=repo.id,
            finding_type=FindingType.SECRET,
            severity=SeverityLevel.HIGH,
            status=FindingStatus.OPEN,
            title="Test Finding",
            description="Test description"
        )
        test_db.add(finding)
        await test_db.commit()
        await test_db.refresh(finding)
        
        # Update status
        response = await client.patch(
            f"/api/v1/findings/{finding.id}/status?status=resolved"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "resolved"
    
    async def test_get_finding_stats(self, client: AsyncClient, test_db):
        """Test getting finding statistics"""
        # Create test data
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo"
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Add various findings
        findings = [
            SecurityFinding(
                repository_id=repo.id,
                finding_type=FindingType.SECRET,
                severity=SeverityLevel.CRITICAL,
                status=FindingStatus.OPEN,
                title="Finding 1",
                description="Test"
            ),
            SecurityFinding(
                repository_id=repo.id,
                finding_type=FindingType.SECRET,
                severity=SeverityLevel.HIGH,
                status=FindingStatus.OPEN,
                title="Finding 2",
                description="Test"
            ),
            SecurityFinding(
                repository_id=repo.id,
                finding_type=FindingType.VULNERABILITY,
                severity=SeverityLevel.MEDIUM,
                status=FindingStatus.RESOLVED,
                title="Finding 3",
                description="Test"
            ),
        ]
        
        for finding in findings:
            test_db.add(finding)
        
        await test_db.commit()
        
        # Get stats
        response = await client.get("/api/v1/findings/stats/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_findings"] == 3
        assert "by_severity" in data
        assert "by_type" in data
        assert "by_status" in data
    
    async def test_pagination(self, client: AsyncClient, test_db):
        """Test pagination of findings"""
        # Create test data
        repo = Repository(
            github_id=12345,
            full_name="test/repo",
            owner="test",
            name="repo"
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Create 15 findings
        for i in range(15):
            finding = SecurityFinding(
                repository_id=repo.id,
                finding_type=FindingType.SECRET,
                severity=SeverityLevel.LOW,
                status=FindingStatus.OPEN,
                title=f"Finding {i}",
                description="Test"
            )
            test_db.add(finding)
        
        await test_db.commit()
        
        # Get first page
        response = await client.get("/api/v1/findings/?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Get second page
        response = await client.get("/api/v1/findings/?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
