# -*- coding: iso8859-1 -*-
## -----------------------------------------------------
## Logik-Generator  V2.014
## -----------------------------------------------------
## Copyright © 2011, knx-user-forum e.V, All rights reserved.
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

LGTVERSION = 2.014

#######################
### Changelog #########
#######################
## 2.014 * interne IP

## 2.013 * diverse HS interne Objekte hinzugefügt
##       * überwachung von AC[x] auf änderungen
##       * __import__ gegen Funktion ausgetauscht um hs interne Module zu imitieren
##       * KO Gateway Verbindung timeout geändert
##       * eingaben string-decode um zum Beispiel bei EN[1]="d100=1\x03" das Steuerzeichen hex 03 zu senden
##       * Fix Ausgang beim internen schreiben über SetWert des iko
##       * --register nun je Python Version (Debug 2.4/Debug 2.6)
##
## 2.012 * runTime je Formelzeile
##       * --register zum registrieren der Debug Erweiterung für .hsl Dateien
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
##       * globals werden nicht mehr an die Formel übergeben
##       * Zeilenummer beim Bedingungstest
##       * Autorun per .config default und pro LogikID
##       * Autorun override per Befehlszeile -a 1|0
##
## 2.007 * Bugfixes KO-Gateway
##       * AutoRUn
##
## 2.006 * KO-Gateway für Ein/ausgänge
##
## 2.005 * Anzeige auf SystemCodepage angepasst, sodass Umlaute angezeigt werden
##       * Option -n zum erstellen von .LGT Dateien aus .hsl
##       * Kontrollen für EI bei nicht startetenden Bausteinen
##       * Kontrolle auf Remanente Speicher bei nicht Remanenten Baustein
##       * Kontrolle der Timer Anzahl
##
## 2.004 * BugFixes _defline
##       * einige Dacom Bausteine (z.B. Codeschloss) haben keine gültige Definition
##
## 2.003 * 'names' zeigen jetzt auch die derzeitigen Werte
##       * LogikGen.config hinzugefügt
##       * Ausgang von intern beschreiben
##       * Ausgaben auf Deutsch
##
## 2.002 * Parse Error in der 5001er Zeile
##       * einige interne HS Klassen hinzugfügt
##       * Timer ON/OC werden unterstützt
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
import time
import threading
import socket
import select
import ConfigParser
import popen2
import zlib
import zipfile
import traceback
import Queue

##  Weil der HS zu viele alte Module erwartet ;) so einfach könnte auch der HS diese blöden Meldungen nicht an der Konsole zeigen.
import warnings
warnings.simplefilter("ignore",DeprecationWarning)

##############
### Config ###
##############


## kleine Hilfsfunktionen
def debug(msg):
    print msg
def console(msg):
    if type(msg) <> str:
        msg = str(msg)
    print msg.decode("iso-8859-1").encode(sys.stdout.encoding)


def unquote(text):
    ## entfernt die Anführungszeichen
    if type(text) <> str:
        try:
            text = str(text)
        except:
            return ""
    return re.sub("^[\"|\']|[\"|\']$","",text)

def quoteVal(e):
    ## setzt Anführungszeichen wenn typ string
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
    Daten = []
    def setErr(self,pException,pComment):
        print "Error:"
        traceback.print_exception(pException[0],pException[1],pException[2],file=sys.stdout)
        print pComment
    def setErrDirekt(self,pText):
        print "Error: %r" % pText
    def addGruppe(self,pGruppe,pItems):
        print "addGruppe %r with Items %r" % (pGruppe,pItems)
    def setWert(self,pGruppe,pToken,pWert):
        print "setWert %s - %s to %r" % (pGruppe,pToken,pWert)
    def addWert(self,pGruppe,pToken,pWert):
        print "addWert %s - %s to %r" % (pGruppe,pToken,pWert)

class HSIKOdummy:
    def __init__(self,LGT,attached_out):
        self.LGT = LGT
        self.Value = ''
        self.Format = 22
        self.SpeicherID = 1
        self._attached_out = attached_out
    def setWert(self,out,wert):
        self.Value = wert
        console("** intern ** auf AN[%d]: %s" % (self._attached_out,repr(wert)))
        self.LGT.setVar("AN",self._attached_out,wert)
    def getWert(self):
        return self.Value
    def checkLogik(self,out):
        pass

__old_import__ = __import__

class hs_queue_queue(Queue.Queue):
    def put(self,item):
        Queue.Queue.put(self,[time.time(),item])
    def get(self):
        return Queue.Queue.get(self)[1]


class hs_queue(object):
    Queue = hs_queue_queue
    hs_threading = threading
  
