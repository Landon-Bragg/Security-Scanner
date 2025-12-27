# GitHub Security Intelligence Pipeline

A real-time security monitoring system that scans GitHub repositories for exposed secrets, vulnerabilities, and security advisories.

## 🎯 Features

- **Real-time Secret Detection**: Scans commits for exposed API keys, tokens, and credentials
- **Vulnerability Monitoring**: Tracks security advisories for popular packages
- **Supply Chain Analysis**: Monitors dependency changes and known vulnerabilities
- **Streaming Architecture**: Event-driven processing with Redis Streams
- **RESTful API**: Query security findings and subscribe to alerts
- **Comprehensive Testing**: Full pytest suite with >80% coverage

## 🏗️ Architecture

```
GitHub → Webhooks → FastAPI Ingester → Redis Streams → Scanner Workers → PostgreSQL
                                                              ↓
                                                         Alert System
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- GitHub Personal Access Token

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/github-security-pipeline.git
cd github-security-pipeline

# Create environment file
cp .env.example .env
# Edit .env with your GitHub token

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Check service health
curl http://localhost:8000/health
```

##