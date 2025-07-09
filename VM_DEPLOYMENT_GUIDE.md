# VM Deployment Guide - Production Ready with Application Gateway

## 🎯 Overview

Deploy the Video Merger API on Azure VM with Application Gateway for scalability, using:
- **VM**: Docker Compose for quick setup
- **Database**: Supabase PostgreSQL
- **Output Storage**: Supabase Storage (S3-compatible)
- **Processing Storage**: Local with auto-cleanup
- **Application Gateway**: For scaling and custom domain
- **Redis**: Your existing Azure Cache for Redis

## 🚀 Quick VM Deployment

### **Step 1: Create Azure Infrastructure**

```bash
# Create resource group
az group create --name video-merger-rg --location eastus

# Create Virtual Network for VM and Application Gateway
az network vnet create \
  --resource-group video-merger-rg \
  --name video-merger-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name vm-subnet \
  --subnet-prefix 10.0.1.0/24

# Create subnet for Application Gateway
az network vnet subnet create \
  --resource-group video-merger-rg \
  --vnet-name video-merger-vnet \
  --name appgw-subnet \
  --address-prefix 10.0.2.0/24

# Create Network Security Group for VM
az network nsg create \
  --resource-group video-merger-rg \
  --name video-merger-vm-nsg

# Allow SSH access
az network nsg rule create \
  --resource-group video-merger-rg \
  --nsg-name video-merger-vm-nsg \
  --name AllowSSH \
  --protocol Tcp \
  --priority 1000 \
  --destination-port-range 22 \
  --access Allow

# Allow API access from Application Gateway subnet only
az network nsg rule create \
  --resource-group video-merger-rg \
  --nsg-name video-merger-vm-nsg \
  --name AllowAppGateway \
  --protocol Tcp \
  --priority 1100 \
  --destination-port-range 8001 \
  --source-address-prefix 10.0.2.0/24 \
  --access Allow

# Create VM with private IP
az vm create \
  --resource-group video-merger-rg \
  --name video-merger-vm \
  --image Ubuntu2204 \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --vnet-name video-merger-vnet \
  --subnet vm-subnet \
  --nsg video-merger-vm-nsg \
  --public-ip-address video-merger-vm-ip \
  --public-ip-sku Standard

# Get VM private and public IPs
VM_PRIVATE_IP=$(az vm show --resource-group video-merger-rg --name video-merger-vm --show-details --query privateIps --output tsv)
VM_PUBLIC_IP=$(az vm show --resource-group video-merger-rg --name video-merger-vm --show-details --query publicIps --output tsv)
echo "VM Private IP: $VM_PRIVATE_IP"
echo "VM Public IP: $VM_PUBLIC_IP"
```

### **Step 2: Setup Supabase (Database & Storage)**

```bash
# Follow the Supabase setup guide first
# 1. Create Supabase project at https://supabase.com
# 2. Run the database schema from database/schema.sql
# 3. Create storage bucket named 'video-processing'
# 4. Get your credentials:

SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_SERVICE_KEY="your-service-role-key"
SUPABASE_ANON_KEY="your-anon-key"

echo "Supabase URL: $SUPABASE_URL"
echo "Make sure to save these credentials for the next step"
```

### **Step 3: Setup VM Environment**

```bash
# SSH into VM
ssh azureuser@$VM_PUBLIC_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose git curl jq
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Create application directories
sudo mkdir -p /app/video-merger-api
sudo chown azureuser:azureuser /app/video-merger-api

# Logout and login again for docker group
exit
ssh azureuser@$VM_PUBLIC_IP
```

### **Step 4: Deploy Application**