sys.modules['hs_queue'] = hs_queue
#def __import__(module):
#    print "LOAD Module %r" % module
#    if module in ['hs_queue']:
#        return globals().get(module)
#    return __old_import__(module)

def get_local_ip():
    _ip = socket.gethostbyname( socket.gethostname() )
    if _ip.startswith("127"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 0))
        _ip = s.getsockname()[0]
        s.close()
    return _ip
       
###########################


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
        self.bCode = []
        self.Options = { 'decode':False,'strict':False}
        self.Errors = {'warning':0, 'error':0}
        
        self.KOGW = {'running':False,'thread':None,'socket':None,'hsip': '','gwport':0,'gwsecret': ''}
        self.KOGWInObj = {}
        self.AutoRun = True
        
        self.mutex = threading.RLock()
        ## some dummy Vars 
        _mc = HomerServerDummy()
        _mc.SystemID = "0123456789ab"
        _mc.ProjectID = time.strftime("%Y%m%d%H%M%S000",time.localtime())
        
        ## GUI
        _mc.GUI = dummy()
        _mc.GUI.ExtDatUrl = {}
        
        ## LogikList
        _mc.LogikList = dummy()
        _mc.LogikList.calcLock = threading.RLock()
        _mc.LogikList.GatterList = []
        
        ## KameraList
        _mc.KameraList = dummy()
        _mc.KameraList.KamList = {}

        ## IP
        _mc.Ethernet = dummy()
        _mc.Ethernet.IPAdr = get_local_ip()
        
        ## Default HS Resolver
        _mc.DNSResolver = dummy()
        _mc.DNSResolver.getHostIP = socket.gethostbyname
        
        ## Debug
        _mc.Debug = debug_dummy()
        
        ## HS self dummy
        _HSself = HSLogikSelfDummy()
        _HSself.MC = _mc
        _HSself.ID = self.LogikNum
        _HSself.makeCheckSum = lambda x: md5(x).hexdigest()

        
        ## HS Logik dummy
        _pItem = HSLogikItemDummy()
        _pItem.MC = _mc
        _pItem.ID = 1
        _pItem.Ausgang = []
        
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
        self.globalvars = globals()
    
    
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
            ## überprüft auch die alternativen Varianten
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
                console("Variablen Kollision :" +repr(i[2])+" ist in " +repr(symbols[sym]) + " und  "+ varName +"["+i[1]+"] vergeben")
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
        print "Removed" 
        console("\n".join(removelist))
        return "\n".join(codelist)
    
    def compileMe(self,code):
        pass
    
    def readConfig(self,configFile):
        self.Licences = {}
        configparse = ConfigParser.SafeConfigParser()
        configparse.read(configFile)
        #for _lic in configparse.options("licences"):
        #    self.Licences[_lic] = configparse.get("licences",_lic)
        console("Looking for %r Config" % self.LogikNum)
        try:
            self.AutoRun = configparse.getboolean('default','autorun')
        except (ConfigParser.NoOptionError,ConfigParser.NoSectionError):
            pass
        if configparse.has_section(str(self.LogikNum)):
            console("Found Config for %r" % self.LogikNum)
            try:
                self.AutoRun = configparse.getboolean(str(self.LogikNum),'autorun')
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
                                    console("** Setze IKO %s auf EN[%d]" % (_val[5:],int(_defSet[1])))
                                elif _defSet[0].upper() == "AN":
                                    self.Ausgang[int(_defSet[1])]['ikos'].append(_val[5:])
                                    console("** Setze IKO %s auf AN[%d]" % (_val[5:],int(_defSet[1])))
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
            console("*** KO-Gateway schon verbunden ***")
            return
        self.KOGW['thread'] = threading.Thread(target=self.__connectKOGW)
        self.KOGW['running'] = True
        self.KOGW['thread'].setDaemon(True)
        self.KOGW['thread'].start()
    
    def __connectKOGW(self):
        while self.KOGW['running']:
            try:
                if not self.KOGW['socket']:
                    try:
                        self.KOGW['socket'] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                        self.KOGW['socket'].connect((self.KOGW['hsip'],self.KOGW['gwport']))
                        self.KOGW['socket'].send(self.KOGW['gwsecret']+"\x00")
                        console("*** Verbindung zum KO-Gateway hergestellt ***")
                        self.__readKOGW()
                    except:
                        __import__('traceback').print_exc(file=__import__('sys').stdout)
                        console("*** Fehler beim verbinden zum KO-Gateway des HS: %s:%d" % (self.KOGW['hsip'],self.KOGW['gwport']))
                if not self.KOGW['running']:
                    break
                _t = 0
                while self.KOGW['running'] and _t < 20:
                    _t += 1
                    time.sleep(0.5)
            finally:
                console("*** Verbindung zum KO-Gateway getrennt ***")
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
                __import__('traceback').print_exc(file=__import__('sys').stdout)
                pass

    def LogikError(self,typ,line,LineNum,msg=" ",console=console):
        if typ == "5000":
            console("*** Fehler bei Experte Definition 5000: %d %s***" % (LineNum,msg))
            console("#5000|\"Text\"|Remanent(1/0)|Anz.Eingänge|.n.|Anzahl Ausgänge|.n.|.n.")
        elif typ == "5001":
            console("*** Fehler bei HS Logik Definition 5001: %d %s***" % (LineNum,msg))
            console("#5001|Anzahl Eingänge|Ausgänge|Offset|Speicher|Berechnung bei Start")
        elif typ == "5002":
            console("*** Fehler bei Eingangsdefinition 5002: %d %s***" % (LineNum,msg))
            console("#5002|Index Eingang|Default Wert|0=numerisch 1=alphanummerisch")
        elif typ =="5003":
            console("*** Fehler bei Speicherdefinition 5003: %d %s***" % (LineNum,msg))
            console("#5003|Speicher|Initwert|Remanent")
        elif typ =="5004":
            console("*** Fehler bei Ausgangsdefinition 5004: %d %s***" % (LineNum,msg))
            console("#5004|ausgang|Initwert|runden binär (0/1)|typ (1-send/2-sbc)|0=numerisch 1=alphanummerisch")
        elif typ =="5012":
            console("*** Fehler bei Formel Definition 5012: %d %s***" % (LineNum,msg))
            console("#5012|abbruch bei bed. (0/1)|bedingung|formel|zeit|pin-ausgang|pin-offset|pin-speicher|pin-neg.ausgang")
        else:
            print "TYPE %r" % typ
        console("--------------------------------------------------------------------------")
        console(line)
        console("--------------------------------------------------------------------------")
        #__import__('traceback').print_exc(file=__import__('sys').stdout)
        if self.Options['strict']:
            self.exitall(1)
    
    def exitall(self,_r):
        if _r > 0:
            __import__('traceback').print_exc(file=__import__('sys').stdout)
        if self.KOGW['running']:
            self.KOGW['running'] = False
            console("** Warte auf KO-Gateway *** ")
            self.KOGW['thread'].join()
        
        for _t in self.Offset:
            try:
                _t[2].cancel()
            except:
                pass
        for _thread in threading.enumerate():
            if _thread <> threading.currentThread():
                try:
                    print "kill Thread: %r" % (_thread.name)
                    _thread._Thread__stop()
                    _thread.join(2)
                except:
                    pass
        time.sleep(2)
        sys.exit(int(_r <> 0))


    def LogikDebug(self):
        console("\n\n### Logik Debugger ###\n")
        
        if self.AutoRun and self.runStart:
            self.LogikCalc()
        while True:
            try:
                _cmd = raw_input(">> ")
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
                    console("%s: %r" % (v,self.localVars[v]))
            elif _lcmd.startswith("connect"):
                self.connectKOGW()
            elif _lcmd.startswith("names"):
                console("Systemstart: % d Remanent: %d" % (self.runStart,self.isRemanent))
                try:
                    for v in range(1,len(self.Eingang)):
                        _iko = ""
                        if self.Eingang[v]['ikos']:
                            _iko = "[" + repr(self.Eingang[v]['ikos']) + "]"
                        console("EN[%d]: %s (%s) %s" % (v,self.Eingang[v]['name'],repr(self.localVars['EN'][v])[:30], _iko))
                    for v in range(1,len(self.Ausgang)):
                        _iko = ""
                        if self.Ausgang[v]['ikos']:
                            _iko = "[" + repr(self.Ausgang[v]['ikos']) + "]"
                        console("AN[%d]: %s (%s) %s" % (v,self.Ausgang[v]['name'],repr(self.localVars['AN'][v])[:30],_iko))
                except:
                    console("*** Fehler ... ***")
                    self.exitall(1)
                    pass
            
            elif _lcmd.startswith("run"):    
                self.LogikCalc()
            
            elif _lcmd.startswith("autorun"):    
                _sw = re.findall("autorun (\d)",_lcmd)
                if _sw:
                    _sw = (int(_sw[0]) == 1)
                self.AutoRun = _sw
            elif _lcmd.startswith("help") or _cmd.startswith("hilfe"):
                console("\nLogik Debugger Hilfe")
                console("--------------------\n")
                console("'quit' oder 'exit' zum beenden")
                console("'show' um die Variablen anzuzeigen")
                console("'names' zeigt die Namen der Ein-/Ausgänge an")
                console("'run' um die Logik auszuführen")
                console("'autorun [0/1]' autorun ein/aus")
                console("'timer 1' lässt Timer OC[1]/ON[1] ablaufen")
                console("'connect' verbinden zum definierten KO Gateway")
                console("'exec [code]' ausführen von python Code innerhalb der Logik")
                console("'EN[1]=23' um Eingang 1 den Wert 23 zu setzen")
                console("-- es können EI,EN,SN,AN,ON sowie EC,SC,AC,OC als auch EA,SA,AA")
                console("-- geändert werden. Bei den ersten wird automatisch das jeweilige xC gesetzt")
                console("")
            elif _lcmd.startswith("exec "):
                try:
                    eval(compile(_cmd[5:],"ldebug","exec"),{'LGT':LGT},self.localVars)
                except:
                    __import__('traceback').print_exc(file=__import__('sys').stdout)
                    
            elif _lcmd.startswith("timer "):
                t = re.findall("\d+",_cmd)
                if t:
                    t=t[0]
                    if type(t) in (list,tuple):
                        t=t[0]
                    t=int(t)
                    _v = self.Offset[t][1]
                    try:
                        self.Offset[t][2].cancel()
                    except:
                        pass
                    #self.Offset[t] = (time.time()-1,_v)
                    self.Offset[t][0] = time.time()-1
                    console("Set Offset: %r" % (self.Offset[t],))
            elif _lcmd.startswith("ei="):
                if _cmd[3] == "1":
                    self.localVars['EI'] = 1
                else:
                    self.localVars['EI'] = 0
            else:
                _var = re.findall("^([O|E|S|A|o|e|s|a][N|n|A|a|C|c])\[([0-9]{1,2})\]=(.*)",_cmd)
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
                                console("** Setze IKO %s auf EN[%d]" % (_val[5:],_vnum))
                            elif __vname == "AN":
                                self.Ausgang[_vnum]['ikos'].append(_val[5:])
                                console("** Setze IKO %s auf AN[%d]" % (_val[5:],_vnum))
                        except:
                            __import__('traceback').print_exc(file=__import__('sys').stdout)
                            pass
                    else:
                        self.setVar(_vname,_vnum,_val.decode('string-escape'))


                else:
                    console("*** unbekannter Befehl - tippe help für Hilfe ***")
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
                                console("*** sende an IKOs %r den Wert %s" % (self.Ausgang[_vnum]['ikos'],repr(_val)[:40]))
                            for _iko in self.Ausgang[_vnum]['ikos']:
                                self.__sendKOGW(_iko,_val)
                        self.localVars[_cvar][_vnum] = 1
                self.localVars[_vname][_vnum] = _val
            finally:
                #self.mutex.release()
                pass
        except:
            console(repr(self.localVars))
            console("Fehler beim beschreiben der Variablen")
            __import__('traceback').print_exc(file=__import__('sys').stdout)
    
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
                    console("teste Bedingung in Zeile %d: %r" % (formel['line'],self.stripline(formel['case'])))
                    startRunTime = time.clock()
                    if eval(formel['caseCode'],self.globalvars,self.localVars):
                        console("starte Formel: %r" % (self.stripline(formel['formel'])))
                        result = eval(formel['formelCode'],self.globalvars,self.localVars)
                        offset = eval(formel['offsetCode'],self.globalvars,self.localVars)
                        runTime = time.clock() - startRunTime
                        console("RunTime: %f" % (runTime))
                        console("Ausgabe: %d|%d|%d|%d" % (formel['pinAusgang'],formel['pinOffset'],formel['pinSpeicher'],formel['pinNegAusgang']))
                        console("Ergebnis: %r" % (result,))
                        console("-------")
                        
                        _result = result
                        if formel['pinAusgang'] > 0:
                            _pin = formel['pinAusgang']
                            self.localVars['AA'][_pin] = self.localVars['AN'][_pin]
                            if self.Ausgang[_pin]['round']:
                                _result = _result <> 0
                            if self.Ausgang[_pin]['isalpha'] and type(_result) <> str:
                                print type(_result)
                                console("** Warnung falsches Format in Zeile %d für Ausgang %d" % ( formel['line'],_pin))
                            if self.Ausgang[_pin]['isalpha']:
                                _result = str(_result)
                            else:
                                _result = float(_result)
                            self.localVars['AN'][_pin] = _result
                            
                            
                            if not self.Ausgang[_pin]['sbc'] or (self.localVars['AA'][_pin] <> self.localVars['AN'][_pin]):
                                self.localVars['AC'][_pin] = 1
                                if len(self.Ausgang[_pin]['ikos']) > 0:
                                    console("*** sende an IKOs %r den Wert %s" % (self.Ausgang[_pin]['ikos'],repr(_result)[:40]))
                                for _iko in self.Ausgang[_pin]['ikos']:
                                    self.__sendKOGW(_iko,_result)
                            
                        _result = result
                        if formel['pinNegAusgang'] > 0:
                            _pin = formel['pinNegAusgang']
                            self.localVars['AA'][_pin] = self.localVars['AN'][_pin]
                            if self.Ausgang[_pin]['round']:
                                _result = _result <> 0
                            if not self.Ausgang[_pin]['isalpha']:
                                if type(_result) == str:
                                    console("** Warnung falsches Format in Zeile %d für Ausgang %d" % ( formel['line'],_pin))
                                self.localVars['AN'][_pin] = float(_result *(-1))
                            if not self.Ausgang[_pin]['sbc'] or (self.localVars['AA'][_pin] <> self.localVars['AN'][_pin]):
                                if _result <> 0:
                                    self.localVars['AC'][_pin] = 1
                                    if len(self.Ausgang[_pin]['ikos']) > 0:
                                        console("*** sende an IKOs %r den Wert %s" % (self.Ausgang[_pin]['ikos'],repr(_result)[:40]))
                                    for _iko in self.Ausgang[_pin]['ikos']:
                                        self.__sendKOGW(_iko,_result)
                                
                        _result = result
                        for _ac in xrange(1, len(self.localVars['AC']) ):
                            if self.localVars['AC'][_ac] == 1:
                                console("** AC[%s] <> 0 schreibe AN[%s] %r" % ( _ac,_ac, self.localVars['AN'][_ac] ))
                                self.localVars['AC'][_ac] = 0
                                
                        if formel['pinSpeicher'] > 0:
                            _pin = formel['pinSpeicher']
                            self.localVars['SA'][_pin] = self.localVars['SN'][_pin]
                            self.localVars['SN'][_pin] = _result
                            self.localVars['SC'][_pin] = 1
                        
                        if formel['pinOffset'] > 0:
                            _pin = formel['pinOffset']
                            if offset >0:
                                try:
                                    self.Offset[_pin][0] =  time.time() + offset
                                    self.Offset[_pin][1] = _result
                                    _t = [_pin] + self.Offset[_pin]
                                    #try:
                                    self.Offset[_pin][2] = threading.Timer(offset,self.TimerCalc)
                                    self.Offset[_pin][2].setName("OC["+str(_pin)+"]")
                                    self.Offset[_pin][2].start()
                                    
                                    #except:
                                        #pass
                                    console("*** setze Offset %s: %r" % (_pin,_t))
                                    console("*** nächster start: %s (%s sec)" % (time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(time.time()+offset)), offset))
                                except:
                                    console("*** Offset Fehler: Wert: %r" % offset)
                                    __import__('traceback').print_exc(file=__import__('sys').stdout)
                            else:
                                console("Offset %s gelöscht" % (_pin,))
                        
                        if formel['dobreak'] == 1:
                            console("*** Ausführung nach Formelzeile abgebrochen ***")
                            break

                except:
                    console("Fehler beim ausführen von Formel in Zeile: %s" % formel['line'])
                    __import__('traceback').print_exc(file=__import__('sys').stdout)

            self.localVars['EI'] = 0
            for v in ["EC","SC","AC","OC"]:
              for i in range(1,len(self.localVars[v])):
                  self.localVars[v][i] = 0
        finally:
            self.mutex.release()


    
    ### HSL Parser ###
    def HSLparser(self,hslfile,console=console):
        fp = codecs.open(hslfile,"r")
        lines = fp.readlines()
        fp.close()
        hslinfo = re.findall(".*(1[0-9][0-9][0-9][0-9])_(.*?).hsl",hslfile)
        if hslinfo:
            self.LogikNum, self.LogikName = hslinfo[0]
            self.LogikNum = int(self.LogikNum)
        self._HSLparser(lines)

    def _HSLparser(self,lines):
        numIn = numOut = 0
        firstLogikLine = False
        line5000 = 0
        line5001 = 0
        line5002 = 0
        line5003 = 0
        line5004 = 0
        line5012 = 0
        LineNum = 0
        for line in lines:
            #line = line.encode("iso-8859-1","backslashreplace")
            #line.decode("iso-8859-1")
            line = re.sub("\r|\n","",line)
            LineNum +=1
            ## Experte Definitionszeile
            if line.startswith("5000|"):
                firstLogikLine = True
                if line5000:
                    console("*** Fehler *** Die 5000er Zeile wurde mehrfach definiert")
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
                        self.localVars['EC'].append(False)
                        self.localVars['EA'].append(None)
                    numOut = int(_defline[4+numIn])
                    for i in range(0,numOut):
                        self.Ausgang.append({'name':unquote(_defline[5+numIn+i]),'value':'','isalpha':True,'defined':False,'sbc':False,'round':False,'ikos':[]})
                        self.localVars['AN'].append(None)
                        self.localVars['AC'].append(False)
                        self.localVars['AA'].append(None)
                        self.localVars['pItem'].Ausgang.append([[],[HSIKOdummy(self,i+1)],[],[]])
                except:
                    self.LogikError("5000",line,LineNum,console=console)
                    self.exitall(1)
                    
            ## HS Definitionszeile
            if line.startswith("5001|"):
                firstLogikLine = True
                if line5001:
                    console("*** Fehler *** Die 5001er Zeile wurde mehrfach definiert")
                line5001 += 1
                try:
                    _defline = line.split("|")
                    if numIn != int(_defline[1]):
                        console("*** 5001er und 5000er Eingänge passen nicht ***")
                        self.exitall(1)
                    if numOut != int(_defline[2]):
                        console("*** 5001er und 5000er Ausgänge passen nicht ***")
                        self.exitall(1)
                    numOffset = int(_defline[3])
                    for o in range(0,numOffset):
                        self.localVars['ON'].append(None)
                        self.localVars['OC'].append(False)
                        self.Offset.append([0,0,None])
                        self.localVars['Timer'].append(self.Offset[o+1])
                        
                    Speicher = int(_defline[4])
                    for i in range(0,Speicher):
                        self.Speicher.append({'value':None,'isalpha':False,'defined':False,'remanent':False})
                        self.localVars['SN'].append(None)
                        self.localVars['SC'].append(False)
                        self.localVars['SA'].append(None)

                    self.runStart = int(_defline[5][0])
                except:
                    self.LogikError("5001",line,LineNum,console=console)
                    self.exitall(1)

            ## Eingänge
            if line.startswith("5002|"):
                firstLogikLine = True
                line5002 += 1
                try:
                    _defline = line.split("|")
                    try:
                        ## :( Dacom Baustein Codeschloss ist nicht gültig :(
                        _isalpha = int(_defline[3][0]) == 1
                    except IndexError:
                        self.LogikError("5002",line,LineNum,msg='(fehlende Angabe)',console=console)
                        _isalpha = False
                    ## convert if string remove " '
                    try:
                        if len(_defline[2]) == 0:
                            _value = None
                        elif not _isalpha:
                            _f = re.findall("\d+(?:\.\d+)?",_defline[2])
                            if _f:
                                _value = float(_f[0])
                        else:
                            _value = unquote(_defline[2])
                    except ValueError:
                        _value = unquote(_defline[2])
                    self.Eingang[int(_defline[1])]['value'] = _value
                    self.Eingang[int(_defline[1])]['isalpha'] = _isalpha
                    self.Eingang[int(_defline[1])]['defined'] = True
                    self.localVars['EN'][int(_defline[1])] = _value
                    
                except:
                    self.LogikError("5002",line,LineNum,console=console)
                    self.exitall(1)
        
            ## Speicher
            if line.startswith("5003|"):
                firstLogikLine = True
                line5003 += 1
                try:
                    _defline = line.split("|")
                    _isremanent = int(_defline[3][0]) == 1
                    if _isremanent and not self.isRemanent:
                        console("\n*** Warnung *** Baustein ist nicht Remanent, hat aber Remanente Speicher\n")
                    _isalpha = False
                    try:
                        if len(_defline[2]) == 0:
                            _value = None
                        _f = re.findall("\d+(?:\.\d+)?",_defline[2])
                        if _f:
                            _value = float(_f[0])
                        else:
                            unquote(_defline[2])
                    
                    except ValueError:
                        ## remove " '
                        _value = unquote(_defline[2])
                        _isalpha = True
                    self.Speicher[int(_defline[1])]['value'] = _value
                    self.Speicher[int(_defline[1])]['isalpha'] = _isalpha
                    self.Speicher[int(_defline[1])]['remanent'] = _isremanent
                    self.Speicher[int(_defline[1])]['defined'] = True
                    self.localVars['SN'][int(_defline[1])] = _value
                except:
                    self.LogikError("5003",line,LineNum,console=console)
                    self.exitall(1)
        
            ## Ausgänge
            if line.startswith("5004|"):
                firstLogikLine = True
                line5004 += 1
                try:
                    _defline = line.split("|")
                    try:
                        ## :( Dacom Baustein Codeschloss ist nicht gültig :(
                        _isalpha = int(_defline[5][0]) == 1
                    except IndexError:
                        _isalpha = False
                    ## convert if string remove " '
                    try:
                        if len(_defline[2]) == 0:
                            _value = None
                        elif not _isalpha:
                            _f = re.findall("\d+(?:\.\d+)?",_defline[2])
                            if _f:
                                _value = float(_f[0])
                        else:
                            _value = unquote(_defline[2])
                    except ValueError:
                        _value = unquote(_defline[2])

                    self.Ausgang[int(_defline[1])]['value'] = _value
                    self.Ausgang[int(_defline[1])]['round'] = int(_defline[3][0])==1
                    self.Ausgang[int(_defline[1])]['sbc'] = int(_defline[4][0])==1
                    self.Ausgang[int(_defline[1])]['isalpha'] = _isalpha
                    self.Ausgang[int(_defline[1])]['defined'] = True
                    self.localVars['AN'][int(_defline[1])] = _value
                except:
                    self.LogikError("5004",line,LineNum,console=console)
                    self.exitall(1)

            if line.startswith("5012|"):
                line5012 += 1
                try:
                    _defline = re.findall("^(5012)\|([0|1])\|\x22(.*?)\x22\|\x22(.*?)\x22\|\x22(.*?)\x22\|(\d+)\|(\d+)\|(\d+)\|(\d+)",line)
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
                            console("\n*** Warnung *** es wird EI als Bedingung gewertet, obwohl der Baustein nicht beim Systemstart startet\n")
                        for _oc in re.findall("O[C|N]\[(\d+)\]",_case):
                            if int(_oc) > numOffset:
                                console("\n*** Warnung *** Timer OC[%s] gefunden aber nur %d Timer definiert\n" % (_oc,numOffset))
                    _caseCode = compile(_case,"Line:"+str(LineNum),"eval")
                    if len(_defline[3])==0:
                        _formel = "None"
                    else:
                        _formel = _defline[3]
                    if _formel.startswith("eval(compile(__import__('base64').decodestring('") and self.Options['decode']:
                        _b64 = re.findall("decodestring\('(.*?)'\)",_formel)
                        if _b64:
                            try:
                                print base64.decodestring(_b64[0])
                            except:
                                pass
                    _formelCode = compile(_formel,"Line:"+str(LineNum),"eval")
                    if len(_defline[4])==0:
                        _offset = "None"
                    else:
                        _offset = _defline[4]
                    _offsetCode = compile(_offset,"Line:"+str(LineNum),"eval")
                    _pinAusgang = int(_defline[5])
                    _pinOffset = int(_defline[6])
                    if _pinOffset > numOffset:
                        console("\n*** Warnung *** Ausgang auf Timer OC[%s] gesetzt aber nur %d Timer definiert\n" % (_pinOffset,numOffset))
                    _pinSpeicher = int(_defline[7])
                    _pinNegAusgang = int(_defline[8])
                    self.Formel.append(
                      {
                      'pinAusgang': _pinAusgang,
                      'pinOffset': _pinOffset,
                      'pinSpeicher': _pinSpeicher,
                      'pinNegAusgang': _pinNegAusgang,
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
                    __import__('traceback').print_exc(file=__import__('sys').stdout)
                    self.exitall(1)

            if not firstLogikLine:
                self.LogikHeader.append(line)
        
        if numIn <> len(self.Eingang)-1:
            console("*** Fehler *** Nicht alle Eingänge sind definiert")
            self.exitall(1)
        if numOut <> len(self.Ausgang)-1:
            console("*** Fehler *** Nicht alle Ausgänge sind definiert")
            self.exitall(1)
        if Speicher <> len(self.Speicher)-1:
            console("*** Fehler *** Nicht alle Speicher sind definiert")
            self.exitall(1)

    def extcompile(self,compiler,code,desc): 
        from tempfile import mkstemp
        _basecode = ""
        try:
            try:
                _fh,_fname = mkstemp(suffix='.tmp',prefix="LGT_compile-")
                console("temporäre Datei '%s' erstellt" % _fname)
                _fp = open(_fname,"w")
                _fp.write(code)
                _fp.close()
                os.close(_fh)
                _cstdout,_cstdin,_cstderr = popen2.popen3(compiler + " -c \"import base64;import marshal;print base64.encodestring(marshal.dumps(compile(open(base64.decodestring('"+re.sub("\n","",base64.encodestring(_fname))+"')).read(),'"+desc+"','exec')))\"")
                _basecode = _cstdout.read()
                _err = _cstderr.read()
                _cstdout.close()
                _cstdin.close()
                _cstderr.close()
            except:
                console("*** externer Compiler Fehler ***")
                return False
        finally:
            os.remove(_fname)
            console("temporäre Datei '%s' gelöscht" % _fname)
            return re.sub("\n","",_basecode)

    def createLGT(self):
        lgtfile = "%d_%s.LGT"  % (self.LogikNum,self.LogikName)
        
        console("erstelle LGT Datei %s" % lgtfile)
        
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
            console("\n*** Warnung *** es wird EI als Bedingung gewertet, obwohl der Baustein nicht beim Systemstart startet\n")
        for _oc in re.findall("O[C|N]\[(\d+)\]",_case):
            if int(_oc) > numOffset:
                console("\n*** Warnung *** Timer OC[%s] gefunden aber nur %d Timer definiert\n" % (_oc,numOffset))
        _caseCode = compile(_case,"Case-Line:"+str(LineNum),"eval")
        if len(_formel)==0:
            _formel = "None"
        _formelCode = compile(_formel,"Formel-Line:"+str(LineNum),"eval")
        if len(_offset)==0:
            _offset = "None"
        _offsetCode = compile(_offset,"Offset-Line:"+str(LineNum),"eval")
        if _pinOffset > numOffset:
            console("\n*** Warnung *** Ausgang auf Timer OC[%s] gesetzt aber nur %d Timer definiert\n" % (_pinOffset,numOffset))


        
        self.Formel.append(
          {
          'pinAusgang': _pinAusgang,
          'pinOffset': _pinOffset,
          'pinSpeicher': _pinSpeicher,
          'pinNegAusgang': _pinNegAusgang,
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

        pass
        
LGT = LogikGeneratorClass()

def Finish():
    print sys.argv
    LGT._HSLparser(LGT.LogikHeader)
    parseCommandLine()

def register(_action):
    import _winreg
    _keyname = "Debug %s" % sys.version[:3]
    if _action <> 1:
        _x = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell\%s" % _keyname,0,_winreg.KEY_ALL_ACCESS)
        _winreg.DeleteKey(_x,"command")
        _x = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell",0,_winreg.KEY_ALL_ACCESS)
        _winreg.DeleteKey(_x,_keyname)
    else:
        _x = sys.executable + " " + sys.path[0] + "\\" + sys.argv[0] + " -d -i \"%1\""
        console("** Register %s mit .hsl Dateien **" % _x)
        try:
            _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell\%s\command" % _keyname,0,_winreg.KEY_WRITE)
        except WindowsError:
            _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell\%s\command" % _keyname)
        _winreg.SetValue(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell\%s" % _keyname,_winreg.REG_SZ,_keyname)
        _winreg.SetValue(_winreg.HKEY_CLASSES_ROOT,r"hsl_auto_file\shell\%s\command" % _keyname,_winreg.REG_SZ,_x)
        _winreg.SetValue(_winreg.HKEY_CLASSES_ROOT,r".hsl",_winreg.REG_SZ,"hsl_auto_file")

    
def parseCommandLine():
    _cmds = []
    configFile = sys.path[0]+"\LogikGen.config"
    argautorun = 0
    
    import getopt
    
    opts, args = getopt.getopt(sys.argv[1:],"a:nn:i:dg",["autorun=","new=","import=","register","debug","b64decode","config="])
    for opt,arg in opts:
        if opt in ("-i","--import"):
            if os.path.isfile(arg):
                importfilename = arg
                _cmds.append("import")
            else:
                if len(arg) <1:
                    console("Kein Import File angegeben")
                else:
                    console("Import File %r nicht gefunden" % arg)

        elif opt in ("-n","--new"):
            _hslinfo = re.findall(".*(1[0-9][0-9][0-9][0-9])_(.*)",arg)
            _logiknum = False
            _logikname = False
            if _hslinfo:
                _logiknum = int(_hslinfo[0][0])
                _logikname = _hslinfo[0][1]
            _cmds.append("create")

        elif opt in ("-d","--debug"):
            _cmds.append("debug")

        elif opt in ("--register"):
            register(1)
            sys.exit(0)

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
            console("unbekannte Option")
            sys.exit(0)
    if "import" in _cmds:
        LGT.HSLparser(importfilename)
    if "create" in _cmds:
        if _logiknum:
            LGT.LogikNum = _logiknum
        if _logikname:
            LGT.LogikName = _logikname
        LGT.createLGT()

    console(LGT.LogikNum)
    LGT.readConfig(configFile)    
    
    if "autorun" in _cmds:
        LGT.AutoRun = argautorun
    if "debug" in _cmds:
        if "kogw" in _cmds:
            LGT.connectKOGW()
            time.sleep(0.5)
        LGT.LogikDebug()
    
    
if __name__ == "__main__":
    try:
        parseCommandLine()
    except SystemExit:
        pass
    except:
        print "Error Prozessing"
        traceback.print_exc(file=sys.stdout)
        time.sleep(5)

    sys.exit(0)
