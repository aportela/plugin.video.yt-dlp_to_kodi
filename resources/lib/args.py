# resources/lib/args.py

import os

from .const import ADDON, ADDON_ARGS, CACHE_PATH
from .log import xmbc_log_debug, xmbc_log_error
from .notification import xmbc_notification_info, xmbc_notification_error
from .cache import clear_cache_path
from .menu import menu_browse_directory, menu_browse_tests, menu_browse_main, menu_open_settings
from .ytdlp_task import process_url

def process_addon_args():
    if 'action' in ADDON_ARGS:
        play = ADDON_ARGS['action'][0] == 'play'
        append = ADDON_ARGS['action'][0] == 'append'
        if (play or append) and 'url' in ADDON_ARGS:
            url = ADDON_ARGS['url'][0]
            xmbc_log_debug(f"yt-dlp_to_kodi: processing url {url}")
            if ADDON.getSetting('auto_clear_cache') == "true":
                clear_cache_path(CACHE_PATH)
            process_url(CACHE_PATH, url, append)

        elif ADDON_ARGS['action'][0] == 'open_settings':
            xmbc_log_debug(f"yt-dlp_to_kodi: opening settings")
            menu_open_settings()
            return

        elif ADDON_ARGS['action'][0] == 'clear_cache':
            xmbc_log_debug(f"yt-dlp_to_kodi: clearing cache")
            clear_cache_path(CACHE_PATH)
            xmbc_notification_info(ADDON.getLocalizedString(30027))
            return

        elif ADDON_ARGS['action'][0] == 'browse_cache' and 'path' in ADDON_ARGS:
            path = ADDON_ARGS['path'][0]
            xmbc_log_debug(f"yt-dlp_to_kodi: browsing cache path {path}")
            menu_browse_directory(path)

        elif ADDON_ARGS['action'][0] == 'show_debug_tests_submenu':
            menu_browse_tests()

        elif ADDON_ARGS['action'][0] == 'play_cache_item' and 'path' in ADDON_ARGS:
            path = ADDON_ARGS['path'][0]
            if os.path.exists(path):
                xmbc_log_debug(f"yt-dlp_to_kodi: playing file {path}")
                player = xbmc.Player()
                player.play(path)
                return
            else:
                xmbc_log_error(f"yt-dlp: file not found: {path}")
                xmbc_notification_error(f"{ADDON.getLocalizedString(30026)}: {path}")
                return
    else:
        xmbc_log_debug(f"Missing/invalid args => show addon menu")
        menu_browse_main()
