# Storage Configuration Guide for Containers

## 🎯 Storage Options Available

The Video Merger API **already supports multiple storage backends**:

✅ **Supabase Storage** (S3-compatible)
✅ **Azure Blob Storage** (via Azure SDK)
✅ **Local Storage** (for development/VM)
✅ **Any S3-compatible storage** (MinIO, DigitalOcean Spaces, etc.)

## 🗂️ How Container Storage Works

### **Container Processing Flow:**
1. **Input**: Files uploaded via API → Temporary container storage
2. **Processing**: FFmpeg processes files in container `/tmp/video_processing`
3. **Output**: Processed files → Persistent storage (Supabase/Azure/S3)
4. **Download**: Users download from persistent storage URLs
5. **Cleanup**: Temporary files deleted after processing

### **Storage Architecture:**
```
User Upload → Container Temp → FFmpeg Processing → Persistent Storage → Download URL
     ↓              ↓                ↓                    ↓              ↓
   API Endpoint   /tmp/video    Container Memory    Supabase/Azure    Public URL
```

## ☁️ Option 1: Supabase Storage (Recommended)

**✅ Pros:**
- S3-compatible API
- Built-in CDN for fast downloads
- Automatic scaling
- Integrated with database
- Free tier: 1GB storage + 2GB bandwidth

### **Configuration:**
```bash
# .env configuration
USE_LOCAL_STORAGE=false
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
STORAGE_BUCKET=video-processing
```

### **Setup Steps:**
1. **Create Supabase project** (if not done)
2. **Go to Storage** in Supabase dashboard
3. **Create bucket** named `video-processing`
4. **Set bucket as public** for downloads
5. **Configure CORS** for your domain

### **Bucket Policies:**
```sql
-- Allow authenticated uploads
CREATE POLICY "Allow authenticated uploads" ON storage.objects
FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow public downloads
CREATE POLICY "Allow public downloads" ON storage.objects
FOR SELECT USING (bucket_id = 'video-processing');
```

## 🔵 Option 2: Azure Blob Storage

**✅ Pros:**
- Native Azure integration
- Excellent performance in Azure regions
- Hot/Cool/Archive tiers for cost optimization
- Built-in CDN with Azure Front Door

### **Setup Azure Blob Storage:**
```bash
# Create storage account
az storage account create \
  --name videomergerstore \
  --resource-group video-merger-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Create container
az storage container create \
  --name video-processing \
  --account-name videomergerstore \
  --public-access blob

# Get connection string
az storage account show-connection-string \
  --name videomergerstore \
  --resource-group video-merger-rg
```

### **Configuration:**
```bash
# .env configuration
USE_LOCAL_STORAGE=false
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=videomergerstore;AccountKey=..."
STORAGE_BUCKET=video-processing
```

### **Add Azure Storage Support:**
```python
# Add to requirements.txt
azure-storage-blob==12.19.0

# services/storage_azure.py
from azure.storage.blob import BlobServiceClient

class AzureStorageService:
    def __init__(self):
        self.blob_service = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = settings.STORAGE_BUCKET
```

## 🏠 Option 3: Local Storage (VM Deployment)

**✅ Pros:**
- Simple setup with docker-compose
- No external dependencies
- Full control over storage
- Good for development/testing

### **VM Deployment with Docker Compose:**
```bash
# Create VM
az vm create \
  --resource-group video-merger-rg \
  --name video-merger-vm \
  --image Ubuntu2204 \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard

# Install Docker on VM
ssh azureuser@vm-ip
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Clone and run
git clone your-repo
cd video-merger-api
docker-compose up -d
```

### **VM Storage Configuration:**
```bash
# .env for VM
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=/app/storage
USE_SQLITE=true
```

## 📊 Storage Comparison

| Feature | Supabase Storage | Azure Blob | Local (VM) |
|---------|------------------|------------|------------|
| **Setup Complexity** | ⭐⭐ Easy | ⭐⭐⭐ Medium | ⭐ Very Easy |
| **Scalability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐ Limited |
| **Cost (1TB)** | ~$25/month | ~$20/month | VM cost only |
| **CDN** | ✅ Built-in | ✅ Azure CDN | ❌ None |
| **Backup** | ✅ Automatic | ✅ Geo-redundant | ❌ Manual |
| **Container Support** | ✅ Perfect | ✅ Perfect | ✅ Good |

## 🚀 Recommended Deployment Strategies

### **Strategy 1: Container + Supabase (Recommended)**
```yaml
# Azure Container Instances + Supabase Storage
Services:
  - API: Azure Container Instances
  - Worker: Azure Container Instances  
  - Database: Supabase PostgreSQL
  - Storage: Supabase Storage
  - Redis: Azure Cache for Redis
```

**Benefits:**
- ✅ Fully managed storage
- ✅ Global CDN
- ✅ Automatic scaling
- ✅ Cost-effective

### **Strategy 2: Container + Azure Blob**
```yaml
# Full Azure Stack
Services:
  - API: Azure Container Instances
  - Worker: Azure Container Instances
  - Database: Azure Database for PostgreSQL
  - Storage: Azure Blob Storage
  - Redis: Azure Cache for Redis
```

**Benefits:**
- ✅ Single cloud provider
- ✅ Native integration
- ✅ Enterprise features

### **Strategy 3: VM + Docker Compose (Quick Setup)**
```yaml
# Single VM deployment
Services:
  - All services on one VM
  - Local storage
  - SQLite database
  - Local Redis
```

**Benefits:**
- ✅ Fastest setup
- ✅ Full control
- ✅ Cost-effective for small scale

## 🔧 Container Storage Implementation

### **How Files Are Handled:**

1. **Upload Processing:**
```python
# User uploads file → Saved to container temp
temp_file = /tmp/video_processing/upload_123.mp4

# FFmpeg processes in container
ffmpeg -i temp_file -o output_file

# Upload to persistent storage
storage_url = storage_service.upload_to_storage(output_file, "jobs/123/output.mp4")

# Return download URL to user
return {"output_url": storage_url}
```

2. **Container Volumes:**
```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - temp_storage:/tmp/video_processing
      - ./storage:/app/storage  # For local storage mode
```

3. **Environment Variables:**
```bash
# Container environment
TEMP_STORAGE_PATH=/tmp/video_processing
USE_LOCAL_STORAGE=false  # Use cloud storage
SUPABASE_URL=https://your-project.supabase.co
```

## 💡 Recommendation

**For your use case, I recommend:**

### **🎯 Container Deployment + Supabase Storage**

**Why:**
1. **Containers handle processing** - No storage persistence needed
2. **Supabase handles files** - S3-compatible, CDN, automatic scaling
3. **Cost-effective** - Pay only for what you use
4. **Easy setup** - Minimal configuration required
5. **Production-ready** - Handles traffic spikes automatically

### **Quick Setup Commands:**
```bash
# 1. Deploy containers (from Azure guide)
az container create --name video-merger-api ...

# 2. Configure Supabase storage
SUPABASE_URL=https://your-project.supabase.co
USE_LOCAL_STORAGE=false

# 3. Done! Files automatically stored in Supabase
```

**vs VM Approach:**
- **Containers**: Auto-scaling, managed infrastructure, pay-per-use
- **VM**: Fixed costs, manual scaling, more maintenance

**The container approach with Supabase storage gives you the best of both worlds: simple deployment with enterprise-grade storage!** 🚀
