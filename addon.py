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

from resources.lib.nfo_generator import parse_nfo, generate_nfo

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
            video_exts = ['.mp4', '.mkv', '.avi', '.webm']
            ext = os.path.splitext(full_path)[1].lower()
            if ext in video_exts:
                base_name = os.path.splitext(full_path)[0]
                nfo_path = os.path.join(path, base_name + '.nfo')

                title = full_path
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
            output_json_metadata = ""

            commandline = [
                'yt-dlp',
                # Ignore warnings
                '--no-warnings',
                # remove ANSI colors
                '--no-color',
                # Show progress bar, even if in quiet mode
                '--progress',
                # Output progress bar as new lines
                '--newline',
                # Video format code, see "FORMAT SELECTION" for more details
                '-f', f'bestvideo[height<=?{COMMAND_LINE_MAX_VIDEO_HEIGHT}]+bestaudio/best',
                # Restrict filenames to only ASCII characters, and avoid "&" and spaces in filenames
                '--restrict-filenames',
                # Force filenames to be Windows-compatible
                '--windows-filenames',
                # Resume partially downloaded files/fragments (default)
                '--continue',
                # Output filename template; see "OUTPUT TEMPLATE" for details
                '-o', COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE,
                # main URL
                url
            ]

            if ADDON.getSetting('force_overwrite') == "true":
                # Overwrite all video and metadata files. This option includes --no-continue
                commandline.insert((len(commandline) - 1), '--force-overwrite')

            if ADDON.getSetting('save_thumbnail') == "true":
                # Write thumbnail image to disk
                commandline.insert((len(commandline) - 1), '--write-thumbnail')
                # Convert the thumbnails to another format (currently supported: jpg, png, webp).
                # You can specify multiple rules using similar syntax as "--remux-video".
                # Use "--convert-thumbnails none" to disable conversion (default)
                commandline.insert((len(commandline) - 1), '--convert-thumbnails')
                commandline.insert((len(commandline) - 1), 'jpg')

            if ADDON.getSetting('save_nfo') == "true":
                # Write video metadata to a .info.json file (this may contain personal information)
                commandline.insert((len(commandline) - 1), '--write-info-json')

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

                if ADDON.getSetting('debug') == "true":
                    xbmc.log(f"yt-dlp_to_kodi: {output_line}", level=xbmc.LOGDEBUG)

                patterns = [
                    (r'\[download\]\s*(\d+\.\d+)%', lambda match: ('percent', float(match.group(1)))),
                    (r'\[Merger\] Merging formats into "(.*)"$', lambda match: ('merger', os.path.abspath(match.group(1).strip()))),
                    (r'\[info\] Writing video thumbnail \d+ to: (.*)$', lambda match: ('thumbnail_path', os.path.abspath(match.group(1).strip()))),
                    (r'Writing video metadata as JSON to: (.*)$', lambda match: ('json_metadata_path', os.path.abspath(match.group(1).strip()))),
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
                        elif result_type == 'json_metadata_path':
                            output_json_metadata = result
                            xbmc.log(f"yt-dlp_to_kodi: output json metadata => {output_json_metadata}", level=xbmc.LOGINFO)
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

                if ADDON.getSetting('save_nfo') == "true":
                    xbmc.log(f"yt-dlp_to_kodi: json: {output_json_metadata}", level=xbmc.LOGERROR)
                    if os.path.exists(output_json_metadata):
                        output_directory = os.path.dirname(output_filename)
                        output_base_name = os.path.splitext(os.path.basename(output_filename))[0]
                        output_nfo_path = os.path.join(output_directory, output_base_name + '.nfo')
                        generate_nfo(output_json_metadata, output_nfo_path)
                        os.remove(output_json_metadata)

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
    cache_path = get_cache_path()
    xbmc.log(f"yt-dlp_to_kodi: cache_path: {cache_path}", level=xbmc.LOGDEBUG)
    item = xbmcgui.ListItem(label='Cached videos')
    url = f"{plugin_url}?action=browse_cache&path={urllib.parse.quote_plus(cache_path)}"
    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=True)
    item = xbmcgui.ListItem(label='Settings')
    url = f"{plugin_url}?action=open_settings"
    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)
    debug = ADDON.getSetting('debug')
    if debug == 'true':
        item = xbmcgui.ListItem(label='Debug tests')
        url = f"{plugin_url}?action=show_debug_tests_submenu"
        xbmcplugin.addDirectoryItem(handle, url, item, isFolder=True)
    xbmcplugin.endOfDirectory(handle)

def show_addon_debug_tests_submenu():
    item = xbmcgui.ListItem(label='Test [youtube] video')
    info = item.getVideoInfoTag()
    info.setTitle("Test [youtube] video")
    url = f"{plugin_url}?action=process&url={urllib.parse.quote_plus(EXAMPLE_VIDEO_YOUTUBE_URL)}"
    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)
    item = xbmcgui.ListItem(label='Test [twitch] video')
    info = item.getVideoInfoTag()
    info.setTitle("Test [twitch] video")
    url = f"{plugin_url}?action=process&url={urllib.parse.quote_plus(EXAMPLE_VIDEO_TWITCH_URL)}"
    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)
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
        elif args['action'][0] == 'show_debug_tests_submenu':
            show_addon_debug_tests_submenu()
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
