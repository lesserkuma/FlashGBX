# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import zipfile, serial, struct, time, random, hashlib, datetime
from PySide2 import QtCore, QtWidgets, QtGui
try:
	from . import Util
except ImportError:
	import Util

class FirmwareUpdater():
	PORT = ""

	def __init__(self, app_path=".", port=None):
		self.APP_PATH = app_path
		self.PORT = port

	def WriteFirmware(self, zipfn, fncSetStatus):
		with zipfile.ZipFile(zipfn) as archive:
			with archive.open("fw.ini") as f: buffer1 = bytearray(f.read())
			with archive.open("fw.bin") as f: buffer2 = bytearray(f.read())
		while len(buffer1) < len(buffer2): buffer1 = buffer1 + buffer1
		random.seed(struct.unpack("<I", buffer2[-0x18:-0x14])[0])
		chk = buffer2[-0x14:]
		buffer = bytearray()
		for i in range(0, len(buffer2[0:-0x18])):
			r = int(random.random()*256) % 256
			buffer.append(buffer2[0:-0x18][len(buffer2[0:-0x18]) - i - 1] ^ r ^ buffer1[len(buffer1) - i - 1])
		if (chk != hashlib.sha1(buffer).digest()):
			fncSetStatus("The firmware update file is corrupted.")
			return 3
		
		if self.PORT is None:
			ports = []
			comports = serial.tools.list_ports.comports()
			for i in range(0, len(comports)):
				if comports[i].vid == 0x1A86 and comports[i].pid == 0x7523:
					ports.append(comports[i].device)
			if len(ports) == 0:
				fncSetStatus("No device found.")
				return 2
			port = ports[0]
		else:
			port = self.PORT
		data = buffer
		buffer = bytearray()
		
		fncSetStatus(text="Connecting...")
		try:
			dev = serial.Serial(port=port, baudrate=57600, timeout=1)
		except:
			fncSetStatus(text="Device not accessible.", enableUI=True)
			return 2
		dev.reset_input_buffer()

		# Write firmware
		fncSetStatus("Updating firmware...", setProgress=0)
		
		size = len(data)
		counter = 0
		while counter < size:
			byte = data[counter:counter+1]
			dev.write(byte)
			tmp_byte = dev.read(1)
			if (tmp_byte != byte):
				try:
					tmp_byte = int.from_bytes(tmp_byte, byteorder="little")
				except:
					tmp_byte = 0
				byte = int.from_bytes(byte, byteorder="little")
				if counter == 0:
					fncSetStatus(text="Update failed!", enableUI=True)
				else:
					fncSetStatus(text="Update failed at offset 0x{:04X}!".format(counter), enableUI=True)
				return 2
			
			counter += 1
			percent = float(counter)/size*100
			fncSetStatus(text="Updating firmware... Do not unplug the device!", setProgress=percent)

		dev.close()
		time.sleep(0.8)
		fncSetStatus("Done.")
		time.sleep(0.2)
		return 1

