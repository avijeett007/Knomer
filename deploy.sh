#!/bin/bash

# 🚀 Video Processing API - Production Deployment Script
# This script automates the production deployment process

set -e  # Exit on any error

echo "🚀 Video Processing API - Production Deployment"
echo "================================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root for security reasons"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to generate secure random string
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

echo "🔍 Checking system requirements..."

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "✅ Linux detected"
    OS="linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    echo "✅ Windows detected"
    OS="windows"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Check Docker
if ! command_exists docker; then
    echo "❌ Docker not found. Please install Docker first."
    echo "   Linux: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    echo "   Windows: Download from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Docker Compose
if ! command_exists docker-compose; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ All requirements met"

# Get deployment configuration
echo ""
echo "📋 Deployment Configuration"
echo "=========================="

read -p "🌐 Enter your domain name (or IP address): " DOMAIN
read -p "📧 Enter your email for SSL certificates: " EMAIL
read -p "🔑 Do you have Supabase credentials? (y/n): " HAS_SUPABASE

if [[ $HAS_SUPABASE == "y" ]]; then
    read -p "🔗 Supabase URL: " SUPABASE_URL
    read -s -p "🔑 Supabase Service Key: " SUPABASE_SERVICE_KEY
    echo ""
    read -p "🗄️ Database URL: " DATABASE_URL
else
    echo "⚠️  Using local SQLite database (not recommended for production)"
    SUPABASE_URL=""
    SUPABASE_SERVICE_KEY=""
    DATABASE_URL=""
fi

# Generate secrets
echo ""
echo "🔐 Generating secure secrets..."
SECRET_KEY=$(generate_secret)
JWT_SECRET=$(generate_secret)

echo "✅ Secrets generated"

# Create production environment file
echo ""
echo "📝 Creating production configuration..."

cat > .env.production << EOF
# ===== SECURITY =====
SECRET_KEY="$SECRET_KEY"
JWT_SECRET="$JWT_SECRET"
API_KEY_PREFIX="vp_"

# ===== DATABASE =====
SUPABASE_URL="$SUPABASE_URL"
SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY"
DATABASE_URL="$DATABASE_URL"
USE_SQLITE=$([ -z "$SUPABASE_URL" ] && echo "true" || echo "false")

# ===== REDIS =====
REDIS_URL="redis://redis:6379/0"
REDIS_PASSWORD=""

# ===== STORAGE =====
STORAGE_BUCKET="video-processing"
USE_LOCAL_STORAGE=$([ -z "$SUPABASE_URL" ] && echo "true" || echo "false")

# ===== API CONFIGURATION =====
HOST="0.0.0.0"
PORT=8000
DEBUG=false
API_TITLE="Video Processing API"
API_VERSION="2.0.0"

# ===== RATE LIMITING =====
DEFAULT_RATE_LIMIT_PER_MINUTE=60
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_DAY=10000

# ===== CREDIT SYSTEM =====
CREDITS_PER_10_SECONDS=1
FREE_TIER_CREDITS=100

# ===== PROCESSING LIMITS =====
MAX_VIDEO_SIZE_MB=1000
MAX_VIDEO_DURATION_SECONDS=1800
MAX_VIDEOS_PER_JOB=20
PROCESSING_TIMEOUT_SECONDS=3600

# ===== FILE CLEANUP =====
TEMP_FILE_CLEANUP_HOURS=2
OUTPUT_FILE_RETENTION_DAYS=30

# ===== MONITORING =====
LOG_LEVEL="INFO"
PYTHONUNBUFFERED=1
EOF

echo "✅ Production configuration created"

# Create directories
echo ""
echo "📁 Creating directories..."
mkdir -p temp logs ssl

echo "✅ Directories created"

# Build and start services
echo ""
echo "🏗️ Building and starting services..."
docker-compose -f docker-compose.production.yml up -d --build

echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo ""
echo "🔍 Checking service health..."

if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API service is healthy"
else
    echo "❌ API service is not responding"
    echo "📋 Check logs: docker-compose -f docker-compose.production.yml logs"
    exit 1
fi

# Get API key
echo ""
echo "🔑 Getting API key..."
API_KEY=$(docker-compose -f docker-compose.production.yml logs video-processor-api 2>/dev/null | grep "Test API key" | tail -1 | sed 's/.*Test API key: //')

if [[ -n "$API_KEY" ]]; then
    echo "✅ API Key: $API_KEY"
else
    echo "⚠️  Could not retrieve API key automatically"
    echo "   Check logs: docker-compose -f docker-compose.production.yml logs video-processor-api | grep 'API key'"
fi

# SSL Setup (Linux only)
if [[ $OS == "linux" ]] && [[ $DOMAIN != *"localhost"* ]] && [[ $DOMAIN != *"127.0.0.1"* ]]; then
    echo ""
    read -p "🔒 Set up SSL certificates with Let's Encrypt? (y/n): " SETUP_SSL
    
    if [[ $SETUP_SSL == "y" ]]; then
        echo "🔒 Setting up SSL certificates..."
        
        # Install certbot if not present
        if ! command_exists certbot; then
            sudo apt update
            sudo apt install -y certbot
        fi
        
        # Get SSL certificate
        sudo certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos --non-interactive
        
        # Copy certificates
        sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
        sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
        sudo chown $USER:$USER ssl/*.pem
        
        echo "✅ SSL certificates configured"
    fi
fi

# Final status
echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "🌐 API Endpoint: http://$DOMAIN:8000"
echo "🔑 API Key: $API_KEY"
echo "📊 Monitoring: http://$DOMAIN:5555 (Flower)"
echo ""
echo "📋 Useful Commands:"
echo "   View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "   Restart: docker-compose -f docker-compose.production.yml restart"
echo "   Stop: docker-compose -f docker-compose.production.yml down"
echo "   Scale workers: docker-compose -f docker-compose.production.yml up -d --scale celery-worker=4"
echo ""
echo "📖 Full documentation: PRODUCTION_DEPLOYMENT.md"
echo ""
echo "🚀 Your video processing API is now live and ready for production use!"
