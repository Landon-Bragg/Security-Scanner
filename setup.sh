#!/bin/bash

# GitHub Security Intelligence Pipeline - Setup Script
# This script sets up the development environment

set -e

echo "🚀 GitHub Security Intelligence Pipeline - Setup"
echo "================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}📝 Please edit .env and add your GITHUB_TOKEN${NC}"
    echo ""
    
    # Prompt for GitHub token
    read -p "Do you want to enter your GitHub token now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your GitHub Personal Access Token: " github_token
        sed -i.bak "s/your_github_personal_access_token_here/$github_token/" .env
        rm .env.bak 2>/dev/null || true
        echo -e "${GREEN}✅ GitHub token configured${NC}"
    fi
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

echo ""
echo "🏗️  Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo ""
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U ghsec_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not ready${NC}"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis is not ready${NC}"
fi

# Check API
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is ready${NC}"
else
    echo -e "${YELLOW}⚠️  API is not ready yet (this may take a few more seconds)${NC}"
fi

echo ""
echo "========================================="
echo -e "${GREEN}✨ Setup Complete!${NC}"
echo "========================================="
echo ""
echo "📚 Next steps:"
echo ""
echo "1. View API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "2. Check service health:"
echo "   curl http://localhost:8000/api/v1/health"
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "4. Run tests:"
echo "   docker-compose exec api pytest tests/ -v"
echo ""
echo "5. Stop services:"
echo "   docker-compose down"
echo ""
echo "📖 For more information, see DOCUMENTATION.md"
echo ""
