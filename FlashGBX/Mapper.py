# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import time, datetime, struct, math, hashlib
from dateutil.relativedelta import relativedelta
from .RomFileDMG import RomFileDMG
from .Util import dprint
from . import Util

class DMG_MBC:
	MBC_ID = 0
	CART_WRITE_FNCPTR = None
	CART_READ_FNCPTR = None
	CART_POWERCYCLE_FNCPTR = None
	CLK_TOGGLE_FNCPTR = None
	ROM_BANK_SIZE = 0x4000
	RAM_BANK_SIZE = 0x2000
	ROM_BANK_NUM = 0
	CURRENT_ROM_BANK = 0
	CURRENT_FLASH_BANK = 0
	START_BANK = 0

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		if "mbc" in args: self.MBC_ID = args["mbc"]
		if "rom_banks" in args:
			self.ROM_BANK_NUM = args["rom_banks"]
		elif "rom_size" in args:
			self.ROM_BANK_NUM = math.ceil(args["rom_size"] / self.ROM_BANK_SIZE)
		self.CART_WRITE_FNCPTR = cart_write_fncptr
		self.CART_READ_FNCPTR = cart_read_fncptr
		self.CART_POWERCYCLE_FNCPTR = cart_powercycle_fncptr
		self.CLK_TOGGLE_FNCPTR = clk_toggle_fncptr

	def GetInstance(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		mbc_id = args["mbc"]
		if mbc_id in (0x01, 0x02, 0x03):						# 0x01:'MBC1', 0x02:'MBC1+SRAM', 0x03:'MBC1+SRAM+BATTERY',
			return DMG_MBC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x06:									# 0x06:'MBC2+SRAM+BATTERY',
			return DMG_MBC2(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x10, 0x13):							# 0x10:'MBC3+RTC+SRAM+BATTERY', 0x13:'MBC3+SRAM+BATTERY',
			return DMG_MBC3(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x19, 0x1B, 0x1C, 0x1E):				# 0x19:'MBC5', 0x1B:'MBC5+SRAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1E:'MBC5+RUMBLE+SRAM+BATTERY',
			return DMG_MBC5(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x20:									# 0x20:'MBC6+FLASH+SRAM+BATTERY',
			return DMG_MBC6(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x22:									# 0x22:'MBC7+ACCELEROMETER+EEPROM',
			return DMG_MBC7(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x101, 0x103):							# 0x101:'MBC1M', 0x103:'MBC1M+SRAM+BATTERY',
			return DMG_MBC1M(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x0B, 0x0D):							# 0x0B:'MMM01',  0x0D:'MMM01+SRAM+BATTERY',
			return DMG_MMM01(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFC:									# 0xFC:'GBD+SRAM+BATTERY',
			return DMG_GBD(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x105:									# 0x105:'G-MMC1+SRAM+BATTERY',
			return DMG_GMMC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x104:									# 0x104:'M161',
			return DMG_M161(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFF:									# 0xFF:'HuC-1+IR+SRAM+BATTERY',
			return DMG_HuC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFE:									# 0xFE:'HuC-3+RTC+SRAM+BATTERY',
			return DMG_HuC3(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFD:									# 0xFD:'TAMA5+RTC+EEPROM'
			return DMG_TAMA5(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x201:									# 0x201:'256M Multi Cart',
			return DMG_Unlicensed_256M(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x202:									# 0x202:'Wisdom Tree Mapper',
			return DMG_Unlicensed_WisdomTree(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x203:									# 0x203:'Xploder GB',
			return DMG_Unlicensed_XploderGB(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x204:									# 0x204:'Sachen',
			return DMG_Unlicensed_Sachen(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x205:									# 0x205:'Datel Orbit V2',
			return DMG_Unlicensed_DatelOrbitV2(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		else:
			self.__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
			return self
	
	def CartRead(self, address, length=0):
		if length == 0: # auto size:
			return self.CART_READ_FNCPTR(address)
		else:
			return self.CART_READ_FNCPTR(address, length)

	def CartWrite(self, commands, delay=False, sram=False):
		for command in commands:
			address = command[0]
			value = command[1]
			self.CART_WRITE_FNCPTR(address, value, sram=sram)
			if delay is not False: time.sleep(delay)

	def GetID(self):
		return self.MBC_ID
	
	def GetName(self):
		return "Unknown MBC {:d}".format(self.MBC_ID)

	def GetFullName(self):
		try:
			return Util.DMG_Header_Mapper[self.MBC_ID]
		except:
			return "Unknown MBC {:d}".format(self.MBC_ID)

	def GetROMBank(self):
		return self.CURRENT_ROM_BANK

	def GetFlashBank(self):
		return self.CURRENT_FLASH_BANK

	def GetROMBanks(self, rom_size):
		return math.ceil(rom_size / self.ROM_BANK_SIZE)
	
	def GetROMBankSize(self):
		return self.ROM_BANK_SIZE
	
	def GetRAMBanks(self, ram_size):
		return math.ceil(ram_size / self.RAM_BANK_SIZE)
	
	def GetRAMBankSize(self):
		return self.RAM_BANK_SIZE
	
	def GetROMSize(self):
		return self.ROM_BANK_SIZE * self.ROM_BANK_NUM
	
	def CalcChecksum(self, buffer):
		chk = 0
		for i in range(0, len(buffer), 2):
			if i != 0x14E:
				chk = chk + buffer[i + 1]
				chk = chk + buffer[i]
		return chk & 0xFFFF

	def EnableMapper(self):
		return True
	
	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x0000, 0x0A if enable else 0x00 ]
		]
		self.CartWrite(commands)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x2100, index & 0xFF ]
		]
		start_address = 0 if index == 0 else 0x4000
		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)
	
	def SelectBankRAM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x4000, index & 0xFF ]
		]
		start_address = 0
		self.CartWrite(commands)
		return (start_address, self.RAM_BANK_SIZE)

	def SetStartBank(self, index):
		self.START_BANK = index
	
	def SelectBankFlash(self, index):
		return
	
	def HasFlashBanks(self):
		return False
	
	def HasHiddenSector(self):
		return False
	
	def HasRTC(self):
		return False

	def GetRTCBufferSize(self):
		return 0

	def LatchRTC(self):
		return 0
	
	def ReadRTC(self):
		return False
	
	def WriteRTC(self, buffer, advance=False):
		pass

	def ResetBeforeBankChange(self, index):
		return False

	def ReadWithCSPulse(self):
		return False

	def WriteWithCSPulse(self):
		return False

class DMG_MBC1(DMG_MBC):
	def GetName(self):
		return "MBC1"

	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		if enable:
			commands = [
				[ 0x6000, 0x01 ],
				[ 0x0000, 0x0A ],
			]
		else:
			commands = [
				[ 0x0000, 0x00 ],
				[ 0x6000, 0x00 ],
			]
		self.CartWrite(commands)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index, hex(index >> 5), hex(index & 0x1F))
		commands = [
			[ 0x6000, 1 ],
			[ 0x2000, index ],
			[ 0x4000, index >> 5 ],
		]
		start_address = 0x4000 if index & 0x1F else 0

		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)

class DMG_MBC2(DMG_MBC):
	def GetName(self):
		return "MBC2"

	def SelectBankRAM(self, index):
		return (0, self.RAM_BANK_SIZE)

class DMG_MBC3(DMG_MBC):
	def GetName(self):
		return "MBC3"
	
	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x0000, 0x0A if enable else 0x00 ],
		]
		self.CartWrite(commands)
	
	def HasRTC(self):
		dprint("Checking for RTC")
		if self.MBC_ID != 16:
			dprint("No RTC because wrong MBC ID", self.MBC_ID)
			return False
		self.EnableRAM(enable=False)
		self.EnableRAM(enable=True)
		self.LatchRTC()
	
		skipped = True
		for i in range(0x08, 0x0D):
			self.CLK_TOGGLE_FNCPTR(60)
			self.CartWrite([ [0x4000, i] ])
			data = self.CartRead(0xA000, 0x800)
			if data[0] in (0, 0xFF): continue
			skipped = False
			if data != bytearray([data[0]] * 0x800):
				dprint("No RTC because whole bank is not the same value", data[0])
				skipped = True
				break

		self.EnableRAM(enable=False)
		self.CartWrite([ [0x4000, 0] ])
		return skipped is False

	def GetRTCBufferSize(self):
		return 0x30

	def LatchRTC(self):
		dprint("Latching RTC")
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x0000, 0x0A ] ])
		time.sleep(0.01)
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x6000, 0x00 ] ])
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x6000, 0x01 ] ])
		time.sleep(0.01)

	def ReadRTC(self):
		dprint("Reading RTC")
		self.EnableRAM(enable=True)

		buffer = bytearray()
		for i in range(0x08, 0x0D):
			self.CLK_TOGGLE_FNCPTR(60)
			self.CartWrite([ [0x4000, i] ])
			buffer.extend(struct.pack("<I", self.CartRead(0xA000)))
		buffer.extend(buffer) # copy

		# Add timestamp of backup time
		ts = int(time.time())
		buffer.extend(struct.pack("<Q", ts))
		
		self.EnableRAM(enable=False)
		self.CartWrite([ [0x4000, 0] ])
		return buffer

	def WriteRTC(self, buffer, advance=False):
		dprint("Writing RTC:", buffer)
		self.EnableRAM(enable=True)
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				if buffer == bytearray([0x00] * len(buffer)): # Reset
					seconds = 0
					minutes = 0
					hours = 0
					days = 0
					carry = 0
				else:
					seconds = buffer[0x00]
					minutes = buffer[0x04]
					hours = buffer[0x08]
					days = buffer[0x0C] | buffer[0x10] << 8
					carry = ((buffer[0x10] & 0x80) != 0)
					days = days & 0x1FF
					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					dprint(seconds, minutes, hours, days, carry)
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer1 = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(2000, 1, 1, 0, 0, 0), "%Y-%m-%d %H:%M:%S")
						dt_buffer2 = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(2000, 1, 1, hours % 24, minutes % 60, seconds % 60), "%Y-%m-%d %H:%M:%S")
						dt_buffer2 += datetime.timedelta(days=days)
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer2 + rd
						dprint(dt_then, dt_now, dt_buffer1, dt_buffer2, dt_new, sep="\n")
						seconds = dt_new.second
						minutes = dt_new.minute
						hours = dt_new.hour
						#temp = dt_new - dt_buffer1
						#days = temp.days
						temp = datetime.date.fromtimestamp(timestamp_now) - datetime.date.fromtimestamp(timestamp_then)
						days = temp.days + days
						if days >= 512:
							carry = True
							days = days % 512
						dprint(seconds, minutes, hours, days, carry)

				buffer[0x00] = seconds % 60
				buffer[0x04] = minutes % 60
				buffer[0x08] = hours % 24
				buffer[0x0C] = days & 0xFF
				buffer[0x10] = days >> 8 & 0x1
				if carry:
					buffer[0x10] |= 0x80
			except Exception as e:
				print("Couldn’t update the RTC register values\n", e)
		
		dprint("New values: RTC_S=0x{:02X}, RTC_M=0x{:02X}, RTC_H=0x{:02X}, RTC_DL=0x{:02X}, RTC_DH=0x{:02X}".format(buffer[0x00], buffer[0x04], buffer[0x08], buffer[0x0C], buffer[0x10]))

		# Unlock and latch RTC
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x0000, 0x0A ] ])
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x6000, 0x00 ] ])
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x6000, 0x01 ] ])
		time.sleep(0.01)

		# Halt RTC
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x4000, 0x0C ] ])
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0xA000, 0x40 ] ])
		time.sleep(0.1)
		
		# Write to registers
		for i in range(0x08, 0x0D):
			self.CLK_TOGGLE_FNCPTR(50)
			self.CartWrite([ [ 0x4000, i ] ])
			self.CLK_TOGGLE_FNCPTR(50)
			data = struct.unpack("<I", buffer[(i-8)*4:(i-8)*4+4])[0] & 0xFF
			self.CartWrite([ [ 0xA000, data ] ])
		time.sleep(0.1)

		# Latch RTC
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x6000, 0x00 ] ])
		self.CLK_TOGGLE_FNCPTR(50)
		self.CartWrite([ [ 0x6000, 0x01 ] ])
		time.sleep(0.1)

		self.CartWrite([ [0x4000, 0] ])
		self.EnableRAM(enable=False)

