# -*- coding: utf-8 -*-
# ＵＴＦ－８
import serial, os, serial.tools.list_ports
from serial import SerialException
import sys, time, re, glob, math, struct, json, traceback, zlib, copy
from .DataTransfer import *
from .RomFileDMG import *
from .RomFileAGB import *
from .Util import *

class GbxDevice:
	DEVICE_NAME = "GBxCart RW"
	DEVICE_MIN_FW = 19
	DEVICE_MAX_FW = 25
	
	DEVICE_CMD = {
		"CART_MODE":'C',
		"GB_MODE":1,
		"GBA_MODE":2,
		# GB/GBC defines/commands
		"SET_START_ADDRESS":'A',
		"READ_ROM_RAM":'R',
		"READ_ROM_4000H":'Q',
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
		"GBA_READ_ROM_8000H":'Z',
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
		"GB_FLASH_WRITE_UNBUFFERED_256BYTE":'{',
		"GB_FLASH_WRITE_BUFFERED_32BYTE":'Y',
		"GB_FLASH_BANK_1_COMMAND_WRITES":'N',
		"GB_FLASH_WRITE_64BYTE_PULSE_RESET":'J',
		"GB_FLASH_WRITE_INTEL_BUFFERED_32BYTE":'y',
		"GBA_FLASH_CART_WRITE_BYTE":'n',
		"GBA_FLASH_WRITE_64BYTE_SWAPPED_D0D1":'q',
		"GBA_FLASH_WRITE_256BYTE_SWAPPED_D0D1":'t',
		"GBA_FLASH_WRITE_256BYTE":'f',
		"GBA_FLASH_WRITE_BUFFERED_256BYTE":'c',
		"GBA_FLASH_WRITE_BUFFERED_256BYTE_SWAPPED_D0D1":'d',
		"GBA_FLASH_WRITE_INTEL_64BYTE":'l',
		"GBA_FLASH_WRITE_INTEL_256BYTE":';',
		"GBA_FLASH_WRITE_INTEL_64BYTE_WORD":'u',
		"GBA_FLASH_WRITE_INTEL_INTERLEAVED_256BYTE":'v',
		"GBA_FLASH_WRITE_SHARP_64BYTE":'x',
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
		"SET_PINS_AS_INPUTS":':',
		"RESET_AVR":'*',
		"RESET_VALUE":0x7E5E1,
		"XMAS_LEDS":'#',
		"XMAS_VALUE":0x7690FCD,
		"READ_BUFFER":0
	}
	PCB_VERSIONS = {1:'v1.0', 2:'v1.1', 4:'v1.3', 90:'XMAS', 100:'Mini'}
	SUPPORTED_CARTS = {}
	
	FW = []
	MODE = None
	PORT = ''
	DEVICE = None
	WORKER = None
	INFO = { "last_action":None }
	CANCEL = False
	CANCEL_ARGS = {}
	SIGNAL = None
	POS = 0
	FAST_READ = False
	
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
				dev = serial.Serial(ports[i], 1000000, timeout=1)
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
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " requires a firmware update to work with this software. Please try again after updating it to version R" + str(self.DEVICE_MIN_FW) + " or higher.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
					continue
				elif self.FW[0] < self.DEVICE_MAX_FW:
					# TODO: not showing this for now
					#conn_msg.append([1, "The GBxCart RW device on port " + ports[i] + " is running an older firmware version. Please consider updating to version R" + str(self.DEVICE_MAX_FW) + " to make use of the latest features.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
					pass
				elif self.FW[0] > self.DEVICE_MAX_FW:
					conn_msg.append([0, "NOTE: The GBxCart RW device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
				
				if (self.FW[1] != 4):
					conn_msg.append([0, "NOTE: This version of FlashGBX was developed to be used with GBxCart RW v1.3 and v1.3 Pro. Other revisions are untested and may not be fully compatible."])
				
				self.PORT = ports[i]
				
				# Load Flash Cartridge Handlers
				self.UpdateFlashCarts(flashcarts)
				
				# Stop after first found device
				break
			
			except SerialException as e:
				if "Permission" in str(e):
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " couldn’t be accessed. Make sure your user account has permission to use it and it’s not already in use by another application.\n\n" + str(e)])
				else:
					conn_msg.append([3, "A critical error occured while trying to access the GBxCart RW device on port " + ports[i] + ".\n\n" + str(e)])
				continue
		
		#conn_msg.append([0, "NOTE: This is a third party tool for GBxCart RW by insideGadgets. Visit https://www.gbxcart.com/ for more information."])
		return conn_msg
	
	def UpdateFlashCarts(self, flashcarts):
		self.SUPPORTED_CARTS = { 
			"DMG":{ "Generic ROM Cartridge":"RETAIL", "● Auto-Detect Flash Cartridge ●":"AUTODETECT" },
			"AGB":{ "Generic ROM Cartridge":"RETAIL", "● Auto-Detect Flash Cartridge ●":"AUTODETECT" }
		}
		for mode in flashcarts.keys():
			for key in sorted(flashcarts[mode].keys(), key=str.casefold):
				self.SUPPORTED_CARTS[mode][key] = flashcarts[mode][key]
	
	def IsConnected(self):
		if self.DEVICE is None: return False
		if not self.DEVICE.isOpen(): return False
		try:
			while self.DEVICE.in_waiting > 0:
				print("Clearing input buffer... ({:d})".format(self.DEVICE.in_waiting))
				self.DEVICE.reset_input_buffer()
				time.sleep(1)
			self.DEVICE.reset_output_buffer()
			self.LoadFirmwareVersion()
			return True
		except SerialException as e:
			return False
	
	def Close(self):
		if self.IsConnected():
			try:
				self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"]) # set to lower voltage when closing for safety
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
		self.write(self.DEVICE_CMD["READ_FIRMWARE_VERSION"])
		fw = bytearray(self.read(1))[0]
		self.write(self.DEVICE_CMD["READ_PCB_VERSION"])
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
	
	def SetProgress(self, args):
		if self.CANCEL and args["action"] != "ABORT": return
		if args["action"] == "UPDATE_POS": self.POS = args["pos"]
		if self.SIGNAL: self.SIGNAL.emit(args)
		if args["action"] == "FINISHED": self.SIGNAL = None
	
	def wait_for_ack(self):
		buffer = self.read(1)
		lives = 2
		while buffer != b'1':
			print("wait_for_ack(): No valid acknowledgement received (", buffer, "). ", end="")
			lives -= 1
			if lives < 1:
				print("Failed.")
				traceback.print_stack()
				#print("\nwait_for_ack(): Skipping...")
				self.CANCEL = True
				self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"A critical error occured while waiting for confirmation from the device. Please re-connect the device and try again from the beginning."}
				return False
			else:
				print("Retrying...")
				time.sleep(0.05)
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
					dprint("read(): Received {:d} byte(s) instead of the expected {:d} bytes.".format(len(buffer), readlen))
					self.write('0')
					time.sleep(0.5)
					while self.DEVICE.in_waiting > 0:
						self.DEVICE.reset_input_buffer()
						time.sleep(0.5)
					self.DEVICE.reset_output_buffer()
					return False
				
				self.SetProgress({"action":"READ", "bytes_added":len(buffer)})
				
				if length == 1:
					return buffer
				else:
					if last:
						self.write('0')
					if not last:
						self.write('1')
					return buffer[:length]
			
			elif self.FAST_READ and (length == 0x10000 or length == 0x4000):
				mbuffer = bytearray()
				for i in range(0, length, readlen):
					if self.DEVICE.in_waiting > 1000: dprint("Recv buffer used: {:d} bytes".format(self.DEVICE.in_waiting))
					buffer = self.DEVICE.read(readlen)
					if len(buffer) != readlen:
						dprint("read(): Received {:d} byte(s) instead of the expected {:d} bytes during iteration {:d}.".format(len(buffer), readlen, i))
						self.write('0')
						time.sleep(1)
						while self.DEVICE.in_waiting > 0:
							self.DEVICE.reset_input_buffer()
							time.sleep(1)
						self.DEVICE.reset_output_buffer()
						return False

					mbuffer += buffer
					self.SetProgress({"action":"READ", "bytes_added":len(buffer)})
				
				self.write('0')
				return mbuffer

			else: # length > 64
				mbuffer = bytearray()
				for i in range(0, length, 64):
					buffer = self.DEVICE.read(readlen)
					if len(buffer) != readlen:
						dprint("read(): Received {:d} byte(s) instead of the expected {:d} bytes during iteration {:d}.".format(len(buffer), readlen, i))
						self.write('0')
						time.sleep(1)
						while self.DEVICE.in_waiting > 0:
							self.DEVICE.reset_input_buffer()
							time.sleep(1)
						self.DEVICE.reset_output_buffer()
						return False
					
					mbuffer += buffer
					self.SetProgress({"action":"READ", "bytes_added":len(buffer)})
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
		lives = 5
		dprint("ReadROM(offset=0x{:X}, length=0x{:X}, set_address={:s}) fast_read_mode={:s}".format(offset, length, str(set_address), str(self.FAST_READ)))
		while buffer == False:
			if self.MODE == "DMG":
				if self.FAST_READ and length == 0x4000:
					if set_address:
						self.set_number(offset, self.DEVICE_CMD["SET_START_ADDRESS"])
					self.set_mode(self.DEVICE_CMD["READ_ROM_4000H"])
				else:
					if set_address:
						self.set_number(offset, self.DEVICE_CMD["SET_START_ADDRESS"])
					self.set_mode(self.DEVICE_CMD["READ_ROM_RAM"])
				buffer = self.read(length, last=True)
			elif self.MODE == "AGB":
				if self.FAST_READ and length == 0x10000:
					if set_address:
						self.set_number(math.floor(offset / 2), self.DEVICE_CMD["SET_START_ADDRESS"])
					self.set_mode(self.DEVICE_CMD["GBA_READ_ROM_8000H"])
				else:
					if set_address:
						self.set_number(math.floor(offset / 2), self.DEVICE_CMD["SET_START_ADDRESS"])
					self.set_mode(self.DEVICE_CMD["GBA_READ_ROM"])
				buffer = self.read(length, last=True)
			
			'''
			# simulate bad driver
			import random
			if random.randint(0, 20) == 5:
				print("#")
				buffer = False
			'''
			
			if buffer == False:
				if lives == 0:
					self.CANCEL = True
					if (self.MODE == "DMG" and length == 0x4000) or (self.MODE == "AGB" and length == 0x10000):
						self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"An error occured while receiving data from the device. Please disable Fast Read Mode, re-connect the device and try again."}
					else:
						self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"An error occured while receiving data from the device. Please re-connect the device and try again."}
					print(" Giving up.", flush=True)
					return False
				elif lives != 5:
					print("", flush=True)
				print("Failed to receive data at 0x{:X}. Retrying...".format(self.POS), end="", flush=True)
				set_address = True
				lives -= 1
		
		if lives < 5:
			print(" OK!", flush=True)
		
		return buffer
	
	def gbx_flash_write_address_byte(self, address, data):
		if self.MODE == "DMG":
			return self.gb_flash_write_address_byte(address, data)
		elif self.MODE == "AGB":
			return self.gba_flash_write_address_byte(address, data)
	
	def gba_flash_write_address_byte(self, address, data):
		address = int(address / 2)
		address = format(address, 'x')
		buffer = self.DEVICE_CMD["GBA_FLASH_CART_WRITE_BYTE"] + address + '\x00'
		self.write(buffer)
		time.sleep(0.001)
		data = format(data, 'x')
		buffer = self.DEVICE_CMD["GBA_FLASH_CART_WRITE_BYTE"] + data + '\x00'
		self.write(buffer)
		time.sleep(0.001)
		ack = self.wait_for_ack()
		if ack == False:
			self.CANCEL = True
			self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"A critical error occured while trying to write the ROM. Please re-connect the device and try again from the beginning."}
			return False
	
	def gb_flash_write_address_byte(self, address, data):
		address = format(address, 'x')
		buffer = self.DEVICE_CMD["GB_FLASH_WRITE_BYTE"] + address + '\x00'
		self.write(buffer)
		buffer = format(data, 'x') + '\x00'
		self.write(buffer)
		ack = self.wait_for_ack()
		if ack == False:
			self.CANCEL = True
			self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"A critical error occured while trying to write a byte. Please re-connect the device and try again from the beginning."}
			return False
	
	def gbx_flash_write_data_bytes(self, command, data):
		buffer = bytearray(command, "ascii") + bytearray(data)
		self.write(buffer)
	
	def set_bank(self, address, bank):
		address = format(address, 'x')
		buffer = self.DEVICE_CMD["SET_BANK"] + address + '\x00'
		self.write(buffer)
		time.sleep(0.005)
		
		bank = format(bank, 'd')
		buffer = self.DEVICE_CMD["SET_BANK"] + bank + '\x00'
		self.write(buffer)
		time.sleep(0.005)
	
	def set_mode(self, command):
		dprint("set_mode(command={:s})".format(str(command)))
		buffer = format(command, 's')
		self.write(buffer)
		if command in (self.DEVICE_CMD["VOLTAGE_3_3V"], self.DEVICE_CMD["VOLTAGE_5V"]):
			#time.sleep(0.01)
			pass

	def set_number(self, number, command):
		buffer = format(command, 's') + format(int(number), 'x') + '\x00'
		self.write(buffer)
		if command in (self.DEVICE_CMD["SET_START_ADDRESS"]):
			#time.sleep(0.005)
			pass
	
	def EnableRAM(self, mbc=1, enable=True):
		if enable:
			if mbc <= 4: self.set_bank(0x6000, 1)
			self.set_bank(0x0000, 0x0A)
		else:
			self.set_bank(0x0000, 0x00)
			if mbc <= 4: self.set_bank(0x6000, 0)
		time.sleep(0.2)
	
	def SetBankROM(self, bank, mbc=0, bank_count=0):
		dprint("SetBankROM(bank={:d}, mbc={:d}, bank_count={:d})".format(bank, mbc, bank_count))
		if mbc == 0 and bank_count == 0: mbc = 5
		if mbc == 1: # MBC1
			dprint("0x6000=0x00, 0x4000=0x{:X}, 0x2000=0x{:X}".format(bank >> 5, bank & 0x1F))
			self.set_bank(0x6000, 0)
			self.set_bank(0x4000, bank >> 5)
			self.set_bank(0x2000, bank & 0x1F)
		elif mbc == 1.1: # Hudson MBC1
			self.set_bank(0x4000, bank >> 4)
			if (bank < 10):
				dprint("0x4000=0x{:X}, 0x2000=0x{:X}".format(bank >> 4, bank & 0x1F))
				self.set_bank(0x2000, bank & 0x1F)
			else:
				dprint("0x4000=0x{:X}, 0x2000=0x{:X}".format(bank >> 4, 0x10 | (bank & 0x1F)))
				self.set_bank(0x2000, 0x10 | (bank & 0x1F))
		elif (mbc == 0 and bank_count > 256) or mbc == 5: # MBC5
			dprint("0x2100=0x{:X}, 0x3000=0x{:X}".format(bank & 0xFF, ((bank >> 8) & 0xFF)))
			self.set_bank(0x2100, (bank & 0xFF))
			self.set_bank(0x3000, ((bank >> 8) & 0xFF))
		else: # MBC2, MBC3 and others
			dprint("0x2100=0x{:X}".format(bank & 0xFF))
			self.set_bank(0x2100, (bank & 0xFF))
	
	def SetBankRAM(self, bank):
		self.set_bank(0x4000, (bank & 0xFF))
	
	def ReadFlashSaveMakerID(self):
		makers = { 0x1F:"ATMEL", 0xBF:"SST/SANYO", 0xC2:"MACRONIX", 0x32:"PANASONIC", 0x62:"SANYO" }
		self.set_mode(self.DEVICE_CMD["GBA_FLASH_READ_ID"])
		time.sleep(0.02)
		buffer = self.DEVICE.read(2)
		if buffer[0] in makers.keys():
			return makers[buffer[0]]
		else:
			return buffer[0]
	
	def SetMode(self, mode):
		if mode == "DMG":
			self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
			self.MODE = "DMG"
		elif mode == "AGB":
			self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"])
			self.MODE = "AGB"
		self.set_number(0, self.DEVICE_CMD["SET_START_ADDRESS"])
	
	def AutoDetectFlash(self, limitVoltage=False):
		flash_types = []
		flash_type = 0
		flash_id = None
		
		if self.MODE == "DMG":
			if limitVoltage:
				self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"])
			else:
				self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
			
			supported_carts = list(self.SUPPORTED_CARTS['DMG'].values())
			for f in range(2, len(supported_carts)):
				flashcart_meta = supported_carts[f]
				if flash_id is not None:
					if flash_id not in flashcart_meta["flash_ids"]:
						continue
				
				self.set_mode(self.DEVICE_CMD["GB_CART_MODE"])
				if "flash_commands_on_bank_1" in flashcart_meta:
					self.set_mode(self.DEVICE_CMD["GB_FLASH_BANK_1_COMMAND_WRITES"])
				
				if flashcart_meta["write_pin"] == "WR":
					self.set_mode(self.DEVICE_CMD["GB_FLASH_WE_PIN"])
					self.set_mode(self.DEVICE_CMD["WE_AS_WR_PIN"])
				elif flashcart_meta["write_pin"] in ("AUDIO", "VIN"):
					self.set_mode(self.DEVICE_CMD["GB_FLASH_WE_PIN"])
					self.set_mode(self.DEVICE_CMD["WE_AS_AUDIO_PIN"])
				
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
				
				# Read Flash ID / Electronic Signature
				if "read_identifier" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["read_identifier"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["read_identifier"][i][0], flashcart_meta["commands"]["read_identifier"][i][1])
					buffer = self.ReadROM(0, 64)
					flash_id_found = False
					for i in range(0, len(flashcart_meta["flash_ids"])):
						id = list(buffer[0:len(flashcart_meta["flash_ids"][i])])
						if id in flashcart_meta["flash_ids"]:
							flash_id = id
							flash_id_found = True
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
				self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
		
		elif self.MODE == "AGB":
			supported_carts = list(self.SUPPORTED_CARTS['AGB'].values())
			for f in range(2, len(supported_carts)):
				flashcart_meta = supported_carts[f]
				if flash_id is not None:
					if flash_id not in flashcart_meta["flash_ids"]:
						continue
				
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
				
				# Read Flash ID / Electronic Signature
				if "read_identifier" in flashcart_meta["commands"]:
					for i in range(0, len(flashcart_meta["commands"]["read_identifier"])):
						self.gbx_flash_write_address_byte(flashcart_meta["commands"]["read_identifier"][i][0], flashcart_meta["commands"]["read_identifier"][i][1])
					buffer = self.ReadROM(0, 64)
					flash_id_found = False
					for i in range(0, len(flashcart_meta["flash_ids"])):
						id = list(buffer[0:len(flashcart_meta["flash_ids"][i])])
						if id in flashcart_meta["flash_ids"]:
							flash_id = id
							flash_id_found = True
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
	
	def CheckFlashChip(self, limitVoltage=False, cart_type=None):
		flash_id_lines = []
		flash_commands = [
			{ 'read_cfi':[[0x555, 0x98]], 'read_identifier':[[ 0x555, 0xAA ], [ 0x2AA, 0x55 ], [ 0x555, 0x90 ]], 'reset':[[ 0x0, 0xF0 ]] },
			{ 'read_cfi':[[0x5555, 0x98]], 'read_identifier':[[ 0x5555, 0xAA ], [ 0x2AAA, 0x55 ], [ 0x5555, 0x90 ]], 'reset':[[ 0x0, 0xF0 ]] },
			{ 'read_cfi':[[0xAA, 0x98]], 'read_identifier':[[ 0xAAA, 0xAA ], [ 0x555, 0x55 ], [ 0xAAA, 0x90 ]], 'reset':[[ 0x0, 0xF0 ]] },
			{ 'read_cfi':[[0xAAA, 0x98]], 'read_identifier':[[ 0xAAA, 0xAA ], [ 0x555, 0x55 ], [ 0xAAA, 0x90 ]], 'reset':[[ 0x0, 0xF0 ]] },
			{ 'read_cfi':[[0xAAAA, 0x98]], 'read_identifier':[[ 0xAAAA, 0xAA ], [ 0x5555, 0x55 ], [ 0xAAAA, 0x90 ]], 'reset':[[ 0x0, 0xF0 ]] },
			{ 'read_cfi':[[0x4555, 0x98]], 'read_identifier':[[ 0x4555, 0xAA ], [ 0x4AAA, 0x55 ], [ 0x4555, 0x90 ]], 'reset':[[ 0x4000, 0xF0 ]] },
			{ 'read_cfi':[[0x7555, 0x98]], 'read_identifier':[[ 0x7555, 0xAA ], [ 0x7AAA, 0x55 ], [ 0x7555, 0x90 ]], 'reset':[[ 0x7000, 0xF0 ]] },
			{ 'read_cfi':[[0x4AAA, 0x98]], 'read_identifier':[[ 0x4AAA, 0xAA ], [ 0x4555, 0x55 ], [ 0x4AAA, 0x90 ]], 'reset':[[ 0x4000, 0xF0 ]] },
			{ 'read_cfi':[[0x7AAA, 0x98]], 'read_identifier':[[ 0x7AAA, 0xAA ], [ 0x7555, 0x55 ], [ 0x7AAA, 0x90 ]], 'reset':[[ 0x7000, 0xF0 ]] },
			{ 'read_cfi':[[0, 0x98]], 'read_identifier':[[ 0, 0x90 ]], 'reset':[[ 0, 0xFF ]] },
		]
		
		check_buffer = self.ReadROM(0, 0x200)
		d_swap = None
		cfi_info = ""
		rom_string = ""
		for j in range(0, 8):
			rom_string += "{:02X} ".format(check_buffer[j])
		rom_string += "\n"
		cfi = {'raw':b''}
		
		if self.MODE == "DMG":
			if limitVoltage:
				self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"])
			else:
				self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
			rom_string = "[     ROM     ] " + rom_string
			we_pins = [ "WR", "AUDIO" ]
		else:
			rom_string = "[   ROM   ] " + rom_string
			we_pins = [ False ]
		
		for we in we_pins:
			if "method" in cfi: break
			for method in flash_commands:
				if self.MODE == "DMG":
					self.set_mode(self.DEVICE_CMD["GB_FLASH_WE_PIN"])
					self.set_mode(self.DEVICE_CMD["WE_AS_" + we + "_PIN"])
				
				for i in range(0, len(method['reset'])):
					self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
				for i in range(0, len(method['read_cfi'])):
					self.gbx_flash_write_address_byte(method['read_cfi'][i][0], method["read_cfi"][i][1])
				buffer = self.ReadROM(0, 0x400)
				for i in range(0, len(method['reset'])):
					self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
				if buffer == check_buffer: continue
				
				magic = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
				if magic == "QRY": # nothing swapped
					d_swap = ( 0, 0 )
				elif magic == "RQZ": # D0D1 swapped
					d_swap = ( 0, 1 )
				if d_swap is not None:
					for i in range(0, len(buffer)):
						buffer[i] = bitswap(buffer[i], d_swap)
				
				cfi_parsed = ParseCFI(buffer)
				dprint(cfi_parsed)
				if cfi_parsed != False:
					cfi = cfi_parsed
					cfi["raw"] = buffer
					#cfi["sha1"] = hashlib.sha1(buffer).hexdigest()
					cfi["bytes"] = ""
					for i in range(0, 0x400):
						cfi["bytes"] += "{:02X}".format(buffer[i])
					if self.MODE == "DMG": cfi["we"] = we
					cfi["method_id"] = flash_commands.index(method)
					
					if d_swap is not None:
						for k, v in method.items():
							for c in range(0, len(method[k])):
								if isinstance(method[k][c][1], int):
									method[k][c][1] = bitswap(method[k][c][1], d_swap)
					
					# Flash ID
					for i in range(0, len(method['read_identifier'])):
						self.gbx_flash_write_address_byte(method['read_identifier'][i][0], method["read_identifier"][i][1])
					flash_id = self.ReadROM(0, 64)[0:8]
					if self.MODE == "DMG":
						method_string = "[" + we.ljust(5) + "/{:4X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
					else:
						method_string = "[{:6X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
					line_exists = False
					for i in range(0, len(flash_id_lines)):
						if method_string == flash_id_lines[i][0]: line_exists = True
					if not line_exists: flash_id_lines.append([method_string, flash_id])
					for i in range(0, len(method['reset'])):
						self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
					
					cfi["method"] = method
				
				if cart_type is not None: # reset cartridge if method is known
					flashcart_meta = copy.deepcopy(cart_type)
					if "reset" in flashcart_meta["commands"]:
						for i in range(0, len(flashcart_meta["commands"]["reset"])):
							self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
		
		if "method" in cfi:
			s = ""
			if d_swap is not None and d_swap != ( 0, 0 ): s += "Swapped pins: {:s}\n".format(str(d_swap))
			s += "Device size: 0x{:07X} ({:.2f} MB)\n".format(cfi["device_size"], cfi["device_size"] / 1024 / 1024)
			s += "Voltage: {:.1f}–{:.1f} V\n".format(cfi["vdd_min"], cfi["vdd_max"])
			s += "Single write: {:s}\n".format(str(cfi["single_write"]))
			if "buffer_size" in cfi:
				s += "Buffered write: {:s} ({:d} Bytes)\n".format(str(cfi["buffer_write"]), cfi["buffer_size"])
			else:
				s += "Buffered write: {:s}\n".format(str(cfi["buffer_write"]))
			if cfi["chip_erase"]: s += "Chip erase: {:d}–{:d} ms\n".format(cfi["chip_erase_time_avg"], cfi["chip_erase_time_max"])
			if cfi["sector_erase"]: s += "Sector erase: {:d}–{:d} ms\n".format(cfi["sector_erase_time_avg"], cfi["sector_erase_time_max"])
			if cfi["tb_boot_sector"] is not False: s += "Top/Bottom flags: {:s}\n".format(str(cfi["tb_boot_sector"]))
			pos = 0
			oversize = False
			s = s[:-1]
			for i in range(0, cfi['erase_sector_regions']):
				esb = cfi['erase_sector_blocks'][i]
				s += "\nRegion {:d}: 0x{:07X}–0x{:07X} @ 0x{:X} Bytes × {:d}".format(i+1, pos, pos+esb[2]-1, esb[0], esb[1])
				if oversize: s += " (alt)"
				pos += esb[2]
				if pos >= cfi['device_size']:
					pos = 0
					oversize = True
			#s += "\nSHA-1: {:s}".format(cfi["sha1"])
			cfi_info = s
		
		if cfi['raw'] == b'':
			for we in we_pins:
				for method in flash_commands:
					for i in range(0, len(method['reset'])):
						self.gbx_flash_write_address_byte(method['reset'][i][0], method["reset"][i][1])
					for i in range(0, len(method['read_identifier'])):
						self.gbx_flash_write_address_byte(method['read_identifier'][i][0], method["read_identifier"][i][1])
					flash_id = self.ReadROM(0, 64)[0:8]
					for i in range(0, len(method['reset'])):
						self.gbx_flash_write_address_byte(method['reset'][i][0], method["reset"][i][1])
					
					if flash_id != check_buffer[0:8]:
						if self.MODE == "DMG":
							method_string = "[" + we.ljust(5) + "/{:4X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
						else:
							method_string = "[{:6X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
						line_exists = False
						for i in range(0, len(flash_id_lines)):
							if method_string == flash_id_lines[i][0]: line_exists = True
						if not line_exists: flash_id_lines.append([method_string, flash_id])
						for i in range(0, len(method['reset'])):
							self.gbx_flash_write_address_byte(method['reset'][i][0], method['reset'][i][1])
			
			if self.MODE == "DMG":
				self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
		
		flash_id = ""
		for i in range(0, len(flash_id_lines)):
			flash_id += flash_id_lines[i][0] + " "
			for j in range(0, 8):
				flash_id += "{:02X} ".format(flash_id_lines[i][1][j])
			flash_id += "\n"
		
		flash_id = rom_string + flash_id
		
		return (flash_id, cfi_info, cfi)
	
	def CheckROMStable(self):
		self.ReadROM(0, 64)
		buffer = self.ReadROM(0, 0x180)
		time.sleep(0.1)
		if buffer != self.ReadROM(0, 0x180):
			return False
		return True
	
	def ReadInfo(self):
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		data = {}
		self.POS = 0
		if self.MODE == "DMG":
			self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
		
		header = self.ReadROM(0, 0x180)
		
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
		
		self.set_mode(self.DEVICE_CMD["SET_PINS_AS_INPUTS"])
		return data
	
	def BackupROM(self, fncSetProgress=None, path="ROM.gb", mbc=0x00, rom_banks=512, agb_rom_size=0, start_addr=0, fast_read_mode=False):
		config = { 'mode':1, 'port':self, 'path':path, 'mbc':mbc, 'rom_banks':rom_banks, 'agb_rom_size':agb_rom_size, 'start_addr':start_addr, 'fast_read_mode':fast_read_mode }
		if self.WORKER is None:
			self.WORKER = DataTransfer(config)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(config)
		self.WORKER.start()
	
	def BackupRAM(self, fncSetProgress=None, path="ROM.sav", mbc=0x00, save_type=0):
		config = { 'mode':2, 'port':self, 'path':path, 'mbc':mbc, 'save_type':save_type }
		if self.WORKER is None:
			self.WORKER = DataTransfer(config)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(config)
		self.WORKER.start()
	
	def RestoreRAM(self, fncSetProgress=None, path="", mbc=0x00, save_type=0, erase=False):
		config = { 'mode':3, 'port':self, 'path':path, 'mbc':mbc, 'save_type':save_type, 'erase':erase }
		if self.WORKER is None:
			self.WORKER = DataTransfer(config)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(config)
		self.WORKER.start()
	
	def FlashROM(self, fncSetProgress=None, path="", cart_type=0, override_voltage=False, buffer=bytearray(), start_addr=0, prefer_sector_erase=False, reverse_sectors=False, fast_read_mode=False, verify_flash=False):
		config = { 'mode':4, 'port':self, 'path':path, 'cart_type':cart_type, 'override_voltage':override_voltage, 'start_addr':start_addr, 'buffer':buffer, 'prefer_sector_erase':prefer_sector_erase, 'reverse_sectors':reverse_sectors, 'fast_read_mode':fast_read_mode, 'verify_flash':verify_flash }
		if self.WORKER is None:
			self.WORKER = DataTransfer(config)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(config)
		self.WORKER.start()
	
	def _TransferData(self, args, signal): # called by thread
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		self.SIGNAL = signal
		mode = args["mode"]
		if self.INFO == None: self.ReadInfo()
		path = args["path"]
		self.INFO["last_path"] = path
		self.INFO["last_action"] = mode
		time_start = time.time()
		bank_size = 0x4000
		self.CANCEL_ARGS = {}
		self.POS = 0
		
		# main work
		self.FAST_READ = False
		if mode == 1: # Backup ROM
			fast_read_mode = args["fast_read_mode"]
			buffer_len = 0x1000
			if self.MODE == "DMG":
				mbc = args["mbc"]
				bank_count = args["rom_banks"]
				if fast_read_mode:
					buffer_len = 0x4000
					self.FAST_READ = True
				rom_size = bank_count * bank_size
			elif self.MODE == "AGB":
				rom_size = args["agb_rom_size"]
				if fast_read_mode:
					buffer_len = 0x10000
					self.FAST_READ = True
				if rom_size == 0:
					rom_size = 32 * 1024 * 1024
			
			data_dump = bytearray()
			
			startAddr = 0
			currAddr = 0
			recvBytes = 0
			
			try:
				file = open(path, "wb")
			except PermissionError as e:
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"FlashGBX doesn’t have permission to access this file for writing:\n" + path, "abortable":False})
				return False
			
			if self.MODE == "DMG":
				endAddr = bank_size
			else:
				endAddr = rom_size
				bank_count = 1
			
			# Read a bit before actually dumping (fixes some bootlegs)
			self.ReadROM(0, 64)
			
			self.SetProgress({"action":"INITIALIZE", "method":"ROM_READ", "size":rom_size})
			
			for bank in range(0, bank_count):
				if self.MODE == "DMG":
					if bank > 0:
						startAddr = bank_size
						endAddr = startAddr + bank_size
					self.SetBankROM(bank, mbc)
				
				for currAddr in range(startAddr, endAddr, buffer_len):
					if self.CANCEL:
						cancel_args = {"action":"ABORT", "abortable":False}
						cancel_args.update(self.CANCEL_ARGS)
						self.CANCEL_ARGS = {}
						self.SetProgress(cancel_args)
						try:
							file.close()
						except:
							pass
						return
					
					if currAddr == startAddr:
						buffer = self.ReadROM(currAddr, buffer_len, True)
					else:
						buffer = self.ReadROM(currAddr, buffer_len, False)
					
					if buffer == False:
						self.CANCEL = True
						continue
					
					data_dump.extend(buffer)
					file.write(buffer)
					recvBytes += buffer_len
					self.SetProgress({"action":"UPDATE_POS", "pos":recvBytes})
			
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
			self.SetProgress({"action":"FINISHED"})
		
		#########################################
		
		elif mode == 2 or mode == 3: # Backup or Restore RAM
			data_dump = bytearray()
			data_import = bytearray()
			self.ReadROM(0, 64) # fix
			
			startAddr = 0
			if self.MODE == "DMG":
				bank_size = 0x2000
				mbc = args["mbc"]
				save_size = args["save_type"]
				bank_count = int(max(save_size, bank_size) / bank_size)
				self.EnableRAM(mbc=mbc, enable=True)
				startAddr = 0xA000
				if mode == 2: # Backup
					transfer_size = 512
				else:
					transfer_size = 64
			
			elif self.MODE == "AGB":
				bank_size = 0x10000
				save_type = args["save_type"]
				bank_count = 1
				eeprom_size = 0
				transfer_size = 64
				
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
				elif save_type == 5: # SRAM 128 KB
					save_size = 128 * 1024
					read_command = 'GBA_READ_SRAM'
					write_command = 'GBA_WRITE_SRAM'
					bank_count = 2
				elif save_type == 6: # FLASH 64 KB
					save_size = 64 * 1024
					read_command = 'GBA_READ_SRAM'
				elif save_type == 7: # FLASH 128 KB
					save_size = 128 * 1024
					read_command = 'GBA_READ_SRAM'
					bank_count = 2
				else:
					return
				
				# Get Save Flash Manufacturer
				maker_id = None
				if save_type == 6 or save_type == 7:
					maker_id = self.ReadFlashSaveMakerID()
					if maker_id == "ATMEL":
						print("NOTE: For save data, this cartridge uses an ATMEL chip which is untested.")
						transfer_size = 128
					elif maker_id == "SANYO":
						if int(self.FW[0]) < 24:
							self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"A firmware update is required to correctly handle the save data chip of this cartridge. Please update the firmware of your GBxCart RW device to version R24 or higher.", "abortable":False})
							return False
			
			# Prepare some stuff
			if mode == 2: # Backup
				try:
					file = open(path, "wb")
				except PermissionError as e:
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"FlashGBX doesn’t have permission to access this file for writing:\n" + path, "abortable":False})
					return False
				self.SetProgress({"action":"INITIALIZE", "method":"SAVE_READ", "size":save_size})
			
			elif mode == 3: # Restore
				if args["erase"]: # Erase
					data_import = save_size * b'\xFF'
					self.INFO["save_erase"] = True
				else:
					with open(path, "rb") as file: data_import = file.read()
				
				if save_size > len(data_import):
					data_import += b'\xFF' * (save_size - len(data_import))
				
				self.SetProgress({"action":"INITIALIZE", "method":"SAVE_WRITE", "size":save_size})
			
			currAddr = 0
			pos = 0
			
			for bank in range(0, bank_count):
				if self.MODE == "DMG":
					endAddr = startAddr + bank_size
					if endAddr > (startAddr + save_size): endAddr = startAddr + save_size
					self.SetBankRAM(bank)
				
				elif self.MODE == "AGB":
					endAddr = startAddr + min(save_size, bank_size)
					if endAddr > (startAddr + save_size): endAddr = startAddr + save_size
					if save_type == 1 or save_type == 2: # EEPROM
						self.set_number(eeprom_size, self.DEVICE_CMD["GBA_SET_EEPROM_SIZE"])
					elif (save_type == 5) and bank > 0: # 1M SRAM
						self.gbx_flash_write_address_byte(0x1000000, bank)
					elif (save_type == 6 or save_type == 7) and bank > 0: # FLASH
						self.set_number(bank, self.DEVICE_CMD["GBA_FLASH_SET_BANK"])
				
				self.set_number(startAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
				
				buffer_len = transfer_size
				sector = 0
				for currAddr in range(startAddr, endAddr, buffer_len):
					if self.CANCEL:
						if self.MODE == "DMG":
							self.EnableRAM(mbc=mbc, enable=False)
						elif self.MODE == "AGB":
							if bank > 0: self.set_number(0, self.DEVICE_CMD["GBA_FLASH_SET_BANK"])
							self.set_mode(self.DEVICE_CMD["READ_ROM_RAM"])
						self.ReadInfo()
						cancel_args = {"action":"ABORT", "abortable":False}
						cancel_args.update(self.CANCEL_ARGS)
						self.CANCEL_ARGS = {}
						self.SetProgress(cancel_args)
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
								self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Backup failed, please try again.", "abortable":False})
								return False
						
						data_dump.extend(buffer)
						file.write(buffer)
					
					elif mode == 3: # Restore
						data = data_import[pos:pos+buffer_len]
						if self.MODE == "DMG":
							
							self.gbx_flash_write_data_bytes(self.DEVICE_CMD["WRITE_RAM"], data)
						
						elif self.MODE == "AGB":
							if save_type == 6 or save_type == 7: # FLASH
								if maker_id == "ATMEL":
									self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_ATMEL"], data)
								else:
									if (currAddr % 4096 == 0):
										self.set_number(sector, self.DEVICE_CMD["GBA_FLASH_4K_SECTOR_ERASE"])
										self.wait_for_ack()
										sector += 1
										lives = 50
										while True: # wait for 0xFF (= erase done)
											self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
											self.set_mode(self.DEVICE_CMD[read_command])
											buffer = self.read(buffer_len, last=True)
											if buffer[0] == 0xFF: break
											time.sleep(0.01)
											lives -= 1
											if lives == 0:
												self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Writing the flash save data failed. Please make sure you selected the correct save type.", "abortable":False})
												return False
										self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
									
									self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_BYTE"], data)
							
							else: # EEPROM / SRAM
								self.gbx_flash_write_data_bytes(write_command, data)
						
						self.SetProgress({"action":"WRITE", "bytes_added":len(data)})
						self.wait_for_ack()
					
					pos += buffer_len
					self.SetProgress({"action":"UPDATE_POS", "pos":pos})
					
					#if not pos == save_size: signal.emit(None, pos, save_size, speed/1024, time.time()-time_start, 0)
					self.INFO["transferred"] = pos
			
			if self.MODE == "DMG":
				self.EnableRAM(mbc=mbc, enable=False)
			elif self.MODE == "AGB":
				if bank > 0:
					if (save_type == 5) and bank > 0: # 1M SRAM
						self.gbx_flash_write_address_byte(0x1000000, 0)
					elif (save_type == 6 or save_type == 7) and bank > 0: # FLASH
						self.set_number(0, self.DEVICE_CMD["GBA_FLASH_SET_BANK"])
			
			if mode == 2: file.close()
			
			self.INFO["last_action"] = mode
			self.SetProgress({"action":"FINISHED"})
		
		#########################################
		
		elif mode == 4: # Flash ROM
			if self.MODE == "DMG":
				supported_carts = list(self.SUPPORTED_CARTS['DMG'].values())
				i_size = 0x4000
			elif self.MODE == "AGB":
				supported_carts = list(self.SUPPORTED_CARTS['AGB'].values())
				i_size = 0x10000
			
			if not isinstance(args["cart_type"], dict):
				cart_type = "RETAIL"
				for i in range(0, len(supported_carts)):
					if i == args["cart_type"]: cart_type = supported_carts[i]
				if cart_type == "RETAIL" or cart_type == "AUTODETECT": return False # Generic ROM Cartridge is not flashable
			else:
				cart_type = args["cart_type"]
			
			if path != "":
				with open(path, "rb") as file: data_import = file.read()
			else:
				data_import = args["buffer"]
			
			# pad to next possible size
			i = i_size
			while len(data_import) > i: i += i_size
			i = i - len(data_import)
			if i > 0: data_import += bytearray([0xFF] * i)
			
			self._FlashROM(buffer=data_import, cart_type=cart_type, voltage=args["override_voltage"], start_addr=args["start_addr"], signal=signal, prefer_sector_erase=args["prefer_sector_erase"], reverse_sectors=args["reverse_sectors"], fast_read_mode=args["fast_read_mode"], verify_flash=args["verify_flash"])
		
		# Reset pins to avoid save data loss
		self.set_mode(self.DEVICE_CMD["SET_PINS_AS_INPUTS"])
	
	#######################################################################################################################################
	
	def _FlashROM(self, buffer=bytearray(), start_addr=0, cart_type=None, voltage=3.3, signal=None, prefer_sector_erase=False, reverse_sectors=False, fast_read_mode=False, verify_flash=False):
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		if self.INFO == None: self.ReadInfo()
		self.INFO["last_action"] = 4
		bank_size = 0x4000
		mbc = 0
		time_start = time.time()
		
		data_import = copy.copy(buffer)
		if start_addr > 0:
			data_import = (b'\xFF' * start_addr) + data_import
		
		if self.MODE == "DMG":
			supported_carts = list(self.SUPPORTED_CARTS['DMG'].values())
		elif self.MODE == "AGB":
			supported_carts = list(self.SUPPORTED_CARTS['AGB'].values())

		if cart_type == "RETAIL" or cart_type == "AUTODETECT": return False # Generic ROM Cartridge is not flashable
		flashcart_meta = copy.deepcopy(cart_type)
		
		# Reverse sectors if requested
		if reverse_sectors: flashcart_meta['sector_size'].reverse()
		
		# Firmware check R20+
		if (int(self.FW[0]) < 20) and self.MODE == "AGB" and "buffer_write" in flashcart_meta["commands"] and flashcart_meta["commands"]["buffer_write"] == [[0xAAA, 0xAA], [0x555, 0x55], ['SA', 0x25], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0x29]]:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"A firmware update is required to write to this cartridge. Please update the firmware of your GBxCart RW device to version R20 or higher.", "abortable":False})
			return False
		# Firmware check R20+
		# Firmware check R23+
		if (int(self.FW[0]) < 23) and self.MODE == "AGB" and "buffer_write" in flashcart_meta["commands"] and flashcart_meta["commands"]["buffer_write"] == [[0xAAA, 0xA9], [0x555, 0x56], ['SA', 0x26], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0x2A]]:
			print("NOTE: Update your GBxCart RW firmware to version R23 or higher for a better transfer rate with this cartridge.")
			del flashcart_meta["commands"]["buffer_write"]
		# Firmware check R23+
		# Firmware check R25+
		if (int(self.FW[0]) >= 25) and self.MODE == "AGB" and "single_write" in flashcart_meta["commands"] and flashcart_meta["commands"]["single_write"] == [[0, 0x70], [0, 0x10], ['PA', 'PD']] and (([ 0xB0, 0x00, 0xE2, 0x00 ] in flashcart_meta["flash_ids"]) or ([ 0xB0, 0x00, 0xB0, 0x00 ] in flashcart_meta["flash_ids"])):
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Support for this flash cartridge type has been temporarily dropped with GBxCart RW firmware version R25. You can either downgrade to firmware version R24, or look for a newer firmware and FlashGBX version.", "abortable":False})
			return False
		# Firmware check R25+
		
		# Set Voltage
		if voltage == 3.3:
			self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"])
		elif voltage == 5:
			self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
		elif flashcart_meta["voltage"] == 3.3:
			self.set_mode(self.DEVICE_CMD["VOLTAGE_3_3V"])
		elif flashcart_meta["voltage"] == 5:
			self.set_mode(self.DEVICE_CMD["VOLTAGE_5V"])
		
		if "mbc" in flashcart_meta:
			mbc = flashcart_meta['mbc']
			dprint("Set MBC to {:d}".format(mbc))
		
		if self.MODE == "DMG":
			self.set_mode(self.DEVICE_CMD["GB_CART_MODE"])
			if "flash_commands_on_bank_1" in flashcart_meta and flashcart_meta["flash_commands_on_bank_1"]:
				self.set_mode(self.DEVICE_CMD["GB_FLASH_BANK_1_COMMAND_WRITES"])
				dprint("Setting GB_FLASH_BANK_1_COMMAND_WRITES...")
			
			self.set_mode(self.DEVICE_CMD["GB_FLASH_WE_PIN"])
			if flashcart_meta["write_pin"] == "WR":
				self.set_mode(self.DEVICE_CMD["WE_AS_WR_PIN"])
				dprint("Setting WE_AS_WR_PIN...")
			elif flashcart_meta["write_pin"] in ("AUDIO", "VIN"):
				self.set_mode(self.DEVICE_CMD["WE_AS_AUDIO_PIN"])
				dprint("Setting WE_AS_AUDIO_PIN...")

			if "single_write" in flashcart_meta["commands"] and len(flashcart_meta["commands"]["single_write"]) == 4:
				# Submit flash program commands to firmware
				dprint("Setting GB_FLASH_PROGRAM_METHOD...")
				self.set_mode(self.DEVICE_CMD["GB_FLASH_PROGRAM_METHOD"])
				for i in range(0, 3):
					dprint("single_write_command(",i,"):", hex(flashcart_meta["commands"]["single_write"][i][0]), "=", hex(flashcart_meta["commands"]["single_write"][i][1]))
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
		
		# Chip Erase
		chip_erase = False
		if "chip_erase" in flashcart_meta["commands"]:
			if "sector_erase" in flashcart_meta["commands"] and prefer_sector_erase is True:
				chip_erase = False
			elif "chip_erase_treshold" in flashcart_meta:
				if len(data_import) > flashcart_meta["chip_erase_treshold"] or "sector_erase" not in flashcart_meta["commands"]:
					chip_erase = True
			else:
				chip_erase = True
				self.SetProgress({"action":"ERASE", "time_start":time_start, "abortable":False})
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
							self.SetProgress({"action":"ERASE", "time_start":time_start, "abortable":False})
							if "wait_read_status_register" in flashcart_meta and flashcart_meta["wait_read_status_register"]:
								for j in range(0, len(flashcart_meta["commands"]["read_status_register"])):
									sr_addr = flashcart_meta["commands"]["read_status_register"][j][0]
									sr_data = flashcart_meta["commands"]["read_status_register"][j][1]
									self.gbx_flash_write_address_byte(sr_addr, sr_data)
							wait_for = self.ReadROM(addr, 64)
							wait_for = ((wait_for[1] << 8 | wait_for[0]) & flashcart_meta["commands"]["chip_erase_wait_for"][i][2])
							if wait_for == data: break
							time.sleep(0.5)
							timeout -= 0.5
							if timeout <= 0:
								self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing the flash chip timed out. Please make sure that the cartridge contacts are clean, and that the selected cartridge type and settings are correct.", "abortable":False})
								return False
			
			# Reset Flash
			if "reset" in flashcart_meta["commands"]:
				for i in range(0, len(flashcart_meta["commands"]["reset"])):
					self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
			
			dprint("Chip erase took {:d} seconds".format(math.ceil(time.time() - time_start)))
		
		self.set_number(0, self.DEVICE_CMD["SET_START_ADDRESS"])
		
		# Write Flash
		pos = 0
		currAddr = 0
		skipping = False # skips if block is full of 0xFF
		if self.MODE == "DMG":
			if "first_bank" in flashcart_meta: first_bank = flashcart_meta["first_bank"]
			if "start_addr" in flashcart_meta: currAddr = flashcart_meta["start_addr"]
			endAddr = 0x7FFF
			bank_count = math.ceil(len(data_import) / bank_size)
			if start_addr == 0: self.SetBankROM(0, mbc=mbc, bank_count=bank_count)
		elif self.MODE == "AGB":
			currAddr = 0
			endAddr = len(data_import)
			first_bank = 0
			bank_count = 1
		
		self.SetProgress({"action":"INITIALIZE", "time_start":time_start, "method":"ROM_WRITE", "size":len(data_import)})
		
		currSect = 0
		
		# Fast Forward
		if start_addr > 0:
			first_bank = math.floor(start_addr / bank_size)
			self.SetBankROM(first_bank, mbc=mbc, bank_count=bank_count)
			offset = start_addr % bank_size
			currAddr = bank_size + offset
			if "sector_erase" in flashcart_meta["commands"]:
				while pos < start_addr:
					dprint("* currSect:",currSect)
					dprint("sector_size:", hex(flashcart_meta["sector_size"][currSect][0]))
					dprint("start_addr:",hex(start_addr),", pos:",hex(pos))
					pos += flashcart_meta["sector_size"][currSect][0]
					flashcart_meta["sector_size"][currSect][1] -= 1
					if flashcart_meta["sector_size"][currSect][1] == 0:
						currSect += 1
				dprint("currSect:", currSect, end=", ")
				dprint(flashcart_meta["sector_size"])
				dprint(flashcart_meta["sector_size"][currSect][1])
		
		sector_count = None
		if "sector_erase" in flashcart_meta["commands"]:
			if isinstance(flashcart_meta["sector_size"], list):
				sector_size = flashcart_meta["sector_size"][currSect][0]
			else:
				sector_size = flashcart_meta["sector_size"]
			dprint("sector_size:", sector_size)
		
		dprint("start_addr:", hex(start_addr))
		dprint("first_bank:", first_bank, ", bank_count:", bank_count)
		dprint("currAddr:", hex(currAddr), ", endAddr:", hex(endAddr))
		dprint("pos:", hex(pos))
		
		ack = True
		if first_bank == bank_count: first_bank -= 1 # dirty hack so that <32 KB works too
		for bank in range(first_bank, bank_count):
			dprint("BANK {:d}".format(bank))
			if self.MODE == "DMG":
				if bank > first_bank: currAddr = bank_size
				self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
			
			while (currAddr < endAddr):
				if pos >= len(data_import): break
				if self.CANCEL:
					# Reset Flash
					if "reset" in flashcart_meta["commands"]:
						for i in range(0, len(flashcart_meta["commands"]["reset"])):
							self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.SetProgress(cancel_args)
					return
				
				if self.MODE == "DMG":
					# Change Bank
					if (currAddr == bank_size):
						# Reset Flash
						if "reset" in flashcart_meta["commands"]:
							for i in range(0, len(flashcart_meta["commands"]["reset"])):
								self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
						self.SetBankROM(bank, mbc=mbc, bank_count=bank_count)
						time.sleep(0.05)
				
				# Sector Erase (if supported)
				if "sector_erase" in flashcart_meta["commands"] and not chip_erase:
					if isinstance(flashcart_meta["sector_size"], list):
						if sector_count == None:
							sector_count = flashcart_meta["sector_size"][currSect][1]
						if sector_count == 0:
							if ((currSect+1) != len(flashcart_meta["sector_size"])):
								currSect += 1
							sector_count = flashcart_meta["sector_size"][currSect][1]
					
					if pos % sector_size == 0:
						self.SetProgress({"action":"SECTOR_ERASE", "time_start":time.time(), "abortable":True})
						
						# Update sector size if changed
						if "sector_erase" in flashcart_meta["commands"]:
							if isinstance(flashcart_meta["sector_size"], list):
								sector_size = flashcart_meta["sector_size"][currSect][0]
						dprint("\n* sector_count:", sector_count, "sector_size:", hex(sector_size), "pos:",hex(pos))
						
						for i in range(0, len(flashcart_meta["commands"]["sector_erase"])):
							addr = flashcart_meta["commands"]["sector_erase"][i][0]
							data = flashcart_meta["commands"]["sector_erase"][i][1]
							if addr == "SA": addr = currAddr
							if addr == "SA+1": addr = currAddr + 1
							if addr == "SA+2": addr = currAddr + 2
							if addr == "SA+0x4000": addr = currAddr + 0x4000
							if addr == "SA+0x7000": addr = currAddr + 0x7000
							if not addr == None:
								self.gbx_flash_write_address_byte(addr, data)
								dprint("SE {:08X}={:X}".format(addr, data))
							if flashcart_meta["commands"]["sector_erase_wait_for"][i][0] != None:
								addr = flashcart_meta["commands"]["sector_erase_wait_for"][i][0]
								data = flashcart_meta["commands"]["sector_erase_wait_for"][i][1]
								if addr == "SA": addr = currAddr
								if addr == "SA+1": addr = currAddr + 1
								if addr == "SA+2": addr = currAddr + 2
								if addr == "SA+0x4000": addr = currAddr + 0x4000
								if addr == "SA+0x7000": addr = currAddr + 0x7000
								time.sleep(0.05)
								timeout = 50
								while True:
									if "wait_read_status_register" in flashcart_meta and flashcart_meta["wait_read_status_register"] == True:
										for j in range(0, len(flashcart_meta["commands"]["read_status_register"])):
											sr_addr = flashcart_meta["commands"]["read_status_register"][j][0]
											sr_data = flashcart_meta["commands"]["read_status_register"][j][1]
											self.gbx_flash_write_address_byte(sr_addr, sr_data)
											dprint("SE_SR {:08X}={:X}".format(addr, data))
									wait_for = self.ReadROM(currAddr, 64)
									wait_for = ((wait_for[1] << 8 | wait_for[0]) & flashcart_meta["commands"]["sector_erase_wait_for"][i][2])
									dprint("SE_SR {:X}=={:X}?".format(wait_for, data))
									time.sleep(0.1)
									timeout -= 1
									if timeout < 1:
										self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Erasing a flash chip sector timed out. Please make sure that the cartridge contacts are clean, and that the selected cartridge type and settings are correct.", "abortable":False})
										return False
									if wait_for == data: break
									self.SetProgress({"action":"SECTOR_ERASE", "time_start":time.time(), "abortable":True})
						
						# Reset Flash
						if "reset" in flashcart_meta["commands"]:
							for i in range(0, len(flashcart_meta["commands"]["reset"])):
								self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
						
						if self.MODE == "DMG":
							self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
						elif self.MODE == "AGB":
							self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
						
						if sector_count is not None:
							sector_count -= 1
						
						#self.SetProgress({"action":"UPDATE_SPEED", "abortable":False})
				
				# Write data (with special firmware acceleration if available)
				if "buffer_write" in flashcart_meta["commands"]:
					if self.MODE == "DMG":
						# BUNG Doctor GB Card 64M
						if flashcart_meta["commands"]["buffer_write"] == [['SA', 0xE8], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0xD0]]:
							data = data_import[pos:pos+32]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GB_FLASH_WRITE_INTEL_BUFFERED_32BYTE"], data)
								ack = self.wait_for_ack()
							currAddr += 32
							pos += 32
						
						else: # TODO
							self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Buffer writing for this flash chip is not implemented yet.", "abortable":False})
							return False
					
					elif self.MODE == "AGB":
						# Flash2Advance 256M
						if flashcart_meta["commands"]["buffer_write"] == [['SA', 0xE8], ['SA+2', 0xE8], ['SA', 'BS'], ['SA+2', 'BS'], ['PA', 'PD'], ['SA', 0xD0], ['SA+2', 0xD0], [None, None], [None, None]]:
							data = data_import[pos:pos+256]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_INTEL_INTERLEAVED_256BYTE"], data)
								ack = self.wait_for_ack()
							currAddr += 256
							pos += 256
						
						# 256L30B etc.
						elif flashcart_meta["commands"]["buffer_write"] == [['SA', 0x60], ['SA', 0xD0], ['SA', 0xE8], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0xD0], ['SA', 0xFF]]:
							if "single_write_7FC0_to_7FFF" in flashcart_meta and flashcart_meta["single_write_7FC0_to_7FFF"] and int(currAddr % 0x8000) in range(0x7FC0, 0x7FFF):
								for i in range(0, len(flashcart_meta["commands"]["single_write"])):
									addr = flashcart_meta["commands"]["single_write"][i][0]
									data = flashcart_meta["commands"]["single_write"][i][1]
									if addr == "PA": addr = int(currAddr)
									if data == "PD": data = struct.unpack('H', data_import[pos:pos+2])[0]
									self.gbx_flash_write_address_byte(addr, data)
								currAddr += 2
								pos += 2
								data = data_import[pos:pos+2]
								
								if int(currAddr % 0x8000) == 0:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
							
							# R24+
							elif (int(self.FW[0]) >= 24) and "single_write_7FC0_to_7FFF" not in flashcart_meta:
								data = data_import[pos:pos+256]
								if data == bytearray([0xFF] * len(data)):
									skipping = True
								else:
									if skipping:
										self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
										skipping = False
									self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_INTEL_256BYTE"], data)
									ack = self.wait_for_ack()
								
								currAddr += 256
								pos += 256
							
							else:
								data = data_import[pos:pos+64]
								if data == bytearray([0xFF] * len(data)):
									skipping = True
								else:
									if skipping:
										self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
										skipping = False
									self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_INTEL_64BYTE"], data)
									ack = self.wait_for_ack()
								
								currAddr += 64
								pos += 64
						
						# MSP55LV128M etc.
						elif flashcart_meta["commands"]["buffer_write"] == [[0xAAA, 0xA9], [0x555, 0x56], ['SA', 0x26], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0x2A]]:
							data = data_import[pos:pos+256]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_BUFFERED_256BYTE_SWAPPED_D0D1"], data)
								ack = self.wait_for_ack()
							currAddr += 256
							pos += 256
						
						# insideGadgets flash carts etc.
						elif flashcart_meta["commands"]["buffer_write"] == [[0xAAA, 0xAA], [0x555, 0x55], ['SA', 0x25], ['SA', 'BS'], ['PA', 'PD'], ['SA', 0x29]]:
							if "single_write_first_256_bytes" in flashcart_meta and flashcart_meta["single_write_first_256_bytes"] and currAddr < 256:
								for i in range(0, len(flashcart_meta["commands"]["single_write"])):
									addr = flashcart_meta["commands"]["single_write"][i][0]
									data = flashcart_meta["commands"]["single_write"][i][1]
									if addr == "PA": addr = int(currAddr)
									if data == "PD": data = struct.unpack('H', data_import[pos:pos+2])[0]
									self.gbx_flash_write_address_byte(addr, data)
								currAddr += 2
								pos += 2
								data = data_import[pos:pos+2]
								
								if currAddr == 256:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
							
							else:
								data = data_import[pos:pos+256]
								if data == bytearray([0xFF] * len(data)):
									skipping = True
								else:
									if skipping:
										self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
										skipping = False
									self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_BUFFERED_256BYTE"], data)
									ack = self.wait_for_ack()
								currAddr += 256
								pos += 256
						
						else: # TODO
							self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Buffer writing for this flash chip is not implemented yet.\n\n{:s}".format(str(flashcart_meta["commands"]["buffer_write"])), "abortable":False})
							return False
				
				elif "single_write" in flashcart_meta["commands"]:
					if self.MODE == "DMG":
						# R24+
						if (int(self.FW[0]) < 24) or ("pulse_reset_after_write" in flashcart_meta and flashcart_meta["pulse_reset_after_write"]):
							data = data_import[pos:pos+64]
						else:
							data = data_import[pos:pos+256]
						
						if data == bytearray([0xFF] * len(data)):
							skipping = True
						else:
							if skipping:
								self.set_number(currAddr, self.DEVICE_CMD["SET_START_ADDRESS"])
								skipping = False
							if "pulse_reset_after_write" in flashcart_meta and flashcart_meta["pulse_reset_after_write"]:
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GB_FLASH_WRITE_64BYTE_PULSE_RESET"], data)
							elif len(data) == 64:
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GB_FLASH_WRITE_64BYTE"], data)
							elif len(data) == 256:
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GB_FLASH_WRITE_UNBUFFERED_256BYTE"], data)
							ack = self.wait_for_ack()
							
						currAddr += len(data)
						pos += len(data)
					
					elif self.MODE == "AGB":
						# MSP55LV128 etc.
						if flashcart_meta["commands"]["single_write"] == [[0xAAA, 0xA9], [0x555, 0x56], [0xAAA, 0xA0], ['PA', 'PD']]:
							data = data_import[pos:pos+256]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_256BYTE_SWAPPED_D0D1"], data)
								ack = self.wait_for_ack()
							currAddr += 256
							pos += 256
						
						# 128W30B0 etc.
						if flashcart_meta["commands"]["single_write"] == [[ 'PA', 0x40 ], [ 'PA', 'PD' ]]:
							data = data_import[pos:pos+64]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_INTEL_64BYTE_WORD"], data)
								ack = self.wait_for_ack()
							currAddr += 64
							pos += 64
						
						# E201850 and E201868
						elif flashcart_meta["commands"]["single_write"] == [[0, 0x70], [0, 0x10], ['PA', 'PD']] and (([ 0xB0, 0x00, 0xE2, 0x00 ] in flashcart_meta["flash_ids"]) or ([ 0xB0, 0x00, 0xB0, 0x00 ] in flashcart_meta["flash_ids"])):
							data = data_import[pos:pos+64]
							if data == bytearray([0xFF] * len(data)):
								skipping = True
							else:
								if skipping:
									self.set_number(currAddr / 2, self.DEVICE_CMD["SET_START_ADDRESS"])
									skipping = False
								self.gbx_flash_write_data_bytes(self.DEVICE_CMD["GBA_FLASH_WRITE_SHARP_64BYTE"], data)
								ack = self.wait_for_ack()
							currAddr += 64
							pos += 64
						
						else: # super slow -- for testing purposes only!
							for i in range(0, len(flashcart_meta["commands"]["single_write"])):
								addr = flashcart_meta["commands"]["single_write"][i][0]
								data = flashcart_meta["commands"]["single_write"][i][1]
								if addr == "PA": addr = int(currAddr)
								if data == "PD": data = struct.unpack('H', data_import[pos:pos+2])[0]
								self.gbx_flash_write_address_byte(addr, data)
							currAddr += 2
							pos += 2
							data = data_import[pos:pos+2]
				
				if ack == False:
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Couldn’t write {:d} bytes to flash at position 0x{:X}. Please make sure that the cartridge contacts are clean, and that the selected cartridge type and settings are correct.".format(len(data), pos-len(data)), "abortable":False})
					return False
				else:
					self.SetProgress({"action":"WRITE", "bytes_added":len(data), "skipping":skipping})
		
		# Reset Flash
		if "reset_every" in flashcart_meta:
			for j in range(0, pos, flashcart_meta["reset_every"]):
				for i in range(0, len(flashcart_meta["commands"]["reset"])):
					self.gbx_flash_write_address_byte(j, flashcart_meta["commands"]["reset"][i][1])
		elif "reset" in flashcart_meta["commands"]:
			for i in range(0, len(flashcart_meta["commands"]["reset"])):
				self.gbx_flash_write_address_byte(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1])
		
		# Verify Flash
		verified = False
		if verify_flash:
			rom_size = len(data_import)
			buffer_len = 0x1000
			if self.MODE == "DMG":
				if fast_read_mode:
					buffer_len = 0x4000
					self.FAST_READ = True
			elif self.MODE == "AGB":
				if fast_read_mode:
					buffer_len = 0x10000
					self.FAST_READ = True
			
			data_dump = bytearray()
			
			startAddr = 0
			currAddr = 0
			pos = 0
			
			if self.MODE == "DMG":
				endAddr = bank_size
			else:
				endAddr = rom_size
				bank_count = 1
			
			# Read a bit before actually dumping (fixes some bootlegs)
			self.ReadROM(0, 64)
			
			self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE_VERIFY", "size":rom_size})
			
			for bank in range(0, bank_count):
				if self.MODE == "DMG":
					if bank > 0:
						startAddr = bank_size
						endAddr = startAddr + bank_size
					self.SetBankROM(bank, mbc=mbc, bank_count=bank_count)
				
				for currAddr in range(startAddr, endAddr, buffer_len):
					if self.CANCEL:
						cancel_args = {"action":"ABORT", "abortable":False}
						cancel_args.update(self.CANCEL_ARGS)
						self.CANCEL_ARGS = {}
						self.SetProgress(cancel_args)
						try:
							file.close()
						except:
							pass
						return
					
					if currAddr == startAddr:
						buffer = self.ReadROM(currAddr, buffer_len, True)
					else:
						buffer = self.ReadROM(currAddr, buffer_len, False)
					
					if buffer == False:
						self.CANCEL = True
						continue
					
					if not buffer == data_import[pos:pos+buffer_len]:
						err_pos = 0
						for i in range(0, buffer_len):
							if buffer[i] != data_import[pos+i]:
								err_pos = pos+i
								break
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The ROM was flashed completely, but verification of flashed data failed at address 0x{:X}.".format(err_pos), "abortable":False})
						self.CANCEL = True
						return False
					
					pos += buffer_len
					self.SetProgress({"action":"UPDATE_POS", "pos":pos})
			verified = True
		
		self.POS = 0
		if self.MODE == "DMG":
			self.SetBankROM(0, mbc=mbc, bank_count=bank_count)
		
		self.SetProgress({"action":"FINISHED", "verified":verified})
