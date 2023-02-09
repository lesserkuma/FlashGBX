# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import datetime, struct, copy
from . import Util
from .RomFileDMG import RomFileDMG

class GBMemoryMap:
	MAP_DATA = bytearray([0xFF] * 0x80)
	IS_MENU = False
	
	def __init__(self, rom=None, oldmap=None):
		if rom is None: return
		if rom == bytearray([0xFF] * len(rom)):
			self.MAP_DATA = bytearray([0x00] * 0x80)
		elif rom is not None:
			self.ImportROM(rom)
			if oldmap is not None:
				self.MAP_DATA[0x70:0x78] = oldmap[0x70:0x78] # keep existing cart id
				write_count = struct.unpack("=H", oldmap[0x6E:0x70])[0]
				write_count += 1
				if write_count > 0xFFFF: write_count = 0xFFFF
				self.MAP_DATA[0x6E:0x70] = struct.pack("=H", write_count) # update write count
	
	def ParseMapData(self, buffer_map, buffer_rom=None):
		data = {}
		try:
			keys = ["mapper_params", "f_size", "b_size", "game_code", "title", "timestamp", "kiosk_id", "write_count", "cart_id", "padding", "unknown"]
			values = struct.unpack("=24sHH12s44s18s8sH8s6sH", buffer_map)
			data = dict(zip(keys, values))
			data["mapper_params"] = data["mapper_params"].hex().upper()
			data["cart_id"] = data["cart_id"].hex().upper()

			rom_header = RomFileDMG(buffer_rom[:0x180]).GetHeader()
			if (rom_header["game_title"] in ("NP M-MENU MENU", "DMG MULTI MENU ")):
				keys = ["menu_index", "f_offset", "b_offset", "f_size", "b_size", "game_code", "title", "title_gfx", "timestamp", "kiosk_id", "padding", "comment"]
				values = struct.unpack("=BBBHH12s44s384s18s8s23s16s", buffer_rom[0x1C000:0x1C200])
				data_menu = dict(zip(keys, values))
				data["game_code"] = data_menu["game_code"].decode("ASCII", "ignore")
				data["title"] = data_menu["title"].decode("SHIFT-JIS", "ignore")
				data["timestamp"] = data_menu["timestamp"].decode("ASCII", "ignore")
				data["kiosk_id"] = data_menu["kiosk_id"].decode("ASCII", "ignore")
			else:
				data["game_code"] = data["game_code"].decode("ASCII", "ignore")
				data["title"] = data["title"].decode("SHIFT-JIS", "ignore")
				data["timestamp"] = data["timestamp"].decode("ASCII", "ignore")
				data["kiosk_id"] = data["kiosk_id"].decode("ASCII", "ignore")
		except:
			pass
		return data

	def ImportROM(self, data):
		info = {"map":{}, "menu":{}}
		if len(data) < 0x180:
			return False
		info["rom_header"] = RomFileDMG(data[:0x180]).GetHeader()
		self.IS_MENU = (info["rom_header"]["game_title"] in ("NP M-MENU MENU", "DMG MULTI MENU "))
		
		data = copy.deepcopy(data)
		if len(data) < 0x20000:
			data = bytearray(data) + bytearray([0xFF] * (0x20000 - len(data)))
		
		if not self.IS_MENU:
			mbc_type = self.MapperToMBCType(info["rom_header"]["mapper_raw"])
			if mbc_type is False: return
			if len(data) <= 0x20000:
				rom_size = 0b010
			elif len(data) <= 0x40000:
				rom_size = 0b011
			elif len(data) <= 0x80000:
				rom_size = 0b100
			else:
				rom_size = 0b101

			if info["rom_header"]["ram_size_raw"] not in Util.DMG_Header_RAM_Sizes_Map:
				sram_size = 0
				sram_type = 0b000
			else:
				sram_size = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(info["rom_header"]["ram_size_raw"])]
				if sram_size == 0:
					sram_type = 0b000
				elif sram_size == 0x2000:
					sram_type = 0b010
				elif sram_size == 0x8000:
					sram_type = 0b011
				elif sram_size == 0x10000:
					sram_type = 0b100
				elif sram_size == 0x20000:
					sram_type = 0b101
				else:
					sram_type = 0b000
			
			info["map"] = {
				"mbc_type":mbc_type,
				"rom_size":rom_size,
				"sram_type":sram_type,
				"rom_start_block":0,
				"ram_start_block":0,
				"raw":bytearray()
			}

			info["menu"]["metadata"] = {}
			info["menu"]["metadata"]["f_size"] = int(len(data) / (128 * 1024))
			if info["map"]["sram_type"] == 0b000: # None
				info["menu"]["metadata"]["b_size"] = 0
			elif info["map"]["sram_type"] == 0b001: # SRAM MBC2 512 Byte
				info["menu"]["metadata"]["b_size"] = 64 #4
			elif info["map"]["sram_type"] == 0b010: # SRAM 8 KB
				info["menu"]["metadata"]["b_size"] = 64
			elif info["map"]["sram_type"] == 0b011: # SRAM 32 KB
				info["menu"]["metadata"]["b_size"] = 256
			elif info["map"]["sram_type"] == 0b100: # SRAM 64 KB
				info["menu"]["metadata"]["b_size"] = 512
			elif info["map"]["sram_type"] == 0b101: # SRAM 128 KB
				info["menu"]["metadata"]["b_size"] = 1024
			
			game_code = info["rom_header"]["game_code"]
			info["menu"]["metadata"]["game_code"] = "{:s} -{:4s}-  ".format("CGB" if info["rom_header"]["cgb"] == 0xC0 else "DMG", game_code).encode("ascii")
			info["menu"]["metadata"]["title"] = info["rom_header"]["game_title"].encode("ascii").ljust(0x2C)
			info["menu"]["metadata"]["timestamp"] = datetime.datetime.now().strftime('%d/%m/%Y%H:%M:%S').encode("ascii")
			info["menu"]["metadata"]["kiosk_id"] = "{:s}".format(Util.APPNAME).encode("ascii").ljust(8, b'\xFF')
			info["menu"]["raw"] = bytearray(0x56)
			data = info
			
			keys = ["f_size", "b_size", "game_code", "title", "timestamp", "kiosk_id"]
			values = []
			for key in keys:
				values.append(data["menu"]["metadata"][key])
			buffer = struct.pack("=HH12s44s18s8s", *values)
			data["menu"]["raw"] = buffer

			temp = 0
			temp |= (data["map"]["mbc_type"] & 0x7) << 29
			temp |= (data["map"]["rom_size"] & 0x7) << 26
			temp |= (data["map"]["sram_type"] & 0x7) << 23
			temp |= (data["map"]["rom_start_block"] & 0x7F) << 16
			temp |= (data["map"]["ram_start_block"] & 0x7F) << 8
			data["map"]["raw"] = temp

			self.MAP_DATA[0x00:0x7E] = bytearray([0xFF] * 0x7E)
			self.MAP_DATA[0x6E:0x70] = bytearray([0x00] * 2)
			#self.MAP_DATA[0x70:0x78] = struct.pack("=8s", "{:s}".format(Util.VERSION_PEP440).encode("ascii").ljust(8, b'\xFF'))
			self.MAP_DATA[0x7E:0x80] = bytearray([0x00] * 2)
			self.MAP_DATA[0:3] = struct.pack(">I", data["map"]["raw"])[:3]
			self.MAP_DATA[0x18:0x18+len(data["menu"]["raw"])] = data["menu"]["raw"]

		elif info["rom_header"]["game_title"] == "NP M-MENU MENU":
			menu_items = []
			rom_offset = 0
			ram_offset = 0
			for i in range(0, 8):
				pos = 0x1C000 + (i * 0x200)
				menu_item = data[pos:pos+0x200]
				keys = ["menu_index", "f_offset", "b_offset", "f_size", "b_size", "game_code", "title", "title_gfx", "timestamp", "kiosk_id", "padding", "comment"]
				values = struct.unpack("=BBBHH12s44s384s18s8s23s16s", menu_item)
				info = dict(zip(keys, values))
				if info["menu_index"] == 0xFF: continue
				info["rom_data_offset"] = info["f_offset"] * (128 * 1024)
				info["rom_data_size"] = info["f_size"] * (128 * 1024)
				info["ram_data_offset"] = info["b_offset"] * (8 * 1024)
				info["ram_data_size"] = self.GetBlockSizeBackup(info["b_size"]) * (8 * 1024)
				del(info["title_gfx"])
				info["rom_start_block"] = int(rom_offset / 0x8000)
				rom_offset += info["rom_data_size"]
				info["ram_start_block"] = int(ram_offset / 0x800)
				ram_offset += info["ram_data_size"]
				info["rom_header"] = RomFileDMG(data[info["rom_data_offset"]:info["rom_data_offset"]+0x180]).GetHeader()
				mbc_type = self.MapperToMBCType(info["rom_header"]["mapper_raw"])
				if mbc_type is False: return

				if info["rom_data_size"] <= 0x20000:
					rom_size = 0b010
				elif info["rom_data_size"] <= 0x40000:
					rom_size = 0b011
				elif info["rom_data_size"] <= 0x80000:
					rom_size = 0b100
				else:
					rom_size = 0b101

				if info["rom_header"]["game_title"] == "NP M-MENU MENU" or info["rom_header"]["ram_size_raw"] not in Util.DMG_Header_RAM_Sizes_Map:
					sram_size = 0
					sram_type = 0b000
				else:
					sram_size = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(info["rom_header"]["ram_size_raw"])]
					if sram_size == 0:
						sram_type = 0b000
					elif sram_size == 0x2000:
						sram_type = 0b010
					elif sram_size == 0x8000:
						sram_type = 0b011
					elif sram_size == 0x10000:
						sram_type = 0b100
					elif sram_size == 0x20000:
						sram_type = 0b101
					else:
						sram_type = 0b000

				info["map"] = {
					"mbc_type":mbc_type,
					"rom_size":rom_size,
					"sram_type":sram_type,
					"rom_start_block":info["rom_start_block"],
					"ram_start_block":info["ram_start_block"],
					"raw":bytearray()
				}
				
				temp = 0
				temp |= (info["map"]["mbc_type"] & 0x7) << 29
				temp |= (info["map"]["rom_size"] & 0x7) << 26
				temp |= (info["map"]["sram_type"] & 0x7) << 23
				temp |= (info["map"]["rom_start_block"] & 0x7F) << 16
				temp |= (info["map"]["ram_start_block"] & 0x7F) << 8
				info["map"]["raw"] = temp
				menu_items.append(info)
			
			self.MAP_DATA[0x00:0x7E] = bytearray([0xFF] * 0x7E)
			self.MAP_DATA[0x6E:0x70] = bytearray([0x00] * 2)
			#self.MAP_DATA[0x70:0x78] = struct.pack("=8s", "{:s}".format(Util.VERSION_PEP440).encode("ascii").ljust(8, b'\xFF'))
			self.MAP_DATA[0x7E:0x80] = bytearray([0x00] * 2)
			for i in range(0, len(menu_items)):
				pos = i * 3
				self.MAP_DATA[pos:pos+3] = struct.pack(">I", menu_items[i]["map"]["raw"])[:3]
			self.MAP_DATA[0x54:0x66] = struct.pack("=18s", datetime.datetime.now().strftime('%d/%m/%Y%H:%M:%S').encode("ascii"))
			self.MAP_DATA[0x66:0x6E] = struct.pack("=8s", "{:s}".format(Util.APPNAME).encode("ascii").ljust(8, b'\xFF'))

	def MapperToMBCType(self, mbc):
		if mbc == 0x00: # ROM only
			mbc_type = 0
		elif mbc in (0x01, 0x02, 0x03): # MBC1
			mbc_type = 1
		elif mbc == 0x06: # MBC2
			mbc_type = 2
		elif mbc in (0x10, 0x13): # MBC3
			mbc_type = 3
		elif mbc in (0x19, 0x1A, 0x1B, 0x1C, 0x1E, 0x105): # MBC5
			mbc_type = 5
		else:
			mbc_type = False
		return mbc_type
	
	def GetBlockSizeBackup(self, b_size=None):
		if b_size == 0:
			b_size = 0
		elif b_size == 1:
			b_size = 1
		elif b_size == 64:
			b_size = 1
		elif b_size == 256:
			b_size = 4
		elif b_size == 1024:
			b_size = 16
		else:
			b_size = 4
		return b_size

	def IsMenu(self):
		return self.IS_MENU
	
	def GetMapData(self):
		if self.MAP_DATA == bytearray([0xFF] * 0x80):
			return False
		return self.MAP_DATA
