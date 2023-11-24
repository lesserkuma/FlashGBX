# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import hashlib, re, zlib, string, os, json, copy
from . import Util

class RomFileAGB:
	ROMFILE_PATH = None
	ROMFILE = bytearray()
	DATA = None

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
	
	def GetHeader(self, unchanged=False):
		buffer = bytearray(self.ROMFILE)
		data = {}
		hash = hashlib.sha1(buffer[0:0x180]).digest()
		nocart_hashes = []
		nocart_hashes.append(bytearray([ 0x4F, 0xE9, 0x3E, 0xEE, 0xBC, 0x55, 0x93, 0xFE, 0x2E, 0x23, 0x1A, 0x39, 0x86, 0xCE, 0x86, 0xC9, 0x5C, 0x11, 0x00, 0xDD ])) # Method 0
		nocart_hashes.append(bytearray([ 0xA5, 0x03, 0xA1, 0xB5, 0xF5, 0xDD, 0xBE, 0xFC, 0x87, 0xC7, 0x9B, 0x13, 0x59, 0xF7, 0xE1, 0xA5, 0xCF, 0xE0, 0xAC, 0x9F ])) # Method 1
		nocart_hashes.append(bytearray([ 0x46, 0x86, 0xE3, 0x81, 0xB2, 0x4A, 0x2D, 0xB0, 0x7D, 0xE8, 0x3D, 0x45, 0x2F, 0xA3, 0x1E, 0x8A, 0x04, 0x4B, 0x3A, 0x50 ])) # Method 2
		data["empty_nocart"] = hash in nocart_hashes
		data["empty"] = (buffer[0x04:0xA0] == bytearray([buffer[0x04]] * 0x9C)) or data["empty_nocart"]
		if data["empty_nocart"]: buffer = bytearray([0x00] * len(buffer))
		data["logo_correct"] = hashlib.sha1(buffer[0x04:0xA0]).digest() == bytearray([ 0x17, 0xDA, 0xA0, 0xFE, 0xC0, 0x2F, 0xC3, 0x3C, 0x0F, 0x6A, 0xBB, 0x54, 0x9A, 0x8B, 0x80, 0xB6, 0x61, 0x3B, 0x48, 0xEE ])
		data["game_title_raw"] = bytearray(buffer[0xA0:0xAC]).decode("ascii", "replace")
		game_title = data["game_title_raw"]
		game_title = re.sub(r"(\x00+)$", "", game_title)
		game_title = re.sub(r"((_)_+|(\x00)\x00+|(\s)\s+)", "\\2\\3\\4", game_title).replace("\x00", "_")
		game_title = ''.join(filter(lambda x: x in set(string.printable), game_title))
		data["game_title"] = game_title
		data["game_code_raw"] = bytearray(buffer[0xAC:0xB0]).decode("ascii", "replace")
		game_code = data["game_code_raw"]
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
		if len(game_code) == 4 and game_code[0] == "M":
			data["header_sha1"] = hashlib.sha1(buffer[0x0:0x100]).hexdigest()
		else:
			data["header_sha1"] = hashlib.sha1(buffer[0x0:0x180]).hexdigest()
		data["version"] = int(buffer[0xBC])
		data["96h_correct"] = (buffer[0xB2] == 0x96)
		data["rom_checksum_calc"] = self.CalcChecksumGlobal()
		data["rom_size_calc"] = int(len(buffer))
		data["save_type"] = None
		data["save_size"] = 0

		# 8M FLASH DACS
		data["dacs_8m"] = False
		if (data["game_title"] == "NGC-HIKARU3" and data["game_code"] == "GHTJ" and data["header_checksum"] == 0xB3):
			data["dacs_8m"] = True
		
		# e-Reader
		data["ereader"] = False
		if (data["game_title"] == "CARDE READER" and data["game_code"] == "PEAJ" and data["header_checksum"] == 0x9E) or \
		(data["game_title"] == "CARDEREADER+" and data["game_code"] == "PSAJ" and data["header_checksum"] == 0x85) or \
		(data["game_title"] == "CARDE READER" and data["game_code"] == "PSAE" and data["header_checksum"] == 0x95):
			data["ereader"] = True

		data["unchanged"] = copy.copy(data)
		self.DATA = data
		data["db"] = self.GetDatabaseEntry()

		# 3D Memory (GBA Video 64 MB)
		data["3d_memory"] = False
		if data["db"] is not None and "3d" in data["db"]:
			data["3d_memory"] = data["db"]["3d"]
		
		return data

	def GetDatabaseEntry(self):
		data = self.DATA
		db_entry = None
		if os.path.exists("{0:s}/db_AGB.json".format(Util.CONFIG_PATH)):
			with open("{0:s}/db_AGB.json".format(Util.CONFIG_PATH), encoding="UTF-8") as f:
				db = f.read()
				db = json.loads(db)
				if data["header_sha1"] in db.keys():
					db_entry = db[data["header_sha1"]]
					if db_entry["gc"] in ("ZMAJ", "ZMBJ", "ZMDE"):
						db_entry["gc"] = "AGS-{:s}".format(db_entry["gc"])
					elif db_entry["gc"] == "ZBBJ":
						db_entry["gc"] = "NTR-{:s}".format(db_entry["gc"])
					elif db_entry["gc"] == "PEAJ":
						db_entry["gc"] = "PEC-{:s}".format(db_entry["gc"])
					elif db_entry["gc"] in ("PSAJ", "PSAE"):
						db_entry["gc"] = "PES-{:s}".format(db_entry["gc"])
					else:
						db_entry["gc"] = "AGB-{:s}".format(db_entry["gc"])
		else:
			print("FAIL: Database for Game Boy Advance titles not found at {0:s}/db_AGB.json".format(Util.CONFIG_PATH))
		return db_entry
