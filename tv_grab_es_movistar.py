#!/usr/bin/env python
# Author: migeng (parsing and xmltv handling only)
# Other github authors: ese (channels grabbing from multicast to xml) and radioactivetoy (EPG grabbing from multicast to xml)
# Acknowleges: wiredrat, radioactivetoy, vuelo23, vsanz and other fellows of forum www.adslzone.net
# TO DO:
# - Fixing encoding and parsing issues
# - Adding tv_grab standard options
# - Using a temporary file to save user province, channels and epg days, so we save time in each execution 

# Stardard tools
import struct
import re
import sys
import os
import itertools

# Networking
import socket

# Time handling
import time
import datetime
from datetime import timedelta

# XML
import urllib
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree
import pprint
import binascii
from pprint import pprint

# XMLTV
import xmltv

reload(sys)

MCAST_GRP_START = '239.0.2.129'
MCAST_PORT = 3937
MCAST_CHANNELS = '239.0.2.140'
FILE_XML = '/tmp/tv_grab_es_movistar.xml' 
FILE_M3U = '/tmp/tv_grab_es_movistar.m3u'
FILE_LOG = '/tmp/tv_grab_es_movistar.log'


# Andalucia 15
# Aragon    34
# Asturias  13
# Cantabria 29
# Castilla# la# Mancha  38
# Castilla# y# Leon 4
# Cataluna  1
# Comunidad# Valenciana 6
# Extremadura   32
# Galicia   24
# Islas# Baleares   10
# Islas# Canarias   37
# La# Rioja 31
# Madrid    19
# Murcia    12
# Navarra   35
# Pais# Vasco   36
PROVINCE = '19'
ENCODING_EPG = 'utf-8'
DECODING_EPG = 'latin1'
ENCODING_SYS = sys.getdefaultencoding()
#print "The default system encoding is : " + ENCODING_SYS
sys.setdefaultencoding(ENCODING_EPG)
#ENCODING_SYS = sys.getdefaultencoding()
#print "The system encoding has been set to : " + ENCODING_SYS

if os.path.isfile(FILE_LOG):
    os.remove(FILE_LOG)
fLog = open(FILE_LOG, 'w+')


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


def getxmlprovince(MCAST_GRP,MCAST_PORT,PROVINCE):
    beginning=0
    end=0
    ipprovince=0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(3)
    sock.bind(('', MCAST_PORT))
    mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        d = sock.recv(8096000)
        regexp = re.compile("DEM_" + str(PROVINCE) +  "\..*?Address\=\\\"(.*?)\\\".*?",re.DOTALL)
        m = regexp.findall(d)

        if(re.findall("\<\?xml", d)):
            beginning=1

        if(beginning==1):
            if(re.findall("</ServiceDiscovery>",d)):
                end=1
            if(end==1):
                if m:
                    print m[0]
                    ipprovince = m[0]
                    print "IP Encontrada! ("+ ipprovince + ")"
                    return ipprovince
                    break
    return None


def getxmlchannels(MCAST_GRP,MCAST_PORT,OBJ_XMLTV,rootXmltv):
    beginning=0
    end=0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(3)
    sock.bind(('', MCAST_PORT))
    mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    lista=[]
    now = datetime.datetime.now()
    w = OBJ_XMLTV

    while (end == 0):
        d = sock.recv(8096000)
        regexp = re.compile("Port\=\\\"(.*?)\\\".*?Address\=\\\"(.*?)\\\" \/\>.*?imSer\/(.*?)\.jpg.*?Language\=\\\"ENG\\\"\>(.*?)\<\/Name\>",re.DOTALL)
        m = regexp.findall(d)
        if m:
            lista.append(m)

        if(re.findall("\<BroadcastDiscovery", d)):
            beginning=1

        if(beginning==1):
            if(re.findall("\<\/BroadcastDiscovery",d)):
                end=1
                lista = list(itertools.chain(*lista))
                lista.sort()
                # M3U file
                if os.path.isfile(FILE_M3U):
                    os.remove(FILE_M3U)
                fM3u = open(FILE_M3U, 'w+')
                fM3u.write("#EXTM3U\n")
                for i in range(0,len(lista)-1):
                    #print "Grabbing " + lista[i][3]
                    # M3U file
                    fM3u.write("#EXTINF:-1," + lista[i][3] + ' [' + lista[i][2] + ']\n')
                    fM3u.write("rtp://@" + lista[i][1] + ":" + str(lista[i][0]) + '\n')
                    # XMLTV file
                    cChannel = SubElement(rootXmltv,'channel',{"id": lista[i][2]+ ".imagenio.es"})
                    cName = SubElement(cChannel, "display-name", {"lang":"es"})
                    cName.text = lista[i][3]
    return rootXmltv


