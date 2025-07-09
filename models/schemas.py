"""
Pydantic models for Video Processing API
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

# Enums
class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    SIMPLE_MERGE = "simple_merge"
    TRANSITION_MERGE = "transition_merge"
    AUTO_EFFECTS = "auto_effects"
    LOGO_OVERLAY = "logo_overlay"
    MULTI_VIDEO = "multi_video"
    PREMIUM_AI_ENHANCEMENT = "premium_ai_enhancement"
    AUDIO_SEPARATION = "audio_separation"

class TransactionType(str, Enum):
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    BONUS = "bonus"

class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class Platform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    CUSTOM = "custom"

# Base Models
class BaseResponse(BaseModel):
    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseResponse):
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# User Models
class UserCreate(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    subscription_tier: SubscriptionTier
    is_active: bool
    created_at: datetime

class UserCredits(BaseModel):
    total_credits: int
    used_credits: int
    remaining_credits: int
    last_updated: datetime

# API Key Models
class APIKeyCreate(BaseModel):
    name: Optional[str] = None
    expires_at: Optional[datetime] = None
    rate_limit_per_minute: Optional[int] = Field(default=10, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(default=100, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(default=1000, ge=1, le=100000)

class APIKeyResponse(BaseModel):
    id: UUID
    key_prefix: str
    name: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int

class APIKeyWithSecret(APIKeyResponse):
    api_key: str  # Only returned once during creation

# Video Processing Models
class VideoInput(BaseModel):
    url: Optional[str] = None  # For external URLs
    file_name: Optional[str] = None
    duration: Optional[float] = None
    order_index: int = Field(default=0, ge=0)

class TransitionConfig(BaseModel):
    type: str = Field(..., pattern=r'^(fade|dissolve|slide|zoom|custom)$')
    duration: float = Field(default=1.0, ge=0.1, le=5.0)
    custom_clip_url: Optional[str] = None  # For custom transitions

class EffectConfig(BaseModel):
    type: str
    intensity: float = Field(default=1.0, ge=0.0, le=2.0)
    parameters: Optional[Dict[str, Any]] = None

class LogoOverlayConfig(BaseModel):
    logo_url: str
    position: str = Field(default="top-right", pattern=r'^(top-left|top-right|bottom-left|bottom-right|center)$')
    size: float = Field(default=0.1, ge=0.01, le=0.5)  # Relative to video size
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    duration: Optional[float] = None  # If None, shows for entire video

class ProcessingOptions(BaseModel):
    platform: Platform = Platform.YOUTUBE
    quality_preset: str = Field(default="balanced", pattern=r'^(fast|balanced|quality)$')
    output_format: str = Field(default="mp4", pattern=r'^(mp4|mov|webm)$')

    # Transition options
    transitions: Optional[List[TransitionConfig]] = None
    auto_transitions: bool = False

    # Effects options
    auto_effects: bool = False
    custom_effects: Optional[List[EffectConfig]] = None

    # Overlay options
    logo_overlay: Optional[LogoOverlayConfig] = None

    # AI features
    enable_transcription: bool = False
    ai_effects_based_on_transcript: bool = False

    # Premium AI features (for premium_ai_enhancement job type)
    ai_smart_zoom: bool = False
    ai_smart_captions: bool = False
    ai_smart_overlays: bool = False
    ai_smart_transitions: bool = False
    premium_logo_overlay: bool = False
    max_effects_per_minute: int = Field(default=5, ge=1, le=20)
    effect_intensity_preference: str = Field(default="balanced", pattern=r'^(subtle|balanced|dramatic)$')

    # Audio separation features (for audio_separation job type)
    enhance_voice: bool = True
    enhance_music: bool = True
    voice_volume: float = Field(default=1.0, ge=0.0, le=2.0)
    music_volume: float = Field(default=0.7, ge=0.0, le=2.0)
    create_mixed_output: bool = False
    output_format: str = Field(default="wav", pattern=r'^(wav|mp3|flac|aac)$')

    # Output specifications
    target_resolution: Optional[str] = Field(default=None, pattern=r'^\d+x\d+$')
    target_aspect_ratio: Optional[str] = Field(default=None, pattern=r'^\d+:\d+$')

# Job Models
class JobCreate(BaseModel):
    job_type: JobType
    videos: List[VideoInput] = Field(..., min_items=1, max_items=10)
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    
    @field_validator('videos')
    @classmethod
    def validate_videos(cls, v, info):
        if info.data.get('job_type') == JobType.SIMPLE_MERGE and len(v) < 2:
            raise ValueError('Simple merge requires at least 2 videos')
        return v

class JobResponse(BaseModel):
    id: UUID
    job_type: JobType
    status: JobStatus
    estimated_credits: Optional[int]
    actual_credits_used: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    output_file_url: Optional[str]
    download_expires_at: Optional[datetime]
    download_count: int = 0

class JobStatusResponse(BaseResponse):
    job: JobResponse
    progress_percentage: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    current_step: Optional[str] = None
    completed_steps: Optional[List[str]] = None
    failed_steps: Optional[List[str]] = None
    retry_count: Optional[int] = None

class JobListResponse(BaseResponse):
    jobs: List[JobResponse]
    total_count: int
    page: int
    page_size: int

# Credit Models
class CreditTransaction(BaseModel):
    id: UUID
    transaction_type: TransactionType
    amount: int
    description: Optional[str]
    job_id: Optional[UUID]
    created_at: datetime

class CreditEstimate(BaseModel):
    estimated_credits: int
    breakdown: Dict[str, int]
    total_duration_seconds: float

class CreditPurchase(BaseModel):
    amount: int = Field(..., ge=1, le=10000)
    payment_method: str
    payment_reference: Optional[str] = None

# File Models
class VideoFile(BaseModel):
    id: UUID
    file_type: str
    file_url: str
    file_name: Optional[str]
    file_size: Optional[int]
    duration: Optional[float]
    resolution: Optional[str]
    format: Optional[str]
    order_index: Optional[int]

# Health and Status Models
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]
    queue_status: Optional[Dict[str, Any]] = None

class SystemStats(BaseModel):
    total_jobs_processed: int
    active_jobs: int
    queue_length: int
    average_processing_time: float
    total_credits_consumed: int
    active_users: int

# Request/Response Models for specific endpoints
class EstimateCreditRequest(BaseModel):
    job_type: JobType
    videos: List[VideoInput]
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)

class DownloadResponse(BaseModel):
    download_url: str
    expires_at: datetime
    file_size: int
    content_type: str = "video/mp4"
