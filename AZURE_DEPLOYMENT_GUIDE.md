# Azure Container Services Deployment Guide

## 🎯 Architecture Overview

**Deployment Strategy:**
- ✅ **Main API**: Azure Container Instances (ACI) behind Application Gateway
- ✅ **Redis**: Use existing Azure Cache for Redis (isolated namespace)
- ✅ **Celery Worker**: Separate ACI (internal, no public access)
- ✅ **Database**: Supabase (external) or Azure Database for PostgreSQL
- ✅ **Storage**: Supabase Storage or Azure Blob Storage
- ✅ **Domain**: Custom domain through Application Gateway

## 🔧 Prerequisites

- Azure CLI installed and logged in
- Docker images built and pushed to Azure Container Registry
- Existing Azure Cache for Redis
- Supabase project setup (or Azure Database)

## 📋 Step 1: Setup Azure Container Registry

```bash
# Create resource group
az group create --name video-merger-rg --location eastus

# Create Azure Container Registry
az acr create --resource-group video-merger-rg \
  --name videomergeracr \
  --sku Basic \
  --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name videomergeracr --query loginServer --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Login to ACR
az acr login --name videomergeracr
```

## 🐳 Step 2: Build and Push Docker Images

```bash
# Build and tag the main API image
docker build -t $ACR_LOGIN_SERVER/video-merger-api:latest .

# Build Celery worker image (create separate Dockerfile.worker)
docker build -f Dockerfile.worker -t $ACR_LOGIN_SERVER/video-merger-worker:latest .

# Push images to ACR
docker push $ACR_LOGIN_SERVER/video-merger-api:latest
docker push $ACR_LOGIN_SERVER/video-merger-worker:latest
```

## 🔑 Step 3: Create Azure Key Vault for Secrets

```bash
# Create Key Vault
az keyvault create --name video-merger-kv \
  --resource-group video-merger-rg \
  --location eastus

# Add secrets
az keyvault secret set --vault-name video-merger-kv \
  --name "supabase-url" --value "https://your-project.supabase.co"

az keyvault secret set --vault-name video-merger-kv \
  --name "supabase-service-key" --value "your-service-key"

az keyvault secret set --vault-name video-merger-kv \
  --name "openai-api-key" --value "your-openai-key"

az keyvault secret set --vault-name video-merger-kv \
  --name "admin-api-key" --value "your-admin-secret-key"

az keyvault secret set --vault-name video-merger-kv \
  --name "redis-connection-string" --value "your-redis-connection-string"
```

## 🌐 Step 4: Create Virtual Network

```bash
# Create VNet for container communication
az network vnet create \
  --resource-group video-merger-rg \
  --name video-merger-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name container-subnet \
  --subnet-prefix 10.0.1.0/24

# Create subnet for Application Gateway
az network vnet subnet create \
  --resource-group video-merger-rg \
  --vnet-name video-merger-vnet \
  --name appgw-subnet \
  --address-prefix 10.0.2.0/24
```

## 📦 Step 5: Deploy Main API Container

```bash
# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name videomergeracr --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name videomergeracr --query passwords[0].value --output tsv)

# Create main API container
az container create \
  --resource-group video-merger-rg \
  --name video-merger-api \
  --image $ACR_LOGIN_SERVER/video-merger-api:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --dns-name-label video-merger-api-$(date +%s) \
  --ports 8001 \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    USE_SQLITE=false \
    USE_LOCAL_STORAGE=false \
    HOST=0.0.0.0 \
    PORT=8001 \
    DEBUG=false \
  --secure-environment-variables \
    SUPABASE_URL="$(az keyvault secret show --vault-name video-merger-kv --name supabase-url --query value -o tsv)" \
    SUPABASE_SERVICE_KEY="$(az keyvault secret show --vault-name video-merger-kv --name supabase-service-key --query value -o tsv)" \
    OPENAI_API_KEY="$(az keyvault secret show --vault-name video-merger-kv --name openai-api-key --query value -o tsv)" \
    ADMIN_API_KEY="$(az keyvault secret show --vault-name video-merger-kv --name admin-api-key --query value -o tsv)" \
    REDIS_URL="$(az keyvault secret show --vault-name video-merger-kv --name redis-connection-string --query value -o tsv)"
```

## 🔄 Step 6: Deploy Celery Worker Container

