#!/usr/bin/env python3
"""
Start local server with proper environment setup
"""
import os
import sys
import subprocess
from pathlib import Path

# Set environment variables for local testing
os.environ.update({
    'USE_SQLITE': 'true',
    'USE_LOCAL_STORAGE': 'true',
    'SECRET_KEY': 'local-development-secret-key-not-for-production',
    'JWT_SECRET': 'local-jwt-secret-not-for-production',
    'DEBUG': 'true',
    'PYTHONPATH': str(Path(__file__).parent)
})

if __name__ == "__main__":
    # Start uvicorn server
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'api.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ])
