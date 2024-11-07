# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import zipfile, time, os, struct, serial, platform
try:
	from . import Util
except ImportError:
	import Util

class FirmwareUpdater():
	PORT = None
	DEVICE = None

	def __init__(self, app_path=".", port=None):
		self.APP_PATH = app_path
		self.PORT = port

	def CalcChecksum(self, buffer):
		checksum = 0
		for value in buffer[:0xFFFC]:
			checksum += value
		return checksum

	def TryConnect(self, port):
		return True

	def WriteFirmwareMSC(self, path, buffer, fncSetStatus):
		file = path
		path = os.path.dirname(path) + "/"
		fncSetStatus(text="Connecting... This may take a moment.")
		
		filename = os.path.split(file)[1]
		filepath = os.path.split(file)[0]
		with open(filepath + "/" + filename, "rb") as f: temp = f.read().decode("UTF-8", "ignore")
		if not temp.startswith("UPDATE"):
			with open(file, "wb") as f:
				temp = bytearray(b"UPDATE")
				temp += bytearray([0] * (256 - len(temp)))
				f.write(temp)
			hp = 30
			while hp > 0:
				if os.path.exists(path + "FIRMWARE.JR"): break
				time.sleep(1)
				hp -= 1
			if hp == 0:
				fncSetStatus(text="Couldn’t communicate with the Joey Jr device.")
				return 2
		
		try:
			with open(filepath + "/" + filename, "rb") as f: temp = f.read().decode("UTF-8", "ignore")
		except FileNotFoundError as e:
			try:
				if filename == "MODE.TXT":
					with open(filepath + "/" + "MODE!.TXT", "rb") as f: temp = f.read().decode("UTF-8", "ignore")
				else:
					raise FileNotFoundError from e
			except FileNotFoundError:
				fncSetStatus(text="Couldn’t access MODE.TXT. Remove cartridge and try again.")
				return 2

		if not temp.startswith("UPDATE"):
			fncSetStatus(text="Couldn’t enter UPDATE mode, please try again.")
			return 2

		fncSetStatus(text="Updating firmware... Do not unplug the device!", setProgress=0)
		os.unlink(path + "FIRMWARE.JR")
		if os.path.exists(path + "FIRMWARE.JR"):
			fncSetStatus(text="Couldn’t write new firmware, please try again.")
			return 2

		try:
			f = open(path + "FIRMWARE.JR", "wb")
		except OSError:
			fncSetStatus(text="Couldn’t write new firmware, please try again.")
			return 2
		
		for i in range(0, len(buffer), 64):
			f.write(buffer[i:i+64])
			percent = float(i + 64) / len(buffer) * 100
			fncSetStatus(text="Updating firmware... Do not unplug the device!", setProgress=percent)
		
		try:
			f.close()
		except OSError:
			pass

		if b"Joey Jr. Firmware" not in buffer:
			hp = 5
			while hp > 0:
				if not os.path.exists(path + "FIRMWARE.JR"): break
				time.sleep(1)
				hp -= 1
			if hp == 0:
				fncSetStatus(text="Couldn’t verify, please try again.")
				return 2

		fncSetStatus("Done.")
		time.sleep(2)

		return True
	
	def WriteFirmware(self, buffer, fncSetStatus):
		if struct.unpack(">I", buffer[0xFFFC:0x10000])[0] != self.CalcChecksum(buffer): return 3

		# Check for serial mode
		if self.PORT is None:
			ports = []
			comports = serial.tools.list_ports.comports()
			for i in range(0, len(comports)):
				if comports[i].vid == 0x483 and comports[i].pid == 0x5740:
					ports.append(comports[i].device)
			if len(ports) == 0:
				return 4
			port = ports[0]
		else:
			port = self.PORT

		while True:
			fncSetStatus(text="Connecting...")
			try:
				dev = serial.Serial(port, 2000000, timeout=0.2)
			except:
				fncSetStatus(text="Device not accessible.", enableUI=True)
				return 2
			dev.reset_input_buffer()

			fncSetStatus("Identifying device...")
			dev.write(b'\x55\xAA')
			time.sleep(0.01)
			device_id = dev.read(dev.in_waiting)
			
			if b"Joey" not in device_id:
				# print("Not a Joey Jr")
				fncSetStatus("Joey Jr device not found.")
				return 2
			
			if b"FW L" in device_id and device_id[-1] != 0:
				fncSetStatus("Rebooting device...")
				dev.write(b'\xF1')
				dev.read(1)
				dev.write(b'\x01')
				dev.close()
				time.sleep(0.5)
				continue
			break

		dev.write(b'\xFE\x01')
		time.sleep(0.01)
		dev.read(1)
		# print("")

		size = len(buffer)
		counter = 0
		while counter < size:
			percent = float(counter)/size*100
			fw_buffer = buffer[counter:counter+64]
			dev.write(fw_buffer)
			time.sleep(0.001)
			try:
				temp = dev.read(dev.in_waiting)
			except:
				temp = False
			if temp is not False:
				# print("Flashing...", hex(i), end="\r")
				pass
			elif counter + 64 < size:
				print("\nBad response at", counter)
				fncSetStatus(text="Error! Bad response at 0x{:X}!".format(counter), setProgress=percent)
				return 2
			
			counter += 64
			fncSetStatus(text="Updating firmware... Do not unplug the device!", setProgress=percent)

		dev.close()
		time.sleep(1)
		fncSetStatus("Done.", setProgress=100)
		time.sleep(2)
		return 1

