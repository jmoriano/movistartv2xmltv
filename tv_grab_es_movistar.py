#!/usr/bin/env python
# TO DO:
# - Fixing encoding and parsing issues
# - Adding tv_grab standard options
# - Using a temporary file to save user province, channels and epg days, so we save time in each execution

# Stardard tools
import sys
import os
import re
import logging
import json


# Time handling
import time
import datetime
from datetime import timedelta

# XML
import urllib

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree

from tva import TvaStream, TvaParser

logger = logging.getLogger('movistarxmltv'+str(os.getpid()))
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('/tmp/movistar.log')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

reload(sys)

SOCK_TIMEOUT = 3
FILE_XML = '/tmp/tv_grab_es_movistar.xml'
FILE_M3U = '/tmp/tv_grab_es_movistar'
FILE_LOG = '/tmp/tv_grab_es_movistar.log'

clientprofile = json.loads(urllib.urlopen("http://172.26.22.23:2001/appserver/mvtv.do?action=getClientProfile").read())['resultData']
platformprofile = json.loads(urllib.urlopen("http://172.26.22.23:2001/appserver/mvtv.do?action=getPlatformProfile").read())['resultData']
DEMARCATION =  clientprofile["demarcation"]
TVPACKAGES = clientprofile["tvPackages"].split("|")
MCAST_GRP_START = platformprofile["dvbConfig"]["dvbEntryPoint"].split(":")[0]
MCAST_PORT = int(platformprofile["dvbConfig"]["dvbEntryPoint"].split(":")[1])
logger.info("Init. DEM="+str(DEMARCATION)+" TVPACKS="+str(TVPACKAGES)+" ENTRY_MCAST="+MCAST_GRP_START+":"+str(MCAST_PORT))


ENCODING_EPG = 'utf-8'
DECODING_EPG = 'latin1'
ENCODING_SYS = sys.getdefaultencoding()
sys.setdefaultencoding(ENCODING_EPG)


if len(sys.argv) > 1:
#    if str(sys.argv[1]) == "--description" or  str(sys.argv[1]) == "-d":
    day = sys.argv[1]
    FILE_XML = '/tmp/tv_grab_es_movistar_'+str(day)+'.xml'
else:
    print "Usage: "+ sys.argv[0]+' [DAY NUMBER(0 today)]'
    exit()


# Example, for debugging purpose only
programmes = [{'audio': {'stereo': u'stereo'},
                   'category': [(u'Biz', u''), (u'Fin', u'')],
                   'channel': u'C23robtv.zap2it.com',
                   'date': u'2003',
                   'start': u'20030702000000 ADT',
                   'stop': u'20030702003000 ADT',
                   'title': [(u'This Week in Business', u'')]},
                  {'audio': {'stereo': u'stereo'},
                   'category': [(u'Comedy', u'')],
                   'channel': u'C36wuhf.zap2it.com',
                   'country': [(u'USA', u'')],
                   'credits': {'producer': [u'Larry David'], 'actor': [u'Jerry Seinfeld']},
                   'date': u'1995',
                   'desc': [(u'In an effort to grow up, George proposes marriage to former girlfriend Susan.',
                             u'')],
                   'episode-num': (u'7 . 1 . 1/1', u'xmltv_ns'),
                   'language': (u'English', u''),
                   'last-chance': (u'Hah!', u''),
                   'length': {'units': u'minutes', 'length': '22'},
                   'new': True,
                   'orig-language': (u'English', u''),
                   'premiere': (u'Not really. Just testing', u'en'),
                   'previously-shown': {'channel': u'C12whdh.zap2it.com',
                                        'start': u'19950921103000 ADT'},
                   'rating': [{'icon': [{'height': u'64',
                                         'src': u'http://some.ratings/PGicon.png',
                                         'width': u'64'}],
                               'system': u'VCHIP',
                               'value': u'PG'}],
                   'star-rating': {'icon': [{'height': u'32',
                                             'src': u'http://some.star/icon.png',
                                             'width': u'32'}],
                                   'value': u'4/5'},
                   'start': u'20030702000000 ADT',
                   'stop': u'20030702003000 ADT',
                   'sub-title': [(u'The Engagement', u'')],
                   'subtitles': [{'type': u'teletext', 'language': (u'English', u'')}],
                   'title': [(u'Seinfeld', u'')],
                   'url': [(u'http://www.nbc.com/')],
                   'video': {'colour': True, 'aspect': u'4:3', 'present': True,
                             'quality': 'standard'}}]


# Main starts

demarcationstream = TvaStream(MCAST_GRP_START,MCAST_PORT)
demarcationstream.getfiles()
demarcationxml = demarcationstream.files()["1_0"]
logger.info("Getting channels source for DEM: "+str(DEMARCATION))
MCAST_CHANNELS = TvaParser(demarcationxml).get_mcast_demarcationip(DEMARCATION)

logger.info("Getting channels list from: "+MCAST_CHANNELS)
now = datetime.datetime.now()
OBJ_XMLTV = ET.Element("tv" , {"date":now.strftime("%Y%m%d%H%M%S"),"source_info_url":"https://go.tv.movistar.es","source_info_name":"Grabber for internal multicast of MovistarTV","generator_info_name":"python-xml-parser","generator_info_url":"http://wiki.xmltv.org/index.php/XMLTVFormat"})
#OBJ_XMLTV = ET.Element("tv" , {"date":now.strftime("%Y%m%d%H%M%S")+" +0200"})

channelsstream = TvaStream(MCAST_CHANNELS,MCAST_PORT)
channelsstream.getfiles()
xmlchannels = channelsstream.files()["2_0"]
xmlchannelspackages = channelsstream.files()["5_0"]

channelparser = TvaParser(xmlchannels)
rawclist = {}
rawclist = channelparser.channellist(rawclist)

channelspackages = {}
channelspackages = TvaParser(xmlchannelspackages).getpackages()

clist = {}
for package in TVPACKAGES:
  for channel in channelspackages[package].keys():
    clist[channel] = rawclist[channel]
    clist[channel]["order"] = channelspackages[package][channel]["order"]
  
channelsm3u = channelparser.channels2m3usimple(clist)
if os.path.isfile(FILE_M3U+"_client.m3u"):
      os.remove(FILE_M3U+"_client.m3u")
fM3u = open(FILE_M3U+"_client.m3u", 'w+')
fM3u.write(channelsm3u)
fM3u.close
    


OBJ_XMLTV = channelparser.channels2xmltv(OBJ_XMLTV,rawclist)

i=int(day)+132
logger.info("\nReading day " + str(i - 132) +"\n")
epgstream = TvaStream('239.0.2.'+str(i),MCAST_PORT)
epgstream.getfiles()
for i in epgstream.files().keys():
    logger.info("Parsing "+i)
    epgparser = TvaParser(epgstream.files()[i])
    epgparser.parseepg(OBJ_XMLTV,rawclist)

# A standard grabber should print the xmltv file to the stdout
ElementTree(OBJ_XMLTV).write(FILE_XML,encoding="UTF-8")
print "Grabbed "+ str(len(OBJ_XMLTV.findall('channel'))) +" channels and "+str(len(OBJ_XMLTV.findall('programme')))+" programmes"

exit()
