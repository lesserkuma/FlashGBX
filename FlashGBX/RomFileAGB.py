# -*- coding: utf-8 -*-
# ＵＴＦ－８
import hashlib, re, zlib, sys, string

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
		buffer = self.ROMFILE
		checksum = 0
		for i in range(0xA0, 0xBD):
			checksum = checksum - buffer[i]
		checksum = (checksum - 0x19) & 0xFF
		
		if fix: buffer[0x14D] = checksum
		return checksum
	
	def CalcChecksumGlobal(self):
		buffer = self.ROMFILE
		return (zlib.crc32(buffer) & 0xffffffff)
	
	def FixChecksums(self):
		self.CalcChecksumHeader(True)
	
	def GetHeader(self):
		buffer = self.ROMFILE
		data = {}
		data["empty"] = (self.ROMFILE == bytearray([buffer[0]] * len(buffer)))
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
		return data

	def GetData(self):
		return self.ROMFILE
