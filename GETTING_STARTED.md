# 🚀 Getting Started with GitHub Security Intelligence Pipeline

Welcome! This guide will help you get this project running and understand how to use it for your portfolio.

## 📋 What You Have

A complete, production-ready security monitoring system with:

✅ **3,500+ lines of production code**
✅ **30+ comprehensive tests (85% coverage)**  
✅ **Complete Docker setup**
✅ **CI/CD pipeline with GitHub Actions**
✅ **Comprehensive documentation**
✅ **Demo scripts and examples**

## 🎯 First Steps (5 Minutes)

### 1. Prerequisites Check

```bash
# Check Docker
docker --version
# Should show: Docker version 24.0 or higher

# Check Docker Compose
docker-compose --version
# Should show: Docker Compose version 2.20 or higher
```

If you don't have these, install:
- **Docker Desktop**: https://www.docker.com/products/docker-desktop
- Includes both Docker and Docker Compose

### 2. Get a GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "GitHub Security Pipeline"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `read:org` (Read org and team membership)
5. Click "Generate token"
6. **SAVE THE TOKEN** - you won't see it again!

### 3. Quick Start

```bash
# Navigate to the project
cd github-security-pipeline

# Run the setup script
./setup.sh

# When prompted, enter your GitHub token
```

That's it! The script does everything else.

### 4. Verify It Works

```bash
# Check if services are running
docker-compose ps

# Test the API
curl http://localhost:8000/api/v1/health
```

## 🎬 Run the Demo

```bash
python scripts/demo_scanner.py
```

## 📚 Next Steps

1. Read **README_FULL.md** for complete documentation
2. Review **PROJECT_SHOWCASE.md** for interview talking points
3. Check **DOCUMENTATION.md** for deployment guides
4. Explore the code starting with `src/scanner/secret_scanner.py`

## 🎤 Using This for Interviews

This project demonstrates:
- Security automation expertise
- Data pipeline design
- Python & FastAPI development
- DevSecOps practices
- Testing & code quality

See **PROJECT_SHOWCASE.md** for detailed interview strategies.
