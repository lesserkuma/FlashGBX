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
		checksum = 0
		for i in range(0x134, 0x14D):
			checksum = checksum - self.ROMFILE[i] - 1
		checksum = checksum & 0xFF
		
		if fix: self.ROMFILE[0x14D] = checksum
		return checksum
	
	def CalcChecksumGlobal(self, fix=False):
		checksum = 0
		for i in range(0, len(self.ROMFILE), 2):
			if i != 0x14E:
				checksum = checksum + self.ROMFILE[i + 1]
				checksum = checksum + self.ROMFILE[i]
		
		if fix:
			self.ROMFILE[0x14E] = checksum >> 8
			self.ROMFILE[0x14F] = checksum & 0xFF
		return checksum & 0xFFFF
	
	def FixHeader(self):
		self.CalcChecksumHeader(True)
		self.CalcChecksumGlobal(True)
		return self.ROMFILE[0:0x200]
	
	def GetHeader(self):
		buffer = self.ROMFILE
		data = {}
		if len(buffer) < 0x180: return {}
		
		data["empty"] = (buffer[0x104:0x134] == bytearray([buffer[0x104]] * 0x30))
		data["empty_nocart"] = (buffer == bytearray([0x00] * len(buffer)))
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
		data["version"] = int(buffer[0x14C])
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

		# Unlicensed 256M Mapper
		elif data["game_title"].upper() == "GB HICOL" and data["header_checksum"] in (0x4A, 0x49, 0xE9):
			data["features_raw"] = 0x201
			data["rom_size_raw"] = 0x0A
			data["ram_size_raw"] = 0x201
		
		# Unlicensed Wisdom Tree Mapper
		elif hashlib.sha1(buffer[0x0:0x150]).digest() == bytearray([ 0xF5, 0xD2, 0x91, 0x7D, 0x5E, 0x5B, 0xAB, 0xD8, 0x5F, 0x0A, 0xC7, 0xBA, 0x56, 0xEB, 0x49, 0x8A, 0xBA, 0x12, 0x49, 0x13 ]): # Exodus / Joshua
			data["features_raw"] = 0x202
			data["rom_size_raw"] = 0x02
		elif hashlib.sha1(buffer[0x0:0x150]).digest() == bytearray([ 0xE9, 0xF8, 0x32, 0x78, 0x39, 0x19, 0xE3, 0xB2, 0xFC, 0x6F, 0xC2, 0x60, 0x30, 0x33, 0x20, 0xD0, 0x3B, 0x1A, 0xA9, 0xA2 ]): # Spiritual Warfare
			data["features_raw"] = 0x202
			data["rom_size_raw"] = 0x03
		elif hashlib.sha1(buffer[0x0:0x150]).digest() == bytearray([ 0xE6, 0xC0, 0x39, 0x7F, 0xA5, 0x99, 0xD6, 0x60, 0xD7, 0x90, 0x45, 0xB9, 0xF0, 0x64, 0x3B, 0x2A, 0x41, 0xA4, 0xD6, 0x35 ]): # King James Bible
			data["features_raw"] = 0x202
			data["rom_size_raw"] = 0x05
		elif hashlib.sha1(buffer[0x0:0x150]).digest() == bytearray([ 0x36, 0x89, 0x60, 0xDD, 0x1B, 0xE1, 0x73, 0x86, 0x8B, 0x24, 0xA3, 0xDC, 0x57, 0xA5, 0xCB, 0x7C, 0xCA, 0x62, 0xDD, 0x34 ]): # NIV Bible
			data["features_raw"] = 0x202
			data["rom_size_raw"] = 0x06
		

		if data["features_raw"] in Util.DMG_Header_Mapper:
			data["features"] = Util.DMG_Header_Mapper[data["features_raw"]]
		elif data["logo_correct"]:
			print("{:s}WARNING: Unknown memory bank controller type 0x{:02X}{:s}".format(Util.ANSI.YELLOW, data["features_raw"], Util.ANSI.RESET))

		return data