try:
	from .pyside import QtCore, QtWidgets, QtGui, QDesktopWidget
	class FirmwareUpdaterWindow(QtWidgets.QDialog):
		APP = None
		DEVICE = None
		FWUPD = None
		DEV_NAME = "Joey Jr"
		FW_VER = ""
		PCB_VER = ""

		def __init__(self, app, app_path, file=None, icon=None, device=None):
			QtWidgets.QDialog.__init__(self)
			if icon is not None: self.setWindowIcon(QtGui.QIcon(icon))
			self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
			self.setWindowTitle("FlashGBX – Firmware Updater for Joey Jr")
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
			self.lblDeviceNameResult = QtWidgets.QLabel("Joey Jr")
			rowDeviceInfo1.addWidget(self.lblDeviceName)
			rowDeviceInfo1.addWidget(self.lblDeviceNameResult)
			rowDeviceInfo1.addStretch(1)
			self.grpDeviceInfoLayout.addLayout(rowDeviceInfo1)
			rowDeviceInfo3 = QtWidgets.QHBoxLayout()
			self.lblDeviceFWVer = QtWidgets.QLabel("Firmware version:")
			self.lblDeviceFWVer.setMinimumWidth(120)
			self.lblDeviceFWVerResult = QtWidgets.QLabel("L12")
			rowDeviceInfo3.addWidget(self.lblDeviceFWVer)
			rowDeviceInfo3.addWidget(self.lblDeviceFWVerResult)
			rowDeviceInfo3.addStretch(1)
			self.grpDeviceInfoLayout.addLayout(rowDeviceInfo3)
			self.grpDeviceInfo.setLayout(self.grpDeviceInfoLayout)
			self.layout_device.addWidget(self.grpDeviceInfo)
			# ↑↑↑ Current Device Information

			# ↓↓↓ Available Firmware Updates
			file_name = self.FWUPD.APP_PATH + "/res/fw_JoeyJr.zip"

			with zipfile.ZipFile(file_name) as zip:
				with zip.open("fw.ini") as f: ini_file = f.read()
				ini_file = ini_file.decode(encoding="utf-8")
				self.INI = Util.IniSettings(ini=ini_file, main_section="Firmware")
				self.FW_LK_VER = self.INI.GetValue("fw_ver")
				self.FW_LK_BUILDTS = self.INI.GetValue("fw_buildts")
				self.FW_LK_TEXT = self.INI.GetValue("fw_text")
				self.FW_MSC_VER = self.INI.GetValue("fw_msc_ver")
				self.FW_MSC_TEXT = self.INI.GetValue("fw_msc_text")
				self.FW_JOEYGUI_VER = self.INI.GetValue("fw_joeygui_ver")
				self.FW_JOEYGUI_TEXT = self.INI.GetValue("fw_joeygui_text")

			self.grpAvailableFwUpdates = QtWidgets.QGroupBox("Firmware Update Options")
			self.grpAvailableFwUpdates.setMinimumWidth(400)
			self.grpAvailableFwUpdatesLayout = QtWidgets.QVBoxLayout()
			self.grpAvailableFwUpdatesLayout.setContentsMargins(-1, 3, -1, -1)

			self.optFW_LK = QtWidgets.QRadioButton("{:s}".format(self.FW_LK_VER))
			self.lblFW_LK_Blerb = QtWidgets.QLabel("{:s}".format(self.FW_LK_TEXT))
			self.lblFW_LK_Blerb.setWordWrap(True)
			self.lblFW_LK_Blerb.mousePressEvent = lambda x: [ self.optFW_LK.setChecked(True) ]
			self.optFW_MSC = QtWidgets.QRadioButton("{:s}".format(self.FW_MSC_VER))
			self.lblFW_MSC_Blerb = QtWidgets.QLabel("{:s}".format(self.FW_MSC_TEXT))
			self.lblFW_MSC_Blerb.setWordWrap(True)
			self.lblFW_MSC_Blerb.mousePressEvent = lambda x: [ self.optFW_MSC.setChecked(True) ]
			self.optFW_JoeyGUI = QtWidgets.QRadioButton("{:s}".format(self.FW_JOEYGUI_VER))
			self.lblFW_JoeyGUI_Blerb = QtWidgets.QLabel("{:s}".format(self.FW_JOEYGUI_TEXT))
			self.lblFW_JoeyGUI_Blerb.setWordWrap(True)
			self.lblFW_JoeyGUI_Blerb.mousePressEvent = lambda x: [ self.optFW_JoeyGUI.setChecked(True) ]
			self.optExternal = QtWidgets.QRadioButton("External FIRMWARE.JR file")
			
			self.rowUpdate = QtWidgets.QHBoxLayout()
			self.btnUpdate = QtWidgets.QPushButton("Install Firmware Update")
			self.btnUpdate.setMinimumWidth(200)
			self.btnUpdate.setContentsMargins(20, 20, 20, 20)
			self.connect(self.btnUpdate, QtCore.SIGNAL("clicked()"), lambda: [ self.UpdateFirmware() ])
			self.rowUpdate.addStretch()
			self.rowUpdate.addWidget(self.btnUpdate)
			self.rowUpdate.addStretch()

			self.rowUpdate2 = QtWidgets.QHBoxLayout()
			self.lblUpdateDisclaimer = QtWidgets.QLabel("Please note that FlashGBX is not officially supported by BennVenn.")
			self.lblUpdateDisclaimer.setWordWrap(True)
			self.lblUpdateDisclaimer.setAlignment(QtGui.Qt.AlignmentFlag.AlignCenter)
			self.rowUpdate2.addWidget(self.lblUpdateDisclaimer)
			
			self.grpAvailableFwUpdatesLayout.addWidget(self.optFW_LK)
			self.grpAvailableFwUpdatesLayout.addWidget(self.lblFW_LK_Blerb)
			self.optFW_LK.setChecked(True)
			self.grpAvailableFwUpdatesLayout.addWidget(self.optFW_MSC)
			self.grpAvailableFwUpdatesLayout.addWidget(self.lblFW_MSC_Blerb)
			self.grpAvailableFwUpdatesLayout.addWidget(self.optFW_JoeyGUI)
			self.grpAvailableFwUpdatesLayout.addWidget(self.lblFW_JoeyGUI_Blerb)
			self.grpAvailableFwUpdatesLayout.addWidget(self.optExternal)
			self.grpAvailableFwUpdatesLayout.addSpacing(3)
			self.grpAvailableFwUpdatesLayout.addItem(self.rowUpdate)
			self.grpAvailableFwUpdatesLayout.addItem(self.rowUpdate2)
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

			self.lblDeviceNameResult.setText(self.DEV_NAME + " " + self.PCB_VER)
			self.lblDeviceFWVerResult.setText(self.FW_VER)

			# if platform.system() == 'Darwin':
			# 	self.optFW_MSC.setVisible(False)
			# 	self.lblFW_MSC_Blerb.setVisible(False)
		
		def run(self):
			try:
				self.layout.update()
				self.layout.activate()
				screenGeometry = QDesktopWidget().screenGeometry(self)
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
			with zipfile.ZipFile(self.FWUPD.APP_PATH + "/res/fw_JoeyJr.zip") as archive:
				fw = ""
				path = ""
				verified = False
				if self.optFW_LK.isChecked():
					fw = self.FW_LK_VER
					fn = "FIRMWARE_LK.JR"
					with archive.open(fn) as f: fw_data = bytearray(f.read())
					if (b"Joey Jr" in fw_data and b"FW LK" in fw_data): verified = True
				elif self.optFW_MSC.isChecked():
					fw = self.FW_MSC_VER
					fn = "FIRMWARE_MSC.JR"
					with archive.open(fn) as f: fw_data = bytearray(f.read())
					if (b"Joey Jr. Firmware" in fw_data): verified = True
				elif self.optFW_JoeyGUI.isChecked():
					fw = self.FW_JOEYGUI_VER
					fn = "FIRMWARE_JOEYGUI.JR"
					with archive.open(fn) as f: fw_data = bytearray(f.read())
					if (b"Joey Jr" in fw_data and b"FW GUI" in fw_data): verified = True
				else:
					path = self.APP.SETTINGS.value("LastDirFirmwareUpdate")
					path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Joey Jr Firmware File", path, "Firmware Update (FIRMWARE.JR)")[0]
					if path == "": return
					if not os.path.basename(path).endswith(".JR"):
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The expected filename for a valid firmware file is <b>FIRMWARE.JR</b>. Please visit <a href=\"https://bennvenn.myshopify.com/products/usb-gb-c-cart-dumper-the-joey-jr\">https://bennvenn.myshopify.com/products/usb-gb-c-cart-dumper-the-joey-jr</a> for the latest official firmware updates.", standardButtons=QtWidgets.QMessageBox.Ok)
						answer = msgbox.exec()
						return
					elif os.path.exists(os.path.dirname(path) + "DEBUG.TXT"):
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text="The selected file can not be used. Please visit <a href=\"https://bennvenn.myshopify.com/products/usb-gb-c-cart-dumper-the-joey-jr\">https://bennvenn.myshopify.com/products/usb-gb-c-cart-dumper-the-joey-jr</a> for the latest official firmware updates.", standardButtons=QtWidgets.QMessageBox.Ok)
						answer = msgbox.exec()
						return
					self.APP.SETTINGS.setValue("LastDirFirmwareUpdate", os.path.dirname(path))
					fw = path
					fn = None
					try:
						with open(path, "rb") as f: fw_data = bytearray(f.read())
						index_from = fw_data.index(b"Joey Jr")
						index_to = fw_data[index_from:].index(b"\x00")
						fw_string = fw_data[index_from:index_from+index_to].decode("ASCII", "ignore")
						if "Firmware" in fw_string:
							fw += "<br><br><b>Detected firmware string:</b><br>" + fw_string
							if "N64 Firmware" in fw_string: raise ValueError("N64 Firmware found")
							if "Jr4Gen3 Firmware" in fw_string: raise ValueError("Jr4Gen3 Firmware found")
						verified = True
						if len(fw_data) > 0x10000:
							verified = False
							raise ValueError("Firmware file is too large")
					except ValueError as e:
						fw += f"<br><br><b>Warning:</b> The selected firmware file couldn’t be confirmed to be valid automatically ({str(e)}). Please double check that this is a valid firmware file for your Joey Jr. If it is invalid or an update for a different device, it may render your device unusable."
					except:
						verified = False

			if verified is False:
				text = "The firmware update file is corrupted."
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
				answer = msgbox.exec()
				return False

			text = "The following firmware will now be written to your Joey Jr device:<br>- {:s}".format(fw)
			text += "<br><br>Do you want to continue?"
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
			msgbox.setTextFormat(QtCore.Qt.TextFormat.RichText)
			answer = msgbox.exec()
			if answer == QtWidgets.QMessageBox.No: return
			self.grpAvailableFwUpdates.setEnabled(False)
			self.btnUpdate.setEnabled(False)
			self.btnClose.setEnabled(False)

			self.APP.DisconnectDevice()
			
			ret = 0
			while True:
				if ret == 4:
					ret = self.FWUPD.WriteFirmwareMSC(path, fw_data, self.SetStatus)
				else:
					ret = self.FWUPD.WriteFirmware(fw_data, self.SetStatus)

				if ret == 1: 
					text = "The firmware update is complete!"
					self.grpAvailableFwUpdates.setEnabled(True)
					self.btnUpdate.setEnabled(True)
					self.btnClose.setEnabled(True)
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
					answer = msgbox.exec()
					self.DEVICE = None
					self.reject()
					return True
				elif ret == 2:
					text = "The firmware update has failed. Please try again."
					self.grpAvailableFwUpdates.setEnabled(True)
					self.btnUpdate.setEnabled(True)
					self.btnClose.setEnabled(True)
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
					answer = msgbox.exec()
					return False
				elif ret == 3:
					text = "The firmware update file is corrupted. Please re-install the application."
					self.grpAvailableFwUpdates.setEnabled(True)
					self.btnUpdate.setEnabled(True)
					self.btnClose.setEnabled(True)
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
					answer = msgbox.exec()
					return False
				elif ret == 4:
					if platform.system() == 'Darwin':
						self.SetStatus("No device found.", enableUI=True)
						text = "If your Joey Jr device is currently running the Drag'n'Drop firmware, please update the firmware on Windows or Linux, or use the standalone firmware updater."
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="FlashGBX", text=text, standardButtons=QtWidgets.QMessageBox.Ok)
						answer = msgbox.exec()
						return False
					answer = QtWidgets.QMessageBox.information(self, "FlashGBX", "If your Joey Jr device is currently running the Drag'n'Drop firmware, please continue and choose its <b>MODE.TXT</b> (or <b>MODE!.TXT</b>) file.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Ok)
					if answer == QtWidgets.QMessageBox.Cancel:
						self.SetStatus("No device found.", enableUI=True)
						return False
					path = self.APP.SETTINGS.value("LastDirFirmwareUpdate")
					path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose the MODE.TXT file of your Joey Jr removable drive", path, "MODE.TXT (MODE*.TXT)")[0]
					self.APP.QT_APP.processEvents()
					if os.path.basename(path) not in ("MODE.TXT", "MODE!.TXT"):
						self.SetStatus("No device found.", enableUI=True)
						return False
					self.APP.SETTINGS.setValue("LastDirFirmwareUpdate", os.path.dirname(path))
		
		def SetStatus(self, text, enableUI=False, setProgress=None):
			self.lblStatus.setText("Status: {:s}".format(text))
			if setProgress is not None:
				self.prgStatus.setValue(setProgress * 10)
			if enableUI:
				self.grpAvailableFwUpdates.setEnabled(True)
				self.btnUpdate.setEnabled(True)
				self.btnClose.setEnabled(True)
			self.APP.QT_APP.processEvents()
except ImportError:
	pass
