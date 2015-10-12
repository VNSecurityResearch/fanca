import PyDbgEng
from comtypes.gen import DbgEng
import threading
from threading import Thread
import os
from ctypes import *
import re

from Fanca.commons.jsonsocket import Client
from Fanca.core.executors.monitors.windows.CONFIG import *


class DbgEventHandler(PyDbgEng.IDebugOutputCallbacksSink, PyDbgEng.IDebugEventCallbacksSink):
    buff = ''

    def GetInterestMask(self):
        return PyDbgEng.DbgEng.DEBUG_EVENT_EXCEPTION | PyDbgEng.DbgEng.DEBUG_FILTER_INITIAL_BREAKPOINT | \
                PyDbgEng.DbgEng.DEBUG_EVENT_EXIT_PROCESS | PyDbgEng.DbgEng.DEBUG_EVENT_LOAD_MODULE
    def Output(self, this, Mask, Text):
        self.buff += Text

    def LoadModule(self, unknown, imageFileHandle, baseOffset, moduleSize, moduleName, imageName, checkSum, timeDateStamp = None):
			if self.pid == None:
				self.dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,
										   c_char_p("|."),
										   DbgEng.DEBUG_EXECUTE_ECHO)
				
				match = re.search(r"\.\s+\d+\s+id:\s+([0-9a-fA-F]+)\s+\w+\s+name:\s", self.buff)
				if match != None:
					self.pid = int(match.group(1), 16)


    def ExitProcess(self, dbg, ExitCode):
        print 'WindowsDebugEngine: Target application has exitted'
        return DEBUG_STATUS_NO_CHANGE

    def Exception(self, dbg, ExceptionCode, ExceptionFlags, ExceptionRecord,
            ExceptionAddress, NumberParameters, ExceptionInformation0, ExceptionInformation1,
            ExceptionInformation2, ExceptionInformation3, ExceptionInformation4,
            ExceptionInformation5, ExceptionInformation6, ExceptionInformation7,
            ExceptionInformation8, ExceptionInformation9, ExceptionInformation10,
            ExceptionInformation11, ExceptionInformation12, ExceptionInformation13,
            ExceptionInformation14, FirstChance):

        print 'WindowsDebugEngine: We got an exception: #8x' % ExceptionCode

        if FirstChance:

            # more code here to output stacktrace, bang explotable, and bucket of exception ...
            print 'WindowsDebugEngine: Found interesting exception'
            try:
                print 'Exception: 1. Output registers'
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("r"), DbgEng.DEBUG_EXECUTE_ECHO)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("rF"), DbgEng.DEBUG_EXECUTE_ECHO)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("rX"), DbgEng.DEBUG_EXECUTE_ECHO)
                self.buff += "\n\n"

                print 'Exception: 2. Output stack trace'
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT,c_char_p("kb"), DbgEng.DEBUG_EXECUTE_ECHO)
                self.buff += "\n\n"

                print "Exception: 3. Bang-Expoitable"

                p = os.path.dirname(__file__)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p(".load %s\\tools\\bangexploitable\\x86\\msec.dll" % p), DbgEng.DEBUG_EXECUTE_ECHO)
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("!exploitable -m"), DbgEng.DEBUG_EXECUTE_ECHO)
                self.buff += "\n\n"
                dbg.idebug_control.Execute(DbgEng.DEBUG_OUTCTL_THIS_CLIENT, c_char_p("!analyze -v"), DbgEng.DEBUG_EXECUTE_ECHO)

            except Exception, e:
                print str(e)

            try:
                ExceptionType = re.compile("DEFAULT_BUCKET_ID:\s+([A-Za-z_]+)").search(self.buff).group(1)
                exceptionAddress = re.compile("ExceptionAddress: ([^\s\b]+)").search(self.buff).group(1)

                bucket = "%s_at_%s" % (ExceptionType, exceptionAddress)

            except Exception, e:
                # Sometimes !analyze -v fails
                bucket = 'Unknown'

            dbgClient = Client()
            dbgClient.connect(REPLY_HOST, REPLY_PORT)
            dbgClient.send({'fin': 'exception', 'bucket': bucket, 'buff': self.buff})
            dbgClient.close()
        # Kill the process
        return DbgEng.DEBUG_STATUS_BREAK

class Debugger():
    def createDebugger(self, command, follow_fork):
        # Using hardcoded path, need to ve changed in future
        dbg_eng_dll_path = "C:\\WinDDK\\Debuggers"
        event_handler = DbgEventHandler()
        dbg = PyDbgEng.ProcessCreator(command, follow_fork, event_handler, event_handler, dbg_eng_dll_path,"SRV*http://msdl.microsoft.com/download/symbols")
        quit_event = threading.Event()
        print 'WindowsDebugEngine: Waitting for debug event'
        #dbg.event_loop_with_quit_event(quit_event)
        dbg.wait_for_event(80000)
        print 'End of event'