class DMG_MBC5(DMG_MBC):
	def GetName(self):
		return "MBC5"
	
	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		if enable:
			commands = [
				[ 0x6000, 0x01 ],
				[ 0x0000, 0x0A ],
			]
		else:
			commands = [
				[ 0x0000, 0x00 ],
				[ 0x6000, 0x00 ],
			]
		self.CartWrite(commands)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		if index == 0 or index >= 256:
			commands = [
				[ 0x2100, index & 0xFF ],
				[ 0x3000, ((index >> 8) & 0xFF) ],
			]
		else:
			commands = [
				[ 0x2100, index & 0xFF ],
			]
		
		start_address = 0 if index == 0 else 0x4000

		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)

class DMG_MBC6(DMG_MBC):
	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=None)
		self.ROM_BANK_SIZE = 0x2000
		self.RAM_BANK_SIZE = 0x1000
		self.ROM_BANK_NUM = 128
	
	def GetName(self):
		return "MBC6"
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		self.CURRENT_ROM_BANK = index
		#index = index * 2
		commands = [
			[ 0x2800, 0 ],
			[ 0x3800, 0 ],
			[ 0x2000, index ],	# ROM Bank A (0x4000–0x5FFF)
			[ 0x3000, index ],	# ROM Bank B (0x6000–0x7FFF)
		]
		self.CartWrite(commands)
		start_address = 0 if index == 0 else 0x4000
		return (start_address, self.ROM_BANK_SIZE)

	def HasFlashBanks(self):
		return True

	def SelectBankFlash(self, index):
		dprint(self.GetName(), "|", index)
		self.CURRENT_ROM_BANK = index
		#index = index * 2
		commands = [
			[ 0x2800, 8 ],
			[ 0x3800, 8 ],
			[ 0x2000, index ],	# ROM Bank A (0x4000–0x5FFF)
			[ 0x3000, index ],	# ROM Bank B (0x6000–0x7FFF)
		]
		self.CartWrite(commands)
		start_address = 0x4000
		return (start_address, self.ROM_BANK_SIZE)

	def GetRAMBanks(self, ram_size): # 0x108000
		return 8 + 128

	def SelectBankRAM(self, index):
		dprint(self.GetName(), "|", index)
		#index = index * 2
		commands = [
			[ 0x0400, index ],	# RAM Bank A (0xA000-0xAFFF)
			[ 0x0800, index ],	# RAM Bank B (0xB000-0xBFFF)
		]
		self.CartWrite(commands)
		start_address = 0
		return (start_address, self.RAM_BANK_SIZE)
	
	def EnableFlash(self, enable=True, enable_write=False):
		if enable:
			self.CartWrite([
				[ 0x1000, 0x01 ],		# Enable flash write
				[ 0x0C00, 0x01 ],		# Enable flash output
				[ 0x1000, 0x01 if enable_write else 0x00 ],		# Disable flash write?
				[ 0x2800, 0x08 ],		# Map flash memory into ROM Bank A
				[ 0x3800, 0x08 ]		# Map flash memory into ROM Bank B
			])
		else:
			self.CartWrite([
				[ 0x1000, 0x01 ],		# Enable flash write
				[ 0x0C00, 0x00 ],		# Disable flash output
				[ 0x1000, 0x00 ],		# Disable flash write
				[ 0x2800, 0x00 ],		# Map ROM memory into ROM Bank A
				[ 0x3800, 0x00 ]		# Map ROM memory into ROM Bank B
			])

	def EraseFlashSector(self):
		cmds = [
			[ 0x2000, 0x01 ],
			[ 0x3000, 0x02 ],
			[ 0x7555, 0xAA ],
			[ 0x4AAA, 0x55 ],
			[ 0x7555, 0x80 ],
			[ 0x7555, 0xAA ],
			[ 0x4AAA, 0x55 ],
		]
		self.CartWrite(cmds)
		self.SelectBankFlash(self.GetROMBank())
		self.CartWrite([[ 0x4000, 0x30 ]])
		while True:
			sr = self.CartRead(0x4000)
			dprint("Status Register Check: 0x{:X} == 0x80? {:s}".format(sr, str(sr == 0x80)))
			if sr == 0x80: break
			time.sleep(0.0001)

	def GetFlashID(self):
		self.EnableFlash(enable=True)
		# Query Flash ID
		self.CartWrite([
			[ 0x2000, 0x01 ],
			[ 0x3000, 0x02 ],
			[ 0x7555, 0xAA ],
			[ 0x4AAA, 0x55 ],
			[ 0x7555, 0x90 ],
		])
		flash_id = self.CartRead(0x6000, 8)
		# Reset to Read Array Mode
		self.CartWrite([
			[ 0x4000, 0xF0 ],
		])
		self.SelectBankROM(self.CURRENT_ROM_BANK)
		return flash_id

