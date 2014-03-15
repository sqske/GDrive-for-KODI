'''
    gdrive XBMC Plugin
    Copyright (C) 2013 dmdsoftware

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from resources.lib import gdrive
import sys
import urllib
import cgi
import re

import xbmc, xbmcgui, xbmcplugin, xbmcaddon


#helper methods
def log(msg, err=False):
    if err:
        xbmc.log(addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGERROR)
    else:
        xbmc.log(addon.getAddonInfo('name') + ': ' + msg, xbmc.LOGDEBUG)

def parse_query(query):
    queries = cgi.parse_qs(query)
    q = {}
    for key, value in queries.items():
        q[key] = value[0]
    q['mode'] = q.get('mode', 'main')
    return q

def addVideo(url, infolabels, label, img='', fanart='', total_items=0,
                   cm=[], cm_replace=False):
    infolabels = decode_dict(infolabels)
    log('adding video: %s - %s' % (infolabels['title'], url))
    listitem = xbmcgui.ListItem(label, iconImage=img,
                                thumbnailImage=img)
    listitem.setInfo('video', infolabels)
    listitem.setProperty('IsPlayable', 'true')
    listitem.setProperty('fanart_image', fanart)
    if cm:
        listitem.addContextMenuItems(cm, cm_replace)
    xbmcplugin.addDirectoryItem(plugin_handle, url, listitem,
                                isFolder=False, totalItems=total_items)

def addDirectory(url, title, img='', fanart='', total_items=0):
    log('adding dir: %s - %s' % (title, url))
    listitem = xbmcgui.ListItem(decode(title), iconImage=img, thumbnailImage=img)
    if not fanart:
        fanart = addon.getAddonInfo('path') + '/fanart.jpg'
    listitem.setProperty('fanart_image', fanart)
    xbmcplugin.addDirectoryItem(plugin_handle, url, listitem,
                                isFolder=True, totalItems=total_items)

#http://stackoverflow.com/questions/1208916/decoding-html-entities-with-python/1208931#1208931
def _callback(matches):
    id = matches.group(1)
    try:
        return unichr(int(id))
    except:
        return id

def decode(data):
    return re.sub("&#(\d+)(;|(?=\s))", _callback, data).strip()

def decode_dict(data):
    for k, v in data.items():
        if type(v) is str or type(v) is unicode:
            data[k] = decode(v)
    return data



#global variables
plugin_url = sys.argv[0]
plugin_handle = int(sys.argv[1])
plugin_queries = parse_query(sys.argv[2][1:])

addon = xbmcaddon.Addon(id='plugin.video.gdrive')

try:

    remote_debugger = addon.getSetting('remote_debugger')
    remote_debugger_host = addon.getSetting('remote_debugger_host')

    # append pydev remote debugger
    if remote_debugger == 'true':
        # Make pydev debugger works for auto reload.
        # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
        import pysrc.pydevd as pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace(remote_debugger_host, stdoutToServer=True, stderrToServer=True)
except ImportError:
    log(addon.getLocalizedString(30016), True)
    sys.exit(1)
except :
    pass


# retrieve settings
username = addon.getSetting('username')
password = addon.getSetting('password')
auth_writely = addon.getSetting('auth_writely')
auth_wise = addon.getSetting('auth_wise')
user_agent = addon.getSetting('user_agent')
save_auth_token = addon.getSetting('save_auth_token')
promptQuality = addon.getSetting('prompt_quality')
useWRITELY = addon.getSetting('force_writely')

if useWRITELY == 'true':
    useWRITELY = True
else:
    useWRITELY = False


mode = plugin_queries['mode']

# allow for playback of public videos without authentication
if (mode.lower() == 'streamurl'):
  authenticate = False
else:
  authenticate = True

# you need to have at least a username&password set or an authorization token
if ((username == '' or password == '') and (auth_writely == '' and auth_wise == '') and (authenticate == True)):
    xbmcgui.Dialog().ok(addon.getLocalizedString(30000), addon.getLocalizedString(30015))
    log(addon.getLocalizedString(30015), True)
    xbmcplugin.endOfDirectory(plugin_handle)


#let's log in
gdrive = gdrive.gdrive(username, password, auth_writely, auth_wise, user_agent, authenticate, useWRITELY)

# if we don't have an authorization token set for the plugin, set it with the recent login.
#   auth_token will permit "quicker" login in future executions by reusing the existing login session (less HTTPS calls = quicker video transitions between clips)
if auth_writely == '' and save_auth_token == 'true':
    addon.setSetting('auth_writely', gdrive.writely)
    addon.setSetting('auth_wise', gdrive.wise)


log('plugin google authorization: ' + gdrive.getHeadersEncoded())
log('plugin url: ' + plugin_url)
log('plugin queries: ' + str(plugin_queries))
log('plugin handle: ' + str(plugin_handle))


#dump a list of videos available to play
if mode.lower() == 'main':
    log(mode)

    cacheType = addon.getSetting('playback_type')

    if cacheType == '0':
      videos = gdrive.getVideosList()
    else:
      videos = gdrive.getVideosList(True,2)

    # if results will generate further input (quality type, we use directories, otherwise add results as videos)
    if cacheType != '0' or promptQuality == 'true':
      for title in sorted(videos.iterkeys()):
        addDirectory(videos[title],title)
    else:
      for title in sorted(videos.iterkeys()):
          addVideo(videos[title],
                             { 'title' : title , 'plot' : title }, title,
                             img='None')

#play a URL that is passed in (presumably requires authorizated session)
elif mode.lower() == 'play':
    url = plugin_queries['url']

    item = xbmcgui.ListItem(path=url+'|'+gdrive.getHeadersEncoded(useWRITELY))
    log('play url: ' + url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

#play a video given its exact-title
elif mode.lower() == 'playvideo':
    title = plugin_queries['title']
    cacheType = addon.getSetting('playback_type')

    if cacheType == '0':
      videoURL = gdrive.getVideoLink(title)
    else:
      videoURL = gdrive.getVideoLink(title,True,cacheType)

    #effective 2014/02, video stream calls require a wise token instead of writely token
    videoURL = videoURL + '|' + gdrive.getHeadersEncoded(useWRITELY)

    item = xbmcgui.ListItem(path=videoURL)
    log('play url: ' + videoURL)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

#force memory-cache - play a video given its exact-title
elif mode.lower() == 'memorycachevideo':
    title = plugin_queries['title']
    videoURL = gdrive.getVideoLink(title)

    #effective 2014/02, video stream calls require a wise token instead of writely token
    videoURL = videoURL + '|' + gdrive.getHeadersEncoded(useWRITELY)

    item = xbmcgui.ListItem(path=videoURL)
    log('play url: ' + videoURL)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)


#force stream - play a video given its exact-title
elif mode.lower() == 'streamvideo':
    try:
      title = plugin_queries['title']
    except:
      title = 0

    # check for promptQuality override
    try:
      promptQuality = plugin_queries['promptQuality']
    except:
      promptQuality = 'false'


    # result will be a list of streams
    if promptQuality == 'true':
      videos = gdrive.getVideoLink(title, True, 2)

      for label in videos.iterkeys():
          addVideo(videos[label]+'|'+gdrive.getHeadersEncoded(useWRITELY),
                             { 'title' : title , 'plot' : title },label,
                             img='None')
    # immediately play resulting (is a video)
    else:
      videoURL = gdrive.getVideoLink(title, False, 2)

      #effective 2014/02, video stream calls require a wise token instead of writely token
      videoURL = videoURL + '|' + gdrive.getHeadersEncoded(useWRITELY)

      item = xbmcgui.ListItem(path=videoURL)
      log('play url: ' + videoURL)
      xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

elif mode.lower() == 'streamurl':
    url = plugin_queries['url']

    videoURL = gdrive.getPublicStream(url)
    item = xbmcgui.ListItem(path=videoURL)
    log('play url: ' + videoURL)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

#clear the authorization token
elif mode.lower() == 'clearauth':
    addon.setSetting('auth_writely', '')
    addon.setSetting('auth_wise', '')

# if we don't have an authorization token set for the plugin, set it with the recent login.
#   auth_token will permit "quicker" login in future executions by reusing the existing login session (less HTTPS calls = quicker video transitions between clips)
# update the authorization token in the configuration file if we had to login for a new one during this execution run
if auth_writely != gdrive.writely and save_auth_token == 'true':
    addon.setSetting('auth_writely', gdrive.writely)
    addon.setSetting('auth_wise', gdrive.wise)

xbmcplugin.endOfDirectory(plugin_handle)

