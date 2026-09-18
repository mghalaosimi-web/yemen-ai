"""
app/core/version.py
===================
Canonical Version Authority & Runtime Identity for Yemen AI v10.2.
"""
import os
import sys
import time
from datetime import datetime, timezone

APP_NAME = "Yemen AI"
APP_VERSION = "10.2.0"
PIPELINE_VERSION = "canonical_v10_2"
BUILD_ID = f"build_v10_2_{int(time.time())}"
START_TIME = datetime.now(timezone.utc).isoformat()


def get_runtime_identity() -> dict:
    """Return non-sensitive runtime process identity metadata."""
    return {
        "project": APP_NAME,
        "version": APP_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "build_id": BUILD_ID,
        "process_id": os.getpid(),
        "started_at": START_TIME,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
