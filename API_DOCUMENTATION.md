# Video Merger API Documentation

## 🚀 Production-Ready Video Processing API

### Base URL
```
http://localhost:8000
```

### Authentication
All protected endpoints require Bearer token authentication:
```
Authorization: Bearer vp_h9DjlkglFgR3Ai8z1vjmHzjTosafcT1Xpp0mdZIv518
```

## 📋 API Endpoints

### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-21T00:59:36.041138"
}
```

### 2. Get Credits
```http
GET /credits
Authorization: Bearer {api_key}
```
**Response:**
```json
{
  "total_credits": 10000,
  "used_credits": 0,
  "remaining_credits": 10000,
  "last_updated": "2025-06-21T00:58:59"
}
```

### 3. Estimate Credits
```http
POST /credits/estimate
Authorization: Bearer {api_key}
Content-Type: application/json
```
**Request Body:**
```json
{
  "job_type": "simple_merge",
  "videos": [
    {"url": "https://example.com/video1.mp4", "duration": 15.0},
    {"url": "https://example.com/video2.mp4", "duration": 15.0}
  ],
  "processing_options": {
    "quality_preset": "balanced"
  }
}
```
**Response:**
```json
{
  "estimated_credits": 2,
  "total_duration_seconds": 30.0
}
```

### 4. Create Job
```http
POST /jobs
Authorization: Bearer {api_key}
Content-Type: application/json
```
**Request Body:**
```json
{
  "job_type": "simple_merge",
  "videos": [
    {"url": "https://example.com/video1.mp4", "duration": 15.0, "order_index": 0},
    {"url": "https://example.com/video2.mp4", "duration": 15.0, "order_index": 1}
  ],
  "processing_options": {
    "quality_preset": "balanced",
    "transitions": [{"type": "fade", "duration": 1.0}]
  }
}
```
**Response:**
```json
{
  "id": "05997952-f814-44f7-b5a9-41e36a45a356",
  "job_type": "simple_merge",
  "status": "pending",
  "estimated_credits": 2,
  "created_at": "2025-06-21T00:59:36.041138"
}
```

### 5. Get Job Status
```http
GET /jobs/{job_id}
Authorization: Bearer {api_key}
```
**Response:**
```json
{
  "job": {
    "id": "05997952-f814-44f7-b5a9-41e36a45a356",
    "status": "pending",
    "job_type": "simple_merge"
  },
  "progress_percentage": null
}
```

### 6. List User Jobs
```http
GET /jobs
Authorization: Bearer {api_key}
```
**Response:**
```json
{
  "jobs": [
    {
      "id": "05997952-f814-44f7-b5a9-41e36a45a356",
      "job_type": "simple_merge",
      "status": "pending",
      "estimated_credits": 2,
      "created_at": "2025-06-21T00:59:36.041138"
    }
  ],
  "total": 1
}
```

## 🎬 Job Types

### Simple Merge
- **Type:** `simple_merge`
- **Cost:** ~2 credits for 30 seconds
- **Features:** Basic video concatenation with transitions

### Auto Effects
- **Type:** `auto_effects`
- **Cost:** ~35 credits for 60 seconds with transcription
- **Features:** AI-powered effects based on transcript analysis

## ⚙️ Processing Options

### Quality Presets
- `balanced` - Good quality/speed balance
- `high` - Maximum quality
- `low` - Fastest processing

### Transitions
- `fade` - Fade in/out between videos
- `crossfade` - Smooth crossfade
- `cut` - Direct cut (no transition)

## 💰 Credit System

- **10 seconds = 1 credit** (base rate)
- **Transcription:** +20 credits per video
- **Auto-effects:** +15 credits per video
- **Free tier:** 100 credits
- **Test account:** 10,000 credits

## 🚀 Getting Started

1. **Start the API:**
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

2. **Test the API:**
   ```bash
   python test_live_api.py
   ```

3. **Use the API key:**
   ```
   vp_h9DjlkglFgR3Ai8z1vjmHzjTosafcT1Xpp0mdZIv518
   ```

## 🔧 Development

- **Database:** SQLite (local testing)
- **Queue:** Redis + Celery
- **Storage:** Local filesystem (configurable for S3/Supabase)
- **Processing:** FFmpeg-based video processing

## 📊 Status Codes

- `200` - Success
- `401` - Authentication failed
- `403` - Insufficient credits
- `404` - Resource not found
- `422` - Validation error
- `500` - Server error

Your API is now production-ready! 🎉
