#!/usr/bin/env python
# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## Logik-Generator  V2.019
## -----------------------------------------------------
## Copyright � 2011, knx-user-forum e.V, All rights reserved.
##
## This program is free software; you can redistribute it and/or modify it under the terms
## of the GNU General Public License as published by the Free Software Foundation; either
## version 3 of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
## without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
## See the GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along with this program;
## if not, see <http://www.gnu.de/documents/gpl-3.0.de.html>.

LGTVERSION = 2.019

#######################
### Changelog #########
#######################
## 2.019 * diverse Funktionen entfernt ;-)
##
## 2.018 * f�ge diverse interne Funktionen hinzu
##
## 2.017 * entferne --register
##
## 2.016 * **
##       * **
##
## 2.015 * 'names' zeigt jetzt SN and Timer
##       * colorama Unterst�tzung f�r farbliche Ausgabe
##       * �berpr�fung der Zeilenende auf Kommentarzeichen #
##       * Timer ON[x] erh�llt Wert der Formel
##       * fix AC wurde teilweise zu fr�h auf 0 gesetzt
##       * 'timer' zeigt jetzt ohne Parameter die verf�gbaren an
##       * 'timer [x]' f�hrt die Logik Berechnung bei aktivem autorun auch aus
##       * 'print' und 'import' als Befehl direkt ohne exec m�glich
##       * 'formel' zeigt die Formelzeilen und dekodierten Base64 Bytecode
##       * Syntax Highlighting
##       * Homeserver Variablen k�nnen an der Debugkonsole auch verk�rzt als en1= oder en2= etc gesetzt werden
##       * removed import popen2 
##
## 2.014 * interne IP
##
## 2.013 * diverse HS interne Objekte hinzugef�gt
##       * �berwachung von AC[x] auf �nderungen
##       * __import__ gegen Funktion ausgetauscht um hs interne Module zu imitieren
##       * KO Gateway Verbindung timeout ge�ndert
##       * eingaben string-decode um zum Beispiel bei EN[1]="d100=1\x03" das Steuerzeichen hex 03 zu senden
##       * Fix Ausgang beim internen schreiben �ber SetWert des iko
##       * --register nun je Python Version (Debug 2.4/Debug 2.6)
##
## 2.012 * runTime je Formelzeile
##       * --register zum registrieren der Debug Erweiterung f�r .hsl Dateien
##
## 2.011 * Name von TimerThreads entsprechend dem OC
##
## 2.010 * Bugfix 'names' 
##
## 2.009 * 'connect' zum manuellen verbinden aus dem Debugger
##       * EN[1]=$IKO$1/0/100 aus dem debugger heraus
##       * Bugfix .config nicht aus dem Installationspfad geladen beim Rechtsklick aus hsl
##
## 2.008 * Timer laufen automatisch bei autorun
##       * Bugfixes beim Beenden
##       * globals werden nicht mehr an die Formel �bergeben
##       * Zeilenummer beim Bedingungstest
##       * Autorun per .config default und pro LogikID
##       * Autorun override per Befehlszeile -a 1|0
##
## 2.007 * Bugfixes KO-Gateway
##       * AutoRun
##
## 2.006 * KO-Gateway f�r Ein/ausg�nge
##
## 2.005 * Anzeige auf SystemCodepage angepasst, sodass Umlaute angezeigt werden
##       * Option -n zum erstellen von .LGT Dateien aus .hsl
##       * Kontrollen f�r EI bei nicht startetenden Bausteinen
##       * Kontrolle auf Remanente Speicher bei nicht Remanenten Baustein
##       * Kontrolle der Timer Anzahl
##
## 2.004 * BugFixes _defline
##       * einige Dacom Bausteine (z.B. Codeschloss) haben keine g�ltige Definition
##
## 2.003 * 'names' zeigen jetzt auch die derzeitigen Werte
##       * LogikGen.config hinzugef�gt
##       * Ausgang von intern beschreiben
##       * Ausgaben auf Deutsch
##
## 2.002 * Parse Error in der 5001er Zeile
##	       * einige interne HS Klassen hinzugf�gt
##       * Timer ON/OC werden unterst�tzt
##
## 2.001 * Initial Release
##

import codecs
import sys
import os
import base64 
import marshal
import re
try:
    from hashlib import md5
except ImportError:
    import md5 as md5old
    md5 = lambda x: md5old.md5(x)
import inspect
import types
import signal
import time
from datetime import datetime
import threading
import socket
import select
import StringIO
import ConfigParser
#import popen2
import random
import zlib
import zipfile
import traceback
import Queue

try:
    from colorama import init,Fore, Back, Style
    init()
except ImportError:
    print "f�r farbliche Ausgaben -> https://pypi.python.org/pypi/colorama"
    ## Dummy Klasse erstellen
    class AnsiCodes(object):
        BLACK = ""
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        RESET = ""
        BRIGHT = ""
        DIM = ""
        NORMAL = ""
        RESET_ALL = ""
    
    Fore = Back = Style = AnsiCodes()


##  Weil der HS zu viele alte Module erwartet ;) so einfach k�nnte auch der HS diese bl�den Meldungen nicht an der Konsole zeigen.
import warnings
warnings.simplefilter("ignore",DeprecationWarning)

##############
### Config ###
##############
DEBUG = True
SYNTAXHIGHLIGHT = True

## kleine Hilfsfunktionen
def debug(msg):
    print(msg)

COLORRESET = Style.RESET_ALL
COLORINFO= Fore.YELLOW+Style.BRIGHT
COLORINTERN = Fore.GREEN+Style.BRIGHT

RE_SYSTEMLOG_FINDER = re.compile("<log>.*?</log>")
RE_SYSTEMLOG_GRABBER = re.compile("<log>(?=.*<facility>(?P<facility>.*?)</facility>)(?=.*<severity>(?P<severity>.*?)</severity>)(?=.*<message>(?P<message>.*?)</message>).*</log>")

RE_SYNTAX_HIGHLIGHT_COMMENT = re.compile("(^#.*?$|###.*?###)",re.MULTILINE)
RE_SYNTAX_HIGHLIGHT_FUNCTIONS = re.compile(r"(\bprint|\btry:|\bexcept\b.*?:|\bfinally:|\bfor\b.*?in.*?:|\bwhile\b.*?:|\belif\b.*?:|\bif\b.*?:|\belse:|\band\b|\bor\b|\bTrue\b|\bFalse\b|\bNone\b|\bdict\b|\blist\b|\bint\b|\bfloat\b|\bstr\b|\blen\b)",re.MULTILINE)
RE_SYNTAX_HIGHLIGHT_BFUNCTIONS = re.compile(r"(__import__\(.*?\)[\.\w+]+\b|\bdef\b.*?:|\bclass\b.*?:|\bfrom\b.*?import.*?$|\bimport\s.*?\bas\b\.*?$|\bimport\b.*?$|\blambda\b|\bcontinue\b|\breturn\b)",re.MULTILINE)
RE_SYNTAX_HIGHLIGHT_MODULES = re.compile(r"(\b\w+\.[\.\w+]+\b)")
RE_SYNTAX_HIGHLIGHT_HSVARS = re.compile(r"((?:[O|E|S|A][N|A|C]\[([0-9]{1,2})\])|\bEI\b|\bpItem\b)")


STDOUT_MUTEX = threading.Lock()

def console(msg,color=None):
    if type(msg) <> str:
        msg = str(msg)
    if color:
        msg = color + msg  + Style.RESET_ALL
    try:
        STDOUT_MUTEX.acquire()
        print (msg.decode("latin1").encode(sys.stdout.encoding))
    finally:
        STDOUT_MUTEX.release()

def console_error(msg):
    console(msg,color=Fore.RED+Style.BRIGHT)

def console_info(msg):
    console(msg,color=COLORINFO)

def console_intern(msg):
    _color = COLORINTERN
    _is_systemlog_message = RE_SYSTEMLOG_FINDER.findall(msg)
    if _is_systemlog_message:
        _outmsg = ""
        for _logmsg in _is_systemlog_message:
            _logdetails = RE_SYSTEMLOG_GRABBER.search(_logmsg)
            if not _logdetails:
                continue
            if len(_outmsg) > 0:
                _outmsg += "\n"
            _logdict = _logdetails.groupdict()
            _logdict['time'] = time.strftime("%H:%M:%S",time.localtime())
            _logdict['message'] = _logdict['message'].decode("string-escape").strip()
            _outmsg += "SYSTEMLOG: {time} - {severity} {facility} - {message}".format(**_logdict)
        if len(_outmsg) > 0:
            msg = _outmsg
            _color = Back.RED + Fore.YELLOW
    else:
        msg = "{0} {1}".format(time.strftime("%H:%M:%S",time.localtime()), msg)
    console(msg,color=_color)

def console_code(msg,color=COLORINFO):
    _color = color
    if Style.RESET_ALL <> "" and SYNTAXHIGHLIGHT:
        msg = RE_SYNTAX_HIGHLIGHT_COMMENT.sub(Fore.RED + Style.DIM + "\\1" + _color,msg)
        msg = RE_SYNTAX_HIGHLIGHT_FUNCTIONS.sub(Fore.WHITE + Style.DIM + "\\1" + _color,msg)
        msg = RE_SYNTAX_HIGHLIGHT_BFUNCTIONS.sub(Fore.MAGENTA + Style.DIM + "\\1" + _color,msg)
        msg = RE_SYNTAX_HIGHLIGHT_MODULES.sub(Fore.YELLOW + Style.DIM + "\\1" + _color,msg)
        msg = RE_SYNTAX_HIGHLIGHT_HSVARS.sub(Fore.CYAN + Style.DIM + "\\1" + _color,msg)
    console(msg,color=_color)


def console_debug(msg):
    if DEBUG:
        console_code(msg,color=Fore.CYAN+Style.BRIGHT)

