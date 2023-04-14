# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

from .pyside import QtCore, QtWidgets, QtGui

class UserInputDialog(QtWidgets.QDialog):
	APP = None

	def __init__(self, app, icon=None, args=None):
		super(UserInputDialog, self).__init__(app)
		if icon is not None: self.setWindowIcon(QtGui.QIcon(icon))
		self.setStyleSheet("QMessageBox { messagebox-text-interaction-flags: 5; }")
		self.setWindowTitle("FlashGBX – {:s}".format(args["title"]))
		self.setWindowFlags((self.windowFlags() | QtCore.Qt.MSWindowsFixedSizeDialogHint) & ~QtCore.Qt.WindowContextHelpButtonHint)

		self.APP = app

		self.lblIntro = QtWidgets.QLabel(args["intro"])
		self.lblIntro.setStyleSheet("margin-bottom: 4px")
		self.btnOK = QtWidgets.QPushButton("&OK")
		self.btnCancel = QtWidgets.QPushButton("&Cancel")
		
		grid_layout = QtWidgets.QGridLayout()
		grid_layout.addWidget(self.lblIntro, 0, 0, 1, 2)
		grid_rows = 1
		
		self.paramWidgets = {}
		for param in args["params"]:
			if param[1] in ("cmb", "cmb_e"):
				lbl = QtWidgets.QLabel(param[2])
				cmb = QtWidgets.QComboBox()
				cmb.clear()
				cmb.addItems(param[3])
				cmb.setCurrentIndex(param[4])
				if param[1] == "cmb_e":
					cmb.setEditable(True)
				elif len(param[3]) == 1:
					cmb.setEnabled(False)
				cmb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
				self.paramWidgets[param[0]] = cmb
				grid_layout.addWidget(lbl, grid_rows, 0, 1, 1)
				grid_layout.addWidget(cmb, grid_rows, 1, 1, 1)
			
			else:
				continue
			
			grid_rows += 1
		grid_layout.setColumnStretch(1, 1)

		grpButtonsLayout = QtWidgets.QHBoxLayout()
		grpButtonsLayout.addStretch(30)
		grpButtonsLayout.addWidget(self.btnOK, grid_rows, QtCore.Qt.AlignRight)
		grpButtonsLayout.addWidget(self.btnCancel, grid_rows, QtCore.Qt.AlignRight)

		grid_layout.addLayout(grpButtonsLayout, grid_rows, 0, 1, 2)
		self.setLayout(grid_layout)

		self.connect(self.btnOK, QtCore.SIGNAL("clicked()"), self.accept)
		self.connect(self.btnCancel, QtCore.SIGNAL("clicked()"), self.reject)
	
	def GetResult(self):
		return self.paramWidgets

	def hideEvent(self, event):
		self.APP.activateWindow()
