# -*- coding: utf-8 -*-
# ＵＴＦ－８
import math, time, datetime, copy, configparser, threading, statistics, os, platform
from enum import Enum

# Common constants
APPNAME = "FlashGBX"
VERSION_PEP440 = "1.4"
VERSION = "v{:s}".format(VERSION_PEP440)
DEBUG = False

AGB_Header_ROM_Sizes = [ "4 MB", "8 MB", "16 MB", "32 MB", "64 MB (GBA Video)" ]
AGB_Header_ROM_Sizes_Map = [ 0x400000, 0x800000, 0x1000000, 0x2000000, 0x4000000 ]
AGB_Header_Save_Types = [ "None", "4K EEPROM (512 Bytes)", "64K EEPROM (8 KB)", "256K SRAM (32 KB)", "512K SRAM (64 KB)", "1M SRAM (128 KB)", "512K FLASH (64 KB)", "1M FLASH (128 KB)" ]
AGB_Global_CRC32 = 0

DMG_Header_Features = { 0x00:'None', 0x01:'MBC1', 0x02:'MBC1+SRAM', 0x03:'MBC1+SRAM+BATTERY', 0x06:'MBC2+BATTERY', 0x10:'MBC3+RTC+SRAM+BATTERY', 0x13:'MBC3+SRAM+BATTERY', 0x19:'MBC5', 0x1B:'MBC5+SRAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1E:'MBC5+RUMBLE+SRAM+BATTERY', 0x20:'MBC6+FLASH+SRAM+BATTERY', 0x22:'MBC7+ACCELEROMETER+EEPROM', 0x101:'MBC1M', 0x103:'MBC1M+SRAM+BATTERY', 0x0B:'MMM01',  0x0D:'MMM01+SRAM+BATTERY', 0xFC:'CAMERA+SRAM+BATTERY', 0x105:'G-MMC1', 0x104:'M161', 0xFF:'HuC-1+IR+SRAM+BATTERY', 0xFE:'HuC-3+RTC+SRAM+BATTERY', 0xFD:'TAMA5+RTC+EEPROM' }
DMG_Header_ROM_Sizes = [ "32 KB", "64 KB", "128 KB", "256 KB", "512 KB", "1 MB", "2 MB", "4 MB", "8 MB" ]
DMG_Header_ROM_Sizes_Map = [ 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08 ]
DMG_Header_ROM_Sizes_Flasher_Map = [ 2, 4, 8, 16, 32, 64, 128, 256, 512 ] # Number of ROM banks
DMG_Header_RAM_Sizes = [ "None", "4K SRAM (512 Bytes)", "16K SRAM (2 KB)", "64K SRAM (8 KB)", "256K SRAM (32 KB)", "512K SRAM (64 KB)", "1M SRAM (128 KB)", "2K MBC7 EEPROM (256 Bytes)", "4K MBC7 EEPROM (512 Bytes)", "TAMA5 EEPROM (32 Bytes)" ]
DMG_Header_RAM_Sizes_Map = [ 0x00, 0x01, 0x01, 0x02, 0x03, 0x05, 0x04, 0x101, 0x102, 0x103 ]
DMG_Header_RAM_Sizes_Flasher_Map = [ 0, 0x200, 0x800, 0x2000, 0x8000, 0x10000, 0x20000, 0x100, 0x200, 0x20 ] # RAM size in bytes
DMG_Header_SGB = { 0x00:'No support', 0x03:'Supported' }
DMG_Header_CGB = { 0x00:'No support', 0x80:'Supported', 0xC0:'Required' }

class ANSI:
	BOLD = '\033[1m'
	RED = '\033[91m'
	GREEN = '\033[92m'
	YELLOW = '\033[33m'
	RESET = '\033[0m'
	CLEAR_LINE = '\033[2K'

class IniSettings():
	FILENAME = ""
	SETTINGS = None
	def __init__(self, ini_file):
		try:
			if not os.path.isdir(os.path.dirname(ini_file)):
				os.makedirs(os.path.dirname(ini_file))
			if os.path.exists(ini_file):
				with open(ini_file, "a+") as f: f.close()
			else:
				with open(ini_file, "w+") as f: f.close()
		except:
			print("Error accessing the configuration directory or settings file.")
			return
		
		self.FILENAME = ini_file
		self.SETTINGS = configparser.ConfigParser()
		self.SETTINGS.optionxform = str
		self.Reload()
		
	def Reload(self):
		if self.SETTINGS is None: return
		with open(self.FILENAME, "r", encoding="utf-8") as f:
			self.SETTINGS.read_file(f)
		if len(self.SETTINGS.sections()) == 0:
			self.SETTINGS.add_section("General")
	
	def value(self, key, default=None): return self.GetValue(key, default)
	def GetValue(self, key, default=None):
		if self.SETTINGS is None: return None
		self.Reload()
		if key not in self.SETTINGS["General"]:
			if default is not None: self.SetValue(key, default)
			return default
		return (self.SETTINGS["General"][key])
	
	def setValue(self, key, value): self.SetValue(key, value)
	def SetValue(self, key, value):
		if self.SETTINGS is None: return None
		self.Reload()
		self.SETTINGS["General"][key] = value
		dprint("Updating settings:", key, "=", value)
		with open(self.FILENAME, "w", encoding="utf-8") as f:
			self.SETTINGS.write(f)
	
	def clear(self): self.Clear()
	def Clear(self):
		if self.SETTINGS is None: return None
		self.SETTINGS.clear()
		with open(self.FILENAME, "w", encoding="utf-8") as f:
			self.SETTINGS.write(f)

class Progress():
	MUTEX = threading.Lock()
	PROGRESS = {}
	UPDATER = None
	
	def __init__(self, updater):
		self.UPDATER = updater
		pass
	
	def SetProgress(self, args):
		self.MUTEX.acquire(1)
		try:
			if not "method" in self.PROGRESS: self.PROGRESS = {}
			now = time.time()
			if args["action"] == "INITIALIZE":
				self.PROGRESS["action"] = args["action"]
				self.PROGRESS["method"] = args["method"]
				self.PROGRESS["size"] = args["size"]
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
			
			elif args["action"] in ("ERASE", "SECTOR_ERASE"):
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
				self.PROGRESS["speed"] = (self.PROGRESS["size"] / self.PROGRESS["time_elapsed"]) / 1024
				self.PROGRESS["bytes_last_emit"] = self.PROGRESS["size"]
				if "verified" in args: self.PROGRESS["verified"] = (args["verified"] == True)
				
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

def formatFileSize(size, asInt=False):
	#size = size / 1024
	if size == 1:
		return "{:d} Byte".format(size)
	elif size < 1024:
		return "{:d} Bytes".format(size)
	elif size < 1024 * 1024:
		if asInt:
			return "{:d} KB".format(int(size/1024))
		else:
			return "{:.1f} KB".format(size/1024)
	else:
		if asInt:
			return "{:d} MB".format(int(size/1024/1024))
		else:
			return "{:.2f} MB".format(size/1024/1024)

def formatProgressTimeShort(sec):
	sec = sec % (24 * 3600)
	hr = sec // 3600
	sec %= 3600
	min = sec // 60
	sec %= 60
	return "{:02d}:{:02d}:{:02d}".format(int(hr), int(min), int(sec))

def formatProgressTime(sec):
	if int(sec) == 1:
		return "{:d} second".format(int(sec))
	elif sec < 60:
		return "{:d} seconds".format(int(sec))
	elif int(sec) == 60:
		return "1 minute"
	else:
		min = int(sec / 60)
		sec = int(sec % 60)
		s = str(min) + " "
		if min == 1:
			s = s + "minute"
		else:
			s = s + "minutes"
		s = s + ", " + str(sec) + " "
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
				info["tb_boot_sector_raw"] = buffer[0x9E]
				try:
					info["tb_boot_sector"] = "{:s} (0x{:02X})".format(temp[buffer[0x9E]], buffer[0x9E])
				except:
					info["tb_boot_sector"] = "0x{:02X}".format(buffer[0x9E])
		elif "{:s}{:s}{:s}".format(chr(buffer[0x214]), chr(buffer[0x216]), chr(buffer[0x218])) == "PRI":
			pass # todo
		
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

def dprint(*args, **kwargs):
	if DEBUG:
		print("{:s}{:s} {:s}".format(ANSI.CLEAR_LINE, datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), " ".join(map(str, args)), **kwargs))
