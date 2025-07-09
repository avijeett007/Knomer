# 🚀 Postman Testing Guide - Video Processing API

## 📦 What's Included

This package contains everything you need to test your Video Processing API manually using Postman:

### Files:
- **`Video_Processing_API.postman_collection.json`** - Complete API collection
- **`Video_Processing_API_Local.postman_environment.json`** - Local testing environment
- **`Video_Processing_API_Production.postman_environment.json`** - Production environment template

## 🔧 Setup Instructions

### Step 1: Import Collection and Environment

1. **Open Postman**
2. **Import Collection:**
   - Click "Import" button
   - Select `Video_Processing_API.postman_collection.json`
   - Click "Import"

3. **Import Environment:**
   - Click "Import" button  
   - Select `Video_Processing_API_Local.postman_environment.json`
   - Click "Import"

4. **Select Environment:**
   - Click the environment dropdown (top right)
   - Select "Video Processing API - Local Environment"

### Step 2: Update API Key

1. **Get Current API Key:**
   ```bash
   # From your running containers
   docker-compose -f docker-compose.local.yml logs video-processor-api | grep "Test API key"
   ```

2. **Update Environment:**
   - Click the environment dropdown
   - Click "Edit" (eye icon)
   - Update the `api_key` value with your current API key
   - Save changes

## 📋 Collection Structure

### 🏥 **Health & Status**
- **Root Health Check** - Basic API availability
- **Detailed Health Check** - Service status and dependencies
- **System Statistics** - Performance metrics (requires authentication)

### 💳 **Credit Management**
- **Get User Credits** - Check available credits
- **Estimate Credits - Simple Merge** - Cost estimation for basic jobs
- **Estimate Credits - Auto Effects** - Cost estimation for advanced jobs

### 🎬 **Job Management**
- **Create Simple Merge Job** - Basic video merging
- **Create Auto Effects Job** - AI-powered video processing
- **Create Logo Overlay Job** - Watermarking functionality
- **Create TikTok Conversion Job** - 16:9 to 9:16 conversion

### 📊 **Job Status & Monitoring**
- **Get Job Status** - Check individual job progress
- **Get Auto Effects Job Status** - Monitor AI processing jobs
- **List All User Jobs** - Paginated job history
- **List Recent Jobs** - Quick recent activity view

## 🎯 Testing Workflow

### Basic Testing Flow:

1. **Health Check**
   ```
   GET /health
   ```
   ✅ Verify API is running and all services are healthy

2. **Check Credits**
   ```
   GET /credits
   ```
   ✅ Confirm you have sufficient credits for testing

3. **Estimate Job Cost**
   ```
   POST /credits/estimate
   ```
   ✅ Get cost estimate before creating jobs

4. **Create Job**
   ```
   POST /jobs
   ```
   ✅ Submit video processing job (saves job_id automatically)

5. **Monitor Progress**
   ```
   GET /jobs/{job_id}
   ```
   ✅ Check job status and progress

6. **List Jobs**
   ```
   GET /jobs
   ```
   ✅ View all your jobs with pagination

### Advanced Testing Scenarios:

#### **Scenario 1: Simple Video Merge**
1. Run "Estimate Credits - Simple Merge"
2. Run "Create Simple Merge Job"
3. Run "Get Job Status" (repeat until completed)
4. Check output file URL in response

#### **Scenario 2: AI-Powered Processing**
1. Run "Estimate Credits - Auto Effects"
2. Run "Create Auto Effects Job"
3. Run "Get Auto Effects Job Status"
4. Verify transcription and AI effects applied

#### **Scenario 3: Logo Watermarking**
1. Run "Create Logo Overlay Job"
2. Monitor with "Get Job Status"
3. Verify logo overlay in output

#### **Scenario 4: TikTok Conversion**
1. Run "Create TikTok Conversion Job"
2. Monitor progress
3. Verify 9:16 aspect ratio output

## 🔍 Expected Responses

### Successful Health Check:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-21T00:59:36.041138",
  "version": "2.0.0",
  "services": {
    "database": true,
    "redis": true,
    "storage": true,
    "ffmpeg": true
  }
}
```

### Credit Information:
```json
{
  "total_credits": 10000,
  "used_credits": 0,
  "remaining_credits": 10000,
  "last_updated": "2025-06-21T00:58:59"
}
```

### Job Creation Response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "simple_merge",
  "status": "pending",
  "estimated_credits": 35,
  "created_at": "2025-06-21T01:00:00Z"
}
```

### Job Status Response:
```json
{
  "job": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "output_file_url": "https://storage.example.com/output.mp4",
    "actual_credits_used": 32,
    "completed_at": "2025-06-21T01:02:30Z"
  },
  "progress_percentage": 100
}
```

## 🚨 Common Issues & Solutions

### Issue: "Invalid API Key"
**Solution:** 
1. Get fresh API key from container logs
2. Update environment variable
3. Ensure Bearer token format: `Bearer vp_your_key_here`

### Issue: "Insufficient Credits"
**Solution:**
1. Check credits with `GET /credits`
2. Use smaller videos or shorter durations
3. Check credit estimation first

### Issue: Job Stuck in "Processing"
**Solution:**
1. Check container logs: `docker-compose logs celery-worker`
2. Verify video URLs are accessible
3. Check file size limits

### Issue: "Service Unavailable"
**Solution:**
1. Run health check first
2. Restart containers if needed
3. Check Docker container status

## 🔄 Environment Switching

### For Production Testing:
1. Import `Video_Processing_API_Production.postman_environment.json`
2. Update `base_url` to your production domain
3. Update `api_key` with production API key
4. Switch environment in Postman

### Environment Variables:
- **`base_url`** - API endpoint (local: http://localhost:8001)
- **`api_key`** - Authentication token
- **`job_id`** - Auto-saved from job creation
- **`auto_effects_job_id`** - Auto-saved for AI jobs
- **`logo_job_id`** - Auto-saved for logo jobs
- **`tiktok_job_id`** - Auto-saved for TikTok jobs

## 📊 Performance Testing

### Load Testing with Postman:
1. Use Collection Runner
2. Set iterations (e.g., 10 jobs)
3. Add delays between requests
4. Monitor system resources

### Metrics to Monitor:
- **Response Time** - Should be < 5 seconds
- **Success Rate** - Should be 100%
- **Credit Consumption** - Should match estimates
- **Job Completion Time** - Varies by video size

## 🎉 Success Criteria

### ✅ All Tests Passing:
- Health checks return "healthy"
- Credit operations work correctly
- Jobs are created successfully
- Job status updates properly
- Output files are generated
- All endpoints respond within 5 seconds

### 🚀 Ready for Production:
- All Postman tests pass
- No authentication errors
- Proper error handling
- Consistent response times
- Credit system working
- File cleanup functioning

## 💡 Pro Tips

1. **Use Test Scripts:** Collection includes automatic job ID saving
2. **Monitor Logs:** Keep container logs open during testing
3. **Test Edge Cases:** Try invalid inputs, large files, etc.
4. **Performance Testing:** Use Collection Runner for load testing
5. **Environment Management:** Keep separate environments for dev/prod

**🎬 Your API is now ready for comprehensive manual testing with Postman!**
