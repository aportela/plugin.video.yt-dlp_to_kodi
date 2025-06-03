import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib.parse
import sys
import os
import tempfile
from pathlib import Path

plugin_url = sys.argv[0]
handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

def get_cache_path():
    ADDON = xbmcaddon.Addon()
    SETTINGS_ROOT_PATH = ADDON.getSetting('data_path')
    ROOT_PATH = None
    if SETTINGS_ROOT_PATH is not None and os.path.exists(SETTINGS_ROOT_PATH):
        CACHE_BASE_PATH = str(Path(SETTINGS_ROOT_PATH))

    else:
        CACHE_BASE_PATH = str(Path(tempfile.gettempdir()))


    path = Path(CACHE_BASE_PATH, "yt-dlp_to_kodi/cache/")
    path.mkdir(parents=True, exist_ok=True)

    CACHE_BASE_PATH = str(path)
    return CACHE_BASE_PATH


# available log levels
"""
xbmc.LOGDEBUG
xbmc.LOGINFO
xbmc.LOGWARNING
xbmc.LOGERROR
xbmc.LOGFATAL
"""

# notification example
#xbmcgui.Dialog().notification("yt-dlp_to_kodi", "Starting...", xbmcgui.NOTIFICATION_INFO, 500)

def list_directory(path):
    if not os.path.exists(path):
        xbmc.log(f"yt-dlp: list_directory -> path not found: {path}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification("yt-dlp_to_kodi", f"Path not found: {path}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(handle)
        return
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            li = xbmcgui.ListItem(label=entry)
            # TODO
            url = f"{plugin_url}?action=browse_cache&path={urllib.parse.quote_plus(full_path)}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
        else:
            li = xbmcgui.ListItem(label=entry)
            # TODO
            url = f"{plugin_url}?action=play_cache_item&path={urllib.parse.quote_plus(full_path)}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

def main():
    if 'action' in args:
        if args['action'][0] == 'open_settings':
            xbmc.log(f"yt-dlp_to_kodi: opening settings", level=xbmc.LOGDEBUG)
            xbmc.executebuiltin(f"Addon.OpenSettings({xbmcaddon.Addon().getAddonInfo('id')})")
            return
        elif args['action'][0] == 'browse_cache' and 'path' in args:
            path = args['path'][0]
            xbmc.log(f"yt-dlp_to_kodi: browsing cache path {path}", level=xbmc.LOGDEBUG)
            list_directory(path)
    else:
        cache_path = get_cache_path()
        xbmc.log(f"yt-dlp_to_kodi: cache_path: {cache_path}", level=xbmc.LOGDEBUG)
        browse_cache_items = xbmcgui.ListItem(label='Cached videos')
        url = f"{plugin_url}?action=browse_cache&path={urllib.parse.quote_plus(cache_path)}"
        xbmcplugin.addDirectoryItem(handle, url, browse_cache_items, isFolder=True)
        open_settings_item = xbmcgui.ListItem(label='Open settings')
        url = f"{plugin_url}?action=open_settings"
        xbmcplugin.addDirectoryItem(handle, url, open_settings_item, isFolder=False)
        xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    main()