def getrawstream(MCAST_GRP,MCAST_PORT,packets):
	xmldata=""
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(3)
	sock.bind(('', MCAST_PORT))
	mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
	while (packets>0):
		data = sock.recv(1500)
		xmldata+=data
		packets-=1
	return xmldata

def getxmlepg(MCAST_GRP,MCAST_PORT,files,OBJ_XMLTV,rootXmltv):
        w = OBJ_XMLTV
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(3)
        sock.bind(('', MCAST_PORT))
        mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        end = 0
        now = datetime.datetime.now() 
        #Esperamos al end de una secuencia para comenzar por el beginning de un fichero
        while not (end):
            data = sock.recv(1500)
            end = struct.unpack('B',data[:1])[0]
            fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
            #Guardamos el id del fichero para reconocer el end del bucle
            lastfile = fileid

        #Bucle por el numero de ficheros indicado o hasta entrar en loop
        while (files>0):
                xmldata=""
                data = sock.recv(1500)

                #Estructura de cabeceras 12 primeros bytes
                # end   xmlsize     ???   ?  id         #Part*10   Partes totales     \0
                # --   --------   -----  ------  ----  ---------  -------------      --
                # 00   00 00 00    F1    X 0 00   00     00 00          00           00
                #FIXME: XMLsize print is incorrect
                end = struct.unpack('B',data[:1])[0]
                size = struct.unpack('>HB',data[1:4])[0]
                fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                chunk_total = struct.unpack('B',data[10:11])[0]

                #Omitimos las cabeceras binarias del fichero xml
                body=data[12:]
                # Si no es la ultima parte del fichero vamos concatenando
                while not (end):
#                        print("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                        xmldata+=body
                        data = sock.recv(1500)
                        end = struct.unpack('B',data[:1])[0]
                        size = struct.unpack('>HB',data[1:4])[0]
                        fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                        chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                        chunk_total = struct.unpack('B',data[10:11])[0]
                        body=data[12:]
                #print("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                #Omitimos los 4 ultimos bytes que quedan fuera del xml
                xmldata+=body[:-4]
