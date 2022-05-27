# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import math, time, datetime, copy, configparser, threading, statistics, os, platform, traceback, io, struct
from enum import Enum

# Common constants
APPNAME = "FlashGBX"
VERSION_PEP440 = "3.12"
VERSION = "v{:s}".format(VERSION_PEP440)
DEBUG = False

AGB_Header_ROM_Sizes = [ "1 MB", "2 MB", "4 MB", "8 MB", "16 MB", "32 MB", "64 MB", "128 MB", "256 MB" ]
AGB_Header_ROM_Sizes_Map = [ 0x100000, 0x200000, 0x400000, 0x800000, 0x1000000, 0x2000000, 0x4000000, 0x8000000, 0x10000000 ]
AGB_Header_Save_Types = [ "None", "4K EEPROM (512 Bytes)", "64K EEPROM (8 KB)", "256K SRAM/FRAM (32 KB)", "512K FLASH (64 KB)", "1M FLASH (128 KB)", "8M DACS (1008 KB)", "Unlicensed 512K SRAM (64 KB)", "Unlicensed 1M SRAM (128 KB)" ]
AGB_Header_Save_Sizes = [ 0, 512, 8192, 32768, 65536, 131072, 1032192, 65536, 131072 ]
AGB_Global_CRC32 = 0
AGB_Flash_Save_Chips = { 0xBFD4:"SST 39VF512", 0x1F3D:"Atmel AT29LV512", 0xC21C:"Macronix MX29L512", 0x321B:"Panasonic MN63F805MNP", 0xC209:"Macronix MX29L010", 0x6213:"SANYO LE26FV10N1TS" }
AGB_Flash_Save_Chips_Sizes = [ 0x10000, 0x10000, 0x10000, 0x10000, 0x20000, 0x20000 ]

