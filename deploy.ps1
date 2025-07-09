# 🚀 Video Processing API - Production Deployment Script (Windows)
# This script automates the production deployment process on Windows

param(
    [string]$Domain = "",
    [string]$Email = "",
    [switch]$Help
)

if ($Help) {
    Write-Host "🚀 Video Processing API - Windows Deployment Script"
    Write-Host "Usage: .\deploy.ps1 -Domain 'your-domain.com' -Email 'your@email.com'"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Domain    Your domain name or IP address"
    Write-Host "  -Email     Your email address"
    Write-Host "  -Help      Show this help message"
    exit 0
}

Write-Host "🚀 Video Processing API - Production Deployment (Windows)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker found" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is available
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose not found. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

# Get deployment configuration
Write-Host ""
Write-Host "📋 Deployment Configuration" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan

if (-not $Domain) {
    $Domain = Read-Host "🌐 Enter your domain name (or IP address)"
}

if (-not $Email) {
    $Email = Read-Host "📧 Enter your email address"
}

$HasSupabase = Read-Host "🔑 Do you have Supabase credentials? (y/n)"

if ($HasSupabase -eq "y") {
    $SupabaseUrl = Read-Host "🔗 Supabase URL"
    $SupabaseServiceKey = Read-Host "🔑 Supabase Service Key" -AsSecureString
    $SupabaseServiceKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SupabaseServiceKey))
    $DatabaseUrl = Read-Host "🗄️ Database URL"
} else {
    Write-Host "⚠️  Using local SQLite database (not recommended for production)" -ForegroundColor Yellow
    $SupabaseUrl = ""
    $SupabaseServiceKeyPlain = ""
    $DatabaseUrl = ""
}

# Generate secrets
Write-Host ""
Write-Host "🔐 Generating secure secrets..." -ForegroundColor Cyan

function Generate-Secret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).Replace("=", "").Replace("+", "").Replace("/", "").Substring(0, 32)
}

$SecretKey = Generate-Secret
$JwtSecret = Generate-Secret

Write-Host "✅ Secrets generated" -ForegroundColor Green

# Create production environment file
Write-Host ""
Write-Host "📝 Creating production configuration..." -ForegroundColor Cyan

$UseLocalStorage = if ($SupabaseUrl) { "false" } else { "true" }
$UseSqlite = if ($SupabaseUrl) { "false" } else { "true" }

$EnvContent = @"
# ===== SECURITY =====
SECRET_KEY="$SecretKey"
JWT_SECRET="$JwtSecret"
API_KEY_PREFIX="vp_"

# ===== DATABASE =====
SUPABASE_URL="$SupabaseUrl"
SUPABASE_SERVICE_KEY="$SupabaseServiceKeyPlain"
DATABASE_URL="$DatabaseUrl"
USE_SQLITE=$UseSqlite

# ===== REDIS =====
REDIS_URL="redis://redis:6379/0"
REDIS_PASSWORD=""

# ===== STORAGE =====
STORAGE_BUCKET="video-processing"
USE_LOCAL_STORAGE=$UseLocalStorage

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
"@

$EnvContent | Out-File -FilePath ".env.production" -Encoding UTF8

Write-Host "✅ Production configuration created" -ForegroundColor Green

# Create directories
Write-Host ""
Write-Host "📁 Creating directories..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path "temp", "logs", "ssl" | Out-Null

Write-Host "✅ Directories created" -ForegroundColor Green

# Build and start services
Write-Host ""
Write-Host "🏗️ Building and starting services..." -ForegroundColor Cyan

docker-compose -f docker-compose.production.yml up -d --build

Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check service health
Write-Host ""
Write-Host "🔍 Checking service health..." -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ API service is healthy" -ForegroundColor Green
    } else {
        throw "API returned status code: $($response.StatusCode)"
    }
} catch {
    Write-Host "❌ API service is not responding" -ForegroundColor Red
    Write-Host "📋 Check logs: docker-compose -f docker-compose.production.yml logs" -ForegroundColor Yellow
    exit 1
}

# Get API key
Write-Host ""
Write-Host "🔑 Getting API key..." -ForegroundColor Cyan

$ApiKeyLog = docker-compose -f docker-compose.production.yml logs video-processor-api 2>$null | Select-String "Test API key"
if ($ApiKeyLog) {
    $ApiKey = ($ApiKeyLog | Select-Object -Last 1).ToString().Split(": ")[1]
    Write-Host "✅ API Key: $ApiKey" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not retrieve API key automatically" -ForegroundColor Yellow
    Write-Host "   Check logs: docker-compose -f docker-compose.production.yml logs video-processor-api | Select-String 'API key'" -ForegroundColor Yellow
    $ApiKey = "Check logs for API key"
}

# Final status
Write-Host ""
Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Service Status:" -ForegroundColor Cyan
docker-compose -f docker-compose.production.yml ps
Write-Host ""
Write-Host "🌐 API Endpoint: http://$Domain`:8000" -ForegroundColor Yellow
Write-Host "🔑 API Key: $ApiKey" -ForegroundColor Yellow
Write-Host "📊 Monitoring: http://$Domain`:5555 (Flower)" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs: docker-compose -f docker-compose.production.yml logs -f"
Write-Host "   Restart: docker-compose -f docker-compose.production.yml restart"
Write-Host "   Stop: docker-compose -f docker-compose.production.yml down"
Write-Host "   Scale workers: docker-compose -f docker-compose.production.yml up -d --scale celery-worker=4"
Write-Host ""
Write-Host "📖 Full documentation: PRODUCTION_DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Your video processing API is now live and ready for production use!" -ForegroundColor Green
