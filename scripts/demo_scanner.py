#!/usr/bin/env python3
"""
Demo script to test the secret scanner functionality
Creates sample files with various types of secrets and scans them
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scanner.secret_scanner import SecretScanner


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_finding(finding, index):
    """Print a finding in a formatted way"""
    severity_colors = {
        "critical": "\033[91m",  # Red
        "high": "\033[93m",  # Yellow
        "medium": "\033[94m",  # Blue
        "low": "\033[92m",  # Green
    }

    color = severity_colors.get(finding.severity, "\033[0m")
    reset = "\033[0m"

    print(f"{color}[{index}] {finding.secret_type} - {finding.severity.upper()}{reset}")
    print(f"    File: {finding.file_path}")
    print(
        f"    Line: {finding.line_number}, Columns: {finding.column_start}-{finding.column_end}"
    )
    print(f"    Entropy: {finding.entropy:.2f}")
    print(f"    Confidence: {finding.confidence:.0%}")
    print(f"    Preview: {finding.matched_string[:80]}...")
    print()


def main():
    """Main demo function"""
    print_header("GitHub Security Intelligence Pipeline - Secret Scanner Demo")

    # Sample files with various secrets
    test_files = {
        "config.py": """
# Application Configuration
import os

# AWS Credentials - CRITICAL FINDING
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# GitHub Token - HIGH FINDING
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz123"

# Database Connection - HIGH FINDING
DATABASE_URL = "postgresql://admin:SuperSecret123@db.example.com:5432/mydb"

# Safe configuration
APP_NAME = "SecureApp"
VERSION = "1.0.0"
DEBUG = False
        """,
        "api_keys.env": """
# API Keys Configuration

# Stripe API Key - CRITICAL FINDING
STRIPE_SECRET_KEY=sk_live_51H7hZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# SendGrid API Key - HIGH FINDING
SENDGRID_API_KEY=SG.1234567890abcdefghij.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr

# Slack Webhook - MEDIUM FINDING
SLACK_WEBHOOK=xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx

# Safe values
APP_ENV=production
LOG_LEVEL=info
        """,
        "keys/private.pem": """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyz
ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/==
... (truncated for demo)
-----END RSA PRIVATE KEY-----
        """,
        "jwt_example.py": """
# JWT Token Example

# Real JWT token - HIGH FINDING
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

def verify_token(token):
    # Implementation here
    pass
        """,
        "safe_config.py": """
# Safe Configuration File - NO FINDINGS EXPECTED

APP_NAME = "MyApplication"
VERSION = "2.0.0"
DEBUG = False
ALLOWED_HOSTS = ["example.com", "www.example.com"]

# These are examples and should not trigger (false positives filtered)
API_KEY_EXAMPLE = "your_api_key_here"
SECRET_PLACEHOLDER = "replace_with_your_secret"
DUMMY_TOKEN = "xxxxxxxxxxxxxxxxxxxxx"
        """,
    }

    print(f"Testing {len(test_files)} sample files...\n")

    total_findings = 0
    scanner = SecretScanner()

    for filename, content in test_files.items():
        print_header(f"Scanning: {filename}")

        findings = scanner.scan_content(content, filename)

        if findings:
            print(f"🚨 Found {len(findings)} potential secret(s):\n")
            for idx, finding in enumerate(findings, 1):
                print_finding(finding, idx)
                total_findings += 1
        else:
            print("✅ No secrets detected in this file.\n")

    # Print summary
    print_header("Scan Summary")

    print(f"Total files scanned: {len(test_files)}")
    print(f"Total secrets found: {total_findings}")
    print()

    if total_findings > 0:
        print("\033[91m⚠️  WARNING: Secrets detected!\033[0m")
        print("These findings would be stored in the database and visible via the API.")
        print()

    # Test entropy calculation
    print_header("Entropy Analysis Examples")

    test_strings = [
        ("Random API Key", "aB3$xK9mQ2pL7nR4vT8wZ1yF6jC0sD5gH"),
        ("Low Entropy", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        ("Medium Entropy", "password123password123password123"),
        ("High Entropy (AWS)", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
    ]

    for name, string in test_strings:
        entropy = scanner.calculate_shannon_entropy(string)
        color = (
            "\033[91m" if entropy > 4.5 else "\033[93m" if entropy > 3.5 else "\033[92m"
        )
        print(f"{color}{name:20s} Entropy: {entropy:.2f}\033[0m")

    print()

    # Test file extension filtering
    print_header("File Extension Filtering Test")

    test_extensions = [
        "config.py",
        "app.js",
        ".env",
        "secrets.yaml",
        "image.png",
        "video.mp4",
        "app.exe",
    ]

    for filename in test_extensions:
        should_scan = scanner.should_scan_file(filename)
        status = "✅ SCAN" if should_scan else "⏭️  SKIP"
        print(f"{status:10s} {filename}")

    print()
    print_header("Demo Complete!")
    print("To see this in action with real repositories:")
    print("1. Set up webhooks on your GitHub repository")
    print("2. Push commits with secrets (in a test repo!)")
    print("3. Check findings via API: http://localhost:8000/api/v1/findings/")
    print()


if __name__ == "__main__":
    main()
