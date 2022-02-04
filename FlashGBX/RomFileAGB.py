# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import hashlib, re, zlib, string

class RomFileAGB:
	ROMFILE_PATH = None
	ROMFILE = bytearray()
	
	def __init__(self, file=None):
		if isinstance(file, str):
			self.ROMFILE_PATH = file
			if self.ROMFILE_PATH != None: self.Load()
		elif isinstance(file, bytearray):
			self.ROMFILE = file
	
	def Open(self, file):
		self.ROMFILE_PATH = file
		self.Load()
	
	def Load(self):
		with open(self.ROMFILE_PATH, "rb") as f:
			self.ROMFILE = bytearray(f.read())
	
	def CalcChecksumHeader(self, fix=False):
		checksum = 0
		for i in range(0xA0, 0xBD):
			checksum = checksum - self.ROMFILE[i]
		checksum = (checksum - 0x19) & 0xFF
		
		if fix: self.ROMFILE[0xBD] = checksum
		return checksum
	
	def CalcChecksumGlobal(self):
		return (zlib.crc32(self.ROMFILE) & 0xFFFFFFFF)
	
	def FixHeader(self):
		self.CalcChecksumHeader(True)
		return self.ROMFILE[0:0x200]
	
	def GetHeader(self):
		buffer = self.ROMFILE
		data = {}
		data["empty"] = (buffer[0x04:0xA0] == bytearray([buffer[0x04]] * 0x9C))
		data["empty_nocart"] = (buffer == bytearray([0x00] * len(buffer)))
		data["logo_correct"] = hashlib.sha1(buffer[0x04:0xA0]).digest() == bytearray([ 0x17, 0xDA, 0xA0, 0xFE, 0xC0, 0x2F, 0xC3, 0x3C, 0x0F, 0x6A, 0xBB, 0x54, 0x9A, 0x8B, 0x80, 0xB6, 0x61, 0x3B, 0x48, 0xEE ])
		game_title = bytearray(buffer[0xA0:0xAC]).decode("ascii", "replace")
		game_title = re.sub(r"(\x00+)$", "", game_title)
		game_title = re.sub(r"((_)_+|(\x00)\x00+|(\s)\s+)", "\\2\\3\\4", game_title).replace("\x00", "_")
		game_title = ''.join(filter(lambda x: x in set(string.printable), game_title))
		data["game_title"] = game_title
		game_code = bytearray(buffer[0xAC:0xB0]).decode("ascii", "replace")
		game_code = re.sub(r"(\x00+)$", "", game_code)
		game_title = re.sub(r"((_)_+|(\x00)\x00+|(\s)\s+)", "\\2\\3\\4", game_title).replace("\x00", "_")
		game_code = ''.join(filter(lambda x: x in set(string.printable), game_code))
		data["game_code"] = game_code
		maker_code = bytearray(buffer[0xB0:0xB2]).decode("ascii", "replace")
		maker_code = re.sub(r"(\x00+)$", "", maker_code)
		game_title = re.sub(r"((_)_+|(\x00)\x00+|(\s)\s+)", "\\2\\3\\4", game_title).replace("\x00", "_")
		maker_code = ''.join(filter(lambda x: x in set(string.printable), maker_code))
		
		data["maker_code"] = maker_code
		data["header_checksum"] = int(buffer[0xBD])
		data["header_checksum_calc"] = self.CalcChecksumHeader()
		data["header_checksum_correct"] = data["header_checksum"] == data["header_checksum_calc"]
		data["header_sha1"] = hashlib.sha1(buffer[0x00:0xC0]).hexdigest()
		data["version"] = int(buffer[0xBC])
		data["96h_correct"] = (buffer[0xB2] == 0x96)
		data["rom_checksum_calc"] = self.CalcChecksumGlobal()
		data["rom_size_calc"] = int(len(buffer))
		data["save_type"] = None
		data["save_size"] = 0

		# 3D Memory (GBA Video 64 MB)
		data["3d_memory"] = False
		if (data["game_title"] == "DISNEYVOL002" and data["game_code"] == "MDSE" and data["header_checksum"] == 0x58) or \
		(data["game_title"] == "SHARKS TALE" and data["game_code"] == "MSAE" and data["header_checksum"] == 0x98) or \
		(data["game_title"] == "SHARKS TALE" and data["game_code"] == "MSAE" and data["header_checksum"] == 0x97) or \
		(data["game_title"] == "SHREK MOVIE" and data["game_code"] == "MSKE" and data["header_checksum"] == 0x83) or \
		(data["game_title"] == "SHREK MOVIE" and data["game_code"] == "MSKE" and data["header_checksum"] == 0x82) or \
		(data["game_title"] == "SHREKSHARK21" and data["game_code"] == "MSTE" and data["header_checksum"] == 0x3E) or \
		(data["game_title"] == "SHREK2MOVIE" and data["game_code"] == "M2SE" and data["header_checksum"] == 0x8A) or \
		(data["game_title"] == "SHREK2MOVIE" and data["game_code"] == "M2SE" and data["header_checksum"] == 0x89):
			data["3d_memory"] = True

		# 8M FLASH DACS
		data["dacs_8m"] = False
		if (data["game_title"] == "NGC-HIKARU3" and data["game_code"] == "GHTJ" and data["header_checksum"] == 0xB3):
			data["dacs_8m"] = True
		
		return data
