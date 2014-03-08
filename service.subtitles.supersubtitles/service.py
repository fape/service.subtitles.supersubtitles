# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import shutil
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin,shutil
import unicodedata
import requests
import simplejson
import os.path
import re

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
#__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

BASE_URL='http://www.feliratok.info/index.php'

TAGS= {
  'WEB\-DL', 
  'PROPER', 
  'REPACK'
}

QUALITIES={
  '720p',
  '1080p',
  'DVDRip',
  'BRRip',
  'BDRip'
}

RELEASERS={
  '2HD',
  'AFG',
  'ASAP',
  'BiA',
  'DIMENSION',
  'EVOLVE',
  'FoV',
  'FQM',
  'IMMERSE',
  'KiNGS',
  'LOL',
  'ORENJI',
  'TLA'
}
HEADERS = { 'User-Agent': 'xbmc subtitle plugin' }

if xbmcvfs.exists(__temp__):
  shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

#sys.path.append (__resource__)

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def lang_hun2eng(hunlang):
  languages = {
    "albán"    : "Albanian",
    "arab"     : "Arabic",
    "bolgár"   : "Bulgarian",
    "kínai"    : "Chinese",
    "horvát"   : "Croatian",
    "cseh"     : "Czech",
    "dán"      : "Danish",
    "holland"  : "Dutch",
    "angol"    : "English",
    "észt"     : "Estonian",
    "finn"     : "Finnish",
    "francia"  : "French",
    "német"    : "German",
    "görög"    : "Greek",
    "héber"    : "Hebrew",
    "hindi"    : "Hindi",
    "magyar"   : "Hungarian",
    "olasz"    : "Italian",
    "japán"    : "Japanese",
    "koreai"   : "Korean",
    "lett"     : "Latvian",
    "litván"   : "Lithuanian",
    "macedón"  : "Macedonian",
    "norvég"   : "Norwegian",
    "lengyel"  : "Polish",
    "portugál" : "Portuguese",
    "román"    : "Romanian",
    "orosz"    : "Russian",
    "szerb"    : "Serbian",
    "szlovák"  : "Slovak",
    "szlovén"  : "Slovenian",
    "spanyol"  : "Spanish",
    "svéd"     : "Swedish",
    "török"    : "Turkish",
  }
  return languages[ hunlang.lower() ] 


def log(msg):
  xbmc.log((u"### [%s] - %s" % (__scriptname__ ,msg,)).encode('utf-8'),level=xbmc.LOGNOTICE ) 

def errorlog(msg):
  xbmc.log((u"### [%s] - %s" % (__scriptname__ ,msg,)).encode('utf-8'),level=xbmc.LOGERROR )

