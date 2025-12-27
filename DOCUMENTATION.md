# GitHub Security Intelligence Pipeline - Complete Guide

## 📚 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Local Development Setup](#local-development-setup)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [API Documentation](#api-documentation)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Security Best Practices](#security-best-practices)

## Overview

This project is a real-time security intelligence pipeline that monitors GitHub repositories for:

- **Exposed Secrets**: API keys, tokens, credentials, private keys
- **Vulnerabilities**: Known CVEs in dependencies
- **Security Advisories**: GitHub security alerts
- **Supply Chain Risks**: Dependency changes and malicious packages

### Key Features

- ✅ Real-time event processing with Redis Streams
- ✅ Advanced secret detection with entropy analysis
- ✅ RESTful API for querying findings
- ✅ Webhook integration with GitHub
- ✅ Comprehensive test coverage (>80%)
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Docker-based deployment
- ✅ PostgreSQL for persistence
- ✅ Structured logging with context

## Architecture

### Components

```
┌──────────────┐
│   GitHub     │
│  Repositories│
└──────┬───────┘
       │ Webhooks
       ▼
┌──────────────┐      ┌──────────────┐
│   FastAPI    │─────▶│    Redis     │
│   Ingester   │      │   Streams    │
└──────────────┘      └──────┬───────┘
                              │
                              ▼
                      ┌──────────────┐
                      │   Scanner    │
                      │   Workers    │
                      └──────┬───────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  PostgreSQL  │
                      │   Database   │
                      └──────────────┘
```

### Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL 16
- **Message Queue**: Redis Streams
- **ORM**: SQLAlchemy (async)
- **Testing**: pytest + pytest-asyncio
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Prerequisites

### Required Software

- Docker 24.0+ and Docker Compose 2.20+
- Python 3.11+ (for local development)
- Git
- A GitHub account with Personal Access Token

### GitHub Personal Access Token

You need a GitHub Personal Access Token with the following permissions:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
   - `admin:repo_hook` (Full control of repository hooks)
4. Generate and save the token securely

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/github-security-pipeline.git
cd github-security-pipeline
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
DATABASE_URL=postgresql+asyncpg://ghsec_user:ghsec_password@localhost:5432/github_security
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
```

### 4. Start Services with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- FastAPI API on port 8000
- Scanner Worker
- Vulnerability Monitor

### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

## Configuration

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | - | ✅ |
| `GITHUB_WEBHOOK_SECRET` | Webhook signature secret | - | Optional |
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ |
| `REDIS_URL` | Redis connection string | - | ✅ |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO | No |
| `MAX_FILE_SIZE_MB` | Maximum file size to scan | 10 | No |
| `SCAN_TIMEOUT_SECONDS` | Scan timeout | 300 | No |
| `ENABLE_ENTROPY_SCANNING` | Enable entropy-based detection | true | No |

### Configuring GitHub Webhooks

1. Go to your repository → Settings → Webhooks → Add webhook
2. Set Payload URL: `https://your-domain.com/api/v1/webhooks/github`
3. Set Content type: `application/json`
4. Set Secret: (same as `GITHUB_WEBHOOK_SECRET`)
5. Select events:
   - Push
   - Pull requests
   - Releases
   - Security advisories

## Running the Application

### Development Mode

```bash
# Start all services
docker-compose up

# Or run API only (requires manual DB/Redis)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run scanner worker
python -m src.scanner.worker
```

### Production Mode

```bash
docker-compose up -d
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f scanner
```

### Stopping Services

```bash
docker-compose down

# With volume cleanup
docker-compose down -v
```

## API Documentation

### Interactive API Docs

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

#### Health Check
```bash
GET /api/v1/health
GET /api/v1/ready
```

#### Findings
```bash
# List all findings
GET /api/v1/findings/

# Filter findings
GET /api/v1/findings/?severity=critical&finding_type=secret&days=7

# Get specific finding
GET /api/v1/findings/{id}

# Update finding status
PATCH /api/v1/findings/{id}/status?status=resolved

# Get statistics
GET /api/v1/findings/stats/summary
GET /api/v1/findings/stats/repositories
```