class DMG_MBC7(DMG_MBC):
	def GetName(self):
		return "MBC7"

	def SelectBankRAM(self, index):
		return (0, 0x200)
	
	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x0000, 0x0A if enable else 0x00 ],
			[ 0x4000, 0x40 ]
		]
		self.CartWrite(commands)

class DMG_MBC1M(DMG_MBC1):
	def GetName(self):
		return "MBC1M"

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x6000, 1 ],
			[ 0x2000, index ],
			[ 0x4000, index >> 4 ],
		]
		start_address = 0x4000 if index & 0x0F else 0

		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)

class DMG_MMM01(DMG_MBC):
	def GetName(self):
		return "MMM01"
	
	def CalcChecksum(self, buffer):
		chk = 0
		temp_data = buffer[0:-0x8000]
		temp_menu = buffer[-0x8000:]
		temp_dump = temp_menu + temp_data
		for i in range(0, len(temp_dump), 2):
			if i != 0x14E:
				chk = chk + temp_dump[i + 1]
				chk = chk + temp_dump[i]
		return chk & 0xFFFF

	def ResetBeforeBankChange(self, index):
		return ((index % 0x20) == 0)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		
		start_address = 0 if index == 0 else 0x4000

		if (index % 0x20) == 0:
			commands = [
				[ 0x2000, index & 0xFF ],	# start from this ROM bank
				[ 0x6000, 0x00 ],			# 0x00 = 512 KB, 0x04 = 32 KB, 0x08 = 64 KB, 0x10 = 128 KB, 0x20 = 256 KB
				[ 0x4000, 0x40 ],			# RAM bank?
				[ 0x0000, 0x00 ],
				[ 0x0000, 0x40 ],			# Enable mapping
				[ 0x2100, ((index % 0x20) & 0xFF)],
			]
			start_address = 0
		else:
			commands = [
				[ 0x2100, ((index % 0x20) & 0xFF)],
			]

		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)

