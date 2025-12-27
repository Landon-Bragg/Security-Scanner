"""
Tests for secret scanner
"""
import pytest
from src.scanner.secret_scanner import SecretScanner


class TestSecretScanner:
    """Test suite for SecretScanner"""
    
    def test_aws_access_key_detection(self):
        """Test AWS access key detection"""
        content = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        findings = SecretScanner.scan_content(content, "test.py")
        
        assert len(findings) > 0
        assert any(f.secret_type == "AWS Access Key ID" for f in findings)
    
    def test_aws_secret_key_detection(self):
        """Test AWS secret key detection"""
        content = 'aws_secret="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        findings = SecretScanner.scan_content(content, "config.py")
        
        assert len(findings) > 0
    
    def test_github_token_detection(self):
        """Test GitHub token detection"""
        content = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz123"
        findings = SecretScanner.scan_content(content, "env.py")
        
        assert len(findings) > 0
        assert any("GitHub Token" in f.secret_type for f in findings)
    
    def test_github_fine_grained_token_detection(self):
        """Test GitHub fine-grained token detection"""
        content = "TOKEN=github_pat_11ABCDEFG0123456789ABC_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxy"
        findings = SecretScanner.scan_content(content, "auth.py")
        
        assert len(findings) > 0
        assert any("GitHub Fine-Grained Token" in f.secret_type for f in findings)
    
    def test_private_key_detection(self):
        """Test private key detection"""
        content = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyz
-----END RSA PRIVATE KEY-----
        """
        findings = SecretScanner.scan_content(content, "key.pem")
        
        assert len(findings) > 0
        assert any("Private Key" in f.secret_type for f in findings)
    
    def test_database_connection_string_detection(self):
        """Test database connection string detection"""
        content = 'DB_URL="postgresql://admin:SuperSecret123@db.example.com:5432/mydb"'
        findings = SecretScanner.scan_content(content, "database.py")
        
        assert len(findings) > 0
        assert any("PostgreSQL" in f.secret_type for f in findings)
    
    def test_stripe_api_key_detection(self):
        """Test Stripe API key detection"""
        content = "STRIPE_KEY=sk_live_51234567890abcdefghijklmnopqrstuvwxyz"
        findings = SecretScanner.scan_content(content, "payment.py")
        
        assert len(findings) > 0
        assert any("Stripe" in f.secret_type for f in findings)
    
    def test_jwt_token_detection(self):
        """Test JWT token detection"""
        content = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        findings = SecretScanner.scan_content(content, "auth.js")
        
        assert len(findings) > 0
        assert any("JWT" in f.secret_type for f in findings)
    
    def test_false_positive_filtering(self):
        """Test that obvious false positives are filtered"""
        content = """
# Examples - not real secrets
AWS_KEY=your_api_key_here
API_KEY=example_key_placeholder
SECRET=xxxxxxxxxxxxxxxxxxxxxxxxx
TOKEN=sample_token_for_testing
DUMMY_KEY=fake_key_12345
        """
        findings = SecretScanner.scan_content(content, "example.py")
        
        # Should filter out most or all of these
        assert len(findings) == 0 or all(f.confidence < 0.5 for f in findings)
    
    def test_entropy_calculation(self):
        """Test Shannon entropy calculation"""
        # High entropy string (random)
        high_entropy = "aB3$xK9mQ2pL7nR4vT8wZ1yF6jC0sD5gH"
        entropy_high = SecretScanner.calculate_shannon_entropy(high_entropy)
        
        # Low entropy string (repeated)
        low_entropy = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        entropy_low = SecretScanner.calculate_shannon_entropy(low_entropy)
        
        assert entropy_high > entropy_low
        assert entropy_high > 4.0
        assert entropy_low < 1.0
    
    def test_file_extension_filtering(self):
        """Test file extension filtering"""
        assert SecretScanner.should_scan_file("app.py") is True
        assert SecretScanner.should_scan_file("script.js") is True
        assert SecretScanner.should_scan_file("config.yaml") is True
        assert SecretScanner.should_scan_file(".env") is True
        
        # Should not scan binary or media files
        assert SecretScanner.should_scan_file("image.png") is False
        assert SecretScanner.should_scan_file("video.mp4") is False
        assert SecretScanner.should_scan_file("app.exe") is False
    
    def test_line_number_accuracy(self):
        """Test that line numbers are correctly reported"""
        content = """line 1
line 2
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
line 4
"""
        findings = SecretScanner.scan_content(content, "test.py")
        
        assert len(findings) > 0
        # Secret is on line 3
        assert any(f.line_number == 3 for f in findings)
    
    def test_multiple_secrets_same_file(self, sample_secret_content):
        """Test detection of multiple secrets in same file"""
        findings = SecretScanner.scan_content(sample_secret_content, "config.py")
        
        # Should find multiple types of secrets
        assert len(findings) >= 3
        
        secret_types = {f.secret_type for f in findings}
        assert len(secret_types) >= 2  # At least 2 different types
    
    def test_severity_assignment(self):
        """Test severity levels are correctly assigned"""
        # Critical: Private key
        content = "-----BEGIN RSA PRIVATE KEY-----"
        findings = SecretScanner.scan_content(content, "key.pem")
        assert len(findings) > 0
        assert findings[0].severity == "critical"
        
        # High: AWS secret with high entropy
        content = "AWS_SECRET=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        findings = SecretScanner.scan_content(content, "aws.py")
        if findings:  # Depends on entropy threshold
            assert findings[0].severity in ["high", "critical"]
    
    def test_empty_content(self):
        """Test handling of empty content"""
        findings = SecretScanner.scan_content("", "empty.py")
        assert len(findings) == 0
    
    def test_very_long_lines(self):
        """Test handling of very long lines (minified code)"""
        content = "x=" + "a" * 20000  # Very long line
        findings = SecretScanner.scan_content(content, "minified.js")
        
        # Should skip very long lines
        assert len(findings) == 0
    
    def test_unicode_content(self):
        """Test handling of unicode content"""
        content = """
# 中文注释
API_KEY = "test_key_with_unicode_周围"
SECRET = "AKIAIOSFODNN7EXAMPLE"
        """
        findings = SecretScanner.scan_content(content, "unicode.py")
        
        # Should still detect secrets
        assert len(findings) > 0
