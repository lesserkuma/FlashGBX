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
	CLK_TOGGLE_FNCPTR = None
	ROM_BANK_SIZE = 0
	RAM_BANK_SIZE = 0
	ROM_BANK_NUM = 0
	CURRENT_ROM_BANK = 0

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		if "mbc" in args: self.MBC_ID = args["mbc"]
		if "rom_banks" in args: self.ROM_BANK_NUM = args["rom_banks"]
		self.CART_WRITE_FNCPTR = cart_write_fncptr
		self.CART_READ_FNCPTR = cart_read_fncptr
		self.CLK_TOGGLE_FNCPTR = clk_toggle_fncptr
		self.ROM_BANK_SIZE = 0x4000
		self.RAM_BANK_SIZE = 0x2000

	def GetInstance(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		mbc_id = args["mbc"]
		if mbc_id in (0x01, 0x02, 0x03):						# 0x01:'MBC1', 0x02:'MBC1+SRAM', 0x03:'MBC1+SRAM+BATTERY',
			return DMG_MBC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x06:									# 0x06:'MBC2+SRAM+BATTERY',
			return DMG_MBC2(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x10, 0x13):							# 0x10:'MBC3+RTC+SRAM+BATTERY', 0x13:'MBC3+SRAM+BATTERY',
			return DMG_MBC3(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x19, 0x1B, 0x1C, 0x1E):				# 0x19:'MBC5', 0x1B:'MBC5+SRAM+BATTERY', 0x1C:'MBC5+RUMBLE', 0x1E:'MBC5+RUMBLE+SRAM+BATTERY',
			return DMG_MBC5(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x20:									# 0x20:'MBC6+FLASH+SRAM+BATTERY',
			return DMG_MBC6(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x22:									# 0x22:'MBC7+ACCELEROMETER+EEPROM',
			return DMG_MBC7(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x101, 0x103):							# 0x101:'MBC1M', 0x103:'MBC1M+SRAM+BATTERY',
			return DMG_MBC1M(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id in (0x0B, 0x0D):							# 0x0B:'MMM01',  0x0D:'MMM01+SRAM+BATTERY',
			return DMG_MMM01(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFC:									# 0xFC:'GBD+SRAM+BATTERY',
			return DMG_GBD(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x105:									# 0x105:'G-MMC1+SRAM+BATTERY',
			return DMG_GMMC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0x104:									# 0x104:'M161',
			return DMG_M161(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFF:									# 0xFF:'HuC-1+IR+SRAM+BATTERY',
			return DMG_HuC1(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFE:									# 0xFE:'HuC-3+RTC+SRAM+BATTERY',
			return DMG_HuC3(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		elif mbc_id == 0xFD:									# 0xFD:'TAMA5+RTC+EEPROM'
			return DMG_TAMA5(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
		else:
			self.__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=clk_toggle_fncptr)
			return self
	
	def CartRead(self, address, length=0):
		if length == 0: # auto size:
			return self.CART_READ_FNCPTR(address)
		else:
			return self.CART_READ_FNCPTR(address, length)

	def CartWrite(self, commands, delay=False):
		for command in commands:
			address = command[0]
			value = command[1]
			self.CART_WRITE_FNCPTR(address, value)
			if delay is not False: time.sleep(delay)

	def GetName(self):
		return "Unknown MBC {:d}".format(self.MBC_ID)

	def GetFullName(self):
		try:
			return Util.DMG_Header_Mapper[self.MBC_ID]
		except:
			return "Unknown MBC {:d}".format(self.MBC_ID)

	def GetROMBank(self):
		return self.CURRENT_ROM_BANK

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
		commands = [
			[ 0x6000, 0x01 if enable else 0x00 ],
			[ 0x0000, 0x0A if enable else 0x00 ],
		]
		self.CartWrite(commands)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0x6000, 0 ],
			[ 0x4000, index >> 5 ],
			[ 0x2000, index & 0x1F ],
		]
		start_address = 0 if index == 0 else 0x4000
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
			#[ 0x6000, 0x01 if enable else 0x00 ],
			[ 0x0000, 0x0A if enable else 0x00 ],
		]
		self.CartWrite(commands)
	
	def HasRTC(self):
		dprint(self.GetName())
		if self.MBC_ID != 16: return False
		self.EnableRAM(enable=False)
		self.EnableRAM(enable=True)
		#self.CartWrite([ [0x4000, 0x08] ])
		self.LatchRTC()

		skipped = True
		for i in range(0x08, 0x0D):
			self.CLK_TOGGLE_FNCPTR(60)
			self.CartWrite([ [0x4000, i] ])
			data = self.CartRead(0xA000, 0x800)
			if data[0] in (0, 0xFF): continue
			skipped = False
			if data != bytearray([data[0]] * 0x800): return False
		return skipped is False

		#ram1 = self.CartRead(0xA000, 0x10)
		#ram2 = ram1
		#t1 = time.time()
		#t2 = 0
		#while t2 < (t1 + 1):
		#	self.LatchRTC()
		#	ram2 = self.CartRead(0xA000, 0x10)
		#	if ram1 != ram2: break
		#	t2 = time.time()
		#dprint("RTC_S {:02X} != {:02X}?".format(ram1[0], ram2[0]), ram1 != ram2)
		#time.sleep(0.1)
		#return (ram1 != ram2)

	def GetRTCBufferSize(self):
		return 0x30

	def LatchRTC(self):
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x0000, 0x0A ] ])
		time.sleep(0.01)
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x6000, 0x00 ] ])
		self.CLK_TOGGLE_FNCPTR(60)
		self.CartWrite([ [ 0x6000, 0x01 ] ])
		time.sleep(0.01)

	def ReadRTC(self):
		#self.EnableRAM(enable=True)
		buffer = bytearray()
		for i in range(0x08, 0x0D):
			self.CLK_TOGGLE_FNCPTR(60)
			self.CartWrite([ [0x4000, i] ])
			buffer.extend(struct.pack("<I", self.CartRead(0xA000)))
		buffer.extend(buffer) # copy

		# Add timestamp of backup time
		ts = int(time.time())
		buffer.extend(struct.pack("<Q", ts))
		
		return buffer

	def WriteRTC(self, buffer, advance=False):
		dprint(buffer)
		#self.LatchRTC()
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				if buffer == bytearray([0xFF] * len(buffer)): # Reset
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
					#debug
					#timestamp_now = 1663106370 # 2022-09-13 23:59:30
					#dt_now = datetime.datetime.fromtimestamp(timestamp_now)
					#debug
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

