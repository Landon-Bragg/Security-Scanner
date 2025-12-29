"""
Scanner worker that processes events from Redis streams
"""

import asyncio
from typing import Dict, Any
import structlog
from github import Github, GithubException
from sqlalchemy import select

from src.core.config import settings
from src.core.redis_client import redis_stream_client
from src.core.database import (
    AsyncSessionLocal,
    Repository,
    SecurityFinding,
    ScanJob,
    FindingType,
    SeverityLevel,
)
from src.scanner.secret_scanner import SecretScanner

logger = structlog.get_logger()


class ScannerWorker:
    """Worker that scans repositories for security issues"""

    def __init__(self):
        self.github_client = Github(settings.GITHUB_TOKEN)
        self.secret_scanner = SecretScanner()
        self.consumer_name = "scanner-worker-1"

    async def process_push_event(self, event_data: Dict[str, Any]):
        """
        Process a push event

        Args:
            event_data: Event data from Redis stream
        """
        payload = event_data.get("payload", {})
        repo_full_name = event_data.get("repository")
        commits = payload.get("commits", [])

        if not commits:
            logger.debug("No commits in push event", repository=repo_full_name)
            return

        logger.info(
            "Processing push event",
            repository=repo_full_name,
            commit_count=len(commits),
        )

        # Get or create repository record
        async with AsyncSessionLocal() as db:
            repo_record = await self._get_or_create_repository(
                db, payload.get("repository", {})
            )

            # Create scan job
            scan_job = ScanJob(
                repository_id=repo_record.id,
                job_type="push_scan",
                status="running",
                metadata={"commits": len(commits)},
            )
            db.add(scan_job)
            await db.commit()
            await db.refresh(scan_job)

            try:
                # Get GitHub repository
                gh_repo = self.github_client.get_repo(repo_full_name)

                findings_count = 0

                # Scan each commit
                for commit_data in commits[:10]:  # Limit to 10 most recent commits
                    commit_sha = commit_data.get("id")

                    try:
                        commit = gh_repo.get_commit(commit_sha)

                        # Scan files in commit
                        for file in commit.files:
                            if not self.secret_scanner.should_scan_file(file.filename):
                                continue

                            # Skip large files
                            if file.changes > 1000:
                                logger.debug(
                                    "Skipping large file",
                                    file=file.filename,
                                    changes=file.changes,
                                )
                                continue

                            # Get file content (only for additions/modifications)
                            if file.status in ["added", "modified"]:
                                try:
                                    # Get file content from the commit
                                    file_content = gh_repo.get_contents(
                                        file.filename, ref=commit_sha
                                    )

                                    if file_content.size > settings.max_file_size_bytes:
                                        logger.debug(
                                            "Skipping file - too large",
                                            file=file.filename,
                                            size=file_content.size,
                                        )
                                        continue

                                    content = file_content.decoded_content.decode(
                                        "utf-8", errors="ignore"
                                    )

                                    # Scan for secrets
                                    secrets = self.secret_scanner.scan_content(
                                        content=content, file_path=file.filename
                                    )

                                    # Store findings
                                    for secret in secrets:
                                        finding = SecurityFinding(
                                            repository_id=repo_record.id,
                                            finding_type=FindingType.SECRET,
                                            severity=SeverityLevel(secret.severity),
                                            title=f"{secret.secret_type} detected in {file.filename}",
                                            description=f"Potential {secret.secret_type} found at line {secret.line_number}",
                                            file_path=file.filename,
                                            line_number=secret.line_number,
                                            commit_sha=commit_sha,
                                            secret_type=secret.secret_type,
                                            entropy_score=secret.entropy,
                                            metadata={
                                                "confidence": secret.confidence,
                                                "column_start": secret.column_start,
                                                "column_end": secret.column_end,
                                            },
                                        )
                                        db.add(finding)
                                        findings_count += 1

                                        logger.warning(
                                            "Secret detected",
                                            repository=repo_full_name,
                                            file=file.filename,
                                            secret_type=secret.secret_type,
                                            severity=secret.severity,
                                        )

                                except Exception as e:
                                    logger.error(
                                        "Error scanning file",
                                        file=file.filename,
                                        error=str(e),
                                    )
                                    continue

                    except GithubException as e:
                        logger.error(
                            "Error fetching commit", commit_sha=commit_sha, error=str(e)
                        )
                        continue

                # Update scan job
                scan_job.status = "completed"
                scan_job.findings_count = findings_count
                scan_job.completed_at = asyncio.get_event_loop().time()

                await db.commit()

                logger.info(
                    "Push scan completed",
                    repository=repo_full_name,
                    findings=findings_count,
                )

            except Exception as e:
                logger.error(
                    "Error processing push event",
                    repository=repo_full_name,
                    error=str(e),
                )
                scan_job.status = "failed"
                scan_job.error_message = str(e)
                await db.commit()

    async def _get_or_create_repository(
        self, db, repo_data: Dict[str, Any]
    ) -> Repository:
        """Get or create repository record"""
        github_id = repo_data.get("id")

        # Try to find existing
        result = await db.execute(
            select(Repository).where(Repository.github_id == github_id)
        )
        repo = result.scalar_one_or_none()

        if repo:
            return repo

        # Create new
        repo = Repository(
            github_id=github_id,
            full_name=repo_data.get("full_name", ""),
            owner=repo_data.get("owner", {}).get("login", ""),
            name=repo_data.get("name", ""),
            description=repo_data.get("description"),
            is_private=repo_data.get("private", False),
            stars=repo_data.get("stargazers_count", 0),
            language=repo_data.get("language"),
            metadata=repo_data,
        )

        db.add(repo)
        await db.commit()
        await db.refresh(repo)

        return repo

    async def run(self):
        """Main worker loop"""
        logger.info("Starting scanner worker", consumer=self.consumer_name)

        await redis_stream_client.connect()

        # Create consumer groups
        await redis_stream_client.create_consumer_group(
            redis_stream_client.STREAM_PUSH_EVENTS, settings.STREAM_CONSUMER_GROUP
        )

        while True:
            try:
                # Consume push events
                events = await redis_stream_client.consume_events(
                    stream_name=redis_stream_client.STREAM_PUSH_EVENTS,
                    group_name=settings.STREAM_CONSUMER_GROUP,
                    consumer_name=self.consumer_name,
                    count=1,
                    block=5000,
                )

                for event_id, event_data in events:
                    try:
                        await self.process_push_event(event_data)

                        # Acknowledge event
                        await redis_stream_client.acknowledge_event(
                            redis_stream_client.STREAM_PUSH_EVENTS,
                            settings.STREAM_CONSUMER_GROUP,
                            event_id,
                        )

                    except Exception as e:
                        logger.error(
                            "Error processing event", event_id=event_id, error=str(e)
                        )
                        # Don't acknowledge - will be retried

            except KeyboardInterrupt:
                logger.info("Shutting down scanner worker")
                break
            except Exception as e:
                logger.error("Worker error", error=str(e))
                await asyncio.sleep(5)


async def main():
    """Entry point for scanner worker"""
    worker = ScannerWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