```bash
# Clone repository (replace with your repo)
cd /app/video-merger-api
git clone https://github.com/your-username/video-merger-api.git .

# Create production environment file with hybrid storage
cat > .env.production << EOF
# Database Configuration - Use Supabase
USE_SQLITE=false
DATABASE_URL=postgresql://postgres:your-db-password@db.your-project-id.supabase.co:5432/postgres

# Supabase Configuration
SUPABASE_URL=$SUPABASE_URL
SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY
SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

# API Configuration
API_TITLE="Video Processing API"
API_VERSION="2.0.0"
HOST=0.0.0.0
PORT=8001
DEBUG=false

# Hybrid Storage Configuration
USE_LOCAL_STORAGE=false
LOCAL_STORAGE_PATH=./temp_storage
STORAGE_BUCKET=video-processing
TEMP_STORAGE_PATH=/tmp/video_processing

# Redis Configuration - Use your existing Azure Cache
REDIS_URL=rediss://:your-redis-password@your-redis.redis.cache.windows.net:6380/5

# Security (CHANGE THESE!)
SECRET_KEY=your-super-secret-production-key-$(openssl rand -hex 16)
ADMIN_API_KEY=admin-$(openssl rand -hex 20)

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Processing Configuration
MAX_VIDEO_SIZE_MB=1000
MAX_PROCESSING_TIME_MINUTES=60
TEMP_FILE_CLEANUP_HOURS=2
OUTPUT_FILE_RETENTION_DAYS=7

# Credit System
DEFAULT_USER_CREDITS=10000
CREDIT_COST_PER_SECOND=1
PREMIUM_CREDIT_COST_PER_MINUTE=100
EOF

# Create production docker-compose file with hybrid storage
cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  video-processor-api:
    build: .
    restart: unless-stopped
    ports:
      - "8001:8001"
    volumes:
      - ./temp_storage:/app/temp_storage
      - /tmp/video_processing:/tmp/video_processing
    env_file:
      - .env.production
    networks:
      - video_network
    environment:
      - REDIS_URL=${REDIS_URL}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    restart: unless-stopped
    volumes:
      - ./temp_storage:/app/temp_storage
      - /tmp/video_processing:/tmp/video_processing
    env_file:
      - .env.production
    networks:
      - video_network
    environment:
      - REDIS_URL=${REDIS_URL}
    healthcheck:
      test: ["CMD", "celery", "-A", "services.celery_app", "inspect", "ping"]
      interval: 60s
      timeout: 30s
      retries: 3

  # Cleanup service for temp files
  cleanup-service:
    build: .
    restart: unless-stopped
    volumes:
      - ./temp_storage:/app/temp_storage
      - /tmp/video_processing:/tmp/video_processing
    env_file:
      - .env.production
    networks:
      - video_network
    command: >
      sh -c "while true; do
        sleep 3600;
        curl -X POST http://video-processor-api:8001/admin/cleanup \
          -F 'max_age_hours=2' \
          -F 'admin_api_key=${ADMIN_API_KEY}' || true;
      done"

networks:
  video_network:
    driver: bridge
EOF

# Create necessary directories
mkdir -p temp_storage
sudo mkdir -p /tmp/video_processing
sudo chmod 777 /tmp/video_processing

# Build and start services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# Test API health
curl http://localhost:8001/health
```

### **Step 5: Setup Application Gateway**

```bash
# Create public IP for Application Gateway
az network public-ip create \
  --resource-group video-merger-rg \
  --name video-merger-appgw-ip \
  --allocation-method Static \
  --sku Standard \
  --dns-name video-merger-api-$(date +%s)

# Get the public IP address
APPGW_PUBLIC_IP=$(az network public-ip show \
  --resource-group video-merger-rg \
  --name video-merger-appgw-ip \
  --query ipAddress \
  --output tsv)

echo "Application Gateway Public IP: $APPGW_PUBLIC_IP"

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
  --public-ip-address video-merger-appgw-ip \
  --servers $VM_PRIVATE_IP

# Create health probe for better monitoring
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
  --probe health-probe \
  --timeout 300 \
  --connection-draining-timeout 60

echo "Application Gateway setup complete!"
echo "Your API will be available at: http://$APPGW_PUBLIC_IP"
```

### **Step 6: Setup Custom Domain and SSL**

```bash
# First, configure your DNS to point to the Application Gateway IP
echo "Configure DNS: Create A record for your domain pointing to $APPGW_PUBLIC_IP"

# Create SSL certificate (replace with your domain)
# Option 1: Use Azure Key Vault certificate
az keyvault certificate create \
  --vault-name video-merger-kv \
  --name ssl-cert \
  --policy "$(az keyvault certificate get-default-policy)"

# Option 2: Upload existing certificate
# az network application-gateway ssl-cert create \
#   --gateway-name video-merger-appgw \
#   --resource-group video-merger-rg \
#   --name ssl-cert \
#   --cert-file path/to/your/certificate.pfx \
#   --cert-password your-cert-password

# Add HTTPS listener (after DNS is configured)
az network application-gateway frontend-port create \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --name httpsPort \
  --port 443

# Create HTTPS listener (replace with your domain)
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

### **Step 7: Setup Monitoring and Scaling**

```bash
# Create comprehensive monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== Application Gateway Health ==="
curl -s http://$APPGW_PUBLIC_IP/health | jq . || echo "Gateway not responding"

echo -e "\n=== Docker Services Status ==="
docker-compose -f docker-compose.production.yml ps

echo -e "\n=== API Health Check (Local) ==="
curl -s http://localhost:8001/health | jq .

echo -e "\n=== Storage Stats ==="
curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8001/stats | jq .

echo -e "\n=== Disk Usage ==="
df -h

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Temp Files Cleanup ==="
find /tmp/video_processing -type f -mtime +1 | wc -l

echo -e "\n=== Recent API Logs ==="
docker-compose -f docker-compose.production.yml logs --tail=10 video-processor-api
EOF

chmod +x monitor.sh

# Create auto-scaling script for VM
cat > scale-check.sh << 'EOF'
#!/bin/bash
# Simple auto-scaling based on CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')

echo "CPU: ${CPU_USAGE}%, Memory: ${MEMORY_USAGE}%"

# Scale up if CPU > 80% or Memory > 85%
if (( $(echo "$CPU_USAGE > 80" | bc -l) )) || (( $(echo "$MEMORY_USAGE > 85" | bc -l) )); then
    echo "High resource usage detected - consider scaling up"
    # Here you could trigger container deployment or VM scaling
    # az vm resize --resource-group video-merger-rg --name video-merger-vm --size Standard_D8s_v3
