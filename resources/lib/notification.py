# resources/lib/notification.py

import xbmcgui

from .const import DEFAULT_NOTIFICATION_MILLISECONDS

def xmbc_notification_info(message):
    xbmcgui.Dialog().notification(
        heading="yt-dlp_to_kodi",
        message = message,
        icon=xbmcgui.NOTIFICATION_INFO,
        time=DEFAULT_NOTIFICATION_MILLISECONDS
    )

def xmbc_notification_error(message):
    xbmcgui.Dialog().notification(
        heading="yt-dlp_to_kodi",
        message = message,
        icon=xbmcgui.NOTIFICATION_ERROR,
        time=DEFAULT_NOTIFICATION_MILLISECONDS
    )
