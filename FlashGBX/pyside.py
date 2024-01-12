# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)
# 
# PySide abstraction layer contributed by J-Fox
# 

import os
from .Util import dprint

try:
	import PySide6
	dprint('Using PySide6 code path.')
	psversion = 6
	from PySide6 import QtCore
	from PySide6 import QtWidgets
	from PySide6 import QtGui
	from PySide6.QtWidgets import QApplication

except ImportError as err:
	try:
		import PySide2, PIL
		# PySide2>=5.14 is required
		major, minor, *_ = PySide2.__version_info__
		if (major, minor) < (5, 14):
			raise ImportError('Requires PySide2>=5.14', name=PySide2.__package__, path=PySide2.__path__)
		# Pillow<10.0.0 is required
		major, minor = map(int, PIL.__version__.split('.')[:2])
		if (major, minor) >= (10, 0):
			raise ImportError('Requires Pillow<10.0.0 if using PySide2', name=PIL.__package__, path=PIL.__path__)

		dprint('Using PySide2 code path.')
		psversion = 2
		from PySide2 import QtCore
		from PySide2 import QtWidgets
		from PySide2 import QtGui
		from PySide2.QtWidgets import QApplication

		os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
		os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
		QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
		QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

	except ImportError as err2:
		raise err2

__all__ = ['QtCore', 'QtWidgets', 'QtGui', 'QApplication', 'QDesktopWidget']

class QDesktopWidget(object):
	def screenGeometry(self, widget):
		if psversion == 2:
			return QtWidgets.QDesktopWidget().screenGeometry()
		else:
			return widget.screen().geometry()
