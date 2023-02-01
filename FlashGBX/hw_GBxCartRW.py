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
	DEVICE_MAX_FW = 8
	DEVICE_LATEST_FW_TS = { 4:1619427330, 5:1673788742, 6:1673788742 }
	
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

	PCB_VERSIONS = {4:'v1.3', 5:'v1.4', 6:'v1.4a', 101:'Mini v1.0d'}
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
	MAX_BUFFER_LEN = 0x2000
	DEVICE_TIMEOUT = 1
	WRITE_DELAY = False
	
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
					self.MAX_BUFFER_LEN = 0x2000
					dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
					self.DEVICE = dev
					if not self.LoadFirmwareVersion():
						dev.close()
						self.DEVICE = None
						self.BAUDRATE = 1000000
						self.MAX_BUFFER_LEN = 0x100
						continue
				elif max_baud >= 1700000 and self.FW["pcb_ver"] in (5, 6, 101) and self.BAUDRATE < 1700000:
					# Switch to higher baud rate
					#self._write(self.DEVICE_CMD["OFW_USART_1_7M_SPEED"])
					#self.BAUDRATE = 1700000
					#dev.close()
					self.ChangeBaudRate(baudrate=1700000)
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
				elif self.FW is None or "cfw_id" not in self.FW or self.FW["cfw_id"] != 'L': # Not a CFW by Lesserkuma
					dev.close()
					self.DEVICE = None
					continue
				elif self.FW["fw_ver"] < self.DEVICE_MIN_FW:
					dev.close()
					self.DEVICE = None
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " requires a firmware update to work with this software. Please try again after updating it to version L" + str(self.DEVICE_MIN_FW) + " or higher.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
					continue
				#elif self.FW["fw_ver"] < self.DEVICE_MAX_FW:
				#	conn_msg.append([1, "The GBxCart RW device on port " + ports[i] + " is running an older firmware version. Please consider updating to version L" + str(self.DEVICE_MAX_FW) + " to make use of the latest features.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
				elif self.FW["fw_ver"] > self.DEVICE_MAX_FW:
					conn_msg.append([0, "NOTE: The GBxCart RW device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
				
				if (self.FW["pcb_ver"] not in (4, 5, 6, 101)): # only the v1.3, v1.4, v1.4a, Mini v1.1 PCB revisions are supported
					dev.close()
					self.DEVICE = None
					continue
				
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
		
		#conn_msg.append([0, "NOTE: This is a third party tool for GBxCart RW by insideGadgets. Visit https://www.gbxcart.com/ for more information."])
		return conn_msg
	
	def LoadFirmwareVersion(self):
		try:
			self.DEVICE.reset_input_buffer()
			self.DEVICE.reset_output_buffer()
			self._write(self.DEVICE_CMD["OFW_PCB_VER"])
			pcb = self.DEVICE.read(1)[0]
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
			return True
		
		except:
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
			self.Close()
			self.BAUDRATE = baudrate
			self.MAX_BUFFER_LEN = 0x2000
		elif baudrate == 1000000:
			self._write(self.DEVICE_CMD["OFW_USART_1_0M_SPEED"])
			self.Close()
			self.BAUDRATE = baudrate
			self.MAX_BUFFER_LEN = 0x100
	
	def CanSetVoltageManually(self):
		return False
	
	def CanSetVoltageAutomatically(self):
		return True
	
	def CanPowerCycleCart(self):
		if self.FW is None or self.DEVICE is None: return False
		return self.FW["pcb_ver"] in (5, 6)
	
	def GetSupprtedModes(self):
		if self.FW["pcb_ver"] == 101:
			return ["DMG"]
		else:
			return ["DMG", "AGB"]
	
	def IsSupportedMbc(self, mbc):
		if self.CanPowerCycleCart():
			return mbc in ( 0x00, 0x01, 0x02, 0x03, 0x06, 0x0B, 0x0D, 0x10, 0x13, 0x19, 0x1A, 0x1B, 0x1C, 0x1E, 0x20, 0x22, 0xFC, 0xFD, 0xFE, 0xFF, 0x101, 0x103, 0x104, 0x105, 0x201, 0x202, 0x203, 0x204, 0x205 )
		else:
			return mbc in ( 0x00, 0x01, 0x02, 0x03, 0x06, 0x0B, 0x0D, 0x10, 0x13, 0x19, 0x1A, 0x1B, 0x1C, 0x1E, 0x20, 0x22, 0xFC, 0xFD, 0xFE, 0xFF, 0x101, 0x103, 0x104, 0x105, 0x202, 0x205 )
	
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
	
	def Close(self):
		if self.IsConnected():
			try:
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
		if self.FW["pcb_ver"] not in (5, 6): return False
		return (self.FW["pcb_ver"] in (4, 5, 6) and self.FW["fw_ts"] < self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]])
	
	def GetFirmwareUpdaterClass(self):
		if self.FW["pcb_ver"] == 4: # v1.3
			try:
				from . import fw_GBxCartRW_v1_3
				return (None, fw_GBxCartRW_v1_3.FirmwareUpdaterWindow)
			except:
				return False
		elif self.FW["pcb_ver"] in (5, 6): # v1.4 / v1.4a
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
		dprint("Setting Write Delay to", enable)
		self.WRITE_DELAY = enable
	
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
				dprint("Timeout error ({:s}(), line {:d})".format(stack.name, stack.lineno))
				self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"A timeout error has occured at {:s}() in line {:d}. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.".format(stack.name, stack.lineno)})
			else:
				dprint("Communication error ({:s}(), line {:d})".format(stack.name, stack.lineno))
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
			dprint("Warning: Received {:d} byte(s) instead of the expected {:d} byte(s)".format(len(buffer), count))
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
			raise Exception("Unknown variable name specified.")
		
		buffer = bytearray([self.DEVICE_CMD["SET_VARIABLE"], size])
		buffer.extend(struct.pack(">I", key))
		buffer.extend(struct.pack(">I", value))
		self._write(buffer)
	
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
				return self.ReadROM(address, length)

	def _cart_write(self, address, value, flashcart=False, sram=False):
		dprint("Writing to cartridge: 0x{:X} = 0x{:X} (flashcart={:s}, sram={:s})".format(address, value & 0xFF, str(flashcart), str(sram)))
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
				self._set_fw_variable("ADDRESS", 2)
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
		self.CartPowerOff(delay=delay)
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
		if args["action"] == "UPDATE_POS":
			self.POS = args["pos"]
			self.INFO["transferred"] = args["pos"]
		try:
			self.SIGNAL.emit(args)
		except AttributeError:
			if self.SIGNAL is not None:
				self.SIGNAL(args)
		
		if args["action"] == "FINISHED":
			self.SIGNAL = None
	
	def ReadInfo(self, setPinsAsInputs=False, checkRtc=True):
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		data = {}
		self.POS = 0
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

		header = self.ReadROM(0, 0x180)
		if Util.DEBUG:
			with open("debug_header.bin", "wb") as f: f.write(header)
		if header is False or len(header) != 0x180:
			print("{:s}\n{:s}Couldn’t read the cartridge information. Please try again.{:s}".format(str(header), ANSI.RED, ANSI.RESET))
			return False
		
		# Parse ROM header
		if self.MODE == "DMG":
			data = RomFileDMG(header).GetHeader()
			if data["game_title"] == "TETRIS" and hashlib.sha1(header).digest() != bytearray([0x1D, 0x69, 0x2A, 0x4B, 0x31, 0x7A, 0xA5, 0xE9, 0x67, 0xEE, 0xC2, 0x2F, 0xCC, 0x32, 0x43, 0x8C, 0xCB, 0xC5, 0x78, 0x0B]): # Sachen
				header = self.ReadROM(0, 0x280)
				data = RomFileDMG(header).GetHeader()
			if data["logo_correct"] is False and not b"Future Console Design" in header: # workaround for strange bootlegs
				self._cart_write(0, 0xFF)
				time.sleep(0.1)
				header = self.ReadROM(0, 0x280)
				data = RomFileDMG(header).GetHeader()
			if data["mapper_raw"] == 0x203 or b"Future Console Design" in header: # Xploder GB version number
				self._cart_write(0x0006, 0)
				header[0:0x10] = self.ReadROM(0x4000, 0x10)
				header[0xD0:0xE0] = self.ReadROM(0x40D0, 0x10)
				data = RomFileDMG(header).GetHeader()
			
			_mbc = DMG_MBC().GetInstance(args={"mbc":data["mapper_raw"]}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
			if checkRtc:
				data["has_rtc"] = _mbc.HasRTC() is True
				if data["has_rtc"] is True:
					if _mbc.GetName() == "TAMA5": _mbc.EnableMapper()
					_mbc.LatchRTC()
					data["rtc_buffer"] = _mbc.ReadRTC()
					if _mbc.GetName() == "TAMA5": self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			else:
				data["has_rtc"] = False
		
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
			elif (data["3d_memory"] == True):
				data["rom_size"] = 0x4000000
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
			
			if checkRtc and data["logo_correct"] is True and header[0xC5] == 0 and header[0xC7] == 0 and header[0xC9] == 0:
				_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
				has_rtc = _agb_gpio.HasRTC()
				data["has_rtc"] = has_rtc is True
				if has_rtc is not True:
					data["no_rtc_reason"] = has_rtc
				else:
					data["rtc_buffer"] = _agb_gpio.ReadRTC()
			else:
				data["has_rtc"] = False
				data["no_rtc_reason"] = None
		
		dprint("Header data:", data)
		data["raw"] = header
		self.INFO = {**self.INFO, **data}
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

		# Header
		has_rtc = self.INFO["has_rtc"]
		info = self.ReadInfo(checkRtc=False)
		self.INFO["has_rtc"] = has_rtc

		if self.MODE == "DMG" and mbc is None:
			mbc = info["mapper_raw"]
			if mbc > 0x200: checkSaveType = False
		
		(cart_types, cart_type_id, flash_id, cfi_s, cfi) = self.AutoDetectFlash(limitVoltage=limitVoltage)
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = supported_carts[cart_type_id]
		if self.MODE == "DMG" and "command_set" in cart_type and cart_type["command_set"] == "DMG-MBC5-32M-FLASH":
			checkSaveType = False
		elif self.MODE == "AGB" and "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
			checkSaveType = False

		# Save Type and Size
		if checkSaveType:
			max_size = 0x20000
			if self.MODE == "DMG":
				if mbc == 0x20: # MBC6
					save_size = 1081344
					save_type = 7
					return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id)
				elif mbc == 0x22: # MBC7
					max_size = 512
				elif mbc == 0xFD: # TAMA5
					save_size = 32
					save_type = 10
					return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id)
				args = { 'mode':2, 'path':None, 'mbc':mbc, 'save_type':max_size, 'rtc':False }
			elif self.MODE == "AGB":
				args = { 'mode':2, 'path':None, 'mbc':mbc, 'save_type':8, 'rtc':False }
			
			ret = self._BackupRestoreRAM(args=args)

			if ret is not False:
				save_size = Util.find_size(self.INFO["data"], len(self.INFO["data"]))
			else:
				save_size = 0
			
			if self.MODE == "DMG":
				if save_size > 0x20:
					if save_size in Util.DMG_Header_RAM_Sizes_Flasher_Map:
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map.index(save_size)
						if mbc == 0x22: # MBC7
							if save_size == 256:
								save_type = 8
							elif save_size == 512:
								save_type = 9
						elif len(self.INFO["data"]) >= 0x12000 and self.INFO["data"][0x10000:0x12000] == bytearray([self.INFO["data"][0x10000]] * 0x2000):
							if self.INFO["data"][0x8000:0x10000] == bytearray([self.INFO["data"][0x8000]] * 0x8000):
								save_size = 32768
								save_type = 4
							else:
								save_size = 65536
								save_type = 5
			
			elif self.MODE == "AGB":
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
					if info["dacs_8m"] is True:
						save_size = 1032192
						save_type = 6
					elif save_size > 256: # SRAM
						if save_size == 131072:
							save_type = 8
						elif save_size == 65536:
							save_type = 7
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
						else:
							save_type = 1
							save_size = 512

		self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
		self.INFO["last_action"] = 0
		self.INFO["action"] = None

		return (info, save_size, save_type, save_chip, sram_unstable, cart_types, cart_type_id, cfi_s, cfi, flash_id)
	
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
		
		for _ in range(0, num):
			self._write(self.DEVICE_CMD[command])
			temp = self._read(length)
			if isinstance(temp, int): temp = bytearray([temp])
			if temp is False or len(temp) != length: return bytearray()
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
		for _ in range(0, int(num / (buffer_size / length))): #32
			for _ in range(0, int(buffer_size / length)): # 0x1000/0x200=8
				self._write(self.DEVICE_CMD["AGB_CART_READ_3D_MEMORY"])
				temp = self._read(length)
				if isinstance(temp, int): temp = bytearray([temp])
				if temp is False or len(temp) != length: return bytearray()
				buffer += temp
			
			if self.INFO["action"] == self.ACTIONS["ROM_READ"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"READ", "bytes_added":length})
			self._write(0)

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
		self.NO_PROG_UPDATE = True
		self._set_fw_variable("DMG_READ_CS_PULSE", 1)
		self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)

		# Read save state
		for i in range(0, 0x20):
			self._cart_write(0xA001, 0x06) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | 0x01 << 1) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, 0x07) # address (low)
			self._cart_write(0xA000, i & 0x0F) # bits 0-3 = lower ram address
			self._cart_write(0xA001, 0x0D) # data out (high)
			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			data_h = value1
			self._cart_write(0xA001, 0x0C) # data out (low)

			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			data_l = value1
			
			data = ((data_h & 0xF) << 4) | (data_l & 0xF)
			buffer.append(data)
			self.SetProgress({"action":"UPDATE_POS", "abortable":False, "pos":i+1})
		
		self.NO_PROG_UPDATE = False
		return buffer
	
	def WriteRAM(self, address, buffer, command=None):
		length = len(buffer)
		max_length = 256
		num = math.ceil(length / max_length)
		dprint("Write 0x{:X} bytes to cartridge RAM in {:d} iteration(s)".format(length, num))
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
		self.NO_PROG_UPDATE = True

		for i in range(0, 0x20):
			self._cart_write(0xA001, 0x05) # data in (high)
			self._cart_write(0xA000, buffer[i] >> 4)
			self._cart_write(0xA001, 0x04) # data in (low)
			self._cart_write(0xA000, buffer[i] & 0xF)
			self._cart_write(0xA001, 0x06) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | 0x00 << 1) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, 0x07) # address (low)
			self._cart_write(0xA000, i & 0x0F) # bits 0-3 = lower ram address
			value1, value2 = None, None
			while value1 is None or value1 != value2:
				value2 = value1
				value1 = self._cart_read(0xA000)
			self.SetProgress({"action":"UPDATE_POS", "abortable":False, "pos":i+1})
		
		self.NO_PROG_UPDATE = False

	def WriteROM(self, address, buffer, flash_buffer_size=False, skip_init=False, rumble_stop=False):
		length = len(buffer)
		if self.FW["pcb_ver"] not in (5, 6, 101) or self.BAUDRATE == 1000000:
			max_length = 256
		else:
			max_length = 1024
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
				
				if ret != 0x03:
					if rumble_stop:
						dprint("Sending rumble stop command")
						self._cart_write(address=0xC6, value=0x00, flashcart=True)
					self._write(self.DEVICE_CMD["FLASH_PROGRAM"])
				ret = self._write(data, wait=True)
				
				if ret not in (0x01, 0x03):
					dprint("Flash error at 0x{:X} in iteration {:d} of {:d} while trying to write a total of 0x{:X} bytes (response = {:s})".format(address, i, num, len(buffer), str(ret)))
					self.ERROR_ARGS = { "iteration":i }
					self.SKIPPING = False
					return False
				pos += len(data)
			
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
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
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
			
			flashcart = Flashcart(config=flashcart_meta, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, cart_powercycle_fncptr=self.CartPowerCycle, set_we_pin_wr=self._set_we_pin_wr, set_we_pin_audio=self._set_we_pin_audio)
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
					if isinstance(cfi, dict) and "device_size" in cfi:
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
		return (flash_types, flash_type_id, flash_id, cfi_s, cfi)

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
			#{ 'read_cfi':[[0xAA, 0x9898]], 'read_identifier':[[ 0xAAA, 0xAAAA ], [ 0x555, 0x5555 ], [ 0xAAA, 0x9090 ]], 'reset':[[ 0x0, 0xF0F0 ]] },
			#{ 'read_cfi':[[0x4000, 0x98]], 'read_identifier':[[ 0x4000, 0x90 ]], 'reset':[[ 0x4000, 0xFF ]] },
		]
		
		if self.MODE == "DMG":
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
				if d_swap is not None:
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
					
					if d_swap is not None:
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
							d_swap = ( 0, 1 )
							for k in method.keys():
								for c in range(0, len(method[k])):
									if isinstance(method[k][c][1], int):
										method[k][c][1] = bitswap(method[k][c][1], d_swap)
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
					flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, cart_powercycle_fncptr=self.CartPowerCycle, progress_fncptr=None, set_we_pin_wr=self._set_we_pin_wr, set_we_pin_audio=self._set_we_pin_audio)
					flashcart.Reset(full_reset=False)
		
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
			flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, cart_powercycle_fncptr=self.CartPowerCycle, progress_fncptr=None, set_we_pin_wr=self._set_we_pin_wr, set_we_pin_audio=self._set_we_pin_audio)
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
	
	#################################################################
	
	def DoTransfer(self, mode, fncSetProgress, args):
		from . import DataTransfer
		args['mode'] = mode
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
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
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = copy.deepcopy(supported_carts[args["cart_type"]])
		if not isinstance(cart_type, str):
			cart_type["_index"] = 0
			for i in range(0, len(list(self.SUPPORTED_CARTS[self.MODE].keys()))):
				if i == args["cart_type"]:
					try:
						cart_type["_index"] = cart_type["names"].index(list(self.SUPPORTED_CARTS[self.MODE].keys())[i])
						flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, cart_powercycle_fncptr=self.CartPowerCycle, progress_fncptr=self.SetProgress, set_we_pin_wr=self._set_we_pin_wr, set_we_pin_audio=self._set_we_pin_audio)
					except:
						pass

		# Firmware check L8
		if self.FW["fw_ver"] < 8 and flashcart and "enable_pullups" in cart_type:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type requires at least firmware version L8 on the GBxCart RW v1.4 hardware revision or newer. It may also work with older hardware revisions using the official firmware and insideGadgets flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>.", "abortable":False})
			return False
		# Firmware check L8

		buffer_len = 0x4000
		
		#self.INFO["dump_info"]["timestamp"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
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

		if "verify_write" in args:
			size = len(args["verify_write"])
			buffer_len = min(buffer_len, size)
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
		max_length = self.MAX_BUFFER_LEN
		dprint("Max buffer size: 0x{:X}".format(max_length))
		if self.FAST_READ is True:
			if (self.MODE == "AGB" and "command_set" in cart_type and cart_type["command_set"] == "3DMEMORY"):
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
		dprint("start_address=0x{:X}, end_address=0x{:X}, start_bank=0x{:X}, rom_banks=0x{:X}".format(start_address, end_address, start_bank, rom_banks))
		
		bank = start_bank

		#for bank in range(0, rom_banks):
		while bank < rom_banks:
			# ↓↓↓ Switch ROM bank
			if self.MODE == "DMG":
				if _mbc.ResetBeforeBankChange(bank) is True:
					dprint("Resetting the MBC")
					self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
				(start_address, bank_size) = _mbc.SelectBankROM(bank)
				end_address = start_address + bank_size
				buffer_len = _mbc.GetROMBankSize()
				if "verify_write" in args:
					buffer_len = min(buffer_len, bank_size)
					#if "start_addr" in flashcart.CONFIG and bank == 0: start_address = flashcart.CONFIG["start_addr"]
					end_address = start_address + bank_size
					start_address += (buffer_pos % rom_bank_size)
					if end_address > start_address + args["verify_len"]:
						end_address = start_address + args["verify_len"]
				
				# dprint("{:X}/{:X}/{:X}".format(start_address, bank_size, buffer_len))
			elif self.MODE == "AGB":
				if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
					flashcart.SelectBankROM(bank)
					temp = end_address - start_address
					start_address %= cart_type["flash_bank_size"]
					end_address = min(cart_type["flash_bank_size"], start_address + temp)
			# ↑↑↑ Switch ROM bank

			skip_init = False
			pos = start_address
			lives = 20

			# dprint("pos_total=0x{:X}, start_address=0x{:X}, end_address=0x{:X}".format(pos_total, start_address, end_address))

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
				
				if (self.MODE == "AGB" and "command_set" in cart_type and cart_type["command_set"] == "3DMEMORY"):
					temp = self.ReadROM_3DMemory(address=pos, length=buffer_len, max_length=max_length)
				else:
					temp = self.ReadROM(address=pos, length=buffer_len, skip_init=skip_init, max_length=max_length)
					skip_init = True
				
				if len(temp) != buffer_len:
					if "verify_write" in args:
						self.SetProgress({"action":"UPDATE_POS", "pos":args["verify_from"]+pos_total})
					else:
						self.SetProgress({"action":"UPDATE_POS", "pos":pos_total})
					
					if (max_length >> 1) < 64:
						dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}!".format(len(temp), buffer_len, pos_total))
						max_length = 64
					elif lives > 18:
						dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}!".format(len(temp), buffer_len, pos_total))
					else:
						dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}! Decreasing maximum transfer buffer size to 0x{:X}.".format(len(temp), buffer_len, pos_total, max_length >> 1))
						max_length >>= 1
						self.MAX_BUFFER_LEN = max_length
					
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
		
		if file is not None: file.close()
		
		if "verify_write" in args:
			return min(pos_total, len(args["verify_write"]))
		
		# Hidden sector (GB Memory)
		if self.MODE == "DMG":
			if len(args["path"]) > 0 and _mbc.HasHiddenSector():
				file = open(os.path.splitext(args["path"])[0] + ".map", "wb")
				temp = _mbc.ReadHiddenSector()
				self.INFO["hidden_sector"] = temp
				self.INFO["dump_info"]["gbmem"] = temp
				file.write(temp)
				file.close()
		
		# Calculate Global Checksum
		self.INFO["file_crc32"] = zlib.crc32(buffer) & 0xFFFFFFFF
		self.INFO["file_sha1"] = hashlib.sha1(buffer).hexdigest()
		self.INFO["file_sha256"] = hashlib.sha256(buffer).hexdigest()
		self.INFO["file_md5"] = hashlib.md5(buffer).hexdigest()
		self.INFO["dump_info"]["hash_crc32"] = self.INFO["file_crc32"]
		self.INFO["dump_info"]["hash_sha1"] = self.INFO["file_sha1"]
		self.INFO["dump_info"]["hash_sha256"] = self.INFO["file_sha256"]
		self.INFO["dump_info"]["hash_md5"] = self.INFO["file_md5"]
		if self.MODE == "DMG":
			if _mbc.GetName() == "MMM01":
				self.INFO["dump_info"]["header"] = RomFileDMG(buffer[-0x8000:-0x8000+0x180]).GetHeader(unchanged=True)
			else:
				self.INFO["dump_info"]["header"] = RomFileDMG(buffer[:0x180]).GetHeader(unchanged=True)
			chk = _mbc.CalcChecksum(buffer)
		elif self.MODE == "AGB":
			self.INFO["dump_info"]["header"] = RomFileAGB(buffer[:0x180]).GetHeader(unchanged=True)
			chk = self.INFO["file_crc32"]
			
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
				agb_save_flash_id = self.ReadFlashSaveID()
				if agb_save_flash_id is not False and len(agb_save_flash_id) == 2:
					self.INFO["dump_info"]["agb_save_flash_id"] = agb_save_flash_id
		
		self.INFO["rom_checksum_calc"] = chk
		
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
		
		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
		elif self.MODE == "AGB":
			if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
				flashcart.SelectBankROM(0)
		# ↑↑↑ Switch to first ROM bank

		# Clean up
		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.INFO["last_path"] = args["path"]
		self.SetProgress({"action":"FINISHED"})
		return True

	def _BackupRestoreRAM(self, args):
		_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, cart_powercycle_fncptr=self.CartPowerCycle, clk_toggle_fncptr=self._clk_toggle)
		self.FAST_READ = False
		if "rtc" not in args: args["rtc"] = False
		
		# Prepare some stuff
		command = None
		empty_data_byte = 0x00
		extra_size = 0
		audio_low = False
		if self.MODE == "DMG":
			if not self.IsSupportedMbc(args["mbc"]):
				msg = "This cartridge uses a mapper that is not supported by {:s} using your {:s} device. An updated hardware revision is required.".format(Util.APPNAME, self.GetFullName())
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":msg, "abortable":False})
				return False
			save_size = args["save_type"]
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
			elif args["save_type"] == 6: # DACS
				empty_data_byte = 0xFF
				# Read Chip ID
				ram_banks = 1
				self._cart_write(0, 0x90)
				flash_id = self._cart_read(0, 4)
				self._cart_write(0, 0x50)
				self._cart_write(0, 0xFF)
				if flash_id != bytearray([ 0xB0, 0x00, 0x9F, 0x00 ]):
					print("WARNING: Unknown DACS flash chip ID ({:s})".format(' '.join(format(x, '02X') for x in flash_id)))
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
					buffer = self.INFO["data"]
				else:
					with open(args["path"], "rb") as f:
						buffer = bytearray(f.read())
				
				# Fill too small file
				if args["mode"] == 3:
					while len(buffer) < save_size:
						buffer += bytearray(buffer)
		
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
					bank_size = 0xFC000
					end_address = 0xFC000
				else:
					end_address = min(save_size, bank_size)
				
				if save_size > bank_size:
					if args["save_type"] == 5: # FLASH 1M
						dprint("Switching to FLASH bank {:d}".format(bank))
						cmds = [
							[ 0x5555, 0xAA ],
							[ 0x2AAA, 0x55 ],
							[ 0x5555, 0xB0 ],
							[ 0, bank ]
						]
						self._cart_write_flash(cmds)
					elif args["save_type"] == 8: # SRAM 1M
						dprint("Switching to SRAM bank {:d}".format(bank))
						self._cart_write(0x1000000, bank)
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
					if self.MODE == "DMG" and _mbc.GetName() == "MBC7":
						temp = self.ReadRAM_MBC7(address=pos, length=buffer_len)
					elif self.MODE == "DMG" and _mbc.GetName() == "MBC6" and bank > 7: # MBC6 flash save memory
						temp = self.ReadROM(address=pos, length=buffer_len, skip_init=False, max_length=max_length)
					elif self.MODE == "DMG" and _mbc.GetName() == "TAMA5":
						temp = self.ReadRAM_TAMA5()
					elif self.MODE == "DMG" and _mbc.GetName() == "Xploder GB":
						temp = self.ReadROM(address=0x20000+pos, length=buffer_len, skip_init=False, max_length=max_length)
					elif self.MODE == "AGB" and args["save_type"] in (1, 2): # EEPROM
						temp = self.ReadRAM(address=int(pos/8), length=buffer_len, command=command, max_length=max_length)
					elif self.MODE == "AGB" and args["save_type"] == 6: # DACS
						temp = self.ReadROM(address=0x1F00000+pos, length=buffer_len, skip_init=False, max_length=max_length)
					elif self.MODE == "DMG" and _mbc.GetName() == "MBC2":
						temp = self.ReadRAM(address=pos, length=buffer_len, command=command, max_length=max_length)
						for i in range(0, len(temp)):
							temp[i] = temp[i] & 0x0F
					else:
						temp = self.ReadRAM(address=pos, length=buffer_len, command=command, max_length=max_length)

					if len(temp) != buffer_len:
						if (max_length >> 1) < 64:
							dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}!".format(len(temp), buffer_len, len(buffer)))
							max_length = 64
						else:
							dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}! Decreasing maximum transfer buffer length to 0x{:X}.".format(len(temp), buffer_len, len(buffer), max_length >> 1))
							max_length >>= 1
						self.DEVICE.reset_input_buffer()
						self.DEVICE.reset_output_buffer()
						continue
					
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
						sector_address = int(pos / buffer_len)
						if agb_flash_chip == 0x1F3D: # Atmel AT29LV512
							self.WriteRAM(address=int(pos/128), buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
						else:
							dprint("sector_address:", sector_address)
							cmds = [
								[ 0x5555, 0xAA ],
								[ 0x2AAA, 0x55 ],
								[ 0x5555, 0x80 ],
								[ 0x5555, 0xAA ],
								[ 0x2AAA, 0x55 ],
								[ sector_address << 12, 0x30 ]
							]
							self._cart_write_flash(cmds)
							sr = 0
							lives = 50
							while True:
								time.sleep(0.01)
								sr = self._cart_read(sector_address << 12, agb_save_flash=True)
								dprint("Data Check: 0x{:X} == 0xFFFF? {:s}".format(sr, str(sr == 0xFFFF)))
								if sr == 0xFFFF: break
								lives -= 1
								if lives == 0:
									self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"Accessing the save data flash chip failed. Please make sure you selected the correct save type. If you are using a reproduction cartridge, check if it really is equipped with a flash chip for save data, or if it uses SRAM for save data instead.", "abortable":False})
									return False
							if buffer[buffer_offset:buffer_offset+buffer_len] != bytearray([0xFF] * buffer_len):
								self.WriteRAM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					elif self.MODE == "AGB" and args["save_type"] == 6: # DACS
						if (pos+0x1F00000) in (0x1F00000, 0x1F10000, 0x1F20000, 0x1F30000, 0x1F40000, 0x1F50000, 0x1F60000, 0x1F70000, 0x1F80000, 0x1F90000, 0x1FA0000, 0x1FB0000, 0x1FC0000, 0x1FD0000, 0x1FE0000, 0x1FF0000, 0x1FF2000, 0x1FF4000, 0x1FF6000, 0x1FF8000, 0x1FFA000):
							sector_address = pos+0x1F00000
							dprint("sector_address:", hex(sector_address))
							cmds = [
								[ sector_address, 0x60 ],
								[ sector_address, 0xD0 ],
								[ sector_address, 0x20 ],
								[ sector_address, 0xD0 ],
								[ sector_address, 0x70 ]
							]
							for c in cmds:
								self._cart_write(c[0], c[1])
							sr = 0
							lives = 20
							while True:
								time.sleep(0.1)
								sr = struct.unpack("<H", self._cart_read(sector_address, 2))[0]
								dprint("Status Register Check: 0x{:X} == 0x80? {:s}".format(sr, str(sr & 0xE0 == 0x80)))
								if sr & 0xE0 == 0x80: break
								lives -= 1
								if lives == 0:
									self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error occured while writing to the cartridge. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.", "abortable":False})
									return False
						self.WriteROM(address=0x1F00000+pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
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
			
			if args["path"] is not None:
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
				_mbc.SelectBankRAM(0)
				self.SetProgress({"action":"INITIALIZE", "method":"SAVE_WRITE_VERIFY", "size":buffer_offset})

				verify_args = copy.copy(args)
				start_address = 0
				end_address = buffer_offset
				
				path = args["path"] # backup path
				verify_args.update({"mode":2, "verify_write":buffer, "path":None})
				self.ReadROM(0, 4) # dummy read
				self.INFO["data"] = None
				self._BackupRestoreRAM(verify_args)

				if args["mbc"] == 6: # MBC2
					for i in range(0, len(self.INFO["data"])):
						self.INFO["data"][i] &= 0x0F
						buffer[i] &= 0x0F

				args["path"] = path # restore path
				if self.CANCEL is True:
					pass
				elif (self.INFO["data"] != buffer[:buffer_offset]):
					msg = ""
					count = 0
					for i in range(0, len(self.INFO["data"])):
						data1 = self.INFO["data"][i]
						data2 = buffer[:buffer_offset][i]
						if data1 != data2:
							count += 1
							if len(msg.split("\n")) <= 10:
								msg += "- 0x{:06X}: {:02X}≠{:02X}\n".format(i, data1, data2)
							elif len(msg.split("\n")) == 11:
								msg += "(more than 10 differences found)\n"
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
		
		if "start_addr" in args and args["start_addr"] > 0:
			data_import = bytearray(b'\xFF' * args["start_addr"]) + data_import
		
		# Pad data
		if len(data_import) > 0:
			if len(data_import) < 0x400:
				data_import += bytearray([0xFF] * (0x400 - len(data_import)))
			if len(data_import) % 0x8000 > 0:
				data_import += bytearray([0xFF] * (0x8000 - len(data_import) % 0x8000))
		
		# Fix header
		if "fix_header" in args and args["fix_header"]:
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
				print("NOTE: Update your GBxCart RW firmware to version L3 or higher for a better transfer rate with this cartridge.")
			del(cart_type["commands"]["buffer_write"])
		# Firmware check L2
		# Firmware check L5
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 5) and ("flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True):
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type requires at least firmware version L5 on the GBxCart RW v1.4 hardware revision or newer. It may also work with older hardware revisions using the official firmware and insideGadgets flasher software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>.", "abortable":False})
			return False
		if (self.FW["pcb_ver"] not in (5, 6, 101) or self.FW["fw_ver"] < 5) and ("double_die" in cart_type and cart_type["double_die"] is True):
			if self.FW["pcb_ver"] in (5, 6):
				print("NOTE: Update your GBxCart RW firmware to version L5 or higher for a better transfer rate with this cartridge.")
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
		
		if cart_type["command_set"] == "GBMEMORY":
			flashcart = Flashcart_DMG_MMSA(config=cart_type, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, progress_fncptr=self.SetProgress)
			if "buffer_map" not in args:
				if os.path.exists(os.path.splitext(args["path"])[0] + ".map"):
					with open(os.path.splitext(args["path"])[0] + ".map", "rb") as file: args["buffer_map"] = file.read()
				else:
					temp = data_import
					if len(temp) == 0: temp = bytearray([0xFF] * 0x180)
					try:
						gbmem = GBMemoryMap(rom=temp)
						args["buffer_map"] = gbmem.GetMapData()
					except:
						print("{:s}An error occured while trying to generate the hidden sector data for the NP GB Memory cartridge.{:s}".format(ANSI.RED, ANSI.RESET))
					
					if args["buffer_map"] is False:
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The NP GB Memory Cartridge requires extra hidden sector data. As it couldn’t be auto-generated, please provide your own at the following path: {:s}".format(os.path.splitext(args["path"])[0] + ".map"), "abortable":False})
						return False
					else:
						dprint("Generated hidden sector data:", args["buffer_map"])
						if Util.DEBUG:
							with open("debug_mmsa_map.bin", "wb") as f: f.write(args["buffer_map"])
			data_map_import = copy.copy(args["buffer_map"])
			data_map_import = bytearray(data_map_import)
			dprint("Hidden sector data loaded")
		else:
			flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_write_fast_fncptr=self._cart_write_flash, cart_read_fncptr=self.ReadROM, cart_powercycle_fncptr=self.CartPowerCycle, progress_fncptr=self.SetProgress, set_we_pin_wr=self._set_we_pin_wr, set_we_pin_audio=self._set_we_pin_audio)
		
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
		if not flashcart.SupportsChipErase() and flashcart.SupportsSectorErase() and args["prefer_chip_erase"] is True:
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
				errmsg_mbc_selection = "\n- Check mapper type used: {:s} (manual selection)".format(_mbc.GetName())
			else:
				errmsg_mbc_selection = "\n- Check mapper type used: {:s} (forced by selected cartridge type)".format(_mbc.GetName())

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
			dprint("Using GB Memory command set")
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
			dprint("Using GB Memory mode on GBxCart RW v1.3")
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
				dprint("Using GB Memory mode on GBxCart RW v1.4")
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

		# ↓↓↓ Unlock cartridge
		if flashcart.Unlock() is False: return False
		if self.MODE == "DMG" and "flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True:
			dprint("Setting ROM bank 1")
			_mbc.SelectBankROM(1)
		# ↑↑↑ Unlock cartridge
		
		# ↓↓↓ Read Flash ID
		if "flash_ids" in cart_type:
			(verified, flash_id) = flashcart.VerifyFlashID()
			if not verified:
				print("NOTE: This cartridge’s Flash ID ({:s}) doesn’t match the cartridge type selection.".format(' '.join(format(x, '02X') for x in flash_id)))
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
			sector_offsets = flashcart.GetSectorOffsets(rom_size=len(data_import), rom_bank_size=rom_bank_size)
			if len(sector_offsets) > 0:
				flash_capacity = sector_offsets[-1][0] + sector_offsets[-1][1]
				if flash_capacity < len(data_import) and not (flashcart.SupportsChipErase() and args["prefer_chip_erase"]):
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"There are not enough flash sectors available to write this ROM. The maximum capacity is {:s}.".format(Util.formatFileSize(flash_capacity, asInt=False)), "abortable":False})
					return False

			sector_offsets_hash = base64.urlsafe_b64encode(hashlib.sha1(str(sector_offsets).encode("UTF-8")).digest()).decode("ASCII", "ignore")[:4]

			# Delta ranges
			if len(sector_offsets) > 1: # and self.MODE == "AGB":
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
				else:
					write_sectors = sector_offsets
			dprint("Sectors to update:", write_sectors)
		# ↑↑↑ Read Sector Map
		
		# ↓↓↓ Chip erase
		chip_erase = False
		if flashcart.SupportsChipErase():
			if flashcart.SupportsSectorErase() and args["prefer_chip_erase"] is False and sector_map is not False:
				chip_erase = False
			else:
				chip_erase = True
				if flashcart.ChipErase() is False:
					return False
		elif flashcart.SupportsSectorErase() is False:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"No erase method available.", "abortable":False})
			return False
		# ↑↑↑ Chip erase
		
		# ↓↓↓ Flash Write
		self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE", "size":len(data_import)})
		self.SetProgress({"action":"UPDATE_POS", "pos":0})
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
		retry_hp = 100
		end_address = len(data_import)
		dprint("ROM banks:", end_bank)

		if chip_erase:
			write_sectors = [[ 0, len(data_import) ]]
		elif write_sectors is None or len(write_sectors) == 0:
			write_sectors = sector_offsets

		for sector in write_sectors:
			if chip_erase is False:
				retry_hp = 100
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
					if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
						flashcart.Reset(full_reset=True)
						flashcart.SelectBankROM(bank)
						temp = end_address - start_address
						start_address %= cart_type["flash_bank_size"]
						#end_address = start_address + temp
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
							status = self.WriteROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], flash_buffer_size=flash_buffer_size, skip_init=(skip_init and not self.SKIPPING), rumble_stop=rumble)
					
					if status is False or se_ret is False:
						self.CANCEL = True
						self.ERROR = True
						if "from_user" in self.CANCEL_ARGS and self.CANCEL_ARGS["from_user"]:
							break
						elif buffer_pos == 0:
							self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"An error occured while writing 0x{:X} bytes at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTips:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n- Check cartridge type selection{:s}".format(buffer_len, buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False), errmsg_mbc_selection)})
						else:
							if chip_erase: retry_hp = 0
							if "iteration" in self.ERROR_ARGS and self.ERROR_ARGS["iteration"] > 0:
								retry_hp -= 5
								if retry_hp <= 0:
									self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"Unstable connection detected while writing 0x{:X} bytes in iteration {:d} at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTips:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables".format(buffer_len, self.ERROR_ARGS["iteration"], buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False))})
									continue
							else:
								retry_hp -= 10
								if retry_hp <= 0:
									self.CANCEL_ARGS.update({"info_type":"msgbox_critical", "info_msg":"An error occured while writing 0x{:X} bytes at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTips:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n- Check cartridge type selection\n- Check cartridge ROM storage size (at least {:s} is required){:s}".format(buffer_len, buffer_pos, Util.formatFileSize(size=buffer_pos, asInt=False), Util.formatFileSize(len(data_import), asInt=False), errmsg_mbc_selection), "abortable":False})
									continue
							
							self.CANCEL_ARGS = {}
							self.CANCEL = False
							self.ERROR = False

							rev_buffer_pos = sector_offsets[sector_pos - 1][0]
							buffer_pos = rev_buffer_pos
							bank = start_bank
							sector_pos -= 1
							err_text = "Write error! Retrying from 0x{:X}...".format(rev_buffer_pos)
							if not Util.DEBUG: print(err_text)
							dprint(err_text, "Bank {:d} | HP: {:d}/100".format(bank, retry_hp))
							pos = end_address
							status = False

							self.SetProgress({"action":"ERROR", "abortable":True, "pos":buffer_pos, "text":"Write error! Retrying from 0x{:X}...".format(rev_buffer_pos)})
							delay = 0.5 + (100-retry_hp)/50
							if self.CanPowerCycleCart():
								self.CartPowerOff(0)
								time.sleep(delay)
								self.CartPowerOn()
								if self.MODE == "DMG" and _mbc.HasFlashBanks(): _mbc.SelectBankFlash(bank)
							time.sleep(delay)
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

		if delta_state_new is not None and not chip_erase:
			try:
				with open(json_file, "wb") as f:
					f.write(json.dumps(delta_state_new).encode("UTF-8-SIG"))
			except PermissionError:
				print("Error: Couldn’t update write-protected file “{:s}”".format(json_file))
		
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
		#self.SetMode(self.MODE)
		# ↑↑↑ Reset flash

		# ↓↓↓ Flash verify
		verified = False
		if "verify_write" in args and args["verify_write"] is True:
			self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE_VERIFY", "size":len(data_import)})
			if Util.DEBUG:
				with open("debug_verify.bin", "wb") as f: pass
			for sector in write_sectors:
				verified = True
				if sector[0] >= len(data_import): break
				verify_args = copy.copy(args)
				verify_args.update({"verify_write":data_import[sector[0]:sector[0]+sector[1]], "rom_size":len(data_import), "verify_from":sector[0], "path":"", "rtc_area":flashcart.HasRTC(), "verify_mbc":_mbc})
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
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The ROM was written completely, but verification of written data failed at position 0x{:X} ({:s}). Please re-connect the device and try again from the beginning.\n\nTips:\n- Clean cartridge contacts\n- Avoid passive USB hubs and try different USB ports/cables\n- Check cartridge type selection\n- Check cartridge ROM storage size (at least {:s} is required){:s}".format(sector[0]+verified_size, Util.formatFileSize(sector[0]+verified_size, asInt=False), Util.formatFileSize(len(data_import), asInt=False), errmsg_mbc_selection), "abortable":False})
					verified = False
					return False
		# ↑↑↑ Flash verify

		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
			self._set_fw_variable("DMG_ROM_BANK", 0)
		elif self.MODE == "AGB":
			if "flash_bank_select_type" in cart_type and cart_type["flash_bank_select_type"] == 1:
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
		if self.IsConnected():
			if self.FW["pcb_ver"] in (5, 6, 101):
				self._write(self.DEVICE_CMD["OFW_CART_MODE"])
				self._read(1)
				self.CartPowerOn()
			
			ret = False
			self.SIGNAL = signal
			try:
				if args['mode'] == 1: ret = self._BackupROM(args)
				elif args['mode'] == 2: ret = self._BackupRestoreRAM(args)
				elif args['mode'] == 3: ret = self._BackupRestoreRAM(args)
				elif args['mode'] == 4: ret = self._FlashROM(args)
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
