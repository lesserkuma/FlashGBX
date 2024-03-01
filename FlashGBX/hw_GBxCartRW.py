# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import time, math, struct, traceback, zlib, copy, hashlib, os, datetime, platform, json, base64
import serial, serial.tools.list_ports
from serial import SerialException
from .RomFileDMG import RomFileDMG
from .RomFileAGB import RomFileAGB
from .Mapper import DMG_MBC, AGB_GPIO
from .Flashcart import Flashcart, Flashcart_DMG_MMSA
from .Util import ANSI, dprint, bitswap, ParseCFI
from .GBMemory import GBMemoryMap
from . import Util

class GbxDevice:
	DEVICE_NAME = "GBxCart RW"
	DEVICE_MIN_FW = 1
	DEVICE_MAX_FW = 10
	DEVICE_LATEST_FW_TS = { 4:1709317610, 5:1707258786, 6:1707258786 }
	
	DEVICE_CMD = {
		"NULL":0x30,
		"OFW_RESET_AVR":0x2A,
		"OFW_CART_MODE":0x43,
		"OFW_FW_VER":0x56,
		"OFW_PCB_VER":0x68,
		"OFW_USART_1_0M_SPEED":0x3C,
		"OFW_USART_1_7M_SPEED":0x3E,
		"OFW_CART_PWR_ON":0x2F,
		"OFW_CART_PWR_OFF":0x2E,
		"OFW_QUERY_CART_PWR":0x5D,
		"OFW_DONE_LED_ON":0x3D,
		"OFW_ERROR_LED_ON":0x3F,
		"OFW_GB_CART_MODE":0x47,
		"OFW_GB_FLASH_BANK_1_COMMAND_WRITES":0x4E,
		"OFW_LNL_QUERY":0x25,
		"QUERY_FW_INFO":0xA1,
		"SET_MODE_AGB":0xA2,
		"SET_MODE_DMG":0xA3,
		"SET_VOLTAGE_3_3V":0xA4,
		"SET_VOLTAGE_5V":0xA5,
		"SET_VARIABLE":0xA6,
		"SET_FLASH_CMD":0xA7,
		"SET_ADDR_AS_INPUTS":0xA8,
		"CLK_HIGH":0xA9,
		"CLK_LOW":0xAA,
		"ENABLE_PULLUPS":0xAB,
		"DISABLE_PULLUPS":0xAC,
		"GET_VARIABLE":0xAD,
		"DMG_CART_READ":0xB1,
		"DMG_CART_WRITE":0xB2,
		"DMG_CART_WRITE_SRAM":0xB3,
		"DMG_MBC_RESET":0xB4,
		"DMG_MBC7_READ_EEPROM":0xB5,
		"DMG_MBC7_WRITE_EEPROM":0xB6,
		"DMG_MBC6_MMSA_WRITE_FLASH":0xB7,
		"DMG_SET_BANK_CHANGE_CMD":0xB8,
		"DMG_EEPROM_WRITE":0xB9,
		"AGB_CART_READ":0xC1,
		"AGB_CART_WRITE":0xC2,
		"AGB_CART_READ_SRAM":0xC3,
		"AGB_CART_WRITE_SRAM":0xC4,
		"AGB_CART_READ_EEPROM":0xC5,
		"AGB_CART_WRITE_EEPROM":0xC6,
		"AGB_CART_WRITE_FLASH_DATA":0xC7,
		"AGB_CART_READ_3D_MEMORY":0xC8,
		"AGB_BOOTUP_SEQUENCE":0xC9,
		"DMG_FLASH_WRITE_BYTE":0xD1,
		"AGB_FLASH_WRITE_SHORT":0xD2,
		"FLASH_PROGRAM":0xD3,
		"CART_WRITE_FLASH_CMD":0xD4,
		"CALC_CRC32":0xD5,
	}
	# \#define VAR(\d+)_([^\t]+)\t+(.+)
	DEVICE_VAR = {
		"ADDRESS":[32, 0x00],
		"TRANSFER_SIZE":[16, 0x00],
		"BUFFER_SIZE":[16, 0x01],
		"DMG_ROM_BANK":[16, 0x02],
		"CART_MODE":[8, 0x00],
		"DMG_ACCESS_MODE":[8, 0x01],
		"FLASH_COMMAND_SET":[8, 0x02],
		"FLASH_METHOD":[8, 0x03],
		"FLASH_WE_PIN":[8, 0x04],
		"FLASH_PULSE_RESET":[8, 0x05],
		"FLASH_COMMANDS_BANK_1":[8, 0x06],
		"FLASH_SHARP_VERIFY_SR":[8, 0x07],
		"DMG_READ_CS_PULSE":[8, 0x08],
		"DMG_WRITE_CS_PULSE":[8, 0x09],
		"FLASH_DOUBLE_DIE":[8, 0x0A],
		"DMG_READ_METHOD":[8, 0x0B],
		"AGB_READ_METHOD":[8, 0x0C],
	}

	PCB_VERSIONS = {4:'v1.3', 5:'v1.4', 6:'v1.4a/b/c', 101:'Mini v1.0d'}
	ACTIONS = {"ROM_READ":1, "SAVE_READ":2, "SAVE_WRITE":3, "ROM_WRITE":4, "ROM_WRITE_VERIFY":4, "SAVE_WRITE_VERIFY":3}
	SUPPORTED_CARTS = {}
	
	FW = []
	FW_UPDATE_REQ = False
	FW_VAR = {}
	MODE = None
	PORT = ''
	DEVICE = None
	WORKER = None
	INFO = { "action":None, "last_action":None, "dump_info":{} }
	ERROR = False
	ERROR_ARGS = {}
	CANCEL = False
	CANCEL_ARGS = {}
	SIGNAL = None
	POS = 0
	NO_PROG_UPDATE = False
	FAST_READ = False
	SKIPPING = False
	BAUDRATE = 1000000
	MAX_BUFFER_READ = 0x2000
	MAX_BUFFER_WRITE = 0x400
	DEVICE_TIMEOUT = 1
	WRITE_DELAY = False
	READ_ERRORS = 0
	
	def __init__(self):
		pass
	
	def Initialize(self, flashcarts, port=None, max_baud=1700000):
		if self.IsConnected(): self.DEVICE.close()
		if platform.system() == "Darwin": max_baud = 1000000
		
		conn_msg = []
		ports = []
		if port is not None:
			ports = [ port ]
		else:
			comports = serial.tools.list_ports.comports()
			for i in range(0, len(comports)):
				if comports[i].vid == 0x1A86 and comports[i].pid == 0x7523:
					ports.append(comports[i].device)
			if len(ports) == 0: return False
		
		for i in range(0, len(ports)):
			try:
				dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
				self.DEVICE = dev
				if not self.LoadFirmwareVersion() and max_baud >= 1700000:
					dev.close()
					self.BAUDRATE = 1700000
					dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
					self.DEVICE = dev
					if not self.LoadFirmwareVersion():
						dev.close()
						self.DEVICE = None
						self.BAUDRATE = 1000000
						continue
				elif max_baud >= 1700000 and self.FW["pcb_ver"] in (5, 6, 101) and self.BAUDRATE < 1700000:
					self.ChangeBaudRate(baudrate=1700000)
					self.DEVICE.close()
					dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
					self.DEVICE = dev
				
				dprint("Firmware information:", self.FW)
				dprint("Baud rate:", self.BAUDRATE)

				if self.DEVICE is None or not self.IsConnected():
					dev.close()
					self.DEVICE = None
					if self.FW is not None:
						conn_msg.append([0, "Couldn’t communicate with the GBxCart RW device on port " + ports[i] + ". Please disconnect and reconnect the device, then try again."])
					continue
				elif self.FW is None or "cfw_id" not in self.FW or self.FW["cfw_id"] != 'L' or self.FW["fw_ver"] < self.DEVICE_MIN_FW or (self.FW["pcb_ver"] < 5 and self.FW["fw_ver"] != 1): # Not a CFW by Lesserkuma
					dev.close()
					self.DEVICE = None
					continue
				elif self.FW["fw_ts"] > self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
					conn_msg.append([0, "Note: The GBxCart RW device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
				
				if self.FW["pcb_ver"] not in (4, 5, 6, 101): # only the v1.3, v1.4, v1.4a/b/c, Mini v1.1 PCB revisions are supported
					dev.close()
					self.DEVICE = None
					continue
				elif self.FW["pcb_ver"] in (5, 6, 101) and self.BAUDRATE > 1000000:
					self.MAX_BUFFER_READ = 0x2000
					self.MAX_BUFFER_WRITE = 0x400
				else:
					self.MAX_BUFFER_READ = 0x1000
					self.MAX_BUFFER_WRITE = 0x100
				
				conn_msg.append([0, "For help please visit the insideGadgets Discord: https://gbxcart.com/discord"])

				self.PORT = ports[i]
				self.DEVICE.timeout = self.DEVICE_TIMEOUT
				
				# Load Flash Cartridge Handlers
				self.UpdateFlashCarts(flashcarts)

				# Stop after first found device
				break
			
			except SerialException as e:
				if "Permission" in str(e):
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " couldn’t be accessed. Make sure your user account has permission to use it and it’s not already in use by another application."])
				else:
					conn_msg.append([3, "A critical error occured while trying to access the GBxCart RW device on port " + ports[i] + ".\n\n" + str(e)])
				continue
		
		return conn_msg
	
	def LoadFirmwareVersion(self):
		dprint("Reading firmware version...")
		try:
			self.DEVICE.reset_input_buffer()
			self.DEVICE.reset_output_buffer()
			self._write(self.DEVICE_CMD["OFW_PCB_VER"])
			temp = self.DEVICE.read(1)
			pcb = temp[0]
			if pcb == b'': return False
			self._write(self.DEVICE_CMD["OFW_FW_VER"])
			ofw = self._read(1)
			if (pcb < 5 and ofw > 0):
				self.FW = None
				return False
			
			self._write(self.DEVICE_CMD["QUERY_FW_INFO"])
			size = self._read(1)
			info = self._read(size)
			keys = ["cfw_id", "fw_ver", "pcb_ver", "fw_ts"]
			values = struct.unpack(">cHBI", bytearray(info))
			self.FW = dict(zip(keys, values))
			self.FW["cfw_id"] = self.FW["cfw_id"].decode('ascii')
			self.FW["fw_dt"] = datetime.datetime.fromtimestamp(self.FW["fw_ts"]).astimezone().replace(microsecond=0).isoformat()
			self.FW["ofw_ver"] = ofw
			dprint(self.FW)
			return True
		
		except:
			dprint("Disconnecting...")
			try:
				if self.DEVICE.isOpen():
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					self.DEVICE.close()
				self.DEVICE = None
			except:
				pass
			return False
	
	def GetBaudRate(self):
		return self.BAUDRATE
	
	def ChangeBaudRate(self, baudrate):
		if not self.IsConnected(): return
		if baudrate == 1700000:
			self._write(self.DEVICE_CMD["OFW_USART_1_7M_SPEED"])
		elif baudrate == 1000000:
			self._write(self.DEVICE_CMD["OFW_USART_1_0M_SPEED"])
		self.BAUDRATE = baudrate
	
	def CanSetVoltageManually(self):
		return False
	
	def CanSetVoltageAutomatically(self):
		return True
	
	def CanPowerCycleCart(self):
		if self.FW is None or self.DEVICE is None: return False
		if not self.DEVICE.is_open: return False
		return self.FW["pcb_ver"] in (5, 6)
	
	def GetSupprtedModes(self):
		if self.FW["pcb_ver"] == 101:
			return ["DMG"]
		else:
			return ["DMG", "AGB"]
	
	def IsSupportedMbc(self, mbc):
		if self.CanPowerCycleCart():
			return mbc in ( 0x00, 0x01, 0x02, 0x03, 0x05, 0x06, 0x08, 0x09, 0x0B, 0x0D, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x20, 0x22, 0xFC, 0xFD, 0xFE, 0xFF, 0x101, 0x103, 0x104, 0x105, 0x110, 0x201, 0x202, 0x203, 0x204, 0x205 )
		else:
			return mbc in ( 0x00, 0x01, 0x02, 0x03, 0x05, 0x06, 0x08, 0x09, 0x0B, 0x0D, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x20, 0x22, 0xFC, 0xFD, 0xFE, 0xFF, 0x101, 0x103, 0x104, 0x105, 0x110, 0x202, 0x205 )
	
	def IsSupported3dMemory(self):
		return True
	
	def IsClkConnected(self):
		return self.FW["pcb_ver"] in (5, 6, 101)

	def UpdateFlashCarts(self, flashcarts):
		self.SUPPORTED_CARTS = { 
			"DMG":{ "Generic ROM Cartridge":"RETAIL" },
			"AGB":{ "Generic ROM Cartridge":"RETAIL" }
		}
		for mode in flashcarts.keys():
			for key in sorted(flashcarts[mode].keys(), key=str.casefold):
				self.SUPPORTED_CARTS[mode][key] = flashcarts[mode][key]
	
	def IsConnected(self):
		if self.DEVICE is None: return False
		if not self.DEVICE.isOpen(): return False
		try:
			while self.DEVICE.in_waiting > 0:
				dprint("Clearing input buffer... ({:d})".format(self.DEVICE.in_waiting), self.DEVICE.read(self.DEVICE.in_waiting))
				self.DEVICE.reset_input_buffer()
				time.sleep(0.5)
			self.DEVICE.reset_output_buffer()
			return self.LoadFirmwareVersion()
		except SerialException as e:
			print("Connection lost!")
			try:
				if e.args[0].startswith("ClearCommError failed"):
					self.DEVICE.close()
					return False
			except:
				pass
			print(str(e))
			return False
	
	def Close(self, cartPowerOff=False):
		if self.IsConnected():
			try:
				if cartPowerOff:
					if self.FW["pcb_ver"] in (5, 6, 101):
						self._write(self.DEVICE_CMD["OFW_CART_MODE"])
						self._read(1)
						self._write(self.DEVICE_CMD["OFW_CART_PWR_OFF"])
					self._write(self.DEVICE_CMD["SET_ADDR_AS_INPUTS"])
				self.DEVICE.close()
			except:
				self.DEVICE = None
			self.MODE = None
	
	def GetName(self):
		return "GBxCart RW"
	
	def GetFirmwareVersion(self, more=False):
		if self.FW["pcb_ver"] in (5, 6, 101):
			s = "R{:d}+{:s}{:d}".format(self.FW["ofw_ver"], self.FW["cfw_id"], self.FW["fw_ver"])
		else:
			s = "{:s}{:d}".format(self.FW["cfw_id"], self.FW["fw_ver"])
		if more:
			s += " ({:s})".format(self.FW["fw_dt"])
		return s
	
	def GetPCBVersion(self):
		if self.FW["pcb_ver"] in self.PCB_VERSIONS:
			return self.PCB_VERSIONS[self.FW["pcb_ver"]]
		else:
			return "(unknown revision)"
	
	def GetFullName(self):
		self.DEVICE_NAME = "{:s} {:s}".format(self.GetName(), self.GetPCBVersion())
		return self.DEVICE_NAME
	
	def GetFullNameExtended(self, more=False):
		if more:
			return "{:s} – Firmware {:s} ({:s}) on {:s} at {:.1f}M baud".format(self.GetFullName(), self.GetFirmwareVersion(), self.FW["fw_dt"], self.PORT, self.BAUDRATE/1000/1000)
		else:
			return "{:s} – Firmware {:s}".format(self.GetFullName(), self.GetFirmwareVersion())

	def GetOfficialWebsite(self):
		return "https://www.gbxcart.com/"
	
	def SupportsFirmwareUpdates(self):
		if self.FW["ofw_ver"] == 30:
			self._write(self.DEVICE_CMD["OFW_LNL_QUERY"])
			old_timeout = self.DEVICE.timeout
			self.DEVICE.timeout = 0.15
			is_lnl = self._read(1) == 0x31
			self.DEVICE.timeout = old_timeout
			dprint("LinkNLoad detected:", is_lnl)
			if is_lnl: return False
		return self.FW["pcb_ver"] in (4, 5, 6)
	
	def FirmwareUpdateAvailable(self):
		if self.FW["pcb_ver"] not in (4, 5, 6): return False
		if self.FW["pcb_ver"] in (5, 6) and self.FW["fw_ts"] < self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
			return True
		if self.FW["pcb_ver"] == 4 and self.FW["fw_ts"] != self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
			self.FW_UPDATE_REQ = True
			return True
	
	def GetFirmwareUpdaterClass(self):
		if self.FW["pcb_ver"] == 4: # v1.3
			try:
				from . import fw_GBxCartRW_v1_3
				return (None, fw_GBxCartRW_v1_3.FirmwareUpdaterWindow)
			except:
				return False
		elif self.FW["pcb_ver"] in (5, 6): # v1.4 / v1.4a/b/c
			try:
				from . import fw_GBxCartRW_v1_4
				return (fw_GBxCartRW_v1_4.FirmwareUpdater, fw_GBxCartRW_v1_4.FirmwareUpdaterWindow)
			except:
				return False
		else:
			return False
	
	def GetPort(self):
		return self.PORT
	
	def GetFWBuildDate(self):
		return self.FW["fw_dt"]
	
	def SetWriteDelay(self, enable=True):
		if self.WRITE_DELAY != enable:
			dprint("Setting Write Delay to", enable)
			self.WRITE_DELAY = enable
	
	def SetTimeout(self, seconds=1):
		if seconds < 1: seconds = 1
		self.DEVICE_TIMEOUT = seconds
		self.DEVICE.timeout = self.DEVICE_TIMEOUT
	
	def wait_for_ack(self, values=None):
		if values is None: values = [0x01, 0x03]
		buffer = self._read(1)
		if buffer not in values:
			tb_stack = traceback.extract_stack()
			stack = tb_stack[len(tb_stack)-2] # caller only
			if stack.name == "_write": stack = tb_stack[len(tb_stack)-3]
			dprint("CANCEL_ARGS:", self.CANCEL_ARGS)
			if "from_user" in self.CANCEL_ARGS and self.CANCEL_ARGS["from_user"]:
				return False
			elif buffer is False:
				dprint("Timeout error ({:s}(), line {:d}): {:f}".format(stack.name, stack.lineno, self.DEVICE.timeout))
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"A timeout error has occured at {:s}() in line {:d}. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.".format(stack.name, stack.lineno)})
			else:
				dprint("Communication error ({:s}(), line {:d}): {:s}".format(stack.name, stack.lineno, str(buffer)))
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"A communication error has occured at {:s}() in line {:d}. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.".format(stack.name, stack.lineno)})
			self.ERROR = True
			self.CANCEL = True
			self.SetWriteDelay(enable=True)
			return False
		return buffer
	
	def _write(self, data, wait=False):
		if not isinstance(data, bytearray):
			data = bytearray([data])

		#dstr = ' '.join(format(x, '02X') for x in data)
		#dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr[:96]))
		
		self.DEVICE.write(data)
		self.DEVICE.flush()
		
		# On MacOS it’s possible not all bytes are transmitted successfully,
		# even though we’re using flush() which is the tcdrain function.
		# Still looking for a better solution than delaying here.
		if platform.system() == "Darwin" or self.WRITE_DELAY is True:
			time.sleep(0.00125)
		
		if wait: return self.wait_for_ack()
	
	def _read(self, count):
		if self.DEVICE.in_waiting > 1000: dprint("in_waiting = {:d} bytes".format(self.DEVICE.in_waiting))
		buffer = self.DEVICE.read(count)
		if len(buffer) != count:
			tb_stack = traceback.extract_stack()
			stack = tb_stack[len(tb_stack)-2] # caller only
			if stack.name == "_read": stack = tb_stack[len(tb_stack)-3]
			#traceback.print_stack()
			dprint("Warning: Received {:d} byte(s) instead of the expected {:d} byte(s) ({:s}(), line {:d})".format(len(buffer), count, stack.name, stack.lineno))
			self.READ_ERRORS += 1
			while self.DEVICE.in_waiting > 0:
				self.DEVICE.reset_input_buffer()
				time.sleep(0.5)
			self.DEVICE.reset_output_buffer()
			return False
		
		if count == 1:
			return buffer[0]
		else:
			return bytearray(buffer)

	def _set_fw_variable(self, key, value):
		dprint("Setting firmware variable {:s} to 0x{:X}".format(key, value))
		self.FW_VAR[key] = value

		size = 0
		for (k, v) in self.DEVICE_VAR.items():
			if key in k:
				if v[0] == 8: size = 1
				elif v[0] == 16: size = 2
				elif v[0] == 32: size = 4
				key = v[1]
				break
		if size == 0:
			raise KeyError("Unknown variable name specified.")
		
		buffer = bytearray([self.DEVICE_CMD["SET_VARIABLE"], size])
		buffer.extend(struct.pack(">I", key))
		buffer.extend(struct.pack(">I", value))
		self._write(buffer)
		if self.WRITE_DELAY is True:
			time.sleep(0.001)
	
	def _cart_read(self, address, length=0, agb_save_flash=False):
		if self.MODE == "DMG":
			if length == 0:
				length = 1
				if address < 0xA000:
					return struct.unpack("B", self.ReadROM(address, 1))[0]
				else:
					return struct.unpack("B", self.ReadRAM(address - 0xA000, 1))[0]
			else:
				if address < 0xA000:
					return self.ReadROM(address, length)
				else:
					return self.ReadRAM(address - 0xA000, length)
		elif self.MODE == "AGB":
			if length == 0:
				length = 2
				if agb_save_flash:
					return struct.unpack(">H", self.ReadRAM(address, length, command=self.DEVICE_CMD["AGB_CART_READ_SRAM"]))[0]
				else:
					return struct.unpack(">H", self.ReadROM(address >> 1, length))[0]
			else:
				if agb_save_flash:
					return self.ReadRAM(address, length, command=self.DEVICE_CMD["AGB_CART_READ_SRAM"])
				else:
					return self.ReadROM(address, length)

	def _cart_write(self, address, value, flashcart=False, sram=False):
		dprint("Writing to cartridge: 0x{:X} = 0x{:X} (args: {:s}, {:s})".format(address, value & 0xFF, str(flashcart), str(sram)))
		if self.MODE == "DMG":
			if flashcart:
				buffer = bytearray([self.DEVICE_CMD["DMG_FLASH_WRITE_BYTE"]])
			else:
				if sram: self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
				buffer = bytearray([self.DEVICE_CMD["DMG_CART_WRITE"]])
			buffer.extend(struct.pack(">I", address))
			buffer.extend(struct.pack("B", value & 0xFF))
		elif self.MODE == "AGB":
			if sram:
				self._set_fw_variable("TRANSFER_SIZE", 1)
				self._set_fw_variable("ADDRESS", address)
				self._write(self.DEVICE_CMD["AGB_CART_WRITE_SRAM"])
				self._write(value)
				self._read(1)
				return
			elif flashcart:
				buffer = bytearray([self.DEVICE_CMD["AGB_FLASH_WRITE_SHORT"]])
			else:
				buffer = bytearray([self.DEVICE_CMD["AGB_CART_WRITE"]])
			
			buffer.extend(struct.pack(">I", address >> 1))
			buffer.extend(struct.pack(">H", value & 0xFFFF))
		
		self._write(buffer)
		
		if self.MODE == "DMG" and sram: self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
	
	def _cart_write_flash(self, commands, flashcart=False):
		if self.FW["fw_ver"] < 6 and not (self.MODE == "AGB" and not flashcart):
			for command in commands:
				self._cart_write(command[0], command[1], flashcart=flashcart)
			return
		
		num = len(commands)
		buffer = bytearray([self.DEVICE_CMD["CART_WRITE_FLASH_CMD"]])
		if self.FW["fw_ver"] >= 6:
			buffer.extend(struct.pack("B", 1 if flashcart else 0))
		buffer.extend(struct.pack("B", num))
		for i in range(0, num):
			dprint("Writing to cartridge: 0x{:X} = 0x{:X} ({:d} of {:d})".format(commands[i][0], commands[i][1], i+1, num))
			if self.MODE == "AGB" and flashcart:
				buffer.extend(struct.pack(">I", commands[i][0] >> 1))
			else:
				buffer.extend(struct.pack(">I", commands[i][0]))
			
			if self.FW["fw_ver"] < 6:
				buffer.extend(struct.pack("B", commands[i][1]))
			else:
				buffer.extend(struct.pack(">H", commands[i][1]))
		
		self._write(buffer)
		ret = self._read(1)
		if ret != 0x01:
			dprint("Communication error in _cart_write_flash():", ret)
			self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"A critical communication error occured during a write. Please avoid passive USB hubs, try different USB ports/cables and re-connect the device."})
			self.CANCEL = True
			self.ERROR = True
			return False

	def _clk_toggle(self, num):
		if self.FW["pcb_ver"] not in (5, 6, 101): return False
		for _ in range(0, num):
			self._write(self.DEVICE_CMD["CLK_HIGH"])
			self._write(self.DEVICE_CMD["CLK_LOW"])
		return True
	
	def _set_we_pin_wr(self):
		if self.MODE == "DMG":
			self._set_fw_variable("FLASH_WE_PIN", 0x01) # FLASH_WE_PIN_WR
	def _set_we_pin_audio(self):
		if self.MODE == "DMG":
			self._set_fw_variable("FLASH_WE_PIN", 0x02) # FLASH_WE_PIN_AUDIO
	
	def CartPowerCycle(self, delay=0.1):
		if self.CanPowerCycleCart():
			dprint("Power cycling cartridge with a delay of {:.1f} seconds".format(delay))
			self.CartPowerOff(delay=delay)
			self.CartPowerOn(delay=delay)
			if self.MODE == "DMG":
				self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			elif self.MODE == "AGB":
				self._write(self.DEVICE_CMD["SET_MODE_AGB"])

	def CartPowerOff(self, delay=0.1):
		if self.FW["pcb_ver"] in (5, 6):
			self._write(self.DEVICE_CMD["OFW_CART_PWR_OFF"])
			time.sleep(delay)
		else:
			self._write(self.DEVICE_CMD["SET_ADDR_AS_INPUTS"])
	
	def CartPowerOn(self, delay=0.1):
		if self.FW["pcb_ver"] in (5, 6):
			self._write(self.DEVICE_CMD["OFW_QUERY_CART_PWR"])
			if self._read(1) == 0:
				self._write(self.DEVICE_CMD["OFW_CART_PWR_ON"])
				time.sleep(delay)
				self.DEVICE.reset_input_buffer() # bug workaround
	
	def GetMode(self):
		return self.MODE
	
	def SetMode(self, mode, delay=0.1):
		# self.CartPowerOff(delay=delay)
		if mode == "DMG":
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			self._set_fw_variable("DMG_READ_METHOD", 1)
			self._set_fw_variable("CART_MODE", 1)
			self.MODE = "DMG"
		elif mode == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			self._set_fw_variable("AGB_READ_METHOD", 0)
			self._set_fw_variable("CART_MODE", 2)
			self.MODE = "AGB"
		self._set_fw_variable(key="ADDRESS", value=0)
		if self.FW["fw_ver"] >= 8: self._write(self.DEVICE_CMD["DISABLE_PULLUPS"], wait=True)
		self.CartPowerOn()
	
	def GetSupportedCartridgesDMG(self):
		return (list(self.SUPPORTED_CARTS['DMG'].keys()), list(self.SUPPORTED_CARTS['DMG'].values()))
	
	def GetSupportedCartridgesAGB(self):
		return (list(self.SUPPORTED_CARTS['AGB'].keys()), list(self.SUPPORTED_CARTS['AGB'].values()))
	
	def SetProgress(self, args):
		if self.CANCEL and args["action"] not in ("ABORT", "FINISHED", "ERROR"): return
		if "pos" in args: self.POS = args["pos"]
		if args["action"] == "UPDATE_POS": self.INFO["transferred"] = args["pos"]
		try:
			self.SIGNAL.emit(args)
		except AttributeError:
			if self.SIGNAL is not None:
				self.SIGNAL(args)
		
		if args["action"] == "INITIALIZE":
			self.POS = 0
		elif args["action"] == "FINISHED":
			self.POS = 0
			self.SIGNAL = None
	
	def ReadInfo(self, setPinsAsInputs=False, checkRtc=True):
		if not self.IsConnected(): raise ConnectionError("Couldn’t access the the device.")
		data = {}
		self.SIGNAL = None
		
		if self.FW["pcb_ver"] in (5, 6, 101):
			self._write(self.DEVICE_CMD["OFW_CART_MODE"]) # Reset LEDs
			self._read(1)
			self.CartPowerOn()
		
		if self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
		elif self.MODE == "AGB":
			if self.FW["pcb_ver"] in (5, 6, 101) and self.FW["fw_ver"] > 1:
				self._write(self.DEVICE_CMD["AGB_BOOTUP_SEQUENCE"], wait=True)
		else:
			print("{:s}Error: No mode was set.{:s}".format(ANSI.RED, ANSI.RESET))
			return False
		
		header = self.ReadROM(0, 0x180)
		if Util.DEBUG:
			with open("debug_header.bin", "wb") as f: f.write(header)
		if header is False or len(header) != 0x180:
			return False
		
		# Parse ROM header
		if self.MODE == "DMG":
			data = RomFileDMG(header).GetHeader()
			if "game_title" in data and data["game_title"] == "TETRIS" and hashlib.sha1(header).digest() != bytearray([0x1D, 0x69, 0x2A, 0x4B, 0x31, 0x7A, 0xA5, 0xE9, 0x67, 0xEE, 0xC2, 0x2F, 0xCC, 0x32, 0x43, 0x8C, 0xCB, 0xC5, 0x78, 0x0B]): # Sachen
				header = self.ReadROM(0, 0x280)
				data = RomFileDMG(header).GetHeader()
			if "logo_correct" in data and data["logo_correct"] is False and not b"Future Console Design" in header: # workaround for strange bootlegs
				self._cart_write(0, 0xFF)
				time.sleep(0.1)
				header = self.ReadROM(0, 0x280)
				data = RomFileDMG(header).GetHeader()
			if "mapper_raw" in data and data["mapper_raw"] == 0x203 or b"Future Console Design" in header: # Xploder GB version number
				self._cart_write(0x0006, 0)
				header[0:0x10] = self.ReadROM(0x4000, 0x10)
				header[0xD0:0xE0] = self.ReadROM(0x40D0, 0x10)
				data = RomFileDMG(header).GetHeader()
			if data == {}: return False

			data["has_rtc"] = False
			data["rtc_string"] = "Not available"
			if data["logo_correct"] is True:
				_mbc = DMG_MBC().GetInstance(args={"mbc":data["mapper_raw"]}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
				if checkRtc:
					data["has_rtc"] = _mbc.HasRTC() is True
					if data["has_rtc"] is True:
						if _mbc.GetName() == "TAMA5": _mbc.EnableMapper()
						_mbc.LatchRTC()
						data["rtc_buffer"] = _mbc.ReadRTC()
						if _mbc.GetName() == "TAMA5": self._set_fw_variable("DMG_READ_CS_PULSE", 0)
						try:
							data["rtc_string"] = _mbc.GetRTCString()
						except:
							data["rtc_string"] = "Invalid data"
				if _mbc.GetName() == "G-MMC1":
					try:
						temp = bytearray([0] * 0x100000)
						temp[0:0x180] = header
						_mbc.SelectBankROM(7)
						if data["game_title"] == "NP M-MENU MENU":
							gbmem_menudata = self.ReadROM(0x4000, 0x1000)
							temp[0x1C000:0x1C000+0x1000] = gbmem_menudata
						elif data["game_title"] == "DMG MULTI MENU ":
							gbmem_menudata = self.ReadROM(0x4000, 0x4000)
							temp[0x1C000:0x1C000+0x4000] = gbmem_menudata
						_mbc.SelectBankROM(0)
						data["gbmem_parsed"] = (GBMemoryMap()).ParseMapData(buffer_map=_mbc.ReadHiddenSector(), buffer_rom=temp)
					except:
						print(traceback.format_exc())
						print("{:s}An error occured while trying to read the hidden sector data of the NP GB-Memory cartridge.{:s}".format(ANSI.RED, ANSI.RESET))

		elif self.MODE == "AGB":
			# Unlock DACS carts on older firmware
			if self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] == 1:
				if header[0x04:0x04+0x9C] == bytearray([0x00] * 0x9C):
					self.ReadROM(0x1FFFFE0, 20)
					header = self.ReadROM(0, 0x180)
			
			data = RomFileAGB(header).GetHeader()
			if data["logo_correct"] is False: # workaround for strange bootlegs
				self._cart_write(0, 0xFF)
				time.sleep(0.1)
				header = self.ReadROM(0, 0x180)
				data = RomFileAGB(header).GetHeader()
			
			if data["empty"] or data["empty_nocart"]:
				data["rom_size"] = 0x2000000
			else:
				# Check where the ROM data repeats (for unlicensed carts)
				size_check = header[0xA0:0xA0+16]
				currAddr = 0x10000
				while currAddr < 0x2000000:
					buffer = self.ReadROM(currAddr + 0xA0, 64)[:16]
					if buffer == size_check: break
					currAddr *= 2
				data["rom_size"] = currAddr
				
			if (self.ReadROM(0x1FFE000, 0x0C) == b"AGBFLASHDACS"):
				data["dacs_8m"] = True
			
			data["rtc_string"] = "Not available"
			if checkRtc and data["logo_correct"] is True and header[0xC5] == 0 and header[0xC7] == 0 and header[0xC9] == 0:
				_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
				has_rtc = _agb_gpio.HasRTC()
				data["has_rtc"] = has_rtc is True
				if has_rtc is not True:
					data["no_rtc_reason"] = has_rtc
					data["has_rtc"] = False
				else:
					data["rtc_buffer"] = _agb_gpio.ReadRTC()
					try:
						data["rtc_string"] = _agb_gpio.GetRTCString()
					except Exception as e:
						dprint("RTC exception:", str(e.args[0]))
						data["has_rtc"] = False
			else:
				data["has_rtc"] = False
				data["no_rtc_reason"] = None
			
			if data["ereader"] is True:
				bank = 0
				dprint("Switching to FLASH bank {:d}".format(bank))
				cmds = [
					[ 0x5555, 0xAA ],
					[ 0x2AAA, 0x55 ],
					[ 0x5555, 0xB0 ],
					[ 0, bank ]
				]
				self._cart_write_flash(cmds)
				temp = self.ReadRAM(address=0xD000, length=0x2000, command=self.DEVICE_CMD["AGB_CART_READ_SRAM"])
				if temp[0:0x14] == b'Card-E Reader 2001\0\0':
					data["ereader_calibration"] = temp
				else:
					data["ereader_calibration"] = None
					del(data["ereader_calibration"])
		
		dprint("Header data:", data)
		data["raw"] = header
		self.INFO = {**self.INFO, **data}
		if "batteryless_sram" in self.INFO["dump_info"]: del(self.INFO["dump_info"]["batteryless_sram"])
		self.INFO["dump_info"]["header"] = data
		self.INFO["flash_type"] = 0
		self.INFO["last_action"] = 0
		
		if self.MODE == "DMG": #and setPinsAsInputs:
			self._write(self.DEVICE_CMD["SET_ADDR_AS_INPUTS"])

		return data
	
	def DetectCartridge(self, mbc=None, limitVoltage=False, checkSaveType=True):
		self.SIGNAL = None
		cart_type_id = 0
		save_type = None
		save_chip = None
		sram_unstable = None
		save_size = None
		checkBatterylessSRAM = False

		# Header
		has_rtc = self.INFO["has_rtc"]
		info = self.ReadInfo(checkRtc=False)
		self.INFO["has_rtc"] = has_rtc

		if self.MODE == "DMG" and mbc is None:
			mbc = info["mapper_raw"]
			if mbc > 0x200: checkSaveType = False

		ret = self.AutoDetectFlash(limitVoltage=limitVoltage)
		if ret is False: return False
		(cart_types, cart_type_id, flash_id, cfi_s, cfi, detected_size) = ret
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = supported_carts[cart_type_id]
		if self.MODE == "DMG" and "command_set" in cart_type and cart_type["command_set"] == "DMG-MBC5-32M-FLASH":
			checkSaveType = False
		elif self.MODE == "AGB" and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
			save_size = 65536
			save_type = 7
			checkSaveType = False
		elif self.MODE == "AGB" and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] > 1:
			checkSaveType = False
		elif self.MODE == "DMG" and "mbc" in cart_type and cart_type["mbc"] == 0x105: # G-MMC1
			header = self.ReadROM(0, 0x180)
			data = RomFileDMG(header).GetHeader()
			_mbc = DMG_MBC().GetInstance(args={"mbc":cart_type["mbc"]}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
			temp = bytearray([0] * 0x100000)
			temp[0:0x180] = header
			_mbc.SelectBankROM(7)
			if data["game_title"] == "NP M-MENU MENU":
				gbmem_menudata = self.ReadROM(0x4000, 0x1000)
				temp[0x1C000:0x1C000+0x1000] = gbmem_menudata
			elif data["game_title"] == "DMG MULTI MENU ":
				gbmem_menudata = self.ReadROM(0x4000, 0x4000)
				temp[0x1C000:0x1C000+0x4000] = gbmem_menudata
			_mbc.SelectBankROM(0)
			info["gbmem"] = _mbc.ReadHiddenSector()
			info["gbmem_parsed"] = (GBMemoryMap()).ParseMapData(buffer_map=info["gbmem"], buffer_rom=temp)
		
		# Save Type and Size
		if checkSaveType:
			if self.MODE == "DMG":
				save_size = 131072
				save_type = 0x04
				if mbc == 0x20: # MBC6
					save_size = 1081344
					save_type = 0x104
					return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id, detected_size)
				elif mbc == 0x22: # MBC7
					save_type = 0x102
					save_size = 512
				elif mbc == 0xFD: # TAMA5
					save_size = 32
					save_type = 0x103
					return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id, detected_size)
				args = { 'mode':2, 'path':None, 'mbc':mbc, 'save_type':save_type, 'rtc':False }
			elif self.MODE == "AGB":
				args = { 'mode':2, 'path':None, 'mbc':mbc, 'save_type':8, 'rtc':False }
			
			ret = self._BackupRestoreRAM(args=args)
			
			if ret is not False and "data" in self.INFO:
				save_size = Util.find_size(self.INFO["data"], len(self.INFO["data"]))
			else:
				save_size = 0

			if self.MODE == "DMG":
				try:
					save_type = Util.DMG_Header_RAM_Sizes_Map[Util.DMG_Header_RAM_Sizes_Flasher_Map.index(save_size)]
				except:
					save_size = 0
					save_type = 0
				
				if save_size > 0x20:
					if mbc == 0x22: # MBC7
						if save_size == 256:
							save_type = 0x101
						elif save_size == 512:
							save_type = 0x102
					elif save_size > 0x10000: # MBC30+RTC?
						check = True
						for i in range(0x8000, 0x10000, 0x40):
							if self.INFO["data"][i:i+3] != bytearray([self.INFO["data"][i]] * 3):
								check = False
								break
						if check:
							save_size = 32768
							save_type = 0x03
						else:
							check = True
							for i in range(0x1A000, 0x20000, 0x40):
								if self.INFO["data"][i:i+3] != bytearray([self.INFO["data"][i]] * 3):
									check = False
									break
							if check:
								save_size = 65536
								save_type = 0x05
			
			elif self.MODE == "AGB":
				if info["3d_memory"] is True:
					save_type = None
					save_size = 0
				else:
					# Check for FLASH
					ret = self.ReadFlashSaveID()
					if ret is not False:
						(flash_save_id, _) = ret
						try:
							if flash_save_id != 0 and flash_save_id in Util.AGB_Flash_Save_Chips:
								save_size = Util.AGB_Flash_Save_Chips_Sizes[list(Util.AGB_Flash_Save_Chips).index(flash_save_id)]
								save_chip = Util.AGB_Flash_Save_Chips[flash_save_id]
								if save_size == 131072:
									save_type = 5
								elif save_size == 65536:
									save_type = 4
						except:
							pass
					
					if save_type is None:
						checkBatterylessSRAM = True
						if info["dacs_8m"] is True:
							save_size = 1048576
							save_type = 6
						elif save_size > 256: # SRAM
							if save_size == 131072:
								save_type = 8
								checkBatterylessSRAM = True
							elif save_size == 65536:
								save_type = 7
								checkBatterylessSRAM = True
							elif save_size == 32768:
								save_type = 3
							elif save_size in Util.AGB_Header_Save_Sizes:
								save_type = Util.AGB_Header_Save_Sizes.index(save_size)
							else:
								save_type = None
								save_size = 0
						else:
							dprint("Testing EEPROM")
							# Check for 4K EEPROM
							self._BackupRestoreRAM(args={ 'mode':2, 'path':None, 'mbc':mbc, 'save_type':1, 'rtc':False })
							save_size = Util.find_size(self.INFO["data"], len(self.INFO["data"]))
							eeprom_4k = self.INFO["data"]
							# Check for 64K EEPROM
							self._BackupRestoreRAM(args={ 'mode':2, 'path':None, 'mbc':mbc, 'save_type':2, 'rtc':False })
							save_size = Util.find_size(self.INFO["data"], len(self.INFO["data"]))
							eeprom_64k = self.INFO["data"]
							if eeprom_64k in (bytearray([0xFF] * len(eeprom_64k)), bytearray([0] * len(eeprom_64k))):
								save_type = None
								save_size = 0
							elif (eeprom_4k == eeprom_64k[:len(eeprom_4k)]):
								save_type = 2
								save_size = 8192
								checkBatterylessSRAM = False
							else:
								save_type = 1
								save_size = 512
								checkBatterylessSRAM = False

					if checkBatterylessSRAM:
						batteryless = self.CheckBatterylessSRAM()
						if batteryless is not False:
							save_type = 9
							info["batteryless_sram"] = batteryless
							self.INFO["dump_info"]["batteryless_sram"] = batteryless

		self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
		self.INFO["last_action"] = 0
		self.INFO["action"] = None
		return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id, detected_size)
	
	def CheckBatterylessSRAM(self):
		bl_size = None
		bl_offset = None
		if self.MODE == "AGB":
			buffer = self.ReadROM(0, 0x180)
			header = RomFileAGB(buffer).GetHeader()
			if header["game_code"] in ("GMBC", "PNES"):
				bl_size = 0x10000
				state_id1 = 0x57a731d7
				state_id2 = 0x57a731d8
				state_id3 = 0x57a731d9
				if struct.unpack("<I", self.ReadROM(0x400000-0x40000, 4))[0] in (state_id1, state_id2, state_id3):
					bl_offset = 0x400000-0x40000
				elif struct.unpack("<I", self.ReadROM(0x800000-0x40000, 4))[0] in (state_id1, state_id2, state_id3):
					bl_offset = 0x800000-0x40000
				elif struct.unpack("<I", self.ReadROM(0x1000000-0x40000, 4))[0] in (state_id1, state_id2, state_id3):
					bl_offset = 0x1000000-0x40000
				elif struct.unpack("<I", self.ReadROM(0x2000000-0x40000, 4))[0] in (state_id1, state_id2, state_id3):
					bl_offset = 0x2000000-0x40000
				dprint("Detected Goomba Color or PocketNES Batteryless ROM by Lesserkuma")
			else:
				boot_vector = (struct.unpack("<I", buffer[0:3] + bytearray([0]))[0] + 2) << 2
				batteryless_loader = self.ReadROM(boot_vector, 0x2000)
				if bytearray(b'<3 from Maniac') in batteryless_loader:
					payload_size = struct.unpack("<H", batteryless_loader[batteryless_loader.index(bytearray(b'<3 from Maniac')):][0x0E:0x10])[0]
					if payload_size == 0:
						payload_size = 0x414
					bl_offset = batteryless_loader.index(bytearray(b'<3 from Maniac')) + boot_vector + 0x10
					payload = self.ReadROM(bl_offset - payload_size, payload_size)
					bl_size = struct.unpack("<I", payload[0x8:0xC])[0]
					dprint("Detected Batteryless SRAM ROM made with the Automatic batteryless saving patcher for GBA by metroid-maniac")
					if bl_size not in (0x2000, 0x8000, 0x10000, 0x20000):
						print("{:s}Warning: Unsupported Batteryless SRAM size value detected: 0x{:X}{:s}".format(ANSI.YELLOW, bl_size, ANSI.RESET))
				elif (bytearray([0x02, 0x13, 0xA0, 0xE3]) in batteryless_loader):
					if (
						bytearray([0x09, 0x04, 0xA0, 0xE3]) in batteryless_loader or
						bytearray([0x09, 0x14, 0xA0, 0xE3]) in batteryless_loader or
						bytearray([0x09, 0x24, 0xA0, 0xE3]) in batteryless_loader or
						bytearray([0x09, 0x34, 0xA0, 0xE3]) in batteryless_loader
					):
						bl_size = 0x20000
					else:
						bl_size = 0x10000
					base_addr = batteryless_loader.index(bytearray([0x02, 0x13, 0xA0, 0xE3]))
					addr_value = batteryless_loader[base_addr - 8]
					addr_rotate_right = batteryless_loader[base_addr - 7] * 2
					addr_shift = batteryless_loader[base_addr - 3] << 1
					address = (addr_value >> addr_rotate_right) | (addr_value << (32 - addr_rotate_right)) & 0xFFFFFFFF
					address = (address << addr_shift)
					if address < 32*1024*1024 and address > 0x1000:
						bl_offset = address
						dprint("Detected Chinese bootleg Batteryless SRAM ROM")
					else:
						dprint("Bad offset with Chinese bootleg Batteryless SRAM ROM:", hex(address))
				else:
					bl_offset = None
					bl_size = None
		if bl_offset is None or bl_size is None:
			dprint("No Batteryless SRAM routine detected")
			return False
		dprint("bl_offset=0x{:X}, bl_size=0x{:X}".format(bl_offset, bl_size))
		return {"bl_offset":bl_offset, "bl_size":bl_size}

	def ReadFlashSaveID(self):
		# Check if actually SRAM/FRAM
		test1 = self._cart_read(0x0004, agb_save_flash=True) >> 8
		self._cart_write_flash([[ 0x0004, test1 ^ 0xFF ]])
		test2 = self._cart_read(0x0004, agb_save_flash=True) >> 8
		if test1 != test2:
			self._cart_write_flash([[ 0x0004, test1 ]])
			dprint("Seems to be SRAM/FRAM, not FLASH")
			return False

		# Read Chip ID
		temp5555 = self._cart_read(0x5555, agb_save_flash=True) >> 8
		temp2AAA = self._cart_read(0x2AAA, agb_save_flash=True) >> 8
		temp0000 = self._cart_read(0x0000, agb_save_flash=True) >> 8
		
		cmds = [
			[ 0x5555, 0xAA ],
			[ 0x2AAA, 0x55 ],
			[ 0x5555, 0x90 ]
		]
		self._cart_write_flash(cmds)
		time.sleep(0.01)
		agb_flash_chip = self._cart_read(0, agb_save_flash=True)
		cmds = [
			[ 0x5555, 0xAA ],
			[ 0x2AAA, 0x55 ],
			[ 0x5555, 0xF0 ]
		]
		self._cart_write_flash(cmds)
		time.sleep(0.01)
		self._cart_write_flash([ [ 0, 0xF0 ] ])
		time.sleep(0.01)
		
		if agb_flash_chip not in Util.AGB_Flash_Save_Chips:
			# Restore SRAM values
			cmds = [
				[ 0x5555, temp5555 ],
				[ 0x2AAA, temp2AAA ],
				[ 0x0000, temp0000 ]
			]
			self._cart_write_flash(cmds)
			agb_flash_chip_name = "Unknown flash chip ID (0x{:04X})".format(agb_flash_chip)
		else:
			agb_flash_chip_name = Util.AGB_Flash_Save_Chips[agb_flash_chip]
		
		dprint(agb_flash_chip_name)
		return (agb_flash_chip, agb_flash_chip_name)
	
	def ReadROM(self, address, length, skip_init=False, max_length=64):
		num = math.ceil(length / max_length)
		dprint("Reading 0x{:X} bytes from cartridge ROM at 0x{:X} in {:d} iteration(s)".format(length, address, num))
		if length > max_length: length = max_length

		buffer = bytearray()
		if not skip_init:
			self._set_fw_variable("TRANSFER_SIZE", length)
			if self.MODE == "DMG":
				self._set_fw_variable("ADDRESS", address)
				self._set_fw_variable("DMG_ACCESS_MODE", 1) # MODE_ROM_READ
			elif self.MODE == "AGB":
				self._set_fw_variable("ADDRESS", address >> 1)
		
		if self.MODE == "DMG":
			command = "DMG_CART_READ"
		elif self.MODE == "AGB":
			command = "AGB_CART_READ"
		
		for n in range(0, num):
			self._write(self.DEVICE_CMD[command])
			temp = self._read(length)
			if temp is not False and isinstance(temp, int): temp = bytearray([temp])
			if temp is False or len(temp) != length:
				dprint("Error while trying to read 0x{:X} bytes from cartridge ROM at 0x{:X} in iteration {:d} of {:d} (response: {:s})".format(length, address, n, num, str(temp)))
				return bytearray()
			buffer += temp
			if self.INFO["action"] in (self.ACTIONS["ROM_READ"], self.ACTIONS["SAVE_READ"], self.ACTIONS["ROM_WRITE_VERIFY"]) and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"READ", "bytes_added":len(temp)})
		
		return buffer

	def ReadROM_3DMemory(self, address, length, max_length=64):
		buffer_size = 0x1000
		num = math.ceil(length / max_length)
		dprint("Reading 0x{:X} bytes from cartridge ROM in {:d} iteration(s)".format(length, num))
		if length > max_length: length = max_length

		self._set_fw_variable("TRANSFER_SIZE", length)
		self._set_fw_variable("BUFFER_SIZE", buffer_size)
		self._set_fw_variable("ADDRESS", address >> 1)

		buffer = bytearray()
		error = False
		for _ in range(0, int(num / (buffer_size / length))): #32
			for _ in range(0, int(buffer_size / length)): # 0x1000/0x200=8
				self._write(self.DEVICE_CMD["AGB_CART_READ_3D_MEMORY"])
				temp = self._read(length)
				if isinstance(temp, int): temp = bytearray([temp])
				if temp is False or len(temp) != length:
					error = True
				buffer += temp
				if self.INFO["action"] == self.ACTIONS["ROM_READ"] and not self.NO_PROG_UPDATE:
					self.SetProgress({"action":"READ", "bytes_added":length})
			self._write(0)
		
		if error: return bytearray()
		return buffer

	def ReadRAM(self, address, length, command=None, max_length=64):
		num = math.ceil(length / max_length)
		dprint("Reading 0x{:X} bytes from cartridge RAM in {:d} iteration(s)".format(length, num))
		if length > max_length: length = max_length
		buffer = bytearray()
		self._set_fw_variable("TRANSFER_SIZE", length)
		
		if self.MODE == "DMG":
			self._set_fw_variable("ADDRESS", 0xA000 + address)
			self._set_fw_variable("DMG_ACCESS_MODE", 3) # MODE_RAM_READ
			self._set_fw_variable("DMG_READ_CS_PULSE", 1)
			if command is None: command = self.DEVICE_CMD["DMG_CART_READ"]
		elif self.MODE == "AGB":
			self._set_fw_variable("ADDRESS", address)
			if command is None: command = self.DEVICE_CMD["AGB_CART_READ_SRAM"]

		for _ in range(0, num):
			self._write(command)
			temp = self._read(length)
			if isinstance(temp, int): temp = bytearray([temp])
			if temp is False or len(temp) != length: return bytearray()
			buffer += temp
			if not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"READ", "bytes_added":len(temp)})

		if self.MODE == "DMG":
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)

		return buffer

	def ReadRAM_MBC7(self, address, length):
		max_length = 32
		num = math.ceil(length / max_length)
		dprint("Reading 0x{:X} bytes from cartridge EEPROM in {:d} iteration(s)".format(length, num))
		if length > max_length: length = max_length
		buffer = bytearray()
		self._set_fw_variable("TRANSFER_SIZE", length)
		self._set_fw_variable("ADDRESS", address)
		for _ in range(0, num):
			self._write(self.DEVICE_CMD["DMG_MBC7_READ_EEPROM"])
			temp = self._read(length)
			if isinstance(temp, int): temp = bytearray([temp])
			buffer += temp
			if not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"READ", "bytes_added":len(temp)})
		
		return buffer

	def ReadRAM_TAMA5(self):
		dprint("Reading 0x20 bytes from cartridge RAM")
		buffer = bytearray()
		npu = self.NO_PROG_UPDATE
		self.NO_PROG_UPDATE = True
		self._set_fw_variable("DMG_READ_CS_PULSE", 1)
		self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)

		# Read save state
		for i in range(0, 0x20):
			self._cart_write(0xA001, 0x06, sram=True) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | 0x01 << 1, sram=True) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, 0x07, sram=True) # address (low)
			self._cart_write(0xA000, i & 0x0F, sram=True) # bits 0-3 = lower ram address
			self._cart_write(0xA001, 0x0D, sram=True) # data out (high)
			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			data_h = value1
			self._cart_write(0xA001, 0x0C, sram=True) # data out (low)

			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			data_l = value1
			
			data = ((data_h & 0xF) << 4) | (data_l & 0xF)
			buffer.append(data)
			self.SetProgress({"action":"UPDATE_POS", "abortable":False, "pos":i+1})
		
		self._set_fw_variable("DMG_READ_CS_PULSE", 0)
		
		self.NO_PROG_UPDATE = npu
		return buffer
	
	def WriteRAM(self, address, buffer, command=None, max_length=256):
		length = len(buffer)
		num = math.ceil(length / max_length)
		dprint("Writing 0x{:X} bytes to cartridge RAM in {:d} iteration(s)".format(length, num))
		if length > max_length: length = max_length

		self._set_fw_variable("TRANSFER_SIZE", length)
		if self.MODE == "DMG":
			self._set_fw_variable("ADDRESS", 0xA000 + address)
			self._set_fw_variable("DMG_ACCESS_MODE", 4) # MODE_RAM_WRITE
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
			if command is None: command = self.DEVICE_CMD["DMG_CART_WRITE_SRAM"]
		elif self.MODE == "AGB":
			self._set_fw_variable("ADDRESS", address)
			if command is None: command = self.DEVICE_CMD["AGB_CART_WRITE_SRAM"]

		for i in range(0, num):
			self._write(command)
			self._write(buffer[i*length:i*length+length])
			self._read(1)
			if self.INFO["action"] == self.ACTIONS["SAVE_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		
		if self.MODE == "DMG":
			self._set_fw_variable("ADDRESS", 0)
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
		
		return True

	def WriteFlash_MBC6(self, address, buffer, mapper):
		length = len(buffer)
		max_length = 128
		num = math.ceil(length / max_length)
		if length > max_length: length = max_length
		dprint("Write 0x{:X} bytes to cartridge FLASH in {:d} iteration(s)".format(length, num))
		
		skip_write = False
		for i in range(0, num):
			self._set_fw_variable("TRANSFER_SIZE", length)
			self._set_fw_variable("ADDRESS", address)
			dprint("Now in iteration {:d}".format(i))

			if buffer[i*length:i*length+length] == bytearray([0xFF] * length):
				skip_write = True
				address += length
				continue

			cmds = [
				[ 0x2000, 0x01 ],
				[ 0x3000, 0x02 ],
				[ 0x7555, 0xAA ],
				[ 0x4AAA, 0x55 ],
				[ 0x7555, 0xA0 ],
			]
			self._cart_write_flash(cmds)
			mapper.SelectBankFlash(mapper.GetROMBank())
			self._write(self.DEVICE_CMD["DMG_MBC6_MMSA_WRITE_FLASH"])
			self._write(buffer[i*length:i*length+length])
			ret = self._read(1)
			if ret not in (0x01, 0x03):
				dprint("Save write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length))
				if "from_user" in self.CANCEL_ARGS and self.CANCEL_ARGS["from_user"]: return False
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Save write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)})
				self.CANCEL = True
				self.ERROR = True
				return False
			self._cart_write(address + length - 1, 0x00)
			while True:
				sr = self._cart_read(address + length - 1)
				if sr == 0x80: break
				time.sleep(0.001)
			
			address += length
			if self.INFO["action"] == self.ACTIONS["SAVE_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		self._cart_write(address - 1, 0xF0)
		self.SKIPPING = skip_write
	
	def WriteEEPROM_MBC7(self, address, buffer):
		length = len(buffer)
		max_length = 32
		num = math.ceil(length / max_length)
		if length > max_length: length = max_length
		dprint("Write 0x{:X} bytes to cartridge EEPROM in {:d} iteration(s)".format(length, num))
		self._set_fw_variable("TRANSFER_SIZE", length)
		self._set_fw_variable("ADDRESS", address)
		for i in range(0, num):
			self._write(self.DEVICE_CMD["DMG_MBC7_WRITE_EEPROM"])
			self._write(buffer[i*length:i*length+length])
			response = self._read(1)
			dprint("Response:", response)
			if self.INFO["action"] == self.ACTIONS["SAVE_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})

	def WriteRAM_TAMA5(self, buffer):
		npu = self.NO_PROG_UPDATE
		self.NO_PROG_UPDATE = True

		for i in range(0, 0x20):
			self._cart_write(0xA001, 0x05, sram=True) # data in (high)
			self._cart_write(0xA000, buffer[i] >> 4, sram=True)
			self._cart_write(0xA001, 0x04, sram=True) # data in (low)
			self._cart_write(0xA000, buffer[i] & 0xF, sram=True)
			self._cart_write(0xA001, 0x06, sram=True) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | 0x00 << 1, sram=True) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, 0x07, sram=True) # address (low)
			self._cart_write(0xA000, i & 0x0F, sram=True) # bits 0-3 = lower ram address
			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			self.SetProgress({"action":"UPDATE_POS", "abortable":False, "pos":i+1})
		
		self.NO_PROG_UPDATE = npu

	def WriteROM(self, address, buffer, flash_buffer_size=False, skip_init=False, rumble_stop=False, max_length=MAX_BUFFER_WRITE):
		length = len(buffer)
		num = math.ceil(length / max_length)
		dprint("Writing 0x{:X} bytes to Flash ROM in {:d} iteration(s)".format(length, num))
		if length == 0:
			dprint("Length is zero?")
			return False
		elif length > max_length:
			length = max_length

		skip_write = False
		ret = 0
		num_of_chunks = math.ceil(flash_buffer_size / length)
		pos = 0

		if not skip_init:
			self._set_fw_variable("TRANSFER_SIZE", length)
			if flash_buffer_size is not False:
				self._set_fw_variable("BUFFER_SIZE", flash_buffer_size)
		
		for i in range(0, num):
			data = bytearray(buffer[i*length:i*length+length])
			if (num_of_chunks == 1 or flash_buffer_size == 0) and (data == bytearray([0xFF] * len(data))):
				skip_init = False
				skip_write = True
			else:
				if skip_write:
					skip_write = False
			
			if not skip_write:
				if not skip_init:
					if self.MODE == "DMG":
						self._set_fw_variable("ADDRESS", address)
					elif self.MODE == "AGB":
						self._set_fw_variable("ADDRESS", address >> 1)
					skip_init = True
				
				if ret != 0x03: self._write(self.DEVICE_CMD["FLASH_PROGRAM"])
				ret = self._write(data, wait=True)
				
				if ret not in (0x01, 0x03):
					dprint("Flash error at 0x{:X} in iteration {:d} of {:d} while trying to write a total of 0x{:X} bytes (response = {:s})".format(address, i, num, len(buffer), str(ret)))
					self.ERROR_ARGS = { "iteration":i }
					self.SKIPPING = False
					return False
				pos += len(data)
				
				if rumble_stop and flash_buffer_size > 0 and pos % flash_buffer_size == 0:
					dprint("Sending rumble stop command")
					self._cart_write(address=0xC6, value=0x00, flashcart=True)
					rumble_stop = False
			
			address += length
			if ((pos % length) * 10 == 0) and (self.INFO["action"] in (self.ACTIONS["ROM_WRITE"], self.ACTIONS["SAVE_WRITE"]) and not self.NO_PROG_UPDATE):
				self.SetProgress({"action":"WRITE", "bytes_added":length, "skipping":skip_write})
		
		self.SKIPPING = skip_write
	
	def WriteROM_GBMEMORY(self, address, buffer, bank):
		length = len(buffer)
		max_length = 128
		num = math.ceil(length / max_length)
		if length > max_length: length = max_length
		dprint("Writing 0x{:X} bytes to Flash ROM in {:d} iteration(s)".format(length, num))
		
		skip_write = False
		for i in range(0, num):
			self._set_fw_variable("TRANSFER_SIZE", length)
			self._set_fw_variable("ADDRESS", address)
			dprint("Now in iteration {:d}".format(i))
			
			if buffer[i*length:i*length+length] == bytearray([0xFF] * length):
				skip_write = True
				address += length
				continue
			
			# Enable flash chip access
			self._cart_write_flash([
				[ 0x120, 0x09 ],
				[ 0x121, 0xAA ],
				[ 0x122, 0x55 ],
				[ 0x13F, 0xA5 ],
			])
			# Re-Enable writes to MBC registers
			self._cart_write_flash([
				[ 0x120, 0x11 ],
				[ 0x13F, 0xA5 ],
			])
			# Bank 1 for commands
			self._cart_write_flash([
				[ 0x2100, 0x01 ],
			])
			
			# Write setup
			self._cart_write_flash([
				[ 0x120, 0x0F ],
				[ 0x125, 0x55 ],
				[ 0x126, 0x55 ],
				[ 0x127, 0xAA ],
				[ 0x13F, 0xA5 ],
			])
			self._cart_write_flash([
				[ 0x120, 0x0F ],
				[ 0x125, 0x2A ],
				[ 0x126, 0xAA ],
				[ 0x127, 0x55 ],
				[ 0x13F, 0xA5 ],
			])
			self._cart_write_flash([
				[ 0x120, 0x0F ],
				[ 0x125, 0x55 ],
				[ 0x126, 0x55 ],
				[ 0x127, 0xA0 ],
				[ 0x13F, 0xA5 ],
			])

			# Set bank back
			self._cart_write_flash([
				[ 0x2100, bank ],
			])
						
			# Disable writes to MBC registers
			self._cart_write_flash([
				[ 0x120, 0x10 ],
				[ 0x13F, 0xA5 ],
			])
						
			# Undo Wakeup
			self._cart_write_flash([
				[ 0x120, 0x08 ],
				[ 0x13F, 0xA5 ],
			])

			self._write(self.DEVICE_CMD["DMG_MBC6_MMSA_WRITE_FLASH"])
			self._write(buffer[i*length:i*length+length])
			ret = self._read(1)
			if ret not in (0x01, 0x03):
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Flash write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)})
				self.CANCEL = True
				self.ERROR = True
				return False
			
			self._cart_write(address + length - 1, 0xFF)
			while True:
				sr = self._cart_read(address + length - 1)
				if sr == 0x80: break
				time.sleep(0.001)

			address += length
			if self.INFO["action"] == self.ACTIONS["ROM_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		
		self._cart_write(address - 1, 0xF0)
		self.SKIPPING = skip_write
	
	def WriteROM_DMG_MBC5_32M_FLASH(self, address, buffer, bank):
		length = len(buffer)
		max_length = 128
		num = math.ceil(length / max_length)
		if length > max_length: length = max_length
		dprint("Writing 0x{:X} bytes to Flash ROM in {:d} iteration(s)".format(length, num))
		
		skip_write = False
		for i in range(0, num):
			self._set_fw_variable("TRANSFER_SIZE", length)
			self._set_fw_variable("ADDRESS", address)
			dprint("Now in iteration {:d}".format(i))
			
			if buffer[i*length:i*length+length] == bytearray([0xFF] * length):
				skip_write = True
				address += length
				continue
			
			self._cart_write(0x4000, 0xFF)
			self._cart_write_flash([
				[ address, 0xE0 ],
				[ address, length - 1 ],
				[ address, 0x00 ],
			])
			self._write(self.DEVICE_CMD["DMG_MBC6_MMSA_WRITE_FLASH"])
			self._write(buffer[i*length:i*length+length])
			ret = self._read(1)
			if ret not in (0x01, 0x03):
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Flash write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)})
				self.CANCEL = True
				self.ERROR = True
				return False
			
			self._cart_write_flash([
				[ address, 0x0C ],
				[ address, length - 1 ],
				[ address, 0x00 ],
			])
			lives = 100
			while lives > 0:
				self._cart_write(0x4000, 0x70)
				sr = self._cart_read(address + length - 1)
				dprint("sr=0x{:X}".format(sr))
				if sr & 0x80 == 0x80: break
				time.sleep(0.001)
				lives -= 1
			self._cart_write(0x4000, 0xFF)
			
			if lives == 0:
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Flash write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(sr), i, length)})
				self.CANCEL = True
				self.ERROR = True
				return False
			
			address += length
			if self.INFO["action"] == self.ACTIONS["ROM_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		
		self._cart_write(address - 1, 0xFF)
		self.SKIPPING = skip_write
	
	def WriteROM_DMG_DatelOrbitV2(self, address, buffer, bank):
		length = len(buffer)
		dprint("Writing 0x{:X} bytes to Datel Orbit V2 cartridge".format(length))
		for i in range(0, length):
			self._cart_write(0x7FE1, 2)
			self._cart_write(0x5555, 0xAA)
			self._cart_write(0x2AAA, 0x55)
			self._cart_write(0x5555, 0xA0)
			self._cart_write(0x7FE1, bank)
			self._cart_write(address + i, buffer[i])
			if self.INFO["action"] == self.ACTIONS["ROM_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":1})
		return True
	
	def WriteROM_DMG_EEPROM(self, address, buffer, bank, eeprom_buffer_size=0x80):
		length = len(buffer)
		if self.FW["pcb_ver"] not in (5, 6, 101) or self.BAUDRATE == 1000000:
			max_length = 256
		else:
			max_length = 1024
		num = math.ceil(length / max_length)
		if length > max_length: length = max_length
		dprint("Writing 0x{:X} bytes to EEPROM in {:d} iteration(s)".format(length, num))
		
		for i in range(0, num):
			self._set_fw_variable("BUFFER_SIZE", eeprom_buffer_size)
			self._set_fw_variable("TRANSFER_SIZE", length)
			self._set_fw_variable("ADDRESS", address)
			dprint("Now in iteration {:d}".format(i))
			
			self._write(self.DEVICE_CMD["DMG_EEPROM_WRITE"])
			self._write(buffer[i*length:i*length+length])
			ret = self._read(1)
			if ret not in (0x01, 0x03):
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"EEPROM write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)})
				self.CANCEL = True
				self.ERROR = True
				return False
			
			address += length
			if self.INFO["action"] == self.ACTIONS["ROM_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		
		self._cart_write_flash([
			[0x0006, 0x01],
			[0x5555, 0xAA],
			[0x2AAA, 0x55],
			[0x5555, 0xF0],
			[0x0006, bank]
		])
	
	def CheckROMStable(self):
		if not self.IsConnected(): raise ConnectionError("Couldn’t access the the device.")
		buffer1 = self.ReadROM(0x80, 0x40)
		time.sleep(0.05)
		buffer2 = self.ReadROM(0x80, 0x40)
		return buffer1 == buffer2
	
	def AutoDetectFlash(self, limitVoltage=False):
		flash_types = []
		flash_type = 0
		flash_id = None
		flash_id_found = False
		
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())

		if self.MODE == "DMG":
			if limitVoltage:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			else:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.1)
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
		elif self.MODE == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
		
		for f in range(1, len(supported_carts)):
			if self.CANCEL or self.ERROR:
				cancel_args = {"action":"ABORT", "abortable":False}
				cancel_args.update(self.CANCEL_ARGS)
				self.CANCEL_ARGS = {}
				self.ERROR_ARGS = {}
				self.SetProgress(cancel_args)
				return False

			flashcart_meta = supported_carts[f]
			if flash_id is not None:
				if ("flash_ids" not in flashcart_meta) or (flash_id not in flashcart_meta["flash_ids"]):
					continue
			dprint("*** Now checking: {:s}\n".format(flashcart_meta["names"][0]))
			
			if self.MODE == "DMG":
				we = flashcart_meta["write_pin"]
				if we == "WR":
					self._set_fw_variable("FLASH_WE_PIN", 0x01) # FLASH_WE_PIN_WR
				elif we in ("AUDIO", "VIN"):
					self._set_fw_variable("FLASH_WE_PIN", 0x02) # FLASH_WE_PIN_AUDIO
				elif we == "WR+RESET":
					self._set_fw_variable("FLASH_WE_PIN", 0x03) # FLASH_WE_PIN_WR_RESET
			
			fc_fncptr = {
				"cart_write_fncptr":self._cart_write,
				"cart_write_fast_fncptr":self._cart_write_flash,
				"cart_read_fncptr":self.ReadROM,
				"cart_powercycle_fncptr":self.CartPowerCycle,
				"progress_fncptr":self.SetProgress,
				"set_we_pin_wr":self._set_we_pin_wr,
				"set_we_pin_audio":self._set_we_pin_audio,
			}
			flashcart = Flashcart(config=flashcart_meta, fncptr=fc_fncptr)
			flashcart.Reset(full_reset=False)
			if flashcart.Unlock() is False: return False
			if "flash_ids" in flashcart_meta and len(flashcart_meta["flash_ids"]) > 0:
				vfid = flashcart.VerifyFlashID()
				if vfid is not False:
					(verified, cart_flash_id) = vfid
					if verified and cart_flash_id in flashcart_meta["flash_ids"]:
						flash_id = cart_flash_id
						flash_id_found = True
						flash_type = f
						flash_types.append(flash_type)
						flashcart.Reset(full_reset=False)
						dprint("Found the correct cartridge type!")
		
		#if self.CanPowerCycleCart(): self.CartPowerCycle()

		# Check flash size
		flash_type_id = 0
		detected_size = 0
		cfi_s = ""
		cfi = None
		if len(flash_types) > 0:
			flash_type_id = flash_types[0]
			if self.MODE == "DMG":
				supp_flash_types = self.GetSupportedCartridgesDMG()
			elif self.MODE == "AGB":
				supp_flash_types = self.GetSupportedCartridgesAGB()
			
			(flash_id, cfi_s, cfi) = self.CheckFlashChip(limitVoltage=limitVoltage, cart_type=supp_flash_types[1][flash_type_id])
			if "flash_size" in supp_flash_types[1][flash_types[0]]:
				size = supp_flash_types[1][flash_types[0]]["flash_size"]
				size_undetected = False
				for i in range(0, len(flash_types)):
					if "flash_size" in supp_flash_types[1][flash_types[i]]:
						if size != supp_flash_types[1][flash_types[i]]["flash_size"]:
							size_undetected = True
				
				if size_undetected:
					if "flash_bank_select_type" in supp_flash_types[1][flash_types[0]] and supp_flash_types[1][flash_types[0]]["flash_bank_select_type"] == 1:
						# Check where the ROM data repeats (by bank switching)
						fc_fncptr = {
							"cart_write_fncptr":self._cart_write,
							"cart_write_fast_fncptr":self._cart_write_flash,
							"cart_read_fncptr":self.ReadROM,
							"cart_powercycle_fncptr":self.CartPowerCycle,
							"progress_fncptr":self.SetProgress,
							"set_we_pin_wr":self._set_we_pin_wr,
							"set_we_pin_audio":self._set_we_pin_audio,
						}
						flashcart = Flashcart(config=supp_flash_types[1][flash_types[0]], fncptr=fc_fncptr)
						flashcart.SelectBankROM(0)
						size_check = self.ReadROM(0, 0x1000) + self.ReadROM(0x1FFF000, 0x1000)
						num_banks = 1
						while num_banks < (flashcart.GetFlashSize() // 0x2000000) + 1:
							dprint("Checking bank {:d}".format(num_banks))
							flashcart.SelectBankROM(num_banks)
							buffer = self.ReadROM(0, 0x1000) + self.ReadROM(0x1FFF000, 0x1000)
							if buffer == size_check: break
							num_banks <<= 1
						detected_size = 0x2000000 * num_banks
						for i in range(0, len(flash_types)):
							if detected_size == supp_flash_types[1][flash_types[i]]["flash_size"]:
								dprint("Detected {:d} flash banks".format(num_banks))
								flash_type_id = flash_types[i]
								size_undetected = False
								break
						flashcart.SelectBankROM(0)

					elif isinstance(cfi, dict) and "device_size" in cfi:
						for i in range(0, len(flash_types)):
							if "flash_size" in supp_flash_types[1][flash_types[i]] and cfi['device_size'] == supp_flash_types[1][flash_types[i]]["flash_size"]:
								flash_type_id = flash_types[i]
								size_undetected = False
								break
					else:
						if self.MODE == "AGB":
							# Check where the ROM data repeats (for unlicensed carts)
							header = self.ReadROM(0, 0x180)
							size_check = header[0xA0:0xA0+16]
							currAddr = 0x10000
							while currAddr < 0x2000000:
								buffer = self.ReadROM(currAddr + 0xA0, 64)[:16]
								if buffer == size_check: break
								currAddr *= 2
							rom_size = currAddr

							for i in range(0, len(flash_types)):
								if "flash_size" in supp_flash_types[1][flash_types[i]] and rom_size == supp_flash_types[1][flash_types[i]]["flash_size"]:
									flash_type_id = flash_types[i]
									size_undetected = False
									break

		else:
			(flash_id, cfi_s, cfi) = self.CheckFlashChip(limitVoltage=limitVoltage)
		
		if self.MODE == "DMG" and not flash_id_found:
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.1)
		
		return (flash_types, flash_type_id, flash_id, cfi_s, cfi, detected_size)

	def CheckFlashChip(self, limitVoltage=False, cart_type=None): # aka. the most horribly written function
		if cart_type is not None:
			if self.MODE == "DMG":
				if cart_type["write_pin"] == "WR":
					we = 0x01 # FLASH_WE_PIN_WR
				elif cart_type["write_pin"] in ("AUDIO", "VIN"):
					we = 0x02 # FLASH_WE_PIN_AUDIO
				elif cart_type["write_pin"] == "WR+RESET":
					we = 0x03 # FLASH_WE_PIN_WR_RESET
				self._set_fw_variable("FLASH_WE_PIN", we)

		if self.FW["pcb_ver"] in (5, 6, 101):
			self._write(self.DEVICE_CMD["OFW_CART_MODE"])
			self._read(1)
			self.CartPowerOn()
		
		flashcart = None
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
		
		if self.MODE == "DMG":
			del(flash_commands[4]) # 0xAAAA is in SRAM space on DMG
			if limitVoltage:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			else:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.1)

		check_buffer = self.ReadROM(0, 0x400)
		d_swap = None
		cfi_info = ""
		rom_string = ""
		for j in range(0, 8):
			rom_string += "{:02X} ".format(check_buffer[j])
		rom_string += "\n"
		cfi = {'raw':b''}
		
		if self.MODE == "DMG":
			rom_string = "[     ROM     ] " + rom_string
			we_pins = [ "WR", "AUDIO" ]
		else:
			rom_string = "[   ROM   ] " + rom_string
			we_pins = [ None ]
		
		for we in we_pins:
			if "method" in cfi: break
			for method in flash_commands:
				if self.MODE == "DMG":
					if we == "WR":
						self._set_fw_variable("FLASH_WE_PIN", 0x01) # FLASH_WE_PIN_WR
					elif we in ("AUDIO", "VIN"):
						self._set_fw_variable("FLASH_WE_PIN", 0x02) # FLASH_WE_PIN_AUDIO
					elif we == "WR+RESET":
						self._set_fw_variable("FLASH_WE_PIN", 0x03) # FLASH_WE_PIN_WR_RESET
				
				for i in range(0, len(method['reset'])):
					self._cart_write(method['reset'][i][0], method['reset'][i][1], flashcart=True)
				for i in range(0, len(method['read_cfi'])):
					self._cart_write(method['read_cfi'][i][0], method["read_cfi"][i][1], flashcart=True)
				buffer = self.ReadROM(0, 0x400)
				for i in range(0, len(method['reset'])):
					self._cart_write(method['reset'][i][0], method['reset'][i][1], flashcart=True)
				#if buffer == check_buffer: continue
				if buffer == bytearray([0x00] * len(buffer)): continue
				
				magic = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
				if magic == "QRY": # nothing swapped
					d_swap = ( 0, 0 )
				elif magic == "RQZ": # D0D1 swapped
					d_swap = ( 0, 1 )
				if d_swap is not None and d_swap != ( 0, 0 ):
					for i in range(0, len(buffer)):
						buffer[i] = bitswap(buffer[i], d_swap)
				
				cfi_parsed = ParseCFI(buffer)
				try:
					if d_swap is not None:
						dprint("CFI @ {:s}/{:X}/{:X}/{:s}".format(str(we), method['read_identifier'][0][0], bitswap(method['read_identifier'][0][1], d_swap), str(d_swap)))
					else:
						dprint("CFI @ {:s}/{:X}/{:X}/{:s}".format(str(we), method['read_identifier'][0][0], method['read_identifier'][0][1], str(d_swap)))
					dprint("└", cfi_parsed)
				except:
					pass
				
				if cfi_parsed != False:
					cfi = cfi_parsed
					cfi["raw"] = buffer
					if Util.DEBUG:
						with open("debug_cfi.bin", "wb") as f: f.write(buffer)
					
					cfi["bytes"] = ""
					for i in range(0, 0x400):
						cfi["bytes"] += "{:02X}".format(buffer[i])
					if self.MODE == "DMG": cfi["we"] = we
					cfi["method_id"] = flash_commands.index(method)
					
					if d_swap is not None and d_swap != ( 0, 0 ):
						for k in method.keys():
							for c in range(0, len(method[k])):
								if isinstance(method[k][c][1], int):
									method[k][c][1] = bitswap(method[k][c][1], d_swap)
					
					# Flash ID
					for i in range(0, len(method['read_identifier'])):
						self._cart_write(method['read_identifier'][i][0], method["read_identifier"][i][1], flashcart=True)
					flash_id = self.ReadROM(0, 8)
					
					if self.MODE == "DMG":
						method_string = "[" + we.ljust(5) + "/{:4X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
					else:
						method_string = "[{:6X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
					line_exists = False
					for i in range(0, len(flash_id_lines)):
						if method_string == flash_id_lines[i][0]: line_exists = True
					if not line_exists: flash_id_lines.append([method_string, flash_id])
					for i in range(0, len(method['reset'])):
						self._cart_write(method['reset'][i][0], method['reset'][i][1], flashcart=True)
					
					cfi["method"] = method
				else:
					for j in range(0, 2):
						if j == 1:
							#d_swap = ( 0, 1 )
							for k in method.keys():
								for c in range(0, len(method[k])):
									if isinstance(method[k][c][1], int):
										method[k][c][1] = bitswap(method[k][c][1], ( 0, 1 ))
						for i in range(0, len(method['read_identifier'])):
							self._cart_write(method['read_identifier'][i][0], method["read_identifier"][i][1], flashcart=True)
						flash_id = self.ReadROM(0, 8)
						if flash_id == check_buffer[:len(flash_id)]: continue
						if flash_id == bytearray([0x00] * len(flash_id)): continue

						if self.MODE == "DMG":
							method_string = "[" + we.ljust(5) + "/{:4X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
						else:
							method_string = "[{:6X}/{:2X}]".format(method['read_identifier'][0][0], method['read_identifier'][0][1])
						line_exists = False
						for i in range(0, len(flash_id_lines)):
							if method_string == flash_id_lines[i][0]: line_exists = True
						if not line_exists: flash_id_lines.append([method_string, flash_id])
						for i in range(0, len(method['reset'])):
							self._cart_write(method['reset'][i][0], method['reset'][i][1], flashcart=True)

				if cart_type is not None: # reset cartridge if method is known
					fc_fncptr = {
						"cart_write_fncptr":self._cart_write,
						"cart_write_fast_fncptr":self._cart_write_flash,
						"cart_read_fncptr":self.ReadROM,
						"cart_powercycle_fncptr":self.CartPowerCycle,
						"progress_fncptr":self.SetProgress,
						"set_we_pin_wr":self._set_we_pin_wr,
						"set_we_pin_audio":self._set_we_pin_audio,
					}
					flashcart = Flashcart(config=cart_type, fncptr=fc_fncptr)
					flashcart.Reset(full_reset=False)
		
		if "method" in cfi:
			s = ""
			if d_swap is not None and d_swap != ( 0, 0 ): s += "Swapped pins: {:s}\n".format(str(d_swap))
			s += "Device size: 0x{:07X} ({:.2f} MiB)\n".format(cfi["device_size"], cfi["device_size"] / 1024 / 1024)
			s += "Voltage: {:.1f}–{:.1f} V\n".format(cfi["vdd_min"], cfi["vdd_max"])
			s += "Single write: {:s}\n".format(str(cfi["single_write"]))
			if "buffer_size" in cfi:
				s += "Buffered write: {:s} ({:d} Bytes)\n".format(str(cfi["buffer_write"]), cfi["buffer_size"])
			else:
				s += "Buffered write: {:s}\n".format(str(cfi["buffer_write"]))
			if cfi["chip_erase"]: s += "Chip erase: {:d}–{:d} ms\n".format(cfi["chip_erase_time_avg"], cfi["chip_erase_time_max"])
			if cfi["sector_erase"]: s += "Sector erase: {:d}–{:d} ms\n".format(cfi["sector_erase_time_avg"], cfi["sector_erase_time_max"])
			if cfi["tb_boot_sector"] is not False: s += "Sector flags: {:s}\n".format(str(cfi["tb_boot_sector"]))
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
				if we == "WR":
					self._set_fw_variable("FLASH_WE_PIN", 0x01) # FLASH_WE_PIN_WR
				elif we in ("AUDIO", "VIN"):
					self._set_fw_variable("FLASH_WE_PIN", 0x02) # FLASH_WE_PIN_AUDIO
				elif we == "WR+RESET":
					self._set_fw_variable("FLASH_WE_PIN", 0x03) # FLASH_WE_PIN_WR_RESET
				
				for method in flash_commands:
					for i in range(0, len(method['reset'])):
						self._cart_write(method['reset'][i][0], method["reset"][i][1], flashcart=True)
					for i in range(0, len(method['read_identifier'])):
						self._cart_write(method['read_identifier'][i][0], method["read_identifier"][i][1], flashcart=True)
					if "start_addr" in method:
						flash_id = self.ReadROM(method["start_addr"], 8)
					else:
						flash_id = self.ReadROM(0, 8)
					if flash_id == bytearray([0x00] * len(flash_id)): continue

					for i in range(0, len(method['reset'])):
						self._cart_write(method['reset'][i][0], method["reset"][i][1], flashcart=True)
					
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
							self._cart_write(method['reset'][i][0], method['reset'][i][1], flashcart=True)
		
		if self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.2)

		if cart_type is not None: # reset cartridge if method is known
			fc_fncptr = {
				"cart_write_fncptr":self._cart_write,
				"cart_write_fast_fncptr":self._cart_write_flash,
				"cart_read_fncptr":self.ReadROM,
				"cart_powercycle_fncptr":self.CartPowerCycle,
				"progress_fncptr":self.SetProgress,
				"set_we_pin_wr":self._set_we_pin_wr,
				"set_we_pin_audio":self._set_we_pin_audio,
			}
			flashcart = Flashcart(config=cart_type, fncptr=fc_fncptr)
			flashcart.Reset(full_reset=True)

		flash_id = ""
		for i in range(0, len(flash_id_lines)):
			flash_id += flash_id_lines[i][0] + " "
			for j in range(0, 8):
				flash_id += "{:02X} ".format(flash_id_lines[i][1][j])
			flash_id += "\n"
		
		flash_id = rom_string + flash_id
		#self._set_fw_variable("FLASH_WE_PIN", 0x02) # Set AUDIO back to high
		return (flash_id, cfi_info, cfi)
	
	def GetDumpReport(self):
		return Util.GetDumpReport(self.INFO["dump_info"], self)

	def GetReadErrors(self):
		return self.READ_ERRORS
	
	#################################################################
	
	def DoTransfer(self, mode, fncSetProgress, args):
		from . import DataTransfer
		args['mode'] = mode
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
			if fncSetProgress not in (False, None):
				self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(args)
		self.WORKER.start()

	def BackupROM(self, fncSetProgress=None, args=None):
		self.DoTransfer(1, fncSetProgress, args)
	
	def BackupRAM(self, fncSetProgress=None, args=None):
		if fncSetProgress is False:
			args['mode'] = 2
			args['port'] = self
			self._BackupRestoreRAM(args=args)
		else:
			self.DoTransfer(2, fncSetProgress, args)
	
	def RestoreRAM(self, fncSetProgress=None, args=None):
		self.DoTransfer(3, fncSetProgress, args)
	
	def FlashROM(self, fncSetProgress=None, args=None):
		self.DoTransfer(4, fncSetProgress, args)
	
	#################################################################

	def _BackupROM(self, args):
		file = None
		if len(args["path"]) > 0:
			file = open(args["path"], "wb")
		
		self.FAST_READ = True
		
		flashcart = False
		#is_3dmemory = False
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = copy.deepcopy(supported_carts[args["cart_type"]])
		if not isinstance(cart_type, str):
			cart_type["_index"] = 0
			for i in range(0, len(list(self.SUPPORTED_CARTS[self.MODE].keys()))):
				if i == args["cart_type"]:
					try:
						cart_type["_index"] = cart_type["names"].index(list(self.SUPPORTED_CARTS[self.MODE].keys())[i])

						fc_fncptr = {
							"cart_write_fncptr":self._cart_write,
							"cart_write_fast_fncptr":self._cart_write_flash,
							"cart_read_fncptr":self.ReadROM,
							"cart_powercycle_fncptr":self.CartPowerCycle,
							"progress_fncptr":self.SetProgress,
							"set_we_pin_wr":self._set_we_pin_wr,
							"set_we_pin_audio":self._set_we_pin_audio,
						}
						flashcart = Flashcart(config=cart_type, fncptr=fc_fncptr)
					except:
						pass

		# Firmware check L8
		if self.FW["fw_ver"] < 8 and flashcart and "enable_pullups" in cart_type:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type requires at least firmware version L8 on the GBxCart RW v1.4 hardware revision or newer. It may also work with older hardware revisions using the official firmware and insideGadgets flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>.", "abortable":False})
			return False
		# Firmware check L8

		buffer_len = 0x4000
		
		self.INFO["dump_info"]["timestamp"] = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
		self.INFO["dump_info"]["file_name"] = args["path"]
		self.INFO["dump_info"]["file_size"] = args["rom_size"]
		self.INFO["dump_info"]["cart_type"] = args["cart_type"]
		self.INFO["dump_info"]["system"] = self.MODE
		if self.MODE == "DMG":
			self.INFO["dump_info"]["rom_size"] = args["rom_size"]
			self.INFO["dump_info"]["mapper_type"] = args["mbc"]
			
			self.INFO["mapper_raw"] = args["mbc"]
			if not self.IsSupportedMbc(args["mbc"]):
				msg = "This cartridge uses a mapper that is not supported by {:s} using your {:s} device. An updated hardware revision is required.".format(Util.APPNAME, self.GetFullName())
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":msg, "abortable":False})
				return False
			
			if "verify_mbc" in args and args["verify_mbc"] is not None:
				_mbc = args["verify_mbc"]
			else:
				_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			if _mbc.GetName() == "TAMA5":
				self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
				self._set_fw_variable("DMG_READ_CS_PULSE", 1)
				_mbc.EnableMapper()
				self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			elif _mbc.GetName() == "Sachen":
				start_bank = int(args["rom_size"] / 0x4000)
				_mbc.SetStartBank(start_bank)
			else:
				_mbc.EnableMapper()
			
			rom_size = args["rom_size"]
			rom_banks = _mbc.GetROMBanks(rom_size)
			rom_bank_size = _mbc.GetROMBankSize()
			size = _mbc.GetROMSize()
			
			#if _mbc.GetName() == "Datel MegaMem":
			#	args["rom_size"] = self.INFO["dump_info"]["file_size"] = rom_size = size = _mbc.GetMaxROMSize()
		
		elif self.MODE == "AGB":
			self.INFO["dump_info"]["mapper_type"] = None
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			buffer_len = 0x10000
			size = 32 * 1024 * 1024
			if "agb_rom_size" in args: size = args["agb_rom_size"]
			self.INFO["dump_info"]["rom_size"] = size
			
			if flashcart and "flash_bank_size" in cart_type:
				if "verify_write" in args:
					rom_banks = math.ceil(len(args["verify_write"]) / cart_type["flash_bank_size"])
				else:
					rom_banks = math.ceil(size / cart_type["flash_bank_size"])
				rom_bank_size = cart_type["flash_bank_size"]
			else:
				rom_banks = 1
				rom_bank_size = 0x2000000
		
		is_3dmemory = (self.MODE == "AGB" and "command_set" in cart_type and cart_type["command_set"] == "3DMEMORY")

		if "verify_write" in args:
			size = len(args["verify_write"])
			buffer_len = min(buffer_len, size)
		else:
			if "bl_offset" in args:
				method = "SAVE_READ"
			else:
				method = "ROM_READ"
			pos = 0
			self.SetProgress({"action":"INITIALIZE", "method":method, "size":size})
			self.INFO["action"] = self.ACTIONS[method]
			if self.FW["fw_ver"] >= 8:
				if flashcart and "enable_pullups" in cart_type:
					self._write(self.DEVICE_CMD["ENABLE_PULLUPS"], wait=True)
					dprint("Pullups enabled")
				else:
					self._write(self.DEVICE_CMD["DISABLE_PULLUPS"], wait=True)
					dprint("Pullups disabled")
		
		buffer = bytearray(size)
		max_length = self.MAX_BUFFER_READ
		dprint("Max buffer size: 0x{:X}".format(max_length))
		if self.FAST_READ is True:
			if is_3dmemory:
				max_length = min(max_length, 0x1000)
			else:
				max_length = min(max_length, 0x2000)
		self.INFO["dump_info"]["transfer_size"] = max_length
		pos_total = 0
		start_address = 0
		end_address = size
		# dprint("ROM banks:", rom_banks)
		
		start_bank = 0
		if "verify_write" in args:
			buffer_pos = args["verify_from"]
			start_address = buffer_pos
			end_address = args["verify_from"] + args["verify_len"]
			start_bank = math.floor(buffer_pos / rom_bank_size)
			end_bank = math.ceil((buffer_pos + args["verify_len"]) / rom_bank_size)
			rom_banks = end_bank
		elif "bl_offset" in args:
			buffer_pos = args["bl_offset"]
			start_address = buffer_pos
			end_address = args["bl_offset"] + args["bl_size"]
			start_bank = math.floor(buffer_pos / rom_bank_size)
			end_bank = math.ceil((buffer_pos + args["bl_size"]) / rom_bank_size)
			rom_banks = end_bank

		dprint("start_address=0x{:X}, end_address=0x{:X}, start_bank=0x{:X}, rom_banks=0x{:X}, buffer_len=0x{:X}, max_length=0x{:X}".format(start_address, end_address, start_bank, rom_banks, buffer_len, max_length))
		bank = start_bank
		while bank < rom_banks:
			# ↓↓↓ Switch ROM bank
			if self.MODE == "DMG":
				if _mbc.ResetBeforeBankChange(bank) is True:
					dprint("Resetting the MBC")
					self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
				(start_address, bank_size) = _mbc.SelectBankROM(bank)
				end_address = start_address + bank_size
				buffer_len = min(buffer_len, _mbc.GetROMBankSize())
				if "verify_write" in args:
					buffer_len = min(buffer_len, bank_size, len(args["verify_write"]))
					end_address = start_address + bank_size
					start_address += (buffer_pos % rom_bank_size)
					if end_address > start_address + args["verify_len"]:
						end_address = start_address + args["verify_len"]
			elif self.MODE == "AGB":
				if "verify_write" in args:
					buffer_len = min(buffer_len, len(args["verify_write"]))
				if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] > 0:
					flashcart.SelectBankROM(bank)
					temp = end_address - start_address
					start_address %= cart_type["flash_bank_size"]
					end_address = min(cart_type["flash_bank_size"], start_address + temp)
			# ↑↑↑ Switch ROM bank

			skip_init = False
			pos = start_address
			lives = 20

			while pos < end_address:
				temp = bytearray()
				if self.CANCEL:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.ERROR_ARGS = {}
					self.SetProgress(cancel_args)
					try:
						if file is not None: file.close()
					except:
						pass
					if self.CanPowerCycleCart(): self.CartPowerCycle()
					return
				
				if is_3dmemory:
					temp = self.ReadROM_3DMemory(address=pos, length=buffer_len, max_length=max_length)
				else:
					if self.FW["fw_ver"] >= 10 and "verify_write" in args and (self.MODE != "AGB" or args["verify_base_pos"] > 0xC9):
						# Verify mode (by CRC32)
						dprint("CRC32 verification (verify_base_pos=0x{:X}, pos=0x{:X}, pos_total=0x{:X}, buffer_len=0x{:X})".format(args["verify_base_pos"], pos, pos_total, buffer_len))
						if self.MODE == "DMG":
							self._set_fw_variable("ADDRESS", pos)
						elif self.MODE == "AGB":
							self._set_fw_variable("ADDRESS", pos >> 1)
						self._write(self.DEVICE_CMD["CALC_CRC32"])
						self._write(bytearray(struct.pack(">I", buffer_len)))
						crc32_expected = zlib.crc32(args["verify_write"][pos_total:pos_total+buffer_len])
						crc32_calculated = struct.unpack(">I", self._read(4))[0]
						dprint("Expected CRC32: 0x{:X}".format(crc32_expected))
						dprint("Calculated CRC32: 0x{:X}".format(crc32_calculated))
						if crc32_expected == crc32_calculated:
							pos += buffer_len
							pos_total += buffer_len
							dprint("CRC32 verification successful between 0x{:X} and 0x{:X}".format(pos_total-buffer_len, pos_total))
							self.SetProgress({"action":"UPDATE_POS", "pos":args["verify_from"]+pos_total})
							continue
						else:
							dprint("Mismatch during CRC32 verification between 0x{:X} and 0x{:X}".format(pos_total, pos_total+buffer_len))
							temp = self.ReadROM(address=pos, length=buffer_len, skip_init=skip_init, max_length=max_length)
					else:
						# Normal read
						temp = self.ReadROM(address=pos, length=buffer_len, skip_init=skip_init, max_length=max_length)
					skip_init = True
				
				if len(temp) != buffer_len:
					pos_temp = pos_total
					if "verify_write" in args:
						pos_temp += args["verify_base_pos"]
						self.SetProgress({"action":"UPDATE_POS", "pos":args["verify_from"]+pos_total})
					else:
						self.SetProgress({"action":"UPDATE_POS", "pos":pos_total})
					
					err_text = "Note: Incomplete transfer detected. Resuming from 0x{:X}...".format(pos_temp)
					if (max_length >> 1) < 64:
						dprint("Failed to receive 0x{:X} bytes from the device at position 0x{:X}.".format(buffer_len, pos_temp))
						max_length = 64
					elif lives > 20:
						dprint("Failed to receive 0x{:X} bytes from the device at position 0x{:X}.".format(buffer_len, pos_temp))
					else:
						dprint("Failed to receive 0x{:X} bytes from the device at position 0x{:X}. Decreasing maximum transfer buffer size to 0x{:X}.".format(buffer_len, pos_temp, max_length >> 1))
						max_length >>= 1
						self.MAX_BUFFER_READ = max_length
						err_text += "\nBuffer size adjusted to {:d} bytes.".format(max_length)
					if ".dev" in Util.VERSION_PEP440 and not Util.DEBUG: print(err_text)
					
					self.INFO["dump_info"]["transfer_size"] = max_length
					skip_init = False
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					lives -= 1
					if lives == 0:
						self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"An error occured while reading from the cartridge. When connecting the device, avoid passive USB hubs and try different USB ports/cables."})
						self.CANCEL = True
						self.ERROR = True
						if "verify_write" in args: return False
					continue
				elif lives < 20:
					lives = 20
				
				if file is not None: file.write(temp)
				buffer[pos_total:pos_total+len(temp)] = temp
				pos_total += len(temp)
				
				if "verify_write" in args:
					#if pos_total >= len(args["verify_write"]): break
					check = args["verify_write"][pos_total-len(temp):pos_total]
					if Util.DEBUG:
						dprint("Writing 0x{:X} bytes to debug_verify.bin".format(len(temp)))
						with open("debug_verify.bin", "ab") as f: f.write(temp)
					
					if temp[:len(check)] != check:
						for i in range(0, pos_total):
							if (i < len(args["verify_write"]) - 1) and (i < pos_total - 1) and args["verify_write"][i] != buffer[i]:
								if args["rtc_area"] is True and i in (0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9):
									dprint("Skipping RTC area at 0x{:X}".format(i))
								else:
									dprint("Mismatch during verification at 0x{:X}".format(i))
									return i
					else:
						dprint("Verification successful between 0x{:X} and 0x{:X}".format(pos_total-len(temp), pos_total))
					self.SetProgress({"action":"UPDATE_POS", "pos":args["verify_from"]+pos_total})
				else:
					self.SetProgress({"action":"UPDATE_POS", "pos":pos_total})

				pos += buffer_len
			
			bank += 1
		
		if "verify_write" in args:
			return min(pos_total, len(args["verify_write"]))

		if not "bl_offset" in args:
			# Hidden sector (GB-Memory)
			if self.MODE == "DMG" and len(args["path"]) > 0 and _mbc.HasHiddenSector():
				file = open(os.path.splitext(args["path"])[0] + ".map", "wb")
				temp = _mbc.ReadHiddenSector()
				self.INFO["hidden_sector"] = temp
				self.INFO["dump_info"]["gbmem"] = temp
				self.INFO["dump_info"]["gbmem_parsed"] = (GBMemoryMap()).ParseMapData(buffer_map=temp, buffer_rom=buffer)
				file.write(temp)
				file.close()
				gbmp = self.INFO["dump_info"]["gbmem_parsed"]
				if (isinstance(gbmp, list)) and len(args["path"]) > 2:
					for i in range(1, len(gbmp)):
						if gbmp[i]["header"] == {} or gbmp[i]["header"]["logo_correct"] is False: continue
						settings = None
						if "settings" in args: settings = args["settings"]
						gbmp_n = Util.GenerateFileName(mode="DMG", header=gbmp[i]["header"], settings=settings)
						gbmp_p = "{:s} - {:s}".format(os.path.splitext(args["path"])[0], gbmp_n)
						with open(gbmp_p, "wb") as f:
							f.write(buffer[gbmp[i]["rom_offset"]:gbmp[i]["rom_offset"]+gbmp[i]["rom_size"]])
			else:
				if "hidden_sector" in self.INFO: del(self.INFO["hidden_sector"])
				if "gbmem" in self.INFO["dump_info"]: del(self.INFO["dump_info"]["gbmem"])
				if "gbmem_parsed" in self.INFO["dump_info"]: del(self.INFO["dump_info"]["gbmem_parsed"])
			
			# Calculate Global Checksum
			if self.MODE == "DMG":
				if _mbc.GetName() == "MMM01":
					self.INFO["dump_info"]["header"] = RomFileDMG(buffer[-0x8000:-0x8000+0x180]).GetHeader(unchanged=True)
				else:
					self.INFO["dump_info"]["header"] = RomFileDMG(buffer[:0x180]).GetHeader()
				#chk = _mbc.CalcChecksum(buffer)
				self.INFO["rom_checksum_calc"] = _mbc.CalcChecksum(buffer)
			elif self.MODE == "AGB":
				self.INFO["dump_info"]["header"] = RomFileAGB(buffer[:0x180]).GetHeader()
				#chk = self.INFO["file_crc32"]
				
				temp_ver = "N/A"
				ids = [ b"SRAM_", b"EEPROM_V", b"FLASH_V", b"FLASH512_V", b"FLASH1M_V", b"AGB_8MDACS_DL_V" ]
				for id in ids:
					temp_pos = buffer.find(id)
					if temp_pos > 0:
						temp_ver = buffer[temp_pos:temp_pos+0x20]
						temp_ver = temp_ver[:temp_ver.index(0x00)].decode("ascii", "replace")
						break
				self.INFO["dump_info"]["agb_savelib"] = temp_ver
				self.INFO["dump_info"]["agb_save_flash_id"] = None
				if "FLASH" in temp_ver:
					try:
						agb_save_flash_id = self.ReadFlashSaveID()
						if agb_save_flash_id is not False and len(agb_save_flash_id) == 2:
							self.INFO["dump_info"]["agb_save_flash_id"] = agb_save_flash_id
					except:
						print("Error querying the flash save chip.")
						self.DEVICE.reset_input_buffer()
						self.DEVICE.reset_output_buffer()
				
				if "eeprom_data" in self.INFO["dump_info"]: del(self.INFO["dump_info"]["eeprom_data"])
				if "EEPROM" in temp_ver and len(buffer) == 0x2000000:
					padding_byte = buffer[0x1FFFEFF]
					dprint("Replacing unmapped ROM data of cartridge (32 MiB ROM + EEPROM save type) with the original padding byte of 0x{:02X}.".format(padding_byte))
					self.INFO["dump_info"]["eeprom_data"] = buffer[0x1FFFF00:0x1FFFF10]
					buffer[0x1FFFF00:0x2000000] = bytearray([padding_byte] * 0x100)
					file.seek(0x1FFFF00)
					file.write(buffer[0x1FFFF00:0x2000000])

			self.INFO["file_crc32"] = zlib.crc32(buffer) & 0xFFFFFFFF
			self.INFO["file_sha1"] = hashlib.sha1(buffer).hexdigest()
			self.INFO["file_sha256"] = hashlib.sha256(buffer).hexdigest()
			self.INFO["file_md5"] = hashlib.md5(buffer).hexdigest()
			self.INFO["dump_info"]["hash_crc32"] = self.INFO["file_crc32"]
			self.INFO["dump_info"]["hash_sha1"] = self.INFO["file_sha1"]
			self.INFO["dump_info"]["hash_sha256"] = self.INFO["file_sha256"]
			self.INFO["dump_info"]["hash_md5"] = self.INFO["file_md5"]
			
			# Check for ROM loops
			self.INFO["loop_detected"] = False
			temp = min(0x2000000, len(buffer))
			while temp > 0x4000:
				temp = temp >> 1
				if (buffer[0:0x4000] == buffer[temp:temp+0x4000]):
					if buffer[0:temp] == buffer[temp:temp*2]:
						self.INFO["loop_detected"] = temp
				else:
					break

		if file is not None: file.close()
		
		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
		elif self.MODE == "AGB":
			if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] > 0:
				flashcart.SelectBankROM(0)
		# ↑↑↑ Switch to first ROM bank

		# Clean up
		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.INFO["last_path"] = args["path"]
		self.SetProgress({"action":"FINISHED"})
		return True

	def _BackupRestoreRAM(self, args):
		self.FAST_READ = False
		if "rtc" not in args: args["rtc"] = False
		
		# Prepare some stuff
		command = None
		empty_data_byte = 0x00
		extra_size = 0
		audio_low = False

		cart_type = None
		if "cart_type" in args:
			supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
			cart_type = copy.deepcopy(supported_carts[args["cart_type"]])

		if self.MODE == "DMG":
			_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
			if not self.IsSupportedMbc(args["mbc"]):
				msg = "This cartridge uses a mapper that is not supported by {:s} using your {:s} device. An updated hardware revision is required.".format(Util.APPNAME, self.GetFullName())
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":msg, "abortable":False})
				return False
			if "save_size" in args:
				save_size = args["save_size"]
			else:
				save_size = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(args["save_type"])]
			ram_banks = _mbc.GetRAMBanks(save_size)
			buffer_len = min(0x200, _mbc.GetRAMBankSize())
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)

			# Enable mappers
			if _mbc.GetName() == "TAMA5":
				self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
				self._set_fw_variable("DMG_READ_CS_PULSE", 1)
				_mbc.EnableMapper()
				self._set_fw_variable("DMG_READ_CS_PULSE", 0)
				buffer_len = 0x20
			elif _mbc.GetName() == "MBC7":
				buffer_len = save_size
			elif _mbc.GetName() == "MBC6":
				empty_data_byte = 0xFF
				audio_low = True
				self._set_fw_variable("FLASH_METHOD", 0x04) # FLASH_METHOD_DMG_MBC6
				self._set_fw_variable("FLASH_WE_PIN", 0x01) # WR
				_mbc.EnableFlash(enable=True, enable_write=True if (args["mode"] == 3) else False)
			elif _mbc.GetName() == "Xploder GB":
				empty_data_byte = 0xFF
				self._set_fw_variable("FLASH_PULSE_RESET", 0)
				self._set_fw_variable("FLASH_DOUBLE_DIE", 0)
				self._write(self.DEVICE_CMD["SET_FLASH_CMD"])
				self._write(0x00) # FLASH_COMMAND_SET_NONE
				self._write(0x01) # FLASH_METHOD_UNBUFFERED
				self._write(0x01) # FLASH_WE_PIN_WR
				commands = [
					[ 0x5555, 0xAA ],
					[ 0x2AAA, 0x55 ],
					[ 0x5555, 0xA0 ],
				]
				for i in range(0, 6):
					if i >= len(commands):
						self._write(bytearray(struct.pack(">I", 0)) + bytearray(struct.pack(">H", 0)))
					else:
						self._write(bytearray(struct.pack(">I", commands[i][0])) + bytearray(struct.pack(">H", commands[i][1])))
				self._set_fw_variable("FLASH_COMMANDS_BANK_1", 1)
				self._write(self.DEVICE_CMD["DMG_SET_BANK_CHANGE_CMD"])
				self._write(1) # number of commands
				self._write(bytearray(struct.pack(">I", 0x0006))) # address/value
				self._write(0) # type = address
				ret = self._read(1)
				if ret != 0x01:
					print("Error in DMG_SET_BANK_CHANGE_CMD:", ret)
			else:
				_mbc.EnableMapper()
			
			if args["rtc"] is True:
				extra_size = _mbc.GetRTCBufferSize()
			
			# Check for DMG-MBC5-32M-FLASH
			self._cart_write(0x2000, 0x00)
			self._cart_write(0x4000, 0x90)
			flash_id = self._cart_read(0x4000, 2)
			if flash_id == bytearray([0xB0, 0x88]): audio_low = True
			self._cart_write(0x4000, 0xF0)
			self._cart_write(0x4000, 0xFF)
			self._cart_write(0x2000, 0x01)
			if audio_low:
				dprint("DMG-MBC5-32M-FLASH Development Cartridge detected")
				self._set_fw_variable("FLASH_WE_PIN", 0x01)
			self._cart_write(0x4000, 0x00)
			
			_mbc.EnableRAM(enable=True)
		
		elif self.MODE == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			buffer_len = 0x2000
			if "save_size" in args:
				save_size = args["save_size"]
			else:
				save_size = Util.AGB_Header_Save_Sizes[args["save_type"]]
			ram_banks = math.ceil(save_size / 0x10000)
			agb_flash_chip = 0

			if args["save_type"] in (1, 2): # EEPROM
				if args["mode"] == 3:
					buffer_len = 0x40
				else:
					buffer_len = 0x100
			elif args["save_type"] in (4, 5): # FLASH
				empty_data_byte = 0xFF
				ret = self.ReadFlashSaveID()
				if ret is False:
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Couldn’t detect the save data flash chip.", "abortable":False})
					return False
				buffer_len = 0x1000
				(agb_flash_chip, _) = ret
				if agb_flash_chip in (0xBF5B, 0xFFFF): # Bootlegs
					buffer_len = 0x800
			elif args["save_type"] == 6: # DACS
				self._write(self.DEVICE_CMD["AGB_BOOTUP_SEQUENCE"], wait=True)
				empty_data_byte = 0xFF
				# Read Chip ID
				ram_banks = 1
				self._cart_write(0, 0x90)
				flash_id = self._cart_read(0, 4)
				self._cart_write(0, 0x50)
				self._cart_write(0, 0xFF)
				if flash_id != bytearray([ 0xB0, 0x00, 0x9F, 0x00 ]):
					dprint("Warning: Unknown DACS flash chip ID ({:s})".format(' '.join(format(x, '02X') for x in flash_id)))
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Couldn’t detect the DACS flash chip.\nUnknown Flash ID: {:s}".format(' '.join(format(x, '02X') for x in flash_id)), "abortable":False})
					return False
				buffer_len = 0x2000

				# ↓↓↓ Load commands into firmware
				flash_cmds = [
					[ "PA", 0x70 ],
					[ "PA", 0x10 ],
					[ "PA", "PD" ]
				]
				self._set_fw_variable("FLASH_SHARP_VERIFY_SR", 1)
				self._write(self.DEVICE_CMD["SET_FLASH_CMD"])
				self._write(0x02) # FLASH_COMMAND_SET_INTEL
				self._write(0x01) # FLASH_METHOD_UNBUFFERED
				self._write(0x00) # unset
				for i in range(0, 6):
					if i > len(flash_cmds) - 1: # skip
						self._write(bytearray(struct.pack(">I", 0)) + bytearray(struct.pack(">H", 0)))
					else:
						address = flash_cmds[i][0]
						value = flash_cmds[i][1]
						if not isinstance(address, int): address = 0
						if not isinstance(value, int): value = 0
						address >>= 1
						dprint("Setting command #{:d} to 0x{:X}=0x{:X}".format(i, address, value))
						self._write(bytearray(struct.pack(">I", address)) + bytearray(struct.pack(">H", value)))
				# ↑↑↑ Load commands into firmware
			
			# Bootleg mapper
			if cart_type is not None and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
				sram_5 = struct.unpack("B", bytes(self._cart_read(address=5, length=1, agb_save_flash=True)))[0]
				self._cart_write(address=5, value=1, sram=True)
			
			commands = [ # save type commands
				[ [None], [None] ], # No save
				[ bytearray([ self.DEVICE_CMD["AGB_CART_READ_EEPROM"], 1]), bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_EEPROM"], 1]) ], # 4K EEPROM
				[ bytearray([ self.DEVICE_CMD["AGB_CART_READ_EEPROM"], 2]), bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_EEPROM"], 2]) ], # 64K EEPROM
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], self.DEVICE_CMD["AGB_CART_WRITE_SRAM"] ], # 256K SRAM
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_FLASH_DATA"], 2 if agb_flash_chip == 0x1F3D else 1]) ], # 512K FLASH
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_FLASH_DATA"], 1]) ], # 1M FLASH
				[ False, False ], # 8M DACS
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], self.DEVICE_CMD["AGB_CART_WRITE_SRAM"] ], # 512K SRAM
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], self.DEVICE_CMD["AGB_CART_WRITE_SRAM"] ], # 1M SRAM
			]
			command = commands[args["save_type"]][args["mode"] - 2]
			
			if args["rtc"] is True:
				extra_size = 0x10
		
		if args["mode"] == 2: # Backup
			action = "SAVE_READ"
			buffer = bytearray()
		elif args["mode"] == 3: # Restore
			action = "SAVE_WRITE"
			self.INFO["save_erase"] = args["erase"]
			if args["erase"] == True:
				buffer = bytearray([ empty_data_byte ] * save_size)
				if self.MODE == "DMG" and _mbc.GetName() == "Xploder GB":
					buffer[0] = 0x00
			else:
				if args["path"] is None:
					if "buffer" in args:
						buffer = args["buffer"]
					else:
						buffer = self.INFO["data"]
				else:
					with open(args["path"], "rb") as f:
						buffer = bytearray(f.read())
				
				# Fill too small file
				if not (self.MODE == "AGB" and args["save_type"] == 6): # Not DACS
					if args["mode"] == 3:
						while len(buffer) < save_size:
							buffer += bytearray(buffer)

				if self.MODE == "AGB" and "ereader" in self.INFO and self.INFO["ereader"] is True: # e-Reader
					buffer[0xFF80:0x10000] = bytearray([0] * 0x80)
					buffer[0x1FF80:0x20000] = bytearray([0] * 0x80)
		
		# Main loop
		if not (args["mode"] == 2 and "verify_write" in args and args["verify_write"]):
			self.INFO["action"] = self.ACTIONS[action]
			self.SetProgress({"action":"INITIALIZE", "method":action, "size":save_size+extra_size})
		
		buffer_offset = 0
		for bank in range(0, ram_banks):
			if self.MODE == "DMG":
				if _mbc.GetName() == "MBC6" and bank > 7:
					self._set_fw_variable("DMG_ROM_BANK", bank - 8)
					(start_address, bank_size) = _mbc.SelectBankFlash(bank - 8)
					end_address = start_address + bank_size
					buffer_len = 0x2000
					if args["mode"] == 3: # Restore
						if ((buffer_offset - 0x8000) % 0x20000) == 0:
							dprint("Erasing flash sector at position 0x{:X}".format(buffer_offset))
							_mbc.EraseFlashSector()
				elif _mbc.GetName() == "Xploder GB":
					self._set_fw_variable("DMG_ROM_BANK", bank + 8)
					(start_address, bank_size) = _mbc.SelectBankRAM(bank)
					end_address = min(save_size, start_address + bank_size)
				else:
					self._set_fw_variable("DMG_WRITE_CS_PULSE", 1 if _mbc.WriteWithCSPulse() else 0)
					(start_address, bank_size) = _mbc.SelectBankRAM(bank)
					end_address = min(save_size, start_address + bank_size)
			elif self.MODE == "AGB":
				start_address = 0
				bank_size = 0x10000
				if args["save_type"] == 6: # DACS
					bank_size = min(save_size, 0x100000)
					buffer_len = 0x2000
				
				end_address = min(save_size, bank_size)
				
				if save_size > bank_size:
					if args["save_type"] == 8 or agb_flash_chip in (0xBF5B, 0xFFFF): # Bootleg 1M
						dprint("Switching to bootleg save bank {:d}".format(bank))
						self._cart_write(0x1000000, bank)
					elif args["save_type"] == 5: # FLASH 1M
						dprint("Switching to FLASH bank {:d}".format(bank))
						cmds = [
							[ 0x5555, 0xAA ],
							[ 0x2AAA, 0x55 ],
							[ 0x5555, 0xB0 ],
							[ 0, bank ]
						]
						self._cart_write_flash(cmds)
					else:
						dprint("Unknown bank switching method")
					time.sleep(0.05)
			
			max_length = 64
			dprint("start_address=0x{:X}, end_address=0x{:X}, buffer_len=0x{:X}, buffer_offset=0x{:X}".format(start_address, end_address, buffer_len, buffer_offset))
			pos = start_address
			while pos < end_address:
				if self.CANCEL:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.ERROR_ARGS = {}
					self.SetProgress(cancel_args)
					if self.CanPowerCycleCart(): self.CartPowerCycle()
					return
				
				if args["mode"] == 2: # Backup
					in_temp = [None] * 2
					if "verify_read" in args and args["verify_read"]: # Read twice for detecting instabilities
						xe = 2
					else:
						xe = 1
					for x in range(0, xe):
						if x == 1:
							self.NO_PROG_UPDATE = True
						else:
							self.NO_PROG_UPDATE = False
						
						if self.MODE == "DMG" and _mbc.GetName() == "MBC7":
							in_temp[x] = self.ReadRAM_MBC7(address=pos, length=buffer_len)
						elif self.MODE == "DMG" and _mbc.GetName() == "MBC6" and bank > 7: # MBC6 flash save memory
							in_temp[x] = self.ReadROM(address=pos, length=buffer_len, skip_init=False, max_length=max_length)
						elif self.MODE == "DMG" and _mbc.GetName() == "TAMA5":
							in_temp[x] = self.ReadRAM_TAMA5()
						elif self.MODE == "DMG" and _mbc.GetName() == "Xploder GB":
							in_temp[x] = self.ReadROM(address=0x20000+pos, length=buffer_len, skip_init=False, max_length=max_length)
						elif self.MODE == "AGB" and args["save_type"] in (1, 2): # EEPROM
							in_temp[x] = self.ReadRAM(address=int(pos/8), length=buffer_len, command=command, max_length=max_length)
						elif self.MODE == "AGB" and args["save_type"] == 6: # DACS
							in_temp[x] = self.ReadROM(address=0x1F00000+pos, length=buffer_len, skip_init=False, max_length=max_length)
						elif self.MODE == "DMG" and _mbc.GetName() == "MBC2":
							in_temp[x] = self.ReadRAM(address=pos, length=buffer_len, command=command, max_length=max_length)
							for i in range(0, len(in_temp[x])):
								in_temp[x][i] = in_temp[x][i] & 0x0F
						else:
							in_temp[x] = self.ReadRAM(address=pos, length=buffer_len, command=command, max_length=max_length)

						if len(in_temp[x]) != buffer_len:
							if (max_length >> 1) < 64:
								dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}!".format(len(in_temp[x]), buffer_len, len(buffer)))
								max_length = 64
							else:
								dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}! Decreasing maximum transfer buffer length to 0x{:X}.".format(len(in_temp[x]), buffer_len, len(buffer), max_length >> 1))
								max_length >>= 1
							self.DEVICE.reset_input_buffer()
							self.DEVICE.reset_output_buffer()
							continue
					
					if xe == 2 and in_temp[0] != in_temp[1]:
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Failed to read save data consistently. Please ensure that the cartridge contacts are clean.", "abortable":False})
						return False
					
					temp = in_temp[0]
					buffer += temp
					self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)})
				
				elif args["mode"] == 3: # Restore
					if self.MODE == "DMG" and _mbc.GetName() == "MBC7":
						self.WriteEEPROM_MBC7(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
					elif self.MODE == "DMG" and _mbc.GetName() == "MBC6" and bank > 7: # MBC6 flash save memory
						if self.FW["pcb_ver"] in (5, 6, 101):
							self.WriteROM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
							self._cart_write(pos + buffer_len - 1, 0xF0)
						else:
							self.WriteFlash_MBC6(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], mapper=_mbc)
					elif self.MODE == "DMG" and _mbc.GetName() == "TAMA5":
						self.WriteRAM_TAMA5(buffer=buffer[buffer_offset:buffer_offset+buffer_len])
					elif self.MODE == "DMG" and _mbc.GetName() == "Xploder GB":
						self.WriteROM_DMG_EEPROM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], bank=bank+8)
					elif self.MODE == "AGB" and args["save_type"] in (1, 2): # EEPROM
						self.WriteRAM(address=int(pos/8), buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					elif self.MODE == "AGB" and args["save_type"] in (4, 5): # FLASH
						sector_address = pos % 0x10000
						if agb_flash_chip == 0x1F3D: # Atmel AT29LV512
							self.WriteRAM(address=int(pos/128), buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
						else:
							dprint("Erasing flash save sector; pos=0x{:X}, sector_address=0x{:X}".format(pos, sector_address))
							cmds = [
								[ 0x5555, 0xAA ],
								[ 0x2AAA, 0x55 ],
								[ 0x5555, 0x80 ],
								[ 0x5555, 0xAA ],
								[ 0x2AAA, 0x55 ],
								[ sector_address, 0x30 ]
							]
							self._cart_write_flash(cmds)
							sr = 0
							lives = 50
							while True:
								time.sleep(0.01)
								sr = self._cart_read(sector_address, agb_save_flash=True)
								dprint("Data Check: 0x{:X} == 0xFFFF? {:s}".format(sr, str(sr == 0xFFFF)))
								if sr == 0xFFFF: break
								lives -= 1
								if lives == 0:
									errmsg = "Warning: Save data flash sector at 0x{:X} didn’t erase successfully (SR={:04X}).".format(bank*0x10000 + pos, sr)
									print(errmsg)
									dprint(errmsg)
									break
							if buffer[buffer_offset:buffer_offset+buffer_len] != bytearray([0xFF] * buffer_len):
								if ("ereader" in self.INFO and self.INFO["ereader"] is True and sector_address == 0xF000):
									self.WriteRAM(address=pos, buffer=buffer[buffer_offset:buffer_offset+0xF80], command=command, max_length=0x80)
								else:
									self.WriteRAM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					elif self.MODE == "AGB" and args["save_type"] == 6: # DACS
						sector_address = pos + 0x1F00000
						if sector_address in (0x1F00000, 0x1F10000, 0x1F20000, 0x1F30000, 0x1F40000, 0x1F50000, 0x1F60000, 0x1F70000, 0x1F80000, 0x1F90000, 0x1FA0000, 0x1FB0000, 0x1FC0000, 0x1FD0000, 0x1FE0000, 0x1FF0000, 0x1FF2000, 0x1FF4000, 0x1FF6000, 0x1FF8000, 0x1FFA000, 0x1FFC000):
							dprint("DACS: Now at sector 0x{:X}".format(sector_address))
							cmds = [
								[ # Erase Sector
									[ 0, 0x50 ],
									[ sector_address, 0x20 ],
									[ sector_address, 0xD0 ],
								]
							]
							if sector_address == 0x1F00000: # First write
								temp = [
									[ # Unlock
										[ 0, 0x50 ],
										[ 0, 0x60 ],
										[ 0, 0xD0 ],
									]
								]
								temp.extend(cmds)
								cmds = temp
							elif sector_address == 0x1FFC000: # Boot sector
								temp = [
									[ # Unlock 1
										[ 0, 0x50 ],
										[ 0, 0x60 ],
										[ 0, 0xD0 ],
									],
									[ # Unlock 2
										[ 0, 0x50 ],
										[ sector_address, 0x60 ],
										[ sector_address, 0xDC ],
									]
								]
								temp.extend(cmds)
								cmds = temp
							
							for cmd in cmds:
								dprint("Executing DACS commands:", cmd)
								self._cart_write_flash(commands=cmd, flashcart=True)
								sr = 0
								lives = 20
								while True:
									time.sleep(0.1)
									sr = struct.unpack("<H", self._cart_read(sector_address, 2))[0]
									dprint("DACS: Status Register Check: 0x{:X} == 0x80? {:s}".format(sr, str(sr & 0xE0 == 0x80)))
									if sr & 0xE0 == 0x80: break
									lives -= 1
									if lives == 0:
										self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error occured while writing to the DACS cartridge. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.", "abortable":False})
										return False
						if sector_address < 0x1FFE000:
							dprint("DACS: Writing to area 0x{:X}–0x{:X}".format(0x1F00000+pos, 0x1F00000+pos+buffer_len-1))
							self.WriteROM(address=0x1F00000+pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
						else:
							dprint("DACS: Skipping read-only area 0x{:X}–0x{:X}".format(0x1F00000+pos, 0x1F00000+pos+buffer_len-1))
					else:
						self.WriteRAM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					self.SetProgress({"action":"UPDATE_POS", "pos":buffer_offset+buffer_len})
				
				pos += buffer_len
				buffer_offset += buffer_len
		
		verified = False
		if args["mode"] == 2: # Backup
			self.INFO["transferred"] = len(buffer)
			rtc_buffer = None
			# Real Time Clock
			if args["rtc"] is True:
				self.NO_PROG_UPDATE = True
				if self.MODE == "DMG" and args["rtc"] is True:
					_mbc.LatchRTC()
					rtc_buffer = _mbc.ReadRTC()
				elif self.MODE == "AGB":
					_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
					rtc_buffer = _agb_gpio.ReadRTC()
				self.NO_PROG_UPDATE = False
				self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)+len(rtc_buffer)})
			
			# Bootleg mapper
			if self.MODE == "AGB" and cart_type is not None and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
				buffer[5] = sram_5
			
			if args["path"] is not None:
				if self.MODE == "DMG" and _mbc.GetName() == "MBC2":
					for i in range(0, len(buffer)):
						buffer[i] = buffer[i] & 0x0F
				file = open(args["path"], "wb")
				file.write(buffer)
				if rtc_buffer is not None:
					file.write(rtc_buffer)
				file.close()
			else:
				self.INFO["data"] = buffer
			
			self.INFO["file_crc32"] = zlib.crc32(buffer) & 0xFFFFFFFF
			self.INFO["file_sha1"] = hashlib.sha1(buffer).hexdigest()

			if "verify_write" in args and args["verify_write"] not in (None, False):
				return True
		
		elif args["mode"] == 3: # Restore
			self.INFO["transferred"] = len(buffer)
			if args["rtc"] is True:
				advance = "rtc_advance" in args and args["rtc_advance"]
				self.SetProgress({"action":"UPDATE_RTC", "method":"write"})
				if self.MODE == "DMG" and args["rtc"] is True:
					_mbc.WriteRTC(buffer[-_mbc.GetRTCBufferSize():], advance=advance)
				elif self.MODE == "AGB":
					_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
					_agb_gpio.WriteRTC(buffer[-0x10:], advance=advance)
				self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)})

			# ↓↓↓ Write verify
			if "verify_write" in args and args["verify_write"] is True and args["erase"] is not True:
				if self.MODE == "DMG": _mbc.SelectBankRAM(0)
				self.SetProgress({"action":"INITIALIZE", "method":"SAVE_WRITE_VERIFY", "size":buffer_offset})

				verify_args = copy.copy(args)
				start_address = 0
				end_address = buffer_offset
				if self.MODE == "AGB" and args["save_type"] == 6: # DACS
					end_address = min(len(buffer), 0xFE000)

				path = args["path"] # backup path
				verify_args.update({"mode":2, "verify_write":buffer, "path":None})
				self.ReadROM(0, 4) # dummy read
				self.INFO["data"] = None
				if self._BackupRestoreRAM(verify_args) is False: return

				if args["mbc"] == 6: # MBC2
					for i in range(0, len(self.INFO["data"])):
						self.INFO["data"][i] &= 0x0F
						buffer[i] &= 0x0F

				args["path"] = path # restore path
				if self.CANCEL is True:
					pass
				elif (self.INFO["data"][:end_address] != buffer[:end_address]):
					msg = ""
					count = 0
					for i in range(0, len(self.INFO["data"])):
						if i >= len(buffer): break
						data1 = self.INFO["data"][i]
						data2 = buffer[:end_address][i]
						if data1 != data2:
							count += 1
							if len(msg.split("\n")) <= 10:
								msg += "- 0x{:06X}: {:02X}≠{:02X}\n".format(i, data1, data2)
							elif len(msg.split("\n")) == 11:
								msg += "(more than 10 differences found)\n"
							else:
								pass
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The save data was written completely, but {:d} byte(s) ({:.2f}%) didn’t pass the verification check.\n\n{:s}".format(count, (count / len(self.INFO["data"]) * 100), msg[:-1]), "abortable":False})
					return False
				else:
					verified = True
			# ↑↑↑ Write verify
		
		if self.MODE == "DMG":
			_mbc.SelectBankRAM(0)
			_mbc.EnableRAM(enable=False)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			if audio_low: self._set_fw_variable("FLASH_WE_PIN", 0x02)
			self._write(self.DEVICE_CMD["SET_ADDR_AS_INPUTS"]) # Prevent hotplugging corruptions on rare occasions
		
		# Bootleg mapper
		elif self.MODE == "AGB" and cart_type is not None and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
			self._cart_write(address=5, value=0, sram=True)
			self._cart_write(address=5, value=sram_5, sram=True)

		# Clean up
		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.INFO["last_path"] = args["path"]
		self.SetProgress({"action":"FINISHED", "verified":verified})
		return True
	
	def _FlashROM(self, args):
		self.FAST_READ = True
		if "buffer" in args:
			data_import = args["buffer"]
		else:
			with open(args["path"], "rb") as file: data_import = bytearray(file.read())
		
		flash_offset = 0 # Batteryless SRAM or Transfer Resume
		if "flash_offset" in args:
			flash_offset = args["flash_offset"]
		if "start_addr" in args and args["start_addr"] > 0:
			data_import = bytearray(b'\xFF' * args["start_addr"]) + data_import
		
		# Pad data
		if len(data_import) > 0:
			if len(data_import) < 0x400:
				data_import += bytearray([0xFF] * (0x400 - len(data_import)))
			if len(data_import) % 0x8000 > 0:
				data_import += bytearray([0xFF] * (0x8000 - len(data_import) % 0x8000))
			
			# Skip writing the last 256 bytes of 32 MiB ROMs with EEPROM save type
			if self.MODE == "AGB" and len(data_import) == 0x2000000:
				temp_ver = "N/A"
				ids = [ b"SRAM_", b"EEPROM_V", b"FLASH_V", b"FLASH512_V", b"FLASH1M_V", b"AGB_8MDACS_DL_V" ]
				for id in ids:
					temp_pos = data_import.find(id)
					if temp_pos > 0:
						temp_ver = data_import[temp_pos:temp_pos+0x20]
						temp_ver = temp_ver[:temp_ver.index(0x00)].decode("ascii", "replace")
						break
				if "EEPROM" in temp_ver:
					print("Note: The last 256 bytes of this 32 MiB ROM will not be written as this area is reserved by the EEPROM save type.")
					data_import = data_import[:0x1FFFF00]
		
		# Fix bootlogo and header
		if "fix_bootlogo" in args and isinstance(args["fix_bootlogo"], bytearray):
			dstr = ''.join(format(x, '02X') for x in args["fix_bootlogo"])
			dprint("Replacing bootlogo data with", dstr)
			if self.MODE == "DMG":
				data_import[0x104:0x134] = args["fix_bootlogo"]
			elif self.MODE == "AGB":
				data_import[0x04:0xA0] = args["fix_bootlogo"]
		if "fix_header" in args and args["fix_header"]:
			dprint("Fixing header checksums")
			if self.MODE == "DMG":
				temp = RomFileDMG(data_import[0:0x200]).FixHeader()
			elif self.MODE == "AGB":
				temp = RomFileAGB(data_import[0:0x200]).FixHeader()
			data_import[0:0x200] = temp
		
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = copy.deepcopy(supported_carts[args["cart_type"]])
		if cart_type == "RETAIL": return False # Generic ROM Cartridge is not flashable
		
		# Special carts
		if "Retrostage GameBoy Blaster" in cart_type["names"]:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The Retrostage GameBoy Blaster cartridge is currently not fully supported by FlashGBX. However, you can use the insideGadgets “Flasher” software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> to flash this cartridge.", "abortable":False})
			return False
		elif "insideGadgets Power Cart 1 MB, 128 KB SRAM" in cart_type["names"]:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The insideGadgets Power Cart is currently not fully supported by FlashGBX. However, you can use the dedicated insideGadgets “iG Power Cart Programs” software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> to flash this cartridge.", "abortable":False})
			return False
		elif "power_cycle" in cart_type and cart_type["power_cycle"] is True and not self.CanPowerCycleCart():
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is not flashable using FlashGBX and your GBxCart RW hardware revision due to missing cartridge power cycling support.", "abortable":False})
			return False
		# Special carts
		# Firmware check L1
		if cart_type["type"] == "DMG" and "write_pin" in cart_type and cart_type["write_pin"] == "WR+RESET":
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported by FlashGBX. Please try the insideGadgets GBxCart RW flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> instead.", "abortable":False})
			return False
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 2) and ("pulse_reset_after_write" in cart_type and cart_type["pulse_reset_after_write"] is True):
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is not supported by FlashGBX using your GBxCart RW hardware revision and/or firmware version. You can also try the official GBxCart RW firmware and interface software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> instead.", "abortable":False})
			return False
		# Firmware check L1
		# Firmware check L2
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 3) and ("command_set" in cart_type and cart_type["command_set"] == "SHARP") and ("buffer_write" in cart_type["commands"]):
			if self.FW["pcb_ver"] in (5, 6):
				print("Note: Update your GBxCart RW firmware to version L3 or higher for a better transfer rate with this cartridge.")
			del(cart_type["commands"]["buffer_write"])
		# Firmware check L2
		# Firmware check L5
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 5) and ("flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True):
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type requires at least firmware version L5 on the GBxCart RW v1.4 hardware revision or newer. It may also work with older hardware revisions using the official firmware and insideGadgets flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>.", "abortable":False})
			return False
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 5) and ("double_die" in cart_type and cart_type["double_die"] is True):
			if self.FW["pcb_ver"] in (5, 6):
				print("Note: Update your GBxCart RW firmware to version L5 or higher for a better transfer rate with this cartridge.")
			del(cart_type["commands"]["buffer_write"])
		# Firmware check L5
		# Firmware check L8
		if self.FW["fw_ver"] < 8 and "enable_pullups" in cart_type and cart_type["enable_pullups"] is True:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type requires at least firmware version L8 on the GBxCart RW v1.4 hardware revision or newer. It may also work with older hardware revisions using the official firmware and insideGadgets flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>.", "abortable":False})
			return False
		# Firmware check L8

		cart_type["_index"] = 0
		for i in range(0, len(list(self.SUPPORTED_CARTS[self.MODE].keys()))):
			if i == args["cart_type"]:
				try:
					cart_type["_index"] = cart_type["names"].index(list(self.SUPPORTED_CARTS[self.MODE].keys())[i])
				except:
					pass
		
		fc_fncptr = {
			"cart_write_fncptr":self._cart_write,
			"cart_write_fast_fncptr":self._cart_write_flash,
			"cart_read_fncptr":self.ReadROM,
			"cart_powercycle_fncptr":self.CartPowerCycle,
			"progress_fncptr":self.SetProgress,
			"set_we_pin_wr":self._set_we_pin_wr,
			"set_we_pin_audio":self._set_we_pin_audio,
		}
		if cart_type["command_set"] == "GBMEMORY":
			flashcart = Flashcart_DMG_MMSA(config=cart_type, fncptr=fc_fncptr)
		else:
			flashcart = Flashcart(config=cart_type, fncptr=fc_fncptr)
		
		rumble = "rumble" in flashcart.CONFIG and flashcart.CONFIG["rumble"] is True
		
		# ↓↓↓ Set Voltage
		if args["override_voltage"] is not False:
			if args["override_voltage"] == 5:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			else:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
		elif flashcart.GetVoltage() == 3.3:
			self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
		elif flashcart.GetVoltage() == 5:
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
		# ↑↑↑ Set Voltage
		
		# ↓↓↓ Pad data for full chip erase on sector erase mode
		if not flashcart.SupportsChipErase() and flashcart.SupportsSectorErase() and args["prefer_chip_erase"]:
			print("{:s}Note: Chip erase mode is not supported for this flash cartridge type. Sector erase mode will be used.{:s}\n".format(ANSI.YELLOW, ANSI.RESET))
			flash_size = flashcart.GetFlashSize()
			if flash_size is not False and len(data_import) < flash_size:
				# Pad with FF till the end (with MemoryError fix)
				pad_len = flash_size - len(data_import)
				while pad_len > 0x2000000:
					data_import += bytearray([0xFF] * 0x2000000)
					pad_len -= 0x2000000
				data_import += bytearray([0xFF] * (flash_size - len(data_import)))
		# ↑↑↑ Pad data for full chip erase on sector erase mode
		
		# ↓↓↓ Flashcart configuration
		_mbc = None
		errmsg_mbc_selection = ""
		if self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			mbc = flashcart.GetMBC()
			if mbc is not False and isinstance(mbc, int):
				args["mbc"] = mbc
				dprint("Using forced mapper type 0x{:02X} for flashing".format(mbc))
			elif mbc == "manual":
				dprint("Using manually selected mapper type 0x{:02X} for flashing".format(args["mbc"]))
			else:
				args["mbc"] = 0
				dprint("Using default mapper type 0x{:02X} for flashing".format(args["mbc"]))
			if args["mbc"] == 0: args["mbc"] = 0x19 # MBC5 default

			if not self.IsSupportedMbc(args["mbc"]):
				msg = "This cartridge uses a mapper that is not supported by {:s} using your {:s} device. An updated hardware revision is required.".format(Util.APPNAME, self.GetFullName())
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":msg, "abortable":False})
				return False
			
			_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)

			self._set_fw_variable("FLASH_PULSE_RESET", 1 if flashcart.PulseResetAfterWrite() else 0)

			end_bank = math.ceil(len(data_import) / _mbc.GetROMBankSize())
			rom_bank_size = _mbc.GetROMBankSize()

			_mbc.EnableMapper()

			if flashcart.GetMBC() == "manual":
				errmsg_mbc_selection += "\n- Check mapper type used: {:s} (manual selection)".format(_mbc.GetName())
			else:
				errmsg_mbc_selection += "\n- Check mapper type used: {:s} (forced by selected cartridge type)".format(_mbc.GetName())
			if len(data_import) > _mbc.GetMaxROMSize():
				errmsg_mbc_selection += "\n- Check mapper type ROM size limit: likely up to {:s}".format(Util.formatFileSize(size=_mbc.GetMaxROMSize()))

		elif self.MODE == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			if flashcart and "flash_bank_size" in cart_type:
				end_bank = math.ceil(len(data_import) / cart_type["flash_bank_size"])
			else:
				end_bank = 1
			if flashcart and "flash_bank_size" in cart_type:
				rom_bank_size = cart_type["flash_bank_size"]
			else:
				rom_bank_size = 0x2000000
		
		flash_buffer_size = flashcart.GetBufferSize()

		if self.FW["fw_ver"] >= 8:
			if "enable_pullups" in cart_type:
				self._write(self.DEVICE_CMD["ENABLE_PULLUPS"], wait=True)
				dprint("Pullups enabled")
			else:
				self._write(self.DEVICE_CMD["DISABLE_PULLUPS"], wait=True)
				dprint("Pullups disabled")
		# ↑↑↑ Flashcart configuration

		# ↓↓↓ DMG-MMSA-JPN hidden sector
		if self.MODE == "DMG" and _mbc.GetName() == "G-MMC1":
			if "buffer_map" not in args:
				if os.path.exists(os.path.splitext(args["path"])[0] + ".map"):
					with open(os.path.splitext(args["path"])[0] + ".map", "rb") as file: args["buffer_map"] = file.read()
				else:
					temp = data_import
					if len(temp) == 0: temp = bytearray([0xFF] * 0x180)
					try:
						gbmem = GBMemoryMap(rom=temp, oldmap=_mbc.ReadHiddenSector())
						args["buffer_map"] = gbmem.GetMapData()
					except Exception:
						print(traceback.format_exc())
						print("{:s}An error occured while trying to generate the hidden sector data for the NP GB-Memory cartridge.{:s}".format(ANSI.RED, ANSI.RESET))
						args["buffer_map"] = False
					
					if args["buffer_map"] is False:
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The NP GB-Memory Cartridge requires extra hidden sector data. As it couldn’t be auto-generated, please provide your own at the following path: {:s}".format(os.path.splitext(args["path"])[0] + ".map"), "abortable":False})
						return False
					else:
						dprint("Generated hidden sector data:", args["buffer_map"])
						if Util.DEBUG:
							with open("debug_mmsa_map.bin", "wb") as f: f.write(args["buffer_map"])
			data_map_import = copy.copy(args["buffer_map"])
			data_map_import = bytearray(data_map_import)
			dprint("Hidden sector data loaded")
		# ↑↑↑ DMG-MMSA-JPN hidden sector

		# ↓↓↓ Load commands into firmware
		flash_cmds = []
		command_set_type = flashcart.GetCommandSetType()
		temp = 0
		if command_set_type == "AMD":
			temp = 0x01
			#self._write(0x01) # FLASH_COMMAND_SET_AMD
			#self._set_fw_variable("FLASH_SHARP_VERIFY_SR", 0)
			dprint("Using AMD command set")
		elif command_set_type == "INTEL":
			temp = 0x02
			#self._write(0x02) # FLASH_COMMAND_SET_INTEL
			self._set_fw_variable("FLASH_SHARP_VERIFY_SR", 0)
			dprint("Using Intel command set")
		elif command_set_type == "SHARP":
			temp = 0x02
			#self._write(0x02) # FLASH_COMMAND_SET_INTEL
			self._set_fw_variable("FLASH_SHARP_VERIFY_SR", 1)
			dprint("Using Sharp/Intel command set")
		elif command_set_type in ("GBMEMORY", "DMG-MBC5-32M-FLASH"):
			temp = 0x00
			dprint("Using GB-Memory command set")
		elif command_set_type in ("BLAZE_XPLODER", "DATEL_ORBITV2"):
			temp = 0x00
		else:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported for ROM flashing.", "abortable":False})
			return False
		
		if flashcart.HasDoubleDie() and self.FW["pcb_ver"] in (5, 6, 101) and self.FW["fw_ver"] >= 5:
			self._set_fw_variable("FLASH_DOUBLE_DIE", 1)
		else:
			self._set_fw_variable("FLASH_DOUBLE_DIE", 0)

		if command_set_type == "GBMEMORY" and self.FW["pcb_ver"] not in (5, 6, 101):
			self._set_fw_variable("FLASH_WE_PIN", 0x01)
			dprint("Using GB-Memory mode on GBxCart RW v1.3")
		elif command_set_type == "DMG-MBC5-32M-FLASH":
			self._set_fw_variable("FLASH_WE_PIN", 0x02)
		else:
			self._write(self.DEVICE_CMD["SET_FLASH_CMD"])
			self._write(temp)

			if flashcart.IsF2A():
				self._write(0x05) # FLASH_METHOD_AGB_FLASH2ADVANCE
				flash_cmds = [
					[ "SA", 0xE8 ],
					[ "SA", "BS" ],
					[ "PA", "PD" ],
					[ "SA", 0xD0 ],
					[ "SA", 0xFF ]
				]
				dprint("Using Flash2Advance mode with a buffer of {:d} bytes".format(flash_buffer_size))
			elif command_set_type == "GBMEMORY" and self.FW["pcb_ver"] in (5, 6, 101):
				self._write(0x03) # FLASH_METHOD_DMG_MMSA
				dprint("Using GB-Memory mode on GBxCart RW v1.4")
			elif flashcart.SupportsBufferWrite() and flash_buffer_size > 0:
				self._write(0x02) # FLASH_METHOD_BUFFERED
				flash_cmds = flashcart.GetCommands("buffer_write")
				dprint("Using buffered writing with a buffer of {:d} bytes".format(flash_buffer_size))
			elif flashcart.SupportsSingleWrite():
				self._write(0x01) # FLASH_METHOD_UNBUFFERED
				flash_cmds = flashcart.GetCommands("single_write")
				dprint("Using single writing")
			else:
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported for ROM flashing.", "abortable":False})
				return False
			
			if flashcart.WEisWR():
				we = 0x01 # FLASH_WE_PIN_WR
				self._write(we)
				dprint("Using WR as WE")
			elif flashcart.WEisAUDIO():
				we = 0x02 # FLASH_WE_PIN_AUDIO
				self._write(we)
				dprint("Using AUDIO as WE")
			elif flashcart.WEisWR_RESET():
				we = 0x03 # FLASH_WE_PIN_WR_RESET
				self._write(we) # FLASH_WE_PIN_WR_RESET
				dprint("Using WR+RESET as WE")
			else:
				we = 0x00
				self._write(we) # unset
			
			for i in range(0, 6):
				if i > len(flash_cmds) - 1: # skip
					self._write(bytearray(struct.pack(">I", 0)) + bytearray(struct.pack(">H", 0)))
				else:
					address = flash_cmds[i][0]
					value = flash_cmds[i][1]
					if not isinstance(address, int): address = 0
					if not isinstance(value, int): value = 0
					if self.MODE == "AGB": address >>= 1
					dprint("Setting command #{:d} to 0x{:X}=0x{:X}".format(i, address, value))
					self._write(bytearray(struct.pack(">I", address)) + bytearray(struct.pack(">H", value)))
			
			if self.FW["fw_ver"] >= 6:
				if "flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True:
					self._set_fw_variable("FLASH_COMMANDS_BANK_1", 1)
					self._write(self.DEVICE_CMD["DMG_SET_BANK_CHANGE_CMD"])
					if "bank_switch" in cart_type["commands"]:
						self._write(len(cart_type["commands"]["bank_switch"])) # number of commands
						for command in cart_type["commands"]["bank_switch"]:
							address = command[0]
							value = command[1]
							if value == "ID":
								self._write(bytearray(struct.pack(">I", address))) # address
								self._write(0) # type = address
							else:
								self._write(bytearray(struct.pack(">I", value))) # value
								self._write(1) # type = value
						ret = self._read(1)
						if ret != 0x01:
							print("Error in DMG_SET_BANK_CHANGE_CMD:", ret)
					else:
						self._write(0, wait=True)
				else:
					self._set_fw_variable("FLASH_COMMANDS_BANK_1", 0)
					self._write(self.DEVICE_CMD["DMG_SET_BANK_CHANGE_CMD"])
					self._write(0, wait=True)
			else:
				if "flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True:
					self._set_fw_variable("FLASH_COMMANDS_BANK_1", 1)
				else:
					self._set_fw_variable("FLASH_COMMANDS_BANK_1", 0)
		# ↑↑↑ Load commands into firmware

		# ↓↓↓ Preparations
		if self.MODE == "DMG" and "flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True:
			dprint("Setting ROM bank 1")
			_mbc.SelectBankROM(1)
		# ↑↑↑ Preparations
		
		# ↓↓↓ Read Flash ID
		if "flash_ids" in cart_type:
			(verified, flash_id) = flashcart.VerifyFlashID()
			if not verified and not command_set_type == "BLAZE_XPLODER":
				print("Note: This cartridge’s Flash ID ({:s}) doesn’t match the cartridge type selection.".format(' '.join(format(x, '02X') for x in flash_id)))
		else:
			if flashcart.Unlock() is False: return False
		# ↑↑↑ Read Flash ID
		
		# ↓↓↓ Read Sector Map
		sector_map = flashcart.GetSectorMap()
		smallest_sector_size = 0x2000
		sector_offsets = []
		write_sectors = None
		sector_pos = 0
		delta_state_new = None
		flash_capacity = len(data_import)
		if sector_map is not None and sector_map is not False:
			smallest_sector_size = flashcart.GetSmallestSectorSize()
			sector_offsets = flashcart.GetSectorOffsets(rom_size=flashcart.GetFlashSize(default=len(data_import)), rom_bank_size=rom_bank_size)
			if len(sector_offsets) > 0:
				flash_capacity = sector_offsets[-1][0] + sector_offsets[-1][1]
				if flash_capacity < len(data_import) and not (flashcart.SupportsChipErase() and args["prefer_chip_erase"]):
					#self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"There are not enough flash sectors available to write this ROM. The maximum capacity is {:s}.".format(Util.formatFileSize(size=flash_capacity, asInt=False)), "abortable":False})
					#return False
					sector_offsets = flashcart.GetSectorOffsets(rom_size=len(data_import), rom_bank_size=rom_bank_size)

			sector_offsets_hash = base64.urlsafe_b64encode(hashlib.sha1(str(sector_offsets).encode("UTF-8")).digest()).decode("ASCII", "ignore")[:4]

			# Delta flashing
			if len(sector_offsets) > 1:
				splitext = os.path.splitext(args["path"])
				if splitext[0].endswith(".delta") and os.path.exists(splitext[0][:-6] + splitext[1]):
					delta_state_new = []
					with open(splitext[0][:-6] + splitext[1], "rb") as f:
						for i in range(0, len(sector_offsets)):
							s_from = sector_offsets[i][0]
							s_size = sector_offsets[i][1]
							s_to = s_from + s_size
							if data_import[s_from:s_to] != f.read(s_to - s_from):
								x = [ s_from, s_size, zlib.crc32(data_import[s_from:s_to]) & 0xFFFFFFFF ]
								delta_state_new.append(x)
								dprint("Sector differs:", x)
					write_sectors = copy.copy(delta_state_new)
					json_file = "{:s}_{:s}.json".format(splitext[0], sector_offsets_hash)
					if os.path.exists(json_file):
						with open(json_file, "rb") as f:
							try:
								delta_state_old = json.loads(f.read().decode("UTF-8-SIG"))
							except:
								delta_state_old = []
							if len(delta_state_old) > 0:
								for x in delta_state_old:
									if x in write_sectors:
										del(write_sectors[write_sectors.index(x)])
										dprint("Skipping sector:", x)
									else:
										write_sectors2 = []
										for y in write_sectors: write_sectors2.append(y[:-1])
										if x[:-1] not in write_sectors2:
											write_sectors.append(x)
											dprint("Forcing sector:", x)
					
					if len(write_sectors) == 0:
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"No flash sectors were found that would need to be updated for delta flashing.", "abortable":False})
						return False

				elif "flash_sectors" in args and len(args["flash_sectors"]) > 0:
					write_sectors = args["flash_sectors"]

				elif flash_offset > 0: # Batteryless SRAM
					if "flash_size" not in args:
						flash_size = len(data_import) - flash_offset
					else:
						flash_size = args["flash_size"]
						data_import = data_import[:flash_size]
					bl_sectors = []
					for sector in sector_offsets:
						if flash_offset > sector[0]: continue
						#if len(bl_sectors) > 0 and (flash_offset + flash_size) < (sector[0] + sector[1]): break
						if (flash_offset + flash_size) < sector[0]: break
						bl_sectors.append(sector)
					write_sectors = bl_sectors
					if "bl_save" in args:
						data_import = bytearray([0] * bl_sectors[0][0]) + data_import
				else:
					write_sectors = []
					for item in sector_offsets:
						if item[0] < len(data_import):
							write_sectors.append(item)
			
			dprint("Sectors to update:", write_sectors)
		# ↑↑↑ Read Sector Map
		
		# ↓↓↓ Chip erase
		chip_erase = False
		if flashcart.SupportsChipErase() and not flash_offset > 0:
			if flashcart.SupportsSectorErase() and args["prefer_chip_erase"] is False and sector_map is not False:
				chip_erase = False
			else:
				chip_erase = True
				dprint("Erasing the entire flash chip")
				if flashcart.ChipErase() is False:
					return False
		elif flashcart.SupportsSectorErase() is False:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"No erase method available.", "abortable":False})
			return False
		# ↑↑↑ Chip erase
		
		# ↓↓↓ Flash Write
		self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE", "size":len(data_import), "flash_offset":flash_offset})
		self.SetProgress({"action":"UPDATE_POS", "pos":flash_offset})
		self.INFO["action"] = self.ACTIONS["ROM_WRITE"]
		
		if smallest_sector_size is not False:
			buffer_len = smallest_sector_size
		elif self.MODE == "DMG":
			buffer_len = _mbc.GetROMBankSize()
			if _mbc.HasFlashBanks(): _mbc.SelectBankFlash(0)
		else:
			buffer_len = 0x2000
		dprint("Transfer buffer length is 0x{:X}".format(buffer_len))
		
		start_bank = 0
		start_address = 0
		buffer_pos = 0
		retry_hp = 0
		end_address = len(data_import)
		dprint("ROM banks:", end_bank)

		if chip_erase:
			write_sectors = [[ 0, len(data_import) ]]
		elif write_sectors is None or len(write_sectors) == 0:
			write_sectors = sector_offsets
		
		if len(write_sectors) == 0:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Coulnd’t start writing ROM because the flash cart couldn’t be detected properly.", "abortable":False})
			return False

		for sector in write_sectors:
			if chip_erase is False:
				if retry_hp == 0:
					retry_hp = 15 # First sector
				else:
					retry_hp = 100 # Other sectors
				
				if self.MODE == "AGB":
					dprint("Writing sector:", hex(sector[0]), hex(sector[1]))
					buffer_pos = sector[0]
					start_address = buffer_pos
					end_address = sector[0] + sector[1]
					if sector[:2] not in sector_offsets:
						dprint("Sector not found for delta writing:", sector)
						continue
					sector_pos = sector_offsets.index(sector[:2])
					start_bank = math.floor(buffer_pos / rom_bank_size)
					end_bank = math.ceil((buffer_pos + sector[1]) / rom_bank_size)
					# print(hex(start_address), hex(end_address), start_bank, end_bank)
					# print(hex(sector_offsets[sector_pos][0]), sector_pos)
					# print("")
				elif self.MODE == "DMG":
					dprint("Writing sector:", hex(sector[0]), hex(sector[1]))
					buffer_pos = sector[0]
					#end_address = sector[0] + sector[1]
					if sector[:2] not in sector_offsets:
						print("Sector not found for delta writing:", sector)
						continue
					sector_pos = sector_offsets.index(sector[:2])
					start_bank = math.floor(buffer_pos / rom_bank_size)
					end_bank = math.ceil((buffer_pos + sector[1]) / rom_bank_size)
					# print(hex(start_address), hex(end_address), start_bank, end_bank)
					# print(hex(sector_offsets[sector_pos][0]), sector_pos)
					# print("")
			
			#for bank in range(start_bank, end_bank):
			bank = start_bank
			while bank < end_bank:
				if self.CANCEL:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.ERROR_ARGS = {}
					self.SetProgress(cancel_args)
					if self.CanPowerCycleCart(): self.CartPowerCycle()
					return
				
				status = None
				#print("Bank:", bank, "...")
				# ↓↓↓ Switch ROM bank
				if self.MODE == "DMG":
					if _mbc.ResetBeforeBankChange(bank) is True:
						dprint("Resetting the MBC")
						self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
					(start_address, bank_size) = _mbc.SelectBankROM(bank)
					if flashcart.PulseResetAfterWrite():
						if bank == 0:
							self._write(self.DEVICE_CMD["OFW_GB_CART_MODE"])
							self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
						else:
							self._write(self.DEVICE_CMD["OFW_GB_FLASH_BANK_1_COMMAND_WRITES"])
					self._set_fw_variable("DMG_ROM_BANK", bank)
					
					buffer_len = min(buffer_len, bank_size)
					if "start_addr" in flashcart.CONFIG and bank == 0: start_address = flashcart.CONFIG["start_addr"]
					end_address = start_address + bank_size
					start_address += (buffer_pos % rom_bank_size)
					if end_address > start_address + sector[1]:
						end_address = start_address + sector[1]

				elif self.MODE == "AGB":
					if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] > 0:
						flashcart.Reset(full_reset=True)
						flashcart.SelectBankROM(bank)
						temp = end_address - start_address
						start_address %= cart_type["flash_bank_size"]
						end_address = min(cart_type["flash_bank_size"], start_address + temp)
				# ↑↑↑ Switch ROM bank

				skip_init = False
				pos = start_address
				dprint("buffer_pos=0x{:X}, start_address=0x{:X}, end_address=0x{:X}".format(buffer_pos, start_address, end_address))
				
				while pos < end_address:
					if self.CANCEL:
						cancel_args = {"action":"ABORT", "abortable":False}
						cancel_args.update(self.CANCEL_ARGS)
						self.CANCEL_ARGS = {}
						self.ERROR_ARGS = {}
						self.SetProgress(cancel_args)
						if self.CanPowerCycleCart(): self.CartPowerCycle()
						return
					
					if buffer_pos >= len(data_import): break

					# ↓↓↓ Sector erase
					se_ret = None
					if chip_erase is False:
						if sector_pos < len(sector_offsets) and buffer_pos == sector_offsets[sector_pos][0]:
							self.SetProgress({"action":"UPDATE_POS", "pos":buffer_pos})
							dprint("Erasing sector #{:d} at position 0x{:X} (0x{:X})".format(sector_pos, buffer_pos, pos))
							sector_pos += 1
							if flashcart.FlashCommandsOnBank1(): _mbc.SelectBankROM(bank)
							se_ret = flashcart.SectorErase(pos=pos, buffer_pos=buffer_pos)
							if se_ret:
								self.SetProgress({"action":"UPDATE_POS", "pos":buffer_pos, "pos_sector":buffer_pos})
								sector_size = se_ret
								dprint("Next sector size: 0x{:X}".format(sector_size))
							skip_init = False
							if "from_user" in self.CANCEL_ARGS and self.CANCEL_ARGS["from_user"]:
								continue
					# ↑↑↑ Sector erase
					
					if se_ret is not False:
						if command_set_type == "GBMEMORY" and self.FW["pcb_ver"] < 5:
							status = self.WriteROM_GBMEMORY(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], bank=bank)
						elif command_set_type == "GBMEMORY" and self.FW["pcb_ver"] in (5, 6, 101):
							status = self.WriteROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], flash_buffer_size=flash_buffer_size, skip_init=(skip_init and not self.SKIPPING))
							self._cart_write(pos + buffer_len - 1, 0xF0)
						elif command_set_type == "DMG-MBC5-32M-FLASH":
							status = self.WriteROM_DMG_MBC5_32M_FLASH(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], bank=bank)
						elif command_set_type == "BLAZE_XPLODER":
							status = self.WriteROM_DMG_EEPROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], bank=bank)
						elif command_set_type == "DATEL_ORBITV2":
							status = self.WriteROM_DMG_DatelOrbitV2(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], bank=bank)
						else:
							max_buffer_write = self.MAX_BUFFER_WRITE
							if (len(data_import) == 0x1FFFF00) and (buffer_pos+buffer_len > len(data_import)):
								# 32 MiB ROM + EEPROM cart
								max_buffer_write = 256
								buffer_len = (buffer_pos+buffer_len - len(data_import))
							status = self.WriteROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], flash_buffer_size=flash_buffer_size, skip_init=(skip_init and not self.SKIPPING), rumble_stop=rumble, max_length=max_buffer_write)
					
					if status is False or se_ret is False:
						self.CANCEL = True
						self.ERROR = True
						sr = "Unknown"
						if (self.FW["pcb_ver"] in (5, 6) and self.FW["fw_ver"] >= 11):
							lives = 3
							while lives > 0:
								dprint("Retrieving last status register value...")
								self.DEVICE.reset_input_buffer()
								self.DEVICE.reset_output_buffer()
								self._write(self.DEVICE_CMD["GET_VARIABLE"])
								self._write(2)
								self._write(3)
								sr = self._read(2)
								if sr not in (False, None) and len(sr) == 2:
									sr = "0x{:X}".format(struct.unpack(">H", sr)[0])
									break
								dprint("Erroneous response:", sr)
								lives -= 1
							if lives == 0:
								sr = "Timeout"
						dprint("Last status register value:", sr)

						if "from_user" in self.CANCEL_ARGS and self.CANCEL_ARGS["from_user"]:
							break
						elif not self.DEVICE.is_open or self.DEVICE is None:
							self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"An error occured while writing 0x{:X} bytes at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTroubleshooting advice:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n- Check cartridge type selection{:s}\n\nStatus Register: {:s}".format(buffer_len, buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False), errmsg_mbc_selection, sr)})
							break
						else:
							if chip_erase: retry_hp = 0
							if "iteration" in self.ERROR_ARGS and self.ERROR_ARGS["iteration"] > 0:
								retry_hp -= 5
								if retry_hp <= 0:
									self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Unstable connection detected while writing 0x{:X} bytes in iteration {:d} at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTroubleshooting advice:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n\nStatus Register: {:s}".format(buffer_len, self.ERROR_ARGS["iteration"], buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False), sr)})
									continue
							else:
								retry_hp -= 10
								if retry_hp <= 0:
									self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"An error occured while writing 0x{:X} bytes at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTroubleshooting advice:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n- Check cartridge type selection\n- Check cartridge ROM storage size (at least {:s} is required){:s}\n\nStatus Register: {:s}".format(buffer_len, buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False), Util.formatFileSize(size=len(data_import), asInt=False), errmsg_mbc_selection, sr), "abortable":False})
									continue
							
							rev_buffer_pos = sector_offsets[sector_pos - 1][0]
							buffer_pos = rev_buffer_pos
							bank = start_bank
							sector_pos -= 1
							err_text = "Write error! Retrying from 0x{:X}...".format(rev_buffer_pos)
							print(err_text)
							dprint(err_text, "Bank {:d} | HP: {:d}/100".format(bank, retry_hp))
							pos = end_address
							status = False

							self.SetProgress({"action":"ERROR", "abortable":True, "pos":buffer_pos, "text":err_text})
							delay = 0.5 + (100-retry_hp)/50
							if self.CanPowerCycleCart():
								self.CartPowerOff()
								time.sleep(delay)
								self.CartPowerOn()
								if self.MODE == "DMG" and _mbc.HasFlashBanks(): _mbc.SelectBankFlash(bank)
							time.sleep(delay)
							if self.DEVICE is None:
								raise ConnectionAbortedError("A critical connection error occured while writing 0x{:X} bytes at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.".format(buffer_len, buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False)))

							self.CANCEL_ARGS = {}
							self.CANCEL = False
							self.ERROR = False
							self.DEVICE.reset_input_buffer()
							self.DEVICE.reset_output_buffer()
							self._cart_write(pos, 0xF0)
							self._cart_write(pos, 0xFF)
							flashcart.Unlock()
							continue
						
						self.CANCEL = True
						self.ERROR = True
						continue
					
					skip_init = True
					
					buffer_pos += buffer_len
					pos += buffer_len
					self.SetProgress({"action":"UPDATE_POS", "pos":buffer_pos})
				
				if status is not False:
					bank += 1

		self.SetProgress({"action":"UPDATE_POS", "pos":len(data_import)})
		# ↑↑↑ Flash write
		
		# ↓↓↓ GB-Memory Hidden Sector
		if command_set_type == "GBMEMORY":
			flashcart.EraseHiddenSector(buffer=data_map_import)
			status = self.WriteROM_GBMEMORY(address=0, buffer=data_map_import[0:128], bank=1)
			if status is False:
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error occured while writing the hidden sector. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.", "abortable":False})
				return False
		# ↑↑↑ GB-Memory Hidden Sector
		
		# ↓↓↓ Reset flash
		flashcart.Reset(full_reset=True)
		# ↑↑↑ Reset flash

		# ↓↓↓ Flash verify
		verified = False
		if "broken_sectors" in self.INFO: del(self.INFO["broken_sectors"])
		if "verify_write" in args and args["verify_write"] is True:
			self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE_VERIFY", "size":len(data_import), "flash_offset":flash_offset})
			if Util.DEBUG:
				with open("debug_verify.bin", "wb") as f: pass
			
			broken_sectors = []
			for sector in write_sectors:
				verified = True
				if sector[0] >= len(data_import): break
				verify_args = copy.copy(args)
				verify_args.update({"verify_write":data_import[sector[0]:sector[0]+sector[1]], "rom_size":len(data_import), "verify_from":sector[0], "path":"", "rtc_area":flashcart.HasRTC(), "verify_mbc":_mbc})
				verify_args["verify_base_pos"] = sector[0]
				verify_args["verify_len"] = len(verify_args["verify_write"])
				verify_args["rom_size"] = len(verify_args["verify_write"])
				self.SetProgress({"action":"UPDATE_POS", "pos":sector[0]})

				self.ReadROM(0, 4) # dummy read
				start_address = 0
				end_address = buffer_pos

				verified_size = self._BackupROM(verify_args)

				if isinstance(verified_size, int): dprint("args[\"verify_len\"]=0x{:X}, verified_size=0x{:X}".format(verify_args["verify_len"], verified_size))
				if self.CANCEL or self.ERROR:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.ERROR_ARGS = {}
					self.SetProgress(cancel_args)
					if self.CanPowerCycleCart(): self.CartPowerCycle()
					verified = False
					return
				elif (verified_size is not True) and (verify_args["verify_len"] != verified_size):
					print("Verification failed at 0x{:X}! Sector: {:s}".format(sector[0]+verified_size, str(sector)))
					broken_sectors.append(sector)
					continue
			
			if len(broken_sectors) > 0:
				self.INFO["broken_sectors"] = broken_sectors
				self.INFO["verify_error_params"] = {}
				self.INFO["verify_error_params"]["rom_size"] = len(data_import)
				if self.MODE == "DMG":
					self.INFO["verify_error_params"]["mapper_name"] = _mbc.GetName()
					if flashcart.GetMBC() == "manual":
						self.INFO["verify_error_params"]["mapper_selection_type"] = 1 # manual
					else:
						self.INFO["verify_error_params"]["mapper_selection_type"] = 2 # forced by cart type
					self.INFO["verify_error_params"]["mapper_max_size"] = _mbc.GetMaxROMSize()
				verified = False
		# ↑↑↑ Flash verify

		if delta_state_new is not None and not chip_erase and not "broken_sectors" in self.INFO:
			try:
				with open(json_file, "wb") as f:
					f.write(json.dumps(delta_state_new).encode("UTF-8-SIG"))
			except PermissionError:
				print("Error: Couldn’t update write-protected file “{:s}”".format(json_file))
		
		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
			self._set_fw_variable("DMG_ROM_BANK", 0)
		elif self.MODE == "AGB":
			if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] > 0:
				flashcart.SelectBankROM(0)
		# ↑↑↑ Switch to first ROM bank
		
		# Power Cycle Cartridge
		self.SetMode(self.MODE)

		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.SetProgress({"action":"FINISHED", "verified":verified})
		return True
	
	#################################################################

	def TransferData(self, args, signal):
		self.ERROR = False
		self.CANCEL = False
		self.CANCEL_ARGS = {}
		self.READ_ERRORS = 0
		if self.IsConnected():
			if self.FW["pcb_ver"] in (5, 6, 101):
				self._write(self.DEVICE_CMD["OFW_CART_MODE"])
				self._read(1)
				self.CartPowerOn()
			
			ret = False
			self.SIGNAL = signal
			try:
				temp = copy.copy(args)
				if "buffer" in temp: temp["buffer"] = "(data)"
				dprint("args:", temp)
				del(temp)
				self.NO_PROG_UPDATE = False
				self.READ_ERRORS = 0
				if args['mode'] == 1: ret = self._BackupROM(args)
				elif args['mode'] == 2: ret = self._BackupRestoreRAM(args)
				elif args['mode'] == 3: ret = self._BackupRestoreRAM(args)
				elif args['mode'] == 4: ret = self._FlashROM(args)
				if self.FW is None: return False
				if self.FW["pcb_ver"] in (5, 6, 101):
					if ret is True:
						self._write(self.DEVICE_CMD["OFW_DONE_LED_ON"])
					elif self.ERROR is True:
						self._write(self.DEVICE_CMD["OFW_ERROR_LED_ON"])
				return True
			except serial.serialutil.SerialTimeoutException as _:
				print("Connection timed out. Please reconnect the device.")
				return False
			except serial.serialutil.PortNotOpenError as _:
				print("Connection closed.")
				return False
