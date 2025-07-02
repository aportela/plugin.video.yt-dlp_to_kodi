# resources/lib/ytdlp_task.py

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui

import os
import threading
import subprocess
import re

from .const import *

from .nfo_generator import generate_nfo

def process_url(cache_path, url, append_to_playlist):

    if not os.path.exists(cache_path):
        xbmc.log(f"yt-dlp_to_kodi: process_url() -> path not found: {cache_path}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = f"{ADDON.getLocalizedString(30021)}: {cache_path}", icon = xbmcgui.NOTIFICATION_ERROR, time = DEFAULT_NOTIFICATION_MILLISECONDS)
        return
    else:

        if SHOW_ADDON_BIG_DIALOG:
            dialog = xbmcgui.DialogProgress()
            dialog.create("yt-dlp to kodi", f"{ADDON.getLocalizedString(30028)}: {url}")

        def ytdlp_download_to_cache_and_process():
            xbmc.log(f"yt-dlp_to_kodi: using url {url}", level=xbmc.LOGINFO)
            COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE = f'{cache_path}{"" if cache_path.endswith(os.sep) else os.sep }%(webpage_url_domain)s/%(uploader)s - %(uploader_id)s/%(upload_date)s - %(title)s - %(id)s - %(height)sp - - %(vcodec)s - %(acodec)s.%(ext)s'
            COMMAND_LINE_MAX_VIDEO_HEIGHT=int(ADDON.getSetting('max_resolution')) or 1080

            output_filename = ""
            output_thumbnail = ""
            output_json_metadata = ""
            unsupported_url = False

            # TODO:
            # MARKETS/CHAPTERS --parse-chapters --merge-output-format mkv
            commandline = [
                'yt-dlp',
                # Ignore warnings
                #'--no-warnings',
                '--verbose',
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
                # Download only the video, if the URL refers to a video and a playlist
                '--no-playlist',
                # Resume partially downloaded files/fragments (default)
                '--continue',
                # Output filename template; see "OUTPUT TEMPLATE" for details
                '-o', COMMAND_LINE_PARAM_OUTPUT_TEMPLATE_VALUE,
                # main URL
                url
            ]

            if ADDON.getSetting('save_subtitles') == "true":
                commandline.insert((len(commandline) - 1), '--write-subs')
                commandline.insert((len(commandline) - 1), '--write-auto-subs')
                commandline.insert((len(commandline) - 1), '--sub-lang')
                #commandline.insert((len(commandline) - 1), xbmc.getLanguage().split('_')[0])
                commandline.insert((len(commandline) - 1), 'en')
                #commandline.insert((len(commandline) - 1), '--convert-subs')
                #commandline.insert((len(commandline) - 1), 'srt')

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

                xbmc.log(f"yt-dlp_to_kodi: {output_line}", level=xbmc.LOGERROR)

                patterns = [
                    (r'\[download\]\s*(\d+\.\d+)%', lambda match: ('percent', float(match.group(1)))),
                    (r'\[Merger\] Merging formats into "(.*)"$', lambda match: ('merger', os.path.abspath(match.group(1).strip()))),
                    (r'\[info\] Writing video thumbnail \d+ to: (.*)$', lambda match: ('thumbnail_path', os.path.abspath(match.group(1).strip()))),
                    (r'Writing video metadata as JSON to: (.*)$', lambda match: ('json_metadata_path', os.path.abspath(match.group(1).strip()))),
                    (r'\[download\] (.*) has already been downloaded$', lambda match: ('already_downloaded', os.path.abspath(match.group(1).strip()))),
                    (r'\[FixupM3u8\] Fixing MPEG-TS in MP4 container of "(.*)"$', lambda match: ('fixup', os.path.abspath(match.group(1).strip()))),
                ]

                for pattern, action in patterns:
                    match = re.search(pattern, output_line)
                    if match:
                        result_type, result = action(match)
                        if result_type == 'percent':
                            percent = result
                            if SHOW_ADDON_BIG_DIALOG:
                                dialog.update(int(percent), f"{ADDON.getLocalizedString(30029)}: {percent:.2f}%")
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
                        break
                xbmc.sleep(100)

            error_patterns = [
                (r'Error: (.*)$', lambda match: ('error', match.group(1)))
            ]

            for error_line in yt_dlp_proc.stderr:
                unsupported_url = True
                xbmc.log(f"yt-dlp_to_kodi: {error_line}", level=xbmc.LOGERROR)
                for pattern, action in error_patterns:
                    match = re.search(pattern, error_line)
                    if match:
                        result_type, result = action(match)
                        if result_type == 'unsupported_url':
                            unsupported_url = True

            yt_dlp_proc.communicate()

            if SHOW_ADDON_BIG_DIALOG:
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

                xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = ADDON.getLocalizedString(30022), icon = xbmcgui.NOTIFICATION_INFO, time = DEFAULT_NOTIFICATION_MILLISECONDS)

                if os.path.exists(output_filename):
                    file = output_filename.replace('\\', '/') # REQUIRED ?
                    xbmc.log(f"yt-dlp: playing: {file}", level=xbmc.LOGINFO)
                    player = xbmc.Player()
                    if append_to_playlist:
                        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                        playlist.add(file)
                        if not player.isPlaying():
                            player.play(playlist)
                    else:
                        player.play(file)
                else:
                    xbmc.log(f"yt-dlp_to_kodi: file not found {output_filename}", level=xbmc.LOGERROR)
                    xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = ADDON.getLocalizedString(30023), icon = xbmcgui.NOTIFICATION_ERROR, time = DEFAULT_NOTIFICATION_MILLISECONDS)
            else:
                xbmc.log(f"yt-dlp_to_kodi: download error", level=xbmc.LOGINFO)
                if unsupported_url is True:
                    xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = ADDON.getLocalizedString(30024), icon = xbmcgui.NOTIFICATION_WARNING, time = DEFAULT_NOTIFICATION_MILLISECONDS)
                else:
                    xbmcgui.Dialog().notification(heading = "yt-dlp_to_kodi", message = ADDON.getLocalizedString(30025), icon = xbmcgui.NOTIFICATION_ERROR, time = DEFAULT_NOTIFICATION_MILLISECONDS)


        threading.Thread(target=ytdlp_download_to_cache_and_process, daemon=True).start()