def unquote(text):
    ## entfernt die Anf�hrungszeichen
    if type(text) <> str:
        try:
            text = str(text)
        except:
            return ""
    return re.sub("^[\"|\']|[\"|\']$","",text)

def quoteVal(e):
    ## setzt Anf�hrungszeichen wenn typ string
    if e['isalpha']:
        return "\"" + e['value'] + "\""
    return str(e['value'])
    

def grp2str(_i):
    return "%d/%d/%d" % (_i >> 11 & 0xff, _x >> 8 & 0x07, x & 0xff)

def str2grp(_s):
    _t = _s.split("/")
    return int(_t[0]) << 11 | int(_t[1]) << 8 | int(_t[2])

### Homeserver Klassen ###
class HomerServerDummy:
    pass
class HSLogikItemDummy:
    pass
class HSLogikSelfDummy:
    pass
class dummy:
    pass

class debug_dummy:
    
    Version = "4.2.LOGIKDEBUGGER"
    def __init__(self):
        self.Daten = []
    def setErr(self,pException,pComment=''):
        console(Fore.RED + Style.BRIGHT + "Error:" + Fore.MAGENTA)
        traceback.print_exception(pException[0],pException[1],pException[2],file=sys.stdout)
        console_intern(pComment)
    def setErrDirekt(self,pText):
        console_error("Error: %r" % pText)
    def addGruppe(self,pGruppe,pItems):
        console_intern("addGruppe %r with Items %r" % (pGruppe,pItems))
        self.Daten.append(pGruppe+[pItems,])
    def setWert(self,pGruppe,pToken,pWert):
        console_intern("setWert %s - %s to %s%r" % (pGruppe,pToken,Fore.YELLOW,pWert))
    def addWert(self,pGruppe,pToken,pWert):
        console_intern("addWert %s - %s to %s%r" % (pGruppe,pToken,Fore.YELLOW,pWert))
    def __str__(self):
        _ret = ""
        for _data in self.Daten:
            _ret += _data[1] + "\n"
            _ret += "*"*20 + "\n"
            for _line in _data[2]:
                _ret += "  " + re.sub(r'<.*?>',"",_line[1])  +"\n"
                _ret += "     " + re.sub(r'<.*?>'," ",_line[3]) + "\n"
        return _ret
        

class HSIKOdummy:
    def __init__(self,LGT,attached_out):
        self.LGT = LGT
        self.Value = ''
        self.Format = 22
        self.SpeicherID = 1
        self._attached_out = attached_out
        self.mutex = threading.Lock()
    def setWert(self,out,wert):
        try:
            self.mutex.acquire()
            self.Value = wert
            console("** intern ** auf AN[%d]: %s%s" % (self._attached_out,Fore.YELLOW,repr(wert)))
            self.LGT.setVar("AN",self._attached_out,wert)
        finally:
            self.mutex.release()
    def getWert(self):
        try:
            self.mutex.acquire()
            return self.Value
        finally:
            self.mutex.release()
            
    def checkLogik(self,out):
        pass


__old_import__ = __import__

class hs_timer(threading._Timer):
    def __init__(self,interval,function):
        self.starttime = time.strftime("%H:%M:%S",time.localtime())
        self.calctime = time.time() + interval
        threading._Timer.__init__(self,interval, function)

    def get_time(self):
        return "start: %s remain %.2f s" % ( self.starttime,self.calctime - time.time() )

class hs_queue_queue(Queue.Queue):
    def put(self,item):
        Queue.Queue.put(self,[time.time(),item])
    def get(self):
        return Queue.Queue.get(self)[1]

import posixpath
import mimetypes
        
class ExtDatItem(object):
    def __init__(self,path,mc):
        import os
        self.MC = mc
        self.source_file = path
        _path = path.replace(self.MC.LGT.hsupload_dir,"")
        _path = _path.replace("\\","/")
        console_info("-> Datei '{0}'".format(_path))
        self.DatName = "OPT/{0}".format(_path.upper())
        _extension = posixpath.splitext(_path)[1]
        self.Typ = mimetypes.types_map.get(_extension,"application/octet-stream")
        self.UrlPfad = _path.upper()
        self.DatPos = 0
        self.DatLen = os.path.getsize(path)
        self.MC.GUI.ExtDatUrl[_path.upper()] = self
        
    def getDaten(self):
        return open(self.source_file,"rb").read()
    def getQuadDaten(self):
        return open(self.source_file,"rb").read()
    def getDatenStream(self,stream):
        steam.write(open(self.source_file,"rb").read())
    def getQuadDatenStream(self,stream):
        steam.write(open(self.source_file,"rb").read())

def dummy_return_all(self,*args,**kwargs):
    console_debug("called '{0}' with args [{1}]".format(traceback.extract_stack(None, 2)[0][2],args))

def addZyklustimer(self,logik,nextstart):
    import time
    _nextstart_time = time.localtime(nextstart)
    _seconds = nextstart - time.time() 
    console_debug("Set Timer {0} to {1} {2} seconds".format(logik,time.strftime("%H:%M:%S",_nextstart_time),_seconds))
    

def taglist_setwert(self,FLAG,iko,value):
    console_intern("*** setwert ** auf AN[{0}]: {1}{2}".format(iko._attached_out,Fore.YELLOW,value))
    self.LGT.setVar("AN",iko._attached_out,value)
    self.LGT.setVar("AC",iko._attached_out,0)


class hs_queue(object):
    Queue = hs_queue_queue
    hs_threading = threading
  
sys.modules['hs_queue'] = hs_queue
def __import__(module):
    console_debug("Lade Modul %r" % module)
    if module in ['hs_queue','sys']:
        print "FROM GLOBAL"
        return globals().get(module)
    return __old_import__(module)

def get_local_ip():
    _ip = socket.gethostbyname( socket.gethostname() )
    if _ip.startswith("127"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 0))
        _ip = s.getsockname()[0]
        s.close()
    return _ip
       
###########################

FLAG_EIB_LOGIK=1
FLAG_EIB_ZENTRAL=2
FLAG_EIB_UNKNOWN=12
FLAG_EIB_REQUEST=13
FLAG_EIB_COMMAND=14