#### Webhooks
```bash
# Test endpoint
GET /api/v1/webhooks/github/test

# Webhook receiver (called by GitHub)
POST /api/v1/webhooks/github
```

### Example API Calls

```bash
# Get critical findings from last 7 days
curl "http://localhost:8000/api/v1/findings/?severity=critical&days=7"

# Get statistics
curl "http://localhost:8000/api/v1/findings/stats/summary?days=30"

# Mark finding as resolved
curl -X PATCH "http://localhost:8000/api/v1/findings/123/status?status=resolved"
```

## Testing

### Run All Tests

```bash
# With coverage
pytest tests/ -v --cov=src --cov-report=html

# Specific test file
pytest tests/test_secret_scanner.py -v

# Specific test
pytest tests/test_secret_scanner.py::TestSecretScanner::test_aws_access_key_detection -v
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Running Tests in Docker

```bash
docker-compose exec api pytest tests/ -v
```

## Deployment

### Docker Deployment

1. Build and push Docker image:

```bash
docker build -t your-registry/github-security-pipeline:latest .
docker push your-registry/github-security-pipeline:latest
```

2. Deploy with docker-compose on server:

```bash
# Copy docker-compose.yml and .env to server
docker-compose pull
docker-compose up -d
```

### Cloud Deployment (AWS Example)

1. **Database**: Use AWS RDS PostgreSQL
2. **Cache**: Use AWS ElastiCache for Redis
3. **Compute**: Use AWS ECS or EKS
4. **Load Balancer**: Use AWS ALB
5. **Secrets**: Use AWS Secrets Manager

Example ECS task definition provided in `deployment/aws/` directory.

## Security Best Practices

### Secrets Management

- Never commit `.env` file
- Use environment-specific secrets
- Rotate GitHub tokens regularly
- Use AWS Secrets Manager or similar in production

### API Security

- Enable webhook signature verification
- Use HTTPS in production
- Implement rate limiting
- Add authentication/authorization for API endpoints

### Database Security

- Use strong passwords
- Enable SSL connections
- Regular backups
- Limit network access

### Container Security

- Use non-root user (already configured)
- Scan images with Trivy
- Keep base images updated
- Minimize image size

## Monitoring and Observability

### Metrics to Monitor

- Scan job success/failure rate
- Finding detection rate
- API response times
- Queue depth (Redis)
- Database connection pool

### Recommended Tools

- **Logging**: Structured logging with structlog (included)
- **Metrics**: Prometheus + Grafana
- **APM**: Datadog or New Relic
- **Alerts**: PagerDuty or OpsGenie

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Verify connection
psql -h localhost -U ghsec_user -d github_security
```

#### 2. Redis Connection Failed

```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost ping
```

#### 3. GitHub API Rate Limiting

- Use authenticated requests (token provides 5000 req/hour)
- Implement exponential backoff
- Monitor rate limit headers

#### 4. Scanner Not Processing Events

```bash
# Check scanner logs
docker-compose logs scanner

# Verify Redis stream
redis-cli XINFO STREAM github:push
```

## Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests for new features
3. Ensure all tests pass: `pytest tests/`
4. Run linting: `black src/ tests/`
5. Create pull request

### Code Style

- Follow PEP 8
- Use Black for formatting
- Add type hints
- Write docstrings for public functions

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: GitHub Issues
- **Documentation**: This README + API docs
- **Email**: your-email@example.com

## Roadmap

- [ ] Machine learning for false positive reduction
- [ ] Support for more secret types
- [ ] Real-time alerting (Slack, Email)
- [ ] Web dashboard UI
- [ ] Multi-repository monitoring
- [ ] Historical trend analysis
- [ ] SBOM generation
- [ ] Integration with SIEM tools
