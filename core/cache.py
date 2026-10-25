"""Cache and temporary artifact manager for the video pipeline."""

from __future__ import annotations
import os
import shutil
import time

TEMP_DIR = os.path.abspath("outputs/temp")
PUBLIC_MEDIA_DIR = os.path.abspath("remotion/public/media")


def cleanup_temporary_artifacts(max_age_hours: float = 24.0) -> int:
    """Removes temporary files older than max_age_hours."""
    deleted_count = 0
    now = time.time()
    max_age_sec = max_age_hours * 3600

    for directory in [TEMP_DIR, PUBLIC_MEDIA_DIR]:
        if not os.path.exists(directory):
            continue
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            try:
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    if now - os.path.getmtime(filepath) > max_age_sec:
                        os.unlink(filepath)
                        deleted_count += 1
            except Exception:
                pass

    return deleted_count
