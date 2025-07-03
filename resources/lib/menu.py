# resources/lib/menu.py

import xbmc
import xbmcplugin
import xbmcgui

import os
from urllib.parse import quote_plus

from .const import CACHE_PATH, ADDON, ADDON_HANDLE, ADDON_PLUGIN_URL, EXAMPLE_VIDEO_YOUTUBE_URL, EXAMPLE_VIDEO_TWITCH_URL
from .nfo_generator import parse_nfo
from .log import xmbc_log_error, xmbc_log_debug

def menu_browse_directory(path):
    if not os.path.exists(path):
        xmbc_log_error(f"yt-dlp_to_kodi: menu_browse_directory() -> path not found: {path}")
        xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = f"{ADDON.getLocalizedString(30021)}: {path}", icon = xbmcgui.NOTIFICATION_ERROR, time = DEFAULT_NOTIFICATION_MILLISECONDS)
        return
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            li = xbmcgui.ListItem(label=entry)
            url = f"{ADDON_PLUGIN_URL}?action=browse_cache&path={quote_plus(full_path)}"
            xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, li, isFolder=True)
        else:
            # TODO: only if use NFO metadata
            video_exts = ['.mp4', '.mkv', '.avi', '.webm']
            ext = os.path.splitext(full_path)[1].lower()
            if ext in video_exts:
                base_name = os.path.splitext(full_path)[0]
                nfo_path = os.path.join(path, base_name + '.nfo')

                title = entry
                year = ''
                plot = ''

                if os.path.exists(nfo_path):
                    nfo_title, nfo_year, nfo_plot = parse_nfo(nfo_path)
                    if nfo_title:
                        title = nfo_title
                    if nfo_year:
                        year = nfo_year
                    if nfo_plot:
                        plot = nfo_plot

                li = xbmcgui.ListItem(label=title)
                fanart = None
                thumb = None
                base_name = os.path.splitext(full_path)[0]
                # TODO: use metadata urls if local image not found
                for img_ext in ['.jpg', '.png']:
                    img_path = os.path.join(path, base_name + img_ext)
                    if os.path.exists(img_path):
                        thumb = img_path
                        fanart = img_path # TODO: channel background as fanart
                        break
                if thumb:
                    li.setArt({'thumb': thumb, 'fanart': fanart})
                info_labels = {
                    'title': title,
                    'year': year,
                    'plot': plot,
                    'mediatype': 'movie'
                }
                li.setInfo('video', info_labels)
                """
                video_info = {
                    'codec': 'h264',
                    'aspect': 1.78,
                    'width': 1280,
                    'height': 720,
                }
                li.addStreamInfo('video', video_info)
                li.addStreamInfo('audio', {'codec': 'dts', 'language': 'en', 'channels': 2})
                li.addStreamInfo('subtitle', {'language': 'en'})
                """
                url = f"{ADDON_PLUGIN_URL}?action=play_cache_item&path={quote_plus(full_path)}"
                xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def menu_browse_main():
    xmbc_log_debug(f"yt-dlp_to_kodi: cache_path: {CACHE_PATH}")
    item = xbmcgui.ListItem(label=ADDON.getLocalizedString(30001))
    url = f"{ADDON_PLUGIN_URL}?action=browse_cache&path={quote_plus(CACHE_PATH)}"
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=True)
    item = xbmcgui.ListItem(label=ADDON.getLocalizedString(30002))
    url = f"{ADDON_PLUGIN_URL}?action=open_settings"
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=False)
    item = xbmcgui.ListItem(label=ADDON.getLocalizedString(30004))
    url = f"{ADDON_PLUGIN_URL}?action=clear_cache"
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=False)
    debug = ADDON.getSetting('debug')
    if debug == 'true':
        item = xbmcgui.ListItem(label=ADDON.getLocalizedString(30005))
        url = f"{ADDON_PLUGIN_URL}?action=show_ytdlp_version"
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=True)
        item = xbmcgui.ListItem(label=ADDON.getLocalizedString(30003))
        url = f"{ADDON_PLUGIN_URL}?action=show_debug_tests_submenu"
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def menu_browse_tests():
    item = xbmcgui.ListItem(label='Test [youtube] video')
    info = item.getVideoInfoTag()
    info.setTitle("Test [youtube] video")
    url = f"{ADDON_PLUGIN_URL}?action=play&url={quote_plus(EXAMPLE_VIDEO_YOUTUBE_URL)}"
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=False)
    item = xbmcgui.ListItem(label='Test [twitch] video')
    info = item.getVideoInfoTag()
    info.setTitle("Test [twitch] video")
    url = f"{ADDON_PLUGIN_URL}?action=play&url={quote_plus(EXAMPLE_VIDEO_TWITCH_URL)}"
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, url, item, isFolder=False)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def menu_open_settings():
    xbmc.executebuiltin(f"Addon.OpenSettings({ADDON.getAddonInfo('id')})")
