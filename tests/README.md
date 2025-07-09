# Video Processing API - Test Suite

This directory contains comprehensive tests for the Video Processing API, covering all functionality from basic video merging to advanced AI-powered features.

## 🧪 Test Structure

### Test Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_e2e_video_processing.py`** - End-to-end tests for complete workflows
- **`test_credit_system.py`** - Tests for credit management and calculations
- **`test_api_endpoints.py`** - Tests for API endpoints and authentication
- **`test_video_features.py`** - Tests for video processing features
- **`test_performance.py`** - Performance and load tests
- **`run_tests.py`** - Test runner script

### Test Categories

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Service integration testing
3. **End-to-End Tests** - Complete workflow testing
4. **Performance Tests** - Speed and efficiency testing
5. **Load Tests** - Concurrent usage testing

## 🎬 Test Assets

The `sample_videos/` directory should contain:

- **`Yetti_Patel_s_London_Vlog.mp4`** - Main test video (16:9 format)
- **`Yetti_Patel_s_UK_Tour_Intro.mp4`** - Intro video for merging
- **`open_door_transition_first_clip.mp4`** - Transition video clip
- **`Animation_Transition/`** - Animation transition assets
- **`knolabslogo.png`** - Logo for watermarking tests

## 🚀 Running Tests

### Prerequisites

1. **Environment Setup**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

2. **Required Services**
   ```bash
   # Start Redis (for job queue)
   redis-server
   
   # Or use Docker Compose
   docker compose up -d redis
   ```

3. **Test Assets**
   - Place test videos in `tests/sample_videos/`
   - Ensure FFmpeg is installed for video processing

### Quick Start

```bash
# Run all tests
python tests/run_tests.py

# Check test environment
python tests/run_tests.py --check-env

# Run specific test types
python tests/run_tests.py --type unit
python tests/run_tests.py --type e2e
python tests/run_tests.py --type performance
```

### Manual Test Execution

```bash
# Unit tests only
pytest tests/test_credit_system.py tests/test_api_endpoints.py -v

# Integration tests
pytest tests/test_video_features.py -v

# End-to-end tests (requires full setup)
pytest tests/test_e2e_video_processing.py -v --timeout=600

# Performance tests
pytest tests/test_performance.py -v -m performance

# Load tests
pytest tests/test_performance.py -v -m load

# Generate coverage report
pytest tests/ --cov=services --cov=api --cov-report=html
```

## 📋 Test Scenarios

### 1. Simple Video Merging
- **Test**: `test_simple_merge_two_videos`
- **Purpose**: Verify basic video concatenation
- **Expected**: Free operation (0 credits), valid output file

### 2. Transition Effects
- **Test**: `test_fade_transition`, `test_custom_transition_clip`
- **Purpose**: Test transition effects between videos
- **Expected**: Credit cost, smooth transitions

### 3. Auto-Zoom with Transcription
- **Test**: `test_auto_zoom_with_transcription`
- **Purpose**: Test AI-powered zoom based on speech content
- **Expected**: Transcription + zoom effects, higher credit cost

### 4. Logo Watermarking
- **Test**: `test_logo_overlay_top_right`, `test_logo_overlay_different_positions`
- **Purpose**: Test logo overlay functionality
- **Expected**: Logo placed correctly, credit cost

### 5. TikTok-Style Processing
- **Test**: `test_tiktok_resize_with_effects`
- **Purpose**: Test 9:16 aspect ratio conversion with effects
- **Expected**: Correct aspect ratio, auto-effects applied

### 6. Multi-Video Processing
- **Test**: `test_multi_video_merge_with_credits`
- **Purpose**: Test processing multiple videos with credit calculation
- **Expected**: Additional video costs, successful merge

### 7. Credit System
- **Test**: Various credit calculation and transaction tests
- **Purpose**: Verify credit system accuracy and reliability
- **Expected**: Correct calculations, transaction integrity

### 8. Error Handling
- **Test**: `test_invalid_video_url`, `test_insufficient_credits`
- **Purpose**: Test graceful error handling
- **Expected**: Appropriate error messages, no crashes

## 🎯 Feature Testing Matrix

