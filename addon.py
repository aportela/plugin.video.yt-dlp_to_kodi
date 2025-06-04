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
            COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE = f'{cache_path}{"" if cache_path.endswith(os.sep) else os.sep }%(webpage_url_domain)s/%(uploader)s - %(uploader_id)s/%(upload_date)s - %(title)s - %(id)s - %(height)sp - - %(vcodec)s - %(acodec)s.%(ext)s'
            COMMAND_LINE_MAX_VIDEO_HEIGHT=int(ADDON.getSetting('max_resolution')) or 1080

            output_filename = ""
            output_thumbnail = ""

            commandline = [
                'yt-dlp',
                '--no-warnings',
                '--no-color',
                '--newline',
                '--progress',
                '-f', f'bestvideo[height<=?{COMMAND_LINE_MAX_VIDEO_HEIGHT}]+bestaudio/best',
                '--restrict-filenames',
                '-o', COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE,
                # TODO: write thumbnail & generate NFO
                url
            ]

            if ADDON.getSetting('force_overwrite') == "true":
                commandline.insert((len(commandline) - 1), '--force-overwrite')

            if True or ADDON.getSetting('save_thumbnail') == "true":
                commandline.insert((len(commandline) - 1), '--write-thumbnail')
                commandline.insert((len(commandline) - 1), '--convert-thumbnails')
                commandline.insert((len(commandline) - 1), 'jpg')

            xbmc.log(f"yt-dlp_to_kodi: commandline => {' '.join(commandline)}", level=xbmc.LOGINFO)

            yt_dlp_proc = subprocess.Popen(commandline, stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 1, universal_newlines = True)

            percent = 0
            output_line = ""

            while True:

                output = yt_dlp_proc.stdout.readline()

                if not output and yt_dlp_proc.poll() is not None:
                    break

                if isinstance(output, bytes):
                    output = output.decode('utf-8')


                output_line = output.strip()

                #xbmc.log(f"yt-dlp_to_kodi: {output_line}", level=xbmc.LOGINFO)

                patterns = [
                    (r'\[download\]\s*(\d+\.\d+)%', lambda match: ('percent', float(match.group(1)))),
                    (r'\[Merger\] Merging formats into "(.*)"$', lambda match: ('merger', os.path.abspath(match.group(1).strip()))),
                    (r'\[info\] Writing video thumbnail \d+ to: "(.*)"$', lambda match: ('thumbnail_path', os.path.abspath(match.group(1).strip()))),
                    (r'\[download\] (.*) has already been downloaded$', lambda match: ('already_downloaded', os.path.abspath(match.group(1).strip()))),
                    (r'\[FixupM3u8\] Fixing MPEG-TS in MP4 container of "(.*)"$', lambda match: ('fixup', os.path.abspath(match.group(1).strip()))),
                    (r'Error: (.*)$', lambda match: ('error', match.group(1)))
                ]

                for pattern, action in patterns:
                    match = re.search(pattern, output_line)
                    if match:
                        result_type, result = action(match)
                        if result_type == 'percent':
                            percent = result
                            dialog.update(int(percent), f"Download progress: {percent:.2f}%")
                        elif result_type == 'merger':
                            output_filename = result
                            xbmc.log(f"yt-dlp_to_kodi: output file => {output_filename}", level=xbmc.LOGINFO)
                        elif result_type == 'thumbnail_path':
                            output_thumbnail = result
                            xbmc.log(f"yt-dlp_to_kodi: output thumbnail => {output_thumbnail}", level=xbmc.LOGINFO)
                        elif result_type == 'already_downloaded':
                            output_filename = result
                            xbmc.log(f"yt-dlp_to_kodi: already downloaded file => {output_filename}", level=xbmc.LOGINFO)
                        elif result_type == 'fixup':
                            output_filename = result
                            xbmc.log(f"yt-dlp_to_kodi: fixup file => {output_filename}", level=xbmc.LOGINFO)
                        elif result_type == 'error':
                            xbmc.log(f"yt-dlp_to_kodi: error occurred: {result}", level=xbmc.LOGERROR)
                        break
                xbmc.sleep(100)

            for error_linea in yt_dlp_proc.stderr:
                xbmc.log(f"yt-dlp_to_kodi: {error_linea}", level=xbmc.LOGERROR)

            yt_dlp_proc.communicate()

            dialog.close()

            if yt_dlp_proc.returncode == 0:
                xbmc.log(f"yt-dlp_to_kodi: download success", level=xbmc.LOGDEBUG)

                xbmc.executebuiltin('Notification("yt-dlp to kodi", "Video has been downloaded, started playing...", 3000)')

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
