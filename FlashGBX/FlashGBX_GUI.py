# -*- coding: utf-8 -*-
# ＵＴＦ－８
import sys, os, time, datetime, re, json, platform, subprocess, argparse, requests, webbrowser, pkg_resources
from PySide2 import QtCore, QtWidgets, QtGui
from .RomFileDMG import RomFileDMG
from .RomFileAGB import RomFileAGB
from .PocketCamera import PocketCamera
from .PocketCameraWindow import PocketCameraWindow
from .Util import APPNAME, VERSION, VERSION_PEP440, ANSI
from . import Util
from . import hw_GBxCartRW
hw_devices = [hw_GBxCartRW]

class FlashGBX_GUI(QtWidgets.QWidget):
	CONN = None
	SETTINGS = None
	DEVICES = {}
	FLASHCARTS = { "DMG":{}, "AGB":{} }
	CONFIG_PATH = ""
	TBPROG = None # Windows 7+ Taskbar Progress Bar
	PROGRESS = None
	
	def __init__(self, args):
		QtWidgets.QWidget.__init__(self)
		app_path = args['app_path']
		self.CONFIG_PATH = args['config_path']
		self.SETTINGS = Util.IniSettings(ini_file=args["config_path"] + "/settings.ini")
		self.FLASHCARTS = args["flashcarts"]
		self.PROGRESS = Util.Progress(self.UpdateProgress)
		
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.setWindowIcon(QtGui.QIcon(app_path + "/res/icon.ico"))
		self.setWindowTitle("{:s} {:s}".format(APPNAME, VERSION))
		self.setWindowFlags(self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint)
		
		# Create the QtWidgets.QVBoxLayout that lays out the whole form
		self.layout = QtWidgets.QGridLayout()
		self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		self.layout_left = QtWidgets.QVBoxLayout()
		self.layout_right = QtWidgets.QVBoxLayout()
		self.layout.setContentsMargins(-1, 8, -1, 8)

		# Cartridge Information GroupBox
		self.grpDMGCartridgeInfo = self.GuiCreateGroupBoxDMGCartInfo()
		self.grpAGBCartridgeInfo = self.GuiCreateGroupBoxAGBCartInfo()
		self.grpAGBCartridgeInfo.setVisible(False)
		self.layout_left.addWidget(self.grpDMGCartridgeInfo)
		self.layout_left.addWidget(self.grpAGBCartridgeInfo)

		# Actions
		self.grpActions = QtWidgets.QGroupBox("Options")
		self.grpActionsLayout = QtWidgets.QVBoxLayout()
		self.grpActionsLayout.setContentsMargins(-1, 3, -1, -1)
		
		rowActionsMode = QtWidgets.QHBoxLayout()
		self.lblMode = QtWidgets.QLabel("Mode: ")
		rowActionsMode.addWidget(self.lblMode)
		self.optDMG = QtWidgets.QRadioButton("&Game Boy")
		self.connect(self.optDMG, QtCore.SIGNAL("clicked()"), self.SetMode)
		self.optAGB = QtWidgets.QRadioButton("Game Boy &Advance")
		self.connect(self.optAGB, QtCore.SIGNAL("clicked()"), self.SetMode)
		rowActionsMode.addWidget(self.optDMG)
		rowActionsMode.addWidget(self.optAGB)
		
		rowActionsGeneral1 = QtWidgets.QHBoxLayout()
		self.btnHeaderRefresh = QtWidgets.QPushButton("Read &Information")
		self.btnHeaderRefresh.setStyleSheet("min-height: 17px;")
		self.connect(self.btnHeaderRefresh, QtCore.SIGNAL("clicked()"), self.ReadCartridge)
		rowActionsGeneral1.addWidget(self.btnHeaderRefresh)

		rowActionsGeneral2 = QtWidgets.QHBoxLayout()
		self.btnBackupROM = QtWidgets.QPushButton("Backup &ROM")
		self.btnBackupROM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnBackupROM, QtCore.SIGNAL("clicked()"), self.BackupROM)
		rowActionsGeneral2.addWidget(self.btnBackupROM)
		self.btnBackupRAM = QtWidgets.QPushButton("Backup &Save Data")
		self.btnBackupRAM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnBackupRAM, QtCore.SIGNAL("clicked()"), self.BackupRAM)
		rowActionsGeneral2.addWidget(self.btnBackupRAM)
		
		self.cmbDMGCartridgeTypeResult.currentIndexChanged.connect(self.CartridgeTypeChanged)
		
		rowActionsGeneral3 = QtWidgets.QHBoxLayout()
		self.btnFlashROM = QtWidgets.QPushButton("&Flash ROM")
		self.btnFlashROM.setStyleSheet("min-height: 17px;")
		self.connect(self.btnFlashROM, QtCore.SIGNAL("clicked()"), self.FlashROM)
		rowActionsGeneral3.addWidget(self.btnFlashROM)
		self.btnRestoreRAM = QtWidgets.QPushButton("Writ&e Save Data")
		self.mnuRestoreRAM = QtWidgets.QMenu()
		self.mnuRestoreRAM.addAction("&Restore from save data file", self.WriteRAM)
		self.mnuRestoreRAM.addAction("&Erase cartridge save data", lambda: self.WriteRAM(erase=True))
		self.btnRestoreRAM.setMenu(self.mnuRestoreRAM)
		self.btnRestoreRAM.setStyleSheet("min-height: 17px;")
		rowActionsGeneral3.addWidget(self.btnRestoreRAM)

		self.grpActionsLayout.setSpacing(4)
		self.grpActionsLayout.addLayout(rowActionsMode)
		self.grpActionsLayout.addLayout(rowActionsGeneral1)
		self.grpActionsLayout.addLayout(rowActionsGeneral2)
		self.grpActionsLayout.addLayout(rowActionsGeneral3)
		self.grpActions.setLayout(self.grpActionsLayout)

		self.layout_right.addWidget(self.grpActions)

		# Transfer Status
		self.grpStatus = QtWidgets.QGroupBox("Transfer Status")
		grpStatusLayout = QtWidgets.QVBoxLayout()
		grpStatusLayout.setContentsMargins(-1, 3, -1, -1)

		rowStatus1a = QtWidgets.QHBoxLayout()
		self.lblStatus1a = QtWidgets.QLabel("Data transferred:")
		rowStatus1a.addWidget(self.lblStatus1a)
		self.lblStatus1aResult = QtWidgets.QLabel("–")
		rowStatus1a.addWidget(self.lblStatus1aResult)
		grpStatusLayout.addLayout(rowStatus1a)
		rowStatus2a = QtWidgets.QHBoxLayout()
		self.lblStatus2a = QtWidgets.QLabel("Transfer rate:")
		rowStatus2a.addWidget(self.lblStatus2a)
		self.lblStatus2aResult = QtWidgets.QLabel("–")
		rowStatus2a.addWidget(self.lblStatus2aResult)
		grpStatusLayout.addLayout(rowStatus2a)
		rowStatus3a = QtWidgets.QHBoxLayout()
		self.lblStatus3a = QtWidgets.QLabel("Time elapsed:")
		rowStatus3a.addWidget(self.lblStatus3a)
		self.lblStatus3aResult = QtWidgets.QLabel("–")
		rowStatus3a.addWidget(self.lblStatus3aResult)
		grpStatusLayout.addLayout(rowStatus3a)
		rowStatus4a = QtWidgets.QHBoxLayout()
		self.lblStatus4a = QtWidgets.QLabel("Ready.")
		rowStatus4a.addWidget(self.lblStatus4a)
		self.lblStatus4aResult = QtWidgets.QLabel("")
		rowStatus4a.addWidget(self.lblStatus4aResult)
		grpStatusLayout.addLayout(rowStatus4a)

		rowStatus2 = QtWidgets.QHBoxLayout()
		self.prgStatus = QtWidgets.QProgressBar()
		self.SetProgressBars(min=0, max=1, value=0)
		rowStatus2.addWidget(self.prgStatus)
		btnText = "Stop"
		self.btnCancel = QtWidgets.QPushButton(btnText)
		self.btnCancel.setEnabled(False)
		btnWidth = self.btnCancel.fontMetrics().boundingRect(btnText).width() + 15
		if platform.system() == "Darwin": btnWidth += 12
		self.btnCancel.setMaximumWidth(btnWidth)
		self.connect(self.btnCancel, QtCore.SIGNAL("clicked()"), self.AbortOperation)
		rowStatus2.addWidget(self.btnCancel)

		grpStatusLayout.addLayout(rowStatus2)
		self.grpStatus.setLayout(grpStatusLayout)

		self.layout_right.addWidget(self.grpStatus)

		self.layout.addLayout(self.layout_left, 0, 0)
		self.layout.addLayout(self.layout_right, 0, 1)
		
		# List devices
		self.layout_devices = QtWidgets.QHBoxLayout()
		self.lblDevice = QtWidgets.QLabel()
		self.cmbDevice = QtWidgets.QComboBox()
		self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }")
		self.layout_devices.addWidget(self.lblDevice)
		self.layout_devices.addWidget(self.cmbDevice)
		self.layout_devices.addStretch()
		
		self.btnCameraViewer = QtWidgets.QPushButton("&GB Camera")
		self.connect(self.btnCameraViewer, QtCore.SIGNAL("clicked()"), self.ShowPocketCameraWindow)
		
		btnText = "C&onfig"
		self.btnConfig = QtWidgets.QPushButton(btnText)
		btnWidth = self.btnConfig.fontMetrics().boundingRect(btnText).width() + 24
		if platform.system() == "Darwin": btnWidth += 12
		self.btnConfig.setMaximumWidth(btnWidth)
		self.mnuConfig = QtWidgets.QMenu()
		self.mnuConfig.addAction("Check for &updates at application startup", lambda: [ self.SETTINGS.setValue("UpdateCheck", str(self.mnuConfig.actions()[0].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")), self.UpdateCheck() ])
		self.mnuConfig.addAction("&Append date && time to filename of save data backups", lambda: self.SETTINGS.setValue("SaveFileNameAddDateTime", str(self.mnuConfig.actions()[1].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Prefer full &chip erase over sector erase when both available", lambda: self.SETTINGS.setValue("PreferChipErase", str(self.mnuConfig.actions()[2].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("&Verify flash after writing", lambda: self.SETTINGS.setValue("VerifyFlash", str(self.mnuConfig.actions()[3].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Use &fast read mode (experimental)", lambda: self.SETTINGS.setValue("FastReadMode", str(self.mnuConfig.actions()[4].isChecked()).lower().replace("true", "enabled").replace("false", "disabled"))) # GBxCart RW
		self.mnuConfig.addSeparator()
		self.mnuConfig.addAction("Show &configuration directory", self.OpenConfigDir)
		self.mnuConfig.actions()[0].setCheckable(True)
		self.mnuConfig.actions()[1].setCheckable(True)
		self.mnuConfig.actions()[2].setCheckable(True)
		self.mnuConfig.actions()[3].setCheckable(True)
		self.mnuConfig.actions()[4].setCheckable(True) # GBxCart RW
		self.mnuConfig.actions()[0].setChecked(self.SETTINGS.value("UpdateCheck") == "enabled")
		self.mnuConfig.actions()[1].setChecked(self.SETTINGS.value("SaveFileNameAddDateTime", default="disabled") == "enabled")
		self.mnuConfig.actions()[2].setChecked(self.SETTINGS.value("PreferChipErase", default="disabled") == "enabled")
		self.mnuConfig.actions()[3].setChecked(self.SETTINGS.value("VerifyFlash", default="enabled") == "enabled")
		self.mnuConfig.actions()[4].setChecked(self.SETTINGS.value("FastReadMode", default="disabled") == "enabled") # GBxCart RW
		self.btnConfig.setMenu(self.mnuConfig)
		
		self.btnConnect = QtWidgets.QPushButton("&Connect")
		self.connect(self.btnConnect, QtCore.SIGNAL("clicked()"), self.ConnectDevice)
		self.layout_devices.addWidget(self.btnCameraViewer)
		self.layout_devices.addWidget(self.btnConfig)
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
		self.btnConnect.setEnabled(False)
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		
		# Set the VBox layout as the window's main layout
		self.setLayout(self.layout)
		
		# Show app window first, then do update check
		qt_app.processEvents()
		
		config_ret = args["config_ret"]
		for i in range(0, len(config_ret)):
			if config_ret[i][0] == 0:
				print(config_ret[i][1])
			elif config_ret[i][0] == 1:
				QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), config_ret[i][1], QtWidgets.QMessageBox.Ok)
			elif config_ret[i][0] == 2:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), config_ret[i][1], QtWidgets.QMessageBox.Ok)
			elif config_ret[i][0] == 3:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), config_ret[i][1], QtWidgets.QMessageBox.Ok)

		QtCore.QTimer.singleShot(1, lambda: [ self.UpdateCheck(), self.FindDevices() ])
	
	def GuiCreateGroupBoxDMGCartInfo(self):
		self.grpDMGCartridgeInfo = QtWidgets.QGroupBox("Game Boy Cartridge Information")
		self.grpDMGCartridgeInfo.setMinimumWidth(280)
		group_layout = QtWidgets.QVBoxLayout()
		group_layout.setContentsMargins(-1, 5, -1, -1)

		rowHeaderTitle = QtWidgets.QHBoxLayout()
		lblHeaderTitle = QtWidgets.QLabel("Game Title/Code:")
		lblHeaderTitle.setContentsMargins(0, 1, 0, 1)
		rowHeaderTitle.addWidget(lblHeaderTitle)
		self.lblHeaderTitleResult = QtWidgets.QLabel("")
		rowHeaderTitle.addWidget(self.lblHeaderTitleResult)
		group_layout.addLayout(rowHeaderTitle)

		rowHeaderSGB = QtWidgets.QHBoxLayout()
		lblHeaderSGB = QtWidgets.QLabel("Super Game Boy:")
		lblHeaderSGB.setContentsMargins(0, 1, 0, 1)
		rowHeaderSGB.addWidget(lblHeaderSGB)
		self.lblHeaderSGBResult = QtWidgets.QLabel("")
		rowHeaderSGB.addWidget(self.lblHeaderSGBResult)
		group_layout.addLayout(rowHeaderSGB)

		rowHeaderCGB = QtWidgets.QHBoxLayout()
		lblHeaderCGB = QtWidgets.QLabel("Game Boy Color:")
		lblHeaderCGB.setContentsMargins(0, 1, 0, 1)
		rowHeaderCGB.addWidget(lblHeaderCGB)
		self.lblHeaderCGBResult = QtWidgets.QLabel("")
		rowHeaderCGB.addWidget(self.lblHeaderCGBResult)
		group_layout.addLayout(rowHeaderCGB)

		rowHeaderLogoValid = QtWidgets.QHBoxLayout()
		lblHeaderLogoValid = QtWidgets.QLabel("Nintendo Logo:")
		lblHeaderLogoValid.setContentsMargins(0, 1, 0, 1)
		rowHeaderLogoValid.addWidget(lblHeaderLogoValid)
		self.lblHeaderLogoValidResult = QtWidgets.QLabel("")
		rowHeaderLogoValid.addWidget(self.lblHeaderLogoValidResult)
		group_layout.addLayout(rowHeaderLogoValid)

		rowHeaderChecksum = QtWidgets.QHBoxLayout()
		lblHeaderChecksum = QtWidgets.QLabel("Header Checksum:")
		lblHeaderChecksum.setContentsMargins(0, 1, 0, 1)
		rowHeaderChecksum.addWidget(lblHeaderChecksum)
		self.lblHeaderChecksumResult = QtWidgets.QLabel("")
		rowHeaderChecksum.addWidget(self.lblHeaderChecksumResult)
		group_layout.addLayout(rowHeaderChecksum)

		rowHeaderROMChecksum = QtWidgets.QHBoxLayout()
		lblHeaderROMChecksum = QtWidgets.QLabel("ROM Checksum:")
		lblHeaderROMChecksum.setContentsMargins(0, 1, 0, 1)
		rowHeaderROMChecksum.addWidget(lblHeaderROMChecksum)
		self.lblHeaderROMChecksumResult = QtWidgets.QLabel("")
		rowHeaderROMChecksum.addWidget(self.lblHeaderROMChecksumResult)
		group_layout.addLayout(rowHeaderROMChecksum)

		rowHeaderROMSize = QtWidgets.QHBoxLayout()
		lblHeaderROMSize = QtWidgets.QLabel("ROM Size:")
		rowHeaderROMSize.addWidget(lblHeaderROMSize)
		self.cmbHeaderROMSizeResult = QtWidgets.QComboBox()
		self.cmbHeaderROMSizeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbHeaderROMSizeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		rowHeaderROMSize.addWidget(self.cmbHeaderROMSizeResult)
		group_layout.addLayout(rowHeaderROMSize)

		rowHeaderRAMSize = QtWidgets.QHBoxLayout()
		lblHeaderRAMSize = QtWidgets.QLabel("Save Type:")
		rowHeaderRAMSize.addWidget(lblHeaderRAMSize)
		self.cmbHeaderRAMSizeResult = QtWidgets.QComboBox()
		self.cmbHeaderRAMSizeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbHeaderRAMSizeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		rowHeaderRAMSize.addWidget(self.cmbHeaderRAMSizeResult)
		group_layout.addLayout(rowHeaderRAMSize)

		rowHeaderFeatures = QtWidgets.QHBoxLayout()
		lblHeaderFeatures = QtWidgets.QLabel("Mapper Type:")
		rowHeaderFeatures.addWidget(lblHeaderFeatures)
		self.cmbHeaderFeaturesResult = QtWidgets.QComboBox()
		self.cmbHeaderFeaturesResult.setStyleSheet("combobox-popup: 0;")
		self.cmbHeaderFeaturesResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		rowHeaderFeatures.addWidget(self.cmbHeaderFeaturesResult)
		group_layout.addLayout(rowHeaderFeatures)

		rowCartridgeType = QtWidgets.QHBoxLayout()
		lblCartridgeType = QtWidgets.QLabel("Cart:")
		rowCartridgeType.addWidget(lblCartridgeType)
		self.cmbDMGCartridgeTypeResult = QtWidgets.QComboBox()
		self.cmbDMGCartridgeTypeResult.setStyleSheet("max-width: 260px;")
		self.cmbDMGCartridgeTypeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbDMGCartridgeTypeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		rowCartridgeType.addWidget(self.cmbDMGCartridgeTypeResult)
		group_layout.addLayout(rowCartridgeType)

		self.grpDMGCartridgeInfo.setLayout(group_layout)
		
		return self.grpDMGCartridgeInfo
	
	def GuiCreateGroupBoxAGBCartInfo(self):
		self.grpAGBCartridgeInfo = QtWidgets.QGroupBox("Game Boy Advance Cartridge Information")
		self.grpAGBCartridgeInfo.setMinimumWidth(280)
		group_layout = QtWidgets.QVBoxLayout()
		group_layout.setContentsMargins(-1, 5, -1, -1)

		rowAGBHeaderTitle = QtWidgets.QHBoxLayout()
		lblAGBHeaderTitle = QtWidgets.QLabel("Game Title:")
		lblAGBHeaderTitle.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderTitle.addWidget(lblAGBHeaderTitle)
		self.lblAGBHeaderTitleResult = QtWidgets.QLabel("")
		rowAGBHeaderTitle.addWidget(self.lblAGBHeaderTitleResult)
		group_layout.addLayout(rowAGBHeaderTitle)

		rowAGBHeaderCode = QtWidgets.QHBoxLayout()
		lblAGBHeaderCode = QtWidgets.QLabel("Game Code:")
		lblAGBHeaderCode.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderCode.addWidget(lblAGBHeaderCode)
		self.lblAGBHeaderCodeResult = QtWidgets.QLabel("")
		rowAGBHeaderCode.addWidget(self.lblAGBHeaderCodeResult)
		group_layout.addLayout(rowAGBHeaderCode)

		rowAGBHeaderVersion = QtWidgets.QHBoxLayout()
		lblAGBHeaderVersion = QtWidgets.QLabel("Revision:")
		lblAGBHeaderVersion.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderVersion.addWidget(lblAGBHeaderVersion)
		self.lblAGBHeaderVersionResult = QtWidgets.QLabel("")
		rowAGBHeaderVersion.addWidget(self.lblAGBHeaderVersionResult)
		group_layout.addLayout(rowAGBHeaderVersion)

		rowAGBHeaderLogoValid = QtWidgets.QHBoxLayout()
		lblAGBHeaderLogoValid = QtWidgets.QLabel("Nintendo Logo:")
		lblAGBHeaderLogoValid.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderLogoValid.addWidget(lblAGBHeaderLogoValid)
		self.lblAGBHeaderLogoValidResult = QtWidgets.QLabel("")
		rowAGBHeaderLogoValid.addWidget(self.lblAGBHeaderLogoValidResult)
		group_layout.addLayout(rowAGBHeaderLogoValid)

		rowAGBHeader96h = QtWidgets.QHBoxLayout()
		lblAGBHeader96h = QtWidgets.QLabel("Cartridge Identifier:")
		lblAGBHeader96h.setContentsMargins(0, 1, 0, 1)
		rowAGBHeader96h.addWidget(lblAGBHeader96h)
		self.lblAGBHeader96hResult = QtWidgets.QLabel("")
		rowAGBHeader96h.addWidget(self.lblAGBHeader96hResult)
		group_layout.addLayout(rowAGBHeader96h)

		rowAGBHeaderChecksum = QtWidgets.QHBoxLayout()
		lblAGBHeaderChecksum = QtWidgets.QLabel("Header Checksum:")
		lblAGBHeaderChecksum.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderChecksum.addWidget(lblAGBHeaderChecksum)
		self.lblAGBHeaderChecksumResult = QtWidgets.QLabel("")
		rowAGBHeaderChecksum.addWidget(self.lblAGBHeaderChecksumResult)
		group_layout.addLayout(rowAGBHeaderChecksum)

		rowAGBHeaderROMChecksum = QtWidgets.QHBoxLayout()
		lblAGBHeaderROMChecksum = QtWidgets.QLabel("ROM Checksum:")
		lblAGBHeaderROMChecksum.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderROMChecksum.addWidget(lblAGBHeaderROMChecksum)
		self.lblAGBHeaderROMChecksumResult = QtWidgets.QLabel("")
		rowAGBHeaderROMChecksum.addWidget(self.lblAGBHeaderROMChecksumResult)
		group_layout.addLayout(rowAGBHeaderROMChecksum)
		
		rowAGBHeaderROMSize = QtWidgets.QHBoxLayout()
		lblAGBHeaderROMSize = QtWidgets.QLabel("ROM Size:")
		rowAGBHeaderROMSize.addWidget(lblAGBHeaderROMSize)
		self.cmbAGBHeaderROMSizeResult = QtWidgets.QComboBox()
		self.cmbAGBHeaderROMSizeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbAGBHeaderROMSizeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self.cmbAGBHeaderROMSizeResult.addItems(Util.AGB_Header_ROM_Sizes)
		self.cmbAGBHeaderROMSizeResult.setCurrentIndex(self.cmbAGBHeaderROMSizeResult.count() - 1)
		rowAGBHeaderROMSize.addWidget(self.cmbAGBHeaderROMSizeResult)
		group_layout.addLayout(rowAGBHeaderROMSize)
		
		rowAGBHeaderRAMSize = QtWidgets.QHBoxLayout()
		lblAGBHeaderRAMSize = QtWidgets.QLabel("Save Type:")
		rowAGBHeaderRAMSize.addWidget(lblAGBHeaderRAMSize)
		self.cmbAGBSaveTypeResult = QtWidgets.QComboBox()
		self.cmbAGBSaveTypeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbAGBSaveTypeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self.cmbAGBSaveTypeResult.addItems(Util.AGB_Header_Save_Types)
		self.cmbAGBSaveTypeResult.setCurrentIndex(self.cmbAGBSaveTypeResult.count() - 1)
		rowAGBHeaderRAMSize.addWidget(self.cmbAGBSaveTypeResult)
		group_layout.addLayout(rowAGBHeaderRAMSize)
		
		rowAGBCartridgeType = QtWidgets.QHBoxLayout()
		lblAGBCartridgeType = QtWidgets.QLabel("Cart:")
		rowAGBCartridgeType.addWidget(lblAGBCartridgeType)
		self.cmbAGBCartridgeTypeResult = QtWidgets.QComboBox()
		self.cmbAGBCartridgeTypeResult.setStyleSheet("max-width: 260px;")
		self.cmbAGBCartridgeTypeResult.setStyleSheet("combobox-popup: 0;")
		self.cmbAGBCartridgeTypeResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self.cmbAGBCartridgeTypeResult.currentIndexChanged.connect(self.CartridgeTypeChanged)
		rowAGBCartridgeType.addWidget(self.cmbAGBCartridgeTypeResult)
		group_layout.addLayout(rowAGBCartridgeType)

		self.grpAGBCartridgeInfo.setLayout(group_layout)
		return self.grpAGBCartridgeInfo
	
	def UpdateCheck(self):
		update_check = self.SETTINGS.value("UpdateCheck")
		if update_check is None:
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "Welcome to {:s} {:s} by Lesserkuma!\nWould you like to automatically check for new versions at application startup?".format(APPNAME, VERSION), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
			if answer == QtWidgets.QMessageBox.Yes:
				self.SETTINGS.setValue("UpdateCheck", "enabled")
				self.mnuConfig.actions()[0].setChecked(True)
				update_check = "enabled"
			else:
				self.SETTINGS.setValue("UpdateCheck", "disabled")
		
		if update_check and update_check.lower() == "enabled":
			if ".dev" in VERSION_PEP440:
				type = "test "
				url = "https://test.pypi.org/pypi/FlashGBX/json"
				site = "https://test.pypi.org/project/FlashGBX/"
			else:
				type = ""
				url = "https://pypi.org/pypi/FlashGBX/json"
				site = "https://github.com/lesserkuma/FlashGBX"
			try:
				ret = requests.get(url, allow_redirects=True, timeout=1.5)
			except requests.exceptions.ConnectTimeout as e:
				print("ERROR: Update check failed due to a connection timeout. Please check your internet connection.", e, sep="\n")
				ret = False
			except requests.exceptions.ConnectionError as e:
				print("ERROR: Update check failed due to a connection error. Please check your network connection.", e, sep="\n")
				ret = False
			except Exception as e:
				print("ERROR: An unexpected error occured while querying the latest version information from PyPI.", e, sep="\n")
				ret = False
			
			if ret is not False and ret.status_code == 200:
				ret = ret.content
				try:
					ret = json.loads(ret)
					if 'info' in ret and 'version' in ret['info']:
						if pkg_resources.parse_version(ret['info']['version']) == pkg_resources.parse_version(VERSION_PEP440):
							print("You are using the latest {:s}version of {:s}.".format(type, APPNAME))
						elif pkg_resources.parse_version(ret['info']['version']) > pkg_resources.parse_version(VERSION_PEP440):
							msg_text = "A new {:s}version of {:s} has been released!\nVersion {:s} is now available.".format(type, APPNAME, ret['info']['version'])
							print(msg_text)
							msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} Update Check".format(APPNAME), text=msg_text)
							button_open = msgbox.addButton("  Open &website  ", QtWidgets.QMessageBox.ActionRole)
							button_cancel = msgbox.addButton("&OK", QtWidgets.QMessageBox.RejectRole)
							msgbox.setDefaultButton(button_open)
							msgbox.setEscapeButton(button_cancel)
							answer = msgbox.exec()
							if msgbox.clickedButton() == button_open:
								webbrowser.open(site)
						else:
							print("This version of {:s} ({:s}) seems to be newer than the latest {:s}release ({:s}). Please check for updates manually.".format(APPNAME, VERSION_PEP440, type, ret['info']['version']))
					else:
						print("ERROR: Update check failed due to missing version information in JSON data from PyPI.")
				except json.decoder.JSONDecodeError:
					print("ERROR: Update check failed due to malformed JSON data from PyPI.")
				except Exception as e:
					print("ERROR: An unexpected error occured while querying the latest version information from PyPI.", e, sep="\n")
			elif ret is not False:
				print("ERROR: Failed to check for updates (HTTP status {:d}).".format(ret.status_code))
	
	def DisconnectDevice(self):
		try:
			devname = self.CONN.GetFullName()
			self.CONN.Close()
			print("Disconnected from {:s}".format(devname))
		except:
			pass
		
		self.CONN = None
		self.optAGB.setEnabled(False)
		self.optDMG.setEnabled(False)
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.btnCancel.setEnabled(False)
		self.btnHeaderRefresh.setEnabled(False)
		self.btnBackupROM.setEnabled(False)
		self.btnFlashROM.setEnabled(False)
		self.btnBackupRAM.setEnabled(False)
		self.btnRestoreRAM.setEnabled(False)
		self.btnConnect.setText("&Connect")
		self.lblDevice.setText("Disconnected.")
	
	def OpenConfigDir(self):
		path = 'file://{0:s}'.format(self.CONFIG_PATH)
		try:
			if platform.system() == "Windows":
				os.startfile(path)
			elif platform.system() == "Darwin":
				subprocess.Popen(["open", path])
			else:
				subprocess.Popen(["xdg-open", path])
		except:
			QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Your configuration files are stored in\n" + path, QtWidgets.QMessageBox.Ok)
	
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
				self.FindDevices(True)
				return
			
			dev = self.DEVICES[index]
			ret = dev.Initialize(self.FLASHCARTS)
			msg = ""
			
			if ret is False:
				self.CONN = None
				if self.cmbDevice.count() == 0: self.lblDevice.setText("No connection.")
				return False
			
			elif isinstance(ret, list):
				for i in range(0, len(ret)):
					status = ret[i][0]
					text = ret[i][1]
					if status == 0:
						msg += text + "\n"
					elif status == 1:
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=text, standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in text: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
					elif status == 2:
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=text, standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in text: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
					elif status == 3:
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=text, standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in text: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
						self.CONN = None
						return False
			
			if dev.IsConnected():
				qt_app.processEvents()
				self.CONN = dev
				self.optDMG.setAutoExclusive(False)
				self.optAGB.setAutoExclusive(False)
				if "DMG" in self.CONN.GetSupprtedModes():
					self.optDMG.setEnabled(True)
					self.optDMG.setChecked(False)
				if "AGB" in self.CONN.GetSupprtedModes():
					self.optAGB.setEnabled(True)
					self.optAGB.setChecked(False)
				self.optAGB.setAutoExclusive(True)
				self.optDMG.setAutoExclusive(True)
				self.btnConnect.setText("&Disconnect")
				self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }")
				self.lblDevice.setText(dev.GetFullName())
				print("\nConnected to " + dev.GetFullName())
				self.grpDMGCartridgeInfo.setEnabled(True)
				self.grpAGBCartridgeInfo.setEnabled(True)
				self.grpActions.setEnabled(True)
				self.btnCancel.setEnabled(False)
				self.SetProgressBars(min=0, max=1, value=0)
				
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
				
				print(msg, end="")
				return True
			return False
	
	def FindDevices(self, connectToFirst=False):
		if self.CONN is not None:
			self.DisconnectDevice()
		self.lblDevice.setText("Searching...")
		self.btnConnect.setEnabled(False)
		qt_app.processEvents()
		time.sleep(0.05)
		
		global hw_devices
		for hw_device in hw_devices:
			dev = hw_device.GbxDevice()
			ret = dev.Initialize(self.FLASHCARTS)
			if ret is False:
				self.CONN = None
			elif isinstance(ret, list):
				for i in range(0, len(ret)):
					status = ret[i][0]
					msg = ret[i][1]
					if status == 3:
						QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Ok)
						self.CONN = None
			
			if dev.IsConnected():
				self.DEVICES[dev.GetFullName()] = dev
				dev.Close()
		
		self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }")
		
		if len(self.DEVICES) == 0:
			self.lblDevice.setText("No devices found.")
			self.lblDevice.setStyleSheet("")
			self.cmbDevice.clear()
			self.btnConnect.setEnabled(False)
		elif len(self.DEVICES) == 1 or (connectToFirst and len(self.DEVICES) > 1):
			self.lblDevice.setText(list(self.DEVICES.keys())[0])
			self.lblDevice.setStyleSheet("")
			self.ConnectDevice()
			self.cmbDevice.clear()
			self.btnConnect.setEnabled(True)
		else:
			self.lblDevice.setText("Select device:")
			self.cmbDevice.clear()
			self.cmbDevice.addItems(self.DEVICES.keys())
			self.cmbDevice.setCurrentIndex(0)
			self.cmbDevice.setStyleSheet("")
			self.btnConnect.setEnabled(True)
		
		self.btnConnect.setEnabled(True)
		
		if len(self.DEVICES) == 0: return False

		# debug
		#self.CONN.SetMode("DMG")
		#self.CONN.ReadInfo()
		#self.CONN.BackupROM(fncSetProgress=self.PROGRESS.SetProgress, path="T:/GBX/TEST/b.gb", mbc=0x19, rom_banks=64, agb_rom_size=1024*1024, fast_read_mode=True, cart_type=21)
		return True

	def AbortOperation(self):
		self.CONN.CANCEL = True

	def FinishOperation(self):
		if self.lblStatus2aResult.text() == "Pending...": self.lblStatus2aResult.setText("–")
		self.lblStatus4aResult.setText("")
		self.grpDMGCartridgeInfo.setEnabled(True)
		self.grpAGBCartridgeInfo.setEnabled(True)
		self.grpActions.setEnabled(True)
		self.btnCancel.setEnabled(False)
		
		dontShowAgain = str(self.SETTINGS.value("SkipFinishMessage", default="disabled")).lower() == "enabled"
		
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="Operation complete!", standardButtons=QtWidgets.QMessageBox.Ok)
		cb = QtWidgets.QCheckBox("Don’t show this message again.", checked=False)
		msgbox.setCheckBox(cb)
		
		if self.CONN.INFO["last_action"] == 4: # Flash ROM
			self.CONN.INFO["last_action"] = 0
			self.ReadCartridge(resetStatus=False)
			self.lblStatus4a.setText("Done!")
			if "verified" in self.PROGRESS.PROGRESS and self.PROGRESS.PROGRESS["verified"] == True:
				msgbox.setText("The ROM was flashed and verified successfully!")
			else:
				msgbox.setText("ROM flashing complete!")
			if not dontShowAgain:
				msgbox.exec()
				dontShowAgain = cb.isChecked()

		elif self.CONN.INFO["last_action"] == 1: # Backup ROM
			self.CONN.INFO["last_action"] = 0
			
			if self.CONN.GetMode() == "DMG":
				if self.CONN.INFO["rom_checksum"] == self.CONN.INFO["rom_checksum_calc"]:
					self.lblHeaderROMChecksumResult.setText("Valid (0x{:04X})".format(self.CONN.INFO["rom_checksum"]))
					self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }")
					self.lblStatus4a.setText("Done!")
					msgbox.setText("The ROM backup is complete and the checksum was verified successfully!")
					if not dontShowAgain:
						msgbox.exec()
						dontShowAgain = cb.isChecked()
				elif "DMG-MMSA-JPN" in self.cmbDMGCartridgeTypeResult.currentText():
					self.lblHeaderROMChecksumResult.setText("0x{:04X}".format(self.CONN.INFO["rom_checksum_calc"]))
					self.lblStatus4a.setText("Done!")
					msgbox.setText("The ROM backup is complete!")
					if not dontShowAgain:
						msgbox.exec()
						dontShowAgain = cb.isChecked()
				else:
					self.lblHeaderROMChecksumResult.setText("Invalid (0x{:04X}≠0x{:04X})".format(self.CONN.INFO["rom_checksum_calc"], self.CONN.INFO["rom_checksum"]))
					self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }")
					self.lblStatus4a.setText("Done.")
					QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The ROM was dumped, but the checksum is not correct. This may indicate a bad dump, however this can be normal for some reproduction cartridges, prototypes, patched games and intentional overdumps.", QtWidgets.QMessageBox.Ok)
			elif self.CONN.GetMode() == "AGB":
				if Util.AGB_Global_CRC32 == self.CONN.INFO["rom_checksum_calc"]:
					self.lblAGBHeaderROMChecksumResult.setText("Valid (0x{:06X})".format(Util.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }")
					self.lblStatus4a.setText("Done!")
					msgbox.setText("The ROM backup is complete and the checksum was verified successfully!")
					if not dontShowAgain:
						msgbox.exec()
						dontShowAgain = cb.isChecked()
				elif Util.AGB_Global_CRC32 == 0:
					self.lblAGBHeaderROMChecksumResult.setText("0x{:06X}".format(self.CONN.INFO["rom_checksum_calc"]))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
					self.lblStatus4a.setText("Done!")
					QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "The ROM backup is complete! As there is no known checksum for this ROM in the database, verification was skipped.", QtWidgets.QMessageBox.Ok)
				else:
					self.lblAGBHeaderROMChecksumResult.setText("Invalid (0x{:06X}≠0x{:06X})".format(self.CONN.INFO["rom_checksum_calc"], Util.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }")
					self.lblStatus4a.setText("Done.")
					QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The ROM backup is complete, but the checksum doesn’t match the known database entry. This may indicate a bad dump, however this can be normal for some reproduction cartridges, prototypes, patched games and intentional overdumps.", QtWidgets.QMessageBox.Ok)
		
		elif self.CONN.INFO["last_action"] == 2: # Backup RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0
			if self.CONN.INFO["transferred"] == 131072: # 128 KB
				with open(self.CONN.INFO["last_path"], "rb") as file: temp = file.read()
				if temp[0x1FFB1:0x1FFB6] == b'Magic':
					answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "Game Boy Camera save data was detected.\nWould you like to load it with the GB Camera Viewer now?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
					if answer == QtWidgets.QMessageBox.Yes:
						self.CAMWIN = None
						self.CAMWIN = PocketCameraWindow(self, icon=self.windowIcon(), file=self.CONN.INFO["last_path"])
						self.CAMWIN.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
						self.CAMWIN.setModal(True)
						self.CAMWIN.run()
						return
			
			msgbox.setText("The save data backup is complete!")
			if not dontShowAgain:
				msgbox.exec()
				dontShowAgain = cb.isChecked()
		
		elif self.CONN.INFO["last_action"] == 3: # Restore RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0
			if "save_erase" in self.CONN.INFO and self.CONN.INFO["save_erase"]:
				msg_text = "The save data was erased."
				del(self.CONN.INFO["save_erase"])
			else:
				msg_text = "The save data was restored!"
			msgbox.setText(msg_text)
			if not dontShowAgain:
				msgbox.exec()
				dontShowAgain = cb.isChecked()
		
		else:
			self.lblStatus4a.setText("Ready.")
			self.CONN.INFO["last_action"] = 0
		
		if dontShowAgain: self.SETTINGS.setValue("SkipFinishMessage", "enabled")
		self.SetProgressBars(min=0, max=1, value=1)
	
	def CartridgeTypeAutoDetect(self):
		cart_type = 0
		cart_text = ""
		
		if self.CONN.CheckROMStable() is False:
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "Unstable ROM reading detected. Please make sure you selected the correct mode and that the cartridge contacts are clean.", QtWidgets.QMessageBox.Ok)
			return 0
		
		if self.CONN.GetMode() in self.FLASHCARTS and len(self.FLASHCARTS[self.CONN.GetMode()]) == 0:
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "No flash cartridge type configuration files found. Try to restart the application with the “--reset” command line switch to reset the configuration.", QtWidgets.QMessageBox.Ok)
			return 0
		
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="Would you like " + APPNAME + " to try and auto-detect the flash cartridge type?\n(Genuine game cartridges can not be re-written.)", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
		msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
		cb = QtWidgets.QCheckBox("Limit voltage to 3.3V", checked=True)
		if self.CONN.GetMode() == "DMG":
			msgbox.setCheckBox(cb)
		answer = msgbox.exec()
		limitVoltage = cb.isChecked()
		if answer == QtWidgets.QMessageBox.No:
			return 0
		else:
			detected = self.CONN.AutoDetectFlash(limitVoltage)
			if len(detected) == 0:
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="No pre-configured flash cartridge type was detected. You can still try and manually select one from the list -- look for similar PCB text and/or flash chip markings. However, chances are this cartridge is currently not supported for flashing with " + APPNAME + ".\n\nWould you like " + APPNAME + " to run a flash chip query? This may help adding support for your flash cartridge in the future.", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
				msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
				if self.CONN.GetMode() == "DMG":
					msgbox.setCheckBox(cb)
				answer = msgbox.exec()
				if self.CONN.GetMode() == "DMG":
					limitVoltage = cb.isChecked()
				else:
					limitVoltage = False
				
				if answer == QtWidgets.QMessageBox.Yes:
					(flash_id, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage)
					if cfi_s == "":
						QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Flash chip query result: <pre>" + flash_id + "</pre>There was no Common Flash Interface (CFI) response from the cartridge. Please clean the cartridge contacts and make sure that the cartridge is seated correctly. If a flash chip exists on the cartridge PCB, it may be too old or require unique unlocking and handling.", QtWidgets.QMessageBox.Ok)
					else:
						QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Flash chip query result: <pre>" + flash_id + "</pre><pre>" + str(cfi_s) + "</pre>", QtWidgets.QMessageBox.Ok)
						with open(self.CONFIG_PATH + "/cfi.bin", "wb") as f: f.write(cfi['raw'])
				return 0
			else:
				cart_type = detected[0]
				size_undetected = False
				sectors_undetected = False
				if self.CONN.GetMode() == "DMG": cart_types = self.CONN.GetSupportedCartridgesDMG()
				elif self.CONN.GetMode() == "AGB": cart_types = self.CONN.GetSupportedCartridgesAGB()
				size = cart_types[1][detected[0]]["flash_size"]
				if "sector_size" in cart_types[1][detected[0]]:
					sectors = cart_types[1][detected[0]]["sector_size"]
				else:
					sectors = []
				
				for i in range(0, len(detected)):
					if size != cart_types[1][detected[i]]["flash_size"]:
						size_undetected = True
					if "sector_size_from_cfi" not in cart_types[1][detected[i]] and "sector_size" in cart_types[1][detected[i]] and sectors != cart_types[1][detected[i]]["sector_size"]:
						sectors_undetected = True
					cart_text += "- " + cart_types[0][detected[i]] + "\n"
				
				if size_undetected:
					(_, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage=limitVoltage, cart_type=cart_types[1][cart_type])
					if isinstance(cfi, dict) and 'device_size' in cfi:
						for i in range(0, len(detected)):
							if cfi['device_size'] == cart_types[1][detected[i]]["flash_size"]:
								cart_type = detected[i]
								size_undetected = False
								break
				
				if len(detected) == 1:
					msg_text = "The following flash cartridge type was detected:\n" + cart_text + "\nThe supported ROM size is up to {:d} MB.".format(int(cart_types[1][cart_type]['flash_size'] / 1024 / 1024))
				else:
					if size_undetected is True:
						msg_text = "Your cartridge responds to flash commands also used by:\n" + cart_text + "\nA compatible entry from this list will now be auto-selected, but you may need to manually adjust the ROM size selection.\n\nIMPORTANT: While these cartridges share the same electronic signature, their supported ROM size can differ. As the size can not be detected automatically at this time, please select it manually."
					else:
						msg_text = "Your cartridge responds to flash commands also used by:\n" + cart_text + "\nA compatible entry from this list will now be auto-selected.\nThe supported ROM size is up to {:d} MB.".format(int(cart_types[1][cart_type]['flash_size'] / 1024 / 1024))
				
				if sectors_undetected and "sector_size_from_cfi" not in cart_types[1][cart_type]:
					msg_text = msg_text + "\n\n{:s}IMPORTANT:{:s} While these share most of their attributes, some of them can not be automatically detected. If you encounter any errors while writing a ROM, please manually select the correct type based on the flash chip markings of your cartridge. Enabling the “Prefer chip erase mode” config option can also help.".format(ANSI.RED, ANSI.RESET)
				
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg_text)
				button_ok = msgbox.addButton("&OK", QtWidgets.QMessageBox.ActionRole)
				button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
				button_cfi = msgbox.addButton("  Run flash chip &query  ", QtWidgets.QMessageBox.ActionRole)
				msgbox.setDefaultButton(button_ok)
				msgbox.setEscapeButton(button_cancel)
				answer = msgbox.exec()
				if msgbox.clickedButton() == button_cfi:
					(flash_id, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage=limitVoltage, cart_type=cart_types[1][cart_type])
					if cfi_s == "":
						QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Flash chip query result: <pre>" + flash_id + "</pre>There was no Common Flash Interface (CFI) response from the cartridge. If a flash chip exists on the cartridge PCB, it may be too old or require unique unlocking and handling.", QtWidgets.QMessageBox.Ok)
					else:
						QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Flash chip query result: <pre>" + flash_id + "</pre><pre>" + str(cfi_s) + "</pre>", QtWidgets.QMessageBox.Ok)
						with open(self.CONFIG_PATH + "/cfi.bin", "wb") as f: f.write(cfi['raw'])
				elif msgbox.clickedButton() == button_cancel: return 0
		
		return cart_type
	
	def CartridgeTypeChanged(self, index):
		if self.CONN.GetMode() == "DMG":
			cart_types = self.CONN.GetSupportedCartridgesDMG()
			if cart_types[1][index] == "AUTODETECT": # special keyword
				cart_type = self.CartridgeTypeAutoDetect()
				if (cart_type == 1): cart_type = 0
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
			elif cart_types[1][index] == "RETAIL": # special keyword
				pass
			else:
				for i in range(0, len(Util.DMG_Header_ROM_Sizes_Flasher_Map)):
					if cart_types[1][index]["flash_size"] == (Util.DMG_Header_ROM_Sizes_Flasher_Map[i] * 0x4000):
						self.cmbHeaderROMSizeResult.setCurrentIndex(i)
			
			#if "DMG-MMSA-JPN" in cart_types[0][index]:
			#	self.cmbHeaderFeaturesResult.setCurrentIndex(list(Util.DMG_Header_Features.keys()).index(0x105))
		
		elif self.CONN.GetMode() == "AGB":
			cart_types = self.CONN.GetSupportedCartridgesAGB()
			if cart_types[1][index] == "AUTODETECT": # special keyword
				cart_type = self.CartridgeTypeAutoDetect()
				if (cart_type == 1): cart_type = 0
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)
			elif cart_types[1][index] == "RETAIL": # special keyword
				pass
			else:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(Util.AGB_Header_ROM_Sizes_Map.index(cart_types[1][index]["flash_size"]))
	
	def BackupROM(self):
		if not self.CheckDeviceAlive(): return
		mbc = (list(Util.DMG_Header_Features.items())[self.cmbHeaderFeaturesResult.currentIndex()])[0]
		rom_banks = Util.DMG_Header_ROM_Sizes_Flasher_Map[self.cmbHeaderROMSizeResult.currentIndex()]
		
		fast_read_mode = self.SETTINGS.value("FastReadMode", default="disabled")
		if fast_read_mode and fast_read_mode.lower() == "enabled":
			fast_read_mode = True
		else:
			fast_read_mode = False
		
		rom_size = 0
		cart_type = 0
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirRomDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "" or path == "(No ROM data detected)": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			if self.CONN.INFO["cgb"] == 0xC0 or self.CONN.INFO["cgb"] == 0x80:
				path = path + ".gbc"
			elif self.CONN.INFO["sgb"] == 0x03:
				path = path + ".sgb"
			else:
				path = path + ".gb"
			path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy ROM File (*.gb *.sgb *.gbc);;All Files (*.*)")[0]
			cart_type = self.cmbDMGCartridgeTypeResult.currentIndex()
		
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirRomAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii') + "_" + self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "_": path = self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "" or path == "(No ROM data detected)": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			rom_size = Util.AGB_Header_ROM_Sizes_Map[self.cmbAGBHeaderROMSizeResult.currentIndex()]
			path = path + ".gba"
			path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy Advance ROM File (*.gba *.srl);;All Files (*.*)")[0]
			cart_type = self.cmbAGBCartridgeTypeResult.currentIndex()
		
		if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
		self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
		
		self.CONN.BackupROM(fncSetProgress=self.PROGRESS.SetProgress, path=path, mbc=mbc, rom_banks=rom_banks, agb_rom_size=rom_size, fast_read_mode=fast_read_mode, cart_type=cart_type)

	def FlashROM(self, dpath=""):
		if not self.CheckDeviceAlive(): return
		path = ""
		if dpath != "":
			text = "The following ROM file will now be written to the flash cartridge:\n" + dpath
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), text, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Ok)
			if answer == QtWidgets.QMessageBox.Cancel: return
			path = dpath
		
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirRomDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			carts = self.CONN.GetSupportedCartridgesDMG()[1]
			cart_type = self.cmbDMGCartridgeTypeResult.currentIndex()
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirRomAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
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
		
		while path == "":
			if self.CONN.GetMode() == "DMG":
				path = QtWidgets.QFileDialog.getOpenFileName(self, "Flash ROM", last_dir, "Game Boy ROM File (*.gb *.gbc *.sgb *.bin);;All Files (*.*)")[0]
			elif self.CONN.GetMode() == "AGB":
				path = QtWidgets.QFileDialog.getOpenFileName(self, "Flash ROM", last_dir, "Game Boy Advance ROM File (*.gba *.srl);;All Files (*.*)")[0]
			
			if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		
		if os.path.getsize(path) > 0x2000000: # reject too large files to avoid exploding RAM
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "Files bigger than 32 MB are not supported.", QtWidgets.QMessageBox.Ok)
			return
		
		with open(path, "rb") as file: buffer = file.read()
		rom_size = len(buffer)
		if rom_size > carts[cart_type]['flash_size']:
			msg = "The selected flash cartridge type seems to support ROMs that are up to {:.2f} MB in size, but the file you selected is {:.2f} MB.".format(int(carts[cart_type]['flash_size'] / 1024 / 1024), os.path.getsize(path)/1024/1024)
			msg += " You can still give it a try, but it’s possible that it’s too large which may cause the flashing to fail."
			answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
			if answer == QtWidgets.QMessageBox.Cancel: return
		
		override_voltage = False
		if 'voltage_variants' in carts[cart_type] and carts[cart_type]['voltage'] == 3.3:
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The selected flash cartridge type usually flashes fine with 3.3V, however sometimes it may require 5V. Which mode should be used?")
			button_3_3v = msgbox.addButton("  Use &3.3V (safer)  ", QtWidgets.QMessageBox.ActionRole)
			button_5v = msgbox.addButton("Use &5V", QtWidgets.QMessageBox.ActionRole)
			button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
			msgbox.setDefaultButton(button_3_3v)
			msgbox.setEscapeButton(button_cancel)
			answer = msgbox.exec()
			if msgbox.clickedButton() == button_5v:
				override_voltage = 5
			elif msgbox.clickedButton() == button_cancel: return
		
		reverse_sectors = False
		if 'sector_reversal' in carts[cart_type]:
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The selected flash cartridge type is reported to sometimes have reversed sectors. If the cartridge is not working after flashing, try reversed sectors.")
			button_normal = msgbox.addButton("Normal", QtWidgets.QMessageBox.ActionRole)
			button_reversed = msgbox.addButton("Reversed", QtWidgets.QMessageBox.ActionRole)
			button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
			msgbox.setDefaultButton(button_normal)
			msgbox.setEscapeButton(button_cancel)
			answer = msgbox.exec()
			if msgbox.clickedButton() == button_reversed:
				reverse_sectors = True
			elif msgbox.clickedButton() == button_cancel: return
		
		prefer_chip_erase = False
		if 'chip_erase' in carts[cart_type]['commands'] and 'sector_erase' in carts[cart_type]['commands']:
			prefer_chip_erase = self.SETTINGS.value("PreferChipErase", default="disabled")
			if prefer_chip_erase and prefer_chip_erase.lower() == "enabled":
				prefer_chip_erase = True
			else:
				prefer_chip_erase = False

		fast_read_mode = self.SETTINGS.value("FastReadMode", default="disabled")
		if fast_read_mode and fast_read_mode.lower() == "enabled":
			fast_read_mode = True
		else:
			fast_read_mode = False
		
		verify_flash = self.SETTINGS.value("VerifyFlash", default="enabled")
		if verify_flash and verify_flash.lower() == "enabled":
			verify_flash = True
		else:
			verify_flash = False
		
		try:
			if self.CONN.GetMode() == "DMG":
				hdr = RomFileDMG(path).GetHeader()
			elif self.CONN.GetMode() == "AGB":
				hdr = RomFileAGB(path).GetHeader()
			if not hdr["logo_correct"]:
				answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Warning: The ROM file you selected will not boot on actual hardware due to invalid logo data.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
				if answer == QtWidgets.QMessageBox.Cancel: return
			if not hdr["header_checksum_correct"]:
				answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Warning: The ROM file you selected will not boot on actual hardware due to an invalid header checksum (expected 0x{:02X} instead of 0x{:02X}).".format(hdr["header_checksum_calc"], hdr["header_checksum"]), QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
				if answer == QtWidgets.QMessageBox.Cancel: return
		except:
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The file you selected could not be read.", QtWidgets.QMessageBox.Ok)
			return
		
		self.CONN.FlashROM(fncSetProgress=self.PROGRESS.SetProgress, path=path, cart_type=cart_type, override_voltage=override_voltage, prefer_chip_erase=prefer_chip_erase, reverse_sectors=reverse_sectors, fast_read_mode=fast_read_mode, verify_flash=verify_flash)
		buffer = None
	
	def BackupRAM(self):
		if not self.CheckDeviceAlive(): return
		rtc = False
		features = []
		
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "" or path == "(No ROM data detected)": path = "ROM"
			#mbc = Util.DMG_Header_Features_MBC[self.cmbHeaderFeaturesResult.currentIndex()]
			mbc = (list(Util.DMG_Header_Features.items())[self.cmbHeaderFeaturesResult.currentIndex()])[0]
			try:
				features = list(Util.DMG_Header_Features.keys())[self.cmbHeaderFeaturesResult.currentIndex()]
			except:
				pass
			save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Please select the correct save data size.", QtWidgets.QMessageBox.Ok)
				return
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii') + "_" + self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "_": path = self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			if path == "" or path == "(No ROM data detected)": path = "ROM"
			mbc = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The save type was not selected or auto-detection failed.", QtWidgets.QMessageBox.Ok)
				return
		else:
			return
		
		add_date_time = self.SETTINGS.value("SaveFileNameAddDateTime", default="disabled")
		if add_date_time and add_date_time.lower() == "enabled":
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path) + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".sav"
		else:
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path) + ".sav"
		
		path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
		if (path == ""): return

		rtc = False
		if features in (0x10, 0xFD, 0xFE): # RTC of MBC3, TAMA5, HuC-3
			msg = "Do you want the cartridge’s Real Time Clock register values also to be saved?"
			if features == 0x10 and not self.CONN.IsClkConnected():
				msg += "\n\nPlease note that this feature is not fully supported by the {:s} hardware. Latching and restoring RTC register data will not work.".format(self.CONN.GetName())
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Yes)
			if answer == QtWidgets.QMessageBox.Cancel: return
			rtc = (answer == QtWidgets.QMessageBox.Yes)

		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.CONN.BackupRAM(fncSetProgress=self.PROGRESS.SetProgress, path=path, mbc=mbc, save_type=save_type, rtc=rtc)

	def WriteRAM(self, dpath="", erase=False):
		if not self.CheckDeviceAlive(): return
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			if dpath == "": path = self.lblHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			#mbc = Util.DMG_Header_Features_MBC[self.cmbHeaderFeaturesResult.currentIndex()]
			mbc = (list(Util.DMG_Header_Features.items())[self.cmbHeaderFeaturesResult.currentIndex()])[0]
			try:
				features = list(Util.DMG_Header_Features.keys())[self.cmbHeaderFeaturesResult.currentIndex()]
			except:
				features = []
			save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Please select the correct save data size.", QtWidgets.QMessageBox.Ok)
				return

		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			if dpath == "":
				path = self.lblAGBHeaderTitleResult.text().strip().encode('ascii', 'ignore').decode('ascii') + "_" + self.lblAGBHeaderCodeResult.text().strip().encode('ascii', 'ignore').decode('ascii')
			mbc = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The save type was not selected or auto-detection failed.", QtWidgets.QMessageBox.Ok)
				return
		else:
			return
		
		filesize = 0
		if dpath != "":
			text = "The following save data file will now be written to the cartridge:\n" + dpath
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), text, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Ok)
			if answer == QtWidgets.QMessageBox.Cancel: return
			path = dpath
			self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		elif erase:
			answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The save data on your cartridge will now be erased.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
			if answer == QtWidgets.QMessageBox.Cancel: return
		else:
			path = path + ".sav"
			path = QtWidgets.QFileDialog.getOpenFileName(self, "Restore Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
			if not path == "": self.SETTINGS.setValue(setting_name, os.path.dirname(path))
			if (path == ""): return
			filesize = os.path.getsize(path)
			if filesize > 0x100000: # reject too large files to avoid exploding RAM
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "Files bigger than 1 MB are not supported.", QtWidgets.QMessageBox.Ok)
				return
		
		rtc = False
		# RTC of TAMA5, HuC-3
		if (features == 0xFD and (filesize == save_type + 0x18 or erase)) or \
		(features == 0xFE and (filesize == save_type + 0xC or erase)): #or (features == 0x10 and filesize == save_type + 0x30 or erase):
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "Do you want the Real Time Clock register values to be also written?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Yes)
			if answer == QtWidgets.QMessageBox.Cancel: return
			rtc = (answer == QtWidgets.QMessageBox.Yes)

		self.CONN.RestoreRAM(fncSetProgress=self.PROGRESS.SetProgress, path=path, mbc=mbc, save_type=save_type, erase=erase, rtc=rtc)
	
	def CheckDeviceAlive(self, setMode=False):
		if self.CONN is not None:
			mode = self.CONN.GetMode()
			if self.CONN.DEVICE is not None:
				if not self.CONN.IsConnected():
					self.DisconnectDevice()
					self.DEVICES = {}
					dontShowAgain = str(self.SETTINGS.value("AutoReconnect", default="disabled")).lower() == "enabled"
					if not dontShowAgain:
						cb = QtWidgets.QCheckBox("Always try to reconnect without asking", checked=False)
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The connection to the device was lost. Do you want to try and reconnect to the first device found? The cartridge information will also be reset and read again.", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
						msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
						msgbox.setCheckBox(cb)
						answer = msgbox.exec()
						dontShowAgain = cb.isChecked()
						if dontShowAgain: self.SETTINGS.setValue("AutoReconnect", "enabled")
						if answer == QtWidgets.QMessageBox.No:
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
		else: # mode not set yet
			if self.optDMG.isChecked():
				setTo = "DMG"
			elif self.optAGB.isChecked():
				setTo = "AGB"
		
		voltageWarning = ""
		if self.CONN.CanSetVoltageAutomatically(): # device can switch in software
			dontShowAgain = str(self.SETTINGS.value("SkipModeChangeWarning", default="disabled")).lower() == "enabled"
		elif self.CONN.CanSetVoltageManually(): # device has a physical switch
			voltageWarning = "\n\nImportant: Also make sure your device is set to the correct voltage!"
			dontShowAgain = False
		else: # no voltage switching supported
			dontShowAgain = False
		
		if not dontShowAgain and mode is not None:
			cb = QtWidgets.QCheckBox("Don’t show this message again.", checked=False)
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The mode will now be changed to " + {"DMG":"Game Boy", "AGB":"Game Boy Advance"}[setTo] + " mode. To be safe, cartridges should only be exchanged while the device is not powered on." + voltageWarning, standardButtons=QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
			msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
			if self.CONN.CanSetVoltageAutomatically(): msgbox.setCheckBox(cb)
			answer = msgbox.exec()
			dontShowAgain = cb.isChecked()
			if answer == QtWidgets.QMessageBox.Cancel:
				if mode == "DMG": self.optDMG.setChecked(True)
				if mode == "AGB": self.optAGB.setChecked(True)
				return False
			if dontShowAgain: self.SETTINGS.setValue("SkipModeChangeWarning", "enabled")
		
		if not self.CheckDeviceAlive(setMode=setTo): return
		
		if self.optDMG.isChecked() and (mode == "AGB" or mode == None):
			self.CONN.SetMode("DMG")
		elif self.optAGB.isChecked() and (mode == "DMG" or mode == None):
			self.CONN.SetMode("AGB")
		
		self.ReadCartridge()
		qt_app.processEvents()
		self.btnHeaderRefresh.setEnabled(True)
		self.btnBackupROM.setEnabled(True)
		self.btnFlashROM.setEnabled(True)
		self.btnBackupRAM.setEnabled(True)
		self.btnRestoreRAM.setEnabled(True)
		self.grpDMGCartridgeInfo.setEnabled(True)
		self.grpAGBCartridgeInfo.setEnabled(True)
	
	def ReadCartridge(self, resetStatus=True):
		if not self.CheckDeviceAlive(): return
		data = self.CONN.ReadInfo(setPinsAsInputs=True)
		
		if data == False or len(data) == 0:
			self.DisconnectDevice()
			return False
				
		if self.CONN.GetMode() == "DMG":
			self.cmbHeaderFeaturesResult.clear()
			self.cmbHeaderFeaturesResult.addItems(list(Util.DMG_Header_Features.values()))
			self.cmbHeaderFeaturesResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			self.cmbDMGCartridgeTypeResult.clear()
			self.cmbDMGCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesDMG()[0])
			self.cmbDMGCartridgeTypeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			self.cmbHeaderROMSizeResult.clear()
			self.cmbHeaderROMSizeResult.addItems(Util.DMG_Header_ROM_Sizes)
			self.cmbHeaderROMSizeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			self.cmbHeaderRAMSizeResult.clear()
			self.cmbHeaderRAMSizeResult.addItems(Util.DMG_Header_RAM_Sizes)
			self.cmbHeaderRAMSizeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			if "flash_type" in data:
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(data["flash_type"])
			
			self.lblHeaderTitleResult.setText(data['game_title'])
			if data['sgb'] in Util.DMG_Header_SGB:
				self.lblHeaderSGBResult.setText(Util.DMG_Header_SGB[data['sgb']])
			else:
				self.lblHeaderSGBResult.setText("Unknown (0x{:02X})".format(data['sgb']))
			if data['cgb'] in Util.DMG_Header_CGB:
				self.lblHeaderCGBResult.setText(Util.DMG_Header_CGB[data['cgb']])
			else:
				self.lblHeaderCGBResult.setText("Unknown (0x{:02X})".format(data['cgb']))
			if data['logo_correct']:
				self.lblHeaderLogoValidResult.setText("OK")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			else:
				self.lblHeaderLogoValidResult.setText("Invalid")
				self.lblHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }")
			if data['header_checksum_correct']:
				self.lblHeaderChecksumResult.setText("Valid (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			else:
				self.lblHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet("QLabel { color: red; }")
			self.lblHeaderROMChecksumResult.setText("0x{:04X}".format(data['rom_checksum']))
			self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			self.cmbHeaderROMSizeResult.setCurrentIndex(data["rom_size_raw"])
			for i in range(0, len(Util.DMG_Header_RAM_Sizes_Map)):
				if data["ram_size_raw"] == Util.DMG_Header_RAM_Sizes_Map[i]:
					self.cmbHeaderRAMSizeResult.setCurrentIndex(i)
			i = 0
			for k in Util.DMG_Header_Features.keys():
				if data["features_raw"] == k:
					self.cmbHeaderFeaturesResult.setCurrentIndex(i)
					if k == 0x06: # MBC2
						self.cmbHeaderRAMSizeResult.setCurrentIndex(1)
					elif k == 0x22 and data["game_title"] in ("KORO2 KIRBYKKKJ", "KIRBY TNT__KTNE"): # MBC7 Kirby
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x101))
					elif k == 0x22 and data["game_title"] in ("CMASTER____KCEJ"): # MBC7 Command Master
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x102))
					elif k == 0xFD: # TAMA5
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x103))

				i += 1
			
			if data['empty'] == True: # defaults
				self.lblHeaderTitleResult.setText("(No ROM data detected)")
				self.lblHeaderTitleResult.setStyleSheet("QLabel { color: red; }")
				self.cmbHeaderROMSizeResult.setCurrentIndex(11)
				self.cmbHeaderRAMSizeResult.setCurrentIndex(0)
				self.cmbHeaderFeaturesResult.setCurrentIndex(0)
			else:
				self.lblHeaderTitleResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
				if data['logo_correct'] and not self.CONN.IsSupportedMbc(data["features_raw"]):
					QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge uses a Memory Bank Controller that may not be completely supported yet. A future version of {:s} may add support for it.".format(APPNAME), QtWidgets.QMessageBox.Ok)
				if data['logo_correct'] and data['game_title'] == "NP M-MENU MENU":
					cart_types = self.CONN.GetSupportedCartridgesDMG()
					for i in range(0, len(cart_types[0])):
						if "DMG-MMSA-JPN" in cart_types[0][i]:
							self.cmbDMGCartridgeTypeResult.setCurrentIndex(i)
			
			self.grpAGBCartridgeInfo.setVisible(False)
			self.grpDMGCartridgeInfo.setVisible(True)
		
		elif self.CONN.GetMode() == "AGB":
			self.cmbAGBCartridgeTypeResult.clear()
			self.cmbAGBCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesAGB()[0])
			self.cmbAGBCartridgeTypeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
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
				self.lblAGBHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }")

			if data['96h_correct']:
				self.lblAGBHeader96hResult.setText("OK")
				self.lblAGBHeader96hResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeader96hResult.setText("Invalid")
				self.lblAGBHeader96hResult.setStyleSheet("QLabel { color: red; }")
			
			if data['header_checksum_correct']:
				self.lblAGBHeaderChecksumResult.setText("Valid (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet("QLabel { color: red; }")
			
			self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			self.lblAGBHeaderROMChecksumResult.setText("Not available")
			Util.AGB_Global_CRC32 = 0
			
			db_agb_entry = None
			if os.path.exists("{0:s}/db_AGB.json".format(self.CONFIG_PATH)):
				with open("{0:s}/db_AGB.json".format(self.CONFIG_PATH)) as f:
					db_agb = f.read()
					db_agb = json.loads(db_agb)
					if data["header_sha1"] in db_agb.keys():
						db_agb_entry = db_agb[data["header_sha1"]]
					else:
						self.lblAGBHeaderROMChecksumResult.setText("Not in database")
			else:
				print("FAIL: Database for Game Boy Advance titles not found in " + "{0:s}/db_AGB.json".format(self.CONFIG_PATH))
			
			if db_agb_entry != None:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(Util.AGB_Header_ROM_Sizes_Map.index(db_agb_entry['rs']))
				if data["rom_size_calc"] < 0x400000:
					self.lblAGBHeaderROMChecksumResult.setText("In database (0x{:06X})".format(db_agb_entry['rc']))
					Util.AGB_Global_CRC32 = db_agb_entry['rc']
			
			elif data["rom_size"] != 0:
				if not data["rom_size"] in Util.AGB_Header_ROM_Sizes_Map:
					data["rom_size"] = 0x2000000
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(Util.AGB_Header_ROM_Sizes_Map.index(data["rom_size"]))
			else:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(0)
			
			if data["save_type"] == None:
				self.cmbAGBSaveTypeResult.setCurrentIndex(0)
				if db_agb_entry != None:
					if db_agb_entry['st'] < len(Util.AGB_Header_Save_Types):
						self.cmbAGBSaveTypeResult.setCurrentIndex(db_agb_entry['st'])
			
			if data['empty'] == True: # defaults
				self.lblAGBHeaderTitleResult.setText("(No ROM data detected)")
				self.lblAGBHeaderTitleResult.setStyleSheet("QLabel { color: red; }")
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(3)
				self.cmbAGBSaveTypeResult.setCurrentIndex(0)
			else:
				self.lblAGBHeaderTitleResult.setStyleSheet(self.lblHeaderCGBResult.styleSheet())
			
			self.grpDMGCartridgeInfo.setVisible(False)
			self.grpAGBCartridgeInfo.setVisible(True)
			
			if data['logo_correct'] and isinstance(db_agb_entry, dict) and "rs" in db_agb_entry and db_agb_entry['rs'] == 0x4000000 and not self.CONN.IsSupported3dMemory():
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge uses a Memory Bank Controller that may not be completely supported yet. A future version of the {:s} device firmware may add support for it.".format(self.CONN.GetName()), QtWidgets.QMessageBox.Ok)
		
		if resetStatus:
			self.lblStatus1aResult.setText("–")
			self.lblStatus2aResult.setText("–")
			self.lblStatus3aResult.setText("–")
			self.lblStatus4a.setText("Ready.")
			self.grpStatus.setTitle("Transfer Status")
			self.FinishOperation()
		
		if self.CONN.CheckROMStable() is False:
			QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Unstable ROM reading detected. Please make sure you selected the correct mode and that the cartridge contacts are clean.", QtWidgets.QMessageBox.Ok)
			return
		
		if not data['logo_correct'] and data['empty'] == False:
			QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The Nintendo Logo check failed which usually means that the cartridge couldn’t be read correctly. Please make sure you selected the correct mode and that the cartridge contacts are clean.", QtWidgets.QMessageBox.Ok)
		
		if data['game_title'][:11] == "YJencrypted":
			QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge may be protected against reading or writing a ROM. If you don’t want to risk this cartridge to render itself unusable, please do not try to write a new ROM to it.", QtWidgets.QMessageBox.Ok)

	def UpdateProgress(self, args):
		if args is None: return
		if "method" in args:
			if args["method"] == "ROM_READ":
				self.grpStatus.setTitle("Transfer Status (Backup ROM)")
			elif args["method"] == "ROM_WRITE":
				self.grpStatus.setTitle("Transfer Status (Flash ROM)")
			elif args["method"] == "ROM_WRITE_VERIFY":
				self.grpStatus.setTitle("Transfer Status (Verify Flash)")
			elif args["method"] == "SAVE_READ":
				self.grpStatus.setTitle("Transfer Status (Backup Save Data)")
			elif args["method"] == "SAVE_WRITE":
				self.grpStatus.setTitle("Transfer Status (Write Save Data)")
		
		if "error" in args:
			self.lblStatus4a.setText("Failed!")
			self.grpDMGCartridgeInfo.setEnabled(True)
			self.grpAGBCartridgeInfo.setEnabled(True)
			self.grpActions.setEnabled(True)
			self.btnCancel.setEnabled(False)
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=str(args["error"]), standardButtons=QtWidgets.QMessageBox.Ok)
			if not '\n' in str(args["error"]): msgbox.setTextFormat(QtCore.Qt.RichText)
			msgbox.exec()
			return
		
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		
		pos = 0
		size = 0
		speed = 0
		elapsed = 0
		left = 0
		if "pos" in args: pos = args["pos"]
		if "size" in args: size = args["size"]
		if "speed" in args: speed = args["speed"]
		if "time_elapsed" in args: elapsed = args["time_elapsed"]
		if "time_left" in args: left = args["time_left"]
		
		if "action" in args:
			if args["action"] == "ERASE":
				self.lblStatus1aResult.setText("Pending...")
				self.lblStatus2aResult.setText("Pending...")
				self.lblStatus3aResult.setText(Util.formatProgressTime(elapsed))
				self.lblStatus4a.setText("Erasing flash... This may take some time.")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(args["abortable"])
				self.SetProgressBars(min=0, max=size, value=pos)
			elif args["action"] == "SECTOR_ERASE":
				if elapsed >= 1:
					self.lblStatus3aResult.setText(Util.formatProgressTime(elapsed))
				self.lblStatus4a.setText("Erasing sector at address 0x{:X}...".format(args["sector_pos"]))
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(args["abortable"])
				self.SetProgressBars(min=0, max=size, value=pos)
			elif args["action"] == "ABORTING":
				self.lblStatus1aResult.setText("–")
				self.lblStatus2aResult.setText("–")
				self.lblStatus3aResult.setText("–")
				self.lblStatus4a.setText("Stopping... Please wait.")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(args["abortable"])
				self.SetProgressBars(min=0, max=size, value=pos)
			elif args["action"] == "FINISHED":
				self.FinishOperation()
			elif args["action"] == "ABORT":
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
				self.grpStatus.setTitle("Transfer Status")
				self.lblStatus1aResult.setText("–")
				self.lblStatus2aResult.setText("–")
				self.lblStatus3aResult.setText("–")
				self.lblStatus4a.setText("Stopped.")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(False)
				self.SetProgressBars(min=0, max=1, value=0)
				self.btnCancel.setEnabled(False)
				
				if "info_type" in args.keys() and "info_msg" in args.keys():
					if args["info_type"] == "msgbox_critical":
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=args["info_msg"], standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in args["info_msg"]: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
					elif args["info_type"] == "msgbox_information":
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=args["info_msg"], standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in args["info_msg"]: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
					elif args["info_type"] == "label":
						self.lblStatus4a.setText(args["info_msg"])
				
				return

			elif args["action"] == "PROGRESS":
				self.SetProgressBars(min=0, max=size, value=pos)
				if "abortable" in args:
					self.btnCancel.setEnabled(args["abortable"])
				else:
					self.btnCancel.setEnabled(True)
				self.lblStatus1aResult.setText(Util.formatFileSize(pos))
				if speed > 0:
					self.lblStatus2aResult.setText("{:.2f} KB/s".format(speed))
				else:
					self.lblStatus2aResult.setText("Pending...")
				if left > 0:
					self.lblStatus4aResult.setText(Util.formatProgressTime(left))
				else:
					self.lblStatus4aResult.setText("Pending...")
				if elapsed > 0:
					self.lblStatus3aResult.setText(Util.formatProgressTime(elapsed))

				if speed == 0 and "skipping" in args and args["skipping"] is True:
					self.lblStatus4aResult.setText("Pending...")
				self.lblStatus4a.setText("Time left:")
	
	def SetProgressBars(self, min=0, max=100, value=0, setPause=None):
		self.prgStatus.setMinimum(min)
		self.prgStatus.setMaximum(max)
		self.prgStatus.setValue(value)
		if self.TBPROG is not None:
			if not value > max:
				self.TBPROG.setRange(min, max)
				self.TBPROG.setValue(value)
				if value != min and value != max:
					self.TBPROG.setVisible(True)
				else:
					self.TBPROG.setVisible(False)
			if setPause is not None:
				self.TBPROG.setPaused(setPause)
			else:
				self.TBPROG.setPaused(False)
	
	def ShowPocketCameraWindow(self):
		self.CAMWIN = None
		self.CAMWIN = PocketCameraWindow(self, icon=self.windowIcon())
		self.CAMWIN.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self.CAMWIN.setModal(True)
		self.CAMWIN.run()
	
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
					# pylint: disable=undefined-variable
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1].lower() == ".sav":
					return True
				elif self.CONN.GetMode() == "DMG" and fn_split[1].lower() in (".gb", ".sgb", ".gbc", ".bin"):
					return True
				elif self.CONN.GetMode() == "AGB" and fn_split[1].lower() in (".gba", ".srl"):
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
					# pylint: disable=undefined-variable
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1].lower() in (".gb", ".sgb", ".gbc", ".bin", ".gba", ".srl"):
					self.FlashROM(fn)
				elif fn_split[1].lower() == ".sav":
					self.WriteRAM(fn)
		else:
			e.ignore()

	def closeEvent(self, event):
		self.DisconnectDevice()
		event.accept()
	
	def run(self):
		self.layout.update()
		self.layout.activate()
		screen = QtGui.QGuiApplication.screens()[0]
		screenGeometry = screen.geometry()
		x = (screenGeometry.width() - self.width()) / 2
		y = (screenGeometry.height() - self.height()) / 2
		self.move(x, y)
		self.setAcceptDrops(True)
		self.show()
		
		# Taskbar Progress on Windows only
		try:
			from PySide2.QtWinExtras import QWinTaskbarButton, QtWin
			myappid = 'lesserkuma.flashgbx'
			QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
			taskbar_button = QWinTaskbarButton()
			self.TBPROG = taskbar_button.progress()
			self.TBPROG.setRange(0, 100)
			taskbar_button.setWindow(self.windowHandle())
			self.TBPROG.setVisible(False)
		except ImportError:
			pass
		
		qt_app.exec_()

qt_app = QtWidgets.QApplication(sys.argv)
qt_app.setApplicationName(APPNAME)
