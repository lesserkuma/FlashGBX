# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

# pylint: disable=wildcard-import, unused-wildcard-import
from .LK_Device import *

class GbxDevice(LK_Device):
	DEVICE_NAME = "GBxCart RW"
	DEVICE_MIN_FW = 1
	DEVICE_MAX_FW = 1
	DEVICE_LATEST_FW_TS = { 4:1709317610, 5:1722774120, 6:1722774120, 2:0, 90:0, 100:0 }
	PCB_VERSIONS = { 5:'v1.4', 6:'v1.4a/b/c', 2:'v1.1/v1.2', 4:'v1.3', 90:'XMAS v1.0', 100:'Mini v1.0' }
	BAUDRATE = 1000000
	MAX_BUFFER_READ = 0x1000
	MAX_BUFFER_WRITE = 0x400

	def Initialize(self, flashcarts, port=None, max_baud=2000000):
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
			for baudrate in (1000000, 1700000, 2000000):
				if max_baud < baudrate: continue
				try:
					if self.TryConnect(ports[i], baudrate):
						self.BAUDRATE = baudrate
						dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
						self.DEVICE = dev
						break
				except SerialException as e:
					if "Permission" in str(e):
						conn_msg.append([3, "The device on port " + ports[i] + " couldn’t be accessed. Make sure your user account has permission to use it and it’s not already in use by another application."])
					elif "FileNotFoundError" in str(e):
						continue
					else:
						conn_msg.append([3, "A critical error occured while trying to access the device on port " + ports[i] + ".\n\n" + str(e)])
					continue
			
			if self.FW is None or self.FW == {}: continue
			if max_baud >= 1700000 and self.FW is not None and "pcb_ver" in self.FW and self.FW["pcb_ver"] in (5, 6, 101) and self.BAUDRATE < 1700000:
				self.ChangeBaudRate(baudrate=1700000)
				self.DEVICE.close()
				dev = serial.Serial(ports[i], self.BAUDRATE, timeout=0.1)
				self.DEVICE = dev

			dprint(f"Found a {self.DEVICE_NAME}")
			dprint("Firmware information:", self.FW)
			dprint("Baud rate:", self.BAUDRATE)

			if self.DEVICE is None or not self.IsConnected() or self.FW is None or self.FW["pcb_ver"] not in self.DEVICE_LATEST_FW_TS:
				self.DEVICE = None
				if self.FW is not None:
					conn_msg.append([0, "Couldn’t communicate with the " + self.DEVICE_NAME + " device on port " + ports[i] + ". Please disconnect and reconnect the device, then try again."])
				continue
			elif self.FW["fw_ts"] > self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
				conn_msg.append([0, "Note: The " + self.DEVICE_NAME + " device on port " + ports[i] + " is running a firmware version that is newer than what this version of FlashGBX was developed to work with, so errors may occur."])
			elif self.FW["pcb_ver"] in (5, 6, 101) and self.BAUDRATE > 1000000:
				self.MAX_BUFFER_READ = 0x1000
				self.MAX_BUFFER_WRITE = 0x400
			else:
				self.MAX_BUFFER_READ = 0x1000
				self.MAX_BUFFER_WRITE = 0x100
			
			conn_msg.append([0, "For help with your GBxCart RW device, please visit the insideGadgets Discord: https://gbxcart.com/discord"])
			if self.FW["pcb_ver"] == 4:
				conn_msg.append([0, "Note: Your GBxCart RW hardware revision does not fully support the latest features due to technical limitations. Please consider upgrading to a newer device."])

			self.PORT = ports[i]
			self.DEVICE.timeout = self.DEVICE_TIMEOUT
			
			# Load Flash Cartridge Handlers
			self.UpdateFlashCarts(flashcarts)

			# Stop after first found device
			break

		return conn_msg

	def LoadFirmwareVersion(self):
		dprint("Querying firmware version")
		try:
			self.DEVICE.timeout = 0.075
			self.DEVICE.reset_input_buffer()
			self.DEVICE.reset_output_buffer()
			self._write(self.DEVICE_CMD["OFW_PCB_VER"])
			temp = self.DEVICE.read(1)
			self.DEVICE.timeout = self.DEVICE_TIMEOUT
			if len(temp) == 0:
				dprint("No response")
				self.FW = None
				return False
			pcb = temp[0]
			if pcb == b'': return False
			self._write(self.DEVICE_CMD["OFW_FW_VER"])
			ofw = self._read(1)
			if (pcb == 2 and ofw == 2):
				dprint(f"Not a {self.DEVICE_NAME}")
				self.FW = None
				return False
			if (pcb >= 5 and ofw == 0):
				dprint(f"Not a {self.DEVICE_NAME}")
				self.FW = None
				return False
			if (pcb < 5 and ofw > 0):
				self.FW = {
					"ofw_ver":ofw,
					"pcb_ver":pcb,
					"pcb_name":"GBxCart RW",
					"cfw_id":"",
					"fw_ver":0,
					"fw_ts":0,
					"fw_dt":"",
				}
				return True

			self._write(self.DEVICE_CMD["QUERY_FW_INFO"])
			size = self._read(1)
			if size != 8: return False
			data = self._read(size)
			info = data[:8]
			keys = ["cfw_id", "fw_ver", "pcb_ver", "fw_ts"]
			values = struct.unpack(">cHBI", bytearray(info))
			self.FW = dict(zip(keys, values))
			self.FW["cfw_id"] = self.FW["cfw_id"].decode('ascii')
			self.FW["fw_dt"] = datetime.datetime.fromtimestamp(self.FW["fw_ts"]).astimezone().replace(microsecond=0).isoformat()
			self.FW["ofw_ver"] = ofw
			self.FW["pcb_name"] = ""
			self.FW["cart_power_ctrl"] = False
			self.FW["bootloader_reset"] = False
			if self.FW["cfw_id"] == "L" and self.FW["fw_ver"] >= 12:
				size = self._read(1)
				name = self._read(size)
				if len(name) > 0:
					try:
						self.FW["pcb_name"] = name.decode("UTF-8").replace("\x00", "").strip()
					except:
						self.FW["pcb_name"] = "Unnamed Device"
					self.DEVICE_NAME = self.FW["pcb_name"]

				# Cartridge Power Control support
				self.FW["cart_power_ctrl"] = True if self._read(1) == 1 else False

				# Reset to bootloader support
				self.FW["bootloader_reset"] = True if self._read(1) == 1 else False

			return True
		
		except Exception as e:
			dprint("Disconnecting due to an error", e, sep="\n")
			try:
				if self.DEVICE.isOpen():
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					self.DEVICE.close()
				self.DEVICE = None
			except:
				pass
			return False

	def ChangeBaudRate(self, baudrate):
		if not self.IsConnected(): return
		dprint("Changing baud rate to", baudrate)
		if baudrate == 1700000:
			self._write(self.DEVICE_CMD["OFW_USART_1_7M_SPEED"])
		elif baudrate == 1000000:
			self._write(self.DEVICE_CMD["OFW_USART_1_0M_SPEED"])
		self.BAUDRATE = baudrate

	def CheckActive(self):
		if time.time() < self.LAST_CHECK_ACTIVE + 1: return True
		dprint("Checking if device is active")
		if self.DEVICE is None: return False
		if self.FW["pcb_name"] is None:
			if self.LoadFirmwareVersion():
				self.LAST_CHECK_ACTIVE = time.time()
				return True
			return False
		try:
			if self.FW["fw_ver"] == 0: # legacy GBxCart RW firmware
				return True
			if self.FW["fw_ver"] >= 12:
				temp = bytearray([self.DEVICE_CMD["QUERY_CART_PWR"]])
				self._get_fw_variable("CART_MODE")
			elif self.CanPowerCycleCart():
				temp = bytearray([self.DEVICE_CMD["OFW_QUERY_CART_PWR"]])
				self._write(temp)
				self._read(1)
			self.LAST_CHECK_ACTIVE = time.time()
			return True
		except Exception as e:
			dprint("Disconnecting...", e)
			try:
				if self.DEVICE.isOpen():
					self.DEVICE.reset_input_buffer()
					self.DEVICE.reset_output_buffer()
					self.DEVICE.close()
				self.DEVICE = None
			except:
				pass
			return False

	def GetFirmwareVersion(self, more=False):
		if self.FW["fw_ver"] == 0: # old GBxCart RW
			return "R{:d}".format(self.FW["ofw_ver"])
		
		if self.FW["pcb_ver"] in (5, 6, 101):
			s = "R{:d}+{:s}{:d}".format(self.FW["ofw_ver"], self.FW["cfw_id"], self.FW["fw_ver"])
		else:
			s = "{:s}{:d}".format(self.FW["cfw_id"], self.FW["fw_ver"])
		if more:
			s += " ({:s})".format(self.FW["fw_dt"])
		return s
	
	def GetFullNameExtended(self, more=False):
		if self.FW["fw_ver"] == 0: # old GBxCart RW
			return "{:s} – Firmware {:s} ({:s})".format(self.GetFullName(), self.GetFirmwareVersion(), self.GetPort())

		if more:
			return "{:s} – Firmware {:s} ({:s}) on {:s} at {:.1f}M baud".format(self.GetFullName(), self.GetFirmwareVersion(), self.FW["fw_dt"], self.GetPort(), self.BAUDRATE/1000/1000)
		else:
			return "{:s} – Firmware {:s} ({:s})".format(self.GetFullName(), self.GetFirmwareVersion(), self.GetPort())

	def CanSetVoltageManually(self):
		return False
	
	def CanSetVoltageAutomatically(self):
		return True
	
	def CanPowerCycleCart(self):
		if self.FW is None or self.DEVICE is None: return False
		if not self.DEVICE.is_open: return False
		if self.FW["fw_ver"] >= 12:
			return self.FW["cart_power_ctrl"]
		else:
			return self.FW["pcb_ver"] in (5, 6)
	
	def GetSupprtedModes(self):
		if self.FW["pcb_ver"] == 101:
			return ["DMG"]
		else:
			return ["DMG", "AGB"]
		
	def IsSupported3dMemory(self):
		return True
	
	def IsClkConnected(self):
		return self.FW["pcb_ver"] in (5, 6, 101)

	def SupportsFirmwareUpdates(self):
		if self.FW["ofw_ver"] == 30:
			self._write(self.DEVICE_CMD["OFW_LNL_QUERY"])
			old_timeout = self.DEVICE.timeout
			self.DEVICE.timeout = 0.15
			is_lnl = self._read(1) == 0x31
			self.DEVICE.timeout = old_timeout
			dprint("LinkNLoad detected:", is_lnl)
			if is_lnl: return False
		return self.FW["pcb_ver"] in (2, 4, 5, 6, 90, 100, 101)
	
	def FirmwareUpdateAvailable(self):
		if self.FW["fw_ver"] == 0 and self.FW["pcb_ver"] in (2, 4, 90, 100, 101):
			if self.FW["pcb_ver"] == 4:
				self.FW_UPDATE_REQ = True
			else:
				self.FW_UPDATE_REQ = 2
			return True
		if self.FW["pcb_ver"] not in (4, 5, 6): return False
		if self.FW["pcb_ver"] in (5, 6) and self.FW["fw_ts"] < self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
			return True
		if self.FW["pcb_ver"] == 4 and self.FW["fw_ts"] < self.DEVICE_LATEST_FW_TS[self.FW["pcb_ver"]]:
			self.FW_UPDATE_REQ = True
			return True
	
	def GetFirmwareUpdaterClass(self):
		if self is None or self.FW["pcb_ver"] in (5, 6): # v1.4 / v1.4a/b/c
			try:
				from . import fw_GBxCartRW_v1_4
				return (fw_GBxCartRW_v1_4.FirmwareUpdater, fw_GBxCartRW_v1_4.FirmwareUpdaterWindow)
			except:
				return None
		elif self.FW["pcb_ver"] in (2, 4, 90, 100, 101): # v1.3
			try:
				from . import fw_GBxCartRW_v1_3
				return (None, fw_GBxCartRW_v1_3.FirmwareUpdaterWindow)
			except:
				return None
		else:
			return None

	def ResetLEDs(self):
		if self.DEVICE in (None, False): return
		self._write(self.DEVICE_CMD["OFW_CART_MODE"]) # Reset LEDs
		self._read(1)
	
	def SupportsBootloaderReset(self):
		if self.FW["fw_ver"] >= 12:
			return self.FW["bootloader_reset"]
		else:
			return False

	def BootloaderReset(self):
		return False

	def SupportsAudioAsWe(self):
		return True

	def Close(self, cartPowerOff=False):
		try:
			self.ResetLEDs()
		except SerialException:
			pass
		return super().Close(cartPowerOff)

	def SetTimeout(self, seconds=1):
		if seconds < 1: seconds = 1
		self.DEVICE_TIMEOUT = seconds
		self.DEVICE.timeout = self.DEVICE_TIMEOUT
