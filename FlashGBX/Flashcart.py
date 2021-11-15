# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import time, copy, math, struct
from .Util import dprint, bitswap

class Flashcart:
	CONFIG = {}
	COMMAND_SET = None
	CART_WRITE_FNCPTR = None
	CART_READ_FNCPTR = None
	PROGRESS_FNCPTR = None
	SECTOR_COUNT = 0
	SECTOR_POS = 0
	SECTOR_MAP = None
	CFI = None

	def __init__(self, config=None, cart_write_fncptr=None, cart_read_fncptr=None, progress_fncptr=None):
		if config is None: config = {}
		self.CART_WRITE_FNCPTR = cart_write_fncptr
		self.CART_READ_FNCPTR = cart_read_fncptr
		self.PROGRESS_FNCPTR = progress_fncptr
		self.CONFIG = config
		if "command_set" in config:
			self.CONFIG["_command_set"] = config["command_set"]
		elif "read_identifier" in config and config["read_identifier"][0][1] == 0x90:
			self.CONFIG["_command_set"] = "INTEL"
		else:
			self.CONFIG["_command_set"] = ""
	
	def CartRead(self, address, length=0):
		if length == 0:
			if self.CONFIG["type"].upper() == "AGB":
				length = 2
			else:
				length = 1
		return self.CART_READ_FNCPTR(address, length)
	
	def CartWrite(self, commands, sram=False):
		for command in commands:
			address = command[0]
			value = command[1]
			self.CART_WRITE_FNCPTR(address, value, flashcart=True, sram=sram)

	def GetCommandSetType(self):
		return self.CONFIG["_command_set"].upper()

	def GetName(self, index=0):
		return self.CONFIG["names"][index]

	def GetFlashID(self, index=0):
		return self.CONFIG["flash_ids"][index]

	def GetVoltage(self):
		return self.CONFIG["voltage"]

	def GetMBC(self):
		if (self.CONFIG["type"].upper() == "AGB") or ("mbc" not in self.CONFIG): return False
		mbc = self.CONFIG["mbc"]
		if mbc == 1: mbc = 0x03
		elif mbc == 2: mbc = 0x06
		elif mbc == 3: mbc = 0x13
		elif mbc == 5: mbc = 0x1B
		elif mbc == 6: mbc = 0x20
		elif mbc == 7: mbc = 0x22
		return mbc

	def FlashCommandsOnBank1(self):
		return ("flash_commands_on_bank_1" in self.CONFIG and self.CONFIG["flash_commands_on_bank_1"] is True)

	def PulseResetAfterWrite(self):
		return ("pulse_reset_after_write" in self.CONFIG and self.CONFIG["pulse_reset_after_write"] is True)

	def HasRTC(self):
		return ("rtc" in self.CONFIG and self.CONFIG["rtc"] is True)

	def SupportsBufferWrite(self):
		buffer_size = self.GetBufferSize()
		if buffer_size is False:
			return False
		else:
			return True
		#return ("buffer_write" in self.CONFIG["commands"])

	def SupportsSingleWrite(self):
		return ("single_write" in self.CONFIG["commands"])
	
	def SupportsChipErase(self):
		return ("chip_erase" in self.CONFIG["commands"])

	def SupportsSectorErase(self):
		return ("sector_erase" in self.CONFIG["commands"])

	def IsF2A(self):
		if "buffer_write" not in self.CONFIG["commands"]: return False
		for cmd in self.CONFIG["commands"]["buffer_write"]:
			if cmd[0] == "SA+2": return True
		return False

	def WEisWR(self):
		if "write_pin" not in self.CONFIG: return False
		return (self.CONFIG["write_pin"] == "WR")

	def WEisAUDIO(self):
		if "write_pin" not in self.CONFIG: return False
		return (self.CONFIG["write_pin"] in ("AUDIO", "VIN"))

	def WEisWR_RESET(self):
		if "write_pin" not in self.CONFIG: return False
		return (self.CONFIG["write_pin"] == "WR+RESET")

	def GetBufferSize(self):
		if "buffer_size" in self.CONFIG:
			return self.CONFIG["buffer_size"]
		elif "buffer_write" in self.CONFIG["commands"]:
			if "cfi" in self.CONFIG:
				cfi = self.CONFIG["cfi"]
			else:
				cfi = self.ReadCFI()
				if cfi is False:
					print("CFI ERROR: Couldn’t retrieve buffer size from the cartridge.")
					return False
			if not "buffer_size" in cfi: return False
			buffer_size = cfi["buffer_size"]
			dprint("Buffer size was read from CFI data:", cfi["buffer_size"])
			self.CONFIG["buffer_size"] = buffer_size
			return buffer_size
		else:
			return False

	def GetCommands(self, key):
		if key not in self.CONFIG["commands"]: return []
		return self.CONFIG["commands"][key]

	def Unlock(self):
		self.CartRead(0) # dummy read
		if "unlock" in self.CONFIG["commands"]:
			self.CartWrite(self.CONFIG["commands"]["unlock"])
			time.sleep(0.001)

	def Reset(self, full_reset=False, max_address=0x2000000):
		#dprint(full_reset, "reset_every" in self.CONFIG)
		if full_reset and "reset_every" in self.CONFIG:
			for j in range(0, self.CONFIG["flash_size"], self.CONFIG["reset_every"]):
				if j >= max_address: break
				dprint("reset_every @ 0x{:X}".format(j))
				for command in self.CONFIG["commands"]["reset"]:
					self.CartWrite([[j, command[1]]])
					time.sleep(0.01)
		elif "reset" in self.CONFIG["commands"]:
			self.CartWrite(self.CONFIG["commands"]["reset"])
			time.sleep(0.001)
	
	def VerifyFlashID(self):
		if "read_identifier" not in self.CONFIG["commands"]: return False
		if len(self.CONFIG["flash_ids"]) == 0: return False
		self.Reset()
		self.Unlock()
		self.CartWrite(self.CONFIG["commands"]["read_identifier"])
		time.sleep(0.001)
		cart_flash_id = list(self.CartRead(0, len(self.CONFIG["flash_ids"][0])))
		self.Reset()
		dprint("Flash ID: {:s}".format(' '.join(format(x, '02X') for x in cart_flash_id)))
		verified = True
		if cart_flash_id not in self.CONFIG["flash_ids"]:
			dprint("This Flash ID does not exist in flashcart handler file.")
			verified = False
		return (verified, cart_flash_id)
	
	def ReadCFI(self):
		if self.CFI is not None: return self.CFI
		if "read_cfi" not in self.CONFIG["commands"]:
			if self.CONFIG["_command_set"] == "INTEL":
				self.CONFIG["commands"]["read_cfi"] = self.CONFIG["commands"]["read_identifier"]
			elif self.CONFIG["_command_set"] == "AMD":
				self.CONFIG["commands"]["read_cfi"] = [ [ 0xAA, 0x98 ] ]
		
		if "read_cfi" in self.CONFIG["commands"]:
			#print(self.CONFIG["commands"]["read_cfi"])
			self.CartWrite(self.CONFIG["commands"]["read_cfi"])
			time.sleep(0.1)
			buffer = self.CartRead(0, 0x400)
			#print(buffer)
			self.Reset()
			cfi = CFI().Parse(buffer)
			if cfi is not False:
				cfi["raw"] = buffer
			dprint(cfi)
			if cfi is not False:
				self.CONFIG["cfi"] = cfi
			return cfi
		return False
	
	def GetSmallestSectorSize(self):
		sector_map = self.GetSectorMap()
		if isinstance(sector_map, int): return sector_map
		smallest_sector_size = sector_map[0][0]
		for sector in sector_map:
			smallest_sector_size = min(smallest_sector_size, sector[0])
		return smallest_sector_size
	
	def GetSectorMap(self):
		if self.SECTOR_MAP is not None:
			return self.SECTOR_MAP
		elif "sector_size" in self.CONFIG:
			return self.CONFIG["sector_size"]
		elif "sector_erase" in self.CONFIG["commands"]:
			if "cfi" in self.CONFIG:
				cfi = self.CONFIG["cfi"]
			else:
				cfi = self.ReadCFI()
				if cfi is False:
					print("CFI ERROR: Couldn’t retrieve sector size map from the cartridge.")
					return False
			sector_size = cfi["erase_sector_blocks"]
			if cfi["tb_boot_sector_raw"] == 0x03: sector_size.reverse()
			dprint("Sector size map was read from CFI data:", cfi["erase_sector_blocks"])
			self.CONFIG["sector_size"] = sector_size
			return sector_size
		else:
			return False

	def ChipErase(self):
		self.Reset(full_reset=True)
		time_start = time.time()
		if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"ERASE", "time_start":time_start, "abortable":False})
		for i in range(0, len(self.CONFIG["commands"]["chip_erase"])):
			addr = self.CONFIG["commands"]["chip_erase"][i][0]
			data = self.CONFIG["commands"]["chip_erase"][i][1]
			if not addr == None:
				self.CartWrite([[addr, data]])
			if self.CONFIG["commands"]["chip_erase_wait_for"][i][0] != None:
				addr = self.CONFIG["commands"]["chip_erase_wait_for"][i][0]
				data = self.CONFIG["commands"]["chip_erase_wait_for"][i][1]
				timeout = self.CONFIG["chip_erase_timeout"]
				while True:
					if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"ERASE", "time_start":time_start, "abortable":False})
					if "wait_read_status_register" in self.CONFIG and self.CONFIG["wait_read_status_register"]:
						for j in range(0, len(self.CONFIG["commands"]["read_status_register"])):
							#sr_addr = self.CONFIG["commands"]["read_status_register"][j][0]
							sr_data = self.CONFIG["commands"]["read_status_register"][j][1]
							self.CartWrite([[addr, sr_data]])
					self.CartRead(addr, 2) # dummy read (fixes some bootlegs)
					wait_for = struct.unpack("<H", self.CartRead(addr, 2))[0]
					dprint("Status Register Check: 0x{:X} & 0x{:X} == 0x{:X}? {:s}".format(wait_for, self.CONFIG["commands"]["chip_erase_wait_for"][i][2], data, str((wait_for & self.CONFIG["commands"]["chip_erase_wait_for"][i][2]) == data)))
					wait_for = wait_for & self.CONFIG["commands"]["chip_erase_wait_for"][i][2]
					if wait_for == data: break
					time.sleep(0.5)
					timeout -= 0.5
					if timeout <= 0:
						self.PROGRESS_FNCPTR({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing the flash chip timed out. Please make sure that the cartridge contacts are clean, and that the selected cartridge type and settings are correct.", "abortable":False})
						return False
		self.Reset(full_reset=True)
		return True

	def SectorErase(self, pos=0, buffer_pos=0):
		self.Reset(full_reset=False)
		#time_start = time.time()
		#if progress_fnc is not None: progress_fnc({"action":"ERASE", "time_start":time_start, "abortable":False})
		if "sector_erase" not in self.CONFIG["commands"]: return False
		for i in range(0, len(self.CONFIG["commands"]["sector_erase"])):
			addr = self.CONFIG["commands"]["sector_erase"][i][0]
			data = self.CONFIG["commands"]["sector_erase"][i][1]
			if addr == "SA": addr = pos
			if addr == "SA+1": addr = pos + 1
			if addr == "SA+2": addr = pos + 2
			if addr == "SA+0x4000": addr = pos + 0x4000
			if addr == "SA+0x7000": addr = pos + 0x7000
			if not addr == None:
				self.CartWrite([[addr, data]])
			if self.CONFIG["commands"]["sector_erase_wait_for"][i][0] != None:
				addr = self.CONFIG["commands"]["sector_erase_wait_for"][i][0]
				data = self.CONFIG["commands"]["sector_erase_wait_for"][i][1]
				if addr == "SA": addr = pos
				if addr == "SA+1": addr = pos + 1
				if addr == "SA+2": addr = pos + 2
				if addr == "SA+0x4000": addr = pos + 0x4000
				if addr == "SA+0x7000": addr = pos + 0x7000
				time.sleep(0.1)
				timeout = 100
				while True:
					if "wait_read_status_register" in self.CONFIG and self.CONFIG["wait_read_status_register"] == True:
						for j in range(0, len(self.CONFIG["commands"]["read_status_register"])):
							sr_addr = self.CONFIG["commands"]["read_status_register"][j][0]
							sr_data = self.CONFIG["commands"]["read_status_register"][j][1]
							self.CartWrite([[sr_addr, sr_data]])
					self.CartRead(addr, 2) # dummy read (fixes some bootlegs)
					wait_for = struct.unpack("<H", self.CartRead(addr, 2))[0]
					dprint("Status Register Check: 0x{:X} & 0x{:X} == 0x{:X}? {:s}".format(wait_for, self.CONFIG["commands"]["sector_erase_wait_for"][i][2], data, str(wait_for & self.CONFIG["commands"]["sector_erase_wait_for"][i][2] == data)))
					wait_for = wait_for & self.CONFIG["commands"]["sector_erase_wait_for"][i][2]
					time.sleep(0.1)
					timeout -= 1
					if timeout < 1:
						dprint("Timeout error!")
						self.PROGRESS_FNCPTR({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing a flash chip sector timed out. Please make sure that the cartridge contacts are clean, and that the selected cartridge type and settings are correct.", "abortable":False})
						return False
					if wait_for == data: break
					self.PROGRESS_FNCPTR({"action":"SECTOR_ERASE", "sector_pos":buffer_pos, "time_start":time.time(), "abortable":True})
				dprint("Done waiting!")

		self.Reset(full_reset=False)
		if isinstance(self.CONFIG["sector_size"], list):
			self.CONFIG["sector_size"][self.SECTOR_POS][1] -= 1
			if (self.CONFIG["sector_size"][self.SECTOR_POS][1] == 0) and (len(self.CONFIG["sector_size"]) > self.SECTOR_POS + 1):
				self.SECTOR_POS += 1
			try:
				sector_size = self.CONFIG["sector_size"][self.SECTOR_POS][0]
			except:
				dprint("Warning: Sector map is smaller than expected.")
				self.SECTOR_POS -= 1
				#self.CONFIG["sector_size"][self.SECTOR_POS][0]
			return sector_size
		else:
			return self.CONFIG["sector_size"]
	
	def SelectBankROM(self, index):
		if "flash_bank_select_type" not in self.CONFIG: return False
		if self.CONFIG["flash_bank_select_type"] == 1:
			dprint(self.GetName(), "|", index)
			self.CartWrite([[2, index << 4]], sram=True)
			return True
		
		return False

class CFI:
	def Parse(self, buffer):
		if buffer is False or buffer == b'': return False
		buffer = copy.copy(buffer)
		info = {}
		magic = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
		info["d_swap"] = None
		if magic == "QRY": # nothing swapped
			info["d_swap"] = ( 0, 0 )
		elif magic == "RQZ": # D0D1 swapped
			info["d_swap"] = ( 0, 1 )
		else:
			return False
		
		if info["d_swap"] is not None:
			for i in range(0, len(buffer)):
				buffer[i] = bitswap(buffer[i], info["d_swap"])
		
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
			dprint("ERROR: Trying to parse CFI data resulted in an error.")
			try:
				with open("./cfi_debug.bin", "wb") as f: f.write(buffer)
			except:
				pass
			return False
		
		s = ""
		if info["d_swap"] is not None and info["d_swap"] != ( 0, 0 ): s += "Swapped pins: {:s}\n".format(str(info["d_swap"]))
		s += "Device size: 0x{:07X} ({:.2f} MB)\n".format(info["device_size"], info["device_size"] / 1024 / 1024)
		s += "Voltage: {:.1f}–{:.1f} V\n".format(info["vdd_min"], info["vdd_max"])
		s += "Single write: {:s}\n".format(str(info["single_write"]))
		if "buffer_size" in info:
			s += "Buffered write: {:s} ({:d} Bytes)\n".format(str(info["buffer_write"]), info["buffer_size"])
		else:
			s += "Buffered write: {:s}\n".format(str(info["buffer_write"]))
		if info["chip_erase"]: s += "Chip erase: {:d}–{:d} ms\n".format(info["chip_erase_time_avg"], info["chip_erase_time_max"])
		if info["sector_erase"]: s += "Sector erase: {:d}–{:d} ms\n".format(info["sector_erase_time_avg"], info["sector_erase_time_max"])
		if info["tb_boot_sector"] is not False: s += "Sector flags: {:s}\n".format(str(info["tb_boot_sector"]))
		pos = 0
		oversize = False
		s = s[:-1]
		for i in range(0, info['erase_sector_regions']):
			esb = info['erase_sector_blocks'][i]
			s += "\nRegion {:d}: 0x{:07X}–0x{:07X} @ 0x{:X} Bytes × {:d}".format(i+1, pos, pos+esb[2]-1, esb[0], esb[1])
			if oversize: s += " (alt)"
			pos += esb[2]
			if pos >= info['device_size']:
				pos = 0
				oversize = True
		#s += "\nSHA-1: {:s}".format(info["sha1"])
		info["info"] = s

		return info

class Flashcart_DMG_MMSA(Flashcart):
	#def __init__(self, config={}, cart_write_fncptr=None, cart_read_fncptr=None):
	#	super().__init__(config=config, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr)
	
	def ReadCFI(self):
		return False

	def GetMBC(self):
		return 0x105
	
	def SupportsSectorErase(self):
		return False
	
	def SupportsChipErase(self):
		return True
	
	def EraseHiddenSector(self, buffer):
		#time_start = time.time()
		if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"SECTOR_ERASE", "sector_pos":0, "time_start":time.time(), "abortable":False})
		
		self.UnlockForWriting()

		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x60 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x04 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		lives = 10
		while lives > 0:
			if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"SECTOR_ERASE", "sector_pos":0, "time_start":time.time(), "abortable":False})
			sr = ord(self.CartRead(0))
			dprint("Status Register Check: 0x{:X} & 0x{:X} == 0x{:X}? {:s}".format(sr, 0x80, 0x80, str(sr == 0x80)))
			if sr == 0x80: break
			time.sleep(0.5)
			lives -= 1
		if lives == 0:
			raise("Hidden Sector Erase Timeout Error")
		
		# Write Hidden Sector
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x60 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xE0 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x2100, 0x01 ],
		]
		self.CartWrite(cmds)
		
		# Disable writes to MBC registers
		cmds = [
			[ 0x120, 0x10 ],
			[ 0x13F, 0xa5 ],
		]
		self.CartWrite(cmds)
		# Undo Wakeup
		cmds = [
			[ 0x120, 0x08 ],
			[ 0x13F, 0xa5 ],
		]
		self.CartWrite(cmds)
		return True

	def ChipErase(self):
		time_start = time.time()
		if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"ERASE", "time_start":time_start, "abortable":False})

		self.UnlockForWriting()

		# Erase Chip
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x80 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x10 ],
			[ 0x13F, 0xA5 ]
		]
		self.CartWrite(cmds)
		lives = 10
		while lives > 0:
			if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"ERASE", "time_start":time_start, "abortable":False})
			sr = ord(self.CartRead(0))
			dprint("Status Register Check: 0x{:X} & 0x{:X} == 0x{:X}? {:s}".format(sr, 0x80, 0x80, str(sr == 0x80)))
			if sr == 0x80: break
			time.sleep(0.5)
			lives -= 1
		if lives == 0:
			raise Exception("Chip Erase Timeout Error")

		# Reset flash to read mode
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x40 ],
			[ 0x126, 0x80 ],
			[ 0x127, 0xF0 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)

		# Map all the flash memory before writing
		cmds = [
			[ 0x120, 0x04 ],
			[ 0x13F, 0xa5 ],
		]
		self.CartWrite(cmds)
		return True

	def Unlock(self):
		self.UnlockForWriting()

	def UnlockForWriting(self):
		time_start = time.time()
		if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"UNLOCK", "time_start":time_start, "abortable":False})
		
		self.CartWrite([[ 0x2100, 0x01 ]])
		# Enable Flash Chip Access
		cmds = [
			[ 0x120, 0x09 ],
			[ 0x121, 0xAA ],
			[ 0x122, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		# Re-Enable writes to MBC registers
		cmds = [
			[ 0x120, 0x11 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		# Disable flash chip protection
		cmds = [
			[ 0x120, 0x0A ],
			[ 0x125, 0x62 ],
			[ 0x126, 0x04 ],
			[ 0x13F, 0xA5 ],
			[ 0x120, 0x02 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		self.CartWrite([[ 0x2100, 0x01 ]])
		
		# Suspend potential previous erase
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x00 ],
			[ 0x126, 0x00 ],
			[ 0x127, 0xB0 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		
		# Unlock Hidden Sector
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x60 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		cmds = [
			[ 0x120, 0x0F ],
			[ 0x125, 0x00 ],
			[ 0x126, 0x00 ],
			[ 0x127, 0x40 ],
			[ 0x13F, 0xA5 ],
		]
		self.CartWrite(cmds)
		lives = 10
		while lives > 0:
			sr = ord(self.CartRead(0))
			dprint("Status Register Check: 0x{:X} & 0x{:X} == 0x{:X}? {:s}".format(sr, 0x80, 0x80, str(sr == 0x80)))
			if sr == 0x80: break
			if self.PROGRESS_FNCPTR is not None: self.PROGRESS_FNCPTR({"action":"UNLOCK", "time_start":time_start, "abortable":False})
			time.sleep(0.5)
			lives -= 1
		if lives == 0:
			raise Exception("Hidden Sector Unlock Timeout Error")