```bash
# Create Celery worker container (no public IP)
az container create \
  --resource-group video-merger-rg \
  --name video-merger-worker \
  --image $ACR_LOGIN_SERVER/video-merger-worker:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --cpu 2 \
  --memory 4 \
  --restart-policy Always \
  --environment-variables \
    USE_SQLITE=false \
    USE_LOCAL_STORAGE=false \
    WORKER_MODE=true \
  --secure-environment-variables \
    SUPABASE_URL="$(az keyvault secret show --vault-name video-merger-kv --name supabase-url --query value -o tsv)" \
    SUPABASE_SERVICE_KEY="$(az keyvault secret show --vault-name video-merger-kv --name supabase-service-key --query value -o tsv)" \
    REDIS_URL="$(az keyvault secret show --vault-name video-merger-kv --name redis-connection-string --query value -o tsv)"
```

## 🌐 Step 7: Create Application Gateway

```bash
# Create public IP for Application Gateway
az network public-ip create \
  --resource-group video-merger-rg \
  --name appgw-public-ip \
  --allocation-method Static \
  --sku Standard

# Get container IP
CONTAINER_IP=$(az container show --resource-group video-merger-rg --name video-merger-api --query ipAddress.ip --output tsv)

# Create Application Gateway
az network application-gateway create \
  --name video-merger-appgw \
  --location eastus \
  --resource-group video-merger-rg \
  --vnet-name video-merger-vnet \
  --subnet appgw-subnet \
  --capacity 1 \
  --sku Standard_v2 \
  --http-settings-cookie-based-affinity Disabled \
  --frontend-port 80 \
  --http-settings-port 8001 \
  --http-settings-protocol Http \
  --public-ip-address appgw-public-ip \
  --servers $CONTAINER_IP
```

## 🔒 Step 8: Configure HTTPS and Custom Domain

```bash
# Create SSL certificate (replace with your domain)
az network application-gateway ssl-cert create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name ssl-cert \
  --cert-file path/to/your/certificate.pfx \
  --cert-password your-cert-password

# Add HTTPS listener
az network application-gateway frontend-port create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name httpsPort \
  --port 443

az network application-gateway http-listener create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name httpsListener \
  --frontend-port httpsPort \
  --ssl-cert ssl-cert \
  --host-name api.yourdomain.com

# Create HTTPS rule
az network application-gateway rule create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name httpsRule \
  --http-listener httpsListener \
  --rule-type Basic \
  --address-pool appGatewayBackendPool \
  --http-settings appGatewayBackendHttpSettings
```

## 📊 Step 9: Configure Health Probes

```bash
# Create health probe
az network application-gateway probe create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name health-probe \
  --protocol Http \
  --host-name-from-http-settings true \
  --path /health \
  --interval 30 \
  --timeout 30 \
  --threshold 3

# Update backend HTTP settings to use health probe
az network application-gateway http-settings update \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name appGatewayBackendHttpSettings \
  --probe health-probe
```

## 🔄 Step 10: Setup Auto-scaling (Optional)

```bash
# Create Container Group with auto-scaling
az container create \
  --resource-group video-merger-rg \
  --name video-merger-api-scaled \
  --image $ACR_LOGIN_SERVER/video-merger-api:latest \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always \
  --environment-variables \
    SCALE_MODE=true
```

## 📋 Step 11: DNS Configuration

1. **Get Application Gateway Public IP:**
```bash
az network public-ip show \
  --resource-group video-merger-rg \
  --name appgw-public-ip \
  --query ipAddress \
  --output tsv
```

2. **Configure DNS:**
   - Go to your domain registrar
   - Create A record: `api.yourdomain.com` → Application Gateway IP
   - Or create CNAME: `api.yourdomain.com` → Application Gateway FQDN

## 🔍 Step 12: Monitoring and Logging

```bash
# Enable Application Insights
az monitor app-insights component create \
  --app video-merger-insights \
  --location eastus \
  --resource-group video-merger-rg

# Get instrumentation key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app video-merger-insights \
  --resource-group video-merger-rg \
  --query instrumentationKey \
  --output tsv)

# Update container with Application Insights
az container update \
  --resource-group video-merger-rg \
  --name video-merger-api \
  --set environmentVariables[0].name=APPINSIGHTS_INSTRUMENTATIONKEY \
  --set environmentVariables[0].value=$INSIGHTS_KEY
```

## 🔴 Step 13: Redis Configuration (Using Existing Azure Cache)

### Option A: Use Existing Redis (Recommended)