class DMG_MBC5(DMG_MBC):
	def GetName(self):
		return "MBC5"
	
	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x6000, 0x01 if enable else 0x00 ],
			[ 0x0000, 0x0A if enable else 0x00 ],
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
	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=None)
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
		while True: # TODO: error handling
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

class DMG_MBC1M(DMG_MBC):
	def GetName(self):
		return "MBC1M"

	def EnableRAM(self, enable=True):
		dprint(self.GetName(), "|", enable)
		commands = [
			[ 0x6000, 0x01 if enable else 0x00 ],
			[ 0x0000, 0x0A if enable else 0x00 ],
		]
		self.CartWrite(commands)
	
	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		if index < 10:
			commands = [
				[ 0x4000, index >> 4 ],
				[ 0x2000, index & 0x1F ],
			]
		else:
			commands = [
				[ 0x4000, index >> 4 ],
				[ 0x2000, 0x10 | (index & 0x1F) ],
			]
		
		start_address = 0 if index == 0 else 0x4000

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
		if header["game_title"] == "NP M-MENU MENU":
			target_chk_value = 0x19E8
			if hashlib.sha1(buffer[0:0x18000]).hexdigest() != "15f5d445c0b2fdf4221cf2a986a4a5cb8dfda131":
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

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		super().__init__(args=args, cart_write_fncptr=cart_write_fncptr, cart_read_fncptr=cart_read_fncptr, clk_toggle_fncptr=None)
		self.ROM_BANK_SIZE = 0x8000
		self.ROM_BANK_NUM = 8
	
	def ResetBeforeBankChange(self, index):
		return True
	
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
				if buffer == bytearray([0xFF] * len(buffer)): # Reset
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
		dprint("Enabling TAMA5")
		lives = 20
		while (tama5_check & 3) != 1:
			dprint("└Current value is 0x{:X}, now writing 0xA001=0x{:X}".format(tama5_check, Util.TAMA5_REG.ENABLE.value))
			self.CART_WRITE_FNCPTR(0xA001, Util.TAMA5_REG.ENABLE.value)
			tama5_check = self.CartRead(0xA000)
			time.sleep(0.1)
			lives -= 1
			if lives < 0: return False
		return True

	def SelectBankROM(self, index):
		dprint(self.GetName(), "|", index)
		commands = [
			[ 0xA001, Util.TAMA5_REG.ROM_BANK_L.value ],	# ROM bank (low)
			[ 0xA000, index & 0x0F ],
			[ 0xA001, Util.TAMA5_REG.ROM_BANK_H.value ],	# ROM bank (high)
			[ 0xA000, (index >> 4) & 0x0F ],
		]
		start_address = 0 if index == 0 else 0x4000
		
		self.CartWrite(commands)
		return (start_address, self.ROM_BANK_SIZE)

	def HasRTC(self):
		#return True
		return False # temporarily disabled

	def GetRTCBufferSize(self):
		return 0x18

	def ReadRTC(self):
		buffer = bytearray()
		commands = [
			[ 0xA001, Util.TAMA5_REG.MEM_WRITE_L.value ], # set address
			[ 0xA000, 0x0D ], # address
			[ 0xA001, Util.TAMA5_REG.MEM_WRITE_H.value ], # set value to write
			[ 0xA000, 0 ], # value
			[ 0xA001, Util.TAMA5_REG.ADDR_H_SET_MODE.value ], # register select
			[ 0xA000, Util.TAMA5_CMD.RTC.value << 1 ], # rtc mode
			[ 0xA001, Util.TAMA5_REG.ADDR_L.value ], # set access mode
			[ 0xA000, 0 ] # 0 = write
		]
		self.CartWrite(commands)
		time.sleep(0.03)

		for r in range(0, 0x0D):
			commands = [
				[ 0xA001, Util.TAMA5_REG.MEM_WRITE_L.value ], # set address
				[ 0xA000, r ], # address
				[ 0xA001, Util.TAMA5_REG.ADDR_H_SET_MODE.value ], # register select
				[ 0xA000, Util.TAMA5_CMD.RTC.value << 1 ], # rtc mode
				[ 0xA001, Util.TAMA5_REG.ADDR_L.value ], # set access mode
				[ 0xA000, 1 ], # 1 = read
				[ 0xA001, Util.TAMA5_REG.MEM_READ_L.value ] # data out
			]
			self.CartWrite(commands)
			time.sleep(0.03)
			data = self.CartRead(0xA000)
			buffer.append(data)
		
		# Add timestamp of backup time
		ts = int(time.time())
		buffer.extend([0xFF, 0xFF, 0xFF])
		buffer.extend(struct.pack("<Q", ts))

		#dstr = ' '.join(format(x, '02X') for x in buffer)
		#dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))

		return buffer

	def WriteRTC(self, buffer, advance=False):
		if advance:
			try:
				dt_now = datetime.datetime.fromtimestamp(time.time())
				if buffer == bytearray([0xFF] * len(buffer)): # Reset
					seconds = 0
					minutes = 0
					hours = 0
					days = 1
					months = 1
				else:
					seconds = Util.DecodeBCD(buffer[0x00] | buffer[0x01] << 4)
					minutes = Util.DecodeBCD(buffer[0x02] | buffer[0x03] << 4)
					hours = Util.DecodeBCD(buffer[0x04] | buffer[0x05] << 4)
					days = Util.DecodeBCD(buffer[0x07] | buffer[0x08] << 4)
					months = Util.DecodeBCD(buffer[0x09] | buffer[0x0A] << 4)
					#dprint(seconds, minutes, hours, days, months)
					
					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(1, months % 12, days % 31, hours % 24, minutes % 60, seconds % 60), "%Y-%m-%d %H:%M:%S")
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer + rd
						#print(dt_then, dt_now, dt_buffer, dt_new, sep="\n")
						months = dt_new.month
						days = dt_new.day
						hours = dt_new.hour
						minutes = dt_new.minute
						seconds = dt_new.second
						dprint(seconds, minutes, hours, days, months)

				#dprint(years, months, days, weekday, hours, minutes, seconds)
				temp = Util.EncodeBCD(seconds)
				buffer[0x00] = temp & 0x0F
				buffer[0x01] = temp >> 4 & 0x0F
				temp = Util.EncodeBCD(minutes)
				buffer[0x02] = temp & 0x0F
				buffer[0x03] = temp >> 4 & 0x0F
				temp = Util.EncodeBCD(hours)
				buffer[0x04] = temp & 0x0F
				buffer[0x05] = temp >> 4 & 0x0F
				temp = Util.EncodeBCD(days)
				buffer[0x07] = temp & 0x0F
				buffer[0x08] = temp >> 4 & 0x0F
				temp = Util.EncodeBCD(months)
				buffer[0x09] = temp & 0x0F
				buffer[0x0A] = temp >> 4 & 0x0F
				
				dstr = ' '.join(format(x, '02X') for x in buffer)
				dprint("[{:02X}] {:s}".format(int(len(dstr)/3) + 1, dstr))
			
			except Exception as e:
				print("Couldn’t update the RTC register values\n", e)

		for r in range(0, 0x10):
			commands = [
				[ 0xA001, Util.TAMA5_REG.MEM_WRITE_L.value ], # set address
				[ 0xA000, r ], # address
				[ 0xA001, Util.TAMA5_REG.MEM_WRITE_H.value ], # set value to write
				[ 0xA000, buffer[r] ], # value
				[ 0xA001, Util.TAMA5_REG.ADDR_H_SET_MODE.value ], # register select
				[ 0xA000, Util.TAMA5_CMD.RTC.value << 1 ], # rtc mode
				[ 0xA001, Util.TAMA5_REG.ADDR_L.value ], # set access mode
				[ 0xA000, 0 ] # 0 = write
			]
			self.CartWrite(commands)
			time.sleep(0.03)
	
	def ReadWithCSPulse(self):
		return False

	def WriteWithCSPulse(self):
		return True


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

	def __init__(self, args=None, cart_write_fncptr=None, cart_read_fncptr=None, clk_toggle_fncptr=None):
		if args is None: args = {}
		self.CART_WRITE_FNCPTR = cart_write_fncptr
		self.CART_READ_FNCPTR = cart_read_fncptr
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

	def HasRTC(self):
		if not self.RTC: return False

		status = self.RTCReadStatus()
		dprint(status)
		if (status >> 7) == 1:
			dprint("No RTC because of RTC Status Register Power Flag:", status >> 7 & 1)
			return 1
		if (status >> 6) != 1:
			dprint("No RTC because of RTC Status Register 24h Flag:", status >> 6 & 1)
			return 2

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
		buffer.extend(b'\x01') # 24h mode (TODO: read from cart?)
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
				else:
					years = Util.DecodeBCD(buffer[0x00])
					months = Util.DecodeBCD(buffer[0x01])
					days = Util.DecodeBCD(buffer[0x02])
					weekday = Util.DecodeBCD(buffer[0x03])
					hours = Util.DecodeBCD(buffer[0x04] & 0x7F)
					minutes = Util.DecodeBCD(buffer[0x05])
					seconds = Util.DecodeBCD(buffer[0x06])
					timestamp_then = struct.unpack("<Q", buffer[-8:])[0]
					timestamp_now = int(time.time())
					#debug
					#timestamp_now = 4102441140 # 2099-12-23 23:59:00
					#dt_now = datetime.datetime.fromtimestamp(timestamp_now)
					#debug
					if timestamp_then < timestamp_now:
						dt_then = datetime.datetime.fromtimestamp(timestamp_then)
						dt_buffer = datetime.datetime.strptime("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(years + 2000, months % 12, days % 31, hours % 60, minutes % 60, seconds % 60), "%Y-%m-%d %H:%M:%S")
						rd = relativedelta(dt_now, dt_then)
						dt_new = dt_buffer + rd
						#print(dt_then, dt_now, dt_buffer, dt_new, sep="\n")
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
		#[0F] 00 01 27 05 08 24 08 51 4B 7C 60 00 00 00 00
		#[0F] 00 01 27 05 08 25 03 88 4B 7C 60 00 00 00 00
		#[0F] 00 01 01 05 08 00 15 96 4B 7C 60 00 00 00 00
		#[0F] 00 01 01 05 08 00 39 BF 4B 7C 60 00 00 00 00
		#[0F] 00 01 01 05 08 00 46 BB 4B 7C 60 00 00 00 00
