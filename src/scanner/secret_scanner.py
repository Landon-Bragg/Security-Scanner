"""
Secret scanner using regex patterns and entropy analysis
"""

import re
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class SecretPattern:
    """Represents a secret detection pattern"""

    name: str
    pattern: re.Pattern
    entropy_threshold: Optional[float] = None
    description: str = ""


@dataclass
class SecretMatch:
    """Represents a detected secret"""

    secret_type: str
    matched_string: str
    line_number: int
    column_start: int
    column_end: int
    entropy: float
    file_path: str
    severity: str
    confidence: float


class SecretScanner:
    """Scanner for detecting exposed secrets in code"""

    # Common secret patterns
    PATTERNS = [
        SecretPattern(
            name="AWS Access Key ID",
            pattern=re.compile(
                r"(?i)(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"
            ),
            entropy_threshold=4.5,
            description="AWS Access Key ID",
        ),
        SecretPattern(
            name="AWS Secret Access Key",
            pattern=re.compile(r'(?i)aws(.{0,20})?["\']?[0-9a-zA-Z/+]{40}["\']?'),
            entropy_threshold=4.5,
            description="AWS Secret Access Key",
        ),
        SecretPattern(
            name="GitHub Token",
            pattern=re.compile(r"(?i)gh[pousr]_[A-Za-z0-9_]{36,255}"),
            entropy_threshold=5.0,
            description="GitHub Personal Access Token or OAuth Token",
        ),
        SecretPattern(
            name="GitHub Fine-Grained Token",
            pattern=re.compile(r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"),
            entropy_threshold=5.0,
            description="GitHub Fine-Grained Personal Access Token",
        ),
        SecretPattern(
            name="Generic API Key",
            pattern=re.compile(
                r'(?i)(?:api[_-]?key|apikey|api[_-]?token)[\s:=]+["\']?([a-z0-9_\-]{20,})["\']?'
            ),
            entropy_threshold=4.0,
            description="Generic API Key",
        ),
        SecretPattern(
            name="Slack Token",
            pattern=re.compile(
                r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"
            ),
            entropy_threshold=4.5,
            description="Slack Token",
        ),
        SecretPattern(
            name="Google API Key",
            pattern=re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
            entropy_threshold=4.0,
            description="Google API Key",
        ),
        SecretPattern(
            name="Google OAuth",
            pattern=re.compile(
                r"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com"
            ),
            entropy_threshold=4.0,
            description="Google OAuth Client ID",
        ),
        SecretPattern(
            name="RSA Private Key",
            pattern=re.compile(
                r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----"
            ),
            entropy_threshold=None,
            description="Private Key",
        ),
        SecretPattern(
            name="SSH Private Key",
            pattern=re.compile(r"-----BEGIN PRIVATE KEY-----"),
            entropy_threshold=None,
            description="SSH Private Key",
        ),
        SecretPattern(
            name="PostgreSQL Connection String",
            pattern=re.compile(
                r"postgres(?:ql)?://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@[a-zA-Z0-9\.\-]+(?::\d+)?/[a-zA-Z0-9_\-]+"
            ),
            entropy_threshold=3.5,
            description="PostgreSQL Connection String with credentials",
        ),
        SecretPattern(
            name="MySQL Connection String",
            pattern=re.compile(
                r"mysql://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@[a-zA-Z0-9\.\-]+(?::\d+)?/[a-zA-Z0-9_\-]+"
            ),
            entropy_threshold=3.5,
            description="MySQL Connection String with credentials",
        ),
        SecretPattern(
            name="JWT Token",
            pattern=re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
            entropy_threshold=4.5,
            description="JSON Web Token",
        ),
        SecretPattern(
            name="Stripe API Key",
            pattern=re.compile(r"(?:r|s)k_live_[0-9a-zA-Z]{24,}"),
            entropy_threshold=4.5,
            description="Stripe API Key",
        ),
        SecretPattern(
            name="Twilio API Key",
            pattern=re.compile(r"SK[a-z0-9]{32}"),
            entropy_threshold=4.5,
            description="Twilio API Key",
        ),
        SecretPattern(
            name="PyPI Token",
            pattern=re.compile(r"pypi-AgEIcHlwaS5vcmc[A-Za-z0-9\-_]{50,}"),
            entropy_threshold=5.0,
            description="PyPI Upload Token",
        ),
        SecretPattern(
            name="NPM Token",
            pattern=re.compile(r"npm_[a-zA-Z0-9]{36}"),
            entropy_threshold=4.5,
            description="NPM Access Token",
        ),
        SecretPattern(
            name="Docker Hub Token",
            pattern=re.compile(r"dckr_pat_[a-zA-Z0-9_-]{36,}"),
            entropy_threshold=4.5,
            description="Docker Hub Personal Access Token",
        ),
        SecretPattern(
            name="Heroku API Key",
            pattern=re.compile(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
            ),
            entropy_threshold=4.0,
            description="Heroku API Key (UUID format)",
        ),
        SecretPattern(
            name="Azure Connection String",
            pattern=re.compile(
                r"DefaultEndpointsProtocol=https;AccountName=[a-zA-Z0-9]+;AccountKey=[A-Za-z0-9+/=]{88}"
            ),
            entropy_threshold=4.5,
            description="Azure Storage Connection String",
        ),
        SecretPattern(
            name="Mailgun API Key",
            pattern=re.compile(r"key-[0-9a-zA-Z]{32}"),
            entropy_threshold=4.5,
            description="Mailgun API Key",
        ),
        SecretPattern(
            name="SendGrid API Key",
            pattern=re.compile(r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}"),
            entropy_threshold=5.0,
            description="SendGrid API Key",
        ),
    ]

    # File extensions to scan
    SCANNABLE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".go",
        ".rb",
        ".php",
        ".cs",
        ".cpp",
        ".c",
        ".sh",
        ".bash",
        ".zsh",
        ".env",
        ".config",
        ".cfg",
        ".ini",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".xml",
        ".properties",
        ".conf",
        ".txt",
        ".md",
    }

    # Patterns to exclude (likely false positives)
    EXCLUDE_PATTERNS = [
        re.compile(r"example", re.IGNORECASE),
        re.compile(r"sample", re.IGNORECASE),
        re.compile(r"placeholder", re.IGNORECASE),
        re.compile(r"your[_-]?api[_-]?key", re.IGNORECASE),
        re.compile(r"dummy", re.IGNORECASE),
        re.compile(r"test[_-]?key", re.IGNORECASE),
        re.compile(r"fake", re.IGNORECASE),
        re.compile(r"xxx+", re.IGNORECASE),
    ]

    @staticmethod
    def calculate_shannon_entropy(data: str) -> float:
        """
        Calculate Shannon entropy of a string

        Args:
            data: String to calculate entropy for

        Returns:
            Entropy value
        """
        if not data:
            return 0.0

        entropy = 0.0
        for x in range(256):
            p_x = float(data.count(chr(x))) / len(data)
            if p_x > 0:
                entropy += -p_x * math.log2(p_x)

        return entropy

    @classmethod
    def is_likely_false_positive(cls, matched_string: str) -> bool:
        """
        Check if a match is likely a false positive

        Args:
            matched_string: The matched string to check

        Returns:
            True if likely false positive
        """
        for pattern in cls.EXCLUDE_PATTERNS:
            if pattern.search(matched_string):
                return True
        return False

    @classmethod
    def scan_content(
        cls, content: str, file_path: str = "unknown"
    ) -> List[SecretMatch]:
        """
        Scan content for secrets

        Args:
            content: File content to scan
            file_path: Path to the file being scanned

        Returns:
            List of detected secrets
        """
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Skip very long lines (likely minified code or data)
            if len(line) > 10000:
                continue

            for pattern in cls.PATTERNS:
                for match in pattern.pattern.finditer(line):
                    matched_string = match.group(0)

                    # Check for false positives
                    if cls.is_likely_false_positive(matched_string):
                        continue

                    # Calculate entropy
                    entropy = cls.calculate_shannon_entropy(matched_string)

                    # Skip if entropy is below threshold
                    if (
                        pattern.entropy_threshold
                        and entropy < pattern.entropy_threshold
                    ):
                        continue

                    # Determine severity based on pattern and entropy
                    severity = cls._determine_severity(pattern.name, entropy)
                    confidence = cls._calculate_confidence(
                        entropy, pattern.entropy_threshold
                    )

                    findings.append(
                        SecretMatch(
                            secret_type=pattern.name,
                            matched_string=matched_string[:100],  # Truncate for safety
                            line_number=line_num,
                            column_start=match.start(),
                            column_end=match.end(),
                            entropy=entropy,
                            file_path=file_path,
                            severity=severity,
                            confidence=confidence,
                        )
                    )

                    logger.debug(
                        "Secret detected",
                        secret_type=pattern.name,
                        file_path=file_path,
                        line_number=line_num,
                        entropy=entropy,
                    )

        return findings

    @staticmethod
    def _determine_severity(secret_type: str, entropy: float) -> str:
        """Determine severity based on secret type and entropy"""
        critical_types = ["AWS Secret Access Key", "Private Key", "SSH Private Key"]
        high_types = ["AWS Access Key ID", "GitHub Token", "Stripe API Key"]

        if secret_type in critical_types:
            return "critical"
        elif secret_type in high_types and entropy > 4.5:
            return "high"
        elif entropy > 5.0:
            return "high"
        elif entropy > 4.0:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _calculate_confidence(entropy: float, threshold: Optional[float]) -> float:
        """Calculate confidence score (0-1)"""
        if threshold is None:
            return 1.0  # Patterns without entropy threshold are high confidence

        if entropy >= threshold + 1.0:
            return 1.0
        elif entropy >= threshold:
            return 0.8
        elif entropy >= threshold - 0.5:
            return 0.6
        else:
            return 0.4

    @classmethod
    def should_scan_file(cls, file_path: str) -> bool:
        """
        Determine if a file should be scanned based on its extension

        Args:
            file_path: Path to the file

        Returns:
            True if file should be scanned
        """
        import os

        _, ext = os.path.splitext(file_path.lower())
        return ext in cls.SCANNABLE_EXTENSIONS or not ext
