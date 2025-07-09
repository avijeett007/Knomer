"""
Celery configuration for async video processing
"""
import os
from celery import Celery
from config.settings import settings

# Create Celery instance
celery_app = Celery(
    "video_processor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.video_processing",
        "tasks.cleanup"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "tasks.video_processing.*": {"queue": "video_processing"},
        "tasks.cleanup.*": {"queue": "cleanup"},
    },
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time for video processing
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to prevent memory leaks
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-temp-files": {
            "task": "tasks.cleanup.cleanup_temp_files",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-expired-jobs": {
            "task": "tasks.cleanup.cleanup_expired_jobs",
            "schedule": 3600.0,  # Every hour
        },
        "update-job-stats": {
            "task": "tasks.cleanup.update_system_stats",
            "schedule": 900.0,  # Every 15 minutes
        },
    },
    
    # Queue configuration
    task_default_queue="default",
    task_queues={
        "video_processing": {
            "routing_key": "video_processing",
            "priority": 10,
        },
        "cleanup": {
            "routing_key": "cleanup",
            "priority": 1,
        },
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

# Task priority levels
PRIORITY_HIGH = 9
PRIORITY_NORMAL = 5
PRIORITY_LOW = 1

# Custom task base class with retry logic
class BaseTaskWithRetry(celery_app.Task):
    """Base task class with custom retry logic"""
    
    def retry_with_backoff(self, exc=None, **kwargs):
        """Retry with exponential backoff"""
        countdown = 2 ** self.request.retries
        max_countdown = 300  # 5 minutes max
        countdown = min(countdown, max_countdown)
        
        return self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=kwargs.get('max_retries', 3),
            **kwargs
        )

# Set the custom base task
celery_app.Task = BaseTaskWithRetry

if __name__ == "__main__":
    celery_app.start()