class DMG_GBD(DMG_MBC5):
	def GetName(self):
		return "GBD"

class DMG_GMMC1(DMG_MBC5):
	def GetName(self):
		return "G-MMC1"

	def EnableMapper(self):
		dprint(self.GetName())
		commands = [
			# Unlock
			[ 0x120, 0x09, 1 ],
			[ 0x121, 0xAA, 1 ],
			[ 0x122, 0x55, 1 ],
			[ 0x13F, 0xA5, 1 ],
			
			[ 0x120, 0x11, 1 ],
			[ 0x13F, 0xA5, 1 ],

			[ 0x2100, 0x01, 1 ],

			[ 0x2100, 0x01 ],
			[ 0x120, 0x02 ],
			
			# Reset
			[ 0x120, 0x0F ],
			[ 0x125, 0x40 ],
			[ 0x126, 0x80 ],
			[ 0x127, 0xF0 ],
			[ 0x13F, 0xA5 ],
			
			[ 0x120, 0x04 ],
			[ 0x13F, 0xA5 ],
			
			[ 0x120, 0x08 ],
			[ 0x13F, 0xA5 ]
		]
		self.CartWrite(commands)
		return True
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		if index == 0 or index >= 256:
			commands = [
				[ 0x2100, index & 0xFF ],
			]
		else:
			commands = [
				[ 0x2100, index & 0xFF ],
			]
		
		start_address = 0 if index == 0 else 0x4000

		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)
	
	def HasHiddenSector(self):
		return True

	def ReadHiddenSector(self):
		self.EnableMapper()
		commands = [
			# Unlock
			[ 0x120, 0x09, 1 ],
			[ 0x121, 0xAA, 1 ],
			[ 0x122, 0x55, 1 ],
			[ 0x13F, 0xA5, 1 ],
			
			[ 0x120, 0x11, 1 ],
			[ 0x13F, 0xA5, 1 ],

			[ 0x2100, 0x01, 1 ],

			[ 0x2100, 0x01 ],
			[ 0x120, 0x02 ],
			
			# Request hidden sector
			[ 0x2100, 0x01 ],
			
			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],

			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],

			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x77 ],
			[ 0x13F, 0xA5 ],

			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0xAA ],
			[ 0x13F, 0xA5 ],

			[ 0x120, 0x0F ],
			[ 0x125, 0x2A ],
			[ 0x126, 0xAA ],
			[ 0x127, 0x55 ],
			[ 0x13F, 0xA5 ],

			[ 0x120, 0x0F ],
			[ 0x125, 0x55 ],
			[ 0x126, 0x55 ],
			[ 0x127, 0x77 ],
			[ 0x13F, 0xA5 ]
		]
		self.CartWrite(commands)
		return self.CartRead(0, 128)

	def CalcChecksum(self, buffer):
		header = RomFileDMG(buffer[:0x180]).GetHeader()
		target_chk_value = 0
		if header["game_title"] == "NP M-MENU MENU":
			target_sha1_value = "15f5d445c0b2fdf4221cf2a986a4a5cb8dfda131"
			target_chk_value = 0x19E8
		elif header["game_title"] == "DMG MULTI MENU ":
			target_sha1_value = "b8949fb9c4343b2c04ad59064e9d1dd78a131366"
			target_chk_value = 0xC297
		
		if target_chk_value != 0:
			if hashlib.sha1(buffer[0:0x18000]).hexdigest() != target_sha1_value:
				return 0
			elif buffer[0:0x180] == buffer[0x20000:0x20180]:
				return 1
			else:
				return target_chk_value
		else:
			return super().CalcChecksum(buffer=buffer)

class DMG_M161(DMG_MBC):
	def GetName(self):
		return "M161"

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		self.ROM_BANK_SIZE = 0x8000
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=None)
	
	def ResetBeforeBankChange(self, index):
		return True
	
	#def GetROMSize(self):
	#	return self.ROM_BANK_SIZE * math.floor(self.ROM_BANK_NUM / 2)

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x4000, (index & 0x7) ]
		]
		self.CartWrite(commands)
		return (0, 0x8000)

class DMG_HuC1(DMG_MBC5):
	def GetName(self):
		return "HuC-1"

	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x0000, 0x0A if enable else 0x0E ]
		]
		self.CartWrite(commands)

