# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import traceback
from serial import SerialException
from . import pyside as PySide2
from . import Util
from .Util import dprint

class DataTransfer(PySide2.QtCore.QThread):
	CONFIG = None
	FINISHED = False
	
	updateProgress = PySide2.QtCore.Signal(object)

	def __init__(self, config=None):
		PySide2.QtCore.QThread.__init__(self)
		if config is not None:
			self.CONFIG = config
		self.FINISHED = False
	
	def setConfig(self, config):
		self.CONFIG = config
		self.FINISHED = False
	
	def isRunning(self):
		return not self.FINISHED
	
	def run(self):
		tb = ""
		error = None
		try:
			if self.CONFIG == None:
				pass
			
			else:
				self.FINISHED = False
				self.CONFIG['port'].TransferData(self.CONFIG, self.updateProgress)
				self.FINISHED = True
		
		except SerialException as e:
			if "GetOverlappedResult failed" in e.args[0]:
				self.updateProgress.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The USB connection was lost during a transfer. Try different USB cables, reconnect the device, restart the software and try again.", "abortable":False})
				self.FINISHED = True
				return
			tb = traceback.format_exc()
			error = e
		
		except Exception as e:
			tb = traceback.format_exc()
			error = e
		
		if error is not None:
			print(tb)
			dprint(tb)
			self.updateProgress.emit({"action":"ABORT", "info_type":"msgbox_critical", "fatal":True, "info_msg":"An unresolvable error has occured. See console output for more information. Reconnect the device, restart the software and try again.\n\n{:s}: {:s}".format(type(error).__name__, str(error)), "abortable":False})
			self.FINISHED = True
