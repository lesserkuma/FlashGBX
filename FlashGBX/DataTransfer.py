# -*- coding: utf-8 -*-
# ＵＴＦ－８
import sys
from PySide2.QtCore import QThread, Signal

class DataTransfer(QThread):
	CONFIG = None
	RUNNING = False
	
	updateProgress = Signal(object, int, int, float, float, float)

	def __init__(self, config=None):
		QThread.__init__(self)
		self.CONFIG = config

	def isRunning(self):
		return self.RUNNING
	
	def run(self):
		try:
			if self.CONFIG == None:
				pass
			elif self.CONFIG['mode'] == 1:
				self.RUNNING = True
				self.CONFIG['port']._TransferData(1, self.updateProgress, [ self.CONFIG['path'], self.CONFIG['mbc'], self.CONFIG['rom_banks'], self.CONFIG['agb_rom_size'] ])
				self.RUNNING = False
			elif self.CONFIG['mode'] == 2:
				self.RUNNING = True
				self.CONFIG['port']._TransferData(2, self.updateProgress, [ self.CONFIG['path'], self.CONFIG['mbc'], self.CONFIG['save_type'] ])
				self.RUNNING = False
			elif self.CONFIG['mode'] == 3:
				self.RUNNING = True
				self.CONFIG['port']._TransferData(3, self.updateProgress, [ self.CONFIG['path'], self.CONFIG['mbc'], self.CONFIG['save_type'], self.CONFIG['erase'] ])
				self.RUNNING = False
			elif self.CONFIG['mode'] == 4:
				self.RUNNING = True
				self.CONFIG['port']._TransferData(4, self.updateProgress, [ self.CONFIG['path'], self.CONFIG['cart_type'], self.CONFIG['trim_rom'], self.CONFIG['override_voltage'] ])
				self.RUNNING = False

		except Exception as e:
			self.updateProgress.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error has occured!\nPlease try to reconnect the hardware and restart the application.\n\n" + str(e), "abortable":False}, 0, 0, 0, 0, 0)
			self.RUNNING = False
