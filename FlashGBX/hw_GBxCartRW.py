# -*- coding: utf-8 -*-
# ＵＴＦ－８
import serial, os, serial.tools.list_ports
from serial import SerialException
import sys, time, re, glob, math, struct, json, statistics, traceback, zlib, random
from .DataTransfer import *
from .RomFileDMG import *
from .RomFileAGB import *

class GbxDevice:
	DEVICE_NAME = "GBxCart RW"
	DEVICE_MIN_FW = 17
	DEVICE_MAX_FW = 19
	
	DEVICE_CMD = {
		"CART_MODE":'C',
		"GB_MODE":1,
		"GBA_MODE":2,
		# GB/GBC defines/commands
		"SET_START_ADDRESS":'A',
		"READ_ROM_RAM":'R',
		"WRITE_RAM":'W',
		"SET_BANK":'B',
		"GB_CART_MODE":'G',
		# GBA defines/commands
		"EEPROM_NONE":0,
		"EEPROM_4KBIT":1,
		"EEPROM_64KBIT":2,
		"SRAM_FLASH_NONE":0,
		"SRAM_FLASH_256KBIT":1,
		"SRAM_FLASH_512KBIT":2,
		"SRAM_FLASH_1MBIT":3,
		"NOT_CHECKED":0,
		"NO_FLASH":1,
		"FLASH_FOUND":2,
		"FLASH_FOUND_ATMEL":3,
		"GBA_READ_ROM":'r',
		"GBA_READ_ROM_256BYTE":'j',
		"GBA_READ_SRAM":'m',
		"GBA_WRITE_SRAM":'w',
		"GBA_WRITE_ONE_BYTE_SRAM":'o',
		"GBA_CART_MODE":'g',
		"GBA_SET_EEPROM_SIZE":'S',
		"GBA_READ_EEPROM":'e',
		"GBA_WRITE_EEPROM":'p',
		"GBA_FLASH_READ_ID":'i',
		"GBA_FLASH_SET_BANK":'k',
		"GBA_FLASH_4K_SECTOR_ERASE":'s',
		"GBA_FLASH_WRITE_BYTE":'b',
		"GBA_FLASH_WRITE_ATMEL":'a',
		# Flash Cart commands
		"GB_FLASH_WE_PIN":'P',
			"WE_AS_AUDIO_PIN":'A',
			"WE_AS_WR_PIN":'W',
		"GB_FLASH_PROGRAM_METHOD":'E',
			"GB_FLASH_PROGRAM_555":0,
			"GB_FLASH_PROGRAM_AAA":1,
			"GB_FLASH_PROGRAM_555_BIT01_SWAPPED":2,
			"GB_FLASH_PROGRAM_AAA_BIT01_SWAPPED":3,
			"GB_FLASH_PROGRAM_5555":4,
			"GB_FLASH_PROGRAM_7AAA_BIT01_SWAPPED":5,
		"GB_FLASH_WRITE_BYTE":'F',
		"GB_FLASH_WRITE_64BYTE":'T',
		"GB_FLASH_WRITE_256BYTE":'X',
		"GB_FLASH_WRITE_BUFFERED_32BYTE":'Y',
		"GB_FLASH_BANK_1_COMMAND_WRITES":'N',
		"GB_FLASH_WRITE_64BYTE_PULSE_RESET":'J',
		"GB_FLASH_WRITE_INTEL_BUFFERED_32BYTE":'y',
		"GBA_FLASH_CART_WRITE_BYTE":'n',
		"GBA_FLASH_WRITE_64BYTE_SWAPPED_D0D1":'q',
		"GBA_FLASH_WRITE_256BYTE_SWAPPED_D0D1":'t',
		"GBA_FLASH_WRITE_256BYTE":'f',
		"GBA_FLASH_WRITE_INTEL_64BYTE":'l',
		"GBA_FLASH_WRITE_INTEL_64BYTE_WORD":'u',
		"GBA_FLASH_WRITE_INTEL_INTERLEAVED_256BYTE":'v',
		"GBA_FLASH_WRITE_SHARP_64BYTE":'x',
		"GBA_SAVEDATA_DETECT":'z',
		# General commands
		"SET_INPUT":'I',
		"SET_OUTPUT":'O',
		"SET_OUTPUT_LOW":'L',
		"SET_OUTPUT_HIGH":'H',
		"READ_INPUT":'D',
		"RESET_COMMON_LINES":'M',
		"READ_FIRMWARE_VERSION":'V',
		"READ_PCB_VERSION":'h',
		"VOLTAGE_3_3V":'3',
		"VOLTAGE_5V":'5',
		"RESET_AVR":'*',
		"RESET_VALUE":0x7E5E1,
		"XMAS_LEDS":'#',
		"XMAS_VALUE":0x7690FCD,
		"READ_BUFFER":0
	}
	PCB_VERSIONS = {1:'v1.0', 2:'v1.1', 4:'v1.3', 90:'XMAS', 100:'Mini'}
	SUPPORTED_CARTS = { 
		"DMG":{ "Generic ROM Cartridge":"RETAIL", "● Auto-Detect Flash Cartridge ●":"AUTODETECT" },
		"AGB":{ "Generic ROM Cartridge":"RETAIL", "● Auto-Detect Flash Cartridge ●":"AUTODETECT" }
	}
	
	FW = []
	MODE = None
	PORT = ''
	DEVICE = None
	WORKER = None
	INFO = { "last_action":None }
	CANCEL = False
	
	def __init__(self):
		pass
	
	def Initialize(self, flashcarts):
		if self.IsConnected(): self.DEVICE.close()
		
		conn_msg = []
		ports = []
		comports = serial.tools.list_ports.comports()
		for i in range(0, len(comports)):
			if comports[i].vid == 0x1A86 and comports[i].pid == 0x7523:
				ports.append(comports[i].device)
				break

		if len(ports) == 0: return False
		
		for i in range(0, len(ports)):
			try:
				dev = serial.Serial(ports[i], 1000000, timeout=0.5)
				self.DEVICE = dev
				try:
					self.LoadFirmwareVersion()
				except:
					self.DEVICE = None
				
				if self.DEVICE is None or not self.IsConnected() or self.FW[0] == b'':
					dev.close()
					self.DEVICE = None
					conn_msg.append([3, "Couldn’t communicate with the GBxCart RW device on port " + ports[i] + ". Please disconnect and reconnect the device, then try again."])
					continue
				if self.FW[0] < self.DEVICE_MIN_FW:
					dev.close()
					self.DEVICE = None
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " requires a firmware update to work with this software. Please try again after updating it to version R" + str(self.DEVICE_MIN_FW) + " or higher."])
					continue
				elif self.FW[0] > self.DEVICE_MAX_FW:
					conn_msg.append([0, "NOTE: The GBxCart RW device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
				
				if (self.FW[1] != 4):
					conn_msg.append([0, "NOTE: FlashGBX was developed to be used with GBxCart RW v1.3 and v1.3 Pro. Other revisions are untested and may not be fully compatible."])
				
				self.PORT = ports[i]
				
				# Load Flash Cartridge Handlers
				for mode in flashcarts.keys():
					for key in sorted(flashcarts[mode].keys(), key=str.casefold):
						self.SUPPORTED_CARTS[mode][key] = flashcarts[mode][key]
				
				# Stop after first found device
				break
			
			except SerialException as e:
				if "Permission" in str(e):
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " couldn’t be accessed. Make sure your user account has permission to use it and it’s not already in use by another application.\n\n" + str(e)])
				else:
					conn_msg.append([3, "A critical error occured while trying to access the GBxCart RW device on port " + ports[i] + ".\n\n" + str(e)])
				continue
		
		conn_msg.append([0, "NOTE: This is an unofficial tool for GBxCart RW. Visit https://www.gbxcart.com/ for officially supported options."])
		return conn_msg
	
	def IsConnected(self):
		if self.DEVICE is None: return False
		if not self.DEVICE.isOpen(): return False
		try:
			self.LoadFirmwareVersion()
			return True
		except SerialException as e:
			return False
	
	def Close(self):
		if self.IsConnected():
			try:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V']) # set to lower voltage when closing for safety
				self.DEVICE.close()
			except:
				self.DEVICE = None
			self.MODE = None
	
	def GetName(self):
		self.GetFullName()
		return self.DEVICE_NAME
	
	def GetFullName(self):
		fw, pcb = self.FW
		if pcb in self.PCB_VERSIONS:
			self.DEVICE_NAME = "GBxCart RW " + self.PCB_VERSIONS[pcb]
		else:
			self.DEVICE_NAME = "GBxCart RW (unknown revision)"
		return self.DEVICE_NAME + " – Firmware R" + str(fw) + " (" + str(self.PORT) + ")"
	
	def GetPort(self):
		return self.PORT
	
	def LoadFirmwareVersion(self):
		self.write(self.DEVICE_CMD['READ_FIRMWARE_VERSION'])
		fw = bytearray(self.read(1))[0]
		self.write(self.DEVICE_CMD['READ_PCB_VERSION'])
		pcb = bytearray(self.read(1))[0]
		self.FW = [fw, pcb]
	
	def CanSetVoltageManually(self):
		fw, pcb = self.FW
		if not pcb in (4, 100):
			return True
		else:
			return False
	
	def CanSetVoltageAutomatically(self):
		fw, pcb = self.FW
		if pcb in (1, 2, 100):
			return False
		else:
			return True
	
	def GetSupprtedModes(self):
		fw, pcb = self.FW
		if pcb == 100:
			return ["DMG"]
		else:
			return ["DMG", "AGB"]
	
	def GetMode(self):
		return self.MODE
	
	def GetSupportedCartridgesDMG(self):
		return (list(self.SUPPORTED_CARTS['DMG'].keys()), list(self.SUPPORTED_CARTS['DMG'].values()))
	
	def GetSupportedCartridgesAGB(self):
		return (list(self.SUPPORTED_CARTS['AGB'].keys()), list(self.SUPPORTED_CARTS['AGB'].values()))
	
	def wait_for_ack(self):
		buffer = self.read(1)
		timeout = 5
		while buffer != b'1':
			print("wait_for_ack(): No valid acknowledgement received (", buffer, "). ", end="")
			timeout -= 1
			if timeout < 1:
				print("Failed.")
				traceback.print_stack()
				print("\nwait_for_ack(): Skipping...")
				return False
			else:
				print("Retrying...")
				time.sleep(0.2)
				buffer = self.read(1)
		return True
	
	def read(self, length=64, last=False):
		readlen = length
		if readlen > 64: readlen = 64
		lives = 5
		while True:
			if length <= 64:
				buffer = self.DEVICE.read(readlen)
				if len(buffer) != readlen:
					print("read(): Failed to receive {:d} byte(s) from the device. Discarding {:d} byte(s).".format(readlen, len(buffer)))
					self.write('0')
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					return False
				
				if length == 1:
					return buffer
				else:
					if last:
						self.write('0')
					if not last:
						self.write('1')
					return buffer[:length]
			
			else: # length > 64
				mbuffer = bytearray()
				for i in range(0, length, 64):
					buffer = self.DEVICE.read(readlen)
					if len(buffer) != readlen:
						print("read(): Failed to receive {:d} byte(s) from the device during iteration {:d}. Discarding {:d} byte(s).".format(readlen, i, len(buffer)))
						self.write('0')
						self.DEVICE.reset_input_buffer()
						self.DEVICE.reset_output_buffer()
						return False
					
					mbuffer += buffer
					if not (i + 64 >= length):
						self.write('1')
				
				if last:
					self.write('0')
				
				return mbuffer[:length]
	
	def write(self, data, wait_for_ack=False):
		if not isinstance(data, bytearray):
			data = bytearray(data, 'ascii')
		self.DEVICE.write(data)
		self.DEVICE.flush()
		
		if wait_for_ack:
			return self.wait_for_ack()
	
	def ReadROM(self, offset, length, set_address=True):
		buffer = False
		lives = 10
		while buffer == False:
			if self.MODE == "DMG":
				if set_address:
					self.set_number(offset, self.DEVICE_CMD['SET_START_ADDRESS'])
				self.set_mode(self.DEVICE_CMD['READ_ROM_RAM'])
				buffer = self.read(length, last=True)
			elif self.MODE == "AGB":
				if set_address:
					self.set_number(math.floor(offset / 2), self.DEVICE_CMD['SET_START_ADDRESS'])
				self.set_mode(self.DEVICE_CMD['GBA_READ_ROM'])
				buffer = self.read(length, last=True)
			
			if buffer == False:
				lives -= 1
				if lives == 0:
					self.CANCEL = True
					print("\nCouldn’t recover from the error. Please try again from the beginning.")
					return False
				print("\nStarting over segment at 0x{:06X}...".format(offset))
				set_address = True
		
		return buffer
	
	def gbx_flash_write_address_byte(self, address, data):
		if self.MODE == "DMG":
			return self.gb_flash_write_address_byte(address, data)
		elif self.MODE == "AGB":
			return self.gba_flash_write_address_byte(address, data)
	
	def gba_flash_write_address_byte(self, address, data):
		address = int(address / 2)
		address = format(address, 'x')
		buffer = self.DEVICE_CMD['GBA_FLASH_CART_WRITE_BYTE'] + address + '\x00'
		self.write(buffer)
		time.sleep(0.001)
		data = format(data, 'x')
		buffer = self.DEVICE_CMD['GBA_FLASH_CART_WRITE_BYTE'] + data + '\x00'
		self.write(buffer)
		time.sleep(0.001)
		ack = self.wait_for_ack()
		if ack == False:
			print("Can’t continue. Please try again.")
			self.CANCEL = True
			return False
	
	def gb_flash_write_address_byte(self, address, data):
		address = format(address, 'x')
		buffer = self.DEVICE_CMD['GB_FLASH_WRITE_BYTE'] + address + '\x00'
		self.write(buffer)
		buffer = format(data, 'x') + '\x00'
		self.write(buffer)
		ack = self.wait_for_ack()
		if ack == False:
			print("Can’t continue. Please try again.")
			self.CANCEL = True
			return False
	
	def gbx_flash_write_data_bytes(self, command, data):
		buffer = bytearray(self.DEVICE_CMD[command], "ascii") + bytearray(data)
		self.write(buffer)
	
	def set_bank(self, address, bank):
		address = format(address, 'x')
		buffer = self.DEVICE_CMD['SET_BANK'] + address + '\x00'
		self.write(buffer)
		time.sleep(0.005)
		
		bank = format(bank, 'd')
		buffer = self.DEVICE_CMD['SET_BANK'] + bank + '\x00'
		self.write(buffer)
		time.sleep(0.005)
	
	def set_mode(self, command):
		buffer = format(command, 's')
		self.write(buffer)

	def set_number(self, number, command):
		buffer = format(command, 's') + format(int(number), 'x') + '\x00'
		self.write(buffer)
		if command in ("SET_START_ADDRESS"):
			time.sleep(0.005)
		elif command in ("VOLTAGE_3_3V", "VOLTAGE_5V"):
			time.sleep(0.3)
	
	def EnableRAM(self, mbc=1, enable=True):
		#self.ReadROM(0, 64)
		if enable:
			if mbc <= 4:
				self.set_bank(0x6000, 1)
			self.set_bank(0x0000, 0x0A)
		else:
			self.set_bank(0x0000, 0x00)
		time.sleep(0.2)
	
	def SetBankROM(self, bank, mbc=5):
		if mbc == 1: # MBC1
			self.set_bank(0x6000, 0)
			self.set_bank(0x4000, bank >> 5)
			self.set_bank(0x2000, bank & 0x1F)
		elif mbc == 1.1: # Hudson MBC1
			self.set_bank(0x4000, bank >> 4)
			if (bank < 10):
				self.set_bank(0x2000, bank & 0x1F)
			else:
				self.set_bank(0x2000, 0x10 | (bank & 0x1F))
		else:
			self.set_bank(0x2100, (bank & 0xFF))
			if bank > 255:
				self.set_bank(0x3000, ((bank >> 8) & 0xFF))
	
	def SetBankRAM(self, bank):
		self.set_bank(0x4000, (bank & 0xFF))
	
	def ReadFlashSaveID(self):
		makers = { 0x1F:"ATMEL", 0xBF:"SST/SANYO", 0xC2:"MACRONIX", 0x32:"PANASONIC", 0x62:"SANYO" }
		self.set_mode(self.DEVICE_CMD['GBA_FLASH_READ_ID'])
		time.sleep(0.02)
		buffer = self.DEVICE.read(2)
		if buffer[0] in makers.keys():
			return makers[buffer[0]]
		else:
			return buffer[0]
	
	def SetMode(self, mode):
		if mode == "DMG":
			self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
			self.MODE = "DMG"
		elif mode == "AGB":
			self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
			self.MODE = "AGB"
		self.set_number(0, self.DEVICE_CMD['SET_START_ADDRESS'])

	def AutoDetectFlash(self, limitVoltage=False):
		flash_types = []
		flash_type = 0
		if limitVoltage:
			self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
		
		if self.MODE == "DMG":
			supported_carts = list(self.SUPPORTED_CARTS['DMG'].values())
			for f in range(2, len(supported_carts)):
				flashcart_meta = supported_carts[f]
				
				self.set_mode(self.DEVICE_CMD['GB_CART_MODE'])
				if "flash_commands_on_bank_1" in flashcart_meta:
					self.set_mode(self.DEVICE_CMD['GB_FLASH_BANK_1_COMMAND_WRITES'])
				
				if flashcart_meta["write_pin"] == "WR":
					self.set_mode(self.DEVICE_CMD['GB_FLASH_WE_PIN'])
					self.set_mode(self.DEVICE_CMD['WE_AS_WR_PIN'])
				elif flashcart_meta["write_pin"] in ("AUDIO", "VIN"):
					self.set_mode(self.DEVICE_CMD['GB_FLASH_WE_PIN'])
					self.set_mode(self.DEVICE_CMD['WE_AS_AUDIO_PIN'])
				
				# Unlock Flash
				if "unlock" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["unlock"])):
						addr = flashcart_meta["commands"]["unlock"][i][0]
						data = flashcart_meta["commands"]["unlock"][i][1]
						count = flashcart_meta["commands"]["unlock"][i][2]
						for j in range(0, count):
							self.gbx_flash_write_address_byte(addr, data)
				
				# Reset Flash
				if "reset" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["reset"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
				
				# Read Identifier
				if "read_identifier" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["read_identifier"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["read_identifier"][i][0], flashcart_meta["commands"]["read_identifier"][i][1])
					flash_id_found = False
					for i in range(0, len(flashcart_meta["flash_ids"])):
						flash_id = list(self.ReadROM(0, 64)[0:len(flashcart_meta["flash_ids"][i])])
						if not len(flashcart_meta["flash_ids"][i]) == 0 and flash_id in flashcart_meta["flash_ids"]: flash_id_found = True
					if not flash_id_found and len(flashcart_meta["flash_ids"]) > 0:
						pass
				
				# Reset Flash
				if "reset" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["reset"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
				
				if flash_id_found:
					flash_type = f
					flash_types.append(flash_type)
			
			if not flash_id_found:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
		
		elif self.MODE == "AGB":
			supported_carts = list(self.SUPPORTED_CARTS['AGB'].values())
			for f in range(2, len(supported_carts)):
				flashcart_meta = supported_carts[f]
				
				# Unlock Flash
				if "unlock" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["unlock"])):
						addr = flashcart_meta["commands"]["unlock"][i][0]
						data_ = flashcart_meta["commands"]["unlock"][i][1]
						count = flashcart_meta["commands"]["unlock"][i][2]
						for j in range(0, count):
							self.gbx_flash_write_address_byte(addr, data_)
				
				# Reset Flash
				if "reset" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["reset"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
				
				# Read Identifier
				if "read_identifier" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["read_identifier"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["read_identifier"][i][0], flashcart_meta["commands"]["read_identifier"][i][1])
					flash_id_found = False
					for i in range(0, len(flashcart_meta["flash_ids"])):
						flash_id = list(self.ReadROM(0, 64)[0:len(flashcart_meta["flash_ids"][i])])
						if flash_id in flashcart_meta["flash_ids"]: flash_id_found = True
					if not flash_id_found and len(flashcart_meta["flash_ids"]) > 0:
						pass
				
				# Reset Flash
				if "reset" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["reset"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
				
				if flash_id_found:
					flash_type = f
					flash_types.append(flash_type)
		
		return flash_types
	
	def CheckFlashID(self, limitVoltage=False):
		if limitVoltage:
			self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
		
		flash_id_lines = []
		if self.MODE == "DMG":
			ret_rom = "[     ROM     ] "
			methods = [
				{'we':'WR', 'read_identifier':[[0x555, 0xAA], [0x2AA, 0x55], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0x555, 0xA9], [0x2AA, 0x56], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0xAAA, 0xAA], [0x555, 0x55], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0xAAA, 0xA9], [0x555, 0x56], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0xAA, 0x98]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0x5555, 0xAA], [0x2AAA, 0x55], [0x5555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0x5555, 0xA9], [0x2AAA, 0x56], [0x5555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'WR', 'read_identifier':[[0x7AAA, 0xA9], [0x7555, 0x56], [0x7AAA, 0x90]], 'reset':[[0x7000, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0x555, 0xAA], [0x2AA, 0x55], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0x555, 0xA9], [0x2AA, 0x56], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0xAAA, 0xAA], [0x555, 0x55], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0xAAA, 0xA9], [0x555, 0x56], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0x5555, 0xAA], [0x2AAA, 0x55], [0x5555, 0x90]], 'reset':[[0, 0xF0]]},
				{'we':'AUDIO', 'read_identifier':[[0x5555, 0xA9], [0x2AAA, 0x56], [0x5555, 0x90]], 'reset':[[0, 0xF0]]},
			]
			
			self.set_mode(self.DEVICE_CMD['GB_CART_MODE'])
			if not limitVoltage: self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
			rom = self.ReadROM(0, 64)[0:8]
			for i in range(0, len(methods)):
				method = methods[i]
				self.set_mode(self.DEVICE_CMD['GB_FLASH_WE_PIN'])
				self.set_mode(self.DEVICE_CMD['WE_AS_' + method['we'] + '_PIN'])
				for i in range(0, len(method['read_identifier'])):
					self.gbx_flash_write_address_byte(method['read_identifier'][i][0], method["read_identifier"][i][1])
				flash_id = self.ReadROM(0, 64)[0:8]
				for i in range(0, len(method['reset'])):
					self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
				if rom == flash_id: continue
				
				method_string = "[" + method['we'].ljust(5) + "/{:4X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
				flash_id_lines.append([method_string, flash_id])
		
		elif self.MODE == "AGB":
			ret_rom = "[   ROM   ] "
			methods = [
				{'read_identifier':[[0x555, 0xAA], [0x2AA, 0x55], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'read_identifier':[[0x555, 0xA9], [0x2AA, 0x56], [0x555, 0x90]], 'reset':[[0, 0xF0]]},
				{'read_identifier':[[0xAAA, 0xAA], [0x555, 0x55], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'read_identifier':[[0xAAA, 0xA9], [0x555, 0x56], [0xAAA, 0x90]], 'reset':[[0, 0xF0]]},
				{'read_identifier':[[0, 0x90]], 'reset':[[0, 0xFF]]},
			]
			
			self.set_mode(self.DEVICE_CMD['GBA_CART_MODE'])
			self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
			rom = self.ReadROM(0, 64)[0:8]
			for i in range(0, len(methods)):
				method = methods[i]
				for i in range(0, len(method['read_identifier'])):
					self.gbx_flash_write_address_byte(method['read_identifier'][i][0], method["read_identifier"][i][1])
				flash_id = self.ReadROM(0, 64)[0:8]
				for i in range(0, len(method['reset'])):
					self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
				if rom == flash_id: continue
				
				method_string = "[{:6X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
				flash_id_lines.append([method_string, flash_id])
		
		ret = ""
		for i in range(0, len(flash_id_lines)):
			ret += flash_id_lines[i][0] + " "
			for j in range(0, 8):
				ret += "{:02X} ".format(flash_id_lines[i][1][j])
			ret += "\n"
		
		if ret != "":
			for j in range(0, 8):
				ret_rom += "{:02X} ".format(rom[j])
			ret_rom += "\n"
			ret = ret_rom + ret
		
		if limitVoltage and self.MODE == "DMG":
			self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
		
		return ret
	
	def ReadInfo(self):
		if not self.IsConnected() and not self.Initialize(): raise Exception("Couldn’t access the the device.")
		data = {}
		header = self.ReadROM(0x000000, 0x000180)
		
		if self.MODE == "DMG":
			data = RomFileDMG(header).GetHeader()
		
		elif self.MODE == "AGB":
			data = RomFileAGB(header).GetHeader()
			size_check = header[0xA0:0xA0+16]
			currAddr = 0x400000
			while currAddr < 0x2000000:
				buffer = self.ReadROM(currAddr + 0x0000A0, 64)[:16]
				if buffer == size_check: break
				currAddr += 0x400000
			data["rom_size"] = currAddr
		
		self.INFO = data
		self.INFO["flash_type"] = 0
		self.INFO["last_action"] = 0
		
		return data

	def BackupROM(self, fncSetProgress, path="ROM.gb", mbc=0x00, rom_banks=512, agb_rom_size=0):
		config = { 'mode':1, 'port':self, 'path':path, 'mbc':mbc, 'rom_banks':rom_banks, 'agb_rom_size':agb_rom_size }
		self.WORKER = DataTransfer(config)
		self.WORKER.updateProgress.connect(fncSetProgress)
		self.WORKER.start()

	def BackupRAM(self, fncSetProgress, path="ROM.sav", mbc=0x00, save_type=0):
		config = { 'mode':2, 'port':self, 'path':path, 'mbc':mbc, 'save_type':save_type }
		self.WORKER = DataTransfer(config)
		self.WORKER.updateProgress.connect(fncSetProgress)
		self.WORKER.start()

	def RestoreRAM(self, fncSetProgress, path="ROM.sav", mbc=0x00, save_type=0, erase=False):
		config = { 'mode':3, 'port':self, 'path':path, 'mbc':mbc, 'save_type':save_type, 'erase':erase }
		self.WORKER = DataTransfer(config)
		self.WORKER.updateProgress.connect(fncSetProgress)
		self.WORKER.start()

	def FlashROM(self, fncSetProgress, path="ROM.gb", cart_type=0, trim_rom=False, override_voltage=False):
		config = { 'mode':4, 'port':self, 'path':path, 'cart_type':cart_type, 'trim_rom':trim_rom, 'override_voltage':override_voltage }
		self.WORKER = DataTransfer(config)
		self.WORKER.updateProgress.connect(fncSetProgress)
		self.WORKER.start()
	
	def _TransferData(self, mode, signal, args): # called by thread
		if not self.IsConnected() and not self.Initialize(): raise Exception("Couldn’t access the the device.")
		
		path = args[0]
		if self.INFO == None: self.ReadInfo()
		self.INFO["last_path"] = path
		self.INFO["last_action"] = mode
		measure_points = []
		time_start = time.time()
		bank_size = 0x4000
		
		# main work
		if mode == 1: # Backup ROM
			if self.MODE == "DMG":
				mbc = args[1]
				bank_count = args[2]
				rom_size = bank_count * bank_size
			elif self.MODE == "AGB":
				rom_size = args[3]
				if rom_size == 0:
					rom_size = 32 * 1024 * 1024
			
			data_dump = bytearray()
			
			startAddr = 0
			currAddr = 0
			recvBytes = 0
			speed = 0
			time_left = 0
			
			signal.emit(None, 0, rom_size, 0, 0, 0)
			last_emit = time.time()
			
			try:
				file = open(path, "wb")
			except PermissionError as e:
				signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"FlashGBX doesn’t have permission to access this file for writing:\n" + path, "abortable":False}, 0, 0, 0, 0, 0)
				return False
			
			if self.MODE == "DMG":
				endAddr = bank_size
			else:
				endAddr = rom_size
				bank_count = 1
			
			for bank in range(0, bank_count):
				if self.MODE == "DMG":
					if bank > 0:
						startAddr = bank_size
						endAddr = startAddr + bank_size
					self.SetBankROM(bank, mbc)
				
				buffer_len = 0x1000 # debug todo
				for currAddr in range(startAddr, endAddr, buffer_len):
					if self.CANCEL:
						signal.emit({"action":"ABORT", "abortable":False}, 0, 0, 0, 0, 0)
						return
					
					if currAddr == startAddr:
						buffer = self.ReadROM(currAddr, buffer_len, True)
					else:
						buffer = self.ReadROM(currAddr, buffer_len, False)
					
					if buffer == False:
						signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An I/O error occured. Please try again from the beginning.", "abortable":False}, 0, 0, 0, 0, 0)
						return False
					
					data_dump.extend(buffer)
					file.write(buffer)
					recvBytes += buffer_len
					
					# Report back to GUI
					if recvBytes % buffer_len == 0:
						now = time.time()
						measure_points.append(now - last_emit)
						last_emit = now
						if len(measure_points) >= 16:
							time_delta = statistics.mean(measure_points)
							speed = buffer_len / time_delta
							time_elapsed = time.time() - time_start
							time_left = (time_elapsed / (recvBytes/rom_size)) - time_elapsed
						if len(measure_points) >= 512:
							measure_points = measure_points[-512:]
					
					if not recvBytes == rom_size: signal.emit(None, recvBytes, rom_size, speed/1024, time.time()-time_start, time_left)

			# check for flashgbx trimmed rom
			if not os.path.splitext(path)[0].endswith("_notrimfix"): # debug
				rom_size = len(data_dump)
				trm_index = data_dump.find(b'TRIMFLASHGBX')
				if trm_index != -1:
					free_byte = data_dump[trm_index-4]
					data_dump = data_dump[0:trm_index-4] + bytes([free_byte] * (rom_size - (trm_index-4)))
					file.seek(0)
					file.write(data_dump)
			
			file.close()
			
			# calculate global checksum
			chk = 0
			if self.MODE == "DMG":
				for i in range(0, len(data_dump), 2):
					if i != 0x14E:
						chk = chk + data_dump[i + 1]
						chk = chk + data_dump[i]
				chk = chk & 0xFFFF
			elif self.MODE == "AGB":
				chk = zlib.crc32(data_dump) & 0xffffffff
			
			self.INFO["rom_checksum_calc"] = chk
			signal.emit(None, recvBytes, rom_size, speed/1024, time.time()-time_start, time_left)
		
		#########################################
		
		elif mode == 2 or mode == 3: # Backup or Restore RAM
			data_dump = bytearray()
			data_import = bytearray()
			self.ReadROM(0, 64) # fix
			
			startAddr = 0
			if self.MODE == "DMG":
				bank_size = 0x2000
				mbc = args[1]
				save_size = args[2]
				bank_count = int(max(save_size, bank_size) / bank_size)
				self.EnableRAM(mbc=mbc, enable=True)
				transfer_size = 64
				startAddr = 0xA000
			
			elif self.MODE == "AGB":
				bank_size = 0x10000
				save_type = args[2]
				bank_count = 1
				transfer_size = 64
				eeprom_size = 0
				
				if save_type == 0:
					return
				elif save_type == 1: # EEPROM 512 Byte
					save_size = 512
					read_command = 'GBA_READ_EEPROM'
					write_command = 'GBA_WRITE_EEPROM'
					transfer_size = 8
					eeprom_size = 1
				elif save_type == 2: # EEPROM 8 KB
					save_size = 8 * 1024
					read_command = 'GBA_READ_EEPROM'
					write_command = 'GBA_WRITE_EEPROM'
					transfer_size = 8
					eeprom_size = 2
				elif save_type == 3: # SRAM 32 KB
					save_size = 32 * 1024
					read_command = 'GBA_READ_SRAM'
					write_command = 'GBA_WRITE_SRAM'
				elif save_type == 4: # SRAM 64 KB
					save_size = 64 * 1024
					read_command = 'GBA_READ_SRAM'
					write_command = 'GBA_WRITE_SRAM'
				elif save_type == 5: # FLASH 64 KB
					save_size = 64 * 1024
					read_command = 'GBA_READ_SRAM'
				elif save_type == 6: # FLASH 128 KB
					save_size = 128 * 1024
					read_command = 'GBA_READ_SRAM'
					bank_count = 2
				else:
					return
				
				# Get Save Flash Manufacturer
				flash_id = None
				if save_type == 5 or save_type == 6:
					flash_id = self.ReadFlashSaveID()
					if flash_id == "ATMEL":
						print("NOTE: For save data this cartridge uses an ATMEL chip which is untested.")
						transfer_size = 128
			
			# Prepare some stuff
			if mode == 2: # Backup
				try:
					file = open(path, "wb")
				except PermissionError as e:
					signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"FlashGBX doesn’t have permission to access this file for writing:\n" + path, "abortable":False}, 0, 0, 0, 0, 0)
					return False
			
			elif mode == 3: # Restore
				if args[3]: # Erase
					data_import = save_size * b'\xFF'
				else:
					with open(path, "rb") as file: data_import = file.read()
				
				if save_size > len(data_import):
					data_import += b'\xFF' * (save_size - len(data_import))
			
			currAddr = 0
			pos = 0
			speed = 0
			time_left = 0
			signal.emit(None, 0, save_size, 0, 0, 0)
			
			for bank in range(0, bank_count):
				if self.MODE == "DMG":
					endAddr = startAddr + bank_size
					if endAddr > (startAddr + save_size): endAddr = startAddr + save_size
					self.SetBankRAM(bank)
					
				elif self.MODE == "AGB":
					endAddr = startAddr + min(save_size, bank_size)
					if endAddr > (startAddr + save_size): endAddr = startAddr + save_size
					if save_type == 1 or save_type == 2: # EEPROM
						self.set_number(eeprom_size, self.DEVICE_CMD['GBA_SET_EEPROM_SIZE'])
					elif (save_type == 5 or save_type == 6) and bank > 0: # FLASH
						self.set_number(bank, self.DEVICE_CMD['GBA_FLASH_SET_BANK'])
				
				self.set_number(startAddr, self.DEVICE_CMD['SET_START_ADDRESS'])
				
				buffer_len = transfer_size
				sector = 0
				for currAddr in range(startAddr, endAddr, buffer_len):
					if self.CANCEL:
						if self.MODE == "DMG":
							self.EnableRAM(mbc=mbc, enable=False)
						elif self.MODE == "AGB":
							if bank > 0: self.set_number(0, self.DEVICE_CMD['GBA_FLASH_SET_BANK'])
							self.set_mode(self.DEVICE_CMD['READ_ROM_RAM'])
						self.ReadInfo()
						signal.emit({"action":"ABORT", "abortable":False}, 0, 0, 0, 0, 0)
						return
					
					if mode == 2: # Backup
						if self.MODE == "DMG":
							buffer = self.ReadROM(currAddr, buffer_len)
						elif self.MODE == "AGB":
							if currAddr + buffer_len < save_size:
								last = False
							else:
								last = True
							self.set_mode(self.DEVICE_CMD[read_command])
							buffer = self.read(buffer_len, last)
							if buffer == False:
								signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Backup failed, please try again.", "abortable":False}, 0, 0, 0, 0, 0)
								return False
						
						data_dump.extend(buffer)
						file.write(buffer)
					
					elif mode == 3: # Restore
						data = data_import[pos:pos+buffer_len]
						if self.MODE == "DMG":
							self.gbx_flash_write_data_bytes("WRITE_RAM", data)
						
						elif self.MODE == "AGB":
							if save_type == 5 or save_type == 6: # FLASH
								if flash_id == "ATMEL":
									self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_ATMEL", data)
								else:
									if (currAddr % 4096 == 0):
										self.set_number(sector, self.DEVICE_CMD['GBA_FLASH_4K_SECTOR_ERASE'])
										self.wait_for_ack()
										sector += 1
										while True: # wait for 0xFF (= erase done)
											self.set_number(currAddr, self.DEVICE_CMD['SET_START_ADDRESS'])
											self.set_mode(self.DEVICE_CMD[read_command])
											buffer = self.read(buffer_len, last=True)
											if buffer[0] == 0xFF: break
											time.sleep(0.01)
										self.set_number(currAddr, self.DEVICE_CMD['SET_START_ADDRESS'])
									
									self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_BYTE", data)
							
							else: # EEPROM / SRAM
								self.gbx_flash_write_data_bytes(write_command, data)
						
						self.wait_for_ack()
					
					pos += buffer_len
					
					if not pos == save_size: signal.emit(None, pos, save_size, speed/1024, time.time()-time_start, 0)
					self.INFO["transfered"] = pos
			
			if self.MODE == "DMG":
				self.EnableRAM(mbc=mbc, enable=False)
			elif self.MODE == "AGB":
				if bank > 0: self.set_number(0, self.DEVICE_CMD['GBA_FLASH_SET_BANK'])
			
			if mode == 2: file.close()
			
			self.INFO["last_action"] = mode
			signal.emit(None, pos, pos, speed/1024, time.time()-time_start, 0)
		
		#########################################
		
		elif mode == 4: # Flash ROM
			with open(path, "rb") as file: data_import = file.read()
			
			if len(data_import) < 0x8000: # smallest flashable ROM is 32 KB
				data_import += b'\xFF' * (0x8000 - len(data_import))
			
			if args[2]: # trim_rom
				free_byte = data_import[len(data_import)-1]
				if free_byte == 0xFF: # or free_byte == 0x00:
					marker = bytes([free_byte] * 4) + b'TRIMFLASHGBX' # a trim marker, so dumps will still be valid
					for i in range(len(data_import)-1, -1, -1):
						if data_import[i] != free_byte: break
						rom_size_trimmed = i
					rom_size_trimmed += len(marker)
					rom_size_trimmed = 0x1000 * (math.ceil(rom_size_trimmed / 0x1000))
					if rom_size_trimmed < len(data_import):
						data_import = data_import[0:rom_size_trimmed-len(marker)] + marker
			
			if self.MODE == "DMG":
				supported_carts = list(self.SUPPORTED_CARTS['DMG'].values())
			elif self.MODE == "AGB":
				supported_carts = list(self.SUPPORTED_CARTS['AGB'].values())

			cart_type = "RETAIL"
			for i in range(0, len(supported_carts)):
				if i == args[1]: cart_type = supported_carts[i]
			if cart_type == "RETAIL" or cart_type == "AUTODETECT": return False # Generic ROM Cartridge is not flashable
			
			flashcart_meta = cart_type.copy()
			
			signal.emit(None, 0, len(data_import), 0, 0, 0)
			time_start = time.time()
			speed = 0
			time_left = 0
			
			# Set Voltage
			if args[3] == 3.3:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
			elif args[3] == 5:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
			elif flashcart_meta["voltage"] == 3.3:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_3_3V'])
			elif flashcart_meta["voltage"] == 5:
				self.set_mode(self.DEVICE_CMD['VOLTAGE_5V'])
			
			if self.MODE == "DMG":
				self.set_mode(self.DEVICE_CMD['GB_CART_MODE'])
				if "flash_commands_on_bank_1" in flashcart_meta:
					self.set_mode(self.DEVICE_CMD['GB_FLASH_BANK_1_COMMAND_WRITES'])
				
				self.set_mode(self.DEVICE_CMD['GB_FLASH_WE_PIN'])
				if flashcart_meta["write_pin"] == "WR":
					self.set_mode(self.DEVICE_CMD['WE_AS_WR_PIN'])
				elif flashcart_meta["write_pin"] in ("AUDIO", "VIN"):
					self.set_mode(self.DEVICE_CMD['WE_AS_AUDIO_PIN'])

				if "single_write" in flashcart_meta["commands"] and len(flashcart_meta["commands"]["single_write"]) == 4:
					# Submit flash program commands to firmware
					self.set_mode(self.DEVICE_CMD['GB_FLASH_PROGRAM_METHOD'])
					for i in range(0, 3):
						self.write(bytearray(format(flashcart_meta["commands"]["single_write"][i][0], "x"), "ascii") + b'\x00', True)
						self.write(bytearray(format(flashcart_meta["commands"]["single_write"][i][1], "x"), "ascii") + b'\x00', True)
			
			elif self.MODE == "AGB":
				# Read a bit of ROM before starting
				self.ReadROM(0, 64)
			
			# Unlock Flash
			if "unlock" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["unlock"])):
					addr = flashcart_meta["commands"]["unlock"][i][0]
					data = flashcart_meta["commands"]["unlock"][i][1]
					count = flashcart_meta["commands"]["unlock"][i][2]
					for j in range(0, count):
						self.gbx_flash_write_address_byte(addr, data)
			
			# Reset Flash
			if "reset" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["reset"])):
					self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
			
			# Read Identifier
			if "read_identifier" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["read_identifier"])):
					self.gbx_flash_write_address_byte(flashcart_meta["commands"]["read_identifier"][i][0], flashcart_meta["commands"]["read_identifier"][i][1])
				flash_id_found = False
				for i in range(0, len(flashcart_meta["flash_ids"])):
					flash_id = list(self.ReadROM(0, 64)[0:len(flashcart_meta["flash_ids"][i])])
					if flash_id in flashcart_meta["flash_ids"]: flash_id_found = True
				if not flash_id_found and len(flashcart_meta["flash_ids"]) > 0:
					pass
			
			# Reset Flash
			if "reset" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["reset"])):
					self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
			
			# Chip Erase
			if "chip_erase" in flashcart_meta["commands"] and "sector_erase" not in flashcart_meta["commands"]:
				signal.emit({"action":"ERASE", "abortable":False}, 1, 0, 0, time.time()-time_start, 0)
				for i in range(0, len(flashcart_meta["commands"]["chip_erase"])):
					addr = flashcart_meta["commands"]["chip_erase"][i][0]
					data = flashcart_meta["commands"]["chip_erase"][i][1]
					if not addr == None:
						self.gbx_flash_write_address_byte(addr, data)
					if flashcart_meta["commands"]["chip_erase_wait_for"][i][0] != None:
						addr = flashcart_meta["commands"]["chip_erase_wait_for"][i][0]
						data = flashcart_meta["commands"]["chip_erase_wait_for"][i][1]
						timeout = flashcart_meta["chip_erase_timeout"]
						while True:
							signal.emit({"action":"ERASE", "abortable":False}, 1, 0, 0, time.time()-time_start, 0)
							if "wait_read_status_register" in flashcart_meta and flashcart_meta["wait_read_status_register"] == True:
								for j in range(0, len(flashcart_meta["commands"]["read_status_register"])):
									sr_addr = flashcart_meta["commands"]["read_status_register"][j][0]
									sr_data = flashcart_meta["commands"]["read_status_register"][j][1]
									self.gbx_flash_write_address_byte(sr_addr, sr_data)
							wait_for = self.ReadROM(addr, 64)
							wait_for = ((wait_for[1] << 8 | wait_for[0]) & flashcart_meta["commands"]["chip_erase_wait_for"][i][2])
							if wait_for == data: break
							time.sleep(1)
							timeout -= 1
							if timeout < 1:
								signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing the flash chip timed out. Please make sure the correct flash cartridge type is selected.", "abortable":False}, 0, 0, 0, 0, 0)
								return False
				
				# Reset Flash
				if "reset" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["reset"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
			
			self.set_number(0, self.DEVICE_CMD['SET_START_ADDRESS'])
			
			# Write Flash
			pos = 0
			currAddr = 0
			if self.MODE == "DMG":
				if "first_bank" in flashcart_meta: first_bank = flashcart_meta["first_bank"]
				if "start_addr" in flashcart_meta: currAddr = flashcart_meta["start_addr"]
				endAddr = 0x7FFF
				bank_count = math.ceil(len(data_import) / bank_size)
				self.SetBankROM(0)
			elif self.MODE == "AGB":
				currAddr = 0
				endAddr = len(data_import)
				first_bank = 0
				bank_count = 1
			
			time_start = time.time()
			last_emit = time.time()
			
			sectCount = None
			currSect = 0
			if "sector_erase" in flashcart_meta["commands"]:
				if isinstance(flashcart_meta["sector_size"], list):
					sector_size = flashcart_meta["sector_size"][currSect][0]
				else:
					sector_size = flashcart_meta["sector_size"]
			
			for bank in range(first_bank, bank_count):
				if self.MODE == "DMG":
					if bank > first_bank: currAddr = bank_size
					self.set_number(currAddr, self.DEVICE_CMD['SET_START_ADDRESS'])
				
				while (currAddr < endAddr):
					if pos == len(data_import): break
					if self.CANCEL:
						# Reset Flash
						if "reset" in flashcart_meta["commands"]:
							for i in range(0, len(flashcart_meta["commands"]["reset"])):
								self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
						signal.emit({"action":"ABORT", "abortable":False}, 0, 0, 0, 0, 0)
						return
					
					if self.MODE == "DMG":
						# Change Bank
						if (currAddr == bank_size):
							# Reset Flash
							if "reset" in flashcart_meta["commands"]:
								for i in range(0, len(flashcart_meta["commands"]["reset"])):
									self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
							self.SetBankROM(bank)
							time.sleep(0.05)
					
					# Sector Erase (if supported)
					if "sector_erase" in flashcart_meta["commands"]:
						if isinstance(flashcart_meta["sector_size"], list):
							if sectCount == None:
								sectCount = flashcart_meta["sector_size"][currSect][1]
							if sectCount == 0:
								if ((currSect+1) != len(flashcart_meta["sector_size"])):
									currSect += 1
								sectCount = flashcart_meta["sector_size"][currSect][1]
						
						if pos % sector_size == 0:
							signal.emit({"action":"SECTOR_ERASE", "abortable":False}, 1, 0, 0, time.time()-time_start, 0)
							
							# Update sector size if required
							if "sector_erase" in flashcart_meta["commands"]:
								if isinstance(flashcart_meta["sector_size"], list):
									sector_size = flashcart_meta["sector_size"][currSect][0]
							
							for i in range(0, len(flashcart_meta["commands"]["sector_erase"])):
								addr = flashcart_meta["commands"]["sector_erase"][i][0]
								data = flashcart_meta["commands"]["sector_erase"][i][1]
								if addr == "SA": addr = currAddr
								if addr == "SA+1": addr = currAddr + 1
								if addr == "SA+2": addr = currAddr + 2
								if not addr == None:
									self.gbx_flash_write_address_byte(addr, data)
								if flashcart_meta["commands"]["sector_erase_wait_for"][i][0] != None:
									addr = flashcart_meta["commands"]["sector_erase_wait_for"][i][0]
									data = flashcart_meta["commands"]["sector_erase_wait_for"][i][1]
									if addr == "SA": addr = currAddr
									if addr == "SA+1": addr = currAddr + 1
									if addr == "SA+2": addr = currAddr + 2
									time.sleep(0.05)
									timeout = 50
									while True:
										if "wait_read_status_register" in flashcart_meta and flashcart_meta["wait_read_status_register"] == True:
											for j in range(0, len(flashcart_meta["commands"]["read_status_register"])):
												sr_addr = flashcart_meta["commands"]["read_status_register"][j][0]
												sr_data = flashcart_meta["commands"]["read_status_register"][j][1]
												self.gbx_flash_write_address_byte(sr_addr, sr_data)
										wait_for = self.ReadROM(currAddr, 64)
										wait_for = ((wait_for[1] << 8 | wait_for[0]) & flashcart_meta["commands"]["sector_erase_wait_for"][i][2])
										time.sleep(0.1)
										timeout -= 1
										if timeout < 1:
											signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing a flash chip sector timed out. Please make sure the correct flash cartridge type is selected.", "abortable":False}, 0, 0, 0, 0, 0)
											return False
										if wait_for == data: break
							
							# Reset Flash
							if "reset" in flashcart_meta["commands"]:
								for i in range(0, len(flashcart_meta["commands"]["reset"])):
									self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
							
							if self.MODE == "DMG":
								self.set_number(currAddr, self.DEVICE_CMD['SET_START_ADDRESS'])
							elif self.MODE == "AGB":
								self.set_number(currAddr / 2, self.DEVICE_CMD['SET_START_ADDRESS'])
							
							if sectCount is not None:
								sectCount -= 1
					
					# Write data (with special firmware acceleration if available)
					if "buffer_write" in flashcart_meta["commands"]:
						if self.MODE == "DMG":
							# BUNG Doctor GB Card 64M
							if flashcart_meta["commands"]["buffer_write"] == [['SA', 232], ['SA', 'BS'], ['PA', 'PD'], ['SA', 208]]:
								data = data_import[pos:pos+32]
								self.gbx_flash_write_data_bytes("GB_FLASH_WRITE_INTEL_BUFFERED_32BYTE", data)
								self.wait_for_ack()
								currAddr += 32
								pos += 32
							
							else:
								signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Buffer writing for this flash chip is not implemented yet.", "abortable":False}, 0, 0, 0, 0, 0)
								return False
								# TODO
						
						elif self.MODE == "AGB":
							# Flash2Advance 256M
							if flashcart_meta["commands"]["buffer_write"] == [['SA', 232], ['SA+2', 232], ['SA', 'BS'], ['SA+2', 'BS'], ['PA', 'PD'], ['SA', 208], ['SA+2', 208], [None, None], [None, None]]:
								data = data_import[pos:pos+256]
								self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_INTEL_INTERLEAVED_256BYTE", data)
								self.wait_for_ack()
								currAddr += 256
								pos += 256
							
							# 256L30B
							elif flashcart_meta["commands"]["buffer_write"] == [['SA', 96], ['SA', 208], ['SA', 232], ['SA', 'BS'], ['PA', 'PD'], ['SA', 208], ['SA', 255]]:
								if "single_write_7FC0_to_7FFF" in flashcart_meta and int(currAddr % 0x8000) in range(0x7FC0, 0x7FFF):
									for i in range(0, len(flashcart_meta["commands"]["single_write"])):
										addr = flashcart_meta["commands"]["single_write"][i][0]
										data = flashcart_meta["commands"]["single_write"][i][1]
										if addr == "PA": addr = int(currAddr)
										if data == "PD": data = struct.unpack('H', data_import[pos:pos+2])[0]
										self.gbx_flash_write_address_byte(addr, data)
									currAddr += 2
									pos += 2
									
									if int(currAddr % 0x8000) == 0:
										self.set_number(currAddr / 2, self.DEVICE_CMD['SET_START_ADDRESS'])
								
								else:
									data = data_import[pos:pos+64]
									self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_INTEL_64BYTE", data)
									self.wait_for_ack()
									currAddr += 64
									pos += 64
							
							else:
								signal.emit({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Buffer writing for this flash chip is not implemented yet.", "abortable":False}, 0, 0, 0, 0, 0)
								return False
								# TODO
					
					elif "single_write" in flashcart_meta["commands"]:
						if self.MODE == "DMG":
							data = data_import[pos:pos+64]
							if "pulse_reset_after_write" in flashcart_meta:
								self.gbx_flash_write_data_bytes("GB_FLASH_WRITE_64BYTE_PULSE_RESET", data)
							else:
								self.gbx_flash_write_data_bytes("GB_FLASH_WRITE_64BYTE", data)
							self.wait_for_ack()
							currAddr += 64
							pos += 64
						
						elif self.MODE == "AGB":
							# MSP55LV128M
							if flashcart_meta["commands"]["single_write"] == [[1365, 169], [682, 86], [1365, 160], ['PA', 'PD']]:
								data = data_import[pos:pos+256]
								self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_256BYTE_SWAPPED_D0D1", data)
								self.wait_for_ack()
								currAddr += 256
								pos += 256
							
							# E201850 and E201868
							elif flashcart_meta["commands"]["single_write"] == [[0, 112], [0, 16], ['PA', 'PD']] and (([ 0xB0, 0x00, 0xE2, 0x00 ] in flashcart_meta["flash_ids"]) or ([ 0xB0, 0x00, 0xB0, 0x00 ] in flashcart_meta["flash_ids"])):
								data = data_import[pos:pos+64]
								self.gbx_flash_write_data_bytes("GBA_FLASH_WRITE_SHARP_64BYTE", data)
								self.wait_for_ack()
								currAddr += 64
								pos += 64
							
							else: # super slow
								for i in range(0, len(flashcart_meta["commands"]["single_write"])):
									addr = flashcart_meta["commands"]["single_write"][i][0]
									data = flashcart_meta["commands"]["single_write"][i][1]
									if addr == "PA": addr = int(currAddr)
									if data == "PD": data = struct.unpack('H', data_import[pos:pos+2])[0]
									self.gbx_flash_write_address_byte(addr, data)
								
								currAddr += 2
								pos += 2
					
					# Report back to GUI
					if pos % 4096 == 0:
						now = time.time()
						measure_points.append(now - last_emit)
						last_emit = now
						if len(measure_points) >= 16:
							time_delta = statistics.median(measure_points)
							speed = 4096 / time_delta
							time_elapsed = time.time() - time_start
							time_left = (time_elapsed / (pos/len(data_import))) - time_elapsed
						if len(measure_points) >= 512:
							measure_points = measure_points[-512:]

					if not pos == len(data_import): signal.emit(None, pos, len(data_import), speed/1024, time.time()-time_start, time_left)

			# Reset Flash
			if "reset" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["reset"])):
					self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
			
			signal.emit(None, pos, len(data_import), speed/1024, time.time()-time_start, time_left)
