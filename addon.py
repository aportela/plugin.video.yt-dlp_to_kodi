import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import urllib.parse
import sys

plugin_url = sys.argv[0]
handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

def main():
    if 'action' in args:
        if args['action'][0] == 'open_settings':
            xbmc.executebuiltin(f"Addon.OpenSettings({xbmcaddon.Addon().getAddonInfo('id')})")
            return
    else:
        settings_item = xbmcgui.ListItem(label='Open settings')
        settings_url = f"{plugin_url}?action=open_settings"
        xbmcplugin.addDirectoryItem(handle, settings_url, settings_item, isFolder=False)
        xbmcplugin.endOfDirectory(handle)

if __name__ == '__main__':
    main()