```bash
# Get your existing Redis connection string
# Replace with your actual Redis details
REDIS_HOST="your-existing-redis.redis.cache.windows.net"
REDIS_PORT="6380"
REDIS_PASSWORD="your-redis-password"

# Create isolated database for video processing
# Use database 5 (or any unused database number)
REDIS_URL="rediss://:$REDIS_PASSWORD@$REDIS_HOST:$REDIS_PORT/5"

# Update Key Vault with Redis connection
az keyvault secret set --vault-name video-merger-kv \
  --name "redis-connection-string" \
  --value "$REDIS_URL"
```

### Option B: Deploy Separate Redis Container

```bash
# Only if you want separate Redis instance
az container create \
  --resource-group video-merger-rg \
  --name video-merger-redis \
  --image redis:7-alpine \
  --cpu 1 \
  --memory 2 \
  --ports 6379 \
  --environment-variables \
    REDIS_PASSWORD=your-redis-password \
  --command-line "redis-server --requirepass your-redis-password"
```

## 🔄 Step 14: Create Dockerfile.worker

Create `Dockerfile.worker` for Celery worker:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory
RUN mkdir -p /tmp/video_processing

# Run Celery worker
CMD ["celery", "-A", "services.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```

## 🚀 Step 15: Deployment Verification

```bash
# Check container status
az container show --resource-group video-merger-rg --name video-merger-api --query instanceView.state
az container show --resource-group video-merger-rg --name video-merger-worker --query instanceView.state

# Check Application Gateway status
az network application-gateway show --resource-group video-merger-rg --name video-merger-appgw --query operationalState

# Test API endpoint
curl -X GET "https://api.yourdomain.com/health"

# Test with API key
curl -X GET "https://api.yourdomain.com/api/v1/users/credits" \
  -H "Authorization: Bearer your-api-key"
```

## 📊 Step 16: Scaling and Performance

```bash
# Scale API container
az container update \
  --resource-group video-merger-rg \
  --name video-merger-api \
  --cpu 4 \
  --memory 8

# Scale worker container
az container update \
  --resource-group video-merger-rg \
  --name video-merger-worker \
  --cpu 4 \
  --memory 8

# Scale Application Gateway
az network application-gateway update \
  --resource-group video-merger-rg \
  --name video-merger-appgw \
  --capacity 2
```

## 🔒 Step 17: Security Hardening

```bash
# Create Network Security Group
az network nsg create \
  --resource-group video-merger-rg \
  --name video-merger-nsg

# Allow HTTPS traffic
az network nsg rule create \
  --resource-group video-merger-rg \
  --nsg-name video-merger-nsg \
  --name AllowHTTPS \
  --protocol Tcp \
  --priority 1000 \
  --destination-port-range 443 \
  --access Allow

# Block direct container access
az network nsg rule create \
  --resource-group video-merger-rg \
  --nsg-name video-merger-nsg \
  --name BlockDirectAccess \
  --protocol Tcp \
  --priority 2000 \
  --destination-port-range 8001 \
  --access Deny
```

## 💰 Step 18: Cost Optimization

```bash
# Use Azure Container Instances with lower specs for development
az container create \
  --resource-group video-merger-rg \
  --name video-merger-api-dev \
  --image $ACR_LOGIN_SERVER/video-merger-api:latest \
  --cpu 0.5 \
  --memory 1 \
  --restart-policy OnFailure

# Set up auto-shutdown for development environments
az container update \
  --resource-group video-merger-rg \
  --name video-merger-api-dev \
  --restart-policy Never
```

## 🎯 Final Configuration Summary

**Your deployment will have:**

✅ **Main API**: `https://api.yourdomain.com` (via Application Gateway)
✅ **Health Check**: `https://api.yourdomain.com/health`
✅ **Redis**: Isolated database in existing Azure Cache
✅ **Worker**: Background processing (no public access)
✅ **Database**: Supabase PostgreSQL
✅ **Storage**: Supabase Storage
✅ **Monitoring**: Application Insights
✅ **Security**: HTTPS, NSG rules, Key Vault secrets

## 🔧 Environment Variables Summary

```bash
# Production environment variables
USE_SQLITE=false
USE_LOCAL_STORAGE=false
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
REDIS_URL=rediss://:password@redis.cache.windows.net:6380/5
OPENAI_API_KEY=your-openai-key
ADMIN_API_KEY=your-admin-secret
HOST=0.0.0.0
PORT=8001
DEBUG=false
```

Your Video Merger API is now production-ready on Azure! 🚀
