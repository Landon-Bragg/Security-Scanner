"""
Application configuration using Pydantic settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # GitHub
    GITHUB_TOKEN: str
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_API_RATE_LIMIT: int = 5000

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Security Scanning
    MAX_FILE_SIZE_MB: int = 10
    SCAN_TIMEOUT_SECONDS: int = 300
    ENABLE_ENTROPY_SCANNING: bool = True
    SCAN_RATE_LIMIT: int = 100

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Alert Configuration
    ALERT_WEBHOOK_URL: str = ""
    SLACK_WEBHOOK_URL: str = ""

    # Redis Streams
    STREAM_MAX_LEN: int = 10000
    STREAM_CONSUMER_GROUP: str = "scanner-workers"

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


# Global settings instance
settings = Settings()