class LogikGeneratorClass:
    def __init__(self):
        self.GeneratorVersion = LGTVERSION
        self.LogikNum = 10100
        self.LogikName = "unamedLogik"
        self.LogikiName = self.LogikName
        self.LogikCat = ""
        self.LogikHeader = []
        self.Eingang = [{'value':0}]
        self.Ausgang = [{'value':0}]
        self.Speicher = [{'value':0}]
        self.Offset = [[0,0,None]]
        self.Formel = []
        self.runStart = False
        self.isRemanent = False
        self.iscrypted = False
        self.rawlines = []
        self.bCode = []
        self.Options = { 'decode':False,'strict':False}
        self.Errors = {'warning':0, 'error':0}
        
        self.KOGW = {'running':False,'thread':None,'socket':None,'connected':False,'hsip': '','gwport':0,'gwsecret': ''}
        self.KOGWInObj = {}
        self.AutoRun = True
        self.AutoConnect = False
        self.hsupload_dir = None
        
        self.mutex = threading.RLock()
        ## some dummy Vars 
        _mc = HomerServerDummy()
        self.MC = _mc
        _mc.LGT = self
        _mc.SystemID = "0123456789ab"
        _mc.ProjectID = time.strftime("%Y%m%d%H%M%S000",time.localtime())
        
        _mc.SichQueue = Queue.Queue()
        
        ## GUI
        _mc.GUI = dummy()
        _mc.GUI.ExtDatUrl = {}
        
        _guiclient = dummy()
        _guiclient.BGList = { "DUMMYBG": [0,4321, "image/png" ] }
        _guiclient.IconList = { "DUMMYICO" : [20,1234, "image/png" ] }
        _guiclient.BGHash = md5("")
        _guiclient.IconHash = md5("")
        
        _mc.GUI.ClientKeyList = {
            "D1024V" : _guiclient
        }
        
        ## LogikList
        _mc.LogikList = dummy()
        _mc.LogikList.ConnectList = []
        _mc.LogikList.calcLock = threading.RLock()
        
        ## TagList
        _mc.TagList = dummy()
        _mc.TagList.LGT = self
        _mc.TagList.TagList = {}
        _mc.TagList.setWert = types.MethodType(taglist_setwert,_mc.TagList) ## FIXME
        
        ## Zyklustimer
        _mc.ZyklusTimer = dummy()
        _mc.ZyklusTimer.addTimerList = types.MethodType(addZyklustimer,_mc.ZyklusTimer) ## FIXME
        
        ## KameraList
        _mc.KameraList = dummy()
        _mc.KameraList.KamList = {}

        ## IP
        _mc.Ethernet = dummy()
        _mc.Ethernet.IPAdr = get_local_ip()
        _mc.Ethernet.IPPort = 8080
        
        ## Default HS Resolver
        _mc.DNSResolver = dummy()
        _mc.DNSResolver.getHostIP = socket.gethostbyname
        
        ## Debug
        _mc.Debug = debug_dummy()

        
        ## HS Telefonbedienung
        _mc.TelefonInterface = dummy()
        _mc.TelefonInterface.DoBefehl = lambda pZielnr,pAbsendernr: console_intern("Telefonbedienung: Ziel:{0} Absender:{1}".format(pZielnr,pAbsendernr))
        ## HS self dummy
        _HSself = HSLogikSelfDummy()
        _HSself.MC = _mc
        _HSself.ID = self.LogikNum
        _HSself.makeCheckSum = lambda: md5(str(random.random())).hexdigest()
        
        
        ## HS Logik dummy
        _pItem = HSLogikItemDummy()
        _pItem.MC = _mc
        _pItem.NextStart = 0
        _pItem.SendIntervall = 0
        _pItem.ID = 1
        _pItem.Speicher = 0
        _pItem.SpeicherWert = []
        _pItem.Eingang = []
        _pItem.Ausgang = []
        _pItem.SpeicherWert = []
        _pItem.OutWert = []
        _pItem.InWert = []
        _pItem.OutOfset = []
        _pItem.LogikItem = HSLogikItemDummy()
        _pItem.LogikItem.Speicher = []
        _pItem.LogikItem.AnzSpeicher = 0
        
        _mc.LogikList.GatterList = {
            _pItem.ID : _pItem 
        }

        ## make them local
        self.localVars = {
          'self':_HSself,
          'pItem':_pItem,
          'Timer':[[None,None]],
          'EI':1,
          'EN':[None],
          'EC':[None],
          'EA':[None],
          'SN':[None],
          'SC':[None],
          'SA':[None],
          'AN':[None],
          'AC':[None],
          'AA':[None],
          'ON':[None],
          'OC':[None],
          'OA':[None]
        }
        self.globalVars = globals()
    
    
    def symbolize(self,LogikHeader,code):
        symbols = {}
        for i in re.findall(r"(?m)^500([234])[|]([0-9]{1,}).*[@][@](.*)\s", LogikHeader):
            varName=((i[0]=='2') and 'E') or ((i[0]=='3') and 'S') or ((i[0]=='4') and 'A')
            isunique=True
            try:
                type(symbols[i[2]])
                sym=i[2]
                isunique=False
            except KeyError:
                pass
            ## �berpr�ft auch die alternativen Varianten
            if re.match("[ACN]",i[2][-1:]):
                try:
                    type(symbols[i[2][:-1]])
                    sym=i[2][:-1]
                    isunique=False
                except KeyError:
                    pass
            if isunique:
                symbols[i[2]]=[varName,"["+i[1]+"]"]
            else:
                console_error("Variablen Kollision :" +repr(i[2])+" ist in " +repr(symbols[sym]) + " und  "+ varName +"["+i[1]+"] vergeben")
                self.exitall(1)

        ## Symbole wieder entfernen
        LogikHeader=re.sub("[@][@]\w+", "",LogikHeader)

        #im Code tauschen
        for i in symbols.keys():
            code=[code[0],re.sub("[\@][\@]"+i+"([ACN])",symbols[i][0]+"\\1"+symbols[i][1],code[1]),re.sub("[\@][\@]"+i+"([ACN])",symbols[i][0]+"\\1"+symbols[i][1],code[2])]
            code=[code[0],re.sub("[\@][\@]"+i+"",symbols[i][0]+"N"+symbols[i][1],code[1]),re.sub("[\@][\@]"+i+"",symbols[i][0]+"N"+symbols[i][1],code[2])]
        return LogikHeader,code
    
    def commentCode(self,code):
        return "##########################\n###### Quelltext: ########\n##########################"+"\n##".join(code.split("\n"))+"\n"
        
    def enableDebug(self,code):
        return re.sub("###DEBUG###","",code)
        
    def removeComments(self,code):
        codelist=code.split("\n")
        removelist=[]
        lencode=len(codelist)-1
        for i in range(1,lencode):
            codeline=codelist[lencode-i].lstrip(" \t")
            if len(codeline)>0:
                if codeline[0]=='#':
                    removelist.insert(0,"REMOVED: ("+str(lencode-i)+") "+codelist.pop(lencode-i))
            else:
                codelist.pop(lencode-i)
        console_info("Removed" )
        console("\n".join(removelist))
        return "\n".join(codelist)
    
    def compileMe(self,code):
        pass
    
    def readConfig(self,configFile):
        global DEBUG
        self.Licences = {}
        configparse = ConfigParser.SafeConfigParser()
        configparse.read(configFile)
        #for _lic in configparse.options("licences"):
        #    self.Licences[_lic] = configparse.get("licences",_lic)
        console_info("Looking for %s%r%s Config" % (Fore.GREEN,self.LogikNum,COLORINFO))
        try:
            DEBUG = configparse.getboolean('default','debug')
        except (ConfigParser.NoOptionError,ConfigParser.NoSectionError):
            pass
        try:
            self.AutoRun = configparse.getboolean('default','autorun')
        except (ConfigParser.NoOptionError,ConfigParser.NoSectionError):
            pass
        try:
            self.hsupload_dir = "{0}\\".format(configparse.get('default','hsupload').rstrip("\\"))
        except (ConfigParser.NoOptionError,ConfigParser.NoSectionError):
            pass

        if configparse.has_section(str(self.LogikNum)):
            console_info("Found Config for %s%r%s" % (Fore.GREEN,self.LogikNum,COLORINFO))
            try:
                DEBUG = configparse.getboolean(str(self.LogikNum),'debug')
            except ConfigParser.NoOptionError:
                pass
            try:
                self.AutoRun = configparse.getboolean(str(self.LogikNum),'autorun')
            except ConfigParser.NoOptionError:
                pass
            try:
                self.AutoConnect = configparse.getboolean(str(self.LogikNum),'autoconnect')
            except ConfigParser.NoOptionError:
                pass

            for _v in configparse.options(str(self.LogikNum)):
                _defSet = re.findall("^([e|a|s][n|a|c])\[(\d+)\]",_v)
                if _defSet:
                    _defSet = _defSet[0]
                    _vals = configparse.get(str(self.LogikNum),_v)
                    for _val in _vals.split("|"):
                        if _val.startswith("$IKO$"):
                            try:
                                #_iko = (lambda x: (lambda y: int(y[0]) <<11 | int(y[1]) << 8 | int(y[2]))(x.split("/")))(_val[5:])
                                _iko = str2grp(_val[5:])
                                if _defSet[0].upper() == "EN":
                                    self.KOGWInObj[_iko] = int(_defSet[1])
                                    self.Eingang[int(_defSet[1])]['ikos'].append(_val[5:])
                                    console_info("** Setze IKO %s auf %sEN[%d]" % (Fore.GREEN + _val[5:] + COLORINFO,Fore.GREEN,int(_defSet[1])))
                                elif _defSet[0].upper() == "AN":
                                    self.Ausgang[int(_defSet[1])]['ikos'].append(_val[5:])
                                    console_info("** Setze IKO %s auf %sAN[%d]" % (Fore.GREEN + _val[5:] + COLORINFO,Fore.GREEN,int(_defSet[1])))
                            except:
                                pass
                        else:
                            self.setVar(_defSet[0].upper(),int(_defSet[1]),_val)
                #print "%s: %r" % (_v,configparse.get(str(self.LogikNum),_v))
        try:
            self.KOGW['hsip'] = configparse.get('kogw','hsip')
            self.KOGW['gwport'] = configparse.getint('kogw','gwport')
            self.KOGW['gwsecret'] = configparse.get('kogw','gwsecret')
        except (ConfigParser.NoOptionError,ConfigParser.NoSectionError):
            pass

        #print self.KOGW


    def _readConfig(self,cfile='LogikGen.config'):
        cfg = ConfigParser.SafeConfigParser()
        cfg.read(cfile)
        console(cfg.get('default','copyright',''))
        console(cfg.get('default','compiler',''))
        
        #print sys.executable

    
    def getHeader(self):
        return "# -*- coding: iso8859-1 -*-"

    def showHSLhelp(self):
        return ""

    def Header(self,header):
        self.LogikHeader = header.split("\n")

    def connectKOGW(self):
        if self.KOGW['socket']:
            console_info("*** KO-Gateway schon verbunden ***")
            return
        self.KOGW['thread'] = threading.Thread(target=self.__connectKOGW)
        self.KOGW['running'] = True
        self.KOGW['thread'].setDaemon(True)
        self.KOGW['thread'].start()
    
    def disconnectKOGW(self):
        self.KOGW['running'] = False
        console_info("*** warte auf KO-Gateway  ***")
        self.KOGW['thread'].join()

    def __connectKOGW(self):
        while self.KOGW['running']:
            try:
                if not self.KOGW['socket']:
                    try:
                        self.KOGW['socket'] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                        self.KOGW['socket'].connect((self.KOGW['hsip'],self.KOGW['gwport']))
                        self.KOGW['socket'].send(self.KOGW['gwsecret']+"\x00")
                        console_info("*** Verbindung zum KO-Gateway hergestellt ***")
                        self.KOGW['connected'] = True
                        self.__readKOGW()
                    except:
                        self.KOGW['connected'] = False
                        traceback.print_exc(file=sys.stdout)
                        console_error("*** Fehler beim verbinden zum KO-Gateway des HS: %s:%d" % (self.KOGW['hsip'],self.KOGW['gwport']))
                if not self.KOGW['running']:
                    break
                _t = 0
                while self.KOGW['running'] and _t < 20:
                    _t += 1
                    time.sleep(0.5)
            finally:
                self.KOGW['connected'] = False
                console_info("*** Verbindung zum KO-Gateway getrennt ***")
                self.KOGW['socket'].close()
                self.KOGW['socket'] = None
                
    
    def __readKOGW(self):
        buf = ""
        while self.KOGW['running']:
            _r,_w,_e = select.select([self.KOGW['socket']],[],[],1)
            if self.KOGW['socket'] in _r:
                _buf = self.KOGW['socket'].recv(8192)
                if not _buf:
                    break
                buf += _buf
                while buf.find("\x00"):
                    try:
                        line,buf = buf.split("\x00",1)
                    except ValueError:
                        break
                    info = line.split("|")
                    if len(info) > 2:
                        if not info[1]:
                            continue
                        address = int(info[1])
                        #addr = "%d/%d/%d" % ((address >> 11) & 0xff, (address >> 8) & 0x07, (address) & 0xff)
                        _io = self.KOGWInObj.get(address,None)
                        if _io:
                            self.setVar("EN",_io,info[2])
                            ## nicht beim INIT
                            if self.AutoRun and info[0] <> "2":
                                self.LogikCalc()
            

                
    def __sendKOGW(self,iko,val):
        if self.KOGW['socket']:
            try:
                _a = (lambda x: (lambda y: int(y[0]) <<11 | int(y[1]) << 8 | int(y[2]))(x.split("/")))(iko)
                _s = "1|"+str(_a)+"|"+str(val)+"\x00"
                self.KOGW['socket'].send(_s)
            except:
                traceback.print_exc(file=sys.stdout)
                pass

    def LogikError(self,typ,line,LineNum,msg=" ",console=console):
        if typ == "5000":
            console_error("*** Fehler bei Experte Definition 5000: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5000|\"Text\"|Remanent(1/0)|Anz.Eing�nge|.n.|Anzahl Ausg�nge|.n.|.n.")
        elif typ == "5001":
            console_error("*** Fehler bei HS Logik Definition 5001: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5001|Anzahl Eing�nge|Ausg�nge|Offset|Speicher|Berechnung bei Start")
        elif typ == "5002":
            console_error("*** Fehler bei Eingangsdefinition 5002: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5002|Index Eingang|Default Wert|0=numerisch 1=alphanummerisch")
        elif typ =="5003":
            console_error("*** Fehler bei Speicherdefinition 5003: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5003|Speicher|Initwert|Remanent")
        elif typ =="5004":
            console_error("*** Fehler bei Ausgangsdefinition 5004: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5004|ausgang|Initwert|runden bin�r (0/1)|typ (1-send/2-sbc)|0=numerisch 1=alphanummerisch")
        elif typ =="5012":
            console_error("*** Fehler bei Formel Definition 5012: Zeile %d %s***" % (LineNum,msg))
            console_info("\n#5012|abbruch bei bed. (0/1)|bedingung|formel|zeit|pin-ausgang|pin-offset|pin-speicher|pin-neg.ausgang")
        else:
            console("TYPE %r" % (typ),color=Back.RED)
        
        console("--------------------------------------------------------------------------")
        console(line)
        console("--------------------------------------------------------------------------")
        #__import__('traceback').print_exc(file=__import__('sys').stdout)
        self.Errors['error'] +=1
        if self.Options['strict']:
            self.exitall(1)
    
    def exitall(self,_r):
        if _r > 0:
            traceback.print_exc(file=sys.stdout)
        if self.KOGW['running']:
            self.KOGW['running'] = False
            console("** Warte auf KO-Gateway *** ")
            self.KOGW['thread'].join()
        
        for _t in self.Offset:
            try:
                _t[2].cancel()
            except:
                pass

        _active_threads = threading.enumerate()
        for _thread in _active_threads:
            if _thread <> threading.currentThread():
                try:
                    console_debug("Beende Thread: %r " % (_thread.name))
                    if type(_thread) == hs_timer:
                        _thread.cancel()
                    else:
                        _thread._Thread__stop()
                        console_error("--> killed")
                    _thread.join(2)
                except:
                    traceback.print_exc(file=sys.stdout)
                    print ("Failed")

        ## Farben wiederherstellen
        print "** CLEANUP **"
        if hasattr(sys.stdout,"TEE"):
            sys.stdout = sys.stdout.stdout
        print Fore.WHITE,Back.BLACK,Style.RESET_ALL,
        if hasattr(os,"kill"):
            #print ("raise SIGTERM")
            _pid = os.getpid()
            os.kill(_pid,signal.SIGTERM)
        time.sleep(0.5)

        sys.exit(int(_r <> 0))


    def LogikDebug(self):
        console("\n\n### Logik Debugger ###\n")
        if self.hsupload_dir:
            console_info("lade hsupload-Verzeichnis '{0}' hoch".format(self.hsupload_dir))
            for _root,_dirs,_files in os.walk(self.hsupload_dir):
                for _file in _files:
                    ExtDatItem(os.path.join(_root,_file),self.MC)
            console_info("") 

        if self.AutoConnect:
            self.connectKOGW()
            while True:
                time.sleep(0.5)
                if self.KOGW['connected']:
                    break
                time.sleep(0.5)
                console_info("*** Waiting for KOGW ***")
        if self.AutoRun and self.runStart:
            self.LogikCalc()
        while True:
            try:
                _cmd = raw_input(">> ")
                if hasattr(sys.stdout,"TEE") and len(_cmd) > 1 :
                    sys.stdout.log(">> " + _cmd)
            except (KeyboardInterrupt,SystemExit):
                self.exitall(0)
                
            _lcmd = _cmd.lower()
            
            if _lcmd.startswith("quit") or _lcmd.startswith("exit"):
                self.exitall(0)
                break
            
            elif _cmd == "":
                continue
            
            elif _lcmd.startswith("show"):
                for v in sorted(self.localVars):
                    console_info("%s: %r" % (v,self.localVars[v]))
                for t in self.localVars['Timer']:
                  if t[0]:
                      console_info("%s: %s (%s)" % (t[2].name,time.strftime("%H:%M:%S",time.localtime(t[0])),t[2].get_time()))
            elif _lcmd.startswith("disconnect"):
                self.disconnectKOGW()
            elif _lcmd.startswith("connect"):
                self.connectKOGW()
            elif _lcmd.startswith("names"):
                console_info("Systemstart: % d Remanent: %d" % (self.runStart,self.isRemanent))
                try:
                    console_info("-------- Eing�nge ------------")
                    for v in range(1,len(self.Eingang)):
                        _iko = ""
                        if self.Eingang[v]['ikos']:
                            _iko = "[" + Fore.GREEN + repr(self.Eingang[v]['ikos']) + Fore.RESET + "]"
                        console("EN[%d]: %s (%s) %s" % (v,self.Eingang[v]['name'],Fore.YELLOW + Style.BRIGHT + repr(self.localVars['EN'][v])[:50] + Style.RESET_ALL, _iko))
                    console_info("-------- Ausg�nge ------------")
                    for v in range(1,len(self.Ausgang)):
                        _iko = ""
                        if self.Ausgang[v]['ikos']:
                            _iko = "[" + Fore.GREEN + repr(self.Ausgang[v]['ikos']) + Fore.RESET + "]"
                        console("AN[%d]: %s (%s) %s" % (v,self.Ausgang[v]['name'],Fore.YELLOW + Style.BRIGHT + repr(self.localVars['AN'][v])[:50]  + Style.RESET_ALL,_iko))
                    console_info("-------- Speicher ------------")
                    for v in range(1,len(self.Speicher)):
                        console("SN[%d]: (%s)" % (v,Fore.YELLOW + Style.BRIGHT + repr(self.localVars['SN'][v])[:50] + Style.RESET_ALL))
                    if len(self.Offset) > 1:
                        console_info("-------- Timer ------------")
                        for v in range(1,len(self.Offset)):
                            console("ON[%d]: %s (%r)" % (v,Fore.YELLOW + Style.BRIGHT + repr(self.Offset[v][1])[:50] + Style.RESET_ALL,self.Offset[v][0] and time.strftime("%H:%M:%S",time.localtime(self.Offset[v][0]))))
                except:
                    console_error("*** Fehler ... ***")
                    self.exitall(1)
                    pass
            
            elif _lcmd.startswith("run"):    
                self.LogikCalc()
            
            elif _lcmd.startswith("files"):
                _args = _lcmd.split(" ")[1:]
                if _args:
                    _args = _args[0].upper()
                else:
                    _args = ""
                _files = self.MC.GUI.ExtDatUrl.keys()
                _files.sort()
                _sum = 0
                _count = 0
                for _file in _files:
                    if _file.startswith(_args):
                        _fileobj = self.MC.GUI.ExtDatUrl.get(_file)
                        _sum += _fileobj.DatLen
                        _count += 1
                        console_info("* {0: <50} {1:>7,.0f} {2}".format(_file,_fileobj.DatLen,_fileobj.Typ.split("\n")[0]))
                if _count > 1:
                    console_info("*"*40)
                    console_info("{0} Files  {1:,.2f} KB".format(_count,1.0 * _sum / 1024))
            elif _lcmd.startswith("cat "):
                _args = _lcmd.split(" ")[1:]
                if _args:
                    _args = _args[0]
                    _file = self.MC.GUI.ExtDatUrl.get(_args.upper())
                    if not _file:
                        console_error("Datei nicht gefunden")
                    else:
                        print _file.getDaten()
            elif _lcmd.startswith("formel"):
                _args = _lcmd.split(" ")
                _range = 10
                try:
                    _limit = int(_args[1])
                except (IndexError,ValueError):
                    _limit = None
                for line in self.Formel:
                    console_code("[{0:^4}] {1}".format(line.get("line"),line.get("rawline","###")))
                    if line.get("bytecode"):
                        _blines = line.get("bytecode").split("\n")
                        for _blinenum in xrange(len(_blines)):
                            if not _limit or ((_limit - _range) <= (_blinenum + 1)  <= (_limit + _range)):
                                console_code("{0:<6} {1}".format(_blinenum + 1,_blines[_blinenum]),color=(Fore.GREEN if (_blinenum + 1) <> _limit else Fore.RED))
            
            elif _lcmd.startswith("autorun"):    
                _sw = re.findall("autorun[=\s]?(\d)",_lcmd)
                if _sw:
                    _sw = (int(_sw[0]) == 1)
                self.AutoRun = _sw

            elif _lcmd.startswith("debug"):    
                global DEBUG
                _sw = re.findall("debug[=\s]?(\d)",_lcmd)
                if _sw:
                    _sw = int(_sw[0]) == 1
                DEBUG = _sw

            elif _lcmd.startswith("help") or _cmd.startswith("hilfe"):
                console("\n")
                console_info("Logik Debugger Hilfe")
                console_info("--------------------\n")
                console_info("'quit' oder 'exit' zum beenden")
                console_info("'show' um die Variablen anzuzeigen")
                console_info("'names' zeigt die Namen der Ein-/Ausg�nge an")
                console_info("'run' um die Logik auszuf�hren")
                console_info("'autorun [0/1]' autorun ein/aus")
                console_info("'timer 1' l�sst Timer OC[1]/ON[1] ablaufen")
                console_info("'connect' verbinden zum definierten KO Gateway")
                console_info("'exec [code]' ausf�hren von python Code innerhalb der Logik")
                console_info("'EN[1]=23' um Eingang 1 den Wert 23 zu setzen")
                console_info("-- es k�nnen EI,EN,SN,AN,ON sowie EC,SC,AC,OC als auch EA,SA,AA")
                console_info("-- ge�ndert werden. Bei den ersten wird automatisch das jeweilige xC gesetzt")
                console("\n")
            elif _lcmd.startswith("exec "):
                try:
                    print Fore.YELLOW
                    eval(compile(_cmd[5:],"ldebug","exec"),self.globalVars,self.localVars)
                except:
                    print Fore.RED
                    traceback.print_exc(file=sys.stdout)
                print Style.RESET_ALL

            elif _lcmd.startswith("print ") or _lcmd.startswith("import "):
                try:
                    print Fore.YELLOW
                    eval(compile(_cmd,"ldebug","exec"),self.globalVars,self.localVars)
                except:
                    print Fore.RED
                    traceback.print_exc(file=sys.stdout)
                print Style.RESET_ALL
                    
            elif _lcmd.startswith("timer"):
                t = re.findall("\d+",_cmd)
                if t:
                    t=int(t[0])
                    if t < 1:
                        continue
                    _v = self.Offset[t][1]
                    try:
                        self.Offset[t][2].cancel()
                    except:
                        pass
                    #self.Offset[t] = (time.time()-1,_v)
                    self.Offset[t][0] = time.time()-1
                    console_info("Set Offset: %r" % (self.Offset[t],))
                    if self.AutoRun:
                        self.LogikCalc()
                else:
                    console_info("-------- Timer ------------")
                    for o in xrange(1,len(self.Offset)):
                        console("%d: Timer ON[%d]: %s (%s)" % (o,o,time.strftime("%H:%M:%S",time.localtime(self.Offset[o][0])),repr(self.Offset[o][1])[:40]))
            elif _lcmd.startswith("ei="):
                if _cmd[3] == "1":
                    self.localVars['EI'] = 1
                else:
                    self.localVars['EI'] = 0
            elif _lcmd.strip() == "":
                pass
            else:
                _var = re.findall("^([O|E|S|A|o|e|s|a][N|n|A|a|C|c])[\[]?([0-9]{1,2})[\]]?=(.*)",_cmd)
                if _var:
                    _vname,_vnum,_val = _var[0]
                    _vnum = int(_vnum)
                    _vname = _vname.upper()
                    if _val.startswith("$IKO$"):
                        try:
                            #_iko = (lambda x: (lambda y: int(y[0]) <<11 | int(y[1]) << 8 | int(y[2]))(x.split("/")))(_val[5:])
                            _iko = str2grp(_val[5:])
                            if _vname == "EN":
                                self.KOGWInObj[_iko] = _vnum
                                self.Eingang[_vnum]['ikos'].append(_val[5:])
                                console_info("** Setze IKO %s auf EN[%d]" % (_val[5:],_vnum))
                            elif __vname == "AN":
                                self.Ausgang[_vnum]['ikos'].append(_val[5:])
                                console_info("** Setze IKO %s auf AN[%d]" % (_val[5:],_vnum))
                        except:
                            console(Fore.RED + Style.BRIGHT)
                            traceback.print_exc(file=sys.stdout)
                            console(Style.RESET_ALL)
                            pass
                    else:
                        self.setVar(_vname,_vnum,_val.decode(sys.stdout.encoding).encode('latin1').decode('string-escape'))

                else:
                    console_error("*** unbekannter Befehl - tippe help f�r Hilfe *** ")
            _cmd = None
    
    def setVar(self,_vname,_vnum,_val):
        try:
            _isalpha = True
            _sbc = False
            _old = None
            _cvar = None
            if _vname[1] == "C":
                _isalpha = False
            if _vname in ["AN","SN","ON","EN"]:
                if _vname == "AN":
                    _isalpha = self.Ausgang[_vnum]['isalpha']
                    _sbc = self.Ausgang[_vnum]['sbc']
                    _old = "AA"
                    _cvar = "AC"
                elif _vname == "EN":
                    _isalpha = self.Eingang[_vnum]['isalpha']
                    _old = "EA"
                    _cvar = "EC"
                elif _vname == "SN":
                    _isalpha = self.Speicher[_vnum]['isalpha']
                    _old = "SA"
                    _cvar = "SC"
            if _isalpha:
                _val = unquote(_val)
            else:
                _val = float(_val)
            try:
                #self.mutex.acquire()
                if _cvar and _old:
                    self.localVars[_old][_vnum] = self.localVars[_vname][_vnum]
                    if not _sbc or _val <> self.localVars[_old][_vnum]:
                        if _vname == "AN":
                            if len(self.Ausgang[_vnum]['ikos']) > 0:
                                console_intern("*** sende an IKOs %r den Wert %s" % (self.Ausgang[_vnum]['ikos'],repr(_val)[:40]))
                            for _iko in self.Ausgang[_vnum]['ikos']:
                                self.__sendKOGW(_iko,_val)
                        self.localVars[_cvar][_vnum] = 1
                self.localVars[_vname][_vnum] = _val
                if _vname == "SN":
                    self.localVars['pItem'].SpeicherWert[_vnum -1] = _val
            finally:
                #self.mutex.release()
                pass
        except:
            console_error("Fehler beim beschreiben der Variablen")
            console_info(repr(self.localVars))
            console(Fore.RED + Style.BRIGHT)
            traceback.print_exc(file=sys.stdout)
            console(Style.RESET_ALL)
    
    def TimerCalc(self):
        if self.AutoRun:
            self.LogikCalc()
    
    def stripline(self,line):
        try:
            if len(line) < 140:
                return line
            else:
                return line[:80] + " .... " + line[-50:]
        except TypeError:
            return ""
            
        
    
    def LogikCalc(self):
        try:
            self.mutex.acquire()

            for t in xrange(1,len(self.Offset)):
                if self.Offset[t][0] < 1:
                    continue
                if time.time() >= self.Offset[t][0]:
                    try:
                        self.Offset[t][2].cancel()
                    except:
                        pass
                    self.localVars['ON'][t] = self.Offset[t][1]
                    self.localVars['OC'][t] = 1
                    #self.Offset[t] = (0,self.localVars['ON'][t])
                    self.Offset[t][0] = 0
                
                
            for formel in self.Formel:
                try:
                    line = self.stripline(formel['case'])
                    resultLine = ""
                    caseVars = re.findall("([O|E|S|A][N|A|C])\[([0-9]{1,2})\]",line)
                    for (v,i) in caseVars:
                        varName = "{0}[{1}]".format(v,i)
                        try:
                            varVal = self.localVars.get(v)[int(i)]
                        except (KeyError,IndexError):
                            varVal = None
                        resultLine += "{0}='{1}' /".format(varName,varVal)
                    resultLine = resultLine[:-2]
                    console_debug("teste Bedingung in Zeile %d: %r # %s #" % (formel['line'],line,resultLine))
                    startRunTime = time.clock()
                    if eval(formel['caseCode'],self.globalVars,self.localVars):
                        console_debug("starte Formel: %r" % (self.stripline(formel['formel'])))
                        result = eval(formel['formelCode'],self.globalVars,self.localVars)
                        offset = eval(formel['offsetCode'],self.globalVars,self.localVars)
                        runTime = time.clock() - startRunTime
                        console_debug("RunTime: %f" % (runTime))
                        console_debug("Ausgabe: %d|%d|%d|%d" % (formel['pinAusgang'],formel['pinOffset'],formel['pinSpeicher'],formel['pinNegAusgang']))
                        console_debug("Ergebnis: %r" % (result,))
                        console_debug("-------")
                        _result = result
                        if formel['pinAusgang'] > 0:
                            _pin = formel['pinAusgang']
                            self.localVars['AA'][_pin] = self.localVars['AN'][_pin]
                            if self.Ausgang[_pin]['round']:
                                _result = _result <> 0
                            if self.Ausgang[_pin]['isalpha'] and type(_result) <> str:
                                console_error("** Warnung falsches Format in Zeile %d f�r Ausgang %d" % ( formel['line'],_pin))
                                self.Errors['warning'] += 1
                            if self.Ausgang[_pin]['isalpha']:
                                if type(_result) <> str:
                                    _result = str(_result)
                            else:
                                _result = float(_result)
                            self.localVars['AN'][_pin] = _result
                            
                            if not self.Ausgang[_pin]['sbc'] or (self.localVars['AA'][_pin] <> self.localVars['AN'][_pin]):
                                self.localVars['AC'][_pin] = 1
                                if len(self.Ausgang[_pin]['ikos']) > 0:
                                    console_intern("*** sende an IKOs %r den Wert %s%s" % (self.Ausgang[_pin]['ikos'],Fore.YELLOW,repr(_result)[:40]))
                                for _iko in self.Ausgang[_pin]['ikos']:
                                    self.__sendKOGW(_iko,_result)
                            
                        _result = result
                        if formel['pinNegAusgang'] > 0:
                            _pin = formel['pinNegAusgang']
                            self.localVars['AA'][_pin] = self.localVars['AN'][_pin]
                            if self.Ausgang[_pin]['round']:
                                _result = float(not _result)
                            if not self.Ausgang[_pin]['isalpha']:
                                if type(_result) == str:
                                    console_error("** Warnung falsches Format in Zeile %d f�r Ausgang %d" % ( formel['line'],_pin))
                                    self.Errors['warning'] += 1
                                self.localVars['AN'][_pin] = float(_result *(-1))
                            self.localVars['AN'][_pin] = _result
                            if not self.Ausgang[_pin]['sbc'] or (self.localVars['AA'][_pin] <> self.localVars['AN'][_pin]):
                                if _result <> 0:
                                    self.localVars['AC'][_pin] = 1
                                    if len(self.Ausgang[_pin]['ikos']) > 0:
                                        console_intern("*** sende an IKOs %r den Wert %s%s" % (self.Ausgang[_pin]['ikos'],Fore.YELLOW,repr(_result)[:40]))
                                    for _iko in self.Ausgang[_pin]['ikos']:
                                        self.__sendKOGW(_iko,_result)
                        _result = result
                                
                        if formel['pinSpeicher'] > 0:
                            _pin = formel['pinSpeicher']
                            self.localVars['SA'][_pin] = self.localVars['SN'][_pin]
                            self.localVars['SN'][_pin] = _result
                            self.localVars['SC'][_pin] = 1
                            self.localVars['pItem'].SpeicherWert[_pin -1] = _result
                        
                        if formel['pinOffset'] > 0:
                            _pin = formel['pinOffset']
                            self.Offset[_pin][1] = _result
                            self.localVars['ON'][_pin] = _result
                            if offset > 0:
                                try:
                                    self.Offset[_pin][0] =  time.time() + offset
                                    #self.Offset[_pin][1] = _result
                                    _t = [_pin] + self.Offset[_pin]
                                    #try:
                                    ## cancel existierenden Trhead
                                    if self.Offset[_pin][2]:
                                        if self.Offset[_pin][2].is_alive():
                                            self.Offset[_pin][2].cancel()
                                    self.Offset[_pin][2] = hs_timer(offset,self.TimerCalc)
                                    self.Offset[_pin][2].setName("OC["+str(_pin)+"]")
                                    self.Offset[_pin][2].start()
                                    
                                    #except:
                                        #pass
                                    console_intern("*** setze Offset %s: %r" % (_pin,_t))
                                    console_intern("*** n�chster start: %s (%s sec)" % (time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(time.time()+offset)), offset))
                                except:
                                    console(Fore.RED + Style.BRIGHT + "*** Offset Fehler: Wert: %r" % offset)
                                    traceback.print_exc(file=sys.stdout)
                                    console(Style.RESET_ALL)
                            else:
                                try:
                                    self.Offset[_pin][2].cancel()
                                    self.Offset[_pin][0] = None
                                    #self.Offset[_pin][1] = None
                                    self.Offset[_pin][2] = None
                                except:
                                    console_error("Error stopping Timer %s" % (_pin,))
                                    pass
                                console_intern("Offset %s gel�scht" % (_pin,))
                                
                        
                        if formel['dobreak'] == 1:
                            console_info("*** Ausf�hrung nach Formelzeile abgebrochen ***")
                            break

                except:
                    console(Fore.RED + Style.BRIGHT + "Fehler beim ausf�hren von Formel in Zeile: %s" % formel['line'])
                    traceback.print_exc(file=sys.stdout)
                    console(Style.RESET_ALL)

            for _ac in xrange(1, len(self.localVars['AC']) ):
                if self.localVars['AC'][_ac] == 1:
                    console_intern("** schreibe AN[%s](%s) --> %s %r" % ( _ac,self.Ausgang[_ac].get('name',""), Fore.YELLOW,self.localVars['AN'][_ac] ))
                    self.localVars['AA'][_ac] = self.localVars['AN'][_ac]
                    if len(self.Ausgang[_ac]['ikos']) > 0:
                        console_intern("*** sende an IKOs %r den Wert %s" % (self.Ausgang[_ac]['ikos'],repr(self.localVars['AN'][_ac])[:40]))
                    for _iko in self.Ausgang[_ac]['ikos']:
                        self.__sendKOGW(_iko,self.localVars['AN'][_ac])

                    #self.localVars['AC'][_ac] = 0


            self.localVars['EI'] = 0
            for v in ["EC","SC","AC","OC"]:
              for i in range(1,len(self.localVars[v])):
                  self.localVars[v][i] = 0
        finally:
            self.mutex.release()


    
    ### HSL Parser ###
    def HSLparser(self,hslfile,console=console):
        fp = codecs.open(hslfile,"r")
        self.rawlines = fp.readlines()
        fp.close()
        hslinfo = re.findall(".*(1[0-9][0-9][0-9][0-9])(?:_|\s)(.*?).hsl",hslfile)
        if hslinfo:
            self.LogikNum, self.LogikName = hslinfo[0]
            self.LogikNum = int(self.LogikNum)
        console_info("lade Baustein {0}".format(hslfile))
        self._HSLparser(self.rawlines)
            
    def _HSLparser(self,lines,add_encrypted=False):
        numIn = numOut = 0
        firstLogikLine = False
        line5000 = 0
        line5001 = 0
        line5002 = 0
        line5003 = 0
        line5004 = 0
        line5012 = 0
        LineNum = 0
        if lines[0].find("-*- coding: iso8859-1 -*-") == -1 and not add_encrypted:
            console_error("*** Warnung *** Encoding Zeile f�r iso8859-1 fehlt")
            self.rawlines.insert(0,"# -*- coding: iso8859-1 -*-")
            self.Errors['warning'] += 1
        
        for line in lines:
            #line = line.decode("latin1","backslashreplace")
            line = re.sub("\r|\n","",line)
            LineNum +=1
            ## Experte Definitionszeile
            if line.startswith("5000|"):
                firstLogikLine = True
                if line5000:
                    console_error("*** Fehler *** Die 5000er Zeile wurde mehrfach definiert")
                    self.Errors['warning'] += 1
                line5000 += 1
                ## remove newline
                try:
                    _defline = line.split("|")
                    _name = unquote(_defline[1])
                    _catName = _name.split("\\")
                    self.LogikiName = _catName[-1]
                    self.LogikCat = "\\".join(_catName[:-1]) + "\\"
                    
                    self.isRemanent = int(int(_defline[2])==1)
                    numIn = int(_defline[3])
                    for i in range(0,numIn):
                        self.Eingang.append({'name':unquote(_defline[4+i]),'value':'','isalpha':True,'defined':False, 'ikos':[] })
                        self.localVars['EN'].append(None)
                        self.localVars['EC'].append(0)
                        self.localVars['EA'].append(None)
                    numOut = int(_defline[4+numIn])
                    for i in range(0,numOut):
                        self.Ausgang.append({'name':unquote(_defline[5+numIn+i]),'value':'','isalpha':True,'defined':False,'sbc':False,'round':False,'ikos':[]})
                        self.localVars['AN'].append(None)
                        self.localVars['AC'].append(0)
                        self.localVars['AA'].append(None)
                        self.localVars['pItem'].Ausgang.append([[],[HSIKOdummy(self,i+1)],[],[]])
                        self.localVars['pItem'].OutWert.append(None)
                except:
                    self.LogikError("5000",line,LineNum,console=console)
                    self.exitall(1)
                    
            ## HS Definitionszeile
            if line.startswith("5001|"):
                firstLogikLine = True
                if line5001:
                    console_error("*** Fehler *** Die 5001er Zeile wurde mehrfach definiert")
                    self.Errors['warning'] += 1
                line5001 += 1
                try:
                    _defline = line.split("|")
                    if numIn != int(_defline[1]):
                        console_error("*** 5001er und 5000er Eing�nge passen nicht ***")
                        self.exitall(1)
                    if numOut != int(_defline[2]):
                        console_error("*** 5001er und 5000er Ausg�nge passen nicht ***")
                        self.exitall(1)
                    numOffset = int(_defline[3])
                    for o in range(0,numOffset):
                        self.localVars['ON'].append(None)
                        self.localVars['OC'].append(0)
                        self.Offset.append([0,0,None])
                        self.localVars['Timer'].append(self.Offset[o+1])
                        self.localVars['pItem'].OutOfset.append([0,None])
                        
                    Speicher = int(_defline[4])
                    self.localVars['pItem'].LogikItem.AnzSpeicher = Speicher
                    for i in range(0,Speicher):
                        self.Speicher.append({'name':"%s" % (i+1,),'value':None,'isalpha':False,'defined':False,'remanent':False})
                        self.localVars['SN'].append(None)
                        self.localVars['SC'].append(0)
                        self.localVars['SA'].append(None)
                        self.localVars['pItem'].SpeicherWert.append(None)

                    self.runStart = int(_defline[5][0])
                    if len(_defline) > 6:
                        ## AES
                        self.iscrypted = int(_defline[6][0])
                except:
                    self.LogikError("5001",line,LineNum,console=console)
                    self.exitall(1)

            ## Eing�nge
            if line.startswith("5002|"):
                firstLogikLine = True
                line5002 += 1
                try:
                    _defline = line.split("|")
                    try:
                        ## :( Dacom Baustein Codeschloss ist nicht g�ltig :(
                        _isalpha = int(_defline[3][0]) == 1
                    except IndexError:
                        self.LogikError("5002",line,LineNum,msg='(fehlende Angabe)',console=console)
                        _isalpha = False
                    ## convert if string remove " '
                    try:
                        if len(_defline[2]) == 0:
                            _value = None
                        elif not _isalpha:
                            _f = re.findall("[+-]?\d+(?:\.\d+)?",_defline[2])
                            if _f:
                                _value = float(_f[0])
                        else:
                            _value = unquote(_defline[2])
                    except ValueError:
                        _value = unquote(_defline[2])
                    
                    if self.Eingang[int(_defline[1])]['defined'] == True:
                        console_error("*** Fehler *** Eingang %s wurde bereits definiert" % (_defline[1],))
                        raise TypeError
                    
                    self.Eingang[int(_defline[1])]['value'] = _value
                    self.Eingang[int(_defline[1])]['isalpha'] = _isalpha
                    self.Eingang[int(_defline[1])]['defined'] = True
                    self.localVars['EN'][int(_defline[1])] = _value
                    
                except:
                    self.LogikError("5002",line,LineNum,console=console)
                    self.exitall(-1)
        
            ## Speicher
            if line.startswith("5003|"):
                firstLogikLine = True
                line5003 += 1
                try:
                    _defline = line.split("|")
                    _isremanent = re.search("^([01])\s*(?:#|$)",_defline[3])
                    if not _isremanent:
                        console_error("*** Fehler *** Speicher %s Zeilenende enth�llt ung�ltige Zeichen" % (_defline[1],))
                        raise TyperError
                    _isremanent = int(_defline[3][0]) == 1
                    if _isremanent and not self.isRemanent:
                        console_error("\n*** Warnung *** Baustein ist nicht Remanent, hat aber Remanente Speicher\n")
                        self.Errors['warning'] += 1
                    _isalpha = False
                    try:
                        _value = eval(_defline[2])
                    except SyntaxError:
                        _value = None

                    _isalpha = type(_value) in [str]
                    if  int(_defline[1]) >= len(self.Speicher) :
                        console_error("*** Fehler *** Speicher %s nicht in 5001 definiert" %(_defline[1],))
                        raise IndexError
                    if self.Speicher[int(_defline[1])]['defined'] == True:
                        console_error("*** Fehler *** Speicher %s wurde bereits definiert" % (_defline[1],))
                        raise TyperError

                    self.Speicher[int(_defline[1])]['value'] = _value
                    self.Speicher[int(_defline[1])]['isalpha'] = _isalpha
                    self.Speicher[int(_defline[1])]['remanent'] = _isremanent
                    self.Speicher[int(_defline[1])]['defined'] = True
                    if _isalpha:
                        _empty = ""
                    else:
                        if _value <> None:
                            _empty = type(_value)(0)
                        else:
                            _empty = None
                    self.localVars['SN'][int(_defline[1])] = _value
                    self.localVars['pItem'].SpeicherWert[int(_defline[1])-1] = _value
                    self.localVars['pItem'].LogikItem.Speicher.append([_empty,int(_isremanent)])
                except:
                    self.LogikError("5003",line,LineNum,console=console)
                    self.exitall(-1)
        
            ## Ausg�nge
            if line.startswith("5004|"):
                firstLogikLine = True
                line5004 += 1
                try:
                    _defline = line.split("|")
                    try:
                        ## :( Dacom Baustein Codeschloss ist nicht g�ltig :(
                        _isalpha = int(_defline[5][0]) == 1
                    except IndexError:
                        _isalpha = False
                    ## convert if string remove " '
                    try:
                        if len(_defline[2]) == 0:
                            _value = None
                        elif not _isalpha:
                            _f = re.findall("[+-]?\d+(?:\.\d+)?",_defline[2])
                            if _f:
                                _value = float(_f[0])
                        else:
                            _value = unquote(_defline[2])
                    except ValueError:
                        _value = unquote(_defline[2])

                    if self.Ausgang[int(_defline[1])]['defined'] == True:
                        console_error("*** Fehler *** Ausgang %s wurde bereits definiert" % (_defline[1],))
                        raise TyperError

                    self.Ausgang[int(_defline[1])]['value'] = _value
                    self.Ausgang[int(_defline[1])]['round'] = int(_defline[3][0])==1
                    self.Ausgang[int(_defline[1])]['sbc'] = int(_defline[4][0])==2
                    self.Ausgang[int(_defline[1])]['isalpha'] = _isalpha
                    self.Ausgang[int(_defline[1])]['defined'] = True
                    self.localVars['AN'][int(_defline[1])] = _value
                except:
                    self.LogikError("5004",line,LineNum,console=console)
                    self.exitall(-1)

            if line.startswith("5012|"):
                line5012 += 1
                try:
                    _defline = re.findall("^(5012)\|([0|1])\|\x22(.*?)\x22\|\x22(.*?)\x22\|\x22(.*?)\x22\|(\d+)\|(\d+)\|(\d+)\|(\d+)",line)
                    _b64 = None
                    if _defline:
                        _defline = _defline[0]
                    else:
                        if len(line.split("|")) <> 9:
                            self.LogikError("5012",line,LineNum,msg='(nicht alle Felder)',console=console)
                        else:
                            self.LogikError("5012",line,LineNum,msg='(falscher Datentyp)',console=console)
                        continue
                    _dobreak = int(_defline[1])
                    if len(_defline[2])==0:
                        _case = "True"
                    else:
                        _case = _defline[2]
                        if re.findall("(?:\(| |\A)EI(?:\Z| |=|\))",_case) and not self.runStart:
                            console_error("\n*** Warnung *** es wird EI als Bedingung gewertet, obwohl der Baustein nicht beim Systemstart startet\n")
                            self.Errors['warning'] += 1
                        for _oc in re.findall("O[C|N]\[(\d+)\]",_case):
                            if int(_oc) > len(self.Offset) -1:
                                console_error("\n*** Fehler *** Timer OC[%s] gefunden aber nur %d Timer definiert\n" % (_oc,numOffset))
                                self.Errors['error'] += 1
                                self.exitall(1)
                    _caseCode = compile(_case,"Line:"+str(LineNum),"eval")
                    if len(_defline[3])==0:
                        _formel = "None"
                    else:
                        _formel = _defline[3]
                    if _formel.startswith("eval(compile(__import__('base64').decodestring('"):
                        _b64 = re.findall("decodestring\('(.*?)'\)",_formel)
                        if _b64:
                            try:
                                _b64 = base64.decodestring(_b64[0])
                                line = line.replace(_formel,"###BYTECODE###")
                            except:
                                console_error("Bytecode konnte nicht entschl�sselt werden")
                                
                                _b64 = None
                    _formelCode = compile("# -*- coding: iso-8859-1 -*-\n" + _formel,"Line:"+str(LineNum),"eval")
                    if len(_defline[4])==0:
                        _offset = "None"
                    else:
                        _offset = _defline[4]
                    _offsetCode = compile(_offset,"Line:"+str(LineNum),"eval")
                    _pinAusgang = int(_defline[5])
                    _pinOffset = int(_defline[6])
                    if _pinOffset > len(self.Offset) -1:
                        console_error("\n*** Fehler *** Ausgang auf Timer OC[%s] gesetzt aber nur %d Timer definiert\n" % (_pinOffset,numOffset))
                        self.Errors['error'] += 1
                        self.exitall(1)
                    _pinSpeicher = int(_defline[7])
                    _pinNegAusgang = int(_defline[8])
                    self.Formel.append(
                      {
                      #'pinAusgang': _pinAusgang,
                      #'pinOffset': _pinOffset,
                      #'pinSpeicher': _pinSpeicher,
                      #'pinNegAusgang': _pinNegAusgang,
                      'bytecode' : _b64,
                      'rawline' : line,
                      'dobreak':_dobreak,
                      'line': LineNum,
                      'case':_case,
                      'caseCode':_caseCode,
                      'formel':_formel,
                      'formelCode':_formelCode,
                      'offset':_offset,
                      'offsetCode':_offsetCode,
                      'pinAusgang':_pinAusgang,
                      'pinSpeicher':_pinSpeicher,
                      'pinOffset':_pinOffset,
                      'pinNegAusgang':_pinNegAusgang
                      })
                except:
                    self.LogikError("5012",line,LineNum,console=console)
                    #__import__('traceback').print_exc(file=__import__('sys').stdout)
                    self.exitall(1)

            if not firstLogikLine:
                self.LogikHeader.append(line)
        
        if not add_encrypted:
            #print numIn,line5002,self.Eingang
            #if numIn <> len(self.Eingang)-1:
            if numIn <> line5002:
                console_error("*** Fehler *** Nicht alle Eing�nge sind definiert (%s)" % (",".join(map(lambda x: x['name'],filter(lambda x: not x['defined'],self.Eingang[1:])))))
                self.exitall(-1)
            #if numOut <> len(self.Ausgang)-1:
            if numOut <> line5004:
                console_error("*** Fehler *** Nicht alle Ausg�nge sind definiert (%s)" % (",".join(map(lambda x: x['name'],filter(lambda x: not x['defined'],self.Ausgang[1:])))))
                self.exitall(-1)
            #if Speicher <> len(self.Speicher)-1:
            if Speicher <> line5003:
                console_error("*** Fehler *** Nicht alle Speicher sind definiert (%s)" % (",".join(map(lambda x: x['name'],filter(lambda x: not x['defined'],self.Speicher[1:])))))
                self.exitall(-1)
        
        if self.iscrypted and not add_encrypted:
            return

        if self.Errors['error'] == 0:
            console("*** Keine Fehler gefunden ****")
        else:
            console_error("*** {0} Fehler gefunden ***".format(self.Errors['error']))
        
        if self.Errors['warning'] > 0:
            console_error("*** {0} Warnungen gefunden ***".format(self.Errors['warning']))

    def build(self,fname):
        console_info("Rebuild hsl as {0}".format(fname))
        with open(fname,"wt") as f:
            f.write("\n".join([x.rstrip("\n").rstrip("\r") for x in self.rawlines]))

    def extcompile(self,compiler,code,desc): 
        from tempfile import mkstemp
        _basecode = ""
        try:
            try:
                _fh,_fname = mkstemp(suffix='.tmp',prefix="LGT_compile-")
                console("tempor�re Datei '%s' erstellt" % _fname)
                _fp = open(_fname,"w")
                _fp.write(code)
                _fp.close()
                os.close(_fh)
                #_cstdout,_cstdin,_cstderr = popen2.popen3(compiler + " -c \"import base64;import marshal;print base64.encodestring(marshal.dumps(compile(open(base64.decodestring('"+re.sub("\n","",base64.encodestring(_fname))+"')).read(),'"+desc+"','exec')))\"")
                _basecode = _cstdout.read()
                _err = _cstderr.read()
                _cstdout.close()
                _cstdin.close()
                _cstderr.close()
            except:
                console_error("*** externer Compiler Fehler ***")
                return False
        finally:
            os.remove(_fname)
            console_debug("tempor�re Datei '%s' gel�scht" % _fname)
            return re.sub("\n","",_basecode)

    def createLGT(self):
        lgtfile = "%d_%s.LGT"  % (self.LogikNum,self.LogikName)
        
        console_info("erstelle LGT Datei %s" % lgtfile)
        
        fp = codecs.open(lgtfile,"w")
        
        fp.write(self.getHeader()+"\n")
        fp.write("\n\n## Using Logik Generator\n")
        fp.write("from "+sys.argv[0][:-3]+" import *\n\n\n")
        fp.write("LGT.Header(\"\"\"\n")
        fp.write("\n".join(self.LogikHeader))
        fp.write("\n\n")
        ## Write 5000er
        fp.write("5000|\"" + self.LogikCat + self.LogikName + "\"|" +str(int(self.isRemanent == 1))+"|" + str(len(self.Eingang[1:])) + "|\"" + "\"|\"".join([o['name'] for o in LGT.Eingang[1:]]) + "\"|" + str(len(self.Ausgang[1:])) + "|\"" + "\"|\"".join([o['name'] for o in LGT.Ausgang[1:]]) +"\"\n") 
        
        ## write 5001er
        fp.write("5001|"+ str(len(self.Eingang[1:])) + "|" + str(len(self.Ausgang[1:])) + "|" + str(len(self.Offset[1:])) + "|" + str(len(self.Speicher[1:])) + "|" + str(self.runStart) + "\n")
        
        n=1
        fp.write("\n\n")
        for _e in self.Eingang[1:]:
            fp.write("5002|"+str(n)+"|" +quoteVal(_e) + "|" +str(int(_e['isalpha'] == 1)) + "   ## " + _e['name'] + "\n")
            n += 1

        fp.write("\n\n")
        n=1
        for _s in self.Speicher[1:]:
            fp.write("5003|"+str(n)+"|" +quoteVal(_s) + "|" +str(int(_s['remanent'] == 1)) + "   ## \n")
            n += 1
        fp.write("\n\n")
        n=1
        for _a in self.Ausgang[1:]:
            fp.write("5004|"+str(n)+"|" +quoteVal(_a) + "|" +str(int(_a['round'] == 1)) + "|" +str(int(_a['sbc'] == 1)) + "|" +str(int(_a['isalpha'] == 1)) + "   ## " + _a['name'] + "\n")
            n += 1
        fp.write("\n\n")
        fp.write("\"\"\")")

        fp.write("\n\n\n\n")
        for _f in self.Formel:
            fp.write("LGT.addFormel(\"5012\","+str(_f['dobreak'])+ ",\"" +_f['case']+ "\",\"" +_f['formel'] + "\",\"" +_f['offset']+ "\"," +str(_f['pinAusgang'])+ ","  +str(_f['pinOffset'])+ "," +str(_f['pinSpeicher'])+ ","  +str(_f['pinNegAusgang'])+ ")")
            fp.write("\n\n")
        
        fp.write("\n\n")
        
        

        fp.write("\n\n#### Compiler und Debugger ####\n")
        fp.write("Finish()")
        
        
        fp.close()
    def addFormel(self,_def,_dobreak,_case,_formel,_offset,_pinAusgang,_pinOffset,_pinSpeicher,_pinNegAusgang,ByteCode=0):
        LineNum = len(self.Formel)
        numOffset = len(self.Offset)

        if len(_case)==0:
            _case = "True"
        if re.findall("(?:\(| |\A)EI(?:\Z| |=|\))",_case) and not self.runStart:
            console_error("\n*** Warnung *** es wird EI als Bedingung gewertet, obwohl der Baustein nicht beim Systemstart startet\n")
            self.Errors['warning'] += 1
        for _oc in re.findall("O[C|N]\[(\d+)\]",_case):
            if int(_oc) > numOffset:
                console_error("\n*** Warnung *** Timer OC[%s] gefunden aber nur %d Timer definiert\n" % (_oc,numOffset))
                self.Errors['warning'] += 1
        _caseCode = compile(_case,"Case-Line:"+str(LineNum),"eval")
        if len(_formel)==0:
            _formel = "None"
        _formelCode = compile(_formel,"Formel-Line:"+str(LineNum),"eval")
        if len(_offset)==0:
            _offset = "None"
        _offsetCode = compile(_offset,"Offset-Line:"+str(LineNum),"eval")
        if _pinOffset > numOffset:
            console_error("\n*** Warnung *** Ausgang auf Timer OC[%s] gesetzt aber nur %d Timer definiert\n" % (_pinOffset,numOffset))
            self.Errors['warning'] += 1


        
        self.Formel.append(
          {
          #'pinAusgang': _pinAusgang,
          #'pinOffset': _pinOffset,
          #'pinSpeicher': _pinSpeicher,
          #'pinNegAusgang': _pinNegAusgang,
          'dobreak':_dobreak,
          'line': LineNum,
          'case':_case,
          'caseCode':_caseCode,
          'formel':_formel,
          'formelCode':_formelCode,
          'offset':_offset,
          'offsetCode':_offsetCode,
          'pinAusgang':_pinAusgang,
          'pinSpeicher':_pinSpeicher,
          'pinOffset':_pinOffset,
          'pinNegAusgang':_pinNegAusgang
          })
        ## TODO
        