def debuglog(msg):
  xbmc.log((u"### [%s] - %s" % (__scriptname__ ,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def queryData(params):
  r=requests.get(BASE_URL,params=params, headers=HEADERS)
  log(r.url)
  try:
    return r.json()
  except ValueError as e:
    errorlog(e.message)
    return None

def getId(term):
  params = {'action': 'autoname', 'nyelv': 'Angol', 'term': term}
  data = queryData(params)
  if data:
    return data[0]['ID']
  else:
    return None

def convert(item): 
  ret = {'filename': item['fnev'], 
         'name': item['nev'],
         'language_hun' : item['language'],
         'id' : item['felirat'],
         'uploader': item['feltolto'],
         'hearing' : False}
  ret['language_eng'] = lang_hun2eng(item['language'])
  score = int(item['pontos_talalat'], 2)
  ret['rating'] = str(score*5/7)
  ret['sync'] = score >= 6
  ret['hearing']=False
  ret['flag'] = xbmc.convertLanguage(ret['language_eng'],xbmc.ISO_639_1)
  return ret

def setParamIfFilenameContains(data, params, paramname, items):
  compare=data['filename'].lower()
  for item in items:
    if item.lower() in compare:
      params[paramname]=item
      return item
  return None

def search_subtitles(item):
  id=getId(item['tvshow'])
  if not id:
    debuglog("No id found for %s" % item['tvshow'])
    return None
 
  params = { 'action' : 'xbmc', 'sid': id, 'ev': item['season'], 'rtol': item['episode']};
  
  setParamIfFilenameContains(item, params, 'relj', TAGS)
  setParamIfFilenameContains(item, params, 'relf', QUALITIES)
  setParamIfFilenameContains(item, params, 'relr', RELEASERS)

  data = queryData(params)
  
  if not data:
    debuglog("No subtitle found for %s" % item['tvshow'])
    return None

  searchlist  = []
  for st in data.values():
    searchlist.append(convert(st))

  searchlist.sort(key=lambda k: k['rating'], reverse=True)
  return searchlist

def Search(item): 
  subtitles_list = search_subtitles(item) 

  if subtitles_list:
    for it in subtitles_list:
      label="%s [%s]"%(it['filename'], it['uploader'])
      listitem = xbmcgui.ListItem(label=it["language_eng"],
            label2="%s [%s]"%(it['filename'], it['uploader']),
            iconImage=it["rating"],
            thumbnailImage= it["flag"] 
            )
      listitem.setProperty( "sync", ("false", "true")[it["sync"]] )
      listitem.setProperty( "hearing_imp", ("false", "true")[it.get("hearing", False)] )
      
      params= {'action' : 'download', 'id' : it['id'], 'filename' : it['filename']}
      url="plugin://%s/?%s" % (__scriptid__, urllib.urlencode(params))
      
      xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)



def download_file(item):
  localfile=os.path.join(__temp__,item['filename'].decode("utf-8"))
  params={'action':'letolt', 'felirat': item['id']}
  r = requests.get(BASE_URL, params=params, headers=HEADERS, stream=True)
  with open(localfile, 'wb') as fd:
    for chunk in r.iter_content(chunk_size=1024):
      fd.write(chunk)
    fd.flush()
  return localfile

def Download(item):
  subtitle = download_file(item)
  listitem = xbmcgui.ListItem(label=subtitle)
  xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=subtitle,listitem=listitem,isFolder=False)
  
   
def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string 
  if len(paramstring)>=2:
    params=paramstring
    cleanedparams=params.replace('?','')
    if (params[len(params)-1]=='/'):
      params=params[0:len(params)-2]
    pairsofparams=cleanedparams.split('&')
    param={}
    for i in range(len(pairsofparams)):
      splitparams={}
      splitparams=pairsofparams[i].split('=')
      if (len(splitparams))==2:
        param[splitparams[0]]=splitparams[1]
          
  return param

params = get_params()

if params['action'] == 'search':
  log("action 'search' called")
  item = {}
  item['temp']    = False
  item['rar']     = False
  item['stack']   = False
  item['year']    = xbmc.getInfoLabel("VideoPlayer.Year")   # Year
  item['season']  = str(xbmc.getInfoLabel("VideoPlayer.Season"))       # Season
  item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))      # Episode
  item['tvshow']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
  item['title']   = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
  item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
  item['3let_language']      = [] #['scc','eng']
  
  for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
    clang = xbmc.convertLanguage(lang,xbmc.ISO_639_2);
    log("lang: %s, clang: %s" % (lang, clang))
    item['3let_language'].append(lang)
  
  if item['title'] == "":
    log("VideoPlayer.OriginalTitle not found")
    item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title
    
  if item['episode'].lower().find("s") > -1:     # Check if season is "Special"
    item['season'] = "0"              #
    item['episode'] = item['episode'][-1:]
  
  if ( item['file_original_path'].find("http") > -1 ):
    item['temp'] = True

  elif ( item['file_original_path'].find("rar://") > -1 ):
    item['rar']  = True
    item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

  elif ( item['file_original_path'].find("stack://") > -1 ):
    item['stack']  = True
    stackPath = item['file_original_path'].split(" , ")
    item['file_original_path'] = stackPath[0][8:]

  item['filename']=os.path.basename(item['file_original_path'])

  if not item['tvshow'] :
     title = xbmc.getCleanMovieTitle(item['file_original_path'])[0];
     pattern = r'^(?P<title>.+)S(?P<season>\d+)E(?P<episode>\d+)$'
     match = re.search(pattern,title, re.I)
     item['tvshow']=match.group('title').strip()
     item['season']=match.group('season')
     item['episode']=match.group('episode')
  
  Search(item)
	
elif params['action'] == 'download':
  item={'id': params['id'], 'filename':params['filename']}
  Download(item)
  

elif params['action'] == 'manualsearch':
  xbmc.executebuiltin(u'Notification(%s,%s,2000,%s)' % 
     (__scriptname__,
      __language__(32004),
      os.path.join(__cwd__,"icon.png")
    )
           )
  
xbmcplugin.endOfDirectory(int(sys.argv[1]))
  
  
  
  
  
  
  
  
  
    
