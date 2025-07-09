# Video Processing API v2.0

A comprehensive, production-ready video processing API with async job processing, credit system, and advanced video manipulation features.

## 🚀 Features

### Core Features
- **Async Video Processing**: Redis + Celery-based job queue system
- **Credit System**: Pay-per-use model with different tiers
- **Multi-Video Support**: Process multiple videos in sequence
- **API Key Authentication**: Secure API access with rate limiting
- **Supabase Integration**: Database and storage using Supabase

### Video Processing Capabilities
- **Simple Merge**: Basic video concatenation (Free tier)
- **Transition Effects**: Fade, dissolve, slide, zoom, custom transitions
- **Auto Effects**: AI-powered effects based on content analysis
- **Logo Overlays**: Dynamic logo placement with customizable positioning
- **Multi-Video Processing**: Handle up to 10 videos per job
- **Quality Presets**: Fast, balanced, or quality processing modes

### Advanced Features (Planned)
- **AI Transcription**: Whisper-based audio transcription
- **Smart Effects**: Auto zoom, blur, motion crop based on transcript
- **Platform Optimization**: Auto-resize for TikTok, Instagram, YouTube
- **Custom Transitions**: User-provided transition clips

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Celery Worker │    │   Supabase DB   │
│   (API Layer)   │◄──►│  (Processing)   │◄──►│   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Queue   │    │   FFmpeg Core   │    │ Supabase Storage│
│   (Job Queue)   │    │  (Video Proc)   │    │  (File Storage) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
video-merger-api/
├── api/
│   └── main.py                 # FastAPI application
├── config/
│   └── settings.py            # Configuration management
├── database/
│   └── schema.sql             # Database schema
├── models/
│   └── schemas.py             # Pydantic models
├── services/
│   ├── auth.py                # Authentication service
│   ├── credit_manager.py      # Credit management
│   ├── database.py            # Database operations
│   └── storage.py             # File storage service
├── tasks/
│   ├── cleanup.py             # Cleanup tasks
│   └── video_processing.py    # Video processing tasks
├── celery_app.py              # Celery configuration
├── docker-compose.yml         # Multi-service setup
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
└── .env.example              # Environment template
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd video-merger-api
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 2. Setup Supabase
1. Create a new Supabase project
2. Run the SQL schema from `database/schema.sql`
3. Create a storage bucket named "video-processing"
4. Update `.env` with your Supabase credentials

### 3. Run with Docker
```bash
docker compose up -d --build
```

This starts:
- **API Server**: http://localhost:8000
- **Redis**: localhost:6379
- **Celery Worker**: Background processing
- **Celery Beat**: Scheduled tasks
- **Flower**: http://localhost:5555 (Celery monitoring)

### 4. Create Your First API Key
```bash
# Use the API to create a user and API key
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "name": "Your Name"}'

curl -X POST "http://localhost:8000/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Key"}'
```

## 📚 API Documentation

### Authentication
All API calls require an API key in the Authorization header:
```bash
Authorization: Bearer vp_your_api_key_here
```

### Core Endpoints

#### Job Management
- `POST /jobs` - Create a new video processing job
- `GET /jobs/{job_id}` - Get job status and details
- `GET /jobs` - List user's jobs with pagination

#### Credit Management
- `GET /credits` - Get user's credit balance
- `POST /credits/estimate` - Estimate credits for a job

#### System
- `GET /health` - Health check
- `GET /stats` - System statistics

### Example: Create a Simple Merge Job
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Authorization: Bearer vp_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "simple_merge",
    "videos": [
      {"url": "https://example.com/video1.mp4", "order_index": 0},
      {"url": "https://example.com/video2.mp4", "order_index": 1}
    ],
    "processing_options": {
      "platform": "youtube",
      "quality_preset": "balanced"
    }
  }'
```

## 💳 Credit System

### Credit Costs
- **Simple Merge**: Free (0 credits)
- **Transition Effects**: 1-3 credits per transition
- **Auto Effects**: 5 base + 2 per 10 seconds
- **Logo Overlay**: 2 base + 1 per 10 seconds
- **Transcription**: 1 credit per minute

### Free Tier
- 100 credits on signup
- Simple merge operations are free
- Perfect for testing and basic use

## 🔧 Configuration

### Environment Variables
See `.env.example` for all configuration options.

Key settings:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Service role key for database access
- `REDIS_URL`: Redis connection string
- `FREE_TIER_CREDITS`: Credits given to new users

### Rate Limiting
Default limits per API key:
- 10 requests per minute
- 100 requests per hour
- 1000 requests per day

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Start Celery worker
celery -A celery_app worker --loglevel=info

# Start API server
uvicorn api.main:app --reload
```

### Running Tests
```bash
pytest tests/
```

## 📈 Monitoring

### Celery Monitoring
Access Flower at http://localhost:5555 to monitor:
- Active tasks
- Worker status
- Task history
- Queue lengths

### Health Checks
- API: `GET /health`
- Individual services health status
- Database connectivity
- Redis connectivity

## 🚀 Deployment

### Production Considerations
1. **Environment Variables**: Set secure values for all secrets
2. **Database**: Use Supabase production instance
3. **Redis**: Use managed Redis service
4. **Storage**: Configure Supabase storage with proper policies
5. **Monitoring**: Set up logging and monitoring
6. **Rate Limiting**: Adjust based on your needs

### RapidAPI Integration
The API is designed to be compatible with RapidAPI marketplace:
- Standard REST endpoints
- API key authentication
- Rate limiting
- Comprehensive documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license here]

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the health check endpoint at `/health`
