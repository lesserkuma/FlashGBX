# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import sys, os, time, datetime, json, platform, subprocess, requests, webbrowser, pkg_resources, threading
#import sys, os, time, datetime, json, platform, subprocess, threading #NOTE#UC
from .pyside import QtCore, QtWidgets, QtGui, QApplication
from PIL.ImageQt import ImageQt
from serial import SerialException
from .RomFileDMG import RomFileDMG
from .RomFileAGB import RomFileAGB
from .PocketCameraWindow import PocketCameraWindow
from .UserInputDialog import UserInputDialog
from .Util import APPNAME, VERSION, VERSION_PEP440
from . import Util
from . import hw_GBxCartRW, hw_GBxCartRW_ofw
hw_devices = [hw_GBxCartRW, hw_GBxCartRW_ofw]

class FlashGBX_GUI(QtWidgets.QWidget):
	CONN = None
	SETTINGS = None
	DEVICES = {}
	FLASHCARTS = { "DMG":{}, "AGB":{} }
	APP_PATH = ""
	CONFIG_PATH = ""
	TBPROG = None # Windows 7+ Taskbar Progress Bar
	PROGRESS = None
	CAMWIN = None
	FWUPWIN = None
	STATUS = {}
	TEXT_COLOR = (0, 0, 0, 255)
	
	def __init__(self, args):
		QtWidgets.QWidget.__init__(self)
		Util.CONFIG_PATH = args['config_path']
		Util.APP_PATH = args['app_path']
		self.SETTINGS = Util.IniSettings(path=args["config_path"] + "/settings.ini")
		self.FLASHCARTS = args["flashcarts"]
		self.PROGRESS = Util.Progress(self.UpdateProgress)
		
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.setWindowIcon(QtGui.QIcon(Util.APP_PATH + "/res/icon.ico"))
		self.setWindowTitle("{:s} {:s}".format(APPNAME, VERSION))
		self.setWindowFlags(self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint)
		self.TEXT_COLOR = QtGui.QPalette().color(QtGui.QPalette.Text).toTuple()
		
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
		self.btnHeaderRefresh = QtWidgets.QPushButton("&Refresh")
		self.btnHeaderRefresh.setMinimumHeight(25)
		self.connect(self.btnHeaderRefresh, QtCore.SIGNAL("clicked()"), self.ReadCartridge)
		rowActionsGeneral1.addWidget(self.btnHeaderRefresh)

		self.btnDetectCartridge = QtWidgets.QPushButton("Analyze &Flash Cart")
		self.btnDetectCartridge.setMinimumHeight(25)
		self.connect(self.btnDetectCartridge, QtCore.SIGNAL("clicked()"), self.DetectCartridge)
		rowActionsGeneral1.addWidget(self.btnDetectCartridge)

		rowActionsGeneral2 = QtWidgets.QHBoxLayout()
		self.btnBackupROM = QtWidgets.QPushButton("&Backup ROM")
		self.btnBackupROM.setMinimumHeight(25)
		self.connect(self.btnBackupROM, QtCore.SIGNAL("clicked()"), self.BackupROM)
		rowActionsGeneral2.addWidget(self.btnBackupROM)
		self.btnBackupRAM = QtWidgets.QPushButton("Backup &Save Data")
		self.btnBackupRAM.setMinimumHeight(25)
		self.connect(self.btnBackupRAM, QtCore.SIGNAL("clicked()"), self.BackupRAM)
		rowActionsGeneral2.addWidget(self.btnBackupRAM)
		
		self.cmbDMGCartridgeTypeResult.currentIndexChanged.connect(self.CartridgeTypeChanged)
		self.cmbHeaderMapperResult.currentIndexChanged.connect(self.DMGMapperTypeChanged)
		
		rowActionsGeneral3 = QtWidgets.QHBoxLayout()
		self.btnFlashROM = QtWidgets.QPushButton("&Write ROM")
		self.btnFlashROM.setMinimumHeight(25)
		self.connect(self.btnFlashROM, QtCore.SIGNAL("clicked()"), self.FlashROM)
		rowActionsGeneral3.addWidget(self.btnFlashROM)
		self.btnRestoreRAM = QtWidgets.QPushButton("Writ&e Save Data")
		self.mnuRestoreRAM = QtWidgets.QMenu()
		self.mnuRestoreRAM.addAction("&Restore from save data file", self.WriteRAM)
		self.mnuRestoreRAM.addAction("&Erase cartridge save data", lambda: self.WriteRAM(erase=True))
		self.mnuRestoreRAM.addSeparator()
		self.mnuRestoreRAM.addAction("Run stress &test", lambda: self.WriteRAM(test=True))
		self.btnRestoreRAM.setMenu(self.mnuRestoreRAM)
		self.btnRestoreRAM.setMinimumHeight(25)
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

		btnText = "Too&ls"
		self.btnTools = QtWidgets.QPushButton(btnText)
		btnWidth = self.btnTools.fontMetrics().boundingRect(btnText).width() + 24
		if platform.system() == "Darwin": btnWidth += 12
		self.btnTools.setMaximumWidth(btnWidth)
		self.mnuTools = QtWidgets.QMenu()
		self.mnuTools.addAction("Game Boy &Camera Album Viewer", self.ShowPocketCameraWindow)
		self.mnuTools.addSeparator()
		self.mnuTools.addAction("Firmware &Updater", self.ShowFirmwareUpdateWindow)
		self.btnTools.setMenu(self.mnuTools)

		btnText = "C&onfig"
		self.btnConfig = QtWidgets.QPushButton(btnText)
		btnWidth = self.btnConfig.fontMetrics().boundingRect(btnText).width() + 24
		if platform.system() == "Darwin": btnWidth += 12
		self.btnConfig.setMaximumWidth(btnWidth)

		self.mnuConfig = QtWidgets.QMenu()
		self.mnuConfig.addAction("Check for &updates on application startup", lambda: [ self.EnableUpdateCheck() ])
		self.mnuConfig.addAction("&Append date && time to filename of save data backups", lambda: self.SETTINGS.setValue("SaveFileNameAddDateTime", str(self.mnuConfig.actions()[1].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Prefer full &chip erase", lambda: self.SETTINGS.setValue("PreferChipErase", str(self.mnuConfig.actions()[2].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Extra data &verification", lambda: self.SETTINGS.setValue("VerifyData", str(self.mnuConfig.actions()[3].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("&Limit voltage to 3.3V when detecting Game Boy flash cartridges", lambda: self.SETTINGS.setValue("AutoDetectLimitVoltage", str(self.mnuConfig.actions()[4].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Limit &baud rate to 1Mbps for GBxCart RW v1.4 devices", lambda: [ self.SETTINGS.setValue("LimitBaudRate", str(self.mnuConfig.actions()[5].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")), self.SetLimitBaudRate() ])
		self.mnuConfig.addAction("Always &generate ROM dump reports", lambda: self.SETTINGS.setValue("GenerateDumpReports", str(self.mnuConfig.actions()[6].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addAction("Use &No-Intro file names", lambda: self.SETTINGS.setValue("UseNoIntroFilenames", str(self.mnuConfig.actions()[7].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")))
		self.mnuConfig.addSeparator()
		self.mnuConfig.addAction("Re-&enable suppressed messages", self.ReEnableMessages)
		self.mnuConfig.addSeparator()
		self.mnuConfig.addAction("Show &configuration directory", self.OpenPath)
		self.mnuConfig.actions()[0].setCheckable(True)
		#self.mnuConfig.actions()[0].setVisible(False) #NOTE#UC
		self.mnuConfig.actions()[1].setCheckable(True)
		self.mnuConfig.actions()[2].setCheckable(True)
		self.mnuConfig.actions()[3].setCheckable(True)
		self.mnuConfig.actions()[4].setCheckable(True)
		self.mnuConfig.actions()[5].setCheckable(True)
		self.mnuConfig.actions()[6].setCheckable(True)
		self.mnuConfig.actions()[7].setCheckable(True)
		self.mnuConfig.actions()[0].setChecked(self.SETTINGS.value("UpdateCheck") == "enabled")
		self.mnuConfig.actions()[1].setChecked(self.SETTINGS.value("SaveFileNameAddDateTime", default="disabled") == "enabled")
		self.mnuConfig.actions()[2].setChecked(self.SETTINGS.value("PreferChipErase", default="disabled") == "enabled")
		self.mnuConfig.actions()[3].setChecked(self.SETTINGS.value("VerifyData", default="enabled") == "enabled")
		self.mnuConfig.actions()[4].setChecked(self.SETTINGS.value("AutoDetectLimitVoltage", default="disabled") == "enabled")
		self.mnuConfig.actions()[5].setChecked(self.SETTINGS.value("LimitBaudRate", default="disabled") == "enabled")
		self.mnuConfig.actions()[6].setChecked(self.SETTINGS.value("GenerateDumpReports", default="disabled") == "enabled")
		self.mnuConfig.actions()[7].setChecked(self.SETTINGS.value("UseNoIntroFilenames", default="enabled") == "enabled")
		
		self.btnConfig.setMenu(self.mnuConfig)
		
		self.btnConnect = QtWidgets.QPushButton("&Connect")
		self.connect(self.btnConnect, QtCore.SIGNAL("clicked()"), self.ConnectDevice)
		self.layout_devices.addWidget(self.btnTools)
		self.layout_devices.addWidget(self.btnConfig)
		self.layout_devices.addWidget(self.btnConnect)
		
		self.layout.addLayout(self.layout_devices, 1, 0, 1, 0)
		
		# Disable widgets
		self.optAGB.setEnabled(False)
		self.optDMG.setEnabled(False)
		self.btnHeaderRefresh.setEnabled(False)
		self.btnDetectCartridge.setEnabled(False)
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
		self.QT_APP = qt_app
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

		QtCore.QTimer.singleShot(1, lambda: [ self.UpdateCheck(), self.FindDevices(port=args["argparsed"].device_port) ])


	def GuiCreateGroupBoxDMGCartInfo(self):
		self.grpDMGCartridgeInfo = QtWidgets.QGroupBox("Game Boy Cartridge Information")
		self.grpDMGCartridgeInfo.setMinimumWidth(364)
		group_layout = QtWidgets.QVBoxLayout()
		group_layout.setContentsMargins(-1, 5, -1, -1)

		rowHeaderTitle = QtWidgets.QHBoxLayout()
		lblHeaderTitle = QtWidgets.QLabel("Game Title:")
		lblHeaderTitle.setContentsMargins(0, 1, 0, 1)
		rowHeaderTitle.addWidget(lblHeaderTitle)
		self.lblHeaderTitleResult = QtWidgets.QLabel("")
		rowHeaderTitle.addWidget(self.lblHeaderTitleResult)
		group_layout.addLayout(rowHeaderTitle)

		rowHeaderRevision = QtWidgets.QHBoxLayout()
		self.lblHeaderRevision = QtWidgets.QLabel("Game Code / Revision:")
		self.lblHeaderRevision.setContentsMargins(0, 1, 0, 1)
		rowHeaderRevision.addWidget(self.lblHeaderRevision)
		self.lblHeaderRevisionResult = QtWidgets.QLabel("")
		rowHeaderRevision.addWidget(self.lblHeaderRevisionResult)
		group_layout.addLayout(rowHeaderRevision)

		rowHeaderRtc = QtWidgets.QHBoxLayout()
		lblHeaderRtc = QtWidgets.QLabel("Real Time Clock:")
		lblHeaderRtc.setContentsMargins(0, 1, 0, 1)
		rowHeaderRtc.addWidget(lblHeaderRtc)
		self.lblHeaderRtcResult = QtWidgets.QLabel("")
		self.lblHeaderRtcResult.setCursor(QtGui.QCursor(QtCore.Qt.WhatsThisCursor))
		self.lblHeaderRtcResult.setToolTip("This shows the internal register values; in-game clock may use an offset")
		rowHeaderRtc.addWidget(self.lblHeaderRtcResult)
		group_layout.addLayout(rowHeaderRtc)

		rowHeaderLogoValid = QtWidgets.QHBoxLayout()
		lblHeaderLogoValid = QtWidgets.QLabel("Boot Logo:")
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

		rowHeaderMapper = QtWidgets.QHBoxLayout()
		lblHeaderMapper = QtWidgets.QLabel("Mapper Type:")
		rowHeaderMapper.addWidget(lblHeaderMapper)
		self.cmbHeaderMapperResult = QtWidgets.QComboBox()
		self.cmbHeaderMapperResult.setStyleSheet("combobox-popup: 0;")
		self.cmbHeaderMapperResult.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		rowHeaderMapper.addWidget(self.cmbHeaderMapperResult)
		group_layout.addLayout(rowHeaderMapper)

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
		self.grpAGBCartridgeInfo.setMinimumWidth(364)
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

		rowAGBHeaderRevision = QtWidgets.QHBoxLayout()
		lblAGBHeaderRevision = QtWidgets.QLabel("Revision:")
		lblAGBHeaderRevision.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderRevision.addWidget(lblAGBHeaderRevision)
		self.lblAGBHeaderRevisionResult = QtWidgets.QLabel("")
		rowAGBHeaderRevision.addWidget(self.lblAGBHeaderRevisionResult)
		group_layout.addLayout(rowAGBHeaderRevision)

		rowAGBGpioRtc = QtWidgets.QHBoxLayout()
		lblAGBGpioRtc = QtWidgets.QLabel("Real Time Clock:")
		lblAGBGpioRtc.setContentsMargins(0, 1, 0, 1)
		rowAGBGpioRtc.addWidget(lblAGBGpioRtc)
		self.lblAGBGpioRtcResult = QtWidgets.QLabel("")
		self.lblAGBGpioRtcResult.setCursor(QtGui.QCursor(QtCore.Qt.WhatsThisCursor))
		self.lblAGBGpioRtcResult.setToolTip(self.lblHeaderRtcResult.toolTip())
		rowAGBGpioRtc.addWidget(self.lblAGBGpioRtcResult)
		group_layout.addLayout(rowAGBGpioRtc)

		rowAGBHeaderLogoValid = QtWidgets.QHBoxLayout()
		lblAGBHeaderLogoValid = QtWidgets.QLabel("Boot Logo:")
		lblAGBHeaderLogoValid.setContentsMargins(0, 1, 0, 1)
		rowAGBHeaderLogoValid.addWidget(lblAGBHeaderLogoValid)
		self.lblAGBHeaderLogoValidResult = QtWidgets.QLabel("")
		rowAGBHeaderLogoValid.addWidget(self.lblAGBHeaderLogoValidResult)
		group_layout.addLayout(rowAGBHeaderLogoValid)

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
	
	def SetLimitBaudRate(self):
		if not self.CheckDeviceAlive(): return
		mode = self.CONN.GetMode()
		limit_baudrate = self.SETTINGS.value("LimitBaudRate")
		if limit_baudrate == "enabled":
			self.CONN.ChangeBaudRate(baudrate=1000000)
		else:
			self.CONN.ChangeBaudRate(baudrate=1700000)
		self.DisconnectDevice()
		self.FindDevices(connectToFirst=True, mode=mode)
	
	def EnableUpdateCheck(self):
		update_check = self.SETTINGS.value("UpdateCheck")
		if update_check is None:
			self.UpdateCheck()
			return
		
		#NOTE#UC
		new_value = str(self.mnuConfig.actions()[0].isChecked()).lower().replace("true", "enabled").replace("false", "disabled")
		if new_value == "enabled":
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "Would you like to automatically check for new versions at application startup? This will make use of the PyPI API (<a href=\"https://www.python.org/privacy/\">privacy policy</a>).", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
			if answer == QtWidgets.QMessageBox.Yes:
				self.SETTINGS.setValue("UpdateCheck", "enabled")
				self.mnuConfig.actions()[0].setChecked(True)
				update_check = "enabled"
				self.UpdateCheck()
			else:
				self.mnuConfig.actions()[0].setChecked(False)
				self.SETTINGS.setValue("UpdateCheck", "disabled")
		else:
			self.SETTINGS.setValue("UpdateCheck", "disabled")
	
	def UpdateCheck(self):
		#NOTE#UC
		# update_check = self.SETTINGS.value("UpdateCheck")
		# if update_check is None or datetime.datetime.now() > datetime.datetime.fromtimestamp(1682892000):
		# 	QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Welcome to {:s} {:s} by Lesserkuma!<br><br>".format(APPNAME, VERSION) + "This version has version update check feature stripped out, so please regularily check the <a href=\"https://github.com/lesserkuma/FlashGBX/\">FlashGBX GitHub page</a> for the latest updates.", QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
		# 	self.SETTINGS.setValue("UpdateCheck", "disabled")
		update_check = self.SETTINGS.value("UpdateCheck")
		if update_check is None:
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "Welcome to {:s} {:s} by Lesserkuma!<br><br>".format(APPNAME, VERSION) + "Would you like to automatically check for new versions at application startup? This will make use of the PyPI API (<a href=\"https://www.python.org/privacy/\">privacy policy</a>).", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
			if answer == QtWidgets.QMessageBox.Yes:
				self.SETTINGS.setValue("UpdateCheck", "enabled")
				self.mnuConfig.actions()[0].setChecked(True)
				update_check = "enabled"
			else:
				self.SETTINGS.setValue("UpdateCheck", "disabled")
		if update_check and update_check.lower() == "enabled":
			print("")
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
			devname = self.CONN.GetFullNameExtended()
			self.CONN.Close()
			self.CONN = None
			self.DEVICES = {}
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
		self.btnDetectCartridge.setEnabled(False)
		self.btnBackupROM.setEnabled(False)
		self.btnFlashROM.setEnabled(False)
		self.btnBackupRAM.setEnabled(False)
		self.btnRestoreRAM.setEnabled(False)
		self.btnConnect.setText("&Connect")
		self.lblDevice.setText("Disconnected.")
		self.SetProgressBars(min=0, max=1, value=0)
		self.lblStatus4a.setText("Disconnected.")
		self.lblStatus1aResult.setText("–")
		self.lblStatus2aResult.setText("–")
		self.lblStatus3aResult.setText("–")
		self.lblStatus4aResult.setText("")
		self.lblStatus4a.setText("Disconnected.")
		self.grpStatus.setTitle("Transfer Status")
	
	def ReEnableMessages(self):
		self.SETTINGS.setValue("AutoReconnect", "disabled")
		self.SETTINGS.setValue("SkipModeChangeWarning", "disabled")
		self.SETTINGS.setValue("SkipAutodetectMessage", "disabled")
		self.SETTINGS.setValue("SkipFinishMessage", "disabled")
		self.SETTINGS.setValue("SkipCameraSavePopup", "disabled")

	def OpenPath(self, path=None):
		if path is None: path = Util.CONFIG_PATH
		path = 'file://{0:s}'.format(path)
		try:
			if platform.system() == "Windows":
				os.startfile(path)
			elif platform.system() == "Darwin":
				subprocess.Popen(["open", path])
			else:
				subprocess.Popen(["xdg-open", path])
		except:
			QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "The path is:\n{:s}".format(path), QtWidgets.QMessageBox.Ok)
		
		kbmod = QtWidgets.QApplication.keyboardModifiers()
		if kbmod == QtCore.Qt.ShiftModifier:
			if self.WriteDebugLog(): print("debug.log written.")

	def WriteDebugLog(self):
		try:
			fn = Util.CONFIG_PATH + "/debug.log"
			with open(fn, "wb") as f:
				f.write("\n".join(Util.DEBUG_LOG).encode("UTF-8-SIG"))
			return True
		except:
			return False

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
			port = dev.GetPort()
			if str(self.SETTINGS.value("LimitBaudRate", default="disabled")).lower() == "enabled":
				max_baud = 1000000
			else:
				max_baud = 1700000
			ret = dev.Initialize(self.FLASHCARTS, port=port, max_baud=max_baud)
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
				dev.SetWriteDelay(enable=str(self.SETTINGS.value("WriteDelay", default="disabled")).lower() == "enabled")
				qt_app.processEvents()
				self.CONN = dev
				self.CONN.SetTimeout(float(self.SETTINGS.value("SerialTimeout", default="0.5")))
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
				self.lblStatus4a.setText("Ready.")
				self.btnConnect.setText("&Disconnect")
				self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }")
				if dev.GetFWBuildDate() == "":
					self.lblDevice.setText(dev.GetFullNameExtended() + " [Legacy Mode]")
				else:
					self.lblDevice.setText(dev.GetFullNameExtended())
				print("\nConnected to {:s}".format(dev.GetFullNameExtended(more=True)))
				self.grpActions.setEnabled(True)
				self.btnTools.setEnabled(True)
				self.btnConfig.setEnabled(True)
				self.btnCancel.setEnabled(False)

				# Firmware Update Menu
				self.mnuTools.actions()[2].setEnabled(True)
				supports_firmware_updates = self.CONN.SupportsFirmwareUpdates()
				if supports_firmware_updates is False:
					self.mnuTools.actions()[2].setEnabled(False)

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

				if supports_firmware_updates:
					if dev.FirmwareUpdateAvailable():
						dontShowAgain = str(self.SETTINGS.value("SkipFirmwareUpdate", default="disabled")).lower() == "enabled"
						if not dontShowAgain or dev.FW_UPDATE_REQ:
							if dev.FW_UPDATE_REQ:
								text = "A firmware update for your {:s} device is required to use this software. Do you want to update now?".format(dev.GetFullName())
								msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.Yes)
							else:
								text = "A firmware update for your {:s} device is available. Do you want to update now?".format(dev.GetFullName())
								msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=text, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.Yes)
								cb = QtWidgets.QCheckBox("Ignore firmware updates", checked=dontShowAgain)
							answer = msgbox.exec()
							if dev.FW_UPDATE_REQ:
								if answer == QtWidgets.QMessageBox.Yes:
									self.ShowFirmwareUpdateWindow()
								if not Util.DEBUG:
									self.DisconnectDevice()
							else:
								dontShowAgain = cb.isChecked()
								if dontShowAgain: self.SETTINGS.setValue("SkipFirmwareUpdate", "enabled")
								if answer == QtWidgets.QMessageBox.Yes:
									self.ShowFirmwareUpdateWindow()
				elif dev.FW_UPDATE_REQ:
					text = "A firmware update for your {:s} device is required to use this software. Please visit the official website (<a href=\"{:s}\">{:s}</a>) for updates.<br><br>Current firmware version: {:s}".format(dev.GetFullName(), dev.GetOfficialWebsite(), dev.GetOfficialWebsite(), dev.GetFirmwareVersion())
					if not Util.DEBUG:
						self.DisconnectDevice()
					QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), text, QtWidgets.QMessageBox.Ok)

				return True
			return False
	
	def FindDevices(self, connectToFirst=False, port=None, mode=None):
		if self.CONN is not None:
			self.DisconnectDevice()
		self.lblDevice.setText("Searching...")
		self.btnConnect.setEnabled(False)
		qt_app.processEvents()
		
		messages = []
		last_msg = ""

		# pylint: disable=global-variable-not-assigned
		global hw_devices
		for hw_device in hw_devices:
			dev = hw_device.GbxDevice()
			if str(self.SETTINGS.value("LimitBaudRate", default="disabled")).lower() == "enabled":
				max_baud = 1000000
			else:
				max_baud = 1700000
			ret = dev.Initialize(self.FLASHCARTS, port=port, max_baud=max_baud)
			if ret is False:
				self.CONN = None
			elif isinstance(ret, list):
				for i in range(0, len(ret)):
					status = ret[i][0]
					msg = ret[i][1]
					if msg == last_msg: # don’t show the same message twice
						continue
					else:
						last_msg = msg
					if status == 3:
						messages.append(msg)
						self.CONN = None
			
			if dev.IsConnected():
				self.DEVICES[dev.GetFullNameExtended()] = dev
				dev.Close()
		
		self.cmbDevice.setStyleSheet("QComboBox { border: 0; margin: 0; padding: 0; max-width: 0px; }")
		
		if len(self.DEVICES) == 0:
			if len(messages) > 0:
				msg = ""
				for message in messages:
					msg += message + "\n\n"
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), msg[:-2], QtWidgets.QMessageBox.Ok)
			else:
				QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="No compatible devices found. Please ensure the device is connected properly.\n\nTroubleshooting advice:\n- Reconnect the device and check if the operating system detects it\n- Try different USB ports and cables, avoid passive USB hubs\n- Use a USB data cable (battery charging cables may not work)\n- Ensure your user account has permissions to use the device\n- Refer to the device compatibility list on the <a href=\"https://github.com/lesserkuma/FlashGBX/#compatible-cartridge-readerwriter-hardware\">GitHub page</a>".replace("\n", "<br>"), standardButtons=QtWidgets.QMessageBox.Ok).exec()
			
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
			self.lblDevice.setText("Connect to:")
			self.cmbDevice.clear()
			self.cmbDevice.addItems(self.DEVICES.keys())
			self.cmbDevice.setCurrentIndex(0)
			self.cmbDevice.setStyleSheet("")
			self.btnConnect.setEnabled(True)
		
		self.btnConnect.setEnabled(True)
		
		if len(self.DEVICES) == 0: return False

		if mode == "DMG":
			self.optDMG.setChecked(True)
			self.SetMode()
		elif mode == "AGB":
			self.optAGB.setChecked(True)
			self.SetMode()
		
		return True

	def AbortOperation(self):
		self.CONN.CANCEL_ARGS["from_user"] = True
		self.CONN.CANCEL = True
		self.CONN.ERROR = False
		self.lblStatus4a.setText("Stopping... Please wait.")
		self.lblStatus4aResult.setText("")
	
	def FinishOperation(self):
		if self.lblStatus2aResult.text() == "Pending...": self.lblStatus2aResult.setText("–")
		self.lblStatus4aResult.setText("")
		self.grpDMGCartridgeInfo.setEnabled(True)
		self.grpAGBCartridgeInfo.setEnabled(True)
		self.grpActions.setEnabled(True)
		self.btnTools.setEnabled(True)
		self.btnConfig.setEnabled(True)
		self.btnCancel.setEnabled(False)
		
		dontShowAgain = str(self.SETTINGS.value("SkipFinishMessage", default="disabled")).lower() == "enabled"
		msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="Operation complete!", standardButtons=QtWidgets.QMessageBox.Ok)
		
		time_elapsed = None
		msg_te = ""
		speed = None
		if "time_start" in self.STATUS and self.STATUS["time_start"] > 0:
			time_elapsed = time.time() - self.STATUS["time_start"]
			msg_te = "\n\nTotal time elapsed: {:s}".format(Util.formatProgressTime(time_elapsed, asFloat=True))
			if "transferred" in self.CONN.INFO:
				speed = "{:.2f} KiB/s".format((self.CONN.INFO["transferred"] / 1024.0) / time_elapsed)
			self.STATUS["time_start"] = 0
		
		if self.CONN.INFO["last_action"] == 1: # Backup ROM
			self.CONN.INFO["last_action"] = 0
			dump_report = False
			button_dump_report = None
			dumpinfo_file = ""
			temp = str(self.SETTINGS.value("GenerateDumpReports", default="disabled")).lower() == "enabled"
			try:
				dump_report = self.CONN.GetDumpReport()
				if dump_report is not False:
					if time_elapsed is not None and speed is not None:
						self.lblStatus2aResult.setText(speed)
						dump_report = dump_report.replace("%TRANSFER_RATE%", speed)
						dump_report = dump_report.replace("%TIME_ELAPSED%", Util.formatProgressTime(time_elapsed))
					else:
						dump_report = dump_report.replace("%TRANSFER_RATE%", "N/A")
						dump_report = dump_report.replace("%TIME_ELAPSED%", "N/A")
					dumpinfo_file = os.path.splitext(self.STATUS["last_path"])[0] + ".txt"
			except Exception as e:
				print("ERROR: {:s}".format(str(e)))
			
			if dump_report is not False and dumpinfo_file != "" and temp is True:
				try:
					with open(dumpinfo_file, "wb") as f:
						f.write(bytearray([ 0xEF, 0xBB, 0xBF ])) # UTF-8 BOM
						f.write(dump_report.encode("UTF-8"))
					button_dump_report = msgbox.addButton("  Open Dump &Report  ", QtWidgets.QMessageBox.ActionRole)
				except Exception as e:
					print("ERROR: {:s}".format(str(e)))
			else:
				button_dump_report = msgbox.addButton("  Generate Dump &Report  ", QtWidgets.QMessageBox.ActionRole)
			
			if self.CONN.GetMode() == "DMG":
				if self.CONN.INFO["rom_checksum"] == self.CONN.INFO["rom_checksum_calc"]:
					self.lblHeaderROMChecksumResult.setText("Valid (0x{:04X})".format(self.CONN.INFO["rom_checksum"]))
					self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }")
					self.lblStatus4a.setText("Done!")
					msg = "The ROM backup is complete and the checksum was verified successfully!"
					msgbox.setText(msg + msg_te)
					msgbox.exec()
				else:
					self.lblStatus4a.setText("Done.")
					if ("cart_type" in self.STATUS and "dmg-mmsa-jpn" in self.STATUS["cart_type"]) or ("mapper_raw" in self.CONN.INFO and self.CONN.INFO["mapper_raw"] in (0x105, 0x202, 0x203, 0x205)):
						msg = "The ROM backup is complete."
						msgbox.setText(msg + msg_te)
						msgbox.exec()
					else:
						self.lblHeaderROMChecksumResult.setText("Invalid (0x{:04X}≠0x{:04X})".format(self.CONN.INFO["rom_checksum_calc"], self.CONN.INFO["rom_checksum"]))
						self.lblHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }")
						msg = "The ROM was dumped, but the checksum is not correct."
						button_gmmc1 = None
						if self.CONN.INFO["loop_detected"] is not False:
							msg += "\n\nA data loop was detected in the ROM backup at position 0x{:X} ({:s}). This may indicate a bad dump or overdump.".format(self.CONN.INFO["loop_detected"], Util.formatFileSize(self.CONN.INFO["loop_detected"], asInt=True))
						else:
							msg += " This may indicate a bad dump, however this can be normal for some reproduction cartridges, unlicensed games, prototypes, patched games and intentional overdumps."
							if self.CONN.GetMode() == "DMG" and (list(Util.DMG_Header_Mapper.items())[self.cmbHeaderMapperResult.currentIndex()])[0] in (1, 2, 3): # If MBC1
								msg += "\n\nIf this is a NP GB-Memory Cartridge, please use the “Retry as G-MMC1” button."
								button_gmmc1 = msgbox.addButton("  Retry as G-MMC1  ", QtWidgets.QMessageBox.ActionRole)
						msgbox.setText(msg + msg_te)
						msgbox.setIcon(QtWidgets.QMessageBox.Warning)
						msgbox.exec()
						if msgbox.clickedButton() == button_gmmc1:
							if self.CheckDeviceAlive():
								mappers = list(Util.DMG_Header_Mapper.keys())
								for i in range(0, len(mappers)):
									if mappers[i] == 0x105:
										self.cmbHeaderMapperResult.setCurrentIndex(i)
								cart_type = 0
								cart_types = self.CONN.GetSupportedCartridgesDMG()
								for i in range(0, len(cart_types[0])):
									if "dmg-mmsa-jpn" in cart_types[1][i]:
										self.cmbDMGCartridgeTypeResult.setCurrentIndex(i)
										cart_type = i
								self.STATUS["args"]["mbc"] = 0x105
								self.STATUS["args"]["rom_size"] = 1048576
								self.STATUS["args"]["cart_type"] = cart_type
								self.STATUS["time_start"] = time.time()
								QtCore.QTimer.singleShot(1, lambda: [ self.CONN.BackupROM(fncSetProgress=self.PROGRESS.SetProgress, args=self.STATUS["args"]) ])
								return
			elif self.CONN.GetMode() == "AGB":
				if Util.AGB_Global_CRC32 == self.CONN.INFO["rom_checksum_calc"]:
					self.lblAGBHeaderROMChecksumResult.setText("Valid (0x{:06X})".format(Util.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: green; }")
					self.lblStatus4a.setText("Done!")
					msg = "The ROM backup is complete and the checksum was verified successfully!"
					msgbox.setText(msg + msg_te)
					msgbox.exec()
				elif Util.AGB_Global_CRC32 == 0:
					self.lblAGBHeaderROMChecksumResult.setText("0x{:06X}".format(self.CONN.INFO["rom_checksum_calc"]))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
					self.lblStatus4a.setText("Done!")
					msg = "The ROM backup is complete! As there is no known checksum for this ROM in the database, verification was skipped."
					if self.CONN.INFO["loop_detected"] is not False:
						msg += "\n\nNOTE: A data loop was detected in the ROM backup at position 0x{:X} ({:s}). This may indicate a bad dump or overdump.".format(self.CONN.INFO["loop_detected"], Util.formatFileSize(self.CONN.INFO["loop_detected"], asInt=True))
						msgbox.setIcon(QtWidgets.QMessageBox.Warning)
					msgbox.setText(msg + msg_te)
					msgbox.exec()
				else:
					self.lblAGBHeaderROMChecksumResult.setText("Invalid (0x{:06X}≠0x{:06X})".format(self.CONN.INFO["rom_checksum_calc"], Util.AGB_Global_CRC32))
					self.lblAGBHeaderROMChecksumResult.setStyleSheet("QLabel { color: red; }")
					self.lblStatus4a.setText("Done.")
					msg = "The ROM backup is complete, but the checksum doesn’t match the known database entry."
					if self.CONN.INFO["loop_detected"] is not False:
						msg += "\n\nA data loop was detected in the ROM backup at position 0x{:X} ({:s}). This may indicate a bad dump or overdump.".format(self.CONN.INFO["loop_detected"], Util.formatFileSize(self.CONN.INFO["loop_detected"], asInt=True))
					else:
						msg += " This may indicate a bad dump, however this can be normal for some reproduction cartridges, unlicensed games, prototypes, patched games and intentional overdumps."
					msgbox.setText(msg + msg_te)
					msgbox.setIcon(QtWidgets.QMessageBox.Warning)
					msgbox.exec()
			
			if msgbox.clickedButton() == button_dump_report:
				if not (dump_report is not False and dumpinfo_file != "" and temp is True):
					try:
						with open(dumpinfo_file, "wb") as f:
							f.write(bytearray([ 0xEF, 0xBB, 0xBF ])) # UTF-8 BOM
							f.write(dump_report.encode("UTF-8"))
					except Exception as e:
						print("ERROR: {:s}".format(str(e)))
				self.OpenPath(dumpinfo_file)
		
		elif self.CONN.INFO["last_action"] == 2: # Backup RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0

			dontShowAgainCameraSavePopup = str(self.SETTINGS.value("SkipCameraSavePopup", default="disabled")).lower() == "enabled"
			if not dontShowAgainCameraSavePopup:
				if self.CONN.GetMode() == "DMG" and self.CONN.INFO["mapper_raw"] == 252 and self.CONN.INFO["transferred"] == 131072: # Pocket Camera / 128 KB
					cbCameraSavePopup = QtWidgets.QCheckBox("Don’t show this message again", checked=dontShowAgain)
					msgboxCameraPopup = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="Would you like to load your save data with the GB Camera Viewer now?")
					msgboxCameraPopup.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
					msgboxCameraPopup.setDefaultButton(QtWidgets.QMessageBox.Yes)
					msgboxCameraPopup.setCheckBox(cbCameraSavePopup)
					answer = msgboxCameraPopup.exec()
					dontShowAgainCameraSavePopup = cbCameraSavePopup.isChecked()
					if dontShowAgainCameraSavePopup: self.SETTINGS.setValue("SkipCameraSavePopup", "enabled")
					if answer == QtWidgets.QMessageBox.Yes:
						self.CAMWIN = None
						self.CAMWIN = PocketCameraWindow(self, icon=self.windowIcon(), file=self.CONN.INFO["last_path"], config_path=Util.CONFIG_PATH)
						self.CAMWIN.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
						self.CAMWIN.setModal(True)
						self.CAMWIN.run()
						return
			
			msgbox.setText("The save data backup is complete!" + msg_te)
			msgbox.exec()
		
		elif self.CONN.INFO["last_action"] == 3: # Restore RAM
			self.lblStatus4a.setText("Done!")
			self.CONN.INFO["last_action"] = 0
			if "save_erase" in self.CONN.INFO and self.CONN.INFO["save_erase"]:
				msg_text = "The save data was erased."
				del(self.CONN.INFO["save_erase"])
			elif "verified" in self.PROGRESS.PROGRESS and self.PROGRESS.PROGRESS["verified"] == True:
				msg_text = "The save data was written and verified successfully!"
			else:
				msg_text = "Save data writing complete!"
			msgbox.setText(msg_text + msg_te)
			msgbox.exec()
		
		elif self.CONN.INFO["last_action"] == 4: # Flash ROM
			if "broken_sectors" in self.CONN.INFO:
				s = ""
				for sector in self.CONN.INFO["broken_sectors"]: s += "0x{:X}~0x{:X}, ".format(sector[0], sector[0]+sector[1]-1)
				answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The ROM was written completely, but verification of written data failed in the following sector(s): {:s}.\n\nDo you want to try and write the sectors again that failed verification?".format(s[:-2]), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
				if answer == QtWidgets.QMessageBox.Yes:
					args = self.STATUS["args"]
					args.update({"flash_sectors":self.CONN.INFO["broken_sectors"]})
					self.CONN.FlashROM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
					return
			
			self.CONN.INFO["last_action"] = 0
			self.lblStatus4a.setText("Done!")
			if "verified" in self.PROGRESS.PROGRESS and self.PROGRESS.PROGRESS["verified"] == True:
				msg = "The ROM was written and verified successfully!"
			else:
				msg = "ROM writing complete!"

			msgbox.setText(msg + msg_te)
			msgbox.exec()
			
			if self.CONN.GetMode() == "AGB" and "Batteryless SRAM" in Util.AGB_Header_Save_Types[self.cmbAGBSaveTypeResult.currentIndex()]:
				temp1 = self.cmbAGBCartridgeTypeResult.currentIndex()
				temp2 = self.cmbAGBSaveTypeResult.currentIndex()
				temp3 = self.CONN.INFO["dump_info"]["batteryless_sram"]
				self.ReadCartridge(resetStatus=False)
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(temp1)
				self.cmbAGBSaveTypeResult.setCurrentIndex(temp2)
				self.CONN.INFO["dump_info"]["batteryless_sram"] = temp3
			else:
				self.ReadCartridge(resetStatus=False)
			# self.STATUS["operation"] = None

		else:
			self.lblStatus4a.setText("Ready.")
			self.CONN.INFO["last_action"] = 0

		if dontShowAgain: self.SETTINGS.setValue("SkipFinishMessage", "enabled")
		self.SetProgressBars(min=0, max=1, value=1)

	def DMGMapperTypeChanged(self, index):
		if index in (-1, 0): return
	
	def SetDMGMapperResult(self, cart_type):
		mappers = list(Util.DMG_Header_Mapper.keys())
		mbc = 0
		if "mbc" in cart_type:
			if isinstance(cart_type["mbc"], int):
				mbc = cart_type["mbc"]
			elif self.cmbHeaderMapperResult.currentIndex() > 0:
				mbc = mappers[self.cmbHeaderMapperResult.currentIndex()]
			for i in range(0, len(mappers)):
				if mbc == mappers[i]:
					self.cmbHeaderMapperResult.setCurrentIndex(i)
	
	def CartridgeTypeChanged(self, index):
		self.STATUS["cart_type"] = {}
		if index in (-1, 0): return
		if self.CONN.GetMode() == "DMG":
			cart_types = self.CONN.GetSupportedCartridgesDMG()
			if cart_types[1][index] == "RETAIL": # special keyword
				pass
			else:
				if "flash_size" in cart_types[1][index] and not "dmg-mmsa-jpn" in cart_types[1][index]:
					for i in range(0, len(Util.DMG_Header_ROM_Sizes_Flasher_Map)):
						if cart_types[1][index]["flash_size"] == (Util.DMG_Header_ROM_Sizes_Flasher_Map[i]):
							self.cmbHeaderROMSizeResult.setCurrentIndex(i)
				self.STATUS["cart_type"] = cart_types[1][index]
				self.SetDMGMapperResult(cart_types[1][index])
		
		elif self.CONN.GetMode() == "AGB":
			cart_types = self.CONN.GetSupportedCartridgesAGB()
			if cart_types[1][index] == "RETAIL": # special keyword
				pass
			else:
				if "flash_size" in cart_types[1][index]:
					self.cmbAGBHeaderROMSizeResult.setCurrentIndex(Util.AGB_Header_ROM_Sizes_Map.index(cart_types[1][index]["flash_size"]))
				self.STATUS["cart_type"] = cart_types[1][index]
	
	def CheckHeader(self):
		data = self.CONN.INFO["dump_info"]["header"]
		if not (self.CONN.GetMode() == "DMG" and data["mapper_raw"] in (0x203, 0x204, 0x205)) and not data['logo_correct'] and not data["header_checksum_correct"] and data['empty'] == False:
			msg = "ROM header checksum and boot logo checks failed. Please ensure that the cartridge contacts are clean.\n\nDo you still want to continue?"
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
			if answer == QtWidgets.QMessageBox.No: return False
		return True
	
	def BackupROM(self):
		if not self.CheckDeviceAlive(): return
		if not self.CheckHeader(): return
		
		mbc = (list(Util.DMG_Header_Mapper.items())[self.cmbHeaderMapperResult.currentIndex()])[0]
		
		rom_size = 0
		cart_type = 0
		path = Util.GenerateFileName(mode=self.CONN.GetMode(), header=self.CONN.INFO, settings=self.SETTINGS)
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirRomDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)

			path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy ROM File (*.gb *.sgb *.gbc);;All Files (*.*)")[0]
			cart_type = self.cmbDMGCartridgeTypeResult.currentIndex()
			rom_size = Util.DMG_Header_ROM_Sizes_Flasher_Map[self.cmbHeaderROMSizeResult.currentIndex()]
		
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirRomAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)

			rom_size = Util.AGB_Header_ROM_Sizes_Map[self.cmbAGBHeaderROMSizeResult.currentIndex()]
			path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup ROM", last_dir + "/" + path, "Game Boy Advance ROM File (*.gba *.srl);;All Files (*.*)")[0]
			cart_type = self.cmbAGBCartridgeTypeResult.currentIndex()
		
		if (path == ""): return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))
		self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
		self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
		
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		self.btnTools.setEnabled(False)
		self.btnConfig.setEnabled(False)
		self.lblStatus4a.setText("Preparing...")
		qt_app.processEvents()
		args = { "path":path, "mbc":mbc, "rom_size":rom_size, "agb_rom_size":rom_size, "fast_read_mode":True, "cart_type":cart_type }
		self.CONN.BackupROM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
		self.grpStatus.setTitle("Transfer Status")
		self.STATUS["time_start"] = time.time()
		self.STATUS["last_path"] = path
		self.STATUS["args"] = args
	
	def FlashROM(self, dpath=""):
		if not self.CheckDeviceAlive(): return
		
		just_erase = False
		path = ""
		if dpath != "":
			ext = os.path.splitext(dpath)[1]
			if ext.lower() == ".isx":
				text = "The following ISX file will now be converted to a regular ROM file and then written to the flash cartridge:\n" + dpath
			else:
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
			cart_type = self.DetectCartridge(canSkipMessage=True)
			if cart_type is False: # clicked Cancel button
				return
			elif cart_type is None or cart_type == 0:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "A compatible flash cartridge type could not be auto-detected.", QtWidgets.QMessageBox.Ok)
				return
			
			if self.CONN.GetMode() == "DMG":
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
			elif self.CONN.GetMode() == "AGB":
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)
		
		if self.CONN.GetMode() == "DMG":
			self.SetDMGMapperResult(carts[cart_type])
			mbc = (list(Util.DMG_Header_Mapper.items())[self.cmbHeaderMapperResult.currentIndex()])[0]
		else:
			mbc = 0
		
		if (path == ""):
			if self.CONN.GetMode() == "DMG":
				path = QtWidgets.QFileDialog.getOpenFileName(self, "Write ROM", last_dir, "Game Boy ROM File (*.gb *.gbc *.sgb *.bin *.isx);;All Files (*.*)")[0]
			elif self.CONN.GetMode() == "AGB":
				path = QtWidgets.QFileDialog.getOpenFileName(self, "Write ROM", last_dir, "Game Boy Advance ROM File (*.gba *.srl *.bin);;All Files (*.*)")[0]
		
		if (path == ""):
			msg = "No ROM file was selected. Do you want to wipe the ROM contents of the cartridge instead?"
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
			if answer == QtWidgets.QMessageBox.No: return
			just_erase = True
			path = False
			buffer = bytearray()
		
		if not just_erase:
			self.SETTINGS.setValue(setting_name, os.path.dirname(path))
			if os.path.getsize(path) == 0:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The selected ROM file is empty.", QtWidgets.QMessageBox.Ok)
				return
			if os.path.getsize(path) > 0x10000000: # reject too large files to avoid exploding RAM
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "ROM files bigger than 256 MB are not supported.", QtWidgets.QMessageBox.Ok)
				return
			
			with open(path, "rb") as file:
				ext = os.path.splitext(path)[1]
				if ext.lower() == ".isx":
					buffer = bytearray(file.read())
					buffer = Util.isx2bin(buffer)
				else:
					buffer = bytearray(file.read(0x1000))
			rom_size = os.stat(path).st_size
			if "flash_size" in carts[cart_type]:
				if rom_size > carts[cart_type]['flash_size']:
					msg = "The selected flash cartridge type seems to support ROMs that are up to {:s} in size, but the file you selected is {:s}.".format(Util.formatFileSize(carts[cart_type]['flash_size']), Util.formatFileSize(os.path.getsize(path), roundUp=True))
					msg += " You can still give it a try, but it’s possible that it’s too large which may cause the ROM writing to fail."
					answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), msg, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
					if answer == QtWidgets.QMessageBox.Cancel: return
			#if "mbc" in carts[cart_type]:
			#	mbc = carts[cart_type]["mbc"]
		
		override_voltage = False
		if 'voltage_variants' in carts[cart_type] and carts[cart_type]['voltage'] == 3.3:
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="Some cartridges of this type can be flashed at 3.3V, others may require 5V. Which mode should be used?")
			button_3_3v = msgbox.addButton("Use &3.3V", QtWidgets.QMessageBox.ActionRole)
			button_5v = msgbox.addButton("Use &5V", QtWidgets.QMessageBox.ActionRole)
			button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
			msgbox.setDefaultButton(button_3_3v)
			msgbox.setEscapeButton(button_cancel)
			answer = msgbox.exec()
			if msgbox.clickedButton() == button_5v:
				override_voltage = 5
			elif msgbox.clickedButton() == button_cancel: return
		
		prefer_chip_erase = self.SETTINGS.value("PreferChipErase", default="disabled")
		if prefer_chip_erase and prefer_chip_erase.lower() == "enabled":
			prefer_chip_erase = True
		else:
			prefer_chip_erase = False

		verify_write = self.SETTINGS.value("VerifyData", default="enabled")
		if verify_write and verify_write.lower() == "enabled":
			verify_write = True
		else:
			verify_write = False
		
		fix_header = False
		if not just_erase and len(buffer) >= 0x1000:
			if self.CONN.GetMode() == "DMG":
				hdr = RomFileDMG(buffer).GetHeader()

				if not Util.compare_mbc(hdr["mapper_raw"], mbc):
					mbc1 = Util.get_mbc_name(mbc)
					mbc2 = Util.get_mbc_name(hdr["mapper_raw"])
					compatible_mbc = [ "None", "MBC2", "MBC3", "MBC5", "MBC7", "GBD", "G-MMC1", "HuC-1", "HuC-3" ]
					if (mbc2 == "None") or (mbc1 == "G-MMC1" and mbc2 == "MBC1") or (mbc2 == "G-MMC1" and mbc1 == "MBC1"):
						pass
					elif mbc2 != "None" and not (mbc1 in compatible_mbc and mbc2 in compatible_mbc):
						if "mbc" in carts[cart_type] and carts[cart_type]["mbc"] == "manual":
							msg_text = "The ROM file you selected uses a different mapper type than your current selection. What mapper should be used when writing the ROM?\n\nSelected mapper type: {:s}\nROM mapper type: {:s}".format(mbc1, mbc2)
							msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg_text)
							if mbc == 0: mbc1 = "MBC5"
							button_1 = msgbox.addButton("  {:s}  ".format(mbc1), QtWidgets.QMessageBox.ActionRole)
							button_2 = msgbox.addButton("  {:s}  ".format(mbc2), QtWidgets.QMessageBox.ActionRole)
							button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
							msgbox.setDefaultButton(button_1)
							msgbox.setEscapeButton(button_cancel)
							msgbox.exec()
							if msgbox.clickedButton() == button_cancel:
								return
							elif msgbox.clickedButton() == button_2:
								mbc = hdr["mapper_raw"]
						else:
							if mbc1 == "None": mbc1 = "None/Unknown"
							msg_text = "Warning: The ROM file you selected uses a different mapper type than your cartridge type. The ROM file may be incompatible with your cartridge.\n\nSelected mapper type: {:s}\nROM mapper type: {:s}".format(mbc1, mbc2)
							answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), msg_text, QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
							if answer == QtWidgets.QMessageBox.Cancel: return
			elif self.CONN.GetMode() == "AGB":
				hdr = RomFileAGB(buffer).GetHeader()
			
			if not hdr["logo_correct"] and (self.CONN.GetMode() == "AGB" or (self.CONN.GetMode() == "DMG" and mbc not in (0x203, 0x205))):
				answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "Warning: The ROM file you selected will not boot on actual hardware due to invalid logo data.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
				if answer == QtWidgets.QMessageBox.Cancel: return
			if not hdr["header_checksum_correct"] and (self.CONN.GetMode() == "AGB" or (self.CONN.GetMode() == "DMG" and mbc not in (0x203, 0x205))):
				msg_text = "Warning: The ROM file you selected will not boot on actual hardware due to an invalid header checksum (expected 0x{:02X} instead of 0x{:02X}).".format(hdr["header_checksum_calc"], hdr["header_checksum"])
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg_text)
				button_1 = msgbox.addButton("  &Fix and Continue  ", QtWidgets.QMessageBox.ActionRole)
				button_2 = msgbox.addButton("  Continue &without fixing  ", QtWidgets.QMessageBox.ActionRole)
				button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
				msgbox.setDefaultButton(button_1)
				msgbox.setEscapeButton(button_cancel)
				msgbox.exec()
				if msgbox.clickedButton() == button_1:
					fix_header = True
				elif msgbox.clickedButton() == button_cancel:
					return
				elif msgbox.clickedButton() == button_2:
					pass
		
		# flash_offset = self.PROGRESS.GetLastPosition()
		# if flash_offset > 0:
		# 	answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "The previous Write ROM operation seems to have been interrupted. Do you want to resume from address 0x{:X}?".format(flash_offset), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Yes)
		# 	if answer == QtWidgets.QMessageBox.No:
		# 		flash_offset = 0
		# 	elif answer == QtWidgets.QMessageBox.Cancel:
		# 		return
		# self.PROGRESS.ResetLastPosition()
		flash_offset = 0
		
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		self.btnTools.setEnabled(False)
		self.btnConfig.setEnabled(False)
		self.lblStatus4a.setText("Preparing...")
		qt_app.processEvents()
		if len(buffer) > 0x1000 or just_erase:
			if just_erase:
				prefer_chip_erase = True
				verify_write = False
			args = { "path":"", "buffer":buffer, "cart_type":cart_type, "override_voltage":override_voltage, "prefer_chip_erase":prefer_chip_erase, "fast_read_mode":True, "verify_write":verify_write, "fix_header":fix_header, "mbc":mbc }
		else:
			args = { "path":path, "cart_type":cart_type, "override_voltage":override_voltage, "prefer_chip_erase":prefer_chip_erase, "fast_read_mode":True, "verify_write":verify_write, "fix_header":fix_header, "mbc":mbc, "flash_offset":flash_offset }
		self.CONN.FlashROM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
		self.grpStatus.setTitle("Transfer Status")
		buffer = None
		self.STATUS["time_start"] = time.time()
		self.STATUS["last_path"] = path
		self.STATUS["args"] = args
	
	def BackupRAM(self):
		if not self.CheckDeviceAlive(): return
		
		rtc = False
		features = []
		add_date_time = self.SETTINGS.value("SaveFileNameAddDateTime", default="disabled")
		path_datetime = ""
		if add_date_time and add_date_time.lower() == "enabled":
			path_datetime = "_{:s}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
		
		path = Util.GenerateFileName(mode=self.CONN.GetMode(), header=self.CONN.INFO, settings=self.SETTINGS)
		path = os.path.splitext(path)[0]
		path += "{:s}.sav".format(path_datetime)
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			mbc = (list(Util.DMG_Header_Mapper.items())[self.cmbHeaderMapperResult.currentIndex()])[0]
			try:
				features = list(Util.DMG_Header_Mapper.keys())[self.cmbHeaderMapperResult.currentIndex()]
			except:
				features = []
			save_type = Util.DMG_Header_RAM_Sizes_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "No save type was selected.", QtWidgets.QMessageBox.Ok)
				return
			#save_size = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(save_type)]
		
		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			mbc = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "No save type was selected.", QtWidgets.QMessageBox.Ok)
				return
			#save_size = Util.AGB_Header_Save_Sizes[save_type]
		else:
			return
		
		if not self.CheckHeader(): return
		path = QtWidgets.QFileDialog.getSaveFileName(self, "Backup Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
		if (path == ""): return

		verify_read = self.SETTINGS.value("VerifyData", default="enabled")
		if verify_read and verify_read.lower() == "enabled":
			verify_read = True
		else:
			verify_read = False
		
		rtc = False
		if self.CONN.INFO["has_rtc"]: # features in (0x10, 0xFD, 0xFE): # RTC of MBC3, TAMA5, HuC-3
			if self.CONN.GetMode() == "DMG" and features == 0x10 and not self.CONN.IsClkConnected():
				rtc = False
			else:
				msg = "A Real Time Clock cartridge was detected. Do you want the cartridge’s Real Time Clock register values also to be saved?"
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
				msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
				answer = msgbox.exec()
				if answer == QtWidgets.QMessageBox.Cancel: return
				rtc = (answer == QtWidgets.QMessageBox.Yes)

		bl_args = {}
		if self.CONN.GetMode() == "AGB" and self.cmbAGBSaveTypeResult.currentIndex() < len(Util.AGB_Header_Save_Types) and "Batteryless SRAM" in Util.AGB_Header_Save_Types[self.cmbAGBSaveTypeResult.currentIndex()]:
			if self.CONN.GetFWBuildDate() == "": # Legacy Mode
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="This feature is not supported in Legacy Mode.", standardButtons=QtWidgets.QMessageBox.Ok)
				msgbox.exec()
				return
			cart_type = self.cmbAGBCartridgeTypeResult.currentIndex()
			if cart_type == 0 or ("dump_info" not in self.CONN.INFO or "batteryless_sram" not in self.CONN.INFO["dump_info"]):
				cart_type = self.DetectCartridge()
				if cart_type is False: # clicked Cancel button
					return
				elif cart_type is None or cart_type == 0:
					QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "A compatible flash cartridge type could not be auto-detected.", QtWidgets.QMessageBox.Ok)
					return
				self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)

			if "dump_info" in self.CONN.INFO and "batteryless_sram" in self.CONN.INFO["dump_info"]:
				detected = self.CONN.INFO["dump_info"]["batteryless_sram"]
			else:
				detected = False
			bl_args = self.GetBLArgs(rom_size=Util.AGB_Header_ROM_Sizes_Map[self.cmbAGBHeaderROMSizeResult.currentIndex()], detected=detected)
			if bl_args is False: return
		
		self.SETTINGS.setValue(setting_name, os.path.dirname(path))

		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		self.btnTools.setEnabled(False)
		self.btnConfig.setEnabled(False)
		self.lblStatus4a.setText("Preparing...")
		qt_app.processEvents()

		if len(bl_args) > 0:
			args = { "path":path, "mbc":mbc, "rom_size":bl_args["bl_size"], "agb_rom_size":bl_args["bl_size"], "fast_read_mode":True, "cart_type":cart_type }
			args.update(bl_args)
			self.CONN.BackupROM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
		else:
			args = { "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc, "verify_read":verify_read }
			self.CONN.BackupRAM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
		
		self.grpStatus.setTitle("Transfer Status")
		self.STATUS["time_start"] = time.time()
		self.STATUS["last_path"] = path
		self.STATUS["args"] = args

	def WriteRAM(self, dpath="", erase=False, test=False):
		if not self.CheckDeviceAlive(): return
		
		features = 0
		
		if dpath == "":
			path = Util.GenerateFileName(mode=self.CONN.GetMode(), header=self.CONN.INFO, settings=self.SETTINGS)
			path = os.path.splitext(path)[0]
			path += ".sav"
		
		if self.CONN.GetMode() == "DMG":
			setting_name = "LastDirSaveDataDMG"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			mbc = (list(Util.DMG_Header_Mapper.items())[self.cmbHeaderMapperResult.currentIndex()])[0]
			try:
				features = list(Util.DMG_Header_Mapper.keys())[self.cmbHeaderMapperResult.currentIndex()]
			except:
				features = []
			save_type = Util.DMG_Header_RAM_Sizes_Map[self.cmbHeaderRAMSizeResult.currentIndex()]
			if save_type == 0:
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "No save type was selected.", QtWidgets.QMessageBox.Ok)
				return
			save_size = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(save_type)]

		elif self.CONN.GetMode() == "AGB":
			setting_name = "LastDirSaveDataAGB"
			last_dir = self.SETTINGS.value(setting_name)
			if last_dir is None: last_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
			mbc = 0
			save_type = self.cmbAGBSaveTypeResult.currentIndex()
			if save_type == 0:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "No save type was selected.", QtWidgets.QMessageBox.Ok)
				return
			save_size = Util.AGB_Header_Save_Sizes[save_type]
		else:
			return
		if not self.CheckHeader(): return
		
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
		elif test:
			path = None
			if self.CONN.GetFWBuildDate() == "": # Legacy Mode
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="This feature is not supported in Legacy Mode.", standardButtons=QtWidgets.QMessageBox.Ok)
				msgbox.exec()
				return
			elif not self.CONN.CanPowerCycleCart():
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="This feature only works with newer GBxCart RW hardware revisions.", standardButtons=QtWidgets.QMessageBox.Ok)
				msgbox.exec()
				return

			if self.CONN.GetMode() == "AGB" and self.cmbAGBSaveTypeResult.currentIndex() < len(Util.AGB_Header_Save_Types) and "Batteryless SRAM" in Util.AGB_Header_Save_Types[self.cmbAGBSaveTypeResult.currentIndex()]:
				QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "Stress test is not supported for this save type.", QtWidgets.QMessageBox.Ok)
				return
			answer = QtWidgets.QMessageBox.question(self, "{:s} {:s}".format(APPNAME, VERSION), "The cartridge’s save chip will be tested for potential problems as follows:\n- Read the same data multiple times\n- Writing and reading different test patterns\n\nPlease ensure the cartridge pins are freshly cleaned and the save data is backed up before proceeding.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Ok)
			if answer == QtWidgets.QMessageBox.Cancel: return
		else:
			path = QtWidgets.QFileDialog.getOpenFileName(self, "Restore Save Data", last_dir + "/" + path, "Save Data File (*.sav);;All Files (*.*)")[0]
			if not path == "": self.SETTINGS.setValue(setting_name, os.path.dirname(path))
			if (path == ""): return
		
		if not erase and not test:
			filesize = os.path.getsize(path)
			if filesize == 0 or filesize > 0x200000: # reject too large files to avoid exploding RAM
				QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The size of this file is not supported.", QtWidgets.QMessageBox.Ok)
				return
		
		verify_write = self.SETTINGS.value("VerifyData", default="enabled")
		if verify_write and verify_write.lower() == "enabled":
			verify_write = True
		else:
			verify_write = False
		
		rtc = False
		rtc_advance = False
		if not test and self.CONN.INFO["has_rtc"]: # features in (0x10, 0xFD, 0xFE): # RTC of MBC3, TAMA5, HuC-3
			if self.CONN.GetMode() == "DMG" and features == 0x10 and not self.CONN.IsClkConnected():
				rtc = False
			elif (self.CONN.GetMode() == "DMG" and ((features == 0xFD and (filesize == save_size + 0x28 or erase)) or (features == 0xFE and (filesize == save_size + 0xC or erase)) or (self.CONN.IsClkConnected() and features == 0x10 and filesize == save_size + 0x30 or erase))) or \
			     (self.CONN.GetMode() == "AGB" and (filesize == save_size + 0x10 or erase)):
				msg = "A Real Time Clock cartridge was detected. Do you want the Real Time Clock register values to be also written?"
				cb = QtWidgets.QCheckBox("&Adjust RTC", checked=True)
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Question, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg, standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
				msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
				if erase:
					cb.setChecked(True)
				else:
					msgbox.setCheckBox(cb)
				answer = msgbox.exec()
				if answer == QtWidgets.QMessageBox.Cancel: return
				rtc_advance = cb.isChecked()
				rtc = (answer == QtWidgets.QMessageBox.Yes)

		if test:
			self.grpDMGCartridgeInfo.setEnabled(False)
			self.grpAGBCartridgeInfo.setEnabled(False)
			self.grpActions.setEnabled(False)
			self.btnTools.setEnabled(False)
			self.btnConfig.setEnabled(False)
			self.lblStatus4a.setText("Preparing...")
			self.grpStatus.setTitle("Transfer Status")
			self.lblStatus1aResult.setText("–")
			self.lblStatus2aResult.setText("–")
			self.lblStatus3aResult.setText("–")
			self.lblStatus4aResult.setText("")
			qt_app.processEvents()
			
			test_patterns = [
				bytearray(os.urandom(128*1024)),
				bytearray([ 0x00, 0x00, 0x00, 0x00 ] * 32768),
				bytearray([ 0x55, 0xAA, 0xAA, 0x55 ] * 32768),
				bytearray([ 0x00, 0xFF, 0xFF, 0x00 ] * 32768),
				bytearray([ 0xFF, 0xFF, 0xFF, 0xFF ] * 32768),
			]
			inc = bytearray()
			dec = bytearray()
			for i in range(0, 256):
				inc.append(i)
				dec.append(255-i)
			test_patterns.append(inc)
			test_patterns.append(dec)

			if Util.get_mbc_name(mbc) == "MBC2":
				for j in range(0, len(test_patterns)):
					for i in range(0, len(test_patterns[j])):
						test_patterns[j][i] = test_patterns[j][i] & 0x0F
			
			test_patterns_names = [
				"reading twice",
				"writing random values",
				"writing 00, 00, 00, 00",
				"writing 55, AA, AA, 55",
				"writing 00, FF, FF, 00",
				"writing FF, FF, FF, FF",
				"writing incrementing values",
				"writing decrementing values",
			]
			#if Util.DEBUG: test_patterns = [ test_patterns[0], test_patterns[1], test_patterns[4] ]
			
			time_start = time.time()
			test_ok = 0
			save1 = bytearray([0])
			save2 = bytearray([1])
			backup_fn = Util.CONFIG_PATH + "/backup_test_{:s}.sav".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
			
			try:
				self.lblStatus4a.setText("Testing ({:s} 1/2)...".format(test_patterns_names[0]))
				self.SetProgressBars(min=0, max=len(test_patterns)+3, value=0)
				qt_app.processEvents()
				args = { "mode":2, "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc }
				t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
				t.start()
				while t.is_alive():
					qt_app.processEvents()
					time.sleep(0.02)
				t.join()
				save1 = self.CONN.INFO["data"]
				if self.CONN.CanPowerCycleCart():
					self.CONN.CartPowerOff()
					self.SetProgressBars(min=0, max=len(test_patterns)+3, value=1)
					for i in range(5, 0, -1):
						self.lblStatus4a.setText("Waiting for power cycle ({:d})...".format(i))
						qt_app.processEvents()
						time.sleep(1)
					self.CONN.CartPowerOn()
				else:
					time.sleep(1)
				self.lblStatus4a.setText("Testing ({:s} 2/2)...".format(test_patterns_names[0]))
				qt_app.processEvents()
				t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
				t.start()
				while t.is_alive():
					qt_app.processEvents()
					time.sleep(0.02)
				t.join()
				save2 = self.CONN.INFO["data"]
			except:
				save1 = None
			
			if save1 is not None and save1 == save2:
				with open(backup_fn, "wb") as f: f.write(save1)
				test_ok += 1
				for i in range(0, len(test_patterns)):
					self.lblStatus4a.setText("Testing ({:s})...".format(test_patterns_names[i+1]))
					self.SetProgressBars(min=0, max=len(test_patterns)+3, value=i+2)
					qt_app.processEvents()
					towrite = test_patterns[i]
					args = { "mode":3, "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc, "rtc_advance":rtc_advance, "erase":erase, "verify_write":False, "buffer":towrite }
					t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
					t.start()
					while t.is_alive():
						qt_app.processEvents()
						time.sleep(0.02)
					t.join()
					if i == 0:
						self.CONN.CartPowerOff()
						time.sleep(0.5)
						self.CONN.CartPowerOn()
					args = { "mode":2, "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc }
					t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
					t.start()
					while t.is_alive():
						qt_app.processEvents()
						time.sleep(0.02)
					t.join()
					readback = self.CONN.INFO["data"]
					if towrite[:len(readback)] != readback:
						break
					test_ok += 1
				
				self.lblStatus4a.setText("Restoring original save data...")
				self.SetProgressBars(min=0, max=len(test_patterns)+3, value=len(test_patterns)+2)
				qt_app.processEvents()
				args = { "mode":3, "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc, "rtc_advance":rtc_advance, "erase":erase, "verify_write":False, "buffer":save1 }
				t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
				t.start()
				while t.is_alive():
					qt_app.processEvents()
					time.sleep(0.02)
				t.join()
				args = { "mode":2, "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc }
				t = threading.Thread(target=lambda a: self.CONN.TransferData(args=a, signal=None), args=[args])
				t.start()
				while t.is_alive():
					qt_app.processEvents()
					time.sleep(0.02)
				t.join()
				save3 = self.CONN.INFO["data"]
				if save3 == save2:
					if os.path.exists(backup_fn):
						os.unlink(backup_fn)
			
			time_elapsed = time.time() - time_start
			msg_te = "\n\nTotal time elapsed: {:s}".format(Util.formatProgressTime(time_elapsed, asFloat=True))

			self.SetProgressBars(min=0, max=100, value=100)
			self.lblStatus4a.setText("Done.")
			qt_app.processEvents()
			if test_ok == len(test_patterns)+1:
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="All tests completed successfully!" + msg_te, standardButtons=QtWidgets.QMessageBox.Ok)
			else:
				try:
					if test_ok == 0:
						towrite = save1
						readback = save2
					with open("debug_savetest_1.bin", "wb") as f: f.write(towrite[:len(readback)])
					with open("debug_savetest_2.bin", "wb") as f: f.write(readback)
				except:
					pass
				msg = "Test {:d} ({:s}) failed!".format(test_ok+1, test_patterns_names[test_ok])
				if test_ok == 0:
					if self.CONN.GetMode() == "DMG" or self.CONN.GetMode() == "AGB" and save_type in (3, 7, 8):
						msg += "\nNote: SRAM requires a working battery to retain save data."
				msg += msg_te
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=msg, standardButtons=QtWidgets.QMessageBox.Ok)
			msgbox.exec()
			
			self.grpDMGCartridgeInfo.setEnabled(True)
			self.grpAGBCartridgeInfo.setEnabled(True)
			self.grpActions.setEnabled(True)
			self.btnTools.setEnabled(True)
			self.btnConfig.setEnabled(True)
			
			if not self.CONN.IsConnected(): self.DisconnectDevice()

		else:
			bl_args = {}
			if self.CONN.GetMode() == "AGB" and self.cmbAGBSaveTypeResult.currentIndex() < len(Util.AGB_Header_Save_Types) and "Batteryless SRAM" in Util.AGB_Header_Save_Types[self.cmbAGBSaveTypeResult.currentIndex()]:
				if self.CONN.GetFWBuildDate() == "": # Legacy Mode
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="This feature is not supported in Legacy Mode.", standardButtons=QtWidgets.QMessageBox.Ok)
					msgbox.exec()
					return
				cart_type = self.cmbAGBCartridgeTypeResult.currentIndex()
				if cart_type == 0 or ("dump_info" not in self.CONN.INFO or "batteryless_sram" not in self.CONN.INFO["dump_info"]):
					cart_type = self.DetectCartridge()
					if cart_type is False: # clicked Cancel button
						return
					elif cart_type is None or cart_type == 0:
						QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "A compatible flash cartridge type could not be auto-detected.", QtWidgets.QMessageBox.Ok)
						return
					self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)

				if "dump_info" in self.CONN.INFO and "batteryless_sram" in self.CONN.INFO["dump_info"]:
					detected = self.CONN.INFO["dump_info"]["batteryless_sram"]
				else:
					detected = False
				bl_args = self.GetBLArgs(rom_size=Util.AGB_Header_ROM_Sizes_Map[self.cmbAGBHeaderROMSizeResult.currentIndex()], detected=detected)
				if bl_args is False: return

				args = { "path":path, "cart_type":cart_type, "override_voltage":False, "prefer_chip_erase":False, "fast_read_mode":True, "verify_write":verify_write, "fix_header":False, "mbc":mbc }
				args.update({"bl_save":True, "flash_offset":bl_args["bl_offset"], "flash_size":bl_args["bl_size"]})
				if erase:
					args["path"] = ""
					args["buffer"] = bytearray([0xFF] * bl_args["bl_size"])
				self.STATUS["args"] = args
				self.CONN.FlashROM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
				#self.CONN._FlashROM(args=args)
			else:
				args = { "path":path, "mbc":mbc, "save_type":save_type, "rtc":rtc, "rtc_advance":rtc_advance, "erase":erase, "verify_write":verify_write }
				self.STATUS["args"] = args
				self.CONN.RestoreRAM(fncSetProgress=self.PROGRESS.SetProgress, args=args)
			self.STATUS["time_start"] = time.time()
			self.STATUS["last_path"] = path
			self.STATUS["args"] = args
			self.grpDMGCartridgeInfo.setEnabled(False)
			self.grpAGBCartridgeInfo.setEnabled(False)
			self.grpActions.setEnabled(False)
			self.btnTools.setEnabled(False)
			self.btnConfig.setEnabled(False)
			self.lblStatus4a.setText("Preparing...")
			self.grpStatus.setTitle("Transfer Status")
			self.lblStatus1aResult.setText("–")
			self.lblStatus2aResult.setText("–")
			self.lblStatus3aResult.setText("–")
			self.lblStatus4aResult.setText("")
			qt_app.processEvents()

	def GetBLArgs(self, rom_size, detected=False):
		locs = [ 0x3C0000, 0x7C0000, 0xFC0000, 0x1FC0000 ]
		lens = [ 0x10000, 0x20000 ]
		temp = self.SETTINGS.value("BatterylessSramLocations{:s}".format(self.CONN.GetMode()), "[]")
		loc_index = None
		len_index = None

		try:
			temp = json.loads(temp)
			locs.extend(temp)
			if detected is not False:
				locs.append(detected["bl_offset"])
			locs = list(set(locs))
			locs.sort()
		except:
			pass
		
		if detected is not False:
			loc_index = locs.index(detected["bl_offset"])
			len_index = lens.index(detected["bl_size"])
			intro_msg = "In order to access Batteryless SRAM save data, its ROM location and size must\nbe specified. The previously detected parameters have been pre-selected.\nPlease adjust if necessary, then click “OK” to continue."
		else:
			intro_msg = "In order to access Batteryless SRAM save data, its ROM location and size must\nbe specified.\n\n⚠️ The required parameters could not be auto-detected.\nPlease enter the ROM location and size manually below."

		try:
			if loc_index is None:
				loc_index = locs.index(int(self.SETTINGS.value("BatterylessSramLastLocation{:s}".format(self.CONN.GetMode()))))
		except:
			pass

		bl_args = {}
		if loc_index is None:
			loc_index = 0
			for l in locs:
				if l + 0x40000 >= rom_size: break
				loc_index += 1
			if loc_index >= len(locs): loc_index = len(locs) - 1
		if len_index is None: len_index = 0

		dlg_args = {
			"title":"Batteryless SRAM Parameters",
			"intro":intro_msg.replace("\n", "<br>"),
			"params": [
				# ID, Type, Value(s), Default Index
				[ "loc", "cmb_e", "Location:", [ "0x{:X}".format(l) for l in locs ], loc_index ],
				[ "len", "cmb", "Size:", [ Util.formatFileSize(s, asInt=True) for s in lens ], len_index ],
			]
		}
		dlg = UserInputDialog(self, icon=self.windowIcon(), args=dlg_args)
		if dlg.exec_() == 1:
			result = dlg.GetResult()
			if result["loc"].currentText() not in [ "0x{:X}".format(l) for l in locs ]:
				try:
					if "0x" in result["loc"].currentText():
						bl_args["bl_offset"] = int(result["loc"].currentText()[2:], 16)
					else:
						bl_args["bl_offset"] = int(result["loc"].currentText(), 16)
				except ValueError:
					bl_args["bl_offset"] = 0
			else:
				bl_args["bl_offset"] = locs[result["loc"].currentIndex()]
			bl_args["bl_size"] = lens[result["len"].currentIndex()]
			
			locs.append(bl_args["bl_offset"])
			self.SETTINGS.setValue("BatterylessSramLocations{:s}".format(self.CONN.GetMode()), json.dumps(locs))
			self.SETTINGS.setValue("BatterylessSramLastLocation{:s}".format(self.CONN.GetMode()), json.dumps(bl_args["bl_offset"]))
			ret = bl_args
		else:
			ret = False
		del(dlg)
		return ret

	def CheckDeviceAlive(self, setMode=False):
		if self.CONN is not None:
			mode = self.CONN.GetMode()
			if self.CONN.DEVICE is not None:
				if not self.CONN.IsConnected():
					self.DisconnectDevice()
					self.CONN = None
					self.DEVICES = {}
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The connection to the device was lost!\n\nThis can be happen in one of the following cases:\n- The USB cable was unplugged or is faulty\n- The inserted cartridge may draw too much peak power (try re-connecting a few times or try hotswapping the cartridge after connecting)\n- The inserted cartrdige may introduce a short circuit (check for bad soldering)\n\nDo you want to try and reconnect to the device?", standardButtons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
					msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
					answer = msgbox.exec()
					if answer == QtWidgets.QMessageBox.No:
						self.DisconnectDevice()
						return False
					
					QtCore.QTimer.singleShot(500, lambda: [ self.FindDevices(connectToFirst=True, mode=mode) ])
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
			cb = QtWidgets.QCheckBox("Don’t show this message again", checked=False)
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Warning, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text="The mode will now be changed to " + {"DMG":"Game Boy", "AGB":"Game Boy Advance"}[setTo] + " mode. To be safe, cartridges should only be exchanged while they are not receiving power by the device." + voltageWarning, standardButtons=QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
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
		
		ok = self.ReadCartridge()
		qt_app.processEvents()
		if ok not in (False, None):
			self.btnHeaderRefresh.setEnabled(True)
			self.btnDetectCartridge.setEnabled(True)
			self.btnBackupROM.setEnabled(True)
			self.btnFlashROM.setEnabled(True)
			self.btnBackupRAM.setEnabled(True)
			self.btnRestoreRAM.setEnabled(True)
			self.grpDMGCartridgeInfo.setEnabled(True)
			self.grpAGBCartridgeInfo.setEnabled(True)
	
	def ReadCartridge(self, resetStatus=True):
		if self.CheckDeviceAlive() is not True: return
		if resetStatus:
			self.btnHeaderRefresh.setEnabled(False)
			self.btnDetectCartridge.setEnabled(False)
			self.btnBackupROM.setEnabled(False)
			self.btnFlashROM.setEnabled(False)
			self.btnBackupRAM.setEnabled(False)
			self.btnRestoreRAM.setEnabled(False)
			self.lblStatus4a.setText("Reading cartridge data...")
			self.SetProgressBars(min=0, max=0, value=1)
			qt_app.processEvents()
		
		try:
			data = self.CONN.ReadInfo(setPinsAsInputs=True)
		except SerialException:
			self.DisconnectDevice()
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The connection to the device was lost while trying to read the ROM header. This may happen if the inserted cartridge issues a short circuit or its peak power draw is too high.\n\nAs a potential workaround for the latter, you can try hotswapping the cartridge:\n1. Remove the cartridge from the device\n2. Reconnect the device and select mode\n3. Then insert the cartridge and click “{:s}”".format(self.btnHeaderRefresh.text().replace("&", "")), QtWidgets.QMessageBox.Ok)
			return False
		
		if resetStatus:
			self.btnHeaderRefresh.setEnabled(True)
			self.btnDetectCartridge.setEnabled(True)
			self.btnBackupROM.setEnabled(True)
			self.btnFlashROM.setEnabled(True)
			self.btnBackupRAM.setEnabled(True)
			self.btnRestoreRAM.setEnabled(True)
			self.btnHeaderRefresh.setFocus()
			self.SetProgressBars(min=0, max=100, value=0)
			self.lblStatus4a.setText("Ready.")
			qt_app.processEvents()
		
		if data == False or len(data) == 0:
			self.DisconnectDevice()
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "Invalid response from the device.", QtWidgets.QMessageBox.Ok)
			return False
		
		if self.CONN.CheckROMStable() is False and resetStatus:
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "The cartridge connection is unstable!\nPlease clean the cartridge pins, carefully realign the cartridge and then try again.", QtWidgets.QMessageBox.Ok)
		
		if self.CONN.GetMode() == "DMG":
			self.cmbHeaderMapperResult.clear()
			self.cmbHeaderMapperResult.addItems(list(Util.DMG_Header_Mapper.values()))
			self.cmbHeaderMapperResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			self.cmbDMGCartridgeTypeResult.clear()
			self.cmbDMGCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesDMG()[0])
			self.cmbDMGCartridgeTypeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			if "flash_type" in data:
				self.cmbDMGCartridgeTypeResult.setCurrentIndex(data["flash_type"])
			self.cmbHeaderROMSizeResult.clear()
			self.cmbHeaderROMSizeResult.addItems(Util.DMG_Header_ROM_Sizes)
			self.cmbHeaderROMSizeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			self.cmbHeaderRAMSizeResult.clear()
			self.cmbHeaderRAMSizeResult.addItems(Util.DMG_Header_RAM_Sizes)
			self.cmbHeaderRAMSizeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
			
			self.lblHeaderTitleResult.setText(data['game_title'])
			if len(data['game_code']) > 0:
				self.lblHeaderRevision.setText("Game Code / Revision:")
				self.lblHeaderRevisionResult.setText("{:s}-{:s}".format(data['game_code'], str(data['version'])))
			else:
				self.lblHeaderRevision.setText("Revision:")
				self.lblHeaderRevisionResult.setText(str(data['version']))

			self.lblHeaderRtcResult.setText(data["rtc_string"])
			
			if data['logo_correct']:
				self.lblHeaderLogoValidResult.setText("OK")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
			else:
				self.lblHeaderLogoValidResult.setText("Invalid")
				self.lblHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }")
			if data['header_checksum_correct']:
				self.lblHeaderChecksumResult.setText("Valid (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
			else:
				self.lblHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblHeaderChecksumResult.setStyleSheet("QLabel { color: red; }")
			self.lblHeaderROMChecksumResult.setText("0x{:04X}".format(data['rom_checksum']))
			self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())

			self.cmbHeaderROMSizeResult.setCurrentIndex(data["rom_size_raw"])
			for i in range(0, len(Util.DMG_Header_RAM_Sizes_Map)):
				if data["ram_size_raw"] == Util.DMG_Header_RAM_Sizes_Map[i]:
					self.cmbHeaderRAMSizeResult.setCurrentIndex(i)
			i = 0
			for k in Util.DMG_Header_Mapper.keys():
				if data["mapper_raw"] == k:
					self.cmbHeaderMapperResult.setCurrentIndex(i)
					if k == 0x06: # MBC2
						self.cmbHeaderRAMSizeResult.setCurrentIndex(1)
					elif k == 0x22 and data["game_title"] in ("KORO2 KIRBY", "KIRBY TNT"): # MBC7 Kirby
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x101))
					elif k == 0x22 and data["game_title"] in ("CMASTER"): # MBC7 Command Master
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x102))
					elif k == 0xFD: # TAMA5
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x103))
					elif k == 0x20: # MBC6
						self.cmbHeaderRAMSizeResult.setCurrentIndex(Util.DMG_Header_RAM_Sizes_Map.index(0x104))

				i += 1
			
			if data['empty'] == True: # defaults
				if data['empty_nocart'] == True:
					self.lblHeaderTitleResult.setText("(No cartridge connected)")
				else:
					self.lblHeaderTitleResult.setText("(No ROM data detected)")
				self.lblHeaderTitleResult.setStyleSheet("QLabel { color: red; }")
				self.cmbHeaderROMSizeResult.setCurrentIndex(0)
				self.cmbHeaderRAMSizeResult.setCurrentIndex(0)
				self.cmbHeaderMapperResult.setCurrentIndex(0)
			else:
				self.lblHeaderTitleResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				if data['logo_correct'] and not self.CONN.IsSupportedMbc(data["mapper_raw"]) and resetStatus:
					QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge uses a mapper that may not be completely supported by {:s} using the current firmware version of the {:s} device. Please check for firmware updates in the Tools menu or the maker’s website.".format(APPNAME, self.CONN.GetFullName()), QtWidgets.QMessageBox.Ok)
				if data['logo_correct'] and data['game_title'] in ("NP M-MENU MENU", "DMG MULTI MENU "):
					cart_types = self.CONN.GetSupportedCartridgesDMG()
					for i in range(0, len(cart_types[0])):
						if "dmg-mmsa-jpn" in cart_types[1][i]:
							self.cmbDMGCartridgeTypeResult.setCurrentIndex(i)
			
			if data["mapper_raw"] == 0x203: # Xploder GB
				self.lblHeaderRtcResult.setText("")
				self.lblHeaderLogoValidResult.setText("")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				self.lblHeaderChecksumResult.setText("")
				self.lblHeaderChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				self.lblHeaderROMChecksumResult.setText("")
				self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
			elif data["mapper_raw"] == 0x205: # Datel Orbit V2
				self.lblHeaderRtcResult.setText("")
				self.lblHeaderRevisionResult.setText("")
				self.lblHeaderLogoValidResult.setText("")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				self.lblHeaderChecksumResult.setText("")
				self.lblHeaderChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				self.lblHeaderROMChecksumResult.setText("")
				self.lblHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
			elif data["mapper_raw"] == 0x204: # Sachen
				self.lblHeaderRtcResult.setText("")
				self.lblHeaderRevisionResult.setText("")
				self.lblHeaderLogoValidResult.setText("")
				self.lblHeaderLogoValidResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				if "logo_sachen" in data:
					data["logo_sachen"].putpalette([ 255, 255, 255, 128, 128, 128 ])
					self.lblHeaderLogoValidResult.setPixmap(QtGui.QPixmap.fromImage(ImageQt(data["logo_sachen"].convert("RGBA"))))
			else:
				if "logo" in data:
					if data['logo_correct']:
						data["logo"].putpalette([ 255, 255, 255, self.TEXT_COLOR[0], self.TEXT_COLOR[1], self.TEXT_COLOR[2] ])
					else:
						data["logo"].putpalette([ 255, 255, 255, 251, 0, 24 ])
					self.lblHeaderLogoValidResult.setPixmap(QtGui.QPixmap.fromImage(ImageQt(data["logo"].convert("RGBA"))))
			
			self.grpAGBCartridgeInfo.setVisible(False)
			self.grpDMGCartridgeInfo.setVisible(True)
		
		elif self.CONN.GetMode() == "AGB":
			if resetStatus:
				self.cmbAGBCartridgeTypeResult.clear()
				self.cmbAGBCartridgeTypeResult.addItems(self.CONN.GetSupportedCartridgesAGB()[0])
				self.cmbAGBCartridgeTypeResult.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
				if "flash_type" in data:
					self.cmbAGBCartridgeTypeResult.setCurrentIndex(data["flash_type"])

			self.lblAGBHeaderTitleResult.setText(data['game_title'])
			self.lblAGBHeaderCodeResult.setText(data['game_code'])
			self.lblAGBHeaderRevisionResult.setText(str(data['version']))
			if data['logo_correct']:
				self.lblAGBHeaderLogoValidResult.setText("OK")
				self.lblAGBHeaderLogoValidResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeaderLogoValidResult.setText("Invalid")
				self.lblAGBHeaderLogoValidResult.setStyleSheet("QLabel { color: red; }")

			self.lblAGBGpioRtcResult.setText(data["rtc_string"])
			
			if data['header_checksum_correct']:
				self.lblAGBHeaderChecksumResult.setText("Valid (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet(self.lblAGBHeaderCodeResult.styleSheet())
			else:
				self.lblAGBHeaderChecksumResult.setText("Invalid (0x{:02X})".format(data['header_checksum']))
				self.lblAGBHeaderChecksumResult.setStyleSheet("QLabel { color: red; }")
			
			self.lblAGBHeaderROMChecksumResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
			self.lblAGBHeaderROMChecksumResult.setText("Not available")
			Util.AGB_Global_CRC32 = 0
			
			db_agb_entry = data["db"]
			if db_agb_entry is None:
				self.lblAGBHeaderROMChecksumResult.setText("Not in database")
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
			
			if data["3d_memory"] is True:
				self.cmbAGBHeaderROMSizeResult.setCurrentIndex(Util.AGB_Header_ROM_Sizes_Map.index(0x4000000))
			
			if data["save_type"] == None:
				self.cmbAGBSaveTypeResult.setCurrentIndex(0)
				if db_agb_entry != None:
					if db_agb_entry['st'] < len(Util.AGB_Header_Save_Types):
						self.cmbAGBSaveTypeResult.setCurrentIndex(db_agb_entry['st'])
				if data["dacs_8m"] is True:
					self.cmbAGBSaveTypeResult.setCurrentIndex(6)

			if data['empty'] == True: # defaults
				if data['empty_nocart'] == True:
					self.lblAGBHeaderTitleResult.setText("(No cartridge connected)")
				else:
					self.lblAGBHeaderTitleResult.setText("(No ROM data detected)")
				self.lblAGBHeaderTitleResult.setStyleSheet("QLabel { color: red; }")
				self.cmbAGBSaveTypeResult.setCurrentIndex(0)
			else:
				self.lblAGBHeaderTitleResult.setStyleSheet(self.lblHeaderRevisionResult.styleSheet())
				if data['logo_correct'] and data['3d_memory'] is True:
					cart_types = self.CONN.GetSupportedCartridgesAGB()
					for i in range(0, len(cart_types[0])):
						if "3d_memory" in cart_types[1][i]:
							self.cmbAGBCartridgeTypeResult.setCurrentIndex(i)
			
			self.grpDMGCartridgeInfo.setVisible(False)
			self.grpAGBCartridgeInfo.setVisible(True)
			
			if data['logo_correct'] and isinstance(db_agb_entry, dict) and "rs" in db_agb_entry and db_agb_entry['rs'] == 0x4000000 and not self.CONN.IsSupported3dMemory() and resetStatus:
				QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge uses a Memory Bank Controller that may not be completely supported by the firmware of the {:s} device. Please check for firmware updates in the Tools menu or the maker’s website.".format(self.CONN.GetFullName()), QtWidgets.QMessageBox.Ok)
		
		if resetStatus:
			self.lblStatus1aResult.setText("–")
			self.lblStatus2aResult.setText("–")
			self.lblStatus3aResult.setText("–")
			self.lblStatus4a.setText("Ready.")
			self.grpStatus.setTitle("Transfer Status")
			self.FinishOperation()
		
		if data['game_title'][:11] == "YJencrypted" and resetStatus:
			QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "This cartridge may be protected against reading or writing a ROM. If you don’t want to risk this cartridge to render itself unusable, please do not try to write a new ROM to it.", QtWidgets.QMessageBox.Ok)
	
	def DetectCartridge(self, canSkipMessage=False):
		if not self.CheckDeviceAlive(): return
		if not self.CONN.CheckROMStable():
			answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), "The cartridge connection is unstable!\nPlease clean the cartridge pins, carefully realign the cartridge for best results.\n\nContinue anyway?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
			if answer == QtWidgets.QMessageBox.No: return
		self.btnHeaderRefresh.setEnabled(False)
		self.btnDetectCartridge.setEnabled(False)
		self.btnBackupROM.setEnabled(False)
		self.btnFlashROM.setEnabled(False)
		self.btnBackupRAM.setEnabled(False)
		self.btnRestoreRAM.setEnabled(False)
		self.grpStatus.setTitle("Transfer Status")
		self.lblStatus1aResult.setText("–")
		self.lblStatus2aResult.setText("–")
		self.lblStatus3aResult.setText("–")
		self.lblStatus4aResult.setText("")
		self.lblStatus4a.setText("Analyzing Cartridge...")
		self.SetProgressBars(min=0, max=0, value=1)
		qt_app.processEvents()
		
		limitVoltage = str(self.SETTINGS.value("AutoDetectLimitVoltage", default="disabled")).lower() == "enabled"
		ret = self.CONN.DetectCartridge(limitVoltage=limitVoltage, checkSaveType=not canSkipMessage)
		if ret is False:
			QtWidgets.QMessageBox.critical(self, "{:s} {:s}".format(APPNAME, VERSION), "An error occured while trying to analyze the cartridge and you may need to physically reconnect the device.\n\nThis cartridge may not be auto-detectable, please select the cartridge type manually.", QtWidgets.QMessageBox.Ok)
			self.DisconnectDevice()
			cart_type = None
		else:
			(header, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, _, flash_id) = ret
			
			# Save Type
			if not canSkipMessage:
				try:
					if save_type is not None and save_type is not False:
						if self.CONN.GetMode() == "DMG":
							self.cmbHeaderRAMSizeResult.setCurrentIndex(save_type)
						elif self.CONN.GetMode() == "AGB":
							self.cmbAGBSaveTypeResult.setCurrentIndex(save_type)
				except:
					pass
			
			# Cart Type
			try:
				cart_type = None
				msg_cart_type = ""
				msg_cart_type_used = ""
				if self.CONN.GetMode() == "DMG":
					supp_cart_types = self.CONN.GetSupportedCartridgesDMG()
				elif self.CONN.GetMode() == "AGB":
					supp_cart_types = self.CONN.GetSupportedCartridgesAGB()
				
				if len(cart_types) > 0:
					cart_type = cart_type_id
					if self.CONN.GetMode() == "DMG":
						self.cmbDMGCartridgeTypeResult.setCurrentIndex(0)
						self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
					elif self.CONN.GetMode() == "AGB":
						self.cmbAGBCartridgeTypeResult.setCurrentIndex(0)
						self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)
					self.STATUS["cart_type"] = supp_cart_types[1][cart_type]
					for i in range(0, len(cart_types)):
						if cart_types[i] == cart_type_id:
							msg_cart_type += "- {:s}*<br>".format(supp_cart_types[0][cart_types[i]])
							msg_cart_type_used = supp_cart_types[0][cart_types[i]]
						else:
							msg_cart_type += "- {:s}<br>".format(supp_cart_types[0][cart_types[i]])
					msg_cart_type = msg_cart_type[:-4]
			
			except:
				pass
			
			# Messages
			# Header
			msg_header_s = "<b>Game Title:</b> {:s}<br>".format(header["game_title"])
			
			# Save Type
			msg_save_type_s = ""
			if not canSkipMessage and save_type is not False and save_type is not None:
				if save_chip is not None:
					temp = "{:s} ({:s})".format(Util.AGB_Header_Save_Types[save_type], save_chip)
				else:
					if self.CONN.GetMode() == "DMG":
						try:
							temp = "{:s}".format(Util.DMG_Header_RAM_Sizes[save_type])
						except:
							temp = "Unknown"
					elif self.CONN.GetMode() == "AGB":
						temp = "{:s}".format(Util.AGB_Header_Save_Types[save_type])
						try:
							if "Batteryless SRAM" in Util.AGB_Header_Save_Types[save_type]:
								if save_size == header["batteryless_sram"]["bl_size"]:
									temp += " ({:s})<br><b>Possible Batteryless SRAM Location:</b> 0x{:X}".format(Util.formatFileSize(save_size, asInt=True), header["batteryless_sram"]["bl_offset"])
								else:
									temp += " ({:s})<br><b>Possible Batteryless SRAM Location:</b> 0x{:X} (expecting {:s} of SRAM)".format(Util.formatFileSize(save_size, asInt=True), header["batteryless_sram"]["bl_offset"], Util.formatFileSize(header["batteryless_sram"]["bl_size"], asInt=True))
						except:
							pass

				if save_type == 0:
					msg_save_type_s = "<b>Save Type:</b> None or unknown (no save data detected)<br>"
				else:
					if sram_unstable and "SRAM" in temp:
						msg_save_type_s = "<b>Save Type:</b> {:s} <span style=\"color: red;\">(not stable or not battery-backed)</span><br>".format(temp)
					else:
						msg_save_type_s = "<b>Save Type:</b> {:s}<br>".format(temp)
			
			# Cart Type
			msg_cart_type_s = ""
			msg_cart_type_s_detail = ""
			msg_flash_size_s = ""
			msg_flash_id_s = ""
			msg_cfi_s = ""
			msg_flash_mapper_s = ""
			try_this = None
			found_supported = False
			is_generic = False
			if cart_type is not None:
				if len(cart_types) > 1:
					msg_cart_type_s = "<b>Cartridge Type:</b> {:s} (or compatible)<br>".format(msg_cart_type_used)
				else:
					msg_cart_type_s = "<b>Cartridge Type:</b> {:s}<br>".format(msg_cart_type_used)
				msg_cart_type_s_detail = "<b>Compatible Cartridge Types:</b><br>{:s}<br>".format(msg_cart_type)
				found_supported = True

				if "flash_size" in supp_cart_types[1][cart_type_id]:
					size = supp_cart_types[1][cart_type_id]["flash_size"]
					msg_flash_size_s = "<b>ROM Size:</b> {:s}<br>".format(Util.formatFileSize(size, asInt=True))
				
				if self.CONN.GetMode() == "DMG":
					if "mbc" in supp_cart_types[1][cart_type_id]:
						if supp_cart_types[1][cart_type_id]["mbc"] == "manual":
							msg_flash_mapper_s = "<b>Mapper Type:</b> <i>Manual selection</i><br>"
						elif supp_cart_types[1][cart_type_id]["mbc"] in Util.DMG_Header_Mapper.keys():
							msg_flash_mapper_s = "<b>Mapper Type:</b> {:s}<br>".format(Util.DMG_Header_Mapper[supp_cart_types[1][cart_type_id]["mbc"]])
					else:
						msg_flash_mapper_s = "<b>Mapper Type:</b> Default (MBC5)<br>"
			
			else:
				if (len(flash_id.split("\n")) > 2) and ((self.CONN.GetMode() == "DMG") or ("dacs_8m" in header and header["dacs_8m"] is not True)):
					msg_cart_type_s = "<b>Cartridge Type:</b> Unknown flash cartridge – Please submit the displayed information along with a picture of the cartridge’s circuit board."
					if ("[     0/90]" in flash_id):
						try_this = "Generic Flash Cartridge (0/90)"
					elif ("[   AAA/AA]" in flash_id):
						try_this = "Generic Flash Cartridge (AAA/AA)"
					elif ("[   AAA/A9]" in flash_id):
						try_this = "Generic Flash Cartridge (AAA/A9)"
					elif ("[WR   / AAA/AA]" in flash_id):
						try_this = "Generic Flash Cartridge (WR/AAA/AA)"
					elif ("[WR   / AAA/A9]" in flash_id):
						try_this = "Generic Flash Cartridge (WR/AAA/A9)"
					elif ("[WR   / 555/AA]" in flash_id):
						try_this = "Generic Flash Cartridge (WR/555/AA)"
					elif ("[WR   / 555/A9]" in flash_id):
						try_this = "Generic Flash Cartridge (WR/555/A9)"
					elif ("[AUDIO/ AAA/AA]" in flash_id):
						try_this = "Generic Flash Cartridge (AUDIO/AAA/AA)"
					elif ("[AUDIO/ 555/AA]" in flash_id):
						try_this = "Generic Flash Cartridge (AUDIO/555/AA)"
					if try_this is not None:
						msg_cart_type_s += " For ROM writing, you can give the option called “{:s}” a try at your own risk.".format(try_this)
					msg_cart_type_s += "<br>"
				else:
					msg_cart_type_s = "<b>Cartridge Type:</b> Generic ROM Cartridge (not rewritable or not auto-detectable)<br>"
					is_generic = True
			
			if (len(flash_id.split("\n")) > 2):
				if limitVoltage:
					msg_flash_id_s_limit = " (voltage limited)"
				else:
					msg_flash_id_s_limit = ""
				msg_flash_id_s = "<br><b>Flash ID Check{:s}:</b><pre style=\"font-size: 8pt; margin: 0;\">{:s}</pre>".format(msg_flash_id_s_limit, flash_id[:-1])
				if cfi_s != "":
					msg_cfi_s = "<br><b>Common Flash Interface Data:</b><br>{:s}<br><br>".format(cfi_s.replace("\n", "<br>"))
				else:
					msg_cfi_s = "<br><b>Common Flash Interface Data:</b> No data provided<br><br>"
			
			if msg_cart_type_s_detail == "": msg_cart_type_s_detail = msg_cart_type_s
			self.SetProgressBars(min=0, max=100, value=100)
			show_details = False
			msg = "The following cartridge configuration was detected:<br><br>"
			if found_supported:
				dontShowAgain = str(self.SETTINGS.value("SkipAutodetectMessage", default="disabled")).lower() == "enabled"
				if not dontShowAgain or not canSkipMessage:
					temp = "{:s}{:s}{:s}{:s}{:s}".format(msg, msg_flash_size_s, msg_save_type_s, msg_flash_mapper_s, msg_cart_type_s)
					temp = temp[:-4]
					msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=temp)
					msgbox.setTextFormat(QtCore.Qt.RichText)
					button_ok = msgbox.addButton("&OK", QtWidgets.QMessageBox.ActionRole)
					button_details = msgbox.addButton("&Details", QtWidgets.QMessageBox.ActionRole)
					button_cancel = None
					msgbox.setDefaultButton(button_ok)
					cb = QtWidgets.QCheckBox("Always skip this message", checked=False)
					if canSkipMessage:
						button_cancel = msgbox.addButton("&Cancel", QtWidgets.QMessageBox.RejectRole)
						msgbox.setEscapeButton(button_cancel)
						msgbox.setCheckBox(cb)
					else:
						msgbox.setEscapeButton(button_ok)
					
					msgbox.exec()
					dontShowAgain = cb.isChecked()
					if dontShowAgain and canSkipMessage: self.SETTINGS.setValue("SkipAutodetectMessage", "enabled")

					if msgbox.clickedButton() == button_details:
						show_details = True
						msg = ""
					elif msgbox.clickedButton() == button_cancel:
						self.btnHeaderRefresh.setEnabled(True)
						self.btnDetectCartridge.setEnabled(True)
						self.btnBackupROM.setEnabled(True)
						self.btnFlashROM.setEnabled(True)
						self.btnBackupRAM.setEnabled(True)
						self.btnRestoreRAM.setEnabled(True)
						self.btnHeaderRefresh.setFocus()
						self.SetProgressBars(min=0, max=100, value=0)
						self.lblStatus4a.setText("Ready.")
						return False

			if not found_supported or show_details is True:
				msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION))
				button_ok = msgbox.addButton("&OK", QtWidgets.QMessageBox.ActionRole)
				msgbox.setDefaultButton(button_ok)
				msgbox.setEscapeButton(button_ok)
				if try_this is not None:
					button_try = msgbox.addButton("  &Try Generic Type  ", QtWidgets.QMessageBox.ActionRole)
					button_try.setToolTip("{:s}".format(try_this))
				else:
					button_try = None
				
				if not is_generic:
					msg_fw = "<br><span style=\"font-size: 8pt;\"><i>{:s} {:s} | {:s}</i></span><br>".format(APPNAME, VERSION, self.CONN.GetFullNameExtended())
					button_clipboard = msgbox.addButton("  &Copy to Clipboard  ", QtWidgets.QMessageBox.ActionRole)
				else:
					msg_fw = ""
					button_clipboard = None
				
				if self.CONN.GetMode() == "DMG" and limitVoltage and (is_generic or not found_supported):
					text = "No known flash cartridge type could be detected. The option “Limit voltage to 3.3V when detecting Game Boy flash cartridges” has been enabled which can cause auto-detection to fail. As it is usually not recommended to enable this option, do you now want to disable it and try again?"
					answer = QtWidgets.QMessageBox.warning(self, "{:s} {:s}".format(APPNAME, VERSION), text, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
					if answer == QtWidgets.QMessageBox.Yes:
						self.SETTINGS.setValue("AutoDetectLimitVoltage", "disabled")
						self.mnuConfig.actions()[4].setChecked(False)
						return self.DetectCartridge()
				
				temp = "{:s}{:s}{:s}{:s}{:s}{:s}{:s}{:s}{:s}".format(msg, msg_header_s, msg_flash_size_s, msg_save_type_s, msg_flash_mapper_s, msg_flash_id_s, msg_cfi_s, msg_cart_type_s_detail, msg_fw)
				temp = temp[:-4]
				msgbox.setText(temp)
				msgbox.setTextFormat(QtCore.Qt.RichText)
				msgbox.exec()
				if msgbox.clickedButton() == button_clipboard:
					clipboard = QtWidgets.QApplication.clipboard()
					doc = QtGui.QTextDocument()
					doc.setHtml(temp)
					temp = doc.toPlainText()
					clipboard.setText(temp)
				elif msgbox.clickedButton() == button_try:
					if try_this in supp_cart_types[0]:
						cart_type = supp_cart_types[0].index(try_this)
					if self.CONN.GetMode() == "DMG":
						self.cmbDMGCartridgeTypeResult.setCurrentIndex(cart_type)
					elif self.CONN.GetMode() == "AGB":
						self.cmbAGBCartridgeTypeResult.setCurrentIndex(cart_type)

		self.btnHeaderRefresh.setEnabled(True)
		self.btnDetectCartridge.setEnabled(True)
		self.btnBackupROM.setEnabled(True)
		self.btnFlashROM.setEnabled(True)
		self.btnBackupRAM.setEnabled(True)
		self.btnRestoreRAM.setEnabled(True)
		self.btnHeaderRefresh.setFocus()
		self.SetProgressBars(min=0, max=100, value=0)
		self.lblStatus4a.setText("Ready.")
		return cart_type
	
	def UpdateProgress(self, args):
		if args is None: return
		if self.CONN is None: return
		
		if "method" in args:
			if args["method"] == "ROM_READ":
				self.grpStatus.setTitle("Transfer Status (Backup ROM)")
			elif args["method"] == "ROM_WRITE":
				self.grpStatus.setTitle("Transfer Status (Write ROM)")
			elif args["method"] == "ROM_WRITE_VERIFY":
				self.grpStatus.setTitle("Transfer Status (Verify Flash)")
			elif args["method"] == "SAVE_READ":
				self.grpStatus.setTitle("Transfer Status (Backup Save Data)")
			elif args["method"] == "SAVE_WRITE":
				self.grpStatus.setTitle("Transfer Status (Write Save Data)")
			elif args["method"] == "SAVE_WRITE_VERIFY":
				self.grpStatus.setTitle("Transfer Status (Verify Save Data)")
		
		if "error" in args:
			self.lblStatus4a.setText("Failed!")
			self.grpDMGCartridgeInfo.setEnabled(True)
			self.grpAGBCartridgeInfo.setEnabled(True)
			self.grpActions.setEnabled(True)
			self.btnTools.setEnabled(True)
			self.btnConfig.setEnabled(True)
			self.btnCancel.setEnabled(False)
			msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=str(args["error"]), standardButtons=QtWidgets.QMessageBox.Ok)
			if not '\n' in str(args["error"]): msgbox.setTextFormat(QtCore.Qt.RichText)
			msgbox.exec()
			return
		
		self.grpDMGCartridgeInfo.setEnabled(False)
		self.grpAGBCartridgeInfo.setEnabled(False)
		self.grpActions.setEnabled(False)
		self.btnTools.setEnabled(False)
		self.btnConfig.setEnabled(False)
		
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
			elif args["action"] == "UNLOCK":
				self.lblStatus1aResult.setText("Pending...")
				self.lblStatus2aResult.setText("Pending...")
				self.lblStatus3aResult.setText("Pending...")
				self.lblStatus4a.setText("Unlocking flash...")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(args["abortable"])
				self.SetProgressBars(min=0, max=size, value=pos)
			elif args["action"] == "UPDATE_RTC":
				self.lblStatus1aResult.setText("Pending...")
				self.lblStatus2aResult.setText("Pending...")
				self.lblStatus3aResult.setText("Pending...")
				self.lblStatus4a.setText("Updating Real Time Clock...")
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(False)
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
			elif args["action"] == "ERROR":
				self.lblStatus2aResult.setText("Pending...")
				self.lblStatus3aResult.setText("Pending...")
				self.lblStatus4a.setText("<span style=\"color: red;\">{:s}</span>".format(args["text"]))
				self.lblStatus4aResult.setText("")
				self.btnCancel.setEnabled(args["abortable"])
				self.SetProgressBars(min=0, max=size, value=pos)
			elif args["action"] == "FINISHED":
				if pos > 0:
					self.lblStatus1aResult.setText(Util.formatFileSize(pos))
				self.FinishOperation()
			elif args["action"] == "ABORT":
				wd = 10
				try:
					while self.CONN.WORKER.isRunning():
						time.sleep(0.1)
						wd -= 1
						if wd == 0: break
				except AttributeError as _:
					return
				self.CONN.CANCEL = False
				self.CONN.ERROR = False
				self.grpDMGCartridgeInfo.setEnabled(True)
				self.grpAGBCartridgeInfo.setEnabled(True)
				self.grpActions.setEnabled(True)
				self.btnTools.setEnabled(True)
				self.btnConfig.setEnabled(True)
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
						Util.dprint("Displaying Message Box:\n----\n{:s} {:s}\n----\n{:s}\n----".format(APPNAME, VERSION, args["info_msg"]))
						self.WriteDebugLog()
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Critical, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=args["info_msg"], standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in args["info_msg"]: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
						if "fatal" in args: self.DisconnectDevice()
					elif args["info_type"] == "msgbox_information":
						msgbox = QtWidgets.QMessageBox(parent=self, icon=QtWidgets.QMessageBox.Information, windowTitle="{:s} {:s}".format(APPNAME, VERSION), text=args["info_msg"], standardButtons=QtWidgets.QMessageBox.Ok)
						if not '\n' in args["info_msg"]: msgbox.setTextFormat(QtCore.Qt.RichText)
						msgbox.exec()
					elif args["info_type"] == "label":
						self.lblStatus4a.setText(args["info_msg"])
				
				QtCore.QTimer.singleShot(1, lambda: [ self.ReadCartridge(resetStatus=False) ])
				return

			elif args["action"] == "PROGRESS":
				self.SetProgressBars(min=0, max=size, value=pos)
				if "abortable" in args:
					self.btnCancel.setEnabled(args["abortable"])
				else:
					self.btnCancel.setEnabled(True)
				self.lblStatus1aResult.setText("{:s}".format(Util.formatFileSize(pos)))
				if speed > 0:
					self.lblStatus2aResult.setText("{:.2f} KiB/s".format(speed))
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
	
	def ShowFirmwareUpdateWindow(self):
		if self.CONN is None:
			try:
				from . import fw_GBxCartRW_v1_4
				FirmwareUpdater = fw_GBxCartRW_v1_4.FirmwareUpdaterWindow
			except:
				return False
		else:
			if not self.CONN.SupportsFirmwareUpdates():
				QtWidgets.QMessageBox.information(self, "{:s} {:s}".format(APPNAME, VERSION), "{:s} currently does not support updaing the firmware of your device.".format(APPNAME), QtWidgets.QMessageBox.Ok)
				return False
			else:
				FirmwareUpdater = self.CONN.GetFirmwareUpdaterClass()[1]
		self.FWUPWIN = None
		self.FWUPWIN = FirmwareUpdater(self, app_path=Util.APP_PATH, icon=self.windowIcon(), device=self.CONN)
		self.FWUPWIN.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self.FWUPWIN.setModal(True)
		self.FWUPWIN.run()
	
	def ShowPocketCameraWindow(self):
		data = None
		if self.CONN is not None:
			if self.CONN.GetMode() is None:
				self.optDMG.setChecked(True)
				self.SetMode()
			if self.CONN.GetMode() == "DMG":
				header = self.CONN.ReadInfo(setPinsAsInputs=True)
				if header["mapper_raw"] == 252: # GBD
					args = { "path":None, "mbc":252, "save_type":128*1024, "rtc":False }
					self.CONN.BackupRAM(fncSetProgress=False, args=args)
					data = self.CONN.INFO["data"]
		
		self.CAMWIN = None
		self.CAMWIN = PocketCameraWindow(self, icon=self.windowIcon(), file=data, config_path=Util.CONFIG_PATH)
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
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path()) # type: ignore
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1].lower() == ".sav":
					return True
				elif self.CONN.GetMode() == "DMG" and fn_split[1].lower() in (".gb", ".sgb", ".gbc", ".bin", ".isx"):
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
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path()) # type: ignore
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1].lower() in (".gb", ".sgb", ".gbc", ".bin", ".isx", ".gba", ".srl"):
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
			from  PySide2.QtWinExtras import QWinTaskbarButton, QtWin
			myappid = 'lesserkuma.flashgbx'
			QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
			taskbar_button = QWinTaskbarButton()
			self.TBPROG = taskbar_button.progress()
			self.TBPROG.setRange(0, 100)
			taskbar_button.setWindow(self.windowHandle())
			self.TBPROG.setVisible(False)
		except ImportError:
			pass
		
		if callable(getattr(qt_app, "exec", None)):
			qt_app.exec() # PySide6
		else:
			qt_app.exec_() # PySide2

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
qt_app = QApplication(sys.argv)
qt_app.setApplicationName(APPNAME)
