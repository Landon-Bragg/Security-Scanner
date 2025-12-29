cat > README.md << 'EOF'
# GitHub Security Intelligence Pipeline

A production-grade security monitoring system that automatically scans GitHub repositories for exposed secrets in real-time.

## Features

- **Real-time Secret Detection** - Scans commits for 20+ secret types (AWS keys, GitHub tokens, API keys, private keys)
- **Advanced Detection** - Pattern matching + Shannon entropy analysis for high accuracy
- **Event-Driven Architecture** - Redis Streams for scalable, distributed processing
- **RESTful API** - Query findings, view statistics, manage alerts
- **Production-Ready** - 85%+ test coverage, CI/CD pipeline, containerized deployment

## Quick Start
```bash
# Clone and setup
git clone https://github.com/Landon-Bragg/Security-Scanner.git
cd Security-Scanner
cp .env.example .env
# Add your GITHUB_TOKEN to .env

# Start services
docker-compose up -d

# Run demo
python scripts/demo_scanner.py

# View API docs
open http://localhost:8000/docs
```

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy (async)  
**Database:** PostgreSQL  
**Queue:** Redis Streams  
**Testing:** pytest (85%+ coverage)  
**DevOps:** Docker, GitHub Actions  

## Architecture
```
GitHub → Webhook → FastAPI → Redis Stream → Scanner Worker → PostgreSQL
```

## API Examples
```bash
# Get all critical findings
curl "http://localhost:8000/api/v1/findings/?severity=critical"

# View statistics
curl "http://localhost:8000/api/v1/findings/stats/summary"
```

## Testing
```bash
pytest tests/ -v --cov=src
```