class DMG_HuC3(DMG_MBC):
	def GetName(self):
		return "HuC-3"

	def HasRTC(self):
		return True
	
	def GetRTCBufferSize(self):
		return 0x0C
	
	def ReadRTC(self):
		buffer = bytearray()
		commands = [
			[ 0x0000, 0x0B ],
			[ 0xA000, 0x60 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x0C ],
			[ 0x0000, 0x00 ],

			[ 0x0000, 0x0B ],
			[ 0xA000, 0x40 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x0C ],
			[ 0x0000, 0x00 ]
		]
		self.CartWrite(commands, delay=0.01)

		rtc = 0
		for i in range(0, 6):
			commands = [
				[ 0x0000, 0x0B ],
				[ 0xA000, 0x10 ],
				[ 0x0000, 0x0D ],
				[ 0xA000, 0xFE ],
				[ 0x0000, 0x0C ]
			]
			self.CartWrite(commands, delay=0.01)
			rtc |= (self.CartRead(0xA000) & 0x0F) << (i * 4)
			self.CartWrite([[ 0x0000, 0x00 ]], delay=0.01)
		
		buffer.extend(struct.pack("<L", rtc))

		# Add timestamp of backup time
		ts = int(time.time())
		buffer.extend(struct.pack("<Q", ts))
		
		#dstr = ' '.join(format(x, '02X') for x in buffer)
		#dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))

		return buffer

	def WriteRTC(self, buffer, advance=False):
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				print(buffer)
				if buffer == bytearray([0x00] * len(buffer)): # Reset
					hours = 0
					minutes = 0
					days = 0
				else:
					data = struct.unpack("<I", buffer[0:4])[0]
					hours = math.floor((data & 0xFFF) / 60)
					minutes = (data & 0xFFF) % 60
					days = (data >> 12) & 0xFFF
					
					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					dprint(hours, minutes, days)
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer1 = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(1, 1, 1, 0, 0, 0), "%Y-%m-%d %H:%M:%S")
						dt_buffer2 = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(1, 1, 1, hours, minutes, 0), "%Y-%m-%d %H:%M:%S")
						dt_buffer2 += datetime.timedelta(days=days)
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer2 + rd
						dprint(dt_then, dt_now, dt_buffer1, dt_buffer2, dt_new, sep="\n")
						minutes = dt_new.minute
						hours = dt_new.hour
						#temp = dt_new - dt_buffer1
						#days = temp.days
						temp = datetime.date.fromtimestamp(timestamp_now) - datetime.date.fromtimestamp(timestamp_then)
						days = temp.days + days
						dprint(minutes, hours, days)
				
				total_minutes = 60 * hours + minutes
				data = (total_minutes & 0xFFF) | ((days & 0xFFF) << 12)
				buffer[0:4] = struct.pack("<I", data)
			
			except Exception as e:
				print("Couldn’t update the RTC register values\n", e)

		commands = [
			[ 0x0000, 0x0B ],
			[ 0xA000, 0x60 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x0C ],
			[ 0x0000, 0x00 ],

			[ 0x0000, 0x0B ],
			[ 0xA000, 0x40 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x0C ],
			[ 0x0000, 0x00 ]
		]
		self.CartWrite(commands, delay=0.01)

		for i in range(0, 3):
			commands = [
				[ 0x0000, 0x0B ],
				[ 0xA000, 0x30 | (buffer[i] & 0x0F) ],
				[ 0x0000, 0x0D ],
				[ 0xA000, 0xFE ],
				[ 0x0000, 0x00 ],
				[ 0x0000, 0x0D ],
				
				[ 0x0000, 0x0B ],
				[ 0xA000, 0x30 | ((buffer[i] >> 4) & 0x0F) ],
				[ 0x0000, 0x0D ],
				[ 0xA000, 0xFE ],
				[ 0x0000, 0x00 ],
				[ 0x0000, 0x0D ]
			]
			self.CartWrite(commands, delay=0.03)
		
		commands = [
			[ 0x0000, 0x0B ],
			[ 0xA000, 0x31 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x00 ],
			[ 0x0000, 0x0D ],

			[ 0x0000, 0x0B ],
			[ 0xA000, 0x61 ],
			[ 0x0000, 0x0D ],
			[ 0xA000, 0xFE ],
			[ 0x0000, 0x00 ]
		]
		self.CartWrite(commands, delay=0.03)
		dstr = ' '.join(format(x, '02X') for x in buffer)
		dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))
	