LGT = LogikGeneratorClass()

def Finish():
    print (sys.argv)
    LGT._HSLparser(LGT.LogikHeader)
    parseCommandLine()

class Tee(object):
    def __init__(self, name, mode):
        self.TEE = True
        self.ANSI_RE = re.compile("(\001?\033\[((?:\d|;)*)([a-zA-Z])\002?)")
        self.LOG_RE = re.compile("(^>>\s\w+|\w+)",re.MULTILINE )
        self.mutex = threading.Lock()
        self.file = codecs.open(name, mode,encoding='latin1')
        self.stdout = sys.stdout
        self.encoding = self.stdout.encoding
        print "Ausgabe in Logfile {0}".format(name)
        sys.stdout = self
        sys.dummy = True
    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()
    def write(self, data):
            self.stdout.write(data)
            self.stdout.flush()
            self.log(data)

    def log(self,data):
        try:
            self.mutex.acquire()
            if len(data.strip()) >0 and self.LOG_RE.search(data):
                if Style.RESET_ALL <> "":
                    data = self.ANSI_RE.sub("",data)
                _timestamp = datetime.now().strftime("%H:%M:%S.%f")
                data = data.decode(sys.stdout.encoding)
                data = u"{0} {1}\n".format(_timestamp[:12],data)
                self.file.write(data)
                self.file.flush()
        finally:
            self.mutex.release()

