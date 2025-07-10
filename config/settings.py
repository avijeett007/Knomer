"""
Configuration settings for Video Processing API
"""
import os
from typing import Dict, Any
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # API Configuration
    API_TITLE: str = "Video Processing API"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "Advanced video processing service with credit system and async processing"
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database Configuration
    USE_SQLITE: bool = Field(default=False, env="USE_SQLITE")
    SQLITE_DB_PATH: str = Field(default="database/test_database.db", env="SQLITE_DB_PATH")

    # Supabase Configuration (optional for local testing)
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_ANON_KEY: str = Field(default="", env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    DATABASE_URL: str = Field(default="", env="DATABASE_URL")
    
    # Redis Configuration for Job Queue
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_PASSWORD: str = Field(default="", env="REDIS_PASSWORD")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # Storage Configuration
    USE_LOCAL_STORAGE: bool = Field(default=False, env="USE_LOCAL_STORAGE")
    LOCAL_STORAGE_PATH: str = Field(default="./storage", env="LOCAL_STORAGE_PATH")
    STORAGE_BUCKET: str = Field(default="video-processing", env="STORAGE_BUCKET")
    TEMP_STORAGE_PATH: str = Field(default="/tmp/video_processing", env="TEMP_STORAGE_PATH")

    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = Field(default="", env="AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_ACCOUNT_NAME: str = Field(default="", env="AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_STORAGE_ACCOUNT_KEY: str = Field(default="", env="AZURE_STORAGE_ACCOUNT_KEY")
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key", env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    API_KEY_PREFIX: str = Field(default="vp_", env="API_KEY_PREFIX")
    JWT_SECRET: str = Field(default="dev-jwt-secret", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ADMIN_API_KEY: str = Field(default="admin-secret-key", env="ADMIN_API_KEY")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="DEFAULT_RATE_LIMIT_PER_MINUTE")
    DEFAULT_RATE_LIMIT_PER_HOUR: int = Field(default=100, env="DEFAULT_RATE_LIMIT_PER_HOUR")
    DEFAULT_RATE_LIMIT_PER_DAY: int = Field(default=1000, env="DEFAULT_RATE_LIMIT_PER_DAY")
    
    # Credit System
    DEFAULT_USER_CREDITS: int = Field(default=10000, env="DEFAULT_USER_CREDITS")
    CREDIT_COST_PER_SECOND: int = Field(default=1, env="CREDIT_COST_PER_SECOND")
    PREMIUM_CREDIT_COST_PER_MINUTE: int = Field(default=100, env="PREMIUM_CREDIT_COST_PER_MINUTE")
    CREDITS_PER_10_SECONDS: int = Field(default=1, env="CREDITS_PER_10_SECONDS")
    FREE_TIER_CREDITS: int = Field(default=100, env="FREE_TIER_CREDITS")
    
    # Processing Configuration
    MAX_VIDEO_SIZE_MB: int = Field(default=500, env="MAX_VIDEO_SIZE_MB")
    MAX_PROCESSING_TIME_MINUTES: int = Field(default=30, env="MAX_PROCESSING_TIME_MINUTES")
    WHISPER_MODEL_DISABLED: bool = Field(default=True, env="WHISPER_MODEL_DISABLED")
    MAX_VIDEO_DURATION_SECONDS: int = Field(default=600, env="MAX_VIDEO_DURATION_SECONDS")  # 10 minutes
    MAX_VIDEOS_PER_JOB: int = Field(default=10, env="MAX_VIDEOS_PER_JOB")
    PROCESSING_TIMEOUT_SECONDS: int = Field(default=1800, env="PROCESSING_TIMEOUT_SECONDS")  # 30 minutes
    
    # File Cleanup
    TEMP_FILE_CLEANUP_HOURS: int = Field(default=1, env="TEMP_FILE_CLEANUP_HOURS")
    OUTPUT_FILE_RETENTION_DAYS: int = Field(default=7, env="OUTPUT_FILE_RETENTION_DAYS")
    
    # External Services
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")  # For Whisper transcription
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Credit costs for different features
CREDIT_COSTS: Dict[str, Dict[str, Any]] = {
    "simple_merge": {
        "base_cost": 0,  # Free tier
        "per_10_seconds": 0
    },
    "transition_merge": {
        "base_cost": 1,
        "per_10_seconds": 1
    },
    "auto_effects": {
        "base_cost": 5,
        "per_10_seconds": 2,
        "transcription_cost": 3  # Additional cost for Whisper
    },
    "logo_overlay": {
        "base_cost": 2,
        "per_10_seconds": 1
    },
    "multi_video": {
        "base_cost": 0,
        "per_10_seconds": 1,
        "per_additional_video": 1
    },
    "premium_ai_enhancement": {
        "base_cost": 50,  # Minimum cost
        "per_minute": 100,  # 100 credits per minute
        "ai_smart_zoom": 20,  # Additional per minute
        "ai_smart_captions": 15,  # Additional per minute
        "ai_smart_overlays": 10,  # Additional per minute
        "ai_smart_transitions": 10,  # Additional per minute
        "premium_logo_overlay": 5  # Additional per minute
    },
    "audio_separation": {
        "base_cost": 5,  # Minimum cost
        "per_minute": 10,  # 10 credits per minute
        "enhancement_cost": 2,  # Additional per minute for enhancement
        "mixed_output_cost": 1  # Additional for mixed output
    },
    "custom_transitions": {
        "base_cost": 3,
        "per_transition": 2
    },
    "ai_effects": {
        "zoom": {"base_cost": 2, "per_10_seconds": 1},
        "blur": {"base_cost": 1, "per_10_seconds": 0.5},
        "motion_crop": {"base_cost": 3, "per_10_seconds": 1.5},
        "auto_resize": {"base_cost": 1, "per_10_seconds": 0.5}
    }
}

# Supported video formats and their processing complexity
SUPPORTED_FORMATS = {
    "mp4": {"complexity": 1.0, "preferred": True},
    "mov": {"complexity": 1.2, "preferred": True},
    "avi": {"complexity": 1.5, "preferred": False},
    "mkv": {"complexity": 1.3, "preferred": False},
    "webm": {"complexity": 1.1, "preferred": True}
}

# FFmpeg presets for different quality levels
FFMPEG_PRESETS = {
    "fast": {
        "preset": "ultrafast",
        "crf": 28,
        "description": "Fastest processing, lower quality"
    },
    "balanced": {
        "preset": "fast",
        "crf": 23,
        "description": "Good balance of speed and quality"
    },
    "quality": {
        "preset": "slow",
        "crf": 18,
        "description": "Best quality, slower processing"
    }
}

# Transition effects available
TRANSITION_EFFECTS = {
    "fade": {
        "duration_range": (0.5, 3.0),
        "credit_multiplier": 1.0,
        "description": "Smooth fade transition"
    },
    "dissolve": {
        "duration_range": (0.5, 2.0),
        "credit_multiplier": 1.2,
        "description": "Cross-dissolve transition"
    },
    "slide": {
        "duration_range": (0.3, 1.5),
        "credit_multiplier": 1.5,
        "description": "Sliding transition"
    },
    "zoom": {
        "duration_range": (0.5, 2.0),
        "credit_multiplier": 1.8,
        "description": "Zoom in/out transition"
    },
    "custom": {
        "duration_range": (0.1, 5.0),
        "credit_multiplier": 2.0,
        "description": "Custom transition clip"
    }
}

# Auto-effects based on content analysis
AUTO_EFFECTS = {
    "zoom_on_face": {
        "trigger_keywords": ["person", "face", "speaker", "interview"],
        "credit_multiplier": 2.0
    },
    "motion_blur": {
        "trigger_keywords": ["action", "movement", "sports", "fast"],
        "credit_multiplier": 1.5
    },
    "crop_to_subject": {
        "trigger_keywords": ["focus", "highlight", "important", "main"],
        "credit_multiplier": 2.5
    },
    "tiktok_style": {
        "trigger_keywords": ["vertical", "mobile", "social", "short"],
        "credit_multiplier": 1.8
    }
}

# Initialize settings
settings = Settings()