class DMG_TAMA5(DMG_MBC):
	def GetName(self):
		return "TAMA5"

	def EnableMapper(self):
		tama5_check = self.CartRead(0xA000)
		lives = 20
		while (tama5_check & 3) != 1:
			dprint("- Current value is 0x{:X}, now writing 0xA001=0x{:X}".format(tama5_check, 0x0A))
			self.CartWrite([[0xA001, 0x0A]], sram=True)
			tama5_check = self.CartRead(0xA000)
			time.sleep(0.01)
			lives -= 1
			if lives < 0:
				print("Error: Couldn’t enable TAMA5 mapper!")
				return False
		dprint("Enabled TAMA5 successfully")
		return True
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0xA001, 0x00 ],	# ROM bank (low)
			[ 0xA000, index & 0x0F ],
			[ 0xA001, 0x01 ],	# ROM bank (high)
			[ 0xA000, (index >> 4) & 0x0F ],
		]
		start_address = 0 if index == 0 else 0x4000
		
		self.CartWrite(commands, sram=True)
		return (start_address, self.ROM_BANK_SIZE)

	def HasRTC(self):
		return True

	def GetRTCBufferSize(self):
		return 0x28
	
	def ReadRTC(self):
		buffer = bytearray()
		for page in range(0, 4):
			page_buffer = bytearray(8)
			for reg in range(0, 0x10):
				commands = [
					# Select RTC
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x08 ],
					# Select RTC register
					[ 0xA001, 0x04 ],
					[ 0xA000, reg ],
					# Select RTC operation
					[ 0xA001, 0x07 ],
					[ 0xA000, (page << 1) + 1 ],
					# Read data
					[ 0xA001, 0x0C ]
				]
				self.CartWrite(commands, sram=True)
				value1, value2 = None, None
				while value1 is None or value1 != value2:
					value2 = value1
					value1 = self.CartRead(0xA000)
				data = self.CartRead(0xA000) & 0x0F
				if reg % 2 == 0:
					page_buffer[reg>>1] = data
				else:
					page_buffer[reg>>1] |= data << 4
			buffer += page_buffer
		
		# Add timestamp of backup time
		ts = int(time.time())
		buffer.extend(struct.pack("<Q", ts))

		#dstr = ' '.join(format(x, '02X') for x in buffer)
		#print("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))

		commands = [
			# Select RTC
			[ 0xA001, 0x00 ]
		]
		self.CartWrite(commands, sram=True)
		self.SelectBankROM(0)

		return buffer

	def WriteRTC(self, buffer, advance=False):
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				if buffer == bytearray([0x00] * len(buffer)): # Reset
					seconds = 0
					minutes = 0
					hours = 0
					weekday = 0
					days = 1
					months = 1
					years = 0
					leap_year_state = 0
					z24h_flag = 1
				else:
					#dstr = ' '.join(format(x, '02X') for x in buffer)
					#print("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))

					seconds = Util.DecodeBCD(buffer[0x00])
					minutes = Util.DecodeBCD(buffer[0x01])
					hours = Util.DecodeBCD(buffer[0x02])
					weekday = buffer[0x03] & 0xF
					days = Util.DecodeBCD(buffer[0x03] >> 4 | (buffer[0x04] & 0xF) << 4)
					months = Util.DecodeBCD(buffer[0x04] >> 4 | (buffer[0x05] & 0xF) << 4)
					years = Util.DecodeBCD(buffer[0x05] >> 4 | (buffer[0x06] & 0xF) << 4)
					leap_year_state = Util.DecodeBCD(buffer[0x0D] >> 4)
					z24h_flag = Util.DecodeBCD(buffer[0x0D] & 0xF)
					#print("Old:", seconds, minutes, hours, day_of_week, days, months, years, leap_year_state, z24h_flag)
					
					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(2000 + leap_year_state, months, days, hours % 24, minutes % 60, seconds % 60), "%Y-%m-%d %H:%M:%S")
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer + rd
						
						# Weird cases
						year_new = (dt_new.year - 2000 - leap_year_state) 
						years += year_new
						if years >= 160:
							years -= 140
						elif years >= 140:
							years -= 100
						elif years >= 120:
							years -= 60
						elif years >= 100 and (years - year_new) < 100:
							years -= 100
						
						months = dt_new.month
						days = dt_new.day
						hours = dt_new.hour
						minutes = dt_new.minute
						seconds = dt_new.second
						dt_buffer_notime = dt_buffer.replace(hour=0, minute=0, second=0)
						dt_new_notime = dt_new.replace(hour=0, minute=0, second=0)
						days_passed = int((dt_new_notime.timestamp() - dt_buffer_notime.timestamp()) / 60 / 60 / 24)
						weekday += days_passed % 7
						#print("leap_year_state#1", leap_year_state)
						leap_year_state = (leap_year_state + year_new) % 4
						#print("leap_year_state#2", leap_year_state)
						#print("New:", seconds, minutes, hours, day_of_week, days, months, years, leap_year_state, z24h_flag)

				buffer[0x00] = Util.EncodeBCD(seconds)
				buffer[0x01] = Util.EncodeBCD(minutes)
				buffer[0x02] = Util.EncodeBCD(hours)
				buffer[0x03] = (weekday & 0xF) | ((Util.EncodeBCD(days) & 0xF) << 4)
				buffer[0x04] = (Util.EncodeBCD(days) >> 4) | ((Util.EncodeBCD(months) & 0xF) << 4)
				buffer[0x05] = (Util.EncodeBCD(months) >> 4) | ((Util.EncodeBCD(years) & 0xF) << 4)
				buffer[0x06] = (Util.EncodeBCD(years) >> 4)
				buffer[0x0D] = leap_year_state << 4 | z24h_flag
				
				#dstr = ' '.join(format(x, '02X') for x in buffer)
				#print("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))
			
			except Exception as e:
				print("Couldn’t update the RTC register values\n", e)

		for page in range(0, 4):
			if page == 0:
				commands = [
					# Select TAMA6
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x04 ],
					# Stop timer
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x04 ],
					[ 0xA001, 0x07 ],
					[ 0xA000, 0x00 ],
				]
				commands = [
					# Select TAMA6
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x04 ],
					# Reset timer
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x04 ],
					[ 0xA001, 0x07 ],
					[ 0xA000, 0x01 ],
				]
				self.CartWrite(commands, sram=True)

			page_buffer = buffer[page*8:page*8+8]
			for reg in range(0, 0x0D):
				commands = [
					# Select RTC
					[ 0xA001, 0x06 ],
					[ 0xA000, 0x08 ],
					# Select RTC register
					[ 0xA001, 0x04 ],
					[ 0xA000, reg ],
					# Set data
					[ 0xA001, 0x05 ]
				]
				self.CartWrite(commands, sram=True)
				if reg % 2 == 0:
					self.CartWrite([[ 0xA000, page_buffer[reg>>1] & 0xF ]], sram=True)
				else:
					self.CartWrite([[ 0xA000, page_buffer[reg>>1] >> 4 ]], sram=True)
				commands = [
					# Select RTC operation
					[ 0xA001, 0x07 ],
					[ 0xA000, (page << 1) ],
					# Read data
					[ 0xA001, 0x0C ]
				]
				self.CartWrite(commands, sram=True)
				value1, value2 = None, None
				while value1 is None or value1 != value2:
					value2 = value1
					value1 = self.CartRead(0xA000)

	def ReadWithCSPulse(self):
		return False

	def WriteWithCSPulse(self):
		return True