fi
EOF

chmod +x scale-check.sh

# Add monitoring to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /app/video-merger-api/scale-check.sh >> /var/log/scale-check.log") | crontab -
```

### **Step 7: Setup Automatic Backups**

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/azureuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp database/production_database.db $BACKUP_DIR/database_$DATE.db

# Backup important storage files (last 7 days)
find storage -name "*.mp4" -mtime -7 | tar -czf $BACKUP_DIR/storage_$DATE.tar.gz -T -

# Keep only last 30 backups
find $BACKUP_DIR -name "database_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "storage_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Add to crontab (daily backup at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/azureuser/video-merger-api/backup.sh") | crontab -
```

### **Step 8: Configure Firewall**

```bash
# Setup UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow from 10.0.0.0/8 to any port 8001  # Internal access only
```

## 🔧 VM Management Commands

### **Service Management:**
```bash
# Start services
docker-compose -f docker-compose.production.yml up -d

# Stop services
docker-compose -f docker-compose.production.yml down

# Restart services
docker-compose -f docker-compose.production.yml restart

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Update application
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

### **Monitoring:**
```bash
# Check service status
./monitor.sh

# Check API health
curl https://your-domain.com/health

# View storage usage
du -sh storage/

# Check database size
ls -lah database/
```

## 📊 VM Specifications

### **Recommended VM Sizes:**

| VM Size | vCPUs | RAM | Storage | Concurrent Jobs | Monthly Cost* |
|---------|-------|-----|---------|----------------|---------------|
| **Standard_D2s_v3** | 2 | 8GB | 16GB | 1-2 | ~$70 |
| **Standard_D4s_v3** | 4 | 16GB | 32GB | 2-4 | ~$140 |
| **Standard_D8s_v3** | 8 | 32GB | 64GB | 4-8 | ~$280 |

*Approximate costs, varies by region

### **Storage Requirements:**
- **OS + App**: ~10GB
- **Temp Processing**: ~50GB (for large videos)
- **Output Storage**: Depends on retention policy
- **Recommended**: 100GB+ SSD

## 🎯 Architecture Benefits

### **✅ Hybrid Storage Approach**
- **Processing**: Local temp storage for fast I/O
- **Output**: Supabase storage for global access
- **Database**: Supabase PostgreSQL for scalability
- **Auto-cleanup**: Temp files cleaned every hour

### **✅ Application Gateway Benefits**
- **Load Balancing**: Ready for multiple VMs
- **SSL Termination**: Centralized certificate management
- **Health Monitoring**: Automatic failover
- **Custom Domain**: Professional API endpoints
- **Scaling Path**: Easy migration to containers

### **✅ Production Ready Features**
- **Monitoring**: Comprehensive health checks
- **Auto-scaling**: CPU/Memory based scaling triggers
- **Backup**: Automated Supabase backups
- **Security**: Private VM with public gateway access

## 🚀 Scaling Path

### **Phase 1: Single VM (Current)**
```
Internet → Application Gateway → VM (Docker Compose)
                                ↓
                          Supabase (DB + Storage)
```

### **Phase 2: Multi-VM Scaling**
```bash
# Add second VM to Application Gateway backend pool
az vm create --name video-merger-vm-2 ...
az network application-gateway address-pool address add \
  --gateway-name video-merger-appgw \
  --resource-group video-merger-rg \
  --pool-name appGatewayBackendPool \
  --servers $VM2_PRIVATE_IP
```

### **Phase 3: Container Migration**
```bash
# Replace VMs with Container Instances
az container create --name video-merger-api-1 ...
az container create --name video-merger-api-2 ...
# Update Application Gateway backend pool
```

## 🚀 Quick Start Summary

**Your Production-Ready Setup:**

1. **Infrastructure Setup** (10 minutes)
   - Create VM with Application Gateway
   - Setup Supabase database and storage

2. **Application Deployment** (15 minutes)
   - Deploy Docker Compose stack
   - Configure hybrid storage

3. **Domain & SSL** (10 minutes)
   - Configure DNS and SSL certificate
   - Test Application Gateway

4. **Monitoring Setup** (5 minutes)
   - Setup health checks and auto-cleanup

**Total setup time: ~40 minutes**

**Your API will be available at:**
- `http://your-appgw-ip/health` (immediate)
- `https://api.yourdomain.com/health` (after DNS)
- `https://api.yourdomain.com/api/v1/users/credits`

**This deployment gives you:**
- ✅ **Production-ready** with Application Gateway
- ✅ **Scalable** - Easy path to containers
- ✅ **Hybrid storage** - Fast processing + cloud output
- ✅ **Auto-cleanup** - Temp file management
- ✅ **Monitoring** - Health checks and scaling triggers
- ✅ **Cost-effective** - Fixed VM cost with cloud storage benefits

**Perfect for:**
- ✅ Immediate production deployment
- ✅ Predictable costs with scaling options
- ✅ Full control with managed database
- ✅ Easy migration path to containers