class FirmwareUpdaterWindow(QtWidgets.QDialog):
	APP = None
	DEVICE = None
	FWUPD = None
	DEV_NAME = "GBxCart RW"
	FW_VER = ""
	PCB_VER = ""

	def __init__(self, app, app_path, file=None, icon=None, device=None):
		QtWidgets.QDialog.__init__(self)
		if icon is not None: self.setWindowIcon(QtGui.QIcon(icon))
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.setWindowTitle("FlashGBX – Firmware Updater for GBxCart RW v1.4")
		self.setWindowFlags((self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint) & ~QtCore.Qt.WindowContextHelpButtonHint)

		self.APP = app
		if device is not None:
			self.FWUPD = FirmwareUpdater(app_path, device.GetPort())
			self.DEV_NAME = device.GetName()
			self.FW_VER = device.GetFirmwareVersion(more=True)
			self.PCB_VER = device.GetPCBVersion()
			self.DEVICE = device
		else:
			self.APP.QT_APP.processEvents()
			text = "This Firmware Updater is for insideGadgets GBxCart RW v1.4 devices only. Please only proceed if your device matches this hardware revision.\n\nGBxCart RW v1.3 can be updated only after connecting to it first. If you want to update another GBxCart RW hardware revision, please use the official firmware updater by insideGadgets instead."
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
			answer = msgbox.exec()
			if answer == QtWidgets.QMessageBox.Cancel: return
			self.FWUPD = FirmwareUpdater(app_path, None)

		self.layout = QtWidgets.QGridLayout()
		self.layout.setContentsMargins(-1, 8, -1, 8)
		self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		self.layout_device = QtWidgets.QVBoxLayout()
		
		# ↓↓↓ Current Device Information
		self.grpDeviceInfo = QtWidgets.QGroupBox("Current Firmware")
		self.grpDeviceInfo.setMinimumWidth(420)
		self.grpDeviceInfoLayout = QtWidgets.QVBoxLayout()
		self.grpDeviceInfoLayout.setContentsMargins(-1, 3, -1, -1)
		rowDeviceInfo1 = QtWidgets.QHBoxLayout()
		self.lblDeviceName = QtWidgets.QLabel("Device:")
		self.lblDeviceName.setMinimumWidth(120)
		self.lblDeviceNameResult = QtWidgets.QLabel("GBxCart RW")
		rowDeviceInfo1.addWidget(self.lblDeviceName)
		rowDeviceInfo1.addWidget(self.lblDeviceNameResult)
		rowDeviceInfo1.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo1)
		rowDeviceInfo3 = QtWidgets.QHBoxLayout()
		self.lblDeviceFWVer = QtWidgets.QLabel("Firmware version:")
		self.lblDeviceFWVer.setMinimumWidth(120)
		self.lblDeviceFWVerResult = QtWidgets.QLabel("R30+L1")
		rowDeviceInfo3.addWidget(self.lblDeviceFWVer)
		rowDeviceInfo3.addWidget(self.lblDeviceFWVerResult)
		rowDeviceInfo3.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo3)
		rowDeviceInfo2 = QtWidgets.QHBoxLayout()
		self.lblDevicePCBVer = QtWidgets.QLabel("PCB version:")
		self.lblDevicePCBVer.setMinimumWidth(120)
		#self.lblDevicePCBVerResult = QtWidgets.QLabel("v1.4")
		self.optDevicePCBVer14 = QtWidgets.QRadioButton("v1.4")
		self.connect(self.optDevicePCBVer14, QtCore.SIGNAL("clicked()"), self.SetPCBVersion)
		self.optDevicePCBVer14a = QtWidgets.QRadioButton("v1.4a")
		self.connect(self.optDevicePCBVer14a, QtCore.SIGNAL("clicked()"), self.SetPCBVersion)
		rowDeviceInfo2.addWidget(self.lblDevicePCBVer)
		#rowDeviceInfo2.addWidget(self.lblDevicePCBVerResult)
		rowDeviceInfo2.addWidget(self.optDevicePCBVer14)
		rowDeviceInfo2.addWidget(self.optDevicePCBVer14a)
		rowDeviceInfo2.addStretch(1)
		self.grpDeviceInfoLayout.addLayout(rowDeviceInfo2)
		self.grpDeviceInfo.setLayout(self.grpDeviceInfoLayout)
		self.layout_device.addWidget(self.grpDeviceInfo)
		# ↑↑↑ Current Device Information
		
		# ↓↓↓ Available Firmware Updates
		self.grpAvailableFwUpdates = QtWidgets.QGroupBox("Available Firmware")
		self.grpAvailableFwUpdates.setMinimumWidth(400)
		self.grpAvailableFwUpdatesLayout = QtWidgets.QVBoxLayout()
		self.grpAvailableFwUpdatesLayout.setContentsMargins(-1, 3, -1, -1)

		rowDeviceInfo4 = QtWidgets.QHBoxLayout()
		self.lblDeviceFWVer2 = QtWidgets.QLabel("Firmware version:")
		self.lblDeviceFWVer2.setMinimumWidth(120)
		self.lblDeviceFWVer2Result = QtWidgets.QLabel("(Please choose the PCB version)")
		rowDeviceInfo4.addWidget(self.lblDeviceFWVer2)
		rowDeviceInfo4.addWidget(self.lblDeviceFWVer2Result)
		rowDeviceInfo4.addStretch(1)
		self.grpAvailableFwUpdatesLayout.addLayout(rowDeviceInfo4)

		self.rowUpdate = QtWidgets.QHBoxLayout()
		self.btnUpdate = QtWidgets.QPushButton("Install Firmware Update")
		self.btnUpdate.setMinimumWidth(200)
		self.btnUpdate.setContentsMargins(20, 20, 20, 20)
		self.connect(self.btnUpdate, QtCore.SIGNAL("clicked()"), lambda: [ self.UpdateFirmware() ])
		self.rowUpdate.addStretch()
		self.rowUpdate.addWidget(self.btnUpdate)
		self.rowUpdate.addStretch()

		self.grpAvailableFwUpdatesLayout.addSpacing(3)
		self.grpAvailableFwUpdatesLayout.addItem(self.rowUpdate)
		self.grpAvailableFwUpdates.setLayout(self.grpAvailableFwUpdatesLayout)
		self.layout_device.addWidget(self.grpAvailableFwUpdates)
		# ↑↑↑ Available Firmware Updates

		self.grpStatus = QtWidgets.QGroupBox("")
		self.grpStatusLayout = QtWidgets.QGridLayout()
		self.prgStatus = QtWidgets.QProgressBar()
		self.prgStatus.setMinimum(0)
		self.prgStatus.setMaximum(1000)
		self.prgStatus.setValue(0)
		self.lblStatus = QtWidgets.QLabel("Ready.")

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

		self.lblDeviceNameResult.setText(self.DEV_NAME)
		self.lblDeviceFWVerResult.setText(self.FW_VER)
		#self.lblDevicePCBVerResult.setText(self.PCB_VER)
		if self.PCB_VER == "v1.4":
			self.optDevicePCBVer14.setChecked(True)
		elif self.PCB_VER == "v1.4a":
			self.optDevicePCBVer14a.setChecked(True)
		self.SetPCBVersion()
	
	def SetPCBVersion(self):
		if self.optDevicePCBVer14.isChecked():
			file_name = self.FWUPD.APP_PATH + "/res/fw_GBxCart_RW_v1_4.zip"
		elif self.optDevicePCBVer14a.isChecked():
			file_name = self.FWUPD.APP_PATH + "/res/fw_GBxCart_RW_v1_4a.zip"
		else:
			return

		with zipfile.ZipFile(file_name) as zip:
			with zip.open("fw.ini") as f: ini_file = f.read()
			ini_file = ini_file.decode(encoding="utf-8")
			self.INI = Util.IniSettings(ini=ini_file, main_section="Firmware")
			self.OFW_VER = self.INI.GetValue("fw_ver")
			self.OFW_BUILDTS = self.INI.GetValue("fw_buildts")
			self.OFW_TEXT = self.INI.GetValue("fw_text")
		
		self.lblDeviceFWVer2Result.setText("{:s} (dated {:s})".format(self.OFW_VER, datetime.datetime.fromtimestamp(int(self.OFW_BUILDTS)).astimezone().replace(microsecond=0).isoformat()))

	def run(self):
		try:
			self.layout.update()
			self.layout.activate()
			screenGeometry = QtWidgets.QDesktopWidget().screenGeometry()
			x = (screenGeometry.width() - self.width()) / 2
			y = (screenGeometry.height() - self.height()) / 2
			self.move(x, y)
			self.show()
		except:
			return
	
	def hideEvent(self, event):
		if self.DEVICE is None:
			self.APP.ConnectDevice()
		self.APP.activateWindow()
	
	def reject(self):
		if self.CloseDialog():
			super().reject()
	
	def CloseDialog(self):
		if self.btnClose.isEnabled() is False:
			text = "<b>WARNING:</b> If you close this window while a firmware update is still running, it may leave the device in an unbootable state. You can still recover it by running the Firmware Updater again later.<br><br>Are you sure you want to close this window?"
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.No)
			answer = msgbox.exec()
			if answer == QtWidgets.QMessageBox.No: return False
		return True
	
	def UpdateFirmware(self):
		if self.optDevicePCBVer14.isChecked():
			device_name = "v1.4"
			file_name = self.FWUPD.APP_PATH + "/res/fw_GBxCart_RW_v1_4.zip"
		elif self.optDevicePCBVer14a.isChecked():
			device_name = "v1.4a"
			file_name = self.FWUPD.APP_PATH + "/res/fw_GBxCart_RW_v1_4a.zip"
		else:
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="Please select the PCB version of your GBxCart RW device.", standardButtons=QtWidgets.QMessageBox.Ok)
			answer = msgbox.exec()
			return False

		self.APP.DisconnectDevice()

		text = "Please follow these steps to proceed with the firmware update:<ol><li>Disconnect the USB cable of your GBxCart RW {:s} device.</li><li>On the circuit board of your GBxCart RW {:s}, press and hold down the small button while connecting the USB cable again.</li><li>Keep the small button held for at least 2 seconds, then let go of it. If done right, the green LED labeled “Done” should remain lit.</li><li>Click OK to continue.</li></ol>".format(device_name, device_name)
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
		msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
		msgbox.setTextFormat(QtCore.Qt.TextFormat.RichText)
		answer = msgbox.exec()
		if answer == QtWidgets.QMessageBox.Cancel: return
		self.btnUpdate.setEnabled(False)
		self.btnClose.setEnabled(False)
		
		while True:
			ret = self.FWUPD.WriteFirmware(file_name, self.SetStatus)
			if ret == 1: 
				text = "The firmware update is complete!"
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
				answer = msgbox.exec()
				self.DEVICE = None
				self.reject()
				return True
			elif ret == 2:
				text = "The firmware update is has failed. Please try again."
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
				answer = msgbox.exec()
				return False
			elif ret == 3:
				text = "The firmware update file is corrupted. Please re-install the application."
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
				answer = msgbox.exec()
				return False
	
	def SetStatus(self, text, enableUI=False, setProgress=None):
		self.lblStatus.setText("Status: {:s}".format(text))
		if setProgress is not None:
			self.prgStatus.setValue(setProgress * 10)
		if enableUI:
			self.btnUpdate.setEnabled(True)
			self.btnClose.setEnabled(True)
		self.APP.QT_APP.processEvents()