class DMG_Unlicensed_256M(DMG_MBC5):
	def GetName(self):
		return "256M Multi Cart"
	
	def HasFlashBanks(self):
		return True

	def SelectBankFlash(self, index):
		flash_bank = math.floor(index / 512)
		dprint(self.GetName(), "|SelectBankFlash()|", index, "->", flash_bank)

		self.CART_POWERCYCLE_FNCPTR()
		
		commands = [
			[ 0x7000, 0x00 ],
			[ 0x7001, 0x00 ],
			[ 0x7002, 0x90 + flash_bank ]
		]
		self.CURRENT_FLASH_BANK = flash_bank
		self.CartWrite(commands, delay=0.1)

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|SelectBankROM()|", index)

		#if index % 512 == 0 or abs(self.CURRENT_ROM_BANK - index) > 1:
		if (index % 512 == 0) or (self.CURRENT_FLASH_BANK != math.floor(index / 512)):
			self.SelectBankFlash(index)
		self.CURRENT_ROM_BANK = index
		index = index % 512

		commands = [
			[ 0x2100, index & 0xFF ],
			[ 0x3000, ((index >> 8) & 0xFF) ],
		]
		
		start_address = 0 if index == 0 else 0x4000
		self.CartWrite(commands)

		return (start_address, self.ROM_BANK_SIZE)

	def SelectBankRAM(self, index):
		dprint(self.GetName(), "|", index)

		flash_bank = math.floor(index / 0x10)
		
		if index % 4 == 0:
			self.EnableRAM(enable=False)
			self.CART_POWERCYCLE_FNCPTR()
			commands = [
				[ 0x7000, (0x40 * math.floor(index / 4)) & 0xFF ],
				[ 0x7001, 0xC0 ],
				[ 0x7002, 0x90 + flash_bank ]
			]
			self.CartWrite(commands, delay=0.01)
			self.EnableRAM(enable=True)
			dprint(hex(index), hex(0x90 + flash_bank), hex((0x40 * math.floor(index / 4)) & 0xFF))
		
		commands = [
			[ 0x4000, index % 4 ]
		]
		start_address = 0
		self.CartWrite(commands)

		return (start_address, self.RAM_BANK_SIZE)

class DMG_Unlicensed_WisdomTree(DMG_MBC):
	def GetName(self):
		return "Wisdom Tree"

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		self.ROM_BANK_SIZE = 0x8000
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=None)

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ index, 0 ]
		]
		self.CartWrite(commands)
		return (0, 0x8000)

class DMG_Unlicensed_XploderGB(DMG_MBC):
	def GetName(self):
		return "Xploder GB"
	
	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=None)
		self.RAM_BANK_SIZE = 0x4000

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		if index == 0:
			self.CART_POWERCYCLE_FNCPTR()
			self.CartRead(0x0102, 1)
		self.CartWrite([[ 0x0006, index & 0xFF ]])
		start_address = 0x4000
		return (start_address, self.ROM_BANK_SIZE)

	def SelectBankRAM(self, index):
		dprint(self.GetName(), "|", index)
		if index == 0:
			self.CART_POWERCYCLE_FNCPTR()
			self.CartRead(0x0102, 1)
		return self.SelectBankROM(index + 8)

class DMG_Unlicensed_Sachen(DMG_MBC):
	def GetName(self):
		return "Sachen"

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x2000, index + self.START_BANK ]
		]
		self.CartWrite(commands)
		start_address = 0x4000
		return (start_address, self.ROM_BANK_SIZE)

class DMG_Unlicensed_DatelOrbitV2(DMG_MBC):
	def GetName(self):
		return "Datel Orbit V2"

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		self.ROM_BANK_SIZE = 0x2000
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, cart_powercycle_fncptr=cart_powercycle_fncptr, clk_toggle_fncptr=None)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		if index == 0:
			self.CartRead(0x0101, 1)
			self.CartRead(0x0108, 1)
			self.CartRead(0x0101, 1)
		self.CartWrite([[ 0x7FE1, index & 0xFF ]])
		start_address = 0x4000
		return (start_address, self.ROM_BANK_SIZE)


