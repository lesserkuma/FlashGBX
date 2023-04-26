# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)
# 
# PySide abstraction layer contributed by J-Fox
# 

from .Util import dprint

try:
	import PySide2
	# PySide2>=5.14 is required
	major, minor, *_ = PySide2.__version_info__
	if (major, minor) < (5, 14):
		raise ImportError('Requires PySide2>=5.14', name=PySide2.__package__, path=PySide2.__path__)
	psversion = 2
except ImportError as err:
	try:
		import PySide6
	except ImportError:
		raise err
	dprint('Using PySide6 code path.')
	psversion = 6
	from PySide6 import QtCore
	from PySide6 import QtWidgets
	from PySide6 import QtGui
	from PySide6.QtWidgets import QApplication
else:
	dprint('Using PySide2 code path.')
	from PySide2 import QtCore
	from PySide2 import QtWidgets
	from PySide2 import QtGui
	from PySide2.QtWidgets import QApplication

__all__ = ['QtCore', 'QtWidgets', 'QtGui', 'QApplication', 'QDesktopWidget']


class QDesktopWidget(object):
	def screenGeometry(self, widget):
		if psversion == 2:
			return QtWidgets.QDesktopWidget().screenGeometry()
		else:
			return widget.screen().geometry()
