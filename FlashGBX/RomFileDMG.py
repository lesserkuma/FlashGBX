# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import hashlib, re, string
from . import Util

class RomFileDMG:
	ROMFILE_PATH = None
	ROMFILE = bytearray()
	
	def __init__(self, file=None):
		if isinstance(file, str):
			self.Open(file)
		elif isinstance(file, bytearray):
			self.ROMFILE = file
	
	def Open(self, file):
		self.ROMFILE_PATH = file
		self.Load()
	
	def Load(self):
		with open(self.ROMFILE_PATH, "rb") as f:
			self.ROMFILE = bytearray(f.read(0x1000))
	
	def CalcChecksumHeader(self, fix=False):
		buffer = self.ROMFILE
		checksum = 0
		for i in range(0x134, 0x14D):
			checksum = checksum - buffer[i] - 1
		checksum = checksum & 0xFF
		
		if fix: buffer[0x14D] = checksum
		return checksum
	
	def CalcChecksumGlobal(self, fix=False):
		buffer = self.ROMFILE
		checksum = 0
		for i in range(0, len(buffer), 2):
			if i != 0x14E:
				checksum = checksum + buffer[i + 1]
				checksum = checksum + buffer[i]
		
		if fix:
			buffer[0x14E] = checksum >> 8
			buffer[0x14F] = checksum & 0xFF
		return checksum & 0xFFFF
	
	def FixChecksums(self):
		self.CalcChecksumHeader(True)
		self.CalcChecksumGlobal(True)
	
	def GetHeader(self):
		buffer = self.ROMFILE
		data = {}
		data["empty"] = (self.ROMFILE == bytearray([buffer[0]] * len(buffer)))
		data["logo_correct"] = hashlib.sha1(buffer[0x104:0x134]).digest() == bytearray([ 0x07, 0x45, 0xFD, 0xEF, 0x34, 0x13, 0x2D, 0x1B, 0x3D, 0x48, 0x8C, 0xFB, 0xDF, 0x03, 0x79, 0xA3, 0x9F, 0xD5, 0x4B, 0x4C ])
		data["cgb"] = int(buffer[0x143])
		data["sgb"] = int(buffer[0x146])
		
		if data["cgb"] in (0x00, 0x80, 0xC0):
			game_title = bytearray(buffer[0x134:0x143]).decode("ascii", "replace")
		else:
			game_title = bytearray(buffer[0x134:0x144]).decode("ascii", "replace")
		game_title = re.sub(r"(\x00+)$", "", game_title)
		game_title = re.sub(r"((_)_+|(\x00)\x00+|(\s)\s+)", "\\2\\3\\4", game_title).replace("\x00", "_")
		game_title = ''.join(filter(lambda x: x in set(string.printable), game_title))
		data["game_title"] = game_title

		data["maker_code"] = format(int(buffer[0x14B]), "02X")
		if data["maker_code"] == '33':
			maker_code = bytearray(buffer[0x144:0x146]).decode("ascii", "replace")
			maker_code = ''.join(filter(lambda x: x in set(string.printable), maker_code))
			data["maker_code_new"] = maker_code
		data["features_raw"] = int(buffer[0x147])
		data["features"] = "?"
		data["rom_size_raw"] = int(buffer[0x148])
		data["rom_size"] = "?"
		if buffer[0x148] in Util.DMG_Header_ROM_Sizes: data["rom_size"] = Util.DMG_Header_ROM_Sizes[buffer[0x148]]
		data["ram_size_raw"] = int(buffer[0x149])
		if data["features_raw"] == 0x05 or data["features_raw"] == 0x06:
			data["ram_size"] = 0x200
		else:
			data["ram_size"] = "?"
			if buffer[0x149] in Util.DMG_Header_RAM_Sizes:
				data["ram_size"] = Util.DMG_Header_RAM_Sizes[buffer[0x149]]
		data["header_checksum"] = int(buffer[0x14D])
		data["header_checksum_calc"] = self.CalcChecksumHeader()
		data["header_checksum_correct"] = data["header_checksum"] == data["header_checksum_calc"]
		data["rom_checksum"] = int(256 * buffer[0x14E] + buffer[0x14F])
		data["rom_checksum_calc"] = self.CalcChecksumGlobal()
		data["rom_checksum_correct"] = data["rom_checksum"] == data["rom_checksum_calc"]

		# MBC1M
		if data["features_raw"] == 0x03 and data["game_title"] == "MOMOCOL" and data["header_checksum"] == 0x28 or \
		data["features_raw"] == 0x01 and data["game_title"] == "BOMCOL" and data["header_checksum"] == 0x86 or \
		data["features_raw"] == 0x01 and data["game_title"] == "GENCOL" and data["header_checksum"] == 0x8A or \
		data["features_raw"] == 0x01 and data["game_title"] == "SUPERCHINESE 123" and data["header_checksum"] == 0xE4 or \
		data["features_raw"] == 0x01 and data["game_title"] == "MORTALKOMBATI&II" and data["header_checksum"] == 0xB9 or \
		data["features_raw"] == 0x01 and data["game_title"] == "MORTALKOMBAT DUO" and data["header_checksum"] == 0xA7:
			data["features_raw"] += 0x100

		# GB Memory
		if data["features_raw"] == 0x19 and data["game_title"] == "NP M-MENU MENU" and data["header_checksum"] == 0xD3:
			data["features_raw"] = 0x105
			data["ram_size_raw"] = 0x04
		
		# M161 (Mani 4 in 1)
		elif data["features_raw"] == 0x10 and data["game_title"] == "TETRIS SET" and data["header_checksum"] == 0x3F:
			data["features_raw"] = 0x104
		
		# MMM01 (Mani 4 in 1)
		elif data["features_raw"] == 0x11 and data["game_title"] == "BOUKENJIMA2 SET" and data["header_checksum"] == 0 or \
		data["features_raw"] == 0x11 and data["game_title"] == "BUBBLEBOBBLE SET" and data["header_checksum"] == 0xC6 or \
		data["features_raw"] == 0x11 and data["game_title"] == "GANBARUGA SET" and data["header_checksum"] == 0x90 or \
		data["features_raw"] == 0x11 and data["game_title"] == "RTYPE 2 SET" and data["header_checksum"] == 0x32:
			data["features_raw"] = 0x0B

		if data["features_raw"] in Util.DMG_Header_Mapper:
			data["features"] = Util.DMG_Header_Mapper[data["features_raw"]]
		elif data["logo_correct"]:
			print("{:s}WARNING: Unknown memory bank controller type 0x{:02X}{:s}".format(Util.ANSI.YELLOW, data["features_raw"], Util.ANSI.RESET))

		return data
	
	def GetData(self):
		return self.ROMFILE
