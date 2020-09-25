# -*- coding: utf-8 -*-
# ＵＴＦ－８
import sys, threading, os, glob, importlib, time, re, json, platform
from PySide2 import QtCore
from PySide2.QtCore import Qt, QSettings, QStandardPaths
from PySide2.QtWidgets import *
from PySide2.QtGui import QIcon, QGuiApplication

VERSION = "0.7β"
print("FlashGBX v" + VERSION + " by Lesserkuma")
print("\nDISCLAIMER: This software is provided as-is and the developer is not responsible for any damage that is caused by the use of it. Use at your own risk!\n")

class FlashGBX(QWidget):
	AGB_Header_ROM_Sizes = [ "4 MB", "8 MB", "16 MB", "32 MB" ]
	AGB_Header_ROM_Sizes_Map = [ 0x400000, 0x800000, 0x1000000, 0x2000000 ]
	AGB_Header_Save_Types = [ "None", "4K EEPROM (512 Bytes)", "64K EEPROM (8 KB)", "256K SRAM (32 KB)", "512K SRAM (64 KB)", "512K FLASH (64 KB)", "1M FLASH (128 KB)" ]
	AGB_Global_CRC32 = 0
	
	DMG_Header_Features = { 0x00:'ROM ONLY', 0x01:'MBC1', 0x02:'MBC1+RAM', 0x03:'MBC1+RAM+BATTERY', 0x05:'MBC2', 0x06:'MBC2+BATTERY', 0x08:'ROM+RAM', 0x09:'ROM+RAM+BATTERY', 0x0B:'MMM01', 0x0C:'MMM01+RAM', 0x0D:'MMM01+RAM+BATTERY', 0x0F:'MBC3+TIMER+BATTERY', 0x10:'MBC3+TIMER+RAM+BATTERY', 0x11:'MBC3', 0x12:'MBC3+RAM', 0x13:'MBC3+RAM+BATTERY', 0x15:'MBC4', 0x16:'MBC4+RAM', 0x17:'MBC4+RAM+BATTERY', 0x19:'MBC5', 0x1A:'MBC5+RAM', 0x1B:'MBC5+RAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1D:'MBC5+RUMBLE+RAM', 0x1E:'MBC5+RUMBLE+RAM+BATTERY', 0x20:'MBC6', 0x22:'MBC7+RAM+BATTERY', 0x55:'Game Genie', 0x56:'Game Genie v3.0', 0xFC:'POCKET CAMERA', 0xFD:'BANDAI TAMA5', 0xFE:'HuC3', 0xFF:'HuC1+RAM+BATTERY' }
	DMG_Header_Features_MBC = [ 0, 1, 1, 1, 2, 2, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 7, 0, 0, 0, 0, 0, 0 ]
	DMG_Header_ROM_Sizes = [ "32 KB", "64 KB", "128 KB", "256 KB", "512 KB", "1 MB", "1.1 MB", "1.2 MB", "1.5 MB", "2 MB", "4 MB", "8 MB" ]
	DMG_Header_ROM_Sizes_Map = [ 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x52, 0x53, 0x54, 0x06, 0x07, 0x08 ]
	DMG_Header_ROM_Sizes_Flasher_Map = [ 2, 4, 8, 16, 32, 64, 72, 80, 96, 128, 256, 512 ] # Number of ROM banks
	DMG_Header_RAM_Sizes = [ "None", "4K SRAM (512 Bytes)", "16K SRAM (2 KB)", "64K SRAM (8 KB)", "256K SRAM (32 KB)", "512K SRAM (64 KB)", "1M SRAM (128 KB)" ]
	DMG_Header_RAM_Sizes_Map = [ 0x00, 0x01, 0x01, 0x02, 0x03, 0x05, 0x04 ]
	DMG_Header_RAM_Sizes_Flasher_Map = [ 0, 0x200, 0x800, 0x2000, 0x8000, 0x10000, 0x20000 ] # RAM size in bytes
	DMG_Header_SGB = { 0x00:'No support', 0x03:'Supported' }
	DMG_Header_CGB = { 0x00:'No support', 0x80:'Supported', 0xC0:'Required' }
	
	CONN = None
	SETTINGS = None
	DEVICES = {}

	def resource_path(self, relative_path):
		""" Get absolute path to resource, works for dev and for PyInstaller """
		base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
		return os.path.join(base_path, relative_path)
		
	def __init__(self, argv):
		QWidget.__init__(self)
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.setWindowIcon(QIcon(self.resource_path("res/icon.ico")))
		self.setWindowTitle("FlashGBX v" + VERSION)
		self.setWindowFlags(self.windowFlags() | Qt.MSWindowsFixedSizeDialogHint);
		self.SETTINGS = QSettings(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) + "/config.ini", QSettings.IniFormat)
		if "--resetconfig" in argv: self.SETTINGS.clear()
		
		# Create the QVBoxLayout that lays out the whole form
		self.layout = QGridLayout()
		self.layout.setSizeConstraint(QLayout.SetFixedSize)
		self.layout_left = QVBoxLayout()
		self.layout_right = QVBoxLayout()
		self.layout.setContentsMargins(-1, 8, -1, 8)

		# Cartridge Information GroupBox
		self.grpDMGCartridgeInfo = self.GuiCreateGroupBoxDMGCartInfo()
		self.grpAGBCartridgeInfo = self.GuiCreateGroupBoxAGBCartInfo()
		self.grpAGBCartridgeInfo.setVisible(False)
		self.layout_left.addWidget(self.grpDMGCartridgeInfo)
		self.layout_left.addWidget(self.grpAGBCartridgeInfo)

		# Actions
		self.grpActions = QGroupBox("Options")
		self.grpActionsLayout = QVBoxLayout()
		self.grpActionsLayout.setContentsMargins(-1, 3, -1, -1)
		
		rowActionsMode = QHBoxLayout()
		self.lblMode = QLabel("Mode: ")
		rowActionsMode.addWidget(self.lblMode)
		self.optDMG = QRadioButton("&Game Boy")
		self.connect(self.optDMG, QtCore.SIGNAL("clicked()"), self.SetMode)
		self.optAGB = QRadioButton("Game Boy &Advance")
		self.connect(self.optAGB, QtCore.SIGNAL("clicked()"), self.SetMode)
		rowActionsMode.addWidget(self.optDMG)
		rowActionsMode.addWidget(self.optAGB)
		
		rowActionsGeneral1 = QHBoxLayout()
		self.btnHeaderRefresh = QPushButton("&Read Information")
		self.btnHeaderRefresh.setStyleSheet("min-height: 17px;")
		self.connect(self.btnHeaderRefresh, QtCore.SIGNAL("clicked()"), self.ReadCartridge)
		rowActionsGeneral1.addWidget(self.btnHeaderRefresh)

		rowActionsGeneral2 = QHBoxLayout()
		self.btnBackupROM = QPushButton("&Backup ROM")
		self.btnBackupROM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnBackupROM, QtCore.SIGNAL("clicked()"), self.BackupROM)
		rowActionsGeneral2.addWidget(self.btnBackupROM)
		self.btnFlashROM = QPushButton("&Flash ROM")
		self.btnFlashROM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnFlashROM, QtCore.SIGNAL("clicked()"), self.FlashROM)
		self.cmbDMGCartridgeTypeResult.currentIndexChanged.connect(self.CartridgeTypeChanged)
		rowActionsGeneral2.addWidget(self.btnFlashROM)

		rowActionsGeneral3 = QHBoxLayout()
		self.btnBackupRAM = QPushButton("Backup &Save Data")
		self.btnBackupRAM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnBackupRAM, QtCore.SIGNAL("clicked()"), self.BackupRAM)
		rowActionsGeneral3.addWidget(self.btnBackupRAM)
		self.btnRestoreRAM = QPushButton("R&estore Save Data")
		self.btnRestoreRAM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnRestoreRAM, QtCore.SIGNAL("clicked()"), self.RestoreRAM)
		rowActionsGeneral3.addWidget(self.btnRestoreRAM)

		self.grpActionsLayout.setSpacing(4)
		self.grpActionsLayout.addLayout(rowActionsMode)
		self.grpActionsLayout.addLayout(rowActionsGeneral1)
		self.grpActionsLayout.addLayout(rowActionsGeneral2)
		self.grpActionsLayout.addLayout(rowActionsGeneral3)
		self.grpActions.setLayout(self.grpActionsLayout)

		self.layout_right.addWidget(self.grpActions)

		# Transfer Status
		grpStatus = QGroupBox("Transfer Status")
		grpStatusLayout = QVBoxLayout()
		grpStatusLayout.setContentsMargins(-1, 3, -1, -1)

		rowStatus1a = QHBoxLayout()
		self.lblStatus1a = QLabel("Data transferred:")
		rowStatus1a.addWidget(self.lblStatus1a)
		self.lblStatus1aResult = QLabel("–")
		rowStatus1a.addWidget(self.lblStatus1aResult)
		grpStatusLayout.addLayout(rowStatus1a)
		rowStatus2a = QHBoxLayout()
		self.lblStatus2a = QLabel("Speed:")
		rowStatus2a.addWidget(self.lblStatus2a)
		self.lblStatus2aResult = QLabel("–")
		rowStatus2a.addWidget(self.lblStatus2aResult)
		grpStatusLayout.addLayout(rowStatus2a)
		rowStatus3a = QHBoxLayout()
		self.lblStatus3a = QLabel("Time elapsed:")
		rowStatus3a.addWidget(self.lblStatus3a)
		self.lblStatus3aResult = QLabel("–")
		rowStatus3a.addWidget(self.lblStatus3aResult)
		grpStatusLayout.addLayout(rowStatus3a)
		rowStatus4a = QHBoxLayout()
		self.lblStatus4a = QLabel("Ready.")
		rowStatus4a.addWidget(self.lblStatus4a)
		self.lblStatus4aResult = QLabel("")
		rowStatus4a.addWidget(self.lblStatus4aResult)
		grpStatusLayout.addLayout(rowStatus4a)

		rowStatus2 = QHBoxLayout()
		self.prgStatus = QProgressBar()
		self.prgStatus.setMinimum(0)
		self.prgStatus.setMaximum(1)
		self.prgStatus.setValue(0)
		rowStatus2.addWidget(self.prgStatus)
		self.btnCancel = QPushButton("&Abort")
		self.btnCancel.setEnabled(False)
		self.btnCancel.setStyleSheet("max-width: 50px;")
		self.connect(self.btnCancel, QtCore.SIGNAL("clicked()"), self.AbortOperation)
		rowStatus2.addWidget(self.btnCancel)

		grpStatusLayout.addLayout(rowStatus2)
		grpStatus.setLayout(grpStatusLayout)

		self.layout_right.addWidget(grpStatus)

		self.layout.addLayout(self.layout_left, 0, 0)
		self.layout.addLayout(self.layout_right, 0, 1)
		
		# List devices
		self.layout_devices = QHBoxLayout()
		self.lblDevice = QLabel()
		self.cmbDevice = QComboBox()
		self.layout_devices.addWidget(self.lblDevice)
		self.layout_devices.addWidget(self.cmbDevice)
		self.layout_devices.addStretch()
		
		self.btnScan = QPushButton("&Device Scan")
		self.connect(self.btnScan, QtCore.SIGNAL("clicked()"), self.FindDevices)
		self.btnConnect = QPushButton("&Connect")
		self.connect(self.btnConnect, QtCore.SIGNAL("clicked()"), self.ConnectDevice)
		self.layout_devices.addWidget(self.btnScan)
		self.layout_devices.addWidget(self.btnConnect)
		
		self.layout.addLayout(self.layout_devices, 1, 0, 1, 0)
		
		# Disable widgets
		self.optAGB.setEnabled(False)
		self.optDMG.setEnabled(False)
		self.btnHeaderRefresh.setEnabled(False)
		self.btnBackupROM.setEnabled(False)
		self.btnFlashROM.setEnabled(False)
		self.btnBackupRAM.setEnabled(False)
		self.btnRestoreRAM.setEnabled(False)
		
		# Scan for devices
		self.FindDevices()

		# Set the VBox layout as the window's main layout
		self.setLayout(self.layout)
	
	def GuiCreateGroupBoxDMGCartInfo(self):
		self.grpDMGCartridgeInfo = QGroupBox("Game Boy Cartridge Information")
		self.grpDMGCartridgeInfo.setMinimumWidth(280)
		group_layout = QVBoxLayout()
		group_layout.setContentsMargins(-1, 5, -1, -1)

		rowHeaderTitle = QHBoxLayout()
		lblHeaderTitle = QLabel("Game Title/Code:")
		lblHeaderTitle.setContentsMargins(0, 1, 0, 1)
		rowHeaderTitle.addWidget(lblHeaderTitle)
		self.lblHeaderTitleResult = QLabel("")
		rowHeaderTitle.addWidget(self.lblHeaderTitleResult)
		group_layout.addLayout(rowHeaderTitle)

		rowHeaderSGB = QHBoxLayout()
		lblHeaderSGB = QLabel("Super Game Boy:")
		lblHeaderSGB.setContentsMargins(0, 1, 0, 1)
		rowHeaderSGB.addWidget(lblHeaderSGB)
		self.lblHeaderSGBResult = QLabel("")
		rowHeaderSGB.addWidget(self.lblHeaderSGBResult)
		group_layout.addLayout(rowHeaderSGB)

		rowHeaderCGB = QHBoxLayout()
		lblHeaderCGB = QLabel("Game Boy Color:")
		lblHeaderCGB.setContentsMargins(0, 1, 0, 1)
		rowHeaderCGB.addWidget(lblHeaderCGB)
		self.lblHeaderCGBResult = QLabel("")
		rowHeaderCGB.addWidget(self.lblHeaderCGBResult)
		group_layout.addLayout(rowHeaderCGB)

		rowHeaderLogoValid = QHBoxLayout()
		lblHeaderLogoValid = QLabel("Nintendo Logo:")
		lblHeaderLogoValid.setContentsMargins(0, 1, 0, 1)
		rowHeaderLogoValid.addWidget(lblHeaderLogoValid)
		self.lblHeaderLogoValidResult = QLabel("")
		rowHeaderLogoValid.addWidget(self.lblHeaderLogoValidResult)
		group_layout.addLayout(rowHeaderLogoValid)

		rowHeaderChecksum = QHBoxLayout()
		lblHeaderChecksum = QLabel("Header Checksum:")
		lblHeaderChecksum.setContentsMargins(0, 1, 0, 1)
		rowHeaderChecksum.addWidget(lblHeaderChecksum)
		self.lblHeaderChecksumResult = QLabel("")
		rowHeaderChecksum.addWidget(self.lblHeaderChecksumResult)
		group_layout.addLayout(rowHeaderChecksum)

		rowHeaderROMChecksum = QHBoxLayout()
		lblHeaderROMChecksum = QLabel("ROM Checksum:")
		lblHeaderROMChecksum.setContentsMargins(0, 1, 0, 1)
		rowHeaderROMChecksum.addWidget(lblHeaderROMChecksum)
		self.lblHeaderROMChecksumResult = QLabel("")
		rowHeaderROMChecksum.addWidget(self.lblHeaderROMChecksumResult)
		group_layout.addLayout(rowHeaderROMChecksum)

		rowChipManufacturer = QHBoxLayout()
		self.lblChipManufacturer = QLabel("Chip Manufacturer:")
		self.lblChipManufacturer.setContentsMargins(0, 1, 0, 1)
		rowChipManufacturer.addWidget(self.lblChipManufacturer)
		self.lblChipManufacturerResult = QLabel("")
		rowChipManufacturer.addWidget(self.lblChipManufacturerResult)
		group_layout.addLayout(rowChipManufacturer)
		self.lblChipManufacturer.setVisible(False)
		self.lblChipManufacturerResult.setVisible(False)

		rowChipID = QHBoxLayout()
		self.lblChipID = QLabel("Chip ID:")
		self.lblChipID.setContentsMargins(0, 1, 0, 1)
		rowChipID.addWidget(self.lblChipID)
		self.lblChipIDResult = QLabel("")
		rowChipID.addWidget(self.lblChipIDResult)
		group_layout.addLayout(rowChipID)
		self.lblChipID.setVisible(False)
		self.lblChipIDResult.setVisible(False)

		rowHeaderROMSize = QHBoxLayout()
		lblHeaderROMSize = QLabel("ROM Size:")
		rowHeaderROMSize.addWidget(lblHeaderROMSize)
		self.cmbHeaderROMSizeResult = QComboBox()
		self.cmbHeaderROMSizeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbHeaderROMSizeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbHeaderROMSizeResult.addItems(self.DMG_Header_ROM_Sizes)
		self.cmbHeaderROMSizeResult.setCurrentIndex(self.cmbHeaderROMSizeResult.count() - 1)
		rowHeaderROMSize.addWidget(self.cmbHeaderROMSizeResult)
		group_layout.addLayout(rowHeaderROMSize)

		rowHeaderRAMSize = QHBoxLayout()
		lblHeaderRAMSize = QLabel("Save Data Type:")
		rowHeaderRAMSize.addWidget(lblHeaderRAMSize)
		self.cmbHeaderRAMSizeResult = QComboBox()
		self.cmbHeaderRAMSizeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbHeaderRAMSizeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbHeaderRAMSizeResult.addItems(self.DMG_Header_RAM_Sizes)
		self.cmbHeaderRAMSizeResult.setCurrentIndex(self.cmbHeaderRAMSizeResult.count() - 1)
		rowHeaderRAMSize.addWidget(self.cmbHeaderRAMSizeResult)
		group_layout.addLayout(rowHeaderRAMSize)

		rowHeaderFeatures = QHBoxLayout()
		lblHeaderFeatures = QLabel("Features:")
		rowHeaderFeatures.addWidget(lblHeaderFeatures)
		self.cmbHeaderFeaturesResult = QComboBox()
		self.cmbHeaderFeaturesResult.setStyleSheet("combobox-popup: 0;");
		self.cmbHeaderFeaturesResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbHeaderFeaturesResult.addItems(self.DMG_Header_Features.values())
		rowHeaderFeatures.addWidget(self.cmbHeaderFeaturesResult)
		group_layout.addLayout(rowHeaderFeatures)

		rowCartridgeType = QHBoxLayout()
		lblCartridgeType = QLabel("Type:")
		rowCartridgeType.addWidget(lblCartridgeType)
		self.cmbDMGCartridgeTypeResult = QComboBox()
		self.cmbDMGCartridgeTypeResult.setStyleSheet("max-width: 260px;")
		self.cmbDMGCartridgeTypeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbDMGCartridgeTypeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		rowCartridgeType.addWidget(self.cmbDMGCartridgeTypeResult)
		group_layout.addLayout(rowCartridgeType)

		self.grpDMGCartridgeInfo.setLayout(group_layout)
		
		return self.grpDMGCartridgeInfo
	
	def GuiCreateGroupBoxAGBCartInfo(self):
		self.grpAGBCartridgeInfo = QGroupBox("Game Boy Advance Cartridge Information")
		self.grpAGBCartridgeInfo.setMinimumWidth(280)
		group_layout = QVBoxLayout()
		group_layout.setContentsMargins(-1, 5, -1, -1)

		rowAGBHeaderTitle = QHBoxLayout()
		lblAGBHeaderTitle = QLabel("Game Title:")
		lblAGBHeaderTitle.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderTitle.addWidget(lblAGBHeaderTitle)
		self.lblAGBHeaderTitleResult = QLabel("")
		rowAGBHeaderTitle.addWidget(self.lblAGBHeaderTitleResult)
		group_layout.addLayout(rowAGBHeaderTitle)

		rowAGBHeaderCode = QHBoxLayout()
		lblAGBHeaderCode = QLabel("Game Code:")
		lblAGBHeaderCode.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderCode.addWidget(lblAGBHeaderCode)
		self.lblAGBHeaderCodeResult = QLabel("")
		rowAGBHeaderCode.addWidget(self.lblAGBHeaderCodeResult)
		group_layout.addLayout(rowAGBHeaderCode)

		rowAGBHeaderVersion = QHBoxLayout()
		lblAGBHeaderVersion = QLabel("Version:")
		lblAGBHeaderVersion.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderVersion.addWidget(lblAGBHeaderVersion)
		self.lblAGBHeaderVersionResult = QLabel("")
		rowAGBHeaderVersion.addWidget(self.lblAGBHeaderVersionResult)
		group_layout.addLayout(rowAGBHeaderVersion)

		rowAGBHeaderLogoValid = QHBoxLayout()
		lblAGBHeaderLogoValid = QLabel("Nintendo Logo:")
		lblAGBHeaderLogoValid.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderLogoValid.addWidget(lblAGBHeaderLogoValid)
		self.lblAGBHeaderLogoValidResult = QLabel("")
		rowAGBHeaderLogoValid.addWidget(self.lblAGBHeaderLogoValidResult)
		group_layout.addLayout(rowAGBHeaderLogoValid)

		rowAGBHeader96h = QHBoxLayout()
		lblAGBHeader96h = QLabel("Cartridge Identifier:")
		lblAGBHeader96h.setContentsMargins(0, 1, 0, 1)
		rowAGBHeader96h.addWidget(lblAGBHeader96h)
		self.lblAGBHeader96hResult = QLabel("")
		rowAGBHeader96h.addWidget(self.lblAGBHeader96hResult)
		group_layout.addLayout(rowAGBHeader96h)

		rowAGBHeaderChecksum = QHBoxLayout()
		lblAGBHeaderChecksum = QLabel("Header Checksum:")
		lblAGBHeaderChecksum.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderChecksum.addWidget(lblAGBHeaderChecksum)
		self.lblAGBHeaderChecksumResult = QLabel("")
		rowAGBHeaderChecksum.addWidget(self.lblAGBHeaderChecksumResult)
		group_layout.addLayout(rowAGBHeaderChecksum)

		rowAGBHeaderROMChecksum = QHBoxLayout()
		lblAGBHeaderROMChecksum = QLabel("ROM Checksum:")
		lblAGBHeaderROMChecksum.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderROMChecksum.addWidget(lblAGBHeaderROMChecksum)
		self.lblAGBHeaderROMChecksumResult = QLabel("")
		rowAGBHeaderROMChecksum.addWidget(self.lblAGBHeaderROMChecksumResult)
		group_layout.addLayout(rowAGBHeaderROMChecksum)
		
		rowAGBHeaderROMSize = QHBoxLayout()
		lblAGBHeaderROMSize = QLabel("ROM Size:")
		rowAGBHeaderROMSize.addWidget(lblAGBHeaderROMSize)
		self.cmbAGBHeaderROMSizeResult = QComboBox()
		self.cmbAGBHeaderROMSizeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbAGBHeaderROMSizeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbAGBHeaderROMSizeResult.addItems(self.AGB_Header_ROM_Sizes)
		self.cmbAGBHeaderROMSizeResult.setCurrentIndex(self.cmbAGBHeaderROMSizeResult.count() - 1)
		rowAGBHeaderROMSize.addWidget(self.cmbAGBHeaderROMSizeResult)
		group_layout.addLayout(rowAGBHeaderROMSize)
		
		rowAGBHeaderRAMSize = QHBoxLayout()
		lblAGBHeaderRAMSize = QLabel("Save Data Type:")
		rowAGBHeaderRAMSize.addWidget(lblAGBHeaderRAMSize)
		self.cmbAGBSaveTypeResult = QComboBox()
		self.cmbAGBSaveTypeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbAGBSaveTypeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbAGBSaveTypeResult.addItems(self.AGB_Header_Save_Types)
		self.cmbAGBSaveTypeResult.setCurrentIndex(self.cmbAGBSaveTypeResult.count() - 1)
		rowAGBHeaderRAMSize.addWidget(self.cmbAGBSaveTypeResult)
		group_layout.addLayout(rowAGBHeaderRAMSize)
		
		rowAGBCartridgeType = QHBoxLayout()
		lblAGBCartridgeType = QLabel("Type:")
		rowAGBCartridgeType.addWidget(lblAGBCartridgeType)
		self.cmbAGBCartridgeTypeResult = QComboBox()
		self.cmbAGBCartridgeTypeResult.setStyleSheet("max-width: 260px;")
		self.cmbAGBCartridgeTypeResult.setStyleSheet("combobox-popup: 0;");
		self.cmbAGBCartridgeTypeResult.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.cmbAGBCartridgeTypeResult.currentIndexChanged.connect(self.CartridgeTypeChanged)
		rowAGBCartridgeType.addWidget(self.cmbAGBCartridgeTypeResult)
		group_layout.addLayout(rowAGBCartridgeType)

		self.grpAGBCartridgeInfo.setLayout(group_layout)
		return self.grpAGBCartridgeInfo

	def ImportPlugin(self, file, class_name):
		module_object = importlib.import_module(file)
		target_class = getattr(module_object, class_name)
		return target_class()
	
	def DisconnectDevice(self):
		try:
			self.CONN.Close()
		except:
			pass
		self.CONN = None
		self.btnScan.show()
		self.optAGB.setEnabled(False)
		self.optDMG.setEnabled(False)
		self.btnHeaderRefresh.setEnabled(False)
		self.btnBackupROM.setEnabled(False)
		self.btnFlashROM.setEnabled(False)
		self.btnBackupRAM.setEnabled(False)
		self.btnRestoreRAM.setEnabled(False)
		self.btnConnect.setText("Connect")
	
	def ConnectDevice(self):
		if self.CONN is not None:
			self.DisconnectDevice()
			return True
		else:
			if self.cmbDevice.count() > 0:
				index = self.cmbDevice.currentText()
			else:
				index = self.lblDevice.text()

			if index not in self.DEVICES:
				self.FindDevices()
			
			dev = self.DEVICES[index]
			ret = dev.Initialize()
			
			if ret is False:
				self.CONN = None
				return False
			elif isinstance(ret, list):
				for i in range(0, len(ret)):
					status = ret[i][0]
					msg = ret[i][1]
					if status == 0:
						print(msg)
					elif status == 1:
						QMessageBox.information(self, "FlashGBX", msg, QMessageBox.Ok)
					elif status == 2:
						QMessageBox.warning(self, "FlashGBX", msg, QMessageBox.Ok)
					elif status == 3:
						QMessageBox.critical(self, "FlashGBX", msg, QMessageBox.Ok)
						self.CONN = None
						return False
			
			if dev.IsConnected():
				self.CONN = dev
				self.btnScan.hide()
				self.optAGB.setEnabled(True)
				self.optDMG.setEnabled(True)
				self.optAGB.setAutoExclusive(False)
				self.optDMG.setAutoExclusive(False)
				self.optDMG.setChecked(False)
				self.optAGB.setChecked(False)
				self.optAGB.setAutoExclusive(True)
				self.optDMG.setAutoExclusive(True)
				self.btnConnect.setText("&Disconnect")
				self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }");
				self.lblDevice.setText(dev.GetFullName() + " (" + dev.GetPort() + ")")
				print("Connected to " + dev.GetFullName() + " on port " + dev.GetPort())
				
				if self.CONN.GetMode() == "DMG":
					self.cmbDMGCartridgeTypeResult.clear()
					self.cmbDMGCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesDMG()[0])
					self.grpAGBCartridgeInfo.setVisible(False)
					self.grpDMGCartridgeInfo.setVisible(True)
				elif self.CONN.GetMode() == "AGB":
					self.cmbAGBCartridgeTypeResult.clear()
					self.cmbAGBCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesAGB()[0])
					self.grpDMGCartridgeInfo.setVisible(False)
					self.grpAGBCartridgeInfo.setVisible(True)
				
				return True
			return False
	
	def FindDevices(self, connectToFirst=False):
		self.lblDevice.setText("Searching...")
		qt_app.processEvents()
		time.sleep(0.1)
		
		global hw_plugins
		hw_plugins = []
		for file in glob.glob("hw_*.py"):
			hw_plugins.append(os.path.splitext(file)[0])
		
		for hw_plugin in hw_plugins:
			dev = self.ImportPlugin(hw_plugin, 'GbxDevice')
			ret = dev.Initialize()
			if ret is False:
				self.CONN = None
			elif isinstance(ret, list):
				for i in range(0, len(ret)):
					status = ret[i][0]
					msg = ret[i][1]
					if status == 3:
						QMessageBox.critical(self, "FlashGBX", msg, QMessageBox.Ok)
						self.CONN = None
			
			if dev.IsConnected():
				self.DEVICES[dev.GetFullName()] = dev
				dev.Close()
		
		self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }");
		
		if len(self.DEVICES) == 0:
			self.lblDevice.setText("No devices found.")
			self.lblDevice.setStyleSheet("");
			self.cmbDevice.clear()
			self.btnConnect.setEnabled(False)
		elif len(self.DEVICES) == 1 or (connectToFirst and len(self.DEVICES) > 1):
			self.lblDevice.setText(list(self.DEVICES.keys())[0])
			self.lblDevice.setStyleSheet("");
			self.ConnectDevice()
			self.cmbDevice.clear()
			self.btnConnect.setEnabled(True)
		else:
			self.lblDevice.setText("Select device:")
			self.cmbDevice.clear()
			self.cmbDevice.addItems(self.DEVICES.keys())
			self.cmbDevice.setCurrentIndex(0)
			self.cmbDevice.setStyleSheet("");
			self.btnConnect.setEnabled(True)
		
		if len(self.DEVICES) == 0: return False
		return True

	def AbortOperation(self):
		self.btnCancel.setEnabled(False)
		self.CONN.CANCEL = True

	def FinishOperation(self):
		self.lblStatus4aResult.setText("")
		self.grpDMGCartridgeInfo.setEnabled(True)
		self.grpAGBCartridgeInfo.setEnabled(True)
		self.grpActions.setEnabled(True)
		self.btnCancel.setEnabled(False)
		self.prgStatus.setMinimum(0)
		self.prgStatus.setMaximum(1)
		self.prgStatus.setValue(1)
		
		if self.CONN.INFO["last_action"] == 4: # Flash ROM
			self.CONN.INFO["last_action"] = 0
			t1 = self.lblStatus1aResult.text()
			t2 = self.lblStatus2aResult.text()
			t3 = self.lblStatus3aResult.text()
			t4 = self.cmbDMGCartridgeTypeResult.currentIndex()
			t5 = self.cmbAGBCartridgeTypeResult.currentIndex()
			self.ReadCartridge()
			self.lblStatus1aResult.setText(t1)
			self.lblStatus2aResult.setText(t2)
			self.lblStatus3aResult.setText(t3)
			self.lblStatus4a.setText("Done!")
			self.cmbDMGCartridgeTypeResult.setCurrentIndex(t4)
			self.cmbAGBCartridgeTypeResult.setCurrentIndex(t5)
			msgbox = QMessageBox(parent=self, icon=QMessageBox.Information, windowTitle="FlashGBX", text="The ROM was flashed successfully!", standardButtons=QMessageBox.Ok)
			msgbox.exec()
		
		elif self.CONN.INFO["last_action"] == 1: # Backup ROM
			self.CONN.INFO["last_action"] = 0
			if self.CONN.GetMode() == "DMG":
				if self.CONN.INFO["rom_checksum"] == self.CONN.INFO["rom_checksum_calc"]:
					self.lblHeaderROMChecksumResult.setText("OK (0x{:04X})".format(self.CONN.INFO["rom_checksum"]))
					self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }");
					self.lblStatus4a.setText("Done!")
					msgbox = QMessageBox(parent=self, icon=QMessageBox.Information, windowTitle="FlashGBX", text="The ROM was dumped successfully!", standardButtons=QMessageBox.Ok)
					msgbox.exec()
				else:
					self.lblHeaderROMChecksumResult.setText("Invalid (0x{:04X}≠0x{:04X})".format(self.CONN.INFO["rom_checksum_calc"], self.CONN.INFO["rom_checksum"]))
					self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }");
					self.lblStatus4a.setText("Done.")
					QMessageBox.warning(self, "FlashGBX", "The ROM dump is complete, but the checksum is not correct. This may indicate a bad dump, however this is normal for some bootleg cartridges, prototypes and patched games.", QMessageBox.Ok)
			elif self.CONN.GetMode() == "AGB":
				if self.AGB_Global_CRC32 == self.CONN.INFO["rom_checksum_calc"]:
					self.lblAGBHeaderROMChecksumResult.setText("OK (0x{:06X})".format(self.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }");
					self.lblStatus4a.setText("Done!")
					msgbox = QMessageBox(parent=self, icon=QMessageBox.Information, windowTitle="FlashGBX", text="The ROM was dumped successfully!", standardButtons=QMessageBox.Ok)
					msgbox.exec()
				elif self.AGB_Global_CRC32 == 0:
					self.lblAGBHeaderROMChecksumResult.setText("0x{:06X}".format(self.CONN.INFO["rom_checksum_calc"]))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
					self.lblStatus4a.setText("Done!")
					QMessageBox.information(self, "FlashGBX", "The ROM was dumped successfully, but its integrity could not be verified as this ROM is not in the database.", QMessageBox.Ok)
				else:
					self.lblAGBHeaderROMChecksumResult.setText("Invalid (0x{:06X}≠0x{:06X})".format(self.CONN.INFO["rom_checksum_calc"], self.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }");
					self.lblStatus4a.setText("Done.")
					QMessageBox.warning(self, "FlashGBX", "The ROM dump is complete, but the checksum doesn’t match the known database entry. This may indicate a bad dump, however this is normal for some bootleg cartridges, prototypes and patched games.", QMessageBox.Ok)
		
		elif self.CONN.INFO["last_action"] == 2: # Backup RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0

		elif self.CONN.INFO["last_action"] == 3: # Restore RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0
		else:
			self.lblStatus4a.setText("Ready.")
			self.CONN.INFO["last_action"] = 0
	
	def CartridgeTypeAutoDetect(self):
		cart_type = 0
		cart_text = ""
		
		msgbox = QMessageBox(parent=self, icon=QMessageBox.Question, windowTitle="FlashGBX", text="Would you like FlashGBX to try and auto-detect the flash cartridge type?", standardButtons=QMessageBox.Yes | QMessageBox.No)
		cb = QCheckBox("Limit voltage to 3.3V", checked=True)
		if self.CONN.GetMode() == "DMG":
			msgbox.setCheckBox(cb)
		answer = msgbox.exec()
		limitVoltage = cb.isChecked()
		if answer == QMessageBox.No:
			return 0
		else:
			detected = self.CONN.AutoDetectFlash(limitVoltage)
			if len(detected) == 0:
				msgbox = QMessageBox(parent=self, icon=QMessageBox.Question, windowTitle="FlashGBX", text="No pre-configured flash cartridge type was detected. You can still try and manually select one from the list -- look for similar PCB text and/or flash chip markings. However, chances are this cartridge is currently not supported for flashing with FlashGBX.\n\nWould you like FlashGBX to run a Flash ID check? This may help adding support for your flash cartridge in the future.", standardButtons=QMessageBox.Yes | QMessageBox.No)
				if self.CONN.GetMode() == "DMG":
					msgbox.setCheckBox(cb)
				answer = msgbox.exec()
				if self.CONN.GetMode() == "DMG":
					limitVoltage = cb.isChecked()
				else:
					limitVoltage = False
				
				if answer == QMessageBox.Yes:
					check = self.CONN.CheckFlashID(limitVoltage)
					if check == "":
						QMessageBox.information(self, "FlashGBX", "There was no Flash ID response from the cartridge. There probably is no flash ROM chip or it requires unique unlocking and handling.", QMessageBox.Ok)
					else:
						QMessageBox.information(self, "FlashGBX", "Here is what the Flash ID check returned: <pre>" + check + "</pre> This information along with a good quality picture of the PCB with readable chip markings may help adding support for your flash cartridge. You should be able to copy & paste the text above.", QMessageBox.Ok)
				return 0
			else:
				cart_type = detected[0]
				if self.CONN.GetMode() == "DMG":
					cart_types = self.CONN.GetSupportedCartridgesDMG()
					for i in range(0, len(detected)):
						cart_text += cart_types[0][detected[i]] + "\n"
				elif self.CONN.GetMode() == "AGB":
					cart_types = self.CONN.GetSupportedCartridgesAGB()
					for i in range(0, len(detected)):
						cart_text += cart_types[0][detected[i]] + "\n"
				
				if len(detected) == 1:
					msg_text = "The following flash cartridge type was detected:\n" + cart_text + "\nIt seems to have a storage capacity of up to {:d} MB.\nOther features (such as save data type) have to be manually selected.".format(int(cart_types[1][detected[0]]['flash_size'] / 1024 / 1024))
					if self.CONN.GetMode() == "DMG":
						for i in range(0, len(self.DMG_Header_ROM_Sizes_Flasher_Map)):
							if cart_types[1][detected[0]]['flash_size'] == (self.DMG_Header_ROM_Sizes_Flasher_Map[i] * 0x4000):
								self.cmbHeaderROMSizeResult.setCurrentIndex(i)
					elif self.CONN.GetMode() == "AGB":
						for i in range(0, len(self.AGB_Header_ROM_Sizes_Map)):
							if cart_types[1][detected[0]]['flash_size'] == self.AGB_Header_ROM_Sizes_Map[i]:
								self.cmbAGBHeaderROMSizeResult.setCurrentIndex(i)
				else:
					msg_text = "The following flash cartridge type variants were detected:\n" + cart_text + "\nAll from this list should behave identical. The flash chip seems to have a storage capacity of up to {:d} MB.\nOther features (such as save data type) have to be manually selected.".format(int(cart_types[1][detected[0]]['flash_size'] / 1024 / 1024))
				
				if QMessageBox.Cancel == QMessageBox.information(self, "FlashGBX", msg_text, QMessageBox.Ok | QMessageBox.Cancel):
					return 0
		
		return cart_type
	
	def CartridgeTypeChanged(self, index):
		if self.CONN.GetMode() == "DMG":
			cart_types = self.CONN.GetSupportedCartridgesDMG()
			if cart_types[1][index] == "AUTODETECT": # special keyword
				cart_type = self.CartridgeTypeAutoDetect()
				if (cart_type == 1): cart_type = 0
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
		elif self.CONN.GetMode() == "AGB":
			cart_types = self.CONN.GetSupportedCartridgesAGB()
			if cart_types[1][index] == "AUTODETECT": # special keyword
				cart_type = self.CartridgeTypeAutoDetect()
				if (cart_type == 1): cart_type = 0
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)
		else:
			return
	
	def BackupROM(self):
		if not self.CheckDeviceAlive(): return
		features = self.DMG_Header_Features_MBC[self.cmbHeaderFeaturesResult.currentIndex()]
		rom_banks = self.DMG_Header_ROM_Sizes_Flasher_Map[self.cmbHeaderROMSizeResult.currentIndex()]
		rom_size = 0
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirRomDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			if self.CONN.INFO["cgb"] == 0xC0 or self.CONN.INFO["cgb"] == 0x80:
				path = path + ".gbc"
			elif self.CONN.INFO["sgb"] == 0x03:
				path = path + ".sgb"
			else:
				path = path + ".gb"
			path = QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy ROM File (*.gb *.sgb *.gbc);;All Files (*.*)")[0]
		
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirRomAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			rom_size = self.AGB_Header_ROM_Sizes_Map[self.cmbAGBHeaderROMSizeResult.currentIndex()]
			path = path + ".gba"
			path = QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy Advance ROM File (*.gba *.srl);;All Files (*.*)")[0]
		
		if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
		self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
		self.CONN.BackupROM(self.setProgress, path, features, rom_banks, rom_size)

	def FlashROM(self, dpath=""):
		if not self.CheckDeviceAlive(): return
		path = ""
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirRomDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			carts = self.CONN.GetSupportedCartridgesDMG()[1]
			cart_type = self.cmbDMGCartridgeTypeResult.currentIndex()
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirRomAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			carts = self.CONN.GetSupportedCartridgesAGB()[1]
			cart_type = self.cmbAGBCartridgeTypeResult.currentIndex()
		else:
			return
		
		if cart_type == 0:
			cart_type = self.CartridgeTypeAutoDetect()
			if (cart_type == 1): cart_type = 0
			if self.CONN.GetMode() == "DMG":
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
			elif self.CONN.GetMode() == "AGB":
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)
			if cart_type == 0: return
		
		if dpath != "":
			answer = QMessageBox.question(self, "FlashGBX", "The following ROM file will now be written to the flash cartridge:\n" + dpath, QMessageBox.Ok | QMessageBox.Cancel)
			if answer == QMessageBox.Cancel: return
			path = dpath
		
		while path == "":
			if self.CONN.GetMode() == "DMG":
				path = QFileDialog.getOpenFileName(self, "Flash ROM", last_dir, "Game Boy ROM File (*.gb *.gbc *.sgb *.bin);;All Files (*.*)")[0]
			elif self.CONN.GetMode() == "AGB":
				path = QFileDialog.getOpenFileName(self, "Flash ROM", last_dir, "Game Boy Advance ROM File (*.gba *.srl);;All Files (*.*)")[0]
			
			if (path == ""): return
		
		if os.path.getsize(path) > carts[cart_type]['flash_size']:
			answer = QMessageBox.warning(self, "FlashGBX", "The selected flash cartridge type seems to support ROMs that are up to " + str(int(carts[cart_type]['flash_size'] / 1024 / 1024)) + " MB in size, but the file you selected is " + str(os.path.getsize(path)/1024/1024) + " MB. You can still give it a try, but it’s possible that it’s too large.", QMessageBox.Ok | QMessageBox.Cancel)
			if answer == QMessageBox.Cancel: return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.CONN.FlashROM(self.setProgress, path, cart_type)

	def BackupRAM(self):
		if not self.CheckDeviceAlive(): return
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			features = self.DMG_Header_Features_MBC[self.cmbHeaderFeaturesResult.currentIndex()]
			save_type = self.DMG_Header_RAM_Sizes_Flasher_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QMessageBox.warning(self, "FlashGBX", "Please select the correct save data size.", QMessageBox.Ok)
				return
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			features = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QMessageBox.critical(self, "FlashGBX", "The save data type was not selected or auto-detection failed.", QMessageBox.Ok)
				return
		else:
			return

		path = re.sub(r"[<>:\"/\\|\?\*]", "_", path) + ".sav"
		path = QFileDialog.getSaveFileName(self, "Backup Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
		
		if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.CONN.BackupRAM(self.setProgress, path, features, save_type)

	def RestoreRAM(self, dpath=""):
		if not self.CheckDeviceAlive(): return
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			if dpath == "": path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			features = self.DMG_Header_Features_MBC[self.cmbHeaderFeaturesResult.currentIndex()]
			save_type = self.DMG_Header_RAM_Sizes_Flasher_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QMessageBox.warning(self, "FlashGBX", "Please select the correct save data size.", QMessageBox.Ok)
				return
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = "."
			if dpath == "": path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			features = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QMessageBox.critical(self, "FlashGBX", "The save data type was not selected or auto-detection failed.", QMessageBox.Ok)
				return
		else:
			return
		
		if dpath != "":
			answer = QMessageBox.question(self, "FlashGBX", "The following save data file will now be written to the cartridge:\n" + dpath, QMessageBox.Ok | QMessageBox.Cancel)
			if answer == QMessageBox.Cancel: return
			path = dpath
		else:
			path = path + ".sav"
			path = QFileDialog.getOpenFileName(self, "Restore Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
		if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.CONN.RestoreRAM(self.setProgress, path, features, save_type)
	
	def CheckDeviceAlive(self, setMode=False):
		if self.CONN is not None:
			mode = self.CONN.GetMode()
			if self.CONN.DEVICE is not None:
				if not self.CONN.IsConnected():
					self.DisconnectDevice()
					self.DEVICES = {}
					dontShowAgain = self.SETTINGS.value("AutoReconnect")
					if not dontShowAgain:
						cb = QCheckBox("Always try to reconnect without asking", checked=False)
						msgbox = QMessageBox(parent=self, icon=QMessageBox.Question, windowTitle="FlashGBX", text="The connection to the device was lost. Do you want to try and reconnect to the first device found? The cartridge information will also be reset and read again.", standardButtons=QMessageBox.Yes | QMessageBox.No)
						msgbox.setCheckBox(cb)
						answer = msgbox.exec()
						dontShowAgain = cb.isChecked()
						if dontShowAgain: self.SETTINGS.setValue("AutoReconnect", dontShowAgain)
						if answer == QMessageBox.No:
							return False
					if self.FindDevices(True):
						if setMode is not False: mode = setMode
						if mode == "DMG": self.optDMG.setChecked(True)
						elif mode == "AGB": self.optAGB.setChecked(True)
						self.SetMode()
						return True
					else:
						return False
				else:
					return True
		return False
	
	def SetMode(self):
		setTo = False
		mode = self.CONN.GetMode()
		if mode == "DMG":
			if self.optDMG.isChecked(): return
			setTo = "AGB"
		elif mode == "AGB":
			if self.optAGB.isChecked(): return
			setTo = "DMG"
		else:
			if self.optDMG.isChecked():
				setTo = "DMG"
			elif self.optAGB.isChecked():
				setTo = "AGB"
		
		dontShowAgain = self.SETTINGS.value("SkipModeChangeWarning")
		if not dontShowAgain and mode is not None:
			cb = QCheckBox("Don’t show this message again.", checked=False)
			msgbox = QMessageBox(parent=self, icon=QMessageBox.Warning, windowTitle="FlashGBX", text="The mode will now be changed to " + {"DMG":"Game Boy", "AGB":"Game Boy Advance"}[setTo] + " mode. To be safe, cartridges should only be exchanged while the device is not powered on.", standardButtons=QMessageBox.Ok | QMessageBox.Cancel)
			msgbox.setCheckBox(cb)
			answer = msgbox.exec()
			dontShowAgain = cb.isChecked()
			if dontShowAgain: self.SETTINGS.setValue("SkipModeChangeWarning", dontShowAgain)
			if answer == QMessageBox.Cancel:
				if mode == "DMG": self.optDMG.setChecked(True)
				if mode == "AGB": self.optAGB.setChecked(True)
				return False
		
		if not self.CheckDeviceAlive(setMode=setTo): return
		
		if self.optDMG.isChecked() and (mode == "AGB" or mode == None):
			self.CONN.SetMode("DMG")
		elif self.optAGB.isChecked() and (mode == "DMG" or mode == None):
			self.CONN.SetMode("AGB")
		
		self.ReadCartridge()
		self.btnHeaderRefresh.setEnabled(True)
		self.btnBackupROM.setEnabled(True)
		self.btnFlashROM.setEnabled(True)
		self.btnBackupRAM.setEnabled(True)
		self.btnRestoreRAM.setEnabled(True)
	
	def ReadCartridge(self):
		if not self.CheckDeviceAlive(): return
		data = self.CONN.ReadInfo()
		
		if data == False or len(data) == 0:
			self.DisconnectDevice()
			return False
				
		if self.CONN.GetMode() == "DMG":
			self.cmbDMGCartridgeTypeResult.clear()
			self.cmbDMGCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesDMG()[0])
			self.cmbDMGCartridgeTypeResult.setSizeAdjustPolicy(QComboBox.AdjustToContents)
			if "flash_type" in data:
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(data["flash_type"])

			if "manufacturer" in data:
				self.lblChipManufacturerResult.setText(data['manufacturer'])
				self.lblChipIDResult.setText("0x{:02X}".format(data['chip_id']))
			self.lblHeaderTitleResult.setText(data['game_title'])
			if data['sgb'] in self.DMG_Header_SGB:
				self.lblHeaderSGBResult.setText(self.DMG_Header_SGB[data['sgb']])
			else:
				self.lblHeaderSGBResult.setText("Unknown (0x{:02X})".format(data['sgb']))
			if data['cgb'] in self.DMG_Header_CGB:
				self.lblHeaderCGBResult.setText(self.DMG_Header_CGB[data['cgb']])
			else:
				self.lblHeaderCGBResult.setText("Unknown (0x{:02X})".format(data['cgb']))
			if data['logo_correct']:
				self.lblHeaderLogoValidResult.setText("OK")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			else:
				self.lblHeaderLogoValidResult.setText("Invalid")
				self.lblHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }");
			if data['header_checksum_correct']:
				self.lblHeaderChecksumResult.setText("OK (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			else:
				self.lblHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet("QLabel { color: red; }");
			self.lblHeaderROMChecksumResult.setText("0x{:04X}".format(data['rom_checksum']))
			self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			for i in range(0, len(self.DMG_Header_ROM_Sizes_Map)):
				if data["rom_size_raw"] == self.DMG_Header_ROM_Sizes_Map[i]:
					self.cmbHeaderROMSizeResult.setCurrentIndex(i)
			for i in range(0, len(self.DMG_Header_RAM_Sizes_Map)):
				if data["ram_size_raw"] == self.DMG_Header_RAM_Sizes_Map[i]:
					self.cmbHeaderRAMSizeResult.setCurrentIndex(i)
			i = 0
			for k, v in self.DMG_Header_Features.items():
				if data["features_raw"] == k:
					self.cmbHeaderFeaturesResult.setCurrentIndex(i)
					if k == 0x05 or k == 0x06: self.cmbHeaderRAMSizeResult.setCurrentIndex(1) # MBC2 Save
				i += 1
			
			self.grpAGBCartridgeInfo.setVisible(False)
			self.grpDMGCartridgeInfo.setVisible(True)
		
		elif self.CONN.GetMode() == "AGB":
			self.cmbAGBCartridgeTypeResult.clear()
			self.cmbAGBCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesAGB()[0])
			self.cmbAGBCartridgeTypeResult.setSizeAdjustPolicy(QComboBox.AdjustToContents)
			if "flash_type" in data:
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(data["flash_type"])

			self.lblAGBHeaderTitleResult.setText(data['game_title'])
			self.lblAGBHeaderCodeResult.setText(data['game_code'])
			self.lblAGBHeaderVersionResult.setText(str(data['version']))
			if data['logo_correct']:
				self.lblAGBHeaderLogoValidResult.setText("OK")
				self.lblAGBHeaderLogoValidResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeaderLogoValidResult.setText("Invalid")
				self.lblAGBHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }");

			if data['96h_correct']:
				self.lblAGBHeader96hResult.setText("OK")
				self.lblAGBHeader96hResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeader96hResult.setText("Invalid")
				self.lblAGBHeader96hResult.setStyleSheet("QLabel { color: red; }");
			
			if data['header_checksum_correct']:
				self.lblAGBHeaderChecksumResult.setText("OK (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet("QLabel { color: red; }");
			self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			self.lblAGBHeaderROMChecksumResult.setText("Not available")
			self.AGB_Global_CRC32 = 0
			
			db_agb_entry = None
			if os.path.exists("./config/db_AGB.json"):
				with open("./config/db_AGB.json") as f:
					db_agb = f.read()
					db_agb = json.loads(db_agb)
					if data["header_sha1"] in db_agb.keys():
						db_agb_entry = db_agb[data["header_sha1"]]
					else:
						self.lblAGBHeaderROMChecksumResult.setText("Not in database")
			
			if db_agb_entry != None:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(self.AGB_Header_ROM_Sizes_Map.index(db_agb_entry['rom_size']))
				if data["rom_size_calc"] < 0x400000:
					self.lblAGBHeaderROMChecksumResult.setText("In database (0x{:06X})".format(db_agb_entry['rom_crc32']))
					self.AGB_Global_CRC32 = db_agb_entry['rom_crc32']
			
			elif data["rom_size"] != 0:
				if not data["rom_size"] in self.AGB_Header_ROM_Sizes_Map:
					data["rom_size"] = 0x2000000
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(self.AGB_Header_ROM_Sizes_Map.index(data["rom_size"]))
			else:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(0)
			
			if data["save_type"] == None:
				self.cmbAGBSaveTypeResult.setCurrentIndex(0)
				if db_agb_entry != None:
					if db_agb_entry['savetype'] < len(self.AGB_Header_Save_Types):
						self.cmbAGBSaveTypeResult.setCurrentIndex(db_agb_entry['savetype'])

			self.grpDMGCartridgeInfo.setVisible(False)
			self.grpAGBCartridgeInfo.setVisible(True)

		self.lblStatus1aResult.setText("–")
		self.lblStatus2aResult.setText("–")
		self.lblStatus3aResult.setText("–")
		self.lblStatus4a.setText("Ready.")
		self.FinishOperation()

	def formatFileSize(self, size):
		size = size / 1024
		if size < 1024:
			return "{:.1f} KB".format(size)
		else:
			return "{:.2f} MB".format(size/1024)

	def formatProgressTime(self, sec):
		if int(sec) == 1:
			return "{:d} second".format(int(sec))
		elif sec < 60:
			return "{:d} seconds".format(int(sec))
		elif int(sec) == 60:
			return "1 minute"
		else:
			min = int(sec / 60)
			sec = int(sec % 60)
			s = str(min) + " "
			if min == 1:
				s = s + "minute"
			else:
				s = s + "minutes"
			s = s + ", " + str(sec) + " "
			if sec == 1:
				s = s + "second"
			else:
				s = s + "seconds"
			return s

	def setProgress(self, error, cur, max, speed=0, elapsed=0, left=0):
		if error != None and type(error) != type({}):
			self.lblStatus4a.setText("Failed!")
			self.grpDMGCartridgeInfo.setEnabled(True)
			self.grpAGBCartridgeInfo.setEnabled(True)
			self.grpActions.setEnabled(True)
			self.btnCancel.setEnabled(False)
			QMessageBox.critical(self, "FlashGBX", str(error), QMessageBox.Ok)
			return

		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		
		if (type(error) == type({})):
			if error["action"] == "ERASE":
				self.lblStatus1aResult.setText("Pending...")
				self.lblStatus2aResult.setText("Pending...")
				self.lblStatus3aResult.setText(self.formatProgressTime(elapsed))
				self.lblStatus4a.setText("Erasing flash...")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(error["abortable"])
				self.prgStatus.setMinimum(0)
				self.prgStatus.setMaximum(max)
				self.prgStatus.setValue(cur)
			elif error["action"] == "SECTOR_ERASE":
				self.lblStatus3aResult.setText(self.formatProgressTime(elapsed))
				self.lblStatus4a.setText("Erasing sector...")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(error["abortable"])
				self.prgStatus.setMinimum(0)
				self.prgStatus.setMaximum(max)
				self.prgStatus.setValue(cur)
			elif error["action"] == "VERIFY":
				self.lblStatus1aResult.setText("")
				self.lblStatus2aResult.setText("")
				self.lblStatus3aResult.setText(self.formatProgressTime(elapsed))
				self.lblStatus4a.setText("Verifying...")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(error["abortable"])
				self.prgStatus.setMinimum(0)
				self.prgStatus.setMaximum(max)
				self.prgStatus.setValue(cur)
			elif error["action"] == "ABORT":
				wd = 10
				while self.CONN.WORKER.isRunning():
					time.sleep(0.1)
					wd -= 1
					if wd == 0: break
					pass
				self.CONN.CANCEL = False
				self.grpDMGCartridgeInfo.setEnabled(True)
				self.grpAGBCartridgeInfo.setEnabled(True)
				self.grpActions.setEnabled(True)
				self.lblStatus1aResult.setText("–")
				self.lblStatus2aResult.setText("–")
				self.lblStatus3aResult.setText("–")
				self.lblStatus4a.setText("Aborted.")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(False)
				self.prgStatus.setMinimum(0)
				self.prgStatus.setMaximum(1)
				self.prgStatus.setValue(0)
				
				if "info_type" in error.keys() and "info_msg" in error.keys():
					if error["info_type"] == "msgbox_critical":
						QMessageBox.critical(self, "FlashGBX", error["info_msg"], QMessageBox.Ok)
					elif error["info_type"] == "msgbox_information":
						QMessageBox.information(self, "FlashGBX", error["info_msg"], QMessageBox.Ok)
					elif error["info_type"] == "label":
						self.lblStatus4a.setText(error["info_msg"])
				
				return
		else:
			self.prgStatus.setMinimum(0)
			self.prgStatus.setMaximum(max)
			self.prgStatus.setValue(cur)

			self.btnCancel.setEnabled(True)
			self.lblStatus1aResult.setText(self.formatFileSize(cur))
			if speed == 0:
				self.lblStatus2aResult.setText("–")
				self.lblStatus4aResult.setText("–")
				pass
			else:
				self.lblStatus2aResult.setText("{:.2f} KB/s".format(speed))
			self.lblStatus3aResult.setText(self.formatProgressTime(elapsed))
			self.lblStatus4a.setText("Time left:")
			if speed > 0 and left > 0:
				self.lblStatus4aResult.setText(self.formatProgressTime(left))
			elif max == cur:
				while self.CONN.WORKER.isRunning():
					time.sleep(0.1)
					pass
				self.FinishOperation()
	
	def dragEnterEvent(self, e):
		if self._dragEventHover(e):
			e.accept()
		else:
			e.ignore()

	def dragMoveEvent(self, e):
		if self._dragEventHover(e):
			e.accept()
		else:
			e.ignore()

	def _dragEventHover(self, e):
		if self.btnHeaderRefresh.isEnabled() and self.grpActions.isEnabled() and e.mimeData().hasUrls:
			for url in e.mimeData().urls():
				if platform.system() == 'Darwin':
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1] == ".sav":
					return True
				elif self.CONN.GetMode() == "DMG" and fn_split[1] in (".gb", ".sgb", ".gbc", ".bin"):
					return True
				elif self.CONN.GetMode() == "AGB" and fn_split[1] in (".gba", ".srl"):
					return True
				else:
					return False
		return False
	
	def dropEvent(self, e):
		if self.btnHeaderRefresh.isEnabled() and self.grpActions.isEnabled() and e.mimeData().hasUrls:
			e.setDropAction(QtCore.Qt.CopyAction)
			e.accept()
			for url in e.mimeData().urls():
				if platform.system() == 'Darwin':
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1] in (".gb", ".sgb", ".gbc", ".bin", ".gba", ".srl"):
					self.FlashROM(fn)
				elif fn_split[1] == ".sav":
					self.RestoreRAM(fn)
		else:
			e.ignore()

	def run(self):
		self.layout.update()
		self.layout.activate()
		screen = QGuiApplication.screens()[0]
		screenGeometry = screen.geometry()
		x = (screenGeometry.width() - self.width()) / 2
		y = (screenGeometry.height() - self.height()) / 2
		self.move(x, y)
		self.setAcceptDrops(True)
		self.show()
		qt_app.exec_()

qt_app = QApplication(sys.argv)
qt_app.setOrganizationName("Lesserkuma")
qt_app.setApplicationName("FlashGBX")
app = FlashGBX(sys.argv)
app.run()
