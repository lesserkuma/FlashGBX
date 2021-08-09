# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import time, math, struct, traceback, zlib, copy, hashlib, os, datetime, platform
import serial, serial.tools.list_ports
from serial import SerialException
from .RomFileDMG import RomFileDMG
from .RomFileAGB import RomFileAGB
from .Mapper import DMG_MBC, AGB_GPIO
from .Flashcart import Flashcart, Flashcart_DMG_MMSA
from .Util import ANSI, dprint, bitswap, ParseCFI
from . import Util

class GbxDevice:
	DEVICE_NAME = "GBxCart RW"
	DEVICE_MIN_FW = 1
	DEVICE_MAX_FW = 2
	
	DEVICE_CMD = {
		"NULL":0x30,
		"OFW_RESET_AVR":0x2A,
		"OFW_CART_MODE":0x43,
		"OFW_FW_VER":0x56,
		"OFW_PCB_VER":0x68,
		"OFW_USART_1_7M_SPEED":0x3E,
		"OFW_CART_PWR_ON":0x2F,
		"OFW_CART_PWR_OFF":0x2E,
		"OFW_QUERY_CART_PWR":0x5D,
		"OFW_DONE_LED_ON":0x3D,
		"OFW_ERROR_LED_ON":0x3F,
		"OFW_GB_CART_MODE":0x47,
		"OFW_GB_FLASH_BANK_1_COMMAND_WRITES":0x4E,
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
		"DMG_CART_READ":0xB1,
		"DMG_CART_WRITE":0xB2,
		"DMG_CART_WRITE_SRAM":0xB3,
		"DMG_MBC_RESET":0xB4,
		"DMG_MBC7_READ_EEPROM":0xB5,
		"DMG_MBC7_WRITE_EEPROM":0xB6,
		"DMG_MBC6_MMSA_WRITE_FLASH":0xB7,
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
		"AGB_FLASH_WRITE_BYTE":0xD2,
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
	}

	PCB_VERSIONS = {4:'v1.3', 5:'v1.4'}
	ACTIONS = {"ROM_READ":1, "SAVE_READ":2, "SAVE_WRITE":3, "ROM_WRITE":4, "ROM_WRITE_VERIFY":4}
	SUPPORTED_CARTS = {}
	
	FW = []
	FW_UPDATE_REQ = False
	MODE = None
	PORT = ''
	DEVICE = None
	WORKER = None
	INFO = { "action":None, "last_action":None }
	ERROR = False
	CANCEL = False
	CANCEL_ARGS = {}
	SIGNAL = None
	POS = 0
	NO_PROG_UPDATE = False
	FAST_READ = False
	SKIPPING = False
	BAUDRATE = 1000000
	MAX_BUFFER_LEN = 512
	
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
					#break
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
						return False
				elif max_baud >= 1700000 and self.FW["pcb_ver"] == 5 and self.BAUDRATE < 1700000:
					# Switch to higher baud rate
					self._write(self.DEVICE_CMD["OFW_USART_1_7M_SPEED"])
					self.BAUDRATE = 1700000
					dev.close()
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
					return False
				elif self.FW["fw_ver"] < self.DEVICE_MIN_FW:
					dev.close()
					self.DEVICE = None
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " requires a firmware update to work with this software. Please try again after updating it to version L" + str(self.DEVICE_MIN_FW) + " or higher.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
					continue
				#elif self.FW["fw_ver"] < self.DEVICE_MAX_FW:
				#	conn_msg.append([1, "The GBxCart RW device on port " + ports[i] + " is running an older firmware version. Please consider updating to version L" + str(self.DEVICE_MAX_FW) + " to make use of the latest features.<br><br>Firmware updates are available at <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a>."])
				elif self.FW["fw_ver"] > self.DEVICE_MAX_FW:
					conn_msg.append([0, "NOTE: The GBxCart RW device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
				
				if (self.FW["pcb_ver"] not in (4, 5)): # only the v1.3 and v1.4 pcb revisions are supported
					dev.close()
					self.DEVICE = None
					return False
				
				conn_msg.append([0, "For help please visit the insideGadgets Discord: https://gbxcart.com/discord"])

				self.PORT = ports[i]
				self.DEVICE.timeout = 1
				
				# Load Flash Cartridge Handlers
				self.UpdateFlashCarts(flashcarts)

				# Stop after first found device
				break
			
			except SerialException as e:
				if "Permission" in str(e):
					conn_msg.append([3, "The GBxCart RW device on port " + ports[i] + " couldn’t be accessed. Make sure your user account has permission to use it and it’s not already in use by another application."])
					print(str(e))
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
	
	def CanSetVoltageManually(self):
		return False
	
	def CanSetVoltageAutomatically(self):
		return True
	
	def GetSupprtedModes(self):
		return ["DMG", "AGB"]
	
	def IsSupportedMbc(self, mbc):
		return mbc in ( 0x00, 0x01, 0x02, 0x03, 0x06, 0x0B, 0x0D, 0x10, 0x13, 0x19, 0x1A, 0x1B, 0x1C, 0x1E, 0x20, 0x22, 0xFC, 0xFD, 0xFE, 0xFF, 0x101, 0x103, 0x104, 0x105 )
	
	def IsSupported3dMemory(self):
		return True
	
	def IsClkConnected(self):
		return self.FW["pcb_ver"] == 5

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
				dprint("Clearing input buffer... ({:d})".format(self.DEVICE.in_waiting), self.DEVICE.read(self.DEVICE.in_waiting))
				self.DEVICE.reset_input_buffer()
				time.sleep(0.5)
			self.DEVICE.reset_output_buffer()
			return self.LoadFirmwareVersion()
		except SerialException as e:
			print(str(e))
			return False
	
	def Close(self):
		if self.IsConnected():
			try:
				if self.FW["pcb_ver"] == 5:
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
		if self.FW["pcb_ver"] == 5:
			s = "R{:d}+{:s}{:d}".format(self.FW["ofw_ver"], self.FW["cfw_id"], self.FW["fw_ver"])
		else:
			s = "{:s}{:d}".format(self.FW["cfw_id"], self.FW["fw_ver"])
		if more:
			s += " (dated {:s})".format(self.FW["fw_dt"])
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
			return "{:s} – Firmware {:s} ({:s}) (dated {:s}) at {:.1f}M baud".format(self.GetFullName(), self.GetFirmwareVersion(), self.PORT, self.FW["fw_dt"], self.BAUDRATE/1000/1000)
		else:
			return "{:s} – Firmware {:s} ({:s})".format(self.GetFullName(), self.GetFirmwareVersion(), self.PORT)

	def SupportsFirmwareUpdates(self):
		#if self.FW["pcb_ver"] != 4: return False
		return self.FW["pcb_ver"] in (4, 5)

	def FirmwareUpdateAvailable(self):
		if self.FW["pcb_ver"] != 5: return False
		#return self.FW["fw_ver"] < self.DEVICE_MAX_FW
		return (self.FW["pcb_ver"] in (4, 5) and self.FW["fw_ver"] < self.DEVICE_MAX_FW)
	
	def GetFirmwareUpdaterClass(self):
		if self.FW["pcb_ver"] == 4: # v1.3
			try:
				from . import fw_GBxCartRW_v1_3
				return (None, fw_GBxCartRW_v1_3.FirmwareUpdaterWindow)
			except:
				return False
		elif self.FW["pcb_ver"] == 5: # v1.4
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
	
	def wait_for_ack(self, values=[0x01, 0x03]):
		buffer = self._read(1)
		if buffer not in values:
			tb_stack = traceback.extract_stack()
			stack = tb_stack[len(tb_stack)-2] # caller only
			if stack.name == "_write": stack = tb_stack[len(tb_stack)-3]
			print("{:s}Waiting for confirmation from the device has failed. (Called from {:s}(), line {:d}){:s}\n".format(ANSI.RED, stack.name, stack.lineno, ANSI.RESET))
			self.CANCEL = True
			self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"An error occured while waiting for confirmation from the device. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning."}
			self.ERROR = True
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
		if platform.system() == "Darwin":
			time.sleep(0.00125)
		
		if wait: return self.wait_for_ack()
	
	def _read(self, count):
		if self.DEVICE.in_waiting > 1000: dprint("in_waiting = {:d} bytes".format(self.DEVICE.in_waiting))
		buffer = self.DEVICE.read(count)
		if len(buffer) != count:
			dprint("Error: Received {:d} byte(s) instead of the expected {:d} byte(s)".format(len(buffer), count))
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
				return struct.unpack("B", self.ReadROM(address, 1))[0]
			else:
				return self.ReadROM(address, length)
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
		dprint("Writing to cartridge: 0x{:X} = 0x{:X}".format(address, value & 0xFF), flashcart, sram)
		if self.MODE == "DMG":
			if flashcart:
				buffer = bytearray([self.DEVICE_CMD["DMG_FLASH_WRITE_BYTE"]])
			else:
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
				buffer = bytearray([self.DEVICE_CMD["AGB_FLASH_WRITE_BYTE"]])
			else:
				buffer = bytearray([self.DEVICE_CMD["AGB_CART_WRITE"]])
			
			buffer.extend(struct.pack(">I", address >> 1))
			buffer.extend(struct.pack(">H", value & 0xFFFF))
		self._write(buffer)
	
	def _cart_write_flash(self, commands):
		num = len(commands)
		buffer = bytearray([self.DEVICE_CMD["CART_WRITE_FLASH_CMD"]])
		buffer.extend(struct.pack("B", num))
		for i in range(0, num):
			#dprint("Writing to cartridge: 0x{:X} = 0x{:X}".format(commands[i][0], commands[i][1] & 0xFF))
			buffer.extend(struct.pack(">I", commands[i][0]))
			buffer.extend(struct.pack("B", commands[i][1]))
		
		self._write(buffer)

		if self._read(1) != 0x01:
			print("Error!")

	def _clk_toggle(self, num):
		if self.FW["pcb_ver"] != 5: return False
		for _ in range(0, num):
			self._write(self.DEVICE_CMD["CLK_HIGH"])
			self._write(self.DEVICE_CMD["CLK_LOW"])
		return True

	def CartPowerOff(self):
		if self.FW["pcb_ver"] == 5:
			self._write(self.DEVICE_CMD["OFW_CART_PWR_OFF"])
			time.sleep(0.05)
	
	def CartPowerOn(self):
		if self.FW["pcb_ver"] == 5:
			self._write(self.DEVICE_CMD["OFW_QUERY_CART_PWR"])
			if self._read(1) == 0:
				self._write(self.DEVICE_CMD["OFW_CART_PWR_ON"])
				time.sleep(0.1)
				self.DEVICE.reset_input_buffer() # bug workaround

	def GetMode(self):
		return self.MODE
	
	def SetMode(self, mode):
		self.CartPowerOff()
		if mode == "DMG":
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			self.MODE = "DMG"
		elif mode == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			self.MODE = "AGB"
		self._set_fw_variable(key="ADDRESS", value=0)
		self.CartPowerOn()
	
	def GetSupportedCartridgesDMG(self):
		return (list(self.SUPPORTED_CARTS['DMG'].keys()), list(self.SUPPORTED_CARTS['DMG'].values()))
	
	def GetSupportedCartridgesAGB(self):
		return (list(self.SUPPORTED_CARTS['AGB'].keys()), list(self.SUPPORTED_CARTS['AGB'].values()))
	
	def SetProgress(self, args):
		if self.CANCEL and args["action"] != "ABORT": return
		if args["action"] == "UPDATE_POS":
			self.POS = args["pos"]
			self.INFO["transferred"] = args["pos"]
		try:
			self.SIGNAL.emit(args)
		except AttributeError:
			if self.SIGNAL is not None:
				self.SIGNAL(args)
		if args["action"] == "FINISHED": self.SIGNAL = None
	
	def ReadInfo(self, setPinsAsInputs=False):
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		if self.FW["pcb_ver"] == 5:
			self._write(self.DEVICE_CMD["OFW_CART_MODE"]) # Reset LEDs
			self._read(1)
			self.CartPowerOn()
		
		data = {}
		self.POS = 0
		
		if self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
		elif self.MODE == "AGB":
			if self.FW["pcb_ver"] == 5 and self.FW["fw_ver"] > 1:
				self._write(self.DEVICE_CMD["AGB_BOOTUP_SEQUENCE"], wait=True)
		
		header = self.ReadROM(0, 0x180)
		if header is False or len(header) != 0x180: raise Exception("Couldn’t read the cartridge information. Please try again.")
		if Util.DEBUG:
			with open("debug_header.bin", "wb") as f: f.write(header)
		
		# Check for DACS
		dacs_8m = False
		if self.FW["pcb_ver"] != 5 or self.FW["fw_ver"] == 1:
			if header[0x04:0x04+0x9C] == bytearray([0x00] * 0x9C):
				self.ReadROM(0x1FFFFE0, 20) # Unlock DACS
				header = self.ReadROM(0, 0x180)
		temp = self.ReadROM(0x1FFE000, 0x0C)
		if temp == b"AGBFLASHDACS":
			dacs_8m = True
		
		# Parse ROM header
		if self.MODE == "DMG":
			data = RomFileDMG(header).GetHeader()
			if data["logo_correct"] is False: # try to fix weird bootlegs
				self._cart_write(0, 0xFF)
				time.sleep(0.1)
				header = self.ReadROM(0, 0x180)
				data = RomFileDMG(header).GetHeader()
			
			_mbc = DMG_MBC().GetInstance(args={"mbc":data["features_raw"]}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
			data["has_rtc"] = _mbc.HasRTC() is True
		
		elif self.MODE == "AGB":
			data = RomFileAGB(header).GetHeader()
			if data["logo_correct"] is False: # try to fix weird bootlegs
				self._cart_write(0, 0xFF)
				time.sleep(0.1)
				header = self.ReadROM(0, 0x180)
				data = RomFileAGB(header).GetHeader()

			size_check = header[0xA0:0xA0+16]
			currAddr = 0x400000
			while currAddr < 0x2000000:
				buffer = self.ReadROM(currAddr + 0x0000A0, 64)[:16]
				if buffer == size_check: break
				currAddr += 0x400000
			data["rom_size"] = currAddr
			if (data["3d_memory"] == True):
				data["rom_size"] = 0x4000000
			elif dacs_8m:
				data["dacs_8m"] = True
			
			if data["logo_correct"] is True and header[0xC5] == 0 and header[0xC7] == 0 and header[0xC9] == 0:
				_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
				has_rtc = _agb_gpio.HasRTC()
				data["has_rtc"] = has_rtc is True
				if has_rtc is not True:
					data["no_rtc_reason"] = has_rtc
			else:
				data["has_rtc"] = False
				data["no_rtc_reason"] = None
		
		dprint("Header data:", data)
		self.INFO = {**self.INFO, **data}
		self.INFO["flash_type"] = 0
		self.INFO["last_action"] = 0
		
		if self.MODE == "DMG" and setPinsAsInputs: self._write(self.DEVICE_CMD["SET_ADDR_AS_INPUTS"])
		return data
	
	def ReadROM(self, address, length, skip_init=False, max_length=64):
		num = math.ceil(length / max_length)
		dprint("Reading 0x{:X} bytes from ROM at 0x{:X} in {:d} iteration(s)".format(length, address, num))
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
		
		#with open("debug.bin", "ab") as f: f.write(buffer)
		return buffer

	def ReadROM_3DMemory(self, address, length, max_length=512):
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
				self.SetProgress({"action":"READ", "bytes_added":buffer_size})
			self._write(0)

		#dprint(hex(len(buffer)))
		return buffer

	def ReadRAM(self, address, length, command=None, max_length=512):
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
			if self.INFO["action"] == self.ACTIONS["SAVE_READ"] and not self.NO_PROG_UPDATE:
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
			if self.INFO["action"] == self.ACTIONS["SAVE_READ"] and not self.NO_PROG_UPDATE:
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
			self._cart_write(0xA001, Util.TAMA5_REG.ADDR_H_SET_MODE.value) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | Util.TAMA5_CMD.RAM_READ.value << 1) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, Util.TAMA5_REG.ADDR_L.value) # address (low)
			self._cart_write(0xA000, i & 0x0F) # bits 0-3 = lower ram address
			self._cart_write(0xA001, Util.TAMA5_REG.MEM_READ_H.value) # data out (high)
			time.sleep(0.03)
			data_h = self._cart_read(0xA000)
			self._cart_write(0xA001, Util.TAMA5_REG.MEM_READ_L.value) # data out (low)
			time.sleep(0.03)
			data_l = self._cart_read(0xA000)
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
				self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"Save write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)}
				self.CANCEL = True
				self.ERROR = True
				return False
			self._cart_write(address + length - 1, 0x00)
			while True: # TODO: error handling
				sr = self._cart_read(address + length - 1)
				#print("sr=0x{:X}".format(sr))
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
			dprint("Response:", response) # TODO: error handling
			if self.INFO["action"] == self.ACTIONS["SAVE_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})

	def WriteRAM_TAMA5(self, buffer):
		self.NO_PROG_UPDATE = True

		for i in range(0, 0x20):
			self._cart_write(0xA001, Util.TAMA5_REG.MEM_WRITE_H.value) # data in (high)
			self._cart_write(0xA000, buffer[i] >> 4)
			self._cart_write(0xA001, Util.TAMA5_REG.MEM_WRITE_L.value) # data in (low)
			self._cart_write(0xA000, buffer[i] & 0xF)
			self._cart_write(0xA001, Util.TAMA5_REG.ADDR_H_SET_MODE.value) # register select and address (high)
			self._cart_write(0xA000, i >> 4 | Util.TAMA5_CMD.RAM_WRITE.value << 1) # bit 0 = higher ram address, rest = command
			self._cart_write(0xA001, Util.TAMA5_REG.ADDR_L.value) # address (low)
			self._cart_write(0xA000, i & 0x0F) # bits 0-3 = lower ram address
			time.sleep(0.03)
			self.SetProgress({"action":"UPDATE_POS", "abortable":False, "pos":i+1})
		
		self.NO_PROG_UPDATE = False

	def WriteROM(self, address, buffer, flash_buffer_size=False, skip_init=False, rumble_stop=False):
		length = len(buffer)
		if self.FW["pcb_ver"] != 5:
			max_length = 256
		else:
			max_length = 1024
		num = math.ceil(length / max_length)
		dprint("Writing 0x{:X} bytes to Flash ROM in {:d} iteration(s)".format(length, num))
		if length > max_length: length = max_length
		
		skip_write = False
		ret = 0
		num_of_chunks = math.ceil(flash_buffer_size / length)
		pos = 0

		if not skip_init:
			self._set_fw_variable("TRANSFER_SIZE", length)
			if flash_buffer_size is not False:
				self._set_fw_variable("BUFFER_SIZE", flash_buffer_size)
		
		for i in range(0, num):
			if rumble_stop:
				dprint("Sending rumble stop command")
				self._cart_write(address=0xC6, value=0x00, flashcart=True)
			
			data = bytearray(buffer[i*length:i*length+length])
			if (num_of_chunks == 1 or flash_buffer_size == 0) and (data == bytearray([0xFF] * len(data))):
				skip_init = False
				skip_write = True
				#dprint("Skipping empty data in iteration {:d}".format(i))
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
					self._write(self.DEVICE_CMD["FLASH_PROGRAM"])
				ret = self._write(data, wait=True)
				
				if ret not in (0x01, 0x03):
					print("{:s}Flash error at 0x{:X} in iteration {:d} of {:d} while trying to write a total of 0x{:X} bytes (response = {:s}){:s}".format(ANSI.RED, address, i, num, len(buffer), str(ret), ANSI.RESET))
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
			#dprint("Now in iteration {:d}".format(i))
			
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
				self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"Save write error (response = {:s}) in iteration {:d} while trying to write 0x{:X} bytes".format(str(ret), i, length)}
				self.CANCEL = True
				self.ERROR = True
				return False
			
			self._cart_write(address + length - 1, 0xFF)
			while True: # TODO: error handling
				sr = self._cart_read(address + length - 1)
				#print("sr=0x{:X}".format(sr))
				if sr == 0x80: break
				time.sleep(0.001)

			address += length
			if self.INFO["action"] == self.ACTIONS["ROM_WRITE"] and not self.NO_PROG_UPDATE:
				self.SetProgress({"action":"WRITE", "bytes_added":length})
		
		self._cart_write(address - 1, 0xF0)
		self.SKIPPING = skip_write
	
	def CheckROMStable(self):
		if not self.IsConnected(): raise Exception("Couldn’t access the the device.")
		buffer1 = self.ReadROM(0, 0xC0)
		time.sleep(0.05)
		buffer2 = self.ReadROM(0, 0xC0)
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
			time.sleep(0.25)
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
		elif self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
		
		for f in range(2, len(supported_carts)):
			flashcart_meta = supported_carts[f]
			if flash_id is not None:
				if ("flash_ids" not in flashcart_meta) or (flash_id not in flashcart_meta["flash_ids"]):
					continue
			dprint("*** Now checking: {:s}\n".format(flashcart_meta["names"][0]))
			
			if self.MODE == "DMG":
				#self._set_fw_variable("FLASH_COMMANDS_BANK_1", "flash_commands_on_bank_1" in flashcart_meta)
				if flashcart_meta["write_pin"] == "WR":
					we = 0x01 # FLASH_WE_PIN_WR
				elif flashcart_meta["write_pin"] in ("AUDIO", "VIN"):
					we = 0x02 # FLASH_WE_PIN_AUDIO
				elif flashcart_meta["write_pin"] == "WR+RESET":
					we = 0x03 # FLASH_WE_PIN_WR_RESET
				self._set_fw_variable("FLASH_WE_PIN", we)

			flashcart = Flashcart(config=flashcart_meta, cart_write_fncptr=self._cart_write, cart_read_fncptr=self.ReadROM)
			flashcart.Reset(full_reset=False)
			flashcart.Unlock()
			if "flash_ids" in flashcart_meta:
				vfid = flashcart.VerifyFlashID()
				if vfid is not False:
					(verified, cart_flash_id) = flashcart.VerifyFlashID()
					if verified and cart_flash_id in flashcart_meta["flash_ids"]:
						flash_id = cart_flash_id
						flash_id_found = True
						flash_type = f
						flash_types.append(flash_type)
						flashcart.Reset(full_reset=False)
						dprint("Found the correct cartridge type!")
		
		if self.MODE == "DMG" and not flash_id_found:
			self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.25)

		return flash_types

	def CheckFlashChip(self, limitVoltage=False, cart_type=None): # aka. the most horribly written function
		if self.FW["pcb_ver"] == 5:
			self._write(self.DEVICE_CMD["OFW_CART_MODE"])
			self._read(1)
			self.CartPowerOn()
		
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
		
		check_buffer = self.ReadROM(0, 0x400)
		d_swap = None
		cfi_info = ""
		rom_string = ""
		for j in range(0, 8):
			rom_string += "{:02X} ".format(check_buffer[j])
		rom_string += "\n"
		cfi = {'raw':b''}
		
		if self.MODE == "DMG":
			if limitVoltage:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_3_3V"])
			else:
				self._write(self.DEVICE_CMD["SET_VOLTAGE_5V"])
			time.sleep(0.25)
			rom_string = "[     ROM     ] " + rom_string
			we_pins = [ "WR", "AUDIO" ]
		else:
			rom_string = "[   ROM   ] " + rom_string
			we_pins = [ None ]
		
		for we in we_pins:
			if "method" in cfi: break
			for method in flash_commands:
				if self.MODE == "DMG":
					#self._set_fw_variable("FLASH_COMMANDS_BANK_1", "flash_commands_on_bank_1" in flashcart_meta)
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
					#cfi["sha1"] = hashlib.sha1(buffer).hexdigest()
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
						flash_id = self.ReadROM(0, 64)[0:8]
						if flash_id == check_buffer[:len(flash_id)]: continue

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
					flashcart_meta = copy.deepcopy(cart_type)
					if "reset" in flashcart_meta["commands"]:
						for i in range(0, len(flashcart_meta["commands"]["reset"])):
							self._cart_write(flashcart_meta["commands"]["reset"][i][0], flashcart_meta["commands"]["reset"][i][1], flashcart=True)
		
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
			if cfi["tb_boot_sector"] is not False: s += "Sector order: {:s}\n".format(str(cfi["tb_boot_sector"]))
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
					flash_id = self.ReadROM(0, 64)[0:8]
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
				time.sleep(0.25)
		
		flash_id = ""
		for i in range(0, len(flash_id_lines)):
			flash_id += flash_id_lines[i][0] + " "
			for j in range(0, 8):
				flash_id += "{:02X} ".format(flash_id_lines[i][1][j])
			flash_id += "\n"
		
		flash_id = rom_string + flash_id
		return (flash_id, cfi_info, cfi)
	
	#################################################################

	def BackupROM(self, fncSetProgress=None, args={}):
		from . import DataTransfer
		args['mode'] = 1
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(args)
		self.WORKER.start()
	
	def BackupRAM(self, fncSetProgress=None, args={}):
		from . import DataTransfer
		args['mode'] = 2
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(args)
		self.WORKER.start()
	
	def RestoreRAM(self, fncSetProgress=None, args={}):
		from . import DataTransfer
		args['mode'] = 3
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(args)
		self.WORKER.start()
	
	def FlashROM(self, fncSetProgress=None, args={}):
		from . import DataTransfer
		args['mode'] = 4
		args['port'] = self
		if self.WORKER is None:
			self.WORKER = DataTransfer.DataTransfer(args)
			self.WORKER.updateProgress.connect(fncSetProgress)
		else:
			self.WORKER.setConfig(args)
		self.WORKER.start()
	
	#################################################################

	def _BackupROM(self, args):
		file = None
		if len(args["path"]) > 0:
			file = open(args["path"], "wb")
		
		self.FAST_READ = args["fast_read_mode"]

		flashcart = False
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = copy.deepcopy(supported_carts[args["cart_type"]])
		if not isinstance(cart_type, str):
			cart_type["_index"] = 0
			for i in range(0, len(list(self.SUPPORTED_CARTS[self.MODE].keys()))):
				if i == args["cart_type"]:
					try:
						cart_type["_index"] = cart_type["names"].index(list(self.SUPPORTED_CARTS[self.MODE].keys())[i])
						flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_read_fncptr=self.ReadROM, progress_fncptr=self.SetProgress)
					except:
						pass

		buffer_len = 0x4000
		if self.MODE == "DMG":
			_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			if _mbc.GetName() == "TAMA5":
				self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
				self._set_fw_variable("DMG_READ_CS_PULSE", 1)
				_mbc.EnableMapper() # TODO: error handling
				self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			else:
				_mbc.EnableMapper()
			
			rom_banks = args['rom_banks']
			if _mbc.GetName() in ("MBC6", "M161"): rom_banks = _mbc.GetROMBanks(args['rom_banks'] * 0x4000)
			size = _mbc.GetROMSize()
		
		elif self.MODE == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			buffer_len = 0x10000
			if "agb_rom_size" in args: size = args["agb_rom_size"]
			if flashcart and "flash_bank_size" in cart_type:
				if "verify_flash" in args:
					rom_banks = math.ceil(len(args["verify_flash"]) / cart_type["flash_bank_size"])
				else:
					rom_banks = int(min(size, cart_type["flash_size"]) / cart_type["flash_bank_size"])
			else:
				rom_banks = 1
		
		if "verify_flash" in args:
			size = len(args["verify_flash"])
		else:
			method = "ROM_READ"
			self.SetProgress({"action":"INITIALIZE", "method":method, "size":size})
			self.INFO["action"] = self.ACTIONS[method]
		
		buffer = bytearray(size)
		max_length = self.MAX_BUFFER_LEN
		if self.FAST_READ is True: max_length = 0x2000
		pos_total = 0
		start_address = 0
		end_address = size
		dprint("ROM banks:", rom_banks)
		for bank in range(0, rom_banks):
			if self.MODE == "DMG":
				if _mbc.ResetBeforeBankChange(bank) is True:
					dprint("Resetting the MBC")
					self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
				(start_address, bank_size) = _mbc.SelectBankROM(bank)
				end_address = start_address + bank_size
				buffer_len = _mbc.GetROMBankSize()
			elif self.MODE == "AGB" and rom_banks > 1:
				if cart_type["flash_bank_select_type"] == 1:
					flashcart.SelectBankROM(bank)
					start_address = 0
					end_address = cart_type["flash_bank_size"]
			
			'''
			if "verify_flash" in args and "dacs" in args and args["dacs"] is True:
				start_address = args["start_address"]
				end_address = args["end_address"]
				buffer += bytearray(start_address)
			'''

			skip_init = False
			pos = start_address
			lives = 20
			while pos < end_address:
				temp = bytearray()
				if self.CANCEL:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.SetProgress(cancel_args)
					try:
						if file is not None: file.close()
					except:
						pass
					return
				
				if (self.MODE == "AGB" and self.INFO["3d_memory"]):
					temp = self.ReadROM_3DMemory(address=pos, length=buffer_len, max_length=max_length)
				else:
					temp = self.ReadROM(address=pos, length=buffer_len, skip_init=skip_init, max_length=max_length)
					skip_init = True
				
				if len(temp) != buffer_len:
					if (max_length >> 1) < 64:
						dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}!".format(len(temp), buffer_len, pos_total))
						max_length = 64
					else:
						dprint("Received 0x{:X} bytes instead of 0x{:X} bytes from the device at position 0x{:X}! Decreasing maximum transfer buffer length to 0x{:X}.".format(len(temp), buffer_len, pos_total, max_length >> 1))
						max_length >>= 1
						self.MAX_BUFFER_LEN = max_length
					skip_init = False
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					lives -= 1
					if lives == 0:
						self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error occured while reading from the cartridge. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.", "abortable":False})
						return False
					continue
				elif lives < 20:
					lives = 20
				
				if file is not None: file.write(temp)
				buffer[pos_total:pos_total+len(temp)] = temp
				pos_total += len(temp)
				
				if "verify_flash" in args:
					check = args["verify_flash"][pos_total-len(temp):pos_total]
					if temp[:len(check)] != check:
						for i in range(0, pos_total):
							if (i < len(args["verify_flash"]) - 1) and (i < pos_total - 1) and args["verify_flash"][i] != buffer[i]:
								if args["rtc_area"] is True and i in (0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9):
									dprint("Skipping RTC area at 0x{:X}".format(i))
								else:
									dprint("Mismatch during verification at 0x{:X}".format(i))
									return i
					else:
						dprint("Verification successful between 0x{:X} and 0x{:X}".format(pos_total-len(temp), pos_total-1))

				self.SetProgress({"action":"UPDATE_POS", "pos":pos_total})
				pos += buffer_len
		
		if file is not None: file.close()
		
		if "verify_flash" in args:
			return min(pos_total, len(args["verify_flash"]))
		
		# Hidden sector (GB Memory)
		if self.MODE == "DMG":
			if len(args["path"]) > 0 and _mbc.HasHiddenSector():
				file = open(os.path.splitext(args["path"])[0] + ".map", "wb")
				temp = _mbc.ReadHiddenSector()
				self.INFO["hidden_sector"] = temp
				file.write(temp)
				file.close()
		
		# Calculate Global Checksum
		if self.MODE == "DMG":
			chk = _mbc.CalcChecksum(buffer)
		elif self.MODE == "AGB":
			chk = zlib.crc32(buffer) & 0xffffffff
		
		self.INFO["rom_checksum_calc"] = chk
		self.INFO["file_sha1"] = hashlib.sha1(buffer).hexdigest()
		
		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
		elif self.MODE == "AGB" and rom_banks > 1:
			if cart_type["flash_bank_select_type"] == 1:
				flashcart.SelectBankROM(0)
		# ↑↑↑ Switch to first ROM bank

		# Clean up
		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.SetProgress({"action":"FINISHED"})
		return True

	def _BackupRestoreRAM(self, args):
		_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
		self.FAST_READ = False
		if "rtc" not in args: args["rtc"] = False
		
		# Prepare some stuff
		command = None
		empty_data_byte = 0xFF
		extra_size = 0
		if self.MODE == "DMG":
			save_size = args["save_type"]
			ram_banks = _mbc.GetRAMBanks(save_size)
			buffer_len = min(0x2000, _mbc.GetRAMBankSize())
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			self._set_fw_variable("DMG_WRITE_CS_PULSE", 0)
			self._set_fw_variable("DMG_READ_CS_PULSE", 0)
			if _mbc.GetName() == "TAMA5":
				self._set_fw_variable("DMG_WRITE_CS_PULSE", 1)
				self._set_fw_variable("DMG_READ_CS_PULSE", 1)
				_mbc.EnableMapper() # TODO: error handling
				self._set_fw_variable("DMG_READ_CS_PULSE", 0)
				empty_data_byte = 0x00
				buffer_len = 0x20
			elif _mbc.GetName() == "MBC7":
				buffer_len = save_size
			elif _mbc.GetName() == "MBC6":
				self._set_fw_variable("FLASH_METHOD", 0x04) # FLASH_METHOD_DMG_MBC6
				self._set_fw_variable("FLASH_WE_PIN", 0x01) # WR
				_mbc.EnableFlash(enable=True, enable_write=True if (args["mode"] == 3) else False)
			else:
				_mbc.EnableMapper()
			
			if args["rtc"] is True:
				extra_size = _mbc.GetRTCBufferSize()
			
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
			elif args["save_type"] in (6, 7): # FLASH
				# Read Chip ID
				cmds = [
					[ 0x5555, 0xAA ],
					[ 0x2AAA, 0x55 ],
					[ 0x5555, 0x90 ]
				]
				self._cart_write_flash(cmds)
				time.sleep(0.01)
				agb_flash_chip = self._cart_read(0, agb_save_flash=True)
				if agb_flash_chip not in Util.AGB_Flash_Save_Chips:
					Util.AGB_Flash_Save_Chips[agb_flash_chip] = "Unknown flash chip ID (0x{:04X})".format(agb_flash_chip)
				dprint("Flash save chip:", Util.AGB_Flash_Save_Chips[agb_flash_chip])
				cmds = [
					[ 0x5555, 0xAA ],
					[ 0x2AAA, 0x55 ],
					[ 0x5555, 0xF0 ]
				]
				self._cart_write_flash(cmds)
				time.sleep(0.01)
				self._cart_write_flash([ [ 0, 0xF0 ] ])
				time.sleep(0.01)
				if agb_flash_chip == 0x1F3D:
					buffer_len = 128
				else:
					buffer_len = 0x1000
				buffer_len = 0x1000
			elif args["save_type"] == 8: # DACS
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
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], self.DEVICE_CMD["AGB_CART_WRITE_SRAM"] ], # 512K SRAM
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], self.DEVICE_CMD["AGB_CART_WRITE_SRAM"] ], # 1M SRAM
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_FLASH_DATA"], 2 if agb_flash_chip == 0x1F3D else 1]) ], # 512K FLASH
				[ self.DEVICE_CMD["AGB_CART_READ_SRAM"], bytearray([ self.DEVICE_CMD["AGB_CART_WRITE_FLASH_DATA"], 2 if agb_flash_chip == 0x1F3D else 1]) ], # 1M FLASH
				[ False, False ], # 8M DACS
			]
			command = commands[args["save_type"]][args["mode"] - 2]
			if args["rtc"] is True:
				extra_size = 0x10

		if args["mode"] == 2: # Backup
			action = "SAVE_READ"
			file = open(args["path"], "wb")
			buffer = bytearray()
		elif args["mode"] == 3: # Restore
			action = "SAVE_WRITE"
			self.INFO["save_erase"] = args["erase"]
			if args["erase"] == True:
				buffer = bytearray([ empty_data_byte ] * save_size)
			else:
				with open(args["path"], "rb") as f:
					buffer = bytearray(f.read())
				
				# Fill too small file
				if args["mode"] == 3 and len(buffer) < save_size:
					buffer = buffer + bytearray([ empty_data_byte ] * (save_size - len(buffer)))

		# Main loop
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
				else:
					self._set_fw_variable("DMG_WRITE_CS_PULSE", 1 if _mbc.WriteWithCSPulse() else 0)
					(start_address, bank_size) = _mbc.SelectBankRAM(bank)
					end_address = min(save_size, start_address + bank_size)
			elif self.MODE == "AGB":
				start_address = 0
				bank_size = 0x10000
				if args["save_type"] == 8: # DACS
					bank_size = 0xFC000
					end_address = 0xFC000
				else:
					end_address = min(save_size, bank_size)
				
				if save_size > bank_size:
					if args["save_type"] == 7: # FLASH 1M
						dprint("Switching to FLASH bank {:d}".format(bank))
						cmds = [
							[ 0x5555, 0xAA ],
							[ 0x2AAA, 0x55 ],
							[ 0x5555, 0xB0 ],
							[ 0, bank ]
						]
						self._cart_write_flash(cmds)
					elif args["save_type"] == 5: # SRAM 1M
						dprint("Switching to SRAM bank {:d}".format(bank))
						self._cart_write(0x1000000, bank)
					else:
						dprint("Unknown bank switching method")
					time.sleep(0.1)
			
			#buffer_offset = bank * bank_size
			max_length = 64
			dprint("start_address=0x{:X}, end_address=0x{:X}, buffer_len=0x{:X}, buffer_offset=0x{:X}".format(start_address, end_address, buffer_len, buffer_offset))
			pos = start_address
			while pos < end_address:
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
				
				if args["mode"] == 2: # Backup
					if self.MODE == "DMG" and _mbc.GetName() == "MBC7":
						temp = self.ReadRAM_MBC7(address=pos, length=buffer_len)
					elif self.MODE == "DMG" and _mbc.GetName() == "MBC6" and bank > 7: # MBC6 flash save memory
						temp = self.ReadROM(address=pos, length=buffer_len, skip_init=False, max_length=max_length)
					elif self.MODE == "DMG" and _mbc.GetName() == "TAMA5":
						temp = self.ReadRAM_TAMA5()
					elif self.MODE == "AGB" and args["save_type"] in (1, 2): # EEPROM
						temp = self.ReadRAM(address=int(pos/8), length=buffer_len, command=command, max_length=max_length)
					elif self.MODE == "AGB" and args["save_type"] == 8: # DACS
						temp = self.ReadROM(address=0x1F00000+pos, length=buffer_len, skip_init=False, max_length=max_length)
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
					
					file.write(temp)
					buffer += temp
					self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)})
				
				elif args["mode"] == 3: # Restore
					if self.MODE == "DMG" and _mbc.GetName() == "MBC7":
						self.WriteEEPROM_MBC7(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
					elif self.MODE == "DMG" and _mbc.GetName() == "MBC6" and bank > 7: # MBC6 flash save memory
						if self.FW["pcb_ver"] == 5:
							self.WriteROM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len])
							self._cart_write(pos + buffer_len - 1, 0xF0)
						else:
							self.WriteFlash_MBC6(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], mapper=_mbc)
					elif self.MODE == "DMG" and _mbc.GetName() == "TAMA5":
						self.WriteRAM_TAMA5(buffer=buffer[buffer_offset:buffer_offset+buffer_len])
					elif self.MODE == "AGB" and args["save_type"] in (1, 2): # EEPROM
						self.WriteRAM(address=int(pos/8), buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					elif self.MODE == "AGB" and args["save_type"] in (6, 7): # FLASH
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
							self.WriteRAM(address=pos, buffer=buffer[buffer_offset:buffer_offset+buffer_len], command=command)
					elif self.MODE == "AGB" and args["save_type"] == 8: # DACS
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
		
		if args["mode"] == 2: # Backup
			self.INFO["transferred"] = len(buffer)
			# Real Time Clock
			if args["rtc"] is True:
				if self.MODE == "DMG" and args["rtc"] is True:
					_mbc.LatchRTC()
					temp = _mbc.ReadRTC()
				elif self.MODE == "AGB":
					_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
					temp = _agb_gpio.ReadRTC()
				file.write(temp)
				self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)+len(temp)})
			
			file.close()
			self.INFO["file_sha1"] = hashlib.sha1(buffer).hexdigest()

		elif args["mode"] == 3: # Restore
			self.INFO["transferred"] = len(buffer)
			if args["rtc"] is True:
				advance = args["rtc_advance"]
				dprint("rtc_advance:", advance)
				if self.MODE == "DMG" and args["rtc"] is True:
					_mbc.WriteRTC(buffer[-_mbc.GetRTCBufferSize():], advance=advance)
				elif self.MODE == "AGB":
					_agb_gpio = AGB_GPIO(args={"rtc":True}, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)
					_agb_gpio.WriteRTC(buffer[-0x10:], advance=advance)
				self.SetProgress({"action":"UPDATE_POS", "pos":len(buffer)})
		
		if self.MODE == "DMG":
			_mbc.EnableRAM(enable=False)
		
		# Clean up
		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.INFO["last_path"] = args["path"]
		self.SetProgress({"action":"FINISHED"})
		return True

	def _FlashROM(self, args):
		self.FAST_READ = args["fast_read_mode"]
		
		if "buffer" in args:
			data_import = args["buffer"]
		else:
			with open(args["path"], "rb") as file:
				data_import = bytearray(file.read())
		if "start_addr" in args and args["start_addr"] > 0:
			data_import = bytearray(b'\xFF' * args["start_addr"]) + data_import
		
		# Pad data
		if len(data_import) % 0x8000 > 0:
			data_import += bytearray([0xFF] * (0x8000 - len(data_import) % 0x8000))
		
		supported_carts = list(self.SUPPORTED_CARTS[self.MODE].values())
		cart_type = copy.deepcopy(supported_carts[args["cart_type"]])
		if cart_type == "RETAIL" or cart_type == "AUTODETECT": return False # Generic ROM Cartridge is not flashable
		
		# Special carts
		if "Retrostage GameBoy Blaster" in cart_type["names"]:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The Retrostage GameBoy Blaster cartridge is currently not fully supported by FlashGBX. However, you can use the insideGadgets “Flasher” software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> to flash this cartridge.", "abortable":False})
			return False
		elif "insideGadgets Power Cart 1 MB, 128 KB SRAM" in cart_type["names"]:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The insideGadgets Power Cart is currently not fully supported by FlashGBX. However, you can use the dedicated insideGadgets “iG Power Cart Programs” software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> to flash this cartridge.", "abortable":False})
			return False
		# Special carts
		# Firmware check L1
		if "flash_commands_on_bank_1" in cart_type and cart_type["flash_commands_on_bank_1"] is True:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported by FlashGBX. Please try the official GBxCart RW firmware and interface software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> instead.", "abortable":False})
			return False
		elif cart_type["type"] == "DMG" and "write_pin" in cart_type and cart_type["write_pin"] == "WR+RESET":
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported by FlashGBX. Please try the official GBxCart RW firmware and interface software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> instead.", "abortable":False})
			return False
		elif (self.FW["pcb_ver"] != 5 or self.FW["fw_ver"] < 2) and ("pulse_reset_after_write" in cart_type and cart_type["pulse_reset_after_write"] is True):
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is only supported by FlashGBX using GBxCart RW v1.4 and firmware version R31+L2 or higher. You can also try the official GBxCart RW firmware and interface software available from <a href=\"https://www.gbxcart.com/\">https://www.gbxcart.com/</a> instead.", "abortable":False})
			return False
		# Firmware check L1

		cart_type["_index"] = 0
		for i in range(0, len(list(self.SUPPORTED_CARTS[self.MODE].keys()))):
			if i == args["cart_type"]:
				try:
					cart_type["_index"] = cart_type["names"].index(list(self.SUPPORTED_CARTS[self.MODE].keys())[i])
				except:
					pass
		
		if cart_type["command_set"] == "GBMEMORY":
			flashcart = Flashcart_DMG_MMSA(config=cart_type, cart_write_fncptr=self._cart_write, cart_read_fncptr=self.ReadROM, progress_fncptr=self.SetProgress)
			if "buffer_map" not in args:
				try:
					with open(os.path.splitext(args["path"])[0] + ".map", "rb") as file: args["buffer_map"] = file.read()
				except:
					self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The GB Memory Cartridge requires a hidden sector file, but it wasn’t found.\nExpected path: {:s}".format(os.path.splitext(args["path"])[0] + ".map"), "abortable":False})
					return False
					#with open(args["path"], "rb") as f: rom_data = bytearray(f.read())
					#gbmem = GBMemory(None, rom_data, None)
					#args["buffer_map"] = gbmem.GetMapData()
			data_map_import = copy.copy(args["buffer_map"])
			data_map_import = bytearray(data_map_import)
			dprint("Hidden sector data loaded")
		else:
			flashcart = Flashcart(config=cart_type, cart_write_fncptr=self._cart_write, cart_read_fncptr=self.ReadROM, progress_fncptr=self.SetProgress)
		
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
		
		# ↓↓↓ Flashcart configuration
		if self.MODE == "DMG":
			self._write(self.DEVICE_CMD["SET_MODE_DMG"])
			mbc = flashcart.GetMBC()
			if mbc != False:
				dprint("Using Mapper Type 0x{:02X} for flashing".format(mbc))
				args["mbc"] = mbc
			else:
				args["mbc"] = 0x1B # MBC5+SRAM+BATTERY
			_mbc = DMG_MBC().GetInstance(args=args, cart_write_fncptr=self._cart_write, cart_read_fncptr=self._cart_read, clk_toggle_fncptr=self._clk_toggle)

			# I need a cart for testing before this has a chance to work ↓
			#self._set_fw_variable("FLASH_COMMANDS_BANK_1", 1 if flashcart.FlashCommandsOnBank1() else 0)
			self._set_fw_variable("FLASH_PULSE_RESET", 1 if flashcart.PulseResetAfterWrite() else 0)

			rom_banks = math.ceil(len(data_import) / _mbc.GetROMBankSize())

			_mbc.EnableMapper()
		elif self.MODE == "AGB":
			self._write(self.DEVICE_CMD["SET_MODE_AGB"])
			if flashcart and "flash_bank_size" in cart_type:
				rom_banks = math.ceil(len(data_import) / cart_type["flash_bank_size"])
			else:
				rom_banks = 1
		
		flash_buffer_size = flashcart.GetBufferSize()
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
		elif command_set_type == "GBMEMORY":
			temp = 0x00
			dprint("Using GB Memory command set")
		else:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"This cartridge type is currently not supported for ROM flashing.", "abortable":False})
			return False
		
		if command_set_type == "GBMEMORY" and self.FW["pcb_ver"] != 5:
			self._set_fw_variable("FLASH_WE_PIN", 0x01)
			dprint("Using GB Memory mode on GBxCart RW v1.3")
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
			elif command_set_type == "GBMEMORY" and self.FW["pcb_ver"] == 5:
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
				self._write(0x01) # FLASH_WE_PIN_WR
				dprint("Using WR as WE")
			elif flashcart.WEisAUDIO():
				self._write(0x02) # FLASH_WE_PIN_AUDIO
				dprint("Using AUDIO as WE")
			elif flashcart.WEisWR_RESET():
				self._write(0x03) # FLASH_WE_PIN_WR_RESET
				dprint("Using WR+RESET as WE")
			else:
				self._write(0x00) # unset
			
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
		# ↑↑↑ Load commands into firmware

		# ↓↓↓ Unlock cartridge
		flashcart.Unlock()
		# ↑↑↑ Unlock cartridge

		# ↓↓↓ Read Flash ID
		if "flash_ids" in cart_type:
			(verified, flash_id) = flashcart.VerifyFlashID()
			if not verified:
				print("WARNING: This cartridge’s Flash ID ({:s}) didn’t match the cartridge type selection.".format(' '.join(format(x, '02X') for x in flash_id)))
				#return False
		# ↑↑↑ Read Flash ID
		
		# ↓↓↓ Read Sector Map
		sector_map = flashcart.GetSectorMap()
		smallest_sector_size = 0x2000
		if sector_map is not None:
			smallest_sector_size = flashcart.GetSmallestSectorSize()
			dprint("Sector map:", sector_map)
			sector_size = 0
			sector_pos = 0
			if isinstance(sector_map, list):
				sector_size = sector_map[sector_pos][0]
			else:
				sector_size = sector_map
			dprint("sector_size:", sector_size)
			current_sector_size = sector_size
		# ↑↑↑ Read Sector Map

		# ↓↓↓ Chip erase
		chip_erase = False
		if flashcart.SupportsChipErase():
			if flashcart.SupportsSectorErase() and args["prefer_chip_erase"] is False:
				chip_erase = False
			else:
				chip_erase = True
				#if flashcart.FlashCommandsOnBank1():
				#	_mbc.SelectBankROM(1)
				if flashcart.ChipErase() is False:
					return False
				#_mbc.SelectBankROM(0)
		elif flashcart.SupportsSectorErase() is False:
			self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"No erase method available.", "abortable":False})
			return False
		# ↑↑↑ Chip erase
		
		# ↓↓↓ Flash Write
		self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE", "size":len(data_import)})
		self.INFO["action"] = self.ACTIONS["ROM_WRITE"]
		
		if smallest_sector_size is not False:
			buffer_len = smallest_sector_size
		elif self.MODE == "DMG":
			buffer_len = _mbc.GetROMBankSize()
		else:
			buffer_len = 0x2000
		dprint("Transfer buffer length is 0x{:X}".format(buffer_len))

		start_address = 0
		end_address = len(data_import)
		buffer_pos = 0
		
		dprint("ROM banks:", rom_banks)
		for bank in range(0, rom_banks):
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
			elif self.MODE == "AGB" and rom_banks > 1:
				if cart_type["flash_bank_select_type"] == 1:
					flashcart.SelectBankROM(bank)
					start_address = 0
					end_address = cart_type["flash_bank_size"]
			# ↑↑↑ Switch ROM bank

			skip_init = False
			pos = start_address
			dprint("pos=0x{:X}, start_address=0x{:X}, end_address=0x{:X}".format(pos, start_address, end_address))
			
			while pos < end_address:
				if self.CANCEL:
					cancel_args = {"action":"ABORT", "abortable":False}
					cancel_args.update(self.CANCEL_ARGS)
					self.CANCEL_ARGS = {}
					self.SetProgress(cancel_args)
					return False
				
				# ↓↓↓ Sector erase
				if chip_erase is False and current_sector_size != 0:
					if buffer_pos % current_sector_size == 0:
						self.SetProgress({"action":"UPDATE_POS", "pos":buffer_pos})
						dprint("Erasing sector of size 0x{:X} at position 0x{:X} (0x{:X})".format(sector_size, buffer_pos, pos))
						current_sector_size = sector_size
						if flashcart.FlashCommandsOnBank1(): _mbc.SelectBankROM(bank)
						ret = flashcart.SectorErase(pos=pos, buffer_pos=buffer_pos)
						if ret is False:
							return False
						else:
							sector_size = ret
							dprint("Next sector size: 0x{:X}".format(sector_size))
						skip_init = False
				# ↑↑↑ Sector erase
				
				if command_set_type == "GBMEMORY" and self.FW["pcb_ver"] < 5:
					status = self.WriteROM_GBMEMORY(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], bank=bank)
				elif command_set_type == "GBMEMORY" and self.FW["pcb_ver"] == 5:
					status = self.WriteROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], flash_buffer_size=flash_buffer_size, skip_init=(skip_init and not self.SKIPPING))
					self._cart_write(pos + buffer_len - 1, 0xF0)
				else:
					status = self.WriteROM(address=pos, buffer=data_import[buffer_pos:buffer_pos+buffer_len], flash_buffer_size=flash_buffer_size, skip_init=(skip_init and not self.SKIPPING), rumble_stop=rumble)
				if status is False:
					self.CANCEL_ARGS = {"info_type":"msgbox_critical", "info_msg":"An error occured while writing 0x{:X} bytes to the flash cartridge at position 0x{:X}. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.".format(buffer_len, buffer_pos)}
					self.CANCEL = True
					self.ERROR = True
					continue
				
				skip_init = True
				
				buffer_pos += buffer_len
				self.SetProgress({"action":"UPDATE_POS", "pos":buffer_pos})
				
				pos += buffer_len
		
		# Hidden Sector
		if command_set_type == "GBMEMORY":
			#Util.DEBUG = True
			flashcart.EraseHiddenSector(buffer=data_map_import)
			status = self.WriteROM_GBMEMORY(address=0, buffer=data_map_import[0:128], bank=1)
			if status is False:
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"An error occured while writing the hidden sector. Please make sure that the cartridge contacts are clean, re-connect the device and try again from the beginning.", "abortable":False})
				return False
		# ↑↑↑ Flash write
		
		# ↓↓↓ Reset flash
		flashcart.Reset(full_reset=True)
		# ↑↑↑ Reset flash

		# ↓↓↓ Flash verify
		verified = False
		if "verify_flash" in args and args["verify_flash"] is True:
			self.SetProgress({"action":"INITIALIZE", "method":"ROM_WRITE_VERIFY", "size":buffer_pos})
			
			verify_args = copy.copy(args)
			if self.MODE == "DMG":
				rom_banks = math.ceil(len(data_import)/_mbc.GetROMBankSize())
			else:
				rom_banks = 1
			
			start_address = 0
			end_address = buffer_pos
			'''
			dacs = False
			if "agb-ghtj-jpn" in flashcart.CONFIG: # DACS
				start_address = 0x1F00000
				end_address = 0x1FFC000
				dacs = True
				#data_import = data_import[start_address:end_address]
			verify_args.update({"verify_flash":data_import, "dacs":dacs, "start_address":start_address, "end_address":end_address, "rom_banks":rom_banks, "path":"", "rtc_area":flashcart.HasRTC()})
			'''
			verify_args.update({"verify_flash":data_import, "rom_banks":rom_banks, "path":"", "rtc_area":flashcart.HasRTC()})
			self.ReadROM(0, 4) # dummy read
			verified_size = self._BackupROM(verify_args)
			if self.CANCEL is True:
				pass
			elif (verified_size is not True) and (buffer_pos != verified_size):
				self.SetProgress({"action":"ABORT", "info_type":"msgbox_critical", "info_msg":"The ROM was written completely, but verification of written data failed at address 0x{:X}.".format(verified_size), "abortable":False})
				return False
			else:
				verified = True
		# ↑↑↑ Flash verify

		# ↓↓↓ Switch to first ROM bank
		if self.MODE == "DMG":
			if _mbc.ResetBeforeBankChange(0) is True:
				dprint("Resetting the MBC")
				self._write(self.DEVICE_CMD["DMG_MBC_RESET"], wait=True)
			_mbc.SelectBankROM(0)
			self._set_fw_variable("DMG_ROM_BANK", 0)
		elif self.MODE == "AGB" and rom_banks > 1:
			if cart_type["flash_bank_select_type"] == 1:
				flashcart.SelectBankROM(0)
		# ↑↑↑ Switch to first ROM bank

		self.INFO["last_action"] = self.INFO["action"]
		self.INFO["action"] = None
		self.SetProgress({"action":"FINISHED", "verified":verified})
		return True
	
	#################################################################

	def _TransferData(self, args, signal):
		self.ERROR = False
		if self.IsConnected():
			if self.FW["pcb_ver"] == 5:
				self._write(self.DEVICE_CMD["OFW_CART_MODE"])
				self._read(1)
				self.CartPowerOn()
			
			ret = False
			self.SIGNAL = signal
			if args['mode'] == 1: ret = self._BackupROM(args)
			elif args['mode'] == 2: ret = self._BackupRestoreRAM(args)
			elif args['mode'] == 3: ret = self._BackupRestoreRAM(args)
			elif args['mode'] == 4: ret = self._FlashROM(args)
			
			if self.FW["pcb_ver"] == 5:
				if ret is True:
					self._write(self.DEVICE_CMD["OFW_DONE_LED_ON"])
				elif self.ERROR is True:
					self._write(self.DEVICE_CMD["OFW_ERROR_LED_ON"])
			return True