class AGB_GPIO:
	CART_WRITE_FNCPTR = None
	CART_READ_FNCPTR = None
	CLK_TOGGLE_FNCPTR = None
	RTC = False

	# Addresses
	GPIO_REG_DAT = 0xC4 # Data
	GPIO_REG_CNT = 0xC6 # IO Select
	GPIO_REG_RE = 0xC8 # Read Enable Flag Register
	
	# Commands
	RTC_RESET = 0x60
	RTC_WRITE_STATS = 0x62
	RTC_READ_STATS = 0x63
	RTC_WRITE_DATE = 0x64
	RTC_READ_DATE = 0x65
	RTC_WRITE_TIME = 0x66
	RTC_READ_TIME = 0x67
	RTC_WRITE_ALARM = 0x68
	RTC_READ_ALARM = 0x69

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, cart_powercycle_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		self.CART_WRITE_FNCPTR = cart_write_fncptr
		self.CART_READ_FNCPTR = cart_read_fncptr
		self.CART_POWERCYCLE_FNCPTR = cart_powercycle_fncptr
		self.CLK_TOGGLE_FNCPTR = clk_toggle_fncptr
		if "rtc" in args: self.RTC = args["rtc"]
	
	def CartRead(self, address, length=0):
		if length == 0: # auto size:
			address = address * 2
			data = self.CART_READ_FNCPTR(address)
			data = struct.pack(">H", data)
			data = struct.unpack("<H", data)[0]
			dprint("0x{:X} is 0x{:X}".format(address, data))
		else:
			data = self.CART_READ_FNCPTR(address, length)
			dprint("0x{:X} is".format(address), data)
		
		return data

	def CartWrite(self, commands, delay=False):
		for command in commands:
			address = command[0]
			value = command[1]
			dprint("0x{:X} = 0x{:X}".format(address, value))
			self.CART_WRITE_FNCPTR(address, value)
			if delay is not False: time.sleep(delay)

	def RTCCommand(self, command):
		for i in range(0, 8):
			bit = (command >> (7 - i)) & 0x01
			self.CartWrite([
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 5 | (bit << 1) ]
			])

	def RTCReadData(self):
		data = 0
		for _ in range(0, 8):
			self.CartWrite([
				[ self.GPIO_REG_DAT, 4 ],
				[ self.GPIO_REG_DAT, 4 ],
				[ self.GPIO_REG_DAT, 4 ],
				[ self.GPIO_REG_DAT, 4 ],
				[ self.GPIO_REG_DAT, 4 ],
				[ self.GPIO_REG_DAT, 5 ]
			])
			bit = (self.CartRead(self.GPIO_REG_DAT) & 2) >> 1
			data = (data >> 1) | (bit << 7)
			dprint(bit, data)
		return data
	
	def RTCWriteData(self, data):
		for i in range(0, 8):
			bit = (data >> i) & 0x01
			self.CartWrite([
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 4 | (bit << 1) ],
				[ self.GPIO_REG_DAT, 5 | (bit << 1) ]
			])
	
	def RTCReadStatus(self):
		self.CartWrite([
			[ self.GPIO_REG_RE, 1 ], # Enable RTC Mapping
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 5 ],
			[ self.GPIO_REG_CNT, 7 ], # Write Enable
		])
		self.RTCCommand(self.RTC_READ_STATS)
		self.CartWrite([
			[ self.GPIO_REG_CNT, 5 ], # Read Enable
		])
		data = self.RTCReadData()
		self.CartWrite([
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_RE, 0 ], # Disable RTC Mapping
		])
		return data

	def RTCWriteStatus(self, value):
		self.CartWrite([
			[ self.GPIO_REG_RE, 1 ], # Enable RTC Mapping
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 5 ],
			[ self.GPIO_REG_CNT, 7 ], # Write Enable
		])
		self.RTCCommand(self.RTC_WRITE_STATS)
		self.RTCWriteData(value)

		self.CartWrite([
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_RE, 0 ], # Disable RTC Mapping
		])

	def HasRTC(self):
		if not self.RTC: return False

		status = self.RTCReadStatus()
		dprint(status)
		if (status >> 7) == 1:
			dprint("No RTC because of set RTC Status Register Power Flag:", status >> 7 & 1)
			return 1
		if (status >> 6) != 1:
			dprint("Unexpected RTC Status Register 24h Flag:", status >> 6 & 1)
			#return 2
		
		rom1 = self.CartRead(self.GPIO_REG_DAT, 6)
		self.CartWrite([
			[ self.GPIO_REG_RE, 1 ], # Enable RTC Mapping
		])
		rom2 = self.CartRead(self.GPIO_REG_DAT, 6)
		self.CartWrite([
			[ self.GPIO_REG_RE, 0 ], # Disable RTC Mapping
		])
		#dprint(rom1, rom2)
		if (rom1 == rom2):
			dprint("No RTC because ROM data didn’t change:", rom1, rom2)
			return 3
		
		return True
	
	def ReadRTC(self):
		if not self.RTC: return False
		self.CartWrite([
			[ self.GPIO_REG_RE, 1 ], # Enable RTC Mapping
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 5 ],
			[ self.GPIO_REG_CNT, 7 ], # Write Enable
		])
		self.RTCCommand(self.RTC_READ_DATE)
		self.CartWrite([
			[ self.GPIO_REG_CNT, 5 ], # Read Enable
		])
		buffer = bytearray()
		for _ in range(0, 7):
			buffer.append(self.RTCReadData())
		
		self.CartWrite([
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_RE, 0 ], # Disable RTC Mapping
		])
		
		# Add timestamp of backup time
		ts = int(time.time())
		buffer.append(self.RTCReadStatus()) # 24h mode = 0x40, reset flag = 0x80
		buffer.extend(struct.pack("<Q", ts))

		dstr = ' '.join(format(x, '02X') for x in buffer)
		dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))
		
		# Digits are BCD (Binary Coded Decimal)
		#[07] 00 01 27 05 06 30 20
		#[07] 00 01 27 05 06 30 28
		# "27 days, 06:51:55"
		#[07] 00 01 27 05 06 52 18
		#     YY MM DD WW HH MM SS
		return buffer
	
	def WriteRTC(self, buffer, advance=False):
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				if buffer == bytearray([0xFF] * len(buffer)): # Reset
					years = 0
					months = 1
					days = 1
					weekday = 0
					hours = 0
					minutes = 0
					seconds = 0
					rtc_status = 0x40 | 0x80
				else:
					years = Util.DecodeBCD(buffer[0x00])
					months = Util.DecodeBCD(buffer[0x01])
					days = Util.DecodeBCD(buffer[0x02])
					weekday = Util.DecodeBCD(buffer[0x03])
					hours = Util.DecodeBCD(buffer[0x04] & 0x7F)
					minutes = Util.DecodeBCD(buffer[0x05])
					seconds = Util.DecodeBCD(buffer[0x06])
					rtc_status = buffer[0x07]
					if rtc_status == 0x01: rtc_status = 0x40 # old dumps had this value

					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(years + 2000, months % 12, days % 31, hours % 60, minutes % 60, seconds % 60), "%Y-%m-%d %H:%M:%S")
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer + rd
						years = dt_new.year - 2000
						months = dt_new.month
						days = dt_new.day
						dt_buffer_notime = dt_buffer.replace(hour=0, minute=0, second=0)
						dt_new_notime = dt_new.replace(hour=0, minute=0, second=0)
						days_passed = int((dt_new_notime.timestamp() - dt_buffer_notime.timestamp()) / 60 / 60 / 24)
						weekday += days_passed % 7
						hours = dt_new.hour
						minutes = dt_new.minute
						seconds = dt_new.second
				
				#dprint(years, months, days, weekday, hours, minutes, seconds)
				buffer[0x00] = Util.EncodeBCD(years)
				buffer[0x01] = Util.EncodeBCD(months)
				buffer[0x02] = Util.EncodeBCD(days)
				buffer[0x03] = Util.EncodeBCD(weekday)
				buffer[0x04] = Util.EncodeBCD(hours)
				if hours >= 12: buffer[0x04] |= 0x80
				buffer[0x05] = Util.EncodeBCD(minutes)
				buffer[0x06] = Util.EncodeBCD(seconds)
				
				dstr = ' '.join(format(x, '02X') for x in buffer)
				dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))
			
			except Exception as e:
				print("Couldn’t update the RTC register values\n", e)
		
		self.CartWrite([
			[ self.GPIO_REG_RE, 1 ], # Enable RTC Mapping
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 5 ],
			[ self.GPIO_REG_CNT, 7 ], # Write Enable
		])
		self.RTCCommand(self.RTC_WRITE_DATE)
		for i in range(0, 7):
			self.RTCWriteData(buffer[i])

		self.CartWrite([
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_DAT, 1 ],
			[ self.GPIO_REG_RE, 0 ], # Disable RTC Mapping
		])

		self.RTCWriteStatus(rtc_status)

