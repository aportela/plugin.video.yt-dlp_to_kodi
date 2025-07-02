# resources/lib/const.py

import xbmcaddon

import sys
from urllib.parse import parse_qs
from .cache import get_cache_path

ADDON = xbmcaddon.Addon()
ADDON_PLUGIN_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
ADDON_ARGS = parse_qs(sys.argv[2][1:])

CACHE_PATH = get_cache_path(ADDON.getSetting('storage_path'))

SHOW_ADDON_BIG_DIALOG = True

DEFAULT_NOTIFICATION_MILLISECONDS = int(ADDON.getSetting('default_notification_seconds')) * 1000 or 3000

EXAMPLE_VIDEO_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
EXAMPLE_VIDEO_TWITCH_URL = "https://www.twitch.tv/videos/799499623"
