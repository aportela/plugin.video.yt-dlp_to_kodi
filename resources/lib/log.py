# resources/lib/log.py

import xbmc

def xmbc_log_debug(str):
    xbmc.log(str, level=xbmc.LOGDEBUG)

def xmbc_log_error(str):
    xbmc.log(str, level=xbmc.LOGERROR)
