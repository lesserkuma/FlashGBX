import sys, functools, os, json, platform, hashlib
from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from PIL.PngImagePlugin import PngInfo
from PySide2 import QtCore, QtWidgets, QtGui
import email.utils

class PocketCameraWindow(QtWidgets.QDialog):
	CUR_PIC = None
	CUR_THUMBS = None
	CUR_INDEX = 1
	CUR_BICUBIC = True
	CUR_FILE = ""
	CUR_EXPORT_PATH = ""
	CUR_PC = None
	APP = None
	PALETTES = [
		[ 255, 255, 255,   176, 176, 176,   104, 104, 104,   0, 0, 0 ], # Grayscale
		[ 208, 217, 60,   120, 164, 106,   84, 88, 84,   36, 70, 36 ], # Game Boy
		#[ 196, 207, 161,   139, 149, 109,   77, 83, 60,   31, 31, 31 ], # Game Boy Pocket
		[ 255, 255, 255,   181, 179, 189,   84, 83, 103,   9, 7, 19 ], # Super Game Boy
		[ 240, 240, 240,   218, 196, 106,   112, 88, 52,   30, 30, 30 ], # Game Boy Color (JPN)
		[ 240, 240, 240,   220, 160, 160,   136, 78, 78,   30, 30, 30 ], # Game Boy Color (USA Gold)
		[ 240, 240, 240,   134, 200, 100,   58, 96, 132,   30, 30, 30 ], # Game Boy Color (USA/EUR)
	]
	
	def __init__(self, app, file=None, icon=None):
		QtWidgets.QDialog.__init__(self)
		self.setAcceptDrops(True)
		if icon is not None: self.setWindowIcon(QtGui.QIcon(icon))
		self.CUR_FILE = file
		self.setWindowTitle("FlashGBX – GB Camera Album Viewer")
		if hasattr(QtGui, "Qt"):
			self.setWindowFlags((self.windowFlags() | QtGui.Qt.MSWindowsFixedSizeDialogHint) & ~QtGui.Qt.WindowContextHelpButtonHint);
		
		self.layout = QtWidgets.QGridLayout()
		self.layout.setContentsMargins(-1, 8, -1, 8)
		self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
		self.layout_options1 = QtWidgets.QVBoxLayout()
		self.layout_options2 = QtWidgets.QVBoxLayout()
		self.layout_options3 = QtWidgets.QVBoxLayout()
		self.layout_photos = QtWidgets.QHBoxLayout()
		
		# Options
		self.grpColors = QtWidgets.QGroupBox("Color palette")
		grpColorsLayout = QtWidgets.QVBoxLayout()
		grpColorsLayout.setContentsMargins(-1, 3, -1, -1)
		self.rowColors1 = QtWidgets.QHBoxLayout()
		self.optColorBW = QtWidgets.QRadioButton("&Grayscale")
		self.optColorBW.setToolTip("Generic grayscale palette")
		self.connect(self.optColorBW, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.optColorDMG = QtWidgets.QRadioButton("&DMG")
		self.optColorDMG.setToolTip("Original Game Boy screen palette")
		self.connect(self.optColorDMG, QtCore.SIGNAL("clicked()"), self.SetColors)
		#self.optColorMGB = QtWidgets.QRadioButton("&MGB")
		#self.optColorMGB.setToolTip("Game Boy Pocket palette")
		#self.connect(self.optColorMGB, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.optColorSGB = QtWidgets.QRadioButton("&SGB")
		self.optColorSGB.setToolTip("Super Game Boy palette")
		self.connect(self.optColorSGB, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.optColorCGB1 = QtWidgets.QRadioButton("CGB &1")
		self.optColorCGB1.setToolTip("Japanese Pocket Camera palette")
		self.connect(self.optColorCGB1, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.optColorCGB2 = QtWidgets.QRadioButton("CGB &2")
		self.optColorCGB2.setToolTip("Golden Limited Edition Game Boy Camera palette")
		self.connect(self.optColorCGB2, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.optColorCGB3 = QtWidgets.QRadioButton("CGB &3")
		self.optColorCGB3.setToolTip("Non-Japanese Game Boy Camera palette")
		self.connect(self.optColorCGB3, QtCore.SIGNAL("clicked()"), self.SetColors)
		self.rowColors1.addWidget(self.optColorBW)
		self.rowColors1.addWidget(self.optColorDMG)
		#self.rowColors1.addWidget(self.optColorMGB)
		self.rowColors1.addWidget(self.optColorSGB)
		self.rowColors1.addWidget(self.optColorCGB1)
		self.rowColors1.addWidget(self.optColorCGB2)
		self.rowColors1.addWidget(self.optColorCGB3)
		self.optColorCGB1.setChecked(True)
		
		grpColorsLayout.addLayout(self.rowColors1)
		
		self.grpColors.setLayout(grpColorsLayout)
		self.layout_options1.addWidget(self.grpColors)

		rowActionsGeneral1 = QtWidgets.QHBoxLayout()
		self.btnOpenSRAM = QtWidgets.QPushButton("&Open Save Data File")
		self.btnOpenSRAM.setStyleSheet("padding: 5px 10px;")
		self.btnOpenSRAM.clicked.connect(self.btnOpenSRAM_Clicked)
		self.btnClose = QtWidgets.QPushButton("&Close")
		self.btnClose.setStyleSheet("padding: 5px 15px;")
		self.btnClose.clicked.connect(self.btnClose_Clicked)
		rowActionsGeneral1.addWidget(self.btnOpenSRAM)
		rowActionsGeneral1.addStretch()
		rowActionsGeneral1.addWidget(self.btnClose)
		self.layout_options3.addLayout(rowActionsGeneral1)
		
		# Photo Viewer
		self.grpPhotoView = QtWidgets.QGroupBox("Preview")
		self.grpPhotoViewLayout = QtWidgets.QVBoxLayout()
		self.grpPhotoViewLayout.setContentsMargins(-1, 3, -1, -1)
		self.lblPhotoViewer = QtWidgets.QLabel(self)
		self.lblPhotoViewer.setMinimumSize(256, 223)
		self.lblPhotoViewer.setMaximumSize(256, 223)
		self.lblPhotoViewer.setStyleSheet("border-top: 1px solid #adadad; border-left: 1px solid #adadad; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff;")
		self.lblPhotoViewer.mousePressEvent = self.lblPhotoViewer_Clicked
		self.grpPhotoViewLayout.addWidget(self.lblPhotoViewer)
		
		# Actions below Viewer
		rowActionsGeneral2 = QtWidgets.QHBoxLayout()
		self.btnSavePhoto = QtWidgets.QPushButton("&Save This Picture")
		self.btnSavePhoto.setStyleSheet("padding: 5px 10px;")
		self.btnSavePhoto.clicked.connect(self.btnSavePhoto_Clicked)
		rowActionsGeneral2.addWidget(self.btnSavePhoto)
		self.btnSaveAll = QtWidgets.QPushButton("Save &All Pictures")
		self.btnSaveAll.setStyleSheet("padding: 5px 10px;")
		self.btnSaveAll.clicked.connect(self.btnSaveAll_Clicked)
		rowActionsGeneral2.addWidget(self.btnSaveAll)
		self.grpPhotoViewLayout.addLayout(rowActionsGeneral2)
		
		self.grpPhotoView.setLayout(self.grpPhotoViewLayout)

		# Photo List
		self.grpPhotoThumbs = QtWidgets.QGroupBox("Photo Album")
		self.grpPhotoThumbsLayout = QtWidgets.QVBoxLayout()
		self.grpPhotoThumbsLayout.setSpacing(2)
		self.grpPhotoThumbsLayout.setContentsMargins(-1, 3, -1, -1)
		self.lblPhoto = []
		rowsPhotos = []
		for row in range(0, 5):
			rowsPhotos.append(QtWidgets.QHBoxLayout())
			rowsPhotos[row].setSpacing(2)
			for col in range(0, 6):
				self.lblPhoto.append(QtWidgets.QLabel(self))
				self.lblPhoto[len(self.lblPhoto)-1].setMinimumSize(49, 43)
				self.lblPhoto[len(self.lblPhoto)-1].setMaximumSize(49, 43)
				self.lblPhoto[len(self.lblPhoto)-1].mousePressEvent = functools.partial(self.lblPhoto_Clicked, index=len(self.lblPhoto)-1)
				self.lblPhoto[len(self.lblPhoto)-1].setCursor(QtGui.QCursor(QtGui.Qt.PointingHandCursor))
				self.lblPhoto[len(self.lblPhoto)-1].setAlignment(QtGui.Qt.AlignCenter)
				self.lblPhoto[len(self.lblPhoto)-1].setStyleSheet("border-top: 1px solid #adadad; border-left: 1px solid #adadad; border-bottom: 1px solid #fefefe; border-right: 1px solid #fefefe;")
				rowsPhotos[row].addWidget(self.lblPhoto[len(self.lblPhoto)-1])
			self.grpPhotoThumbsLayout.addLayout(rowsPhotos[row])
		
		rowActionsGeneral3 = QtWidgets.QHBoxLayout()
		self.btnShowGameFace = QtWidgets.QPushButton("Load &Game Face")
		self.btnShowGameFace.setStyleSheet("padding: 5px 10px;")
		self.btnShowGameFace.clicked.connect(self.btnShowGameFace_Clicked)
		rowActionsGeneral3.addWidget(self.btnShowGameFace)
		self.grpPhotoThumbsLayout.addStretch()
		self.grpPhotoThumbsLayout.addLayout(rowActionsGeneral3)

		self.grpPhotoThumbsLayout.setAlignment(QtGui.Qt.AlignTop)
		self.grpPhotoThumbs.setLayout(self.grpPhotoThumbsLayout)
		
		self.layout_photos.addWidget(self.grpPhotoThumbs)
		self.layout_photos.addWidget(self.grpPhotoView)
		
		self.layout.addLayout(self.layout_options1, 0, 0)
		self.layout.addLayout(self.layout_options2, 1, 0)
		self.layout.addLayout(self.layout_photos, 2, 0)
		self.layout.addLayout(self.layout_options3, 3, 0)
		self.setLayout(self.layout)
		
		self.APP = app
		
		palette = self.APP.SETTINGS.value("PocketCameraPalette")
		try:
			palette = json.loads(palette)
		except:
			palette = None
		if palette is not None:
			for i in range(0, len(self.PALETTES)):
				if palette == self.PALETTES[i]:
					self.rowColors1.itemAt(i).widget().setChecked(True)
		
		if self.CUR_FILE is not None:
			self.OpenFile(self.CUR_FILE)

		export_path = self.APP.SETTINGS.value("LastDirPocketCamera")
		if export_path is not None:
			self.CUR_EXPORT_PATH = export_path
		
		self.SetColors()
		
		self.btnSaveAll.setDefault(True)
		self.btnSaveAll.setAutoDefault(True)
		self.btnSaveAll.setFocus()
	
	def run(self):
		self.layout.update()
		self.layout.activate()
		screenGeometry = QtWidgets.QDesktopWidget().screenGeometry()
		x = (screenGeometry.width() - self.width()) / 2
		y = (screenGeometry.height() - self.height()) / 2
		self.move(x, y)
		self.show()
	
	def SetColors(self):
		if self.CUR_PC is None: return
		for i in range(0, self.rowColors1.count()):
			if self.rowColors1.itemAt(i).widget().isChecked():
				self.CUR_PC.SetPalette(self.PALETTES[i])
		self.BuildPhotoList()
		self.UpdateViewer(self.CUR_INDEX)
	
	def OpenFile(self, file):
		self.CUR_PC = PocketCamera()
		if self.CUR_PC.LoadFile(file) == False:
			self.CUR_PC = None
			QtWidgets.QMessageBox.warning(self, "FlashGBX", "The save data file couldn’t be loaded.", QtWidgets.QMessageBox.Ok)
			return False
		self.CUR_FILE = file
		if self.CUR_EXPORT_PATH == "":
			self.CUR_EXPORT_PATH = os.path.dirname(self.CUR_FILE)
		self.UpdateViewer(1)
		self.SetColors()
		
		return True
	
	def lblPhoto_Clicked(self, event, index):
		if event.button() == QtGui.Qt.LeftButton:
			self.CUR_INDEX = index + 1
			self.UpdateViewer(self.CUR_INDEX)
	
	def lblPhotoViewer_Clicked(self, event):
		if event.button() == QtGui.Qt.LeftButton:
			self.CUR_BICUBIC = not self.CUR_BICUBIC
			self.UpdateViewer(self.CUR_INDEX)
	
	def btnOpenSRAM_Clicked(self):
		last_dir = self.APP.SETTINGS.value("LastDirSaveDataDMG")
		path = QtWidgets.QFileDialog.getOpenFileName(self, "Open GB Camera Save Data File", last_dir, "Save Data File (*.sav);;All Files (*.*)")[0]
		if (path == ""): return
		if self.OpenFile(path) is True:
			self.APP.SETTINGS.setValue("LastDirSaveDataDMG", os.path.dirname(path))
	
	def btnShowGameFace_Clicked(self, event):
		self.UpdateViewer(0)
		self.CUR_INDEX = 0
	
	def btnSaveAll_Clicked(self, event):
		if self.CUR_PC is None: return
		path = self.CUR_EXPORT_PATH + "/IMG_PC.png"
		path = QtWidgets.QFileDialog.getSaveFileName(self, "Export all pictures", path, "PNG Files (*.png);;All Files (*.*)")[0]
		if path == "": return
		self.CUR_EXPORT_PATH = os.path.dirname(path)
		
		for i in range(0, 31):
			file = os.path.splitext(path)[0] + "{:02d}".format(i) + os.path.splitext(path)[1]
			if os.path.exists(file):
				answer = QtWidgets.QMessageBox.warning(self, "FlashGBX", "There are already pictures that use the same file names. If you continue, these files will be overwritten.", QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
				if answer == QtWidgets.QMessageBox.Ok:
					break
				elif answer == QtWidgets.QMessageBox.Cancel:
					return

		for i in range(0, 31):
			file = os.path.splitext(path)[0] + "{:02d}".format(i) + os.path.splitext(path)[1]
			self.SavePicture(i, path=file)
	
	def btnSavePhoto_Clicked(self, event):
		if self.CUR_PC is None: return
		self.SavePicture(self.CUR_INDEX)
	
	def btnClose_Clicked(self, event):
		self.reject()
	
	def hideEvent(self, event):
		for i in range(0, self.rowColors1.count()):
			if self.rowColors1.itemAt(i).widget().isChecked():
				self.APP.SETTINGS.setValue("PocketCameraPalette", json.dumps(self.PALETTES[i]))
		self.APP.SETTINGS.setValue("LastDirPocketCamera", self.CUR_EXPORT_PATH)
		self.APP.activateWindow()
	
	def BuildPhotoList(self):
		cam = self.CUR_PC
		self.CUR_THUMBS = [None] * 30
		for i in range(0, 30):
			pic = cam.GetPicture(i+1).convert("RGBA")
			self.lblPhoto[i].setToolTip("")
			if cam.IsEmpty(i+1):
				pass
				#draw = ImageDraw.Draw(pic, "RGBA")
				#draw.line([0, 0, 128, 112], fill=(255, 0, 0), width=8)
				#draw.line([0, 112, 128, 0], fill=(255, 0, 0), width=8)
			elif cam.IsDeleted(i+1):
				draw_bg = Image.new("RGBA", pic.size)
				draw = ImageDraw.Draw(draw_bg)
				draw.line([0, 0, 128, 112], fill=(255, 0, 0, 192), width=8)
				draw.line([0, 112, 128, 0], fill=(255, 0, 0, 192), width=8)
				pic.paste(draw_bg, mask=draw_bg)
				self.lblPhoto[i].setToolTip("This picture was marked as “deleted” and may be overwritten when you take new pictures.")
			self.CUR_THUMBS[i] = ImageQt(pic.resize((47, 41), Image.HAMMING))
			qpixmap = QtGui.QPixmap.fromImage(self.CUR_THUMBS[i])
			self.lblPhoto[i].setPixmap(qpixmap)
	
	def UpdateViewer(self, index):
		resampler = Image.NEAREST
		if self.CUR_BICUBIC: resampler = Image.BICUBIC
		cam = self.CUR_PC
		if cam is None: return
		
		for i in range(0, 30):
			self.lblPhoto[i].setStyleSheet("border-top: 1px solid #adadad; border-left: 1px solid #adadad; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff;")
		
		if index == 0:
			self.CUR_PIC = ImageQt(cam.GetPicture(0).convert("RGBA").resize((256, 224), resampler))
		else:
			self.CUR_PIC = ImageQt(cam.GetPicture(index).convert("RGBA").resize((256, 224), resampler))
			self.lblPhoto[index - 1].setStyleSheet("border: 3px solid green; padding: 1px;")
		
		qpixmap = QtGui.QPixmap.fromImage(self.CUR_PIC)
		self.lblPhotoViewer.setPixmap(qpixmap)
	
	def SavePicture(self, index, path=""):
		if path == "":
			path = self.CUR_EXPORT_PATH + "/IMG_PC{:02d}.png".format(index)
			path = QtWidgets.QFileDialog.getSaveFileName(self, "Save Photo", path, "PNG Files (*.png);;All Files (*.*)")[0]
			if path != "": self.CUR_EXPORT_PATH = os.path.dirname(path)
		if path == "": return
		
		pnginfo = PngInfo()
		pnginfo.add_text("Software", "FlashGBX")
		pnginfo.add_text("Source", "Pocket Camera")
		pnginfo.add_text("Creation Time", email.utils.formatdate())
		
		cam = self.CUR_PC
		if index == 0:
			pic = cam.GetPicture(0)
			pnginfo.add_text("Title", "Game Face")
		else:
			pic = cam.GetPicture(index)
			pnginfo.add_text("Title", "Photo {:02d}".format(index))
		
		pic.save(path, pnginfo=pnginfo)
	
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
		if e.mimeData().hasUrls:
			for url in e.mimeData().urls():
				if platform.system() == 'Darwin':
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1] == ".sav":
					return True
		return False
	
	def dropEvent(self, e):
		if e.mimeData().hasUrls:
			e.setDropAction(QtCore.Qt.CopyAction)
			e.accept()
			for url in e.mimeData().urls():
				if platform.system() == 'Darwin':
					fn = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
				else:
					fn = str(url.toLocalFile())
				
				fn_split = os.path.splitext(os.path.abspath(fn))
				if fn_split[1] == ".sav":
					self.OpenFile(fn)
		else:
			e.ignore()

class PocketCamera:
	DATA = None
	PALETTE = [ 240, 240, 240,   218, 196, 106,   112, 88, 52,   30, 30, 30 ] # default
	IMAGES = [None] * 31
	IMAGES_DELETED = []
	ORDER = None
	
	def __init__(self):
		pass
		
	def LoadFile(self, savefile):
		if os.path.getsize(savefile) != 128*1024: return False
		with open(savefile, "rb") as file: self.DATA = file.read()
		if self.DATA[0x1FFB1:0x1FFB6] != b'Magic':
			self.DATA = None
			return False
		
		order_raw = self.DATA[0x11D7:0x11F5]
		order = [None] * 30
		deleted = []
		for i in range(0, 30):
			if order_raw[i] == 0xFF:
				deleted.append(i)
			else:
				order[order_raw[i]] = i
		
		while None in order: order.remove(None)
		order.extend(deleted)
		self.ORDER = order
		self.IMAGES_DELETED = deleted
		
		self.IMAGES[0] = self.ExtractGameFace()
		for i in range(0, 30):
			self.IMAGES[i+1] = self.ExtractPicture(i)
		return True
	
	def SetPalette(self, palette):
		for p in range (0, len(self.IMAGES)):
			self.IMAGES[p].putpalette(palette)
		self.PALETTE = palette
	
	def GetPicture(self, index):
		return self.IMAGES[index]
	
	def IsEmpty(self, index):
		return (hashlib.sha1(self.IMAGES[index].tobytes()).digest() == b'\xefX\xa8\x12\xa8\x1a\xb1EI\xd8\xf4\xfb\x86\xe9\xec\xb5J_\xb7#')
	
	def IsDeleted(self, index):
		index = self.ORDER[index-1]
		return index in self.IMAGES_DELETED
	
	def ConvertPicture(self, buffer):
		tile_width = 16
		tile_height = 14
		
		img = Image.new(mode='P', size=(128, 112))
		img.putpalette(self.PALETTE)
		pixels = img.load()
		for h in range(tile_height):
			for w in range(tile_width):
				tile_pos = 16 * ((h * tile_width) + w)
				tile = buffer[tile_pos:tile_pos+16]
				for i in range(8):
					for j in range(8):
						hi = (tile[i * 2] >> (7 - j)) & 1
						lo = (tile[i * 2 + 1] >> (7 - j)) & 1
						pixels[(w * 8) + j, (h * 8) + i] = (lo << 1 | hi)
		
		return img
	
	def ExtractGameFace(self):
		offset = 0x11FC
		imgbuffer = self.DATA[offset:offset+0x1000]
		return self.ConvertPicture(imgbuffer)
		
	def ExtractPicture(self, index):
		index = self.ORDER[index]
		offset = 0x2000 + (index * 0x1000)
		imgbuffer = self.DATA[offset:offset+0x1000]
		return self.ConvertPicture(imgbuffer)
