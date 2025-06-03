import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib.parse
import sys
import os
import threading
import subprocess
import tempfile
from pathlib import Path
import re

EXAMPLE_VIDEO_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
EXAMPLE_VIDEO_TWITCH_URL = "https://www.twitch.tv/videos/799499623"

plugin_url = sys.argv[0]
handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])
ADDON = xbmcaddon.Addon()

def get_cache_path():
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
        xbmc.log(f"yt-dlp_to_kodi: list_directory() -> path not found: {path}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification("yt-dlp_to_kodi", f"Path not found: {path}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(handle)
        return
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            li = xbmcgui.ListItem(label=entry)
            url = f"{plugin_url}?action=browse_cache&path={urllib.parse.quote_plus(full_path)}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
        else:
            li = xbmcgui.ListItem(label=entry)
            # TODO
            url = f"{plugin_url}?action=play_cache_item&path={urllib.parse.quote_plus(full_path)}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

def download_to_cache(cache_path, url):

    if not os.path.exists(cache_path):
        xbmc.log(f"yt-dlp_to_kodi: download_to_cache() -> path not found: {cache_path}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification("yt-dlp_to_kodi", f"Path not found: {cache_path}", xbmcgui.NOTIFICATION_ERROR)
        return
    else:
        dialog = xbmcgui.DialogProgress()
        dialog.create("yt-dlp to kodi", f"Processing url: {url}")

        def ytdlp_download_to_cache():
            xbmc.log(f"yt-dlp_to_kodi: using url {url}", level=xbmc.LOGINFO)
            COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE = f'{cache_path}{"" if cache_path.endswith(os.sep) else os.sep }%(webpage_url_domain)s/%(uploader)s - %(uploader_id)s/%(title)s - %(id)s - %(height)sp - - %(vcodec)s - %(acodec)s.%(ext)s'
            COMMAND_LINE_MAX_VIDEO_HEIGHT=int(ADDON.getSetting('max_resolution')) or 1080

            output_filename = ""

            commandline = [
                'yt-dlp',
                '--no-warnings',
                '--no-color',
                '--progress',
                '-f', f'bestvideo[height<=?{COMMAND_LINE_MAX_VIDEO_HEIGHT}]+bestaudio/best',
                '--force-overwrite', # TODO: use settings
                '--restrict-filenames',
                '-o', COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE,
                # TODO: write thumbnail & generate NFO
                url
            ]

            xbmc.log(f"yt-dlp_to_kodi: commandline => {' '.join(commandline)}", level=xbmc.LOGINFO)

            yt_dlp_proc = subprocess.Popen(commandline, stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 1, universal_newlines = True)

            percent = 0
            output_buffer = ""
            output_line = ""

            while True:

                output = yt_dlp_proc.stdout.read(1024)

                if not output and yt_dlp_proc.poll() is not None:
                    break

                if isinstance(output, bytes):
                    output = output.decode('utf-8')

                output_buffer += output

                while '\r' in output_buffer or '\n' in output_buffer:
                    if '\r' in output_buffer:
                        output_line, output_buffer = output_buffer.split('\r', 1)
                    elif '\n' in output_buffer:
                        output_line, output_buffer = output_buffer.split('\n', 1)

                    match = re.search(r'\[download\]\s*(\d+\.\d+)%', output_line)
                    if match:
                        percent = float(match.group(1))
                        dialog.update(int(percent), f"Downloaded: {percent:.2f}%")
                    elif not output_filename:
                        match = re.search(r'\[Merger\] Merging formats into "(.*)"$', output_line)
                        if match:
                            output_filename = os.path.abspath(match.group(1).strip())
                            xbmc.log(f"yt-dlp_to_kodi: output file => {output_filename}", level=xbmc.LOGINFO)
                        else:
                            # required for twitch streams
                            match = re.search(r'\[FixupM3u8\] Fixing MPEG-TS in MP4 container of "(.*)"$', output_line)
                            if match:
                                output_filename = os.path.abspath(match.group(1).strip())
                                xbmc.log(f"yt-dlp_to_kodi: output file => {output_filename}", level=xbmc.LOGINFO)

                    #xbmc.log(f"yt-dlp_to_kodi: {output_line}", level=xbmc.LOGINFO)

                xbmc.sleep(100)

            for error_linea in yt_dlp_proc.stderr:
                xbmc.log(f"yt-dlp_to_kodi: {error_linea}", level=xbmc.LOGERROR)

            yt_dlp_proc.communicate()

            dialog.close()

            if yt_dlp_proc.returncode == 0:
                xbmc.log(f"yt-dlp_to_kodi: download success", level=xbmc.LOGDEBUG)

                xbmc.executebuiltin('Notification("Download sucess", "Video has been downloaded", 3000)')

                if os.path.exists(output_filename):
                    file = output_filename.replace('\\', '/') # REQUIRED ?
                    xbmc.log(f"yt-dlp: playing: {file}", level=xbmc.LOGINFO)
                    # TODO play using play_cache_item
                    player = xbmc.Player()
                    player.play(file)
                else:
                    xbmc.log(f"yt-dlp_to_kodi: file not found {output_filename}", level=xbmc.LOGERROR)
                    xbmc.executebuiltin('Notification("Error", "Downloaded file not found", 3000)')
            else:
                xbmc.log(f"yt-dlp_to_kodi: download error", level=xbmc.LOGINFO)
                xbmc.executebuiltin('Notification("Download error", "Error while downloading file", 3000)')

        descarga_thread = threading.Thread(target=ytdlp_download_to_cache)
        descarga_thread.start()

def show_addon_menu():
    debug = ADDON.getSetting('debug')
    if debug == 'true':
        test_video_item = xbmcgui.ListItem(label='Youtube test video')
        info = test_video_item.getVideoInfoTag()
        info.setTitle("Youtube test video")
        url_with_param = f"{plugin_url}?action=process&url={urllib.parse.quote_plus(EXAMPLE_VIDEO_YOUTUBE_URL)}"
        xbmcplugin.addDirectoryItem(handle, url_with_param, test_video_item, isFolder=False)
        test_video_item = xbmcgui.ListItem(label='Twitch test video')
        info = test_video_item.getVideoInfoTag()
        info.setTitle("Twitch test video")
        url_with_param = f"{plugin_url}?action=process&url={urllib.parse.quote_plus(EXAMPLE_VIDEO_TWITCH_URL)}"
        xbmcplugin.addDirectoryItem(handle, url_with_param, test_video_item, isFolder=False)
    cache_path = get_cache_path()
    xbmc.log(f"yt-dlp_to_kodi: cache_path: {cache_path}", level=xbmc.LOGDEBUG)
    browse_cache_items = xbmcgui.ListItem(label='Cached videos')
    url = f"{plugin_url}?action=browse_cache&path={urllib.parse.quote_plus(cache_path)}"
    xbmcplugin.addDirectoryItem(handle, url, browse_cache_items, isFolder=True)
    open_settings_item = xbmcgui.ListItem(label='Open settings')
    url = f"{plugin_url}?action=open_settings"
    xbmcplugin.addDirectoryItem(handle, url, open_settings_item, isFolder=False)
    xbmcplugin.endOfDirectory(handle)

def main():
    if 'action' in args:
        if args['action'][0] == 'process' and 'url' in args:
            url = args['url'][0]
            xbmc.log(f"yt-dlp_to_kodi: processing url {url}", level=xbmc.LOGDEBUG)
            cache_path = get_cache_path()
            download_to_cache(cache_path, url)
        elif args['action'][0] == 'open_settings':
            xbmc.log(f"yt-dlp_to_kodi: opening settings", level=xbmc.LOGDEBUG)
            xbmc.executebuiltin(f"Addon.OpenSettings({xbmcaddon.Addon().getAddonInfo('id')})")
            return
        elif args['action'][0] == 'browse_cache' and 'path' in args:
            path = args['path'][0]
            xbmc.log(f"yt-dlp_to_kodi: browsing cache path {path}", level=xbmc.LOGDEBUG)
            list_directory(path)
        elif args['action'][0] == 'play_cache_item' and 'path' in args:
            path = args['path'][0]
            if os.path.exists(path):
                xbmc.log(f"yt-dlp_to_kodi: playing file {path}", level=xbmc.LOGDEBUG)
                player = xbmc.Player()
                player.play(path)
            else:
                xbmc.log(f"yt-dlp: file not found: {path}", level=xbmc.LOGERROR)
                xbmcgui.Dialog().notification("yt-dlp_to_kodi", f"file not found: {path}", xbmcgui.NOTIFICATION_ERROR)
                return
    else:
        show_addon_menu()

if __name__ == '__main__':
    main()
