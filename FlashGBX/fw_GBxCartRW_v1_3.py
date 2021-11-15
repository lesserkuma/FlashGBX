# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import zipfile, os, serial, struct, time, re, math, platform
from PySide2 import QtCore, QtWidgets, QtGui
from . import Util

class FirmwareUpdaterWindow(QtWidgets.QDialog):
	APP = None
	DEVICE = None
	PORT = ""

	def __init__(self, app, app_path, file=None, icon=None, device=None):
		QtWidgets.QDialog.__init__(self)
		if icon is not None: self.setWindowIcon(QtGui.QIcon(icon))
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.APP = app
		self.APP_PATH = app_path
		self.DEVICE = device
		self.PORT = device.GetPort()

		self.setWindowTitle("FlashGBX – Firmware Updater for GBxCart RW v1.3")
		self.setWindowFlags((self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint) & ~QtCore.Qt.WindowContextHelpButtonHint)

		with zipfile.ZipFile(self.APP_PATH + "/res/fw_GBxCart_RW_v1_3.zip") as zip:
			with zip.open("fw.ini") as f: ini_file = f.read()
			ini_file = ini_file.decode(encoding="utf-8")
			self.INI = Util.IniSettings(ini=ini_file, main_section="Firmware")
			self.CFW_VER = self.INI.GetValue("cfw_ver")
			self.CFW_TEXT = self.INI.GetValue("cfw_text")
			self.OFW_VER = self.INI.GetValue("ofw_ver")
			self.OFW_TEXT = self.INI.GetValue("ofw_text")
		
		self.layout = QtWidgets.QGridLayout()
		self.layout.setContentsMargins(-1, 8, -1, 8)
		self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		self.layout_device = QtWidgets.QVBoxLayout()
		
		# ↓↓↓ Current Device Information
		self.grpDeviceInfo = QtWidgets.QGroupBox("Current Device Information")
		self.grpDeviceInfo.setMinimumWidth(420)
		self.grpDeviceInfoLayout = QtWidgets.QVBoxLayout()
		self.grpDeviceInfoLayout.setContentsMargins(-1, 3, -1, -1)
		rowDeviceInfo1 = QtWidgets.QHBoxLayout()
		self.lblDeviceName = QtWidgets.QLabel("Name:")
		self.lblDeviceName.setMinimumWidth(120)
		self.lblDeviceNameResult = QtWidgets.QLabel("GBxCart RW")
		rowDeviceInfo1.addWidget(self.lblDeviceName)
		rowDeviceInfo1.addWidget(self.lblDeviceNameResult)
		rowDeviceInfo1.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo1)
		rowDeviceInfo2 = QtWidgets.QHBoxLayout()
		self.lblDevicePCBVer = QtWidgets.QLabel("PCB version:")
		self.lblDevicePCBVer.setMinimumWidth(120)
		self.lblDevicePCBVerResult = QtWidgets.QLabel("1.3")
		rowDeviceInfo2.addWidget(self.lblDevicePCBVer)
		rowDeviceInfo2.addWidget(self.lblDevicePCBVerResult)
		rowDeviceInfo2.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo2)
		rowDeviceInfo3 = QtWidgets.QHBoxLayout()
		self.lblDeviceFWVer = QtWidgets.QLabel("Firmware version:")
		self.lblDeviceFWVer.setMinimumWidth(120)
		self.lblDeviceFWVerResult = QtWidgets.QLabel("R26")
		rowDeviceInfo3.addWidget(self.lblDeviceFWVer)
		rowDeviceInfo3.addWidget(self.lblDeviceFWVerResult)
		rowDeviceInfo3.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo3)
		self.grpDeviceInfo.setLayout(self.grpDeviceInfoLayout)
		self.layout_device.addWidget(self.grpDeviceInfo)
		# ↑↑↑ Current Device Information
		
		# ↓↓↓ Available Firmware Updates
		self.grpAvailableFwUpdates = QtWidgets.QGroupBox("Firmware Update Options")
		self.grpAvailableFwUpdates.setMinimumWidth(400)
		self.grpAvailableFwUpdatesLayout = QtWidgets.QVBoxLayout()
		self.grpAvailableFwUpdatesLayout.setContentsMargins(-1, 3, -1, -1)
		self.optCFW = QtWidgets.QRadioButton("{:s}".format(self.CFW_VER))
		self.optCFW.setChecked(True)
		self.lblCFW_Blerb = QtWidgets.QLabel("{:s}".format(self.CFW_TEXT))
		self.lblCFW_Blerb.setWordWrap(True)
		self.lblCFW_Blerb.mousePressEvent = lambda x: [ self.optCFW.setChecked(True) ]
		self.optOFW = QtWidgets.QRadioButton("{:s}".format(self.OFW_VER))
		self.lblOFW_Blerb = QtWidgets.QLabel("{:s}".format(self.OFW_TEXT))
		self.lblOFW_Blerb.setWordWrap(True)
		self.lblOFW_Blerb.mousePressEvent = lambda x: [ self.optOFW.setChecked(True) ]
		self.optExternal = QtWidgets.QRadioButton("External firmware file")
		#self.lblExternal_Blerb = QtWidgets.QLabel("<ul><li>Please check <a href=\"https://www.gbxcart.com/\">gbxcart.com</a> for the latest official firmware version</li></ul>")
		#self.lblExternal_Blerb.setWordWrap(True)
		#self.lblExternal_Blerb.mousePressEvent = lambda x: [ self.optOFW.setChecked(True) ]
		
		self.rowUpdate = QtWidgets.QHBoxLayout()
		self.btnUpdate = QtWidgets.QPushButton("Install Firmware Update")
		self.btnUpdate.setMinimumWidth(200)
		self.btnUpdate.setContentsMargins(20, 20, 20, 20)
		self.connect(self.btnUpdate, QtCore.SIGNAL("clicked()"), lambda: [ self.UpdateFirmware() ])
		self.rowUpdate.addStretch()
		self.rowUpdate.addWidget(self.btnUpdate)
		self.rowUpdate.addStretch()

		self.grpAvailableFwUpdatesLayout.addWidget(self.optCFW)
		self.grpAvailableFwUpdatesLayout.addWidget(self.lblCFW_Blerb)
		self.grpAvailableFwUpdatesLayout.addWidget(self.optOFW)
		self.grpAvailableFwUpdatesLayout.addWidget(self.lblOFW_Blerb)
		self.grpAvailableFwUpdatesLayout.addWidget(self.optExternal)
		#self.grpAvailableFwUpdatesLayout.addWidget(self.lblExternal_Blerb)
		self.grpAvailableFwUpdatesLayout.addSpacing(3)
		self.grpAvailableFwUpdatesLayout.addItem(self.rowUpdate)
		#self.grpAvailableFwUpdatesLayout.addWidget(self.btnUpdate)
		self.grpAvailableFwUpdates.setLayout(self.grpAvailableFwUpdatesLayout)
		self.layout_device.addWidget(self.grpAvailableFwUpdates)
		# ↑↑↑ Available Firmware Updates

		self.grpStatus = QtWidgets.QGroupBox("")
		self.grpStatusLayout = QtWidgets.QGridLayout()
		self.prgStatus = QtWidgets.QProgressBar()
		self.prgStatus.setMinimum(0)
		self.prgStatus.setMaximum(100)
		self.prgStatus.setValue(0)
		self.lblStatus = QtWidgets.QLabel("Status: Ready.")

		#self.grpStatusLayout.addWidget(self.btnUpdate, 0, 0, QtCore.Qt.AlignCenter)
		self.grpStatusLayout.addWidget(self.prgStatus, 1, 0)
		self.grpStatusLayout.addWidget(self.lblStatus, 2, 0)
		
		self.grpStatus.setLayout(self.grpStatusLayout)
		self.layout_device.addWidget(self.grpStatus)
		
		self.grpFooterLayout = QtWidgets.QHBoxLayout()
		self.btnClose = QtWidgets.QPushButton("&Close")
		self.connect(self.btnClose, QtCore.SIGNAL("clicked()"), lambda: [ self.reject() ])
		self.grpFooterLayout.addStretch()
		self.grpFooterLayout.addWidget(self.btnClose)
		self.layout_device.addItem(self.grpFooterLayout)

		self.layout.addLayout(self.layout_device, 0, 0)
		self.setLayout(self.layout)

		self.ReadDeviceInfo()

	def run(self):
		self.layout.update()
		self.layout.activate()
		screenGeometry = QtWidgets.QDesktopWidget().screenGeometry()
		x = (screenGeometry.width() - self.width()) / 2
		y = (screenGeometry.height() - self.height()) / 2
		self.move(x, y)
		self.show()
	
	def hideEvent(self, event):
		if self.DEVICE is None:
			self.APP.ConnectDevice()
		self.APP.activateWindow()
	
	def reject(self):
		if self.CloseDialog():
			super().reject()
	
	def CloseDialog(self):
		if self.btnClose.isEnabled() is False:
			text = "<b>WARNING:</b> If you close this window while a firmware update is still running, it might leave the device in an unbootable state.<br><br>Are you sure you want to close this window?"
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.No)
			answer = msgbox.exec()
			if answer == QtWidgets.QMessageBox.No: return False
		return True

	def ReadDeviceInfo(self):
		self.lblDeviceNameResult.setText(self.DEVICE.GetName())
		self.lblDeviceFWVerResult.setText(self.DEVICE.GetFirmwareVersion(more=True))
		self.lblDevicePCBVerResult.setText(self.DEVICE.GetPCBVersion())
	
	def ResetAVR(self, delay=0.1):
		port = self.PORT
		try:
			dev = serial.Serial(port, 1000000, timeout=1)
		except serial.SerialException:
			return False
		dev.write(b'0')
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		dev.write(struct.pack(">BIBB", 0x2A, 0x37653565, 0x31, 0))
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		self.APP.QT_APP.processEvents()
		time.sleep(0.3 + delay)
		dev.reset_input_buffer()
		dev.reset_output_buffer()
		dev.close()
		return True

	def UpdateFirmware(self):
		fw = ""
		path = ""
		if self.optCFW.isChecked():
			fw = "Version {:s}".format(self.CFW_VER)
			fn = "cfw.hex"
		elif self.optOFW.isChecked():
			fw = "Version {:s}".format(self.OFW_VER)
			fn = "ofw.hex"
		else:
			path = self.APP.SETTINGS.value("LastDirFirmwareUpdate")
			path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose GBxCart RW v1.3 Firmware File", path, "Firmware Update (*.hex);;All Files (*.*)")[0]
			if path == "": return
			temp = re.search(r"^(gbxcart_rw_v1\.3_pcb_r.+\.hex)$", os.path.basename(path))
			if temp is None:
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The expected filename for a valid firmware file is <b>gbxcart_rw_v1.3_pcb_r**.hex</b>. Please visit <a href=\"https://www.gbxcart.com/\">gbxcart.com</a> for the latest official firmware updates.", standardButtons=QtWidgets.QMessageBox.Ok)
				answer = msgbox.exec()
				return
			self.APP.SETTINGS.setValue("LastDirFirmwareUpdate", os.path.dirname(path))
			fw = "{:s}<br><br><b>Please double check that this is a valid firmware file for the GBxCart RW v1.3. If it is invalid or an update for a different device, it may render your device unusable.</b>".format(path)
			fn = None
		
		text = "The following firmware will now be written to your GBxCart v1.3 device:<br>- {:s}".format(fw)
		text += "<br><br>Do you want to continue?"
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
		msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
		msgbox.setTextFormat(QtCore.Qt.TextFormat.RichText)
		answer = msgbox.exec()
		if answer == QtWidgets.QMessageBox.No: return
		self.btnUpdate.setEnabled(False)
		self.btnClose.setEnabled(False)
		self.grpAvailableFwUpdates.setEnabled(False)

		if path == "":
			with zipfile.ZipFile(self.APP_PATH + "/res/fw_GBxCart_RW_v1_3.zip") as archive:
				with archive.open(fn) as f: ihex = f.read().decode("ascii")
		else:
			with open(path, "rb") as f: ihex = f.read().decode("ascii")
		
		ihex = ihex.splitlines()
		buffer = bytearray()
		for line in ihex:
			keys = ["colon", "raw", "bytecount", "address", "type", "data", "checksum"]
			values = re.search(r"^(\:)((.{2})(.{4})(.{2})(.*))(.{2})$", line)
			if values == None: continue
			values = values.groups()
			data = dict(zip(keys, values))
			for (k, v) in data.items():
				if k in ("bytecount", "type", "checksum"):
					data[k] = struct.unpack("B", bytes.fromhex(v))[0]
				elif k == "address":
					data[k] = struct.unpack("H", bytes.fromhex(v))[0]
				elif k != "colon":
					data[k] = bytes.fromhex(v)

			# Calculate checksum
			chk = 0
			for i in range(0, len(data["raw"])):
				chk += data["raw"][i]
			chk = chk & 0xFF
			chk = (~chk + 1) & 0xFF
			if (chk != data["checksum"]):
				self.SetStatus("Status: Firmware checksum error.")
				self.prgStatus.setValue(0)
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
				self.grpAvailableFwUpdates.setEnabled(True)
				return False
			
			else:
				buffer += bytearray(data["data"])
	
		if len(buffer) >= 7168:
			self.SetStatus("Status: Firmware file is too large.")
			self.prgStatus.setValue(0)
			self.btnUpdate.setEnabled(True)
			self.btnClose.setEnabled(True)
			self.grpAvailableFwUpdates.setEnabled(True)
			return False
		
		self.APP.DisconnectDevice()

		while True:
			ret = self.WriteFirmware(buffer, self.SetStatus)
			if ret == 1: return True
			elif ret == 2: return False
			elif ret == 3: continue
	
	def SetStatus(self, text, enableUI=False, setProgress=None):
		self.lblStatus.setText(text)
		if setProgress is not None:
			self.prgStatus.setValue(setProgress)
		if enableUI:
			self.btnUpdate.setEnabled(True)
			self.btnClose.setEnabled(True)
			self.grpAvailableFwUpdates.setEnabled(True)

	def WriteFirmware(self, data, fncSetStatus):
		fw_buffer = data
		port = self.PORT
		
		delay = 0
		lives = 10
		buffer = bytearray()

		fncSetStatus(text="Status: Waiting for bootloader...", setProgress=0)
		if self.ResetAVR(delay) is False:
			fncSetStatus(text="Status: Bootloader error.", enableUI=True)
			self.prgStatus.setValue(0)
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful as the GBxCart RW v1.3 bootloader is not responding. If it doesn’t work even after multiple retries, please use the official firmware updater instead.", standardButtons=QtWidgets.QMessageBox.Ok)
			answer = msgbox.exec()
			return 2
		
		while True:
			try:
				dev = serial.Serial(port=port, baudrate=9600, timeout=1)
			except:
				fncSetStatus(text="Status: Device access error.", enableUI=True)
				return 2
			dev.reset_input_buffer()
			dev.reset_output_buffer()
			dev.write(b"@@@")
			dev.flush()
			if platform.system() == "Darwin": time.sleep(0.00125)
			buffer = dev.read(0x11)
			if (len(buffer) < 0x11) or (buffer[0:3] != b'TSB'):
				dev.write(b"?")
				dev.flush()
				if platform.system() == "Darwin": time.sleep(0.00125)
				dev.close()
				self.APP.QT_APP.processEvents()
				time.sleep(1)
				if len(buffer) != 0x11:
					delay += 0.05
				fncSetStatus("Status: Waiting for bootloader... (+{:d}ms)".format(math.ceil(delay * 1000)))
				if self.ResetAVR(delay) is False:
					fncSetStatus(text="Status: Bootloader error.", enableUI=True)
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful as the GBxCart RW v1.3 bootloader is not responding. If it doesn’t work even after multiple retries, please use the official firmware updater instead.", standardButtons=QtWidgets.QMessageBox.Ok)
					answer = msgbox.exec()
					return 2
				lives -= 1
				if lives < 0:
					fncSetStatus(text="Status: Bootloader timeout.", enableUI=True)
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful as the GBxCart RW v1.3 bootloader is not responding. If it doesn’t work even after multiple retries, please use the official firmware updater instead.", standardButtons=QtWidgets.QMessageBox.Ok)
					answer = msgbox.exec()
					return 2
				continue
			break
		
		fncSetStatus("Reading bootloader information...")
		info = {}
		keys = ["magic", "tsb_version", "tsb_status", "signature", "page_size", "flash_size", "eeprom_size", "unknown", "avr_jmp_identifier"]
		values = struct.unpack("<3sHB3sBHHBB", bytearray(buffer[:-1]))
		info = dict(zip(keys, values))
		info["page_size"] *= 2
		info["flash_size"] *= 2
		info["eeprom_size"] += 1
		if info["avr_jmp_identifier"] == 0x00:
			info["jmp_mode"] = "relative"
			info["device_type"] = "attiny"
		elif info["avr_jmp_identifier"] == 0x0C:
			info["jmp_mode"] = "absolute"
			info["device_type"] = "attiny"
		elif info["avr_jmp_identifier"] == 0xAA:
			info["jmp_mode"] = "relative"
			info["device_type"] = "atmega"
		
		if info["page_size"] != 64 or info["flash_size"] != 7616 or info["eeprom_size"] != 512 or info["jmp_mode"] != "relative" or info["device_type"] != "atmega" or info["signature"] != b'\x1E\x93\x06':
			fncSetStatus(text="Status: Wrong device detected.", enableUI=True)
			return 2
		
		if (info["tsb_version"] < 32768):
			info["tsb_version"] = int((info["tsb_version"] & 31) + ((info["tsb_version"] & 480) / 32) * 100 + ((info["tsb_version"] & 65024 ) / 512) * 10000 + 20000000)
		else:
			fncSetStatus(text="Status: Wrong device detected.", enableUI=True)
			return 2
		
		#################

		# Read user data
		fncSetStatus("Status: Reading user data...")
		dev.write(b"c")
		user_data = bytearray(dev.read(0x41))
		info["tsb_timeout"] = user_data[2]

		# Change timeout to 6s
		fncSetStatus("Status: Writing user data...")
		user_data[2] = 254
		dev.write(b"C")
		dev.read(1)
		dev.write(b"!")
		dev.write(user_data)
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		dev.read(0x41)

		# Write firmware
		fncSetStatus("Status: Updating firmware... Do not unplug the device!")
		iterations = math.ceil(len(fw_buffer) / 0x40)
		if len(fw_buffer) < iterations * 0x40:
			fw_buffer = fw_buffer + bytearray([0xFF] * ((iterations * 0x40) - len(fw_buffer)))

		lives = 10
		dev.write(b"F")
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		ret = dev.read(1)
		while ret != b"?":
			dev.write(b"F")
			dev.flush()
			if platform.system() == "Darwin": time.sleep(0.00125)
			ret = dev.read(1)
			lives -= 1
			if lives == 0:
				dev.write(b"?")
				dev.flush()
				if platform.system() == "Darwin": time.sleep(0.00125)
				dev.close()
				fncSetStatus(text="Status: Protocol Error. Please try again.", enableUI=True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful (Protocol Error). Do you want to try again?\n\nIf it doesn’t work even after multiple retries, please use the official firmware updater instead.", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.Yes)
				answer = msgbox.exec()
				if answer == QtWidgets.QMessageBox.Yes:
					time.sleep(1)
					return 3
				return 2
		
		for i in range(0, iterations):
			self.APP.QT_APP.processEvents()
			dev.write(b"!")
			dev.write(fw_buffer[i*0x40:i*0x40+0x40])
			fncSetStatus(text="Status: Updating firmware... Do not unplug the device!", setProgress=(i*0x40+0x40) / len(fw_buffer) * 100)
			ret = dev.read(1)
			if (ret != b"?"):
				dev.write(b"?")
				dev.flush()
				if platform.system() == "Darwin": time.sleep(0.00125)
				dev.close()
				fncSetStatus(text="Status: Write Error ({:s}). Please try again.".format(str(ret)), enableUI=True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful (Write Error, {:s}). Do you want to try again?\n\nIf it doesn’t work even after multiple retries, you will have to use the official firmware updater to recover the firmware.".format(str(ret)), standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.Yes)
				answer = msgbox.exec()
				if answer == QtWidgets.QMessageBox.Yes:
					time.sleep(1)
					return 3
				return 2
		dev.write(b"?")
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		dev.read(1)
		
		# verify flash
		fncSetStatus("Status: Verifying update...")
		buffer2 = bytearray()
		dev.write(b"f")
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		for i in range(0, 0x1DC0, 0x40):
			self.APP.QT_APP.processEvents()
			dev.write(b"!")
			dev.flush()
			if platform.system() == "Darwin": time.sleep(0.00125)
			while dev.in_waiting == 0: time.sleep(0.01)
			ret = bytearray(dev.read(0x40))
			buffer2 += ret
			self.prgStatus.setValue(len(buffer2) / 0x1DC0 * 100)
		dev.read(1)
		
		buffer2 = buffer2[:len(fw_buffer)]

		if fw_buffer == buffer2:
			fncSetStatus("Status: Verification OK.")
			self.APP.QT_APP.processEvents()
			time.sleep(0.2)
		else:
			fncSetStatus(text="Status: Verification Error.", enableUI=True)
			dev.write(b"?")
			dev.flush()
			if platform.system() == "Darwin": time.sleep(0.00125)
			dev.close()
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The firmware update was not successful (Verification Error). Do you want to try again?\n\nIf it doesn’t work even after multiple retries, please use the official firmware updater instead.", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.Yes)
			answer = msgbox.exec()
			if answer == QtWidgets.QMessageBox.Yes:
				time.sleep(1)
				return 3
			return 2

		# Change timeout to 1s
		fncSetStatus("Status: Writing user data...")
		user_data[2] = 42
		dev.write(b"C")
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		ret = dev.read(1)
		while ret != b"?":
			dev.write(b"C")
			dev.flush()
			if platform.system() == "Darwin": time.sleep(0.00125)
			ret = dev.read(1)
			lives -= 1
			if lives == 0:
				dev.write(b"?")
				dev.flush()
				if platform.system() == "Darwin": time.sleep(0.00125)
				dev.close()
				fncSetStatus(text="Status: User data update error. Please try again.", enableUI=True)
				return 2
		dev.write(b"!")
		dev.write(user_data)
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		dev.read(0x41)
		
		# Restart
		self.APP.QT_APP.processEvents()
		time.sleep(0.1)
		fncSetStatus("Status: Restarting the device...")
		dev.write(b"?")
		dev.flush()
		if platform.system() == "Darwin": time.sleep(0.00125)
		dev.close()
		self.APP.QT_APP.processEvents()
		time.sleep(0.8)
		fncSetStatus("Status: Done.")
		self.APP.QT_APP.processEvents()
		time.sleep(0.2)
		self.DEVICE = None
		self.btnUpdate.setEnabled(True)
		self.btnClose.setEnabled(True)
		self.grpAvailableFwUpdates.setEnabled(True)
		text = "The firmware update is complete!"
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
		answer = msgbox.exec()
		self.reject()
		return 1