#                file = open(MCAST_GRP+"/"+str(fileid)+".xml", "w")
                # Keeping the file for dubugging. TODO: no file, just we use the XML tree in memmory
                file = open("/tmp/programme.xml", "w+")
                file.write(xmldata)
                file.close()
                #print("File written")

                try:
                    tree = ET.parse('/tmp/programme.xml')
                except ET.ParseError, v:
                    row, column = v.position
                    fLog.write("\nError when opening /tmp/programme.xml\n")
                    fLog.write(str(ET.ParseError))
                    fLog.write("\nerror on row" + str(row) + "column" + str(column) + ":" + str(v) + "\n")
                    break
                root = tree.getroot()

                if root[0][0][0].get('serviceIDRef') is not None:
                    channelid = root[0][0][0].get('serviceIDRef') 

                for child in root[0][0][0]:
                    programme = {}
                    if child[0].get('crid') is not None:
                        programmeId = child[0].get('crid').split('/')[5]   # id for description
                    if child[1][1][0] is not None:
                        genre =  child[1][1][0].text #.encode(ENCODING_EPG).replace('\n', ' ') # Genre
                    #   20030702000000 XMLTV format
                    #   YYYYMMddHHmmss
                    #   2014-09-21T22:24:00.000Z IPTV multicast format
                    #   YYYY-MM-ddTHH:mm:ss.000Z
                    if child[2] is not None:
                        startTimeXml = child[2].text.replace('\n', ' ').replace('.000Z', '').replace('T', ' ') # Start time
                        startTimePy = datetime.datetime.strptime(startTimeXml,'%Y-%m-%d %H:%M:%S')
                        startTime = startTimePy.strftime('%Y%m%d%H%M%S') 

                    durationXml = child[3].text.replace('\n', ' ').replace('PT','') # Duration
                    if durationXml.find('H') > 0 and durationXml.find('M') > 0:
                        durationPy = datetime.datetime.strptime(durationXml,'%HH%MM')
                    elif durationXml.find('H') > 0 and durationXml.find('M') < 0:
                        durationPy = datetime.datetime.strptime(durationXml,'%HH')
                    elif durationXml.find('H') < 0 and durationXml.find('M') > 0:
                        durationPy = datetime.datetime.strptime(durationXml,'%MM')
                    else:
                        durationPy = None

                    durationPy = 60 * int(durationPy.strftime('%H')) + int(durationPy.strftime('%M'))
                    duration = str(durationPy)#.encode(ENCODING_EPG) # Duration or length
                    stopTimePy = startTimePy + timedelta(minutes=durationPy)
                    stopTime = stopTimePy.strftime('%Y%m%d%H%M%S')#.encode(ENCODING_EPG) # Stop time

                    url ='http://www-60.svc.imagenio.telefonica.net:2001/appserver/mvtv.do?action=getEpgInfo&extInfoID='+ programmeId +'&tvWholesaler=1'
                    strProgramme = urllib.urlopen(url).read().replace('\n',' ') #.decode(DECODING_EPG).encode(ENCODING_EPG)
                    #   Genre can be also got from the extra information
                    #    s = strProgramme[:]
                    #    genre = s.split('"genre":"')[1].split('","')[0] # Genre
                    s = strProgramme[:]
                    if s.find("productionDate")>0:
                        year = s.split('"productionDate":["')[1].split('"],"')[0] # Year
                    else:
                        year = None
                    s = strProgramme[:]
                    fullTitle = child[1][0].text #.encode(ENCODING_EPG)

                    s = fullTitle[:].replace('\n',' ')
                    m = re.search(r"(.*?) T(\d+) Cap. (\d+)", s)
                    title = ""
                    if m:
                        title = m.group(1) # title
                        season = m.group(2) # season
                        episode = m.group(3) # episode
                    elif s.find(': Episodio ') > 0 :
                        episode = s.split(': Episodio ')[1].split('"')[0] # Episode
                        season = 0
                        title = s.split(': Episodio ')[0] # Title
                    else:
                        episode = None
                        season = None
                        title = fullTitle[:]
#                    title = child[1][0].text #.encode(ENCODING_EPG)

                    if len(title) < 3:
                        fLog.write("\nToo short title: " + s + " / " + title +"\n")
                        break
                    title = title.replace('\n',' ').encode(ENCODING_EPG)
                    s = strProgramme[:]
                    if s.find('"description":"')>0:
                        description = s.split('"description":"')[1].split('","')[0] #.decode(DECODING_EPG,'xmlcharrefreplace').encode(ENCODING_EPG,'xmlcharrefreplace') # Description
 
                    s = strProgramme[:]
                    if s.find('"subgenre":"')>0:
                        subgenre =  s.split('"subgenre":"')[1].split('","')[0] #.encode(ENCODING_EPG) # Subgenre

                    programme['date'] = year
                    programme['length'] = {'units': 'minutes', 'length': duration}
                    # Creating XMLTV with XML libraries instead XMLTV
                    cProgramme = SubElement(rootXmltv,'programme', {"start":startTime+" +0200", "stop": stopTime+" +0200", "channel":channelid})
                    cTitle = SubElement(cProgramme, "title", {"lang":"es"})
                    cTitle.text = title.encode(ENCODING_EPG)
                    cDesc = SubElement(cProgramme, "desc", {"lang":"es"})
                    cDesc.text = description.encode(ENCODING_EPG)
                    cCategory = SubElement(cProgramme, "category", {"lang":"es"})
                    if len(genre) < 2:
                        fLog.write("\nToo short genre: " + genre +"\n")
                        fLog.write(str(strProgramme))
                        if genre == subgenre:
                            cCategory.text = subgenre
                        else:
                            cCategory.text = genre +", "+subgenre
                    if episode is not None:
                        cEpisode = SubElement(cProgramme, "episode-num")
                        cEpisode.text = "."+episode.encode(ENCODING_EPG)+"."
                    elif season is not None:
                        cEpisode = SubElement(cProgramme, "episode-num")
                        cEpisode.text = season.encode(ENCODING_EPG)+"."+episode.encode(ENCODING_EPG)+"."
                    if len(duration) > 0:
                        cDuration = SubElement(cProgramme, "length")
                        cDuration.text = duration.encode(ENCODING_EPG)


                # Si el fileid es el mismo que detectamos al beginning acabamos con el bucle.
                if (fileid == lastfile):
                    files = 1
                files-=1
        sock.close()