| Feature | Unit Test | Integration Test | E2E Test | Performance Test |
|---------|-----------|------------------|----------|------------------|
| Simple Merge | ✅ | ✅ | ✅ | ✅ |
| Transitions | ✅ | ✅ | ✅ | ⚠️ |
| Auto-Zoom | ✅ | ✅ | ✅ | ⚠️ |
| Transcription | ✅ | ✅ | ✅ | ⚠️ |
| Logo Overlay | ✅ | ✅ | ✅ | ✅ |
| Credit System | ✅ | ✅ | ✅ | ✅ |
| API Endpoints | ✅ | ✅ | ✅ | ✅ |
| Authentication | ✅ | ✅ | ✅ | ✅ |
| Error Handling | ✅ | ✅ | ✅ | ⚠️ |

Legend: ✅ Implemented, ⚠️ Partial/Optional, ❌ Not Implemented

## 🔧 Test Configuration

### Environment Variables for Testing

```bash
# Test-specific settings
TEST_DATABASE_URL="postgresql://test_user:test_pass@localhost/test_db"
TEST_REDIS_URL="redis://localhost:6379/1"
TEST_STORAGE_BUCKET="test-video-processing"

# Disable external services for unit tests
DISABLE_WHISPER=true
DISABLE_EXTERNAL_STORAGE=true
```

### Pytest Markers

- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.load` - Load tests
- `@pytest.mark.scalability` - Scalability tests
- `@pytest.mark.slow` - Slow-running tests

### Test Fixtures

- `test_user` - Creates test user with API key
- `test_credits` - Adds test credits to user account
- `sample_videos` - Provides paths to test video files
- `temp_dir` - Temporary directory for test outputs
- `api_helper` - Helper for API testing operations
- `video_helper` - Helper for video testing operations

## 📊 Expected Test Results

### Performance Benchmarks

- **Credit Calculation**: < 10ms per calculation
- **API Response Time**: < 2s for most endpoints
- **Simple Video Merge**: < 30s for short videos
- **Logo Overlay**: < 60s for typical videos
- **Auto-Effects**: < 5 minutes (includes transcription)

### Success Criteria

- **Unit Tests**: 100% pass rate
- **Integration Tests**: 95%+ pass rate (some may fail without proper setup)
- **E2E Tests**: 90%+ pass rate (depends on external services)
- **Performance Tests**: Meet benchmark requirements
- **Load Tests**: Handle concurrent operations gracefully

## 🐛 Troubleshooting

### Common Issues

1. **Missing Test Videos**
   - Ensure all test assets are in `tests/sample_videos/`
   - Some tests will be skipped if videos are missing

2. **FFmpeg Not Found**
   - Install FFmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Ubuntu)
   - Video processing tests will fail without FFmpeg

3. **Redis Connection Failed**
   - Start Redis: `redis-server`
   - Or use Docker: `docker run -d -p 6379:6379 redis:alpine`

4. **Whisper Model Download**
   - First run may be slow due to model download
   - Ensure internet connection for initial setup

5. **Database Connection Issues**
   - Check Supabase credentials in `.env`
   - Ensure database schema is properly set up

### Test Debugging

```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test with debugging
pytest tests/test_e2e_video_processing.py::TestSimpleVideoMerge::test_simple_merge_two_videos -v -s

# Run with pdb debugger
pytest tests/ --pdb

# Generate detailed coverage report
pytest tests/ --cov=services --cov-report=html --cov-report=term-missing
```

## 📈 Continuous Integration

For CI/CD pipelines, use:

```bash
# Fast test suite (unit + integration)
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration

# Full test suite (for release testing)
python tests/run_tests.py --type all
```

## 🤝 Contributing Tests

When adding new features:

1. Add unit tests for individual components
2. Add integration tests for service interactions
3. Add E2E tests for complete workflows
4. Update this documentation
5. Ensure all tests pass before submitting PR

### Test Naming Convention

- `test_<feature>_<scenario>` - Basic functionality
- `test_<feature>_<scenario>_error` - Error handling
- `test_<feature>_performance` - Performance testing
- `test_<feature>_edge_case` - Edge case handling