def parseCommandLine():
    _cmds = []
    configFile = os.path.join(sys.path[0],"LogikGen.config")
    argautorun = 0
    import getopt
    
    opts, args = getopt.getopt(sys.argv[1:],"a:n:l:i:b:dg",["autorun=","new=","import=","log=","debug","b64decode","config=","build="])
    for opt,arg in opts:
        if opt in ("-i","--import"):
            if os.path.isfile(arg):
                importfilename = arg
                _configFile = os.path.join( os.path.dirname(arg), "LogikGen.config")
                if os.path.isfile(_configFile):
                    configFile = _configFile
                _cmds.append("import")
            else:
                if len(arg) <1:
                    console_error("Kein Import File angegeben")
                else:
                    console_error("Import File %r nicht gefunden" % arg)

        elif opt in ("-n","--new"):
            _hslinfo = re.findall(".*(1[0-9][0-9][0-9][0-9])_(.*)",arg)
            _logiknum = False
            _logikname = False
            if _hslinfo:
                _logiknum = int(_hslinfo[0][0])
                _logikname = _hslinfo[0][1]
            _cmds.append("create")

        elif opt in ("-l","--log"):
            Tee(arg,"a+")

        elif opt in ("-d","--debug"):
            _cmds.append("debug")

        elif opt in ("-b","--build"):
            buildfile = arg
            if os.path.isfile(buildfile):
                if raw_input("Datei {0} existiert bereits. �berschreiben (j/n)?".format(arg)) != "j":
                    sys.exit(1)
            _cmds.append("build")
            
        elif opt in ("-a","--autorun"):
            _cmds.append("autorun")
            argautorun = int(arg == "1")

        elif opt in ("-g"):
            _cmds.append("kogw")

        elif opt in ("--b64decode"):
            LGT.Options['decode'] = True

        elif opt in ("--config"):
            configFile = arg
        else:
            console_error("unbekannte Option")
            sys.exit(0)
    if "import" in _cmds:
        LGT.HSLparser(importfilename)
    if "build" in _cmds:
        LGT.build(buildfile)
    if "create" in _cmds:
        if _logiknum:
            LGT.LogikNum = _logiknum
        if _logikname:
            LGT.LogikName = _logikname
        LGT.createLGT()

    #console(LGT.LogikNum)
    if "debug" in _cmds:
        LGT.readConfig(configFile)    
    
    if "autorun" in _cmds:
        LGT.AutoRun = argautorun
    if "debug" in _cmds:
        if "kogw" in _cmds:
            LGT.connectKOGW()
            time.sleep(0.5)
        LGT.LogikDebug()
    
    
if __name__ == "__main__":
    print Fore.WHITE,Back.BLACK,Style.RESET_ALL
    try:
        parseCommandLine()
    except SystemExit:
        pass
    except:
        print (Fore.RED + Style.BRIGHT + "Error Prozessing")
        traceback.print_exc(file=sys.stdout)
        time.sleep(5)
    print Fore.WHITE,Back.BLACK,Style.RESET_ALL,
    sys.exit(0)
