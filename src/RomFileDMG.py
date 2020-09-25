# -*- coding: utf-8 -*-
# ＵＴＦ－８
import hashlib, re, sys, string

class RomFileDMG:
	DMG_Header_Features = { 0x00:'ROM ONLY', 0x01:'MBC1', 0x02:'MBC1+RAM', 0x03:'MBC1+RAM+BATTERY', 0x05:'MBC2', 0x06:'MBC2+BATTERY', 0x08:'ROM+RAM', 0x09:'ROM+RAM+BATTERY', 0x0B:'MMM01', 0x0C:'MMM01+RAM', 0x0D:'MMM01+RAM+BATTERY', 0x0F:'MBC3+TIMER+BATTERY', 0x10:'MBC3+TIMER+RAM+BATTERY', 0x11:'MBC3', 0x12:'MBC3+RAM', 0x13:'MBC3+RAM+BATTERY', 0x15:'MBC4', 0x16:'MBC4+RAM', 0x17:'MBC4+RAM+BATTERY', 0x19:'MBC5', 0x1A:'MBC5+RAM', 0x1B:'MBC5+RAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1D:'MBC5+RUMBLE+RAM', 0x1E:'MBC5+RUMBLE+RAM+BATTERY', 0x20:'MBC6', 0x22:'MBC7+SENSOR+RUMBLE+RAM+BATTERY', 0x55:'Game Genie', 0x56:'Game Genie v3.0', 0xFC:'POCKET CAMERA', 0xFD:'BANDAI TAMA5', 0xFE:'HuC3', 0xFF:'HuC1+RAM+BATTERY' }
	DMG_Header_ROM_Sizes = { 0x00:0x8000, 0x01:0x10000, 0x02:0x20000, 0x03:0x40000, 0x04:0x80000, 0x05:0x100000, 0x52:0x120000, 0x53:0x140000, 0x54:0x180000, 0x06:0x200000, 0x07:0x400000, 0x08:0x800000 }
	DMG_Header_RAM_Sizes = { 0x00:0, 0x01:0x800, 0x02:0x2000, 0x03:0x8000, 0x05:0x10000, 0x04:0x20000 }
	DMG_Header_SGB = { 0x00:'No support', 0x03:'Supported' }
	DMG_Header_CGB = { 0x00:'No support', 0x80:'Supported', 0xC0:'Required' }
	
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
		data["logo_correct"] = hashlib.sha1(buffer[0x104:0x134]).digest() == bytearray([ 0x07, 0x45, 0xFD, 0xEF, 0x34, 0x13, 0x2D, 0x1B, 0x3D, 0x48, 0x8C, 0xFB, 0xDF, 0x03, 0x79, 0xA3, 0x9F, 0xD5, 0x4B, 0x4C ])
		game_title = bytearray(buffer[0x134:0x143]).decode("ascii", "replace")
		game_title = re.sub(r"(\x00+)$", "", game_title).replace("\x00", "_")
		game_title = ''.join(filter(lambda x: x in set(string.printable), game_title))
		data["game_title"] = game_title
		data["maker_code"] = format(int(buffer[0x14B]), "02X")
		if data["maker_code"] == '33':
			maker_code = bytearray(buffer[0x144:0x146]).decode("ascii", "replace")
			maker_code = ''.join(filter(lambda x: x in set(string.printable), maker_code))
			data["maker_code_new"] = maker_code
		data["cgb"] = int(buffer[0x143])
		data["sgb"] = int(buffer[0x146])
		data["features_raw"] = int(buffer[0x147])
		data["features"] = "?"
		if buffer[0x147] in self.DMG_Header_Features: data["features"] = self.DMG_Header_Features[buffer[0x147]]
		data["rom_size_raw"] = int(buffer[0x148])
		data["rom_size"] = "?"
		if buffer[0x148] in self.DMG_Header_ROM_Sizes: data["rom_size"] = self.DMG_Header_ROM_Sizes[buffer[0x148]]
		data["ram_size_raw"] = int(buffer[0x149])
		if data["features"] == 0x05 or data["features"] == 0x06:
			data["ram_size"] = 0x200
		else:
			data["ram_size"] = "?"
			if buffer[0x149] in self.DMG_Header_RAM_Sizes: data["ram_size"] = self.DMG_Header_RAM_Sizes[buffer[0x149]]
		data["header_checksum"] = int(buffer[0x14D])
		data["header_checksum_calc"] = self.CalcChecksumHeader()
		data["header_checksum_correct"] = data["header_checksum"] == data["header_checksum_calc"]
		data["rom_checksum"] = int(256 * buffer[0x14E] + buffer[0x14F])
		data["rom_checksum_calc"] = self.CalcChecksumGlobal()
		data["rom_checksum_correct"] = data["rom_checksum"] == data["rom_checksum_calc"]
		return data
	
	def GetData(self):
		return self.ROMFILE