DMG_Header_Mapper = { 0x00:'None', 0x01:'MBC1', 0x02:'MBC1+SRAM', 0x03:'MBC1+SRAM+BATTERY', 0x06:'MBC2+SRAM+BATTERY', 0x10:'MBC3+RTC+SRAM+BATTERY', 0x13:'MBC3+SRAM+BATTERY', 0x19:'MBC5', 0x1A:'MBC5+SRAM', 0x1B:'MBC5+SRAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1E:'MBC5+RUMBLE+SRAM+BATTERY', 0x20:'MBC6+SRAM+FLASH+BATTERY', 0x22:'MBC7+ACCELEROMETER+EEPROM', 0x101:'MBC1M', 0x103:'MBC1M+SRAM+BATTERY', 0x0B:'MMM01',  0x0D:'MMM01+SRAM+BATTERY', 0xFC:'GBD+SRAM+BATTERY', 0x105:'G-MMC1+SRAM+BATTERY', 0x104:'M161', 0xFF:'HuC-1+IR+SRAM+BATTERY', 0xFE:'HuC-3+RTC+SRAM+BATTERY', 0xFD:'TAMA5+RTC+EEPROM', 0x201:'Unlicensed 256M Mapper', 0x202:'Unlicensed Wisdom Tree Mapper', 0x203:'Unlicensed Xploder GB Mapper', 0x204:'Unlicensed Sachen Mapper', 0x205:'Unlicensed Datel Orbit V2 Mapper' }
DMG_Header_ROM_Sizes = [ "32 KB", "64 KB", "128 KB", "256 KB", "512 KB", "1 MB", "2 MB", "4 MB", "8 MB", "16 MB", "32 MB" ]
DMG_Header_ROM_Sizes_Map = [ 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A ]
DMG_Header_ROM_Sizes_Flasher_Map = [ 0x8000, 0x10000, 0x20000, 0x40000, 0x80000, 0x100000, 0x200000, 0x400000, 0x800000, 0x1000000, 0x2000000 ]
DMG_Header_RAM_Sizes = [ "None", "4K SRAM (512 Bytes)", "16K SRAM (2 KB)", "64K SRAM (8 KB)", "256K SRAM (32 KB)", "512K SRAM (64 KB)", "1M SRAM (128 KB)", "MBC6 SRAM+FLASH (1.03 MB)", "MBC7 2K EEPROM (256 Bytes)", "MBC7 4K EEPROM (512 Bytes)", "TAMA5 EEPROM (32 Bytes)", "Unlicensed 4M SRAM (512 KB)", "Unlicensed 1M EEPROM (128 KB)" ]
DMG_Header_RAM_Sizes_Map = [ 0x00, 0x01, 0x01, 0x02, 0x03, 0x05, 0x04, 0x104, 0x101, 0x102, 0x103, 0x201, 0x203 ]
DMG_Header_RAM_Sizes_Flasher_Map = [ 0, 0x200, 0x800, 0x2000, 0x8000, 0x10000, 0x20000, 0x108000, 0x100, 0x200, 0x20, 0x80000, 0x20000 ] # RAM size in bytes
DMG_Header_SGB = { 0x00:'No support', 0x03:'Supported' }
DMG_Header_CGB = { 0x00:'No support', 0x80:'Supported', 0xC0:'Required' }

class ANSI:
	BOLD = '\033[1m'
	RED = '\033[91m'
	GREEN = '\033[92m'
	YELLOW = '\033[33m'
	DARK_GRAY = '\033[90m'
	RESET = '\033[0m'
	CLEAR_LINE = '\033[2K'

class IniSettings():
	FILENAME = ""
	SETTINGS = None
	MAIN_SECTION = "General"
	def __init__(self, path="", ini="", main_section="General"):
		if path != "":
			try:
				if not os.path.isdir(os.path.dirname(path)):
					os.makedirs(os.path.dirname(path))
				if os.path.exists(path):
					with open(path, "a+") as f: f.close()
				else:
					with open(path, "w+") as f: f.close()
			except:
				print("Error accessing the configuration directory or settings file.")
				return
			self.FILENAME = path
			self.SETTINGS = configparser.RawConfigParser()
			self.SETTINGS.optionxform = str
			try:
				self.Reload()
			except configparser.MissingSectionHeaderError:
				print("Resetting invalid configuration file...")
				os.unlink(path)
				path = ""
		
		if path == "":
			self.FILENAME = False
			self.SETTINGS = configparser.RawConfigParser()
			self.SETTINGS.read_string(ini)
			self.SETTINGS.optionxform = str
		
		self.MAIN_SECTION = main_section
	
	def Reload(self):
		if self.SETTINGS is None: return
		if self.FILENAME is not False:
			with open(self.FILENAME, "r", encoding="utf-8") as f:
				self.SETTINGS.read_file(f)
		if len(self.SETTINGS.sections()) == 0:
			self.SETTINGS.add_section(self.MAIN_SECTION)
	
	def value(self, key, default=None): return self.GetValue(key, default)
	def GetValue(self, key, default=None):
		if self.SETTINGS is None: return None
		self.Reload()
		if key not in self.SETTINGS[self.MAIN_SECTION]:
			if default is not None: self.SetValue(key, default)
			return default
		return (self.SETTINGS[self.MAIN_SECTION][key])
	
	def setValue(self, key, value): self.SetValue(key, value)
	def SetValue(self, key, value):
		if self.SETTINGS is None: return None
		self.Reload()
		self.SETTINGS[self.MAIN_SECTION][key] = value
		dprint("Updating settings:", key, "=", value)
		if self.FILENAME is not False:
			with open(self.FILENAME, "w", encoding="utf-8") as f:
				self.SETTINGS.write(f)
	
	def clear(self): self.Clear()
	def Clear(self):
		if self.SETTINGS is None: return None
		self.SETTINGS.clear()
		if self.FILENAME is not False:
			with open(self.FILENAME, "w", encoding="utf-8") as f:
				self.SETTINGS.write(f)

class Progress():
	MUTEX = threading.Lock()
	PROGRESS = {}
	UPDATER = None
	
	def __init__(self, updater):
		self.UPDATER = updater
	
	def SetProgress(self, args):
		self.MUTEX.acquire(1)
		try:
			if not "method" in self.PROGRESS: self.PROGRESS = {}
			now = time.time()
			if args["action"] == "INITIALIZE":
				self.PROGRESS["action"] = args["action"]
				self.PROGRESS["method"] = args["method"]
				if "size" in args:
					self.PROGRESS["size"] = args["size"]
				else:
					self.PROGRESS["size"] = 0
				if "pos" in args:
					self.PROGRESS["pos"] = args["pos"]
				else:
					self.PROGRESS["pos"] = 0
				if "time_start" in args:
					self.PROGRESS["time_start"] = args["time_start"]
				else:
					self.PROGRESS["time_start"] = now
				self.PROGRESS["time_last_emit"] = now
				self.PROGRESS["time_last_update_speed"] = now
				self.PROGRESS["time_left"] = 0
				self.PROGRESS["speed"] = 0
				self.PROGRESS["speeds"] = []
				self.PROGRESS["bytes_last_update_speed"] = 0
				self.UPDATER(self.PROGRESS)
			
			if args["action"] == "ABORT":
				self.UPDATER(args)
				self.PROGRESS = {}
			
			elif args["action"] in ("ERASE", "SECTOR_ERASE", "UNLOCK", "UPDATE_RTC"):
				if "time_start" in self.PROGRESS:
					args["time_elapsed"] = now - self.PROGRESS["time_start"]
				elif "time_start" in args:
					args["time_elapsed"] = now - args["time_start"]
				args["pos"] = 1
				args["size"] = 0
				self.UPDATER(args)
			
			elif self.PROGRESS == {}:
				return
			
			elif args["action"] == "UPDATE_POS":
				self.PROGRESS["pos"] = args["pos"]
				self.PROGRESS["action"] = "PROGRESS"
				if "time_start" in self.PROGRESS:
					self.PROGRESS["time_elapsed"] = now - self.PROGRESS["time_start"]
				
				try:
					total_speed = statistics.mean(self.PROGRESS["speeds"])
					self.PROGRESS["time_left"] = (self.PROGRESS["size"] - self.PROGRESS["pos"]) / 1024 / total_speed
				except:
					pass
				if "abortable" in args: self.PROGRESS["abortable"] = args["abortable"]
				self.UPDATER(self.PROGRESS)
			
			elif args["action"] in ("READ", "WRITE"):
				if "method" not in self.PROGRESS: return
				elif args["action"] in ("READ") and self.PROGRESS["method"] in ("SAVE_WRITE", "ROM_WRITE"): return
				elif args["action"] in ("WRITE") and self.PROGRESS["method"] in ("SAVE_READ", "ROM_READ", "ROM_WRITE_VERIFY"): return
				if self.PROGRESS["pos"] >= self.PROGRESS["size"]: return
				
				self.PROGRESS["action"] = "PROGRESS"
				self.PROGRESS["pos"] += args["bytes_added"]
				if (now - self.PROGRESS["time_last_emit"]) > 0.05:
					self.PROGRESS["time_elapsed"] = now - self.PROGRESS["time_start"]
					if (now - self.PROGRESS["time_last_update_speed"]) > 0.25:
						time_delta = now - self.PROGRESS["time_last_update_speed"]
						pos_delta = self.PROGRESS["pos"] - self.PROGRESS["bytes_last_update_speed"]
						if time_delta > 0:
							speed = (pos_delta / time_delta) / 1024
							self.PROGRESS["speeds"].append(speed)
							if len(self.PROGRESS["speeds"]) > 256: self.PROGRESS["speeds"].pop(0)
							self.PROGRESS["speed"] = statistics.median(self.PROGRESS["speeds"])
						self.PROGRESS["time_last_update_speed"] = now
						self.PROGRESS["bytes_last_update_speed"] = self.PROGRESS["pos"]
					
					if "skipping" in args and args["skipping"] is True:
						self.PROGRESS["speed"] = 0
						self.PROGRESS["skipping"] = True
					else:
						self.PROGRESS["skipping"] = False
					
					if self.PROGRESS["speed"] > 0:
						total_speed = statistics.mean(self.PROGRESS["speeds"])
						self.PROGRESS["time_left"] = (self.PROGRESS["size"] - self.PROGRESS["pos"]) / 1024 / total_speed
					
					self.UPDATER(self.PROGRESS)
					self.PROGRESS["time_last_emit"] = now
			
			elif args["action"] == "FINISHED":
				self.PROGRESS["pos"] = self.PROGRESS["size"]
				self.UPDATER(self.PROGRESS)
				self.PROGRESS["action"] = args["action"]
				self.PROGRESS["bytes_last_update_speed"] = self.PROGRESS["size"]
				self.PROGRESS["time_elapsed"] = now - self.PROGRESS["time_start"]
				self.PROGRESS["time_last_emit"] = now
				self.PROGRESS["time_last_update_speed"] = now
				self.PROGRESS["time_left"] = 0
				if self.PROGRESS["time_elapsed"] == 0: self.PROGRESS["time_elapsed"] = 0.001
				self.PROGRESS["speed"] = (self.PROGRESS["size"] / self.PROGRESS["time_elapsed"]) / 1024
				self.PROGRESS["bytes_last_emit"] = self.PROGRESS["size"]
				if "verified" in args:
					self.PROGRESS["verified"] = (args["verified"] == True)
				
				if self.PROGRESS["speed"] > self.PROGRESS["size"] / 1024:
					self.PROGRESS["speed"] = self.PROGRESS["size"] / 1024
				
				self.UPDATER(self.PROGRESS)
				del(self.PROGRESS["method"])
		
		finally:
			self.MUTEX.release()

class TAMA5_CMD(Enum):
	RAM_WRITE = 0x0
	RAM_READ = 0x1
	RTC = 0x4

class TAMA5_REG(Enum):
	ROM_BANK_L = 0x0
	ROM_BANK_H = 0x1
	MEM_WRITE_L = 0x4
	MEM_WRITE_H = 0x5
	ADDR_H_SET_MODE = 0x6
	ADDR_L = 0x7
	ENABLE = 0xA
	MEM_READ_L = 0xC
	MEM_READ_H = 0xD

def isx2bin(buffer):
	data_input = io.BytesIO(buffer)
	data_output = bytearray(8 * 1024 * 1024)
	rom_size = 0
	temp = 32 * 1024
	while 1:
		try:
			type = struct.unpack('B', data_input.read(1))[0]
			if type == 4:
				break
			elif type != 1:
				print("WARNING: Unhandled ISX record type 0x{:02X} found. Converted ROM may not be working correctly.".format(type))
				continue
			bank = struct.unpack('B', data_input.read(1))[0]
			offset = struct.unpack('<H', data_input.read(2))[0] % 0x4000
			realoffset = bank * 16 * 1024 + offset
			size = struct.unpack('<H', data_input.read(2))[0]
			data_output[realoffset:realoffset+size] = data_input.read(size)
			rom_size = max(rom_size, realoffset+size)
			temp = 32 * 1024
			while temp < rom_size: temp *= 2
		except:
			print("ERROR: Couldn’t convert ISX file correctly.")
			break
	return data_output[:temp]

def roundup(x):
	# https://stackoverflow.com/questions/50405017/
	d = 10 ** 2
	if x < 0:
		return math.floor(x * d) / d
	else:
		return math.ceil(x * d) / d

def formatFileSize(size, asInt=False, roundUp=False):
	if size == 1:
		return "{:d} Byte".format(size)
	elif size < 1024:
		return "{:d} Bytes".format(size)
	elif size < 1024 * 1024:
		val = size/1024
		if roundUp: val = roundup(val)
		if asInt:
			return "{:d} KB".format(int(val))
		else:
			return "{:.1f} KB".format(val)
	else:
		val = size/1024/1024
		if roundUp: val = roundup(val)
		if asInt:
			return "{:d} MB".format(int(val))
		else:
			return "{:.2f} MB".format(val)

def formatProgressTimeShort(sec):
	sec = sec % (24 * 3600)
	hr = sec // 3600
	sec %= 3600
	min = sec // 60
	sec %= 60
	return "{:02d}:{:02d}:{:02d}".format(int(hr), int(min), int(sec))

def formatProgressTime(sec):
	if int(sec) == 1:
		return "{:d} second".format(int(sec))
	elif sec < 60:
		return "{:d} seconds".format(int(sec))
	elif int(sec) == 60:
		return "1 minute"
	else:
		min = int(sec / 60)
		sec = int(sec % 60)
		s = str(min) + " "
		if min == 1:
			s = s + "minute"
		else:
			s = s + "minutes"
		s = s + ", " + str(sec) + " "
		if sec == 1:
			s = s + "second"
		else:
			s = s + "seconds"
		return s

def formatPathOS(path, end_sep=False):
	if platform.system() == "Windows":
		path = path.replace("/", "\\")
		if end_sep:
			path += "\\"
	else:
		if end_sep:
			path += "/"
	return path

def bitswap(n, s):
	p, q = s
	if (((n & (1 << p)) >> p) ^ ((n & (1 << q)) >> q)) == 1:
		n ^= (1 << p)
		n ^= (1 << q)
	return n

def DecodeBCD(value):
	return (((value) & 0x0F) + (((value) >> 4) * 10))
def EncodeBCD(value):
	return math.floor(value / 10) << 4 | value % 10

def ParseCFI(buffer):
	buffer = copy.copy(buffer)
	info = {}
	magic = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
	if magic != "QRY": # nothing swapped
		return False
	
	try:
		info["flash_id"] = buffer[0:8]
		info["magic"] = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
		
		if buffer[0x36] == 0xFF and buffer[0x48] == 0xFF:
			print("FAIL: No information about the voltage range found in CFI data.")
			try:
				with open("./cfi_debug.bin", "wb") as f: f.write(buffer)
			except:
				pass
			return False
		
		pri_address = (buffer[0x2A] | (buffer[0x2C] << 8)) * 2
		if (pri_address + 0x3C) >= 0x400: pri_address = 0x80
		
		info["vdd_min"] = (buffer[0x36] >> 4) + ((buffer[0x36] & 0x0F) / 10)
		info["vdd_max"] = (buffer[0x38] >> 4) + ((buffer[0x38] & 0x0F) / 10)
		
		if buffer[0x3E] > 0 and buffer[0x3E] < 0xFF:
			info["single_write"] = True
			info["single_write_time_avg"] = int(math.pow(2, buffer[0x3E]))
			info["single_write_time_max"] = int(math.pow(2, buffer[0x46]) * info["single_write_time_avg"])
		else:
			info["single_write"] = False

		if buffer[0x40] > 0 and buffer[0x40] < 0xFF:
			info["buffer_write"] = True
			info["buffer_write_time_avg"] = int(math.pow(2, buffer[0x40]))
			info["buffer_write_time_max"] = int(math.pow(2, buffer[0x48]) * info["buffer_write_time_avg"])
		else:
			info["buffer_write"] = False

		if buffer[0x42] > 0 and buffer[0x42] < 0xFF:
			info["sector_erase"] = True
			info["sector_erase_time_avg"] = int(math.pow(2, buffer[0x42]))
			info["sector_erase_time_max"] = int(math.pow(2, buffer[0x4A]) * info["sector_erase_time_avg"])
		else:
			info["sector_erase"] = False

		if buffer[0x44] > 0 and buffer[0x44] < 0xFF:
			info["chip_erase"] = True
			info["chip_erase_time_avg"] = int(math.pow(2, buffer[0x44]))
			info["chip_erase_time_max"] = int(math.pow(2, buffer[0x4C]) * info["chip_erase_time_avg"])
		else:
			info["chip_erase"] = False

		info["tb_boot_sector"] = False
		info["tb_boot_sector_raw"] = 0
		if "{:s}{:s}{:s}".format(chr(buffer[pri_address]), chr(buffer[pri_address+2]), chr(buffer[pri_address+4])) == "PRI":
			if buffer[pri_address + 0x1E] not in (0, 0xFF):
				temp = { 0x02: 'As shown', 0x03: 'Reversed' }
				info["tb_boot_sector_raw"] = buffer[pri_address + 0x1E]
				try:
					info["tb_boot_sector"] = "{:s} (0x{:02X})".format(temp[buffer[pri_address + 0x1E]], buffer[pri_address + 0x1E])
				except:
					info["tb_boot_sector"] = "0x{:02X}".format(buffer[pri_address + 0x1E])
		#elif "{:s}{:s}{:s}".format(chr(buffer[0x214]), chr(buffer[0x216]), chr(buffer[0x218])) == "PRI":
		#	pass
		
		info["device_size"] = int(math.pow(2, buffer[0x4E]))
		info["buffer_size"] = buffer[0x56] << 8 | buffer[0x54]
		if info["buffer_size"] > 1:
			info["buffer_write"] = True
			info["buffer_size"] = int(math.pow(2, info["buffer_size"]))
		else:
			del(info["buffer_size"])
			info["buffer_write"] = False
		info["erase_sector_regions"] = buffer[0x58]
		info["erase_sector_blocks"] = []
		total_blocks = 0
		pos = 0
		for i in range(0, min(4, info["erase_sector_regions"])):
			b = (buffer[0x5C+(i*8)] << 8 | buffer[0x5A+(i*8)]) + 1
			t = (buffer[0x60+(i*8)] << 8 | buffer[0x5E+(i*8)]) * 256
			total_blocks += b
			size = b * t
			pos += size
			info["erase_sector_blocks"].append([ t, b, size ])
	
	except:
		print("ERROR: Trying to parse CFI data resulted in an error.")
		try:
			with open("./cfi_debug.bin", "wb") as f: f.write(buffer)
		except:
			pass
		return False
	
	return info

def GetDumpReport(di, device):
	if di["system"] == "DMG":
		mode = "DMG"
		di["system"] = "Game Boy"
		if di["rom_size"] in DMG_Header_ROM_Sizes_Flasher_Map:
			di["rom_size"] = "{:s}".format(DMG_Header_ROM_Sizes[DMG_Header_ROM_Sizes_Flasher_Map.index(di["rom_size"])])
		else:
			di["rom_size"] = "{:,} bytes".format(di["rom_size"])
		
		if di["mapper_type"] in DMG_Header_Mapper:
			di["mapper_type"] = "{:s}".format(DMG_Header_Mapper[di["mapper_type"]])
		else:
			di["mapper_type"] = "0x{:02X}".format(di["mapper_type"])
	
	elif di["system"] == "AGB":
		mode = "AGB"
		di["system"] = "Game Boy Advance"
		if di["rom_size"] in AGB_Header_ROM_Sizes_Map:
			di["rom_size"] = "{:s}".format(AGB_Header_ROM_Sizes[AGB_Header_ROM_Sizes_Map.index(di["rom_size"])])
		else:
			di["rom_size"] = "{:,} bytes".format(di["rom_size"])
	
	di["cart_type"] = list(device.SUPPORTED_CARTS[mode].keys())[di["cart_type"]]
	if di["file_name"] is None:
		di["file_name"] = ""
	else:
		di["file_name"] = os.path.split(di["file_name"])[1]
	di["file_size"] = "{:s} ({:d} bytes)".format(formatFileSize(di["file_size"]), di["file_size"])
	
	s = "" \
		"= FlashGBX Dump Report =\n" \
	
	s += "" \
		"\n== File Information ==\n" \
		"* File Name:       {file_name:s}\n" \
		"* File Size:       {file_size:s}\n" \
		"* CRC32:           {hash_crc32:08x}\n" \
		"* MD5:             {hash_md5:s}\n" \
		"* SHA-1:           {hash_sha1:s}\n" \
		"* SHA-256:         {hash_sha256:s}\n" \
	.format(file_name=di["file_name"], file_size=di["file_size"], hash_crc32=di["hash_crc32"], hash_md5=di["hash_md5"], hash_sha1=di["hash_sha1"], hash_sha256=di["hash_sha256"])

	s += "" \
		"\n== General Information ==\n" \
		"* Hardware:        {hardware:s} – Firmware {firmware:s}\n" \
		"* Software:        {software:s}\n" \
		"* OS Platform:     {platform:s}\n" \
		"* Dump Time:       {timestamp:s}\n" \
		"* Time Elapsed:    %TIME_ELAPSED% (%TRANSFER_RATE%)\n" \
		"* Transfer Buffer: {buffer_size:d} bytes\n" \
	.format(hardware=device.GetFullName(), firmware=device.GetFirmwareVersion(), software="{:s} {:s}".format(APPNAME, VERSION), platform=platform.platform(), buffer_size=di["transfer_size"], timestamp=di["timestamp"])
	
	if mode == "DMG":
		s += "" \
			"\n== Dumping Settings ==\n" \
			"* Mode:            {system:s}\n" \
			"* ROM Size:        {rom_size:s}\n" \
			"* Mapper Type:     {mapper_type:s}\n" \
			"* Cartridge Type:  {cart_type:s}\n" \
		.format(system=di["system"], rom_size=di["rom_size"], mapper_type=di["mapper_type"], cart_type=di["cart_type"])
	elif mode == "AGB":
		s += "" \
			"\n== Dumping Settings ==\n" \
			"* Mode:            {system:s}\n" \
			"* ROM Size:        {rom_size:s}\n" \
			"* Cartridge Type:  {cart_type:s}\n" \
		.format(system=di["system"], rom_size=di["rom_size"], cart_type=di["cart_type"])

	di["hdr_logo"] = "OK" if di["header"]["logo_correct"] else "Invalid"
	di["header"]["game_title_raw"] = di["header"]["game_title_raw"].replace("\0", "␀")
	if mode == "DMG":
		if di["header"]["cgb"] == 0xC0 or di["header"]["cgb"] == 0x80:
			di["hdr_target_platform"] = "Game Boy Color"
		elif di["header"]["old_lic"] == 0x33 and di["header"]["sgb"] == 0x03:
			di["hdr_target_platform"] = "Super Game Boy"
		else:
			di["hdr_target_platform"] = "Game Boy"

		if di["header"]["old_lic"] == 0x33 and di["header"]["sgb"] == 0x03:
			di["hdr_sgb"] = "Supported"
		else:
			di["hdr_sgb"] = "No support" # (146h=0x{:02X}, 14Bh=0x{:02X})".format(di["header"]["sgb"], di["header"]["old_lic"])
		if di["header"]["cgb"] in DMG_Header_CGB:
			di["hdr_cgb"] = "{:s}".format(DMG_Header_CGB[di["header"]["cgb"]])
		else:
			di["hdr_cgb"] = "Unknown (0x{:02X})".format(di["header"]["cgb"])
		
		di["hdr_header_checksum"] = "OK (0x{:02X})".format(di["header"]["header_checksum"]) if di["header"]["header_checksum_correct"] else "Invalid (0x{:02X}≠0x{:02X})".format(di["header"]["header_checksum_calc"], di["header"]["header_checksum"])
		di["header"]["rom_checksum_calc"] = device.INFO["rom_checksum_calc"]
		di["header"]["rom_checksum_correct"] = di["header"]["rom_checksum_calc"] == di["header"]["rom_checksum"]
		di["hdr_rom_checksum"] = "OK (0x{:04X})".format(di["header"]["rom_checksum"]) if di["header"]["rom_checksum_correct"] else "Invalid (0x{:04X}≠0x{:04X})".format(di["header"]["rom_checksum_calc"], di["header"]["rom_checksum"])
		
		di["hdr_rom_size"] = di["header"]["rom_size_raw"]
		if di["hdr_rom_size"] in DMG_Header_ROM_Sizes_Map:
			di["hdr_rom_size"] = "{:s} (0x{:02X})".format(DMG_Header_ROM_Sizes[DMG_Header_ROM_Sizes_Map.index(di["hdr_rom_size"])], di["hdr_rom_size"])
		else:
			di["hdr_rom_size"] = "Unknown (0x{:02X})".format(di["hdr_rom_size"])
		
		di["hdr_save_type"] = di["header"]["ram_size_raw"]
		if di["hdr_save_type"] in DMG_Header_RAM_Sizes_Map:
			di["hdr_save_type"] = "{:s} (0x{:02X})".format(DMG_Header_RAM_Sizes[DMG_Header_RAM_Sizes_Map.index(di["hdr_save_type"])], di["hdr_save_type"])
		else:
			di["hdr_save_type"] = "Unknown (0x{:02X})".format(di["hdr_save_type"])
		
		di["hdr_mapper_type"] = di["header"]["mapper_raw"]
		if di["hdr_mapper_type"] in DMG_Header_Mapper:
			di["hdr_mapper_type"] = "{:s} (0x{:02X})".format(DMG_Header_Mapper[di["hdr_mapper_type"]], di["hdr_mapper_type"])
		else:
			di["hdr_mapper_type"] = "Unknown (0x{:02X})".format(di["hdr_mapper_type"])
		
		s += "" \
			"\n== Parsed Data ==\n" \
			"* Game Title/Code: {hdr_game_title:s}\n" \
			"* Revision:        {hdr_revision:s}\n" \
			"* Super Game Boy:  {hdr_sgb:s}\n" \
			"* Game Boy Color:  {hdr_cgb:s}\n" \
			"* Nintendo Logo:   {hdr_logo:s}\n" \
			"* Header Checksum: {hdr_header_checksum:s}\n" \
			"* ROM Checksum:    {hdr_rom_checksum:s}\n" \
			"* ROM Size:        {hdr_rom_size:s}\n" \
			"* Save Type:       {hdr_save_type:s}\n" \
			"* Mapper Type:     {hdr_mapper_type:s}\n" \
			"* Target Platform: {hdr_target_platform:s}\n" \
		.format(hdr_game_title=di["header"]["game_title_raw"], hdr_revision=str(di["header"]["version"]), hdr_sgb=di["hdr_sgb"], hdr_cgb=di["hdr_cgb"], hdr_logo=di["hdr_logo"], hdr_header_checksum=di["hdr_header_checksum"], hdr_rom_checksum=di["hdr_rom_checksum"], hdr_rom_size=di["hdr_rom_size"], hdr_save_type=di["hdr_save_type"], hdr_mapper_type=di["hdr_mapper_type"], hdr_target_platform=di["hdr_target_platform"])
		if "gbmem" in di and di["gbmem"] is not None:
			s += "" \
				"* Map Parameters:  {gbmem:s}\n" \
			.format(gbmem=''.join(format(x, '02X') for x in di["gbmem"][:0x18]))
	
	if mode == "AGB":
		di["header"]["game_code_raw"] = di["header"]["game_code_raw"].replace("\0", "␀")
		di["hdr_header_checksum"] = "OK (0x{:02X})".format(di["header"]["header_checksum"]) if di["header"]["header_checksum_correct"] else "Invalid (0x{:02X}≠0x{:02X})".format(di["header"]["header_checksum_calc"], di["header"]["header_checksum"])
		if "agb_savelib" not in di:
			di["agb_savelib"] = "None"
		elif "SRAM_F_" in di["agb_savelib"]:
			di["agb_savelib"] = "256K SRAM/FRAM ({:s})".format(di["agb_savelib"])
		elif "SRAM_" in di["agb_savelib"]:
			di["agb_savelib"] = "256K SRAM ({:s})".format(di["agb_savelib"])
		elif "EEPROM_V" in di["agb_savelib"]:
			di["agb_savelib"] = "4K or 64K EEPROM ({:s})".format(di["agb_savelib"])
		elif "FLASH_V" in di["agb_savelib"] or "FLASH512_V" in di["agb_savelib"]:
			di["agb_savelib"] = "512K FLASH ({:s})".format(di["agb_savelib"])
		elif "FLASH1M_V" in di["agb_savelib"] or "FLASH512_V" in di["agb_savelib"]:
			di["agb_savelib"] = "1M FLASH ({:s})".format(di["agb_savelib"])
		elif "AGB_8MDACS_DL_V" in di["agb_savelib"]:
			di["agb_savelib"] = "8M DACS ({:s})".format(di["agb_savelib"])
		elif di["agb_savelib"] == "N/A":
			di["agb_savelib"] = "None"
		else:
			di["agb_savelib"] = "Unknown ({:s})".format(di["agb_savelib"])
		s += "" \
			"\n== Parsed Data ==\n" \
			"* Game Title:      {hdr_game_title:s}\n" \
			"* Game Code:       {hdr_game_code:s}\n" \
			"* Revision:        {hdr_revision:s}\n" \
			"* Nintendo Logo:   {hdr_logo:s}\n" \
			"* Header Checksum: {hdr_header_checksum:s}\n" \
			"* Save Type:       {agb_savetype}\n" \
		.format(hdr_game_title=di["header"]["game_title_raw"], hdr_game_code=di["header"]["game_code_raw"], hdr_revision=str(di["header"]["version"]), hdr_logo=di["hdr_logo"], hdr_header_checksum=di["hdr_header_checksum"], agb_savetype=di["agb_savelib"])
		if "agb_save_flash_id" in di and di["agb_save_flash_id"] is not None:
			s += "" \
				"* Save Flash Chip: {agb_save_flash_chip_name:s} (0x{agb_save_flash_chip_id:04X})\n" \
			.format(agb_save_flash_chip_name=di["agb_save_flash_id"][2], agb_save_flash_chip_id=di["agb_save_flash_id"][1])
	
	return s

def validate_datetime_format(string, format):
	try:
		if string != datetime.datetime.strptime(string, format).strftime(format):
			raise ValueError
		return True
	except ValueError:
		return False

def find_size(data, max_size, min_size=0x20):
	offset = max_size
	while offset >= min_size:
		offset = int(offset / 2)
		if data[0:offset] != data[offset:offset*2]:
			offset = offset * 2
			break
	return offset

def dprint(*args, **kwargs):
	if DEBUG:
		stack = traceback.extract_stack()
		stack = stack[len(stack)-2]
		print("{:s}[{:s}] [{:s}:{:d}] {:s}(): {:s}".format(ANSI.CLEAR_LINE, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), stack.filename[stack.filename.replace("\\", "/").rindex("/")+1:], stack.lineno, stack.name, " ".join(map(str, args)), **kwargs))
