# resources/lib/cache.py

from pathlib import Path
import tempfile
import os

def clear_cache_path(directory_path):
    for name in os.listdir(directory_path):
        path = os.path.join(directory_path, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):
            clear_cache_path(path)
            os.rmdir(path)

def get_cache_path(settings_root_path = None):
    if settings_root_path is not None and os.path.exists(settings_root_path):
        CACHE_BASE_PATH = str(Path(settings_root_path))
    else:
        CACHE_BASE_PATH = str(Path(tempfile.gettempdir()))

    path = Path(CACHE_BASE_PATH, "yt-dlp_to_kodi", "cache")
    path.mkdir(parents=True, exist_ok=True)

    CACHE_BASE_PATH = str(path)
    return CACHE_BASE_PATH