def getxmlfile(MCAST_GRP,MCAST_PORT,DISCNAME,ENDSTRING):
	# DISCNAME = xml tag that identifies the file
	# If DISCNAME="" then gets the first file
	# ENDSTRIG= string that ends a file
	xmldata=""
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(3)
	sock.bind(('', MCAST_PORT))
	mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
	while True:
		data = sock.recv(1500)
		start = data.find("<?xml")
		if(start!=-1):
			if(DISCNAME==""):
				isourservice=0
			else:
				isourservice=data.find(DISCNAME)
			if(isourservice!=-1):
				xmldata+=data[start:]
				#print data[start:],
				while True:
					data = sock.recv(1500)
					start = data.find(ENDSTRING)
					if(start!=-1):
						xmldata+=data[12:start+len(ENDSTRING)]
						#print data[13:start+19],
						return(xmldata)
					else:
						xmldata+=data[12:]
					#print data[13:],


def parsechannelxml(xmldata):
	clist=[]
	root = ET.fromstring(xmldata)
	for channel in root.findall('.//{urn:dvb:ipisdns:2006}SingleService'):
		mcaddr=channel.find('.//{urn:dvb:ipisdns:2006}IPMulticastAddress')
		port=mcaddr.get('Port')
		ip=mcaddr.get('Address')
		shortname=channel.find('.//{urn:dvb:ipisdns:2006}ShortName').text
		name=channel.find('.//{urn:dvb:ipisdns:2006}Name').text
		#genre=channel.find('.//{urn:dvb:ipisdns:2006}urn:Name').text
		genre=""
		textualid=channel.find('.//{urn:dvb:ipisdns:2006}TextualIdentifier')
		servicename=textualid.get('ServiceName')
		logouri=textualid.get('logoURI')
		serviceinfo=channel.find('.//{urn:dvb:ipisdns:2006}SI').get('ServiceInfo')
		clist.append({'name':name,'shortname':shortname,'ip':ip,'port':port,'genre':genre,'servicename':servicename,'logouri':logouri,'serviceinfo':serviceinfo})
        #print clist
	return clist

def parseepgservicesxml(xmldata):
	slist=[]
	root = ET.fromstring(xmldata)
	bcg=root.find(".//{urn:dvb:ipisdns:2006}BCG[@Id='EPG']")
	for service in bcg.findall('.//{urn:dvb:ipisdns:2006}DVBSTP'):
		ip=service.get('Address')
		port=service.get('Port')
		source=service.get('Source')
		slist.append({'source':source,'ip':ip,'port':port})
	return slist


# Main starts
# TO-DO: Adding 7th day for EPG

#print "Looking for the ip of your province"
#ipprovince = getxmlprovince(MCAST_CHANNELS,MCAST_PORT,PROVINCE)
fLog.write("\nGetting channels list\n")
now = datetime.datetime.now()
w = xmltv.Writer(encoding=ENCODING_EPG,
                       date=str(now.strftime("%Y%m%d%H%M%S"))+" +0200",
                       source_info_url="https://go.tv.movistar.es/",
                       source_info_name="Grabber for internal multicast of MovistarTV",
                       generator_info_name="python-xmltv",
                       generator_info_url="/usr/lib/python2.7/dist-packages/xmltv.py")

#if os.path.isfile(FILE_XML):
#    tree = ET.parse(FILE_XML)
#    root = ET.fromstring("tv")
#    rootXmltv = tree.getroot()
#else:
rootXmltv = ET.Element("tv")
getxmlchannels(MCAST_CHANNELS,MCAST_PORT,w,rootXmltv)

for i in range(130,138):
#for i in range(137,138):
    fLog.write("\nReading day " + str(i - 132) +"\n")
    getxmlepg('239.0.2.'+str(i),MCAST_PORT,260,w,rootXmltv)

# A standard grabber should print the xmltv file to the stdout
ElementTree(rootXmltv).write(FILE_XML)

#print fXmltv.read()
fXml = open(FILE_XML, 'r')
#print fXml.read()

fXml.close()
fLog.close()
exit()
