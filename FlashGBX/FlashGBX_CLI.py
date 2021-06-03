# -*- coding: utf-8 -*-
# FlashGBX
# Author: Lesserkuma (github.com/lesserkuma)

import datetime, shutil, platform, os, json, math, traceback, re, time
try:
	# pylint: disable=import-error
	import readline
	readline.set_completer_delims('\t\n=')
	readline.parse_and_bind("tab:complete")
except:
	pass

from .RomFileDMG import RomFileDMG
from .RomFileAGB import RomFileAGB
from .PocketCamera import PocketCamera
from .Util import APPNAME, VERSION, ANSI
from . import Util
from . import hw_GBxCartRW, hw_GBxCartRW_ofw
hw_devices = [hw_GBxCartRW, hw_GBxCartRW_ofw]

class FlashGBX_CLI():
	ARGS = {}
	CONFIG_PATH = ""
	FLASHCARTS = { "DMG":{}, "AGB":{} }
	CONN = None
	DEVICE = None
	PROGRESS = None
	
	def __init__(self, args):
		self.ARGS = args
		self.CONFIG_PATH = args['config_path']
		self.FLASHCARTS = args["flashcarts"]
		self.PROGRESS = Util.Progress(self.UpdateProgress)
		
		global prog_bar_part_char
		if platform.system() == "Windows":
			prog_bar_part_char = [" ", " ", " ", " ", "▌", "▌", "▌", "▌"]
		else:
			prog_bar_part_char = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
	
	def run(self):
		config_ret = self.ARGS["config_ret"]
		for i in range(0, len(config_ret)):
			if config_ret[i][0] < 1:
				print(config_ret[i][1])
			elif config_ret[i][0] == 2:
				print("{:s}{:s}{:s}".format(ANSI.YELLOW, config_ret[i][1], ANSI.RESET))
			elif config_ret[i][0] == 2:
				print("{:s}{:s}{:s}".format(ANSI.RED, config_ret[i][1], ANSI.RESET))
		
		args = self.ARGS["argparsed"]
		config_path = Util.formatPathOS(self.CONFIG_PATH)
		print("Configuration directory: {:s}\n".format(config_path))
		
		# Ask interactively if no args set
		if args.action is None:
			actions = ["info", "backup-rom", "flash-rom", "backup-save", "restore-save", "erase-save", "gbcamera-extract", "debug-test-save"]
			print("Select Operation:\n 1) Read Cartridge Information\n 2) Backup ROM\n 3) Flash ROM\n 4) Backup Save Data\n 5) Restore Save Data\n 6) Erase Save Data\n 7) Extract Game Boy Camera Pictures\n")
			args.action = input("Enter number 1-7 [1]: ").lower().strip()
			print("")
			try:
				args.action = actions[int(args.action) - 1]
			except:
				if args.action == "":
					args.action = "info"
				else:
					print("Canceled.")
					return
		
		if args.action is None or args.action not in ("gbcamera-extract"):
			if not self.FindDevices():
				print("No devices found.")
				return
			else:
				if not self.ConnectDevice():
					print("Couldn’t connect to the device.")
					return
				dev = self.DEVICE[1]
				builddate = dev.GetFWBuildDate()
				if builddate != "":
					print("\nConnected to {:s} (dated {:s})".format(dev.GetFullNameExtended(), builddate))
				else:
					print("\nConnected to {:s}".format(dev.GetFullNameExtended()))
		
		if args.action == "gbcamera-extract":
			if args.path == "auto":
				args.path = input("Enter file path of Game Boy Camera save data file: ").strip().replace("\"", "")
				print("")
				if args.path == "":
					print("Canceled.")
					return
			
			pc = PocketCamera()
			if pc.LoadFile(args.path) != False:
				palettes = [ "grayscale", "dmg", "sgb", "cgb1", "cgb2", "cgb3" ]
				pc.SetPalette(palettes.index(args.gbcamera_palette))
				file = os.path.splitext(args.path)[0] + "/IMG_PC00.png"
				if os.path.isfile(os.path.dirname(file)):
					print("\n{:s}Can’t save pictures at location “{:s}”.{:s}\n".format(ANSI.RED, os.path.abspath(os.path.dirname(file)), ANSI.RESET))
					return
				if not os.path.isdir(os.path.dirname(file)):
					os.makedirs(os.path.dirname(file))
				for i in range(0, 31):
					file = os.path.splitext(args.path)[0] + "/IMG_PC{:02d}".format(i) + "." + args.gbcamera_outfile_format
					pc.ExportPicture(i, file)
				print("The pictures from “{:s}” were extracted to “{:s}”.".format(os.path.abspath(args.path), Util.formatPathOS(os.path.abspath(os.path.dirname(file)), end_sep=True) + "IMG_PC**.{:s}".format(args.gbcamera_outfile_format)))
			else:
				print("\n{:s}Couldn’t parse the save data file.{:s}\n".format(ANSI.RED, ANSI.RESET))
			return
		
		if args.mode is None:
			print("Select Cartridge Mode:\n 1) Game Boy or Game Boy Color\n 2) Game Boy Advance\n")
			answer = input("Enter number 1-2 [2]: ").lower().strip()
			print("")
			if answer == "1":
				args.mode = "dmg"
			elif answer == "2" or answer == "":
				args.mode = "agb"
			else:
				print("Canceled.")
				self.DisconnectDevice()
				return
			print("")
		
		if args.mode == "dmg":
			print("Cartridge Mode: Game Boy or Game Boy Color")
			self.CONN.SetMode("DMG")
		else:
			print("Cartridge Mode: Game Boy Advance")
			self.CONN.SetMode("AGB")
		time.sleep(0.2)

		header = self.CONN.ReadInfo()
		(bad_read, s_header, header) = self.ReadCartridge(header)
		if s_header == "":
			print("\n{:s}Couldn’t read cartridge header. Please try again.{:s}\n".format(ANSI.RED, ANSI.RESET))
			self.DisconnectDevice()
			return
		elif bad_read and not args.ignore_bad_header:
			print("\n{:s}Invalid data was detected which usually means that the cartridge couldn’t be read correctly. Please make sure you selected the correct mode and that the cartridge contacts are clean. This check can be disabled with the command line switch “--ignore-bad-header”.{:s}\n".format(ANSI.RED, ANSI.RESET))
			print("Cartridge Information:")
			print(s_header)
			self.DisconnectDevice()
			return
		
		print("\nCartridge Information:")
		print(s_header)

		if args.action == "backup-rom":
			self.BackupROM(args, header)
		
		elif args.action == "backup-save":
			self.BackupRestoreRAM(args, header)
		
		elif args.action == "restore-save":
			if args.path == "auto":
				args.path = input("Enter file path of save data file: ").strip().replace("\"", "")
				print("")
				if args.path == "":
					print("Canceled.")
					self.DisconnectDevice()
					return
			self.BackupRestoreRAM(args, header)
		
		elif args.action == "erase-save":
			self.BackupRestoreRAM(args, header)
		
		elif args.action == "debug-test-save":
   			self.BackupRestoreRAM(args, header)
		
		elif args.action == "flash-rom":
			if args.path == "auto":
				args.path = input("Enter file path of ROM file: ").strip().replace("\"", "")
				print("")
				if args.path == "":
					print("Canceled.")
					self.DisconnectDevice()
					return
			self.FlashROM(args, header)
		
		if args.action != "info":
			print("")
		
		self.DisconnectDevice()
		return 0
	
	def UpdateProgress(self, args):
		if args is None: return
		
		if "error" in args:
			print("{:s}{:s}{:s}".format(ANSI.RED, args["error"], ANSI.RESET))
			return
		
		pos = 0
		size = 0
		speed = 0
		elapsed = 0
		left = 0
		if "pos" in args: pos = args["pos"]
		if "size" in args: size = args["size"]
		if "speed" in args: speed = args["speed"]
		if "time_elapsed" in args: elapsed = args["time_elapsed"]
		if "time_left" in args: left = args["time_left"]
		
		if "action" in args:
			if args["action"] == "INITIALIZE":
				if args["method"] == "ROM_WRITE_VERIFY":
					print("\n\nThe newly written ROM data will now be checked for errors.\n")
			elif args["action"] == "ERASE":
				print("\033[KPlease wait while the flash chip is being erased... (Elapsed time: {:s})".format(Util.formatProgressTime(elapsed)), end="\r")
			elif args["action"] == "UNLOCK":
				print("\033[KPlease wait while the flash chip is being unlocked... (Elapsed time: {:s})".format(Util.formatProgressTime(elapsed)), end="\r")
			elif args["action"] == "SECTOR_ERASE":
				print("\033[KErasing flash sector at address 0x{:X}...".format(args["sector_pos"]), end="\r")
			elif args["action"] == "ABORTING":
				print("\nStopping...")
				pass
			elif args["action"] == "FINISHED":
				print("\n")
				self.FinishOperation()
			elif args["action"] == "ABORT":
				print("\nOperation stopped.\n")
				if "info_type" in args.keys() and "info_msg" in args.keys():
					if args["info_type"] == "msgbox_critical":
						print(ANSI.RED + args["info_msg"] + ANSI.RESET)
					elif args["info_type"] == "msgbox_information":
						print(args["info_msg"])
					elif args["info_type"] == "label":
						print(args["info_msg"])
				return
			elif args["action"] == "PROGRESS":
				# pv style progress status
				prog_str = "{:s}/{:s} {:s} [{:s}KB/s] [{:s}] {:s}% ETA {:s} ".format(Util.formatFileSize(size=pos).replace(" ", "").replace("Bytes", "B").replace("Byte", "B").rjust(8), Util.formatFileSize(size=size).replace(" ", "").replace("Bytes", "B"), Util.formatProgressTimeShort(elapsed), "{:.2f}".format(speed).rjust(6), "%PROG_BAR%", "{:d}".format(int(pos/size*100)).rjust(3), Util.formatProgressTimeShort(left))
				prog_width = shutil.get_terminal_size((80, 20))[0] - (len(prog_str) - 10)
				progress = min(1, max(0, pos/size))
				whole_width = math.floor(progress * prog_width)
				remainder_width = (progress * prog_width) % 1
				part_width = math.floor(remainder_width * 8)
				try:
					part_char = prog_bar_part_char[part_width]
					if (prog_width - whole_width - 1) < 0: part_char = ""
					prog_bar = "█" * whole_width + part_char + " " * (prog_width - whole_width - 1)
					print(prog_str.replace("%PROG_BAR%", prog_bar), end="\r")
				except UnicodeEncodeError:
					prog_bar = "#" * whole_width + " " * (prog_width - whole_width)
					print(prog_str.replace("%PROG_BAR%", prog_bar), end="\r", flush=True)
				except:
					pass
	
	def FinishOperation(self):
		if self.CONN.INFO["last_action"] == 4: # Flash ROM
			self.CONN.INFO["last_action"] = 0
			if "verified" in self.PROGRESS.PROGRESS and self.PROGRESS.PROGRESS["verified"] == True:
				print("{:s}The ROM was flashed and verified successfully!{:s}".format(ANSI.GREEN, ANSI.RESET))
			else:
				print("ROM flashing complete!")
		
		elif self.CONN.INFO["last_action"] == 1: # Backup ROM
			self.CONN.INFO["last_action"] = 0
			if self.CONN.GetMode() == "DMG":
				print("Checksum: 0x{:04X}".format(self.CONN.INFO["rom_checksum_calc"]))
				print("SHA-1:    {:s}\n".format(self.CONN.INFO["file_sha1"]))
				if self.CONN.INFO["rom_checksum"] == self.CONN.INFO["rom_checksum_calc"]:
					print("{:s}The ROM backup is complete and the checksum was verified successfully!{:s}".format(ANSI.GREEN, ANSI.RESET))
				elif "DMG-MMSA-JPN" in self.ARGS["argparsed"].flashcart_handler:
					print("The ROM backup is complete!")
				else:
					print("{:s}The ROM was dumped, but the checksum is not correct. This may indicate a bad dump, however this can be normal for some reproduction prototypes, patched games and intentional overdumps.{:s}".format(ANSI.YELLOW, ANSI.RESET))
			elif self.CONN.GetMode() == "AGB":
				print("CRC32: 0x{:08X}".format(self.CONN.INFO["rom_checksum_calc"]))
				print("SHA-1: {:s}\n".format(self.CONN.INFO["file_sha1"]))
				if Util.AGB_Global_CRC32 == self.CONN.INFO["rom_checksum_calc"]:
					print("{:s}The ROM backup is complete and the checksum was verified successfully!{:s}".format(ANSI.GREEN, ANSI.RESET))
				elif Util.AGB_Global_CRC32 == 0:
					print("The ROM backup is complete! As there is no known checksum for this ROM in the database, verification was skipped.")
				else:
					print("{:s}The ROM backup is complete, but the checksum doesn’t match the known database entry. This may indicate a bad dump, however this can be normal for some reproduction cartridges, prototypes, patched games and intentional overdumps.{:s}".format(ANSI.YELLOW, ANSI.RESET))
		
		elif self.CONN.INFO["last_action"] == 2: # Backup RAM
			self.CONN.INFO["last_action"] = 0
			if not "debug" in self.ARGS and self.CONN.INFO["transferred"] == 131072: # 128 KB
				with open(self.CONN.INFO["last_path"], "rb") as file: temp = file.read()
				if temp[0x1FFB1:0x1FFB6] == b'Magic':
					answer = input("Game Boy Camera save data was detected.\nWould you like to extract all pictures to “{:s}” now? [Y/n]: ".format(Util.formatPathOS(os.path.abspath(os.path.splitext(self.CONN.INFO["last_path"])[0]), end_sep=True) + "IMG_PC**.{:s}".format(self.ARGS["argparsed"].gbcamera_outfile_format))).strip().lower()
					if answer != "n":
						pc = PocketCamera()
						if pc.LoadFile(self.CONN.INFO["last_path"]) != False:
							palettes = [ "grayscale", "dmg", "sgb", "cgb1", "cgb2", "cgb3" ]
							pc.SetPalette(palettes.index(self.ARGS["argparsed"].gbcamera_palette))
							file = os.path.splitext(self.CONN.INFO["last_path"])[0] + "/IMG_PC00.png"
							if os.path.isfile(os.path.dirname(file)):
								print("Can’t save pictures at location “{:s}”.".format(os.path.abspath(os.path.dirname(file))))
								return
							if not os.path.isdir(os.path.dirname(file)):
								os.makedirs(os.path.dirname(file))
							for i in range(0, 31):
								file = os.path.splitext(self.CONN.INFO["last_path"])[0] + "/IMG_PC{:02d}".format(i) + "." + self.ARGS["argparsed"].gbcamera_outfile_format
								pc.ExportPicture(i, file)
							print("The pictures were extracted.")
					print("")
			
			print("The save data backup is complete!")
		
		elif self.CONN.INFO["last_action"] == 3: # Restore RAM
			self.CONN.INFO["last_action"] = 0
			if "save_erase" in self.CONN.INFO and self.CONN.INFO["save_erase"]:
				print("The save data was erased.")
				del(self.CONN.INFO["save_erase"])
			else:
				print("The save data was restored!")
		
		else:
			self.CONN.INFO["last_action"] = 0
	
	def FindDevices(self, connectToFirst=False):
		global hw_devices
		for hw_device in hw_devices:
			dev = hw_device.GbxDevice()
			ret = dev.Initialize(self.FLASHCARTS, max_baud=1700000)
			if ret is False:
				self.CONN = None
			elif isinstance(ret, list):
				if len(ret) > 0: print("\n")
				for i in range(0, len(ret)):
					status = ret[i][0]
					msg = re.sub('<[^<]+?>', '', ret[i][1])
					if status == 3:
						print("{:s}{:s}{:s}".format(ANSI.RED, msg.replace("\n\n", "\n"), ANSI.RESET))
						self.CONN = None
			
			if dev.IsConnected():
				self.DEVICE = (dev.GetFullNameExtended(), dev)
				dev.Close()
				break
		
		if self.DEVICE is None: return False
		return True
		
	def ConnectDevice(self):
		dev = self.DEVICE[1]
		port = dev.GetPort()
		ret = dev.Initialize(self.FLASHCARTS, port=port, max_baud=1700000)

		if ret is False:
			print("\n{:s}An error occured while trying to connect to the device.{:s}".format(ANSI.RED, ANSI.RESET))
			traceback.print_stack()
			self.CONN = None
			return False
		
		elif isinstance(ret, list):
			for i in range(0, len(ret)):
				status = ret[i][0]
				msg = re.sub('<[^<]+?>', '', ret[i][1])
				if status == 0:
					print("\n" + msg)
				elif status == 1:
					print("{:s}".format(msg))
				elif status == 2:
					print("{:s}{:s}{:s}".format(ANSI.YELLOW, msg, ANSI.RESET))
				elif status == 3:
					print("{:s}{:s}{:s}".format(ANSI.RED, msg, ANSI.RESET))
					self.CONN = None
					return False
		
		self.CONN = dev
		return True

	def DisconnectDevice(self):
		try:
			devname = self.CONN.GetFullNameExtended()
			self.CONN.Close()
			print("Disconnected from {:s}".format(devname))
		except:
			pass
		self.CONN = None
	
	def ReadCartridge(self, data):
		bad_read = False
		str = ""
		if self.CONN.GetMode() == "DMG":
			str += "Game Title/Code: {:s}\n".format(data["game_title"])
			str += "Super Game Boy:  "
			if data['sgb'] in Util.DMG_Header_SGB:
				str += "{:s}\n".format(Util.DMG_Header_SGB[data['sgb']])
			else:
				str += "Unknown (0x{:02X})\n".format(data['sgb'])
				bad_read = True
			str += "Game Boy Color:  "
			if data['cgb'] in Util.DMG_Header_CGB:
				str += "{:s}\n".format(Util.DMG_Header_CGB[data['cgb']])
			else:
				str += "Unknown (0x{:02X})\n".format(data['cgb'])
				bad_read = True
			if data["logo_correct"]:
				str += "Nintendo Logo:   OK\n"
			else:
				str += "Nintendo Logo:   {:s}Invalid{:s}\n".format(ANSI.RED, ANSI.RESET)
				bad_read = True
			if data['header_checksum_correct']:
				str += "Header Checksum: Valid (0x{:02X})\n".format(data['header_checksum'])
			else:
				str += "Header Checksum: {:s}Invalid (0x{:02X}){:s}\n".format(ANSI.RED, data['header_checksum'], ANSI.RESET)
				bad_read = True
			str += "ROM Checksum:    0x{:04X}\n".format(data['rom_checksum'])
			try:
				str += "ROM Size:        {:s}\n".format(Util.DMG_Header_ROM_Sizes[data['rom_size_raw']])
			except:
				str += "ROM Size:        {:s}Not detected{:s}\n".format(ANSI.RED, ANSI.RESET)
				bad_read = True
			
			try:
				if data['features_raw'] == 0x06: # MBC2
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[1])
				elif data['features_raw'] == 0x22 and data["game_title"] in ("KORO2 KIRBYKKKJ", "KIRBY TNT__KTNE"): # MBC7 Kirby
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[Util.DMG_Header_RAM_Sizes_Map.index(0x101)])
				elif data['features_raw'] == 0x22 and data["game_title"] in ("CMASTER____KCEJ"): # MBC7 Command Master
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[Util.DMG_Header_RAM_Sizes_Map.index(0x102)])
				elif data['features_raw'] == 0xFD: # TAMA5
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[Util.DMG_Header_RAM_Sizes_Map.index(0x103)])
				elif data['features_raw'] == 0x20: # MBC6
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[Util.DMG_Header_RAM_Sizes_Map.index(0x104)])
				else:
					str += "Save Type:       {:s}\n".format(Util.DMG_Header_RAM_Sizes[Util.DMG_Header_RAM_Sizes_Map.index(data['ram_size_raw'])])
			except:
				str += "Save Type:       Not detected\n"
			
			try:
				str += "Mapper Type:     {:s}\n".format(Util.DMG_Header_Mapper[data['features_raw']])
			except:
				str += "Mapper Type:     {:s}Not detected{:s}\n".format(ANSI.RED, ANSI.RESET)
				bad_read = True

			if data['logo_correct'] and not self.CONN.IsSupportedMbc(data["features_raw"]):
				print("{:s}\nWARNING: This cartridge uses a Memory Bank Controller that may not be completely supported yet. A future version of {:s} may add support for it.{:s}".format(ANSI.YELLOW, APPNAME, ANSI.RESET))
			if data['logo_correct'] and data['game_title'] == "NP M-MENU MENU" and self.ARGS["argparsed"].flashcart_handler == "autodetect":
				cart_types = self.CONN.GetSupportedCartridgesDMG()
				for i in range(0, len(cart_types[0])):
					if "DMG-MMSA-JPN" in cart_types[0][i]:
						self.ARGS["argparsed"].flashcart_handler = cart_types[0][i]

		elif self.CONN.GetMode() == "AGB":
			str += "Game Title:           {:s}\n".format(data["game_title"])
			str += "Game Code:            {:s}\n".format(data["game_code"])
			str += "Revision:             {:d}\n".format(data["version"])
			if data["logo_correct"]:
				str += "Nintendo Logo:        OK\n"
			else:
				str += "Nintendo Logo:        {:s}Invalid{:s}\n".format(ANSI.RED, ANSI.RESET)
				bad_read = True
			if data["96h_correct"]:
				str += "Cartridge Identifier: OK\n"
			else:
				str += "Cartridge Identifier: {:s}Invalid{:s}\n".format(ANSI.RED, ANSI.RESET)
				bad_read = True
			if data['header_checksum_correct']:
				str += "Header Checksum:      Valid (0x{:02X})\n".format(data['header_checksum'])
			else:
				str += "Header Checksum:      {:s}Invalid (0x{:02X}){:s}\n".format(ANSI.RED, data['header_checksum'], ANSI.RESET)
				bad_read = True
			
			str += "ROM Checksum:         "
			Util.AGB_Global_CRC32 = 0
			db_agb_entry = None
			if os.path.exists("{0:s}/db_AGB.json".format(self.CONFIG_PATH)):
				with open("{0:s}/db_AGB.json".format(self.CONFIG_PATH)) as f:
					db_agb = f.read()
					db_agb = json.loads(db_agb)
					if data["header_sha1"] in db_agb.keys():
						db_agb_entry = db_agb[data["header_sha1"]]
					else:
						str += "Not in database\n"
			else:
				str += "FAIL: Database for Game Boy Advance titles not found in {:s}/db_AGB.json\n".format(self.CONFIG_PATH)
			
			if db_agb_entry != None:
				if data["rom_size_calc"] < 0x400000:
					str += "In database (0x{:06X})\n".format(db_agb_entry['rc'])
					Util.AGB_Global_CRC32 = db_agb_entry['rc']
				str += "ROM Size:             {:d} MB\n".format(int(db_agb_entry['rs']/1024/1024))
				data['rom_size'] = db_agb_entry['rs']
			
			elif data["rom_size"] != 0:
				if not data["rom_size"] in Util.AGB_Header_ROM_Sizes_Map:
					data["rom_size"] = 0x2000000
				str += "ROM Size:             {:d} MB\n".format(int(data["rom_size"]/1024/1024))
			else:
				str += "ROM Size:             Not detected\n"
				bad_read = True
			
			stok = False
			if data["save_type"] == None:
				if db_agb_entry != None:
					if db_agb_entry['st'] < len(Util.AGB_Header_Save_Types):
						stok = True
						str += "Save Type:            {:s}\n".format(Util.AGB_Header_Save_Types[db_agb_entry['st']])
						data["save_type"] = db_agb_entry['st']
				if data["dacs_8m"] is True:
						stok = True
						str += "Save Type:            {:s}\n".format(Util.AGB_Header_Save_Types[8])
						data["save_type"] = 8
			
			if stok is False:
				str += "Save Type:            Not detected\n"
			
			if data['logo_correct'] and isinstance(db_agb_entry, dict) and "rs" in db_agb_entry and db_agb_entry['rs'] == 0x4000000 and not self.CONN.IsSupported3dMemory():
				print("{:s}\nWARNING: This cartridge uses a Memory Bank Controller that may not be completely supported yet. A future version of the {:s} device firmware may add support for it.{:s}".format(ANSI.YELLOW, self.CONN.GetFullName(), ANSI.RESET))
		
			if "has_rtc" in data and data["has_rtc"] is not True and "no_rtc_reason" in data:
				if data["no_rtc_reason"] == 1:
					print("{:s}NOTE: It seems that this cartridge’s Real Time Clock battery may no longer be functional and needs to be replaced.{:s}".format(ANSI.YELLOW, ANSI.RESET))

		return (bad_read, str, data)
	
	def CartridgeTypeAutoDetect(self, limitVoltage=True, knownCartCFI=False):
		cart_type = 0
		cart_text = ""
		
		print("Now attempting to auto-detect the flash cartridge type...")
		if self.CONN.CheckROMStable() is False:
			print("{:s}Unstable ROM reading detected. Please make sure you selected the correct mode and that the cartridge contacts are clean.{:s}".format(ANSI.RED, ANSI.RESET))
			return -1
		
		if self.CONN.GetMode() in self.FLASHCARTS and len(self.FLASHCARTS[self.CONN.GetMode()]) == 0:
			print("{:s}No flash cartridge type configuration files found. Try to restart the application with the “--reset” command line switch to reset the configuration.{:s}".format(ANSI.RED, ANSI.RESET))
			return -2
		
		detected = self.CONN.AutoDetectFlash(limitVoltage)
		if len(detected) == 0:
			print("\n{:s}No pre-configured flash cartridge type was detected.{:s} You can still manually specify one using the “--flashcart-handler” command line switch -- look for similar PCB text and/or flash chip markings. However, chances are this cartridge is currently not supported for flashing with {:s}.\n".format(ANSI.YELLOW, ANSI.RESET, APPNAME))
			
			(flash_id, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage)
			if cfi_s == "":
				print("Flash chip query result:\n" + flash_id + "\nThere was no Common Flash Interface (CFI) response from the cartridge. Please clean the cartridge contacts and make sure that the cartridge is seated correctly. If a flash chip exists on the cartridge PCB, it may be too old or require unique unlocking and handling.")
			else:
				print("Flash chip query result:\n" + flash_id + "\n" + str(cfi_s))
				with open(self.CONFIG_PATH + "/cfi.bin", "wb") as f: f.write(cfi['raw'])
		
		else:
			cart_type = detected[0]
			size_undetected = False
			sectors_undetected = False
			if self.CONN.GetMode() == "DMG": cart_types = self.CONN.GetSupportedCartridgesDMG()
			elif self.CONN.GetMode() == "AGB": cart_types = self.CONN.GetSupportedCartridgesAGB()
			size = cart_types[1][detected[0]]["flash_size"]
			if "manual_select" in cart_types[1][detected[0]]:
				manual_select = cart_types[1][detected[0]]["manual_select"]
			else:
				manual_select = False
			if "sector_size" in cart_types[1][detected[0]]:
				sectors = cart_types[1][detected[0]]["sector_size"]
			else:
				sectors = []
			
			for i in range(0, len(detected)):
				if size != cart_types[1][detected[i]]["flash_size"]:
					size_undetected = True
				if "sector_size_from_cfi" not in cart_types[1][detected[i]] and "sector_size" in cart_types[1][detected[i]] and sectors != cart_types[1][detected[i]]["sector_size"]:
					sectors_undetected = True
				cart_text += "- " + cart_types[0][detected[i]] + "\n"
			
			if manual_select:
				msg_text = "Your cartridge responds to flash commands used by:\n" + cart_text + "\nHowever, there are differences between these cartridge types that cannot be detected automatically, so please select the correct cartridge type manually."
				cart_type = 0
			else:
				if size_undetected:
					(_, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage=limitVoltage, cart_type=cart_types[1][cart_type])
					if isinstance(cfi, dict) and 'device_size' in cfi:
						for i in range(0, len(detected)):
							if cfi['device_size'] == cart_types[1][detected[i]]["flash_size"]:
								cart_type = detected[i]
								size_undetected = False
								break
				
				if len(detected) == 1:
					msg_text = "The following flash cartridge type was detected:\n" + cart_text + "\nThe supported ROM size is up to {:d} MB.".format(int(cart_types[1][cart_type]['flash_size'] / 1024 / 1024))
				else:
					if size_undetected is True:
						msg_text = "Your cartridge responds to flash commands used by:\n" + cart_text + "\nHowever, you may need to manually adjust the ROM size selection.\n\nIMPORTANT: While these cartridges share the same electronic signature, their supported ROM size can differ. As the size can not be detected automatically at this time, please select it manually."
					else:
						msg_text = "Your cartridge responds to flash commands used by:\n" + cart_text + "\nThe supported ROM size is up to {:d} MB.".format(int(cart_types[1][cart_type]['flash_size'] / 1024 / 1024))
				
				if sectors_undetected and "sector_size_from_cfi" not in cart_types[1][cart_type]:
					msg_text = msg_text + "\n\n{:s}IMPORTANT:{:s} While these share most of their attributes, some of them can not be automatically detected. If you encounter any errors while writing a ROM, please manually select the correct type based on the flash chip markings of your cartridge. Unchecking the “Prefer sector erase mode” config option can also help.".format(ANSI.RED, ANSI.RESET)
			
			print(msg_text)
			if knownCartCFI:
				(flash_id, cfi_s, cfi) = self.CONN.CheckFlashChip(limitVoltage=limitVoltage, cart_type=cart_types[1][cart_type])
				if cfi_s == "":
					print("\nFlash chip query result:\n" + flash_id + "\nThere was no Common Flash Interface (CFI) response from the cartridge. If a flash chip exists on the cartridge PCB, it may be too old or require unique unlocking and handling.")
				else:
					print("\nFlash chip query result:\n" + flash_id + "\n" + str(cfi_s))
					with open(self.CONFIG_PATH + "/cfi.bin", "wb") as f: f.write(cfi['raw'])
		
		return cart_type
	
	def BackupROM(self, args, header):
		mbc = 1
		rom_banks = 1
		fast_read_mode = args.fast_read_mode is True

		if self.CONN.GetMode() == "DMG":
			if args.dmg_mbc == "auto":
				try:
					mbc = header["features_raw"]
					if mbc == 0: mbc = 5
				except:
					print("{:s}Couldn’t determine MBC type, will try to use MBC5. It can also be manually set with the “--dmg-mbc” command line switch.{:s}".format(ANSI.YELLOW, ANSI.RESET))
					mbc = 5
			else:
				mbc = int(args.dmg_mbc)
				if mbc == 2: mbc = 0x06
				elif mbc == 3: mbc = 0x13
				elif mbc == 5: mbc = 0x19
				elif mbc == 6: mbc = 0x20
				elif mbc == 7: mbc = 0x22
			
			if args.dmg_romsize == "auto":
				try:
					rom_banks = Util.DMG_Header_ROM_Sizes_Flasher_Map[header["rom_size_raw"]]
				except:
					print("{:s}Couldn’t determine ROM size, will use 8 MB. It can also be manually set with the “--dmg-romsize” command line switch.{:s}".format(ANSI.YELLOW, ANSI.RESET))
					rom_banks = 512
			else:
				sizes = [ "auto", "32kb", "64kb", "128kb", "256kb", "512kb", "1mb", "2mb", "4mb", "8mb" ]
				rom_banks = Util.DMG_Header_ROM_Sizes_Flasher_Map[sizes.index(args.dmg_romsize) - 1]
			rom_size = rom_banks * 0x4000
			
			path = header["game_title"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			if self.CONN.INFO["cgb"] == 0xC0 or self.CONN.INFO["cgb"] == 0x80:
				path = path + ".gbc"
			elif self.CONN.INFO["sgb"] == 0x03:
				path = path + ".sgb"
			else:
				path = path + ".gb"
		
		elif self.CONN.GetMode() == "AGB":
			if args.agb_romsize == "auto":
				rom_size = header["rom_size"]
			else:
				sizes = [ "auto", "4mb", "8mb", "16mb", "32mb", "64mb" ]
				rom_size = Util.AGB_Header_ROM_Sizes_Map[sizes.index(args.agb_romsize) - 1]

			path = header["game_title"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = header["game_code"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path)
			path = path + ".gba"
		
		if args.path != "auto":
			if os.path.isdir(args.path):
				path = args.path + "/" + path
			else:
				path = args.path
		
		if (path == ""): return
		if not args.overwrite and os.path.exists(os.path.abspath(path)):
			answer = input("The target file “{:s}” already exists.\nDo you want to overwrite it? [y/N]: ".format(os.path.abspath(path))).strip().lower()
			print("")
			if answer != "y":
				print("Canceled.")
				return
		
		
		try:
			f = open(path, "ab+")
			f.close()
		except (PermissionError, FileNotFoundError):
			print("{:s}Couldn’t access “{:s}”.{:s}".format(ANSI.RED, path, ANSI.RESET))
			return
		
		if fast_read_mode: print("Fast Read Mode enabled.")
		s_mbc = ""
		if self.CONN.GetMode() == "DMG": s_mbc = " using Mapper Type 0x{:X}".format(mbc)
		if self.CONN.GetMode() == "DMG":
			print("The ROM will now be read{:s} and saved to “{:s}”.".format(s_mbc, os.path.abspath(path)))
		else:
			print("The ROM will now be read and saved to “{:s}”.".format(os.path.abspath(path)))
		
		print("")
		
		cart_type = 0
		if args.flashcart_handler != "autodetect": 
			if self.CONN.GetMode() == "DMG":
				carts = self.CONN.GetSupportedCartridgesDMG()[1]
			elif self.CONN.GetMode() == "AGB":
				carts = self.CONN.GetSupportedCartridgesAGB()[1]
			cart_type = 0
			for i in range(0, len(carts)):
				if not "names" in carts[i]: continue
				if carts[i]["type"] != self.CONN.GetMode(): continue
				if args.flashcart_handler in carts[i]["names"]:
					print("Selected flash cartridge type: {:s}".format(args.flashcart_handler))
					rom_banks = int(carts[i]["flash_size"] / 0x4000)
					rom_size = carts[i]["flash_size"]
					cart_type = i
					break

		self.CONN._TransferData(args={ 'mode':1, 'path':path, 'mbc':mbc, 'rom_banks':rom_banks, 'agb_rom_size':rom_size, 'start_addr':0, 'fast_read_mode':fast_read_mode, 'cart_type':cart_type }, signal=self.PROGRESS.SetProgress)
	
	def FlashROM(self, args, header):
		path = ""
		mode = self.CONN.GetMode()
		if mode == "DMG":
			carts = self.CONN.GetSupportedCartridgesDMG()[1]
		elif mode == "AGB":
			carts = self.CONN.GetSupportedCartridgesAGB()[1]
		else:
			return
		
		cart_type = 0
		for i in range(0, len(carts)):
			if not "names" in carts[i]: continue
			if carts[i]["type"] != mode: continue
			if args.flashcart_handler in carts[i]["names"]:
				print("Selected flash cartridge type: {:s}".format(args.flashcart_handler))
				cart_type = i
				break
		
		if cart_type <= 0 and args.flashcart_handler == "autodetect":
			if args.force_5v is True:
				cart_type = self.CartridgeTypeAutoDetect(limitVoltage=False)
			else:
				cart_type = self.CartridgeTypeAutoDetect()
			if (cart_type == 1): cart_type = 0
			if cart_type == 0:
				msg_5v = ""
				if mode == "DMG": msg_5v = "If your flash cartridge requires 5V to work, you can use the “--force-5v” command line switch, however please note that 5V can be unsafe for some flash chips."
				print("\n{:s}Auto-detection failed. Please use the “--flashcart-handler” command line switch to select the flash cartridge type manually.\n{:s}{:s}{:s}".format(ANSI.RED, ANSI.YELLOW, msg_5v, ANSI.RESET))
				return
			elif cart_type < 0: return
		elif cart_type == 0 and args.flashcart_handler != "autodetect":
			print("{:s}Couldn’t find the selected flash cartridge type “{:s}”. Please make sure the correct cartridge mode is selected and copy the exact name from the configuration files located in {:s}.{:s}".format(ANSI.RED, args.flashcart_handler, self.CONFIG_PATH, ANSI.RESET))
			return
		
		if args.path == "auto":
			print("{:s}No ROM file for flashing was selected.{:s}".format(ANSI.RED, ANSI.RESET))
			return
		else:
			path = args.path
		
		try:
			if os.path.getsize(path) > 0x10000000: # reject too large files to avoid exploding RAM
				print("{:s}ROM files bigger than 256 MB are not supported.{:s}".format(ANSI.RED, ANSI.RESET))
				return
			elif os.path.getsize(path) < 0x400:
				print("{:s}ROM files smaller than 1 KB are not supported.{:s}".format(ANSI.RED, ANSI.RESET))
				return
			with open(path, "rb") as file: buffer = file.read()
		except (PermissionError, FileNotFoundError):
			print("{:s}Couldn’t access file path “{:s}”.{:s}".format(ANSI.RED, args.path, ANSI.RESET))
			return
		
		rom_size = len(buffer)
		if "flash_size" in carts[cart_type]:
			if rom_size > carts[cart_type]['flash_size']:
				msg = "The selected flash cartridge type seems to support ROMs that are up to {:.2f} MB in size, but the file you selected is {:.2f} MB.".format(carts[cart_type]['flash_size'] / 1024 / 1024, os.path.getsize(path)/1024/1024)
				msg += " It’s possible that it’s too large which may cause the flashing to fail."
				print("{:s}{:s}{:s}".format(ANSI.YELLOW, msg, ANSI.RESET))
				answer = input("Do you want to continue? [y/N]: ").strip().lower()
				print("")
				if answer != "y":
					print("Canceled.")
					return
		
		override_voltage = False
		if args.force_5v is True:
			override_voltage = 5
		elif 'voltage_variants' in carts[cart_type] and carts[cart_type]['voltage'] == 3.3:
			print("The selected flash cartridge type usually flashes fine with 3.3V, however sometimes it may require 5V. You can use the “--force-5v” command line switch if necessary. Please note that 5V can be unsafe for some flash chips.")
		
		reverse_sectors = False
		if args.reversed_sectors is True:
			reverse_sectors = True
			print("Will be writing to the cartridge with reversed flash sectors.")
		elif 'sector_reversal' in carts[cart_type]:
			print("The selected flash cartridge type is reported to sometimes have reversed sectors. You can use the “--reversed-sectors” command line switch if the cartridge is not working after flashing.")
		
		prefer_chip_erase = args.prefer_chip_erase is True
		if not prefer_chip_erase and 'chip_erase' in carts[cart_type]['commands'] and 'sector_erase' in carts[cart_type]['commands']:
			print("This flash cartridge supports both Sector Erase and Full Chip Erase methods. You can use the “--prefer-chip-erase” command line switch if necessary.")
		
		fast_read_mode = args.fast_read_mode is True
		verify_flash = args.no_verify_flash is False
		
		try:
			if self.CONN.GetMode() == "DMG":
				hdr = RomFileDMG(path).GetHeader()
			elif self.CONN.GetMode() == "AGB":
				hdr = RomFileAGB(path).GetHeader()
			if not hdr["logo_correct"]:
				print("{:s}WARNING: The ROM file you selected will not boot on actual hardware due to invalid logo data.{:s}".format(ANSI.YELLOW, ANSI.RESET))
			if not hdr["header_checksum_correct"]:
				print("{:s}WARNING: The ROM file you selected will not boot on actual hardware due to an invalid header checksum (expected 0x{:02X} instead of 0x{:02X}).{:s}".format(ANSI.YELLOW, hdr["header_checksum_calc"], hdr["header_checksum"], ANSI.RESET))
		
		except:
			print("{:s}The selected file could not be read.{:s}".format(ANSI.RED, ANSI.RESET))
			return
		
		print("")
		if fast_read_mode: print("Fast Read Mode enabled for flash verification.")
		v = carts[cart_type]["voltage"]
		if override_voltage: v = override_voltage
		print("The following ROM file will now be written to the flash cartridge at {:s}V:\n{:s}".format(str(v), os.path.abspath(path)))
		
		print("")
		self.CONN._TransferData(args={ 'mode':4, 'path':path, 'cart_type':cart_type, 'override_voltage':override_voltage, 'start_addr':0, 'buffer':buffer, 'prefer_chip_erase':prefer_chip_erase, 'reverse_sectors':reverse_sectors, 'fast_read_mode':fast_read_mode, 'verify_flash':verify_flash }, signal=self.PROGRESS.SetProgress)
		buffer = None
	
	def BackupRestoreRAM(self, args, header):
		add_date_time = args.save_filename_add_datetime is True
		rtc = args.store_rtc is True
		
		if self.CONN.GetMode() == "DMG":
			if args.dmg_mbc == "auto":
				try:
					mbc = header["features_raw"]
					if mbc == 0: mbc = 5
				except:
					print("{:s}Couldn’t determine MBC type, will try to use MBC5. It can also be manually set with the “--dmg-mbc” command line switch.{:s}".format(ANSI.YELLOW, ANSI.RESET))
					mbc = 5
			else:
				mbc = int(args.dmg_mbc)
				if mbc == 2: mbc = 0x06
				elif mbc == 3: mbc = 0x13
				elif mbc == 5: mbc = 0x19
				elif mbc == 6: mbc = 0x20
				elif mbc == 7: mbc = 0x22

			if args.dmg_savesize == "auto":
				try:
					if header['features_raw'] == 0x06: # MBC2
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[1]
					elif header['features_raw'] == 0x22 and header["game_title"] in ("KORO2 KIRBYKKKJ", "KIRBY TNT_KTNE"): # MBC7 Kirby
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(0x101)]
					elif header['features_raw'] == 0x22 and header["game_title"] in ("CMASTER_KCEJ"): # MBC7 Command Master
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(0x102)]
					elif header['features_raw'] == 0xFD: # TAMA5
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(0x103)]
					elif header['features_raw'] == 0x20: # TAMA5
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(0x104)]
					else:
						save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[Util.DMG_Header_RAM_Sizes_Map.index(header['ram_size_raw'])]
				except:
					save_type = 0x20000
			else:
				sizes = [ "auto", "4k", "16k", "64k", "256k", "512k", "1m", "eeprom2k", "eeprom4k", "tama5" ]
				save_type = Util.DMG_Header_RAM_Sizes_Flasher_Map[sizes.index(args.dmg_savesize)]

			path = header["game_title"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			
			if save_type == 0:
				print("{:s}Unable to auto-detect the save size. Please use the “--dmg-savesize” command line switch to manually select it.{:s}".format(ANSI.RED, ANSI.RESET))
				return
		
		elif self.CONN.GetMode() == "AGB":
			if args.agb_savetype == "auto":
				save_type = header["save_type"]
			else:
				sizes = [ "auto", "eeprom4k", "eeprom64k", "sram256k", "sram512k", "sram1m", "flash512k", "flash1m", "dacs8m" ]
				save_type = sizes.index(args.agb_savetype)
			
			path = header["game_title"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = header["game_code"].strip().encode('ascii', 'ignore').decode('ascii')
			if path == "": path = "ROM"
			
			mbc = 0
			if save_type == 0 or save_type == None:
				print("{:s}Unable to auto-detect the save type. Please use the “--agb-savetype” command line switch to manually select it.{:s}".format(ANSI.RED, ANSI.RESET))
				return
		
		else:
			return
		
		if add_date_time:
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path) + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".sav"
		else:
			path = re.sub(r"[<>:\"/\\|\?\*]", "_", path) + ".sav"
		
		if args.path != "auto":
			if os.path.isdir(args.path):
				path = args.path + "/" + path
			else:
				path = args.path
		
		if (path == ""): return
		
		s_mbc = ""
		if self.CONN.GetMode() == "DMG": s_mbc = " using Mapper Type 0x{:X}".format(mbc)
		if args.action == "backup-save":
			if not args.overwrite and os.path.exists(os.path.abspath(path)):
				answer = input("The target file “{:s}” already exists.\nDo you want to overwrite it? [y/N]: ".format(os.path.abspath(path))).strip().lower()
				print("")
				if answer != "y":
					print("Canceled.")
					return
			print("The cartridge save data will now be read{:s} and saved to the following file:\n{:s}".format(s_mbc, os.path.abspath(path)))
		elif args.action == "restore-save":
			if not args.overwrite:
				answer = input("Restoring save data to the cartridge will erase the previous save.\nDo you want to overwrite it? [y/N]: ").strip().lower()
				if answer != "y":
					print("Canceled.")
					return
			print("The following save data file will now be written to the cartridge{:s}:\n{:s}".format(s_mbc, os.path.abspath(path)))
		elif args.action == "erase-save":
			if not args.overwrite:
				answer = input("Do you really want to erase the save data from the cartridge? [y/N]: ").strip().lower()
				if answer != "y":
					print("Canceled.")
					return
			print("The cartridge save data will now be erased from the cartridge{:s}.".format(s_mbc))
		elif args.action == "debug-test-save":
			print("The cartridge save data size will now be examined{:s}.\nNote: This is for debug use only.\n".format(s_mbc))
		
		if self.CONN.GetMode() == "AGB":
			print("Using Save Type “{:s}”.".format(Util.AGB_Header_Save_Types[save_type]))
		elif self.CONN.GetMode() == "DMG":
			#if rtc and header["features_raw"] in (0x10, 0xFD, 0xFE): # RTC of MBC3, TAMA5, HuC-3
			if rtc and header["features_raw"] in (0x10, 0xFE): # RTC of MBC3, HuC-3
				print("Real Time Clock register values will also be written if applicable/possible.")

		try:
			if args.action == "backup-save":
				f = open(path, "ab+")
				f.close()
			elif args.action == "restore-save":
				f = open(path, "rb+")
				f.close()
		except (PermissionError, FileNotFoundError):
			print("{:s}Couldn’t access “{:s}”.{:s}".format(ANSI.RED, path, ANSI.RESET))
			return
		
		print("")
		if args.action == "backup-save":
			self.CONN._TransferData(args={ 'mode':2, 'path':path, 'mbc':mbc, 'save_type':save_type, 'rtc':rtc }, signal=self.PROGRESS.SetProgress)
		elif args.action == "restore-save":
			self.CONN._TransferData(args={ 'mode':3, 'path':path, 'mbc':mbc, 'save_type':save_type, 'erase':False, 'rtc':rtc }, signal=self.PROGRESS.SetProgress)
		elif args.action == "erase-save":
			self.CONN._TransferData(args={ 'mode':3, 'path':path, 'mbc':mbc, 'save_type':save_type, 'erase':True, 'rtc':rtc }, signal=self.PROGRESS.SetProgress)
		elif args.action == "debug-test-save": # debug
			self.ARGS["debug"] = True
			print("Making a backup of the original save data.")
			ret = self.CONN._TransferData(args={ 'mode':2, 'path':self.CONFIG_PATH + "/test1.bin", 'mbc':mbc, 'save_type':save_type }, signal=self.PROGRESS.SetProgress)
			if ret is False: return False
			time.sleep(0.1)
			print("Writing random data.")
			test2 = bytearray(os.urandom(os.path.getsize(self.CONFIG_PATH + "/test1.bin")))
			with open(self.CONFIG_PATH + "/test2.bin", "wb") as f: f.write(test2)
			self.CONN._TransferData(args={ 'mode':3, 'path':self.CONFIG_PATH + "/test2.bin", 'mbc':mbc, 'save_type':save_type, 'erase':False }, signal=self.PROGRESS.SetProgress)
			time.sleep(0.1)
			print("Reading back and comparing data.")
			self.CONN._TransferData(args={ 'mode':2, 'path':self.CONFIG_PATH + "/test3.bin", 'mbc':mbc, 'save_type':save_type }, signal=self.PROGRESS.SetProgress)
			time.sleep(0.1)
			with open(self.CONFIG_PATH + "/test3.bin", "rb") as f: test3 = bytearray(f.read())
			print("Restoring original save data.")
			self.CONN._TransferData(args={ 'mode':3, 'path':self.CONFIG_PATH + "/test1.bin", 'mbc':mbc, 'save_type':save_type, 'erase':False }, signal=self.PROGRESS.SetProgress)
			time.sleep(0.1)
			
			if mbc == 6:
				for i in range(0, len(test2)):
					test2[i] &= 0x0F
					test3[i] &= 0x0F
			
			found_offset = test2.find(test3[0:512])
			if found_offset < 0:
				if self.CONN.GetMode() == "AGB":
					print("\n{:s}It was not possible to save any data to the cartridge using save type “{:s}”.{:s}".format(ANSI.RED, Util.AGB_Header_Save_Types[save_type], ANSI.RESET))
				else:
					print("\n{:s}It was not possible to save any data to the cartridge.{:s}".format(ANSI.RED, ANSI.RESET))
			else:
				if found_offset == 0 and test2 != test3: # Pokémon Crystal JPN
					found_length = 0
					for i in range(0, len(test2)):
						if test2[i] != test3[i]: break
						found_length += 1
				else:
					found_length = len(test2) - found_offset
				
				if self.CONN.GetMode() == "DMG":
					print("\nDone! The writable save data size is {:s} out of {:s} checked.".format(Util.formatFileSize(found_length), Util.formatFileSize(save_type)))
				elif self.CONN.GetMode() == "AGB":
					print("\nDone! The writable save data size using save type “{:s}” is {:s}.".format(Util.AGB_Header_Save_Types[save_type], Util.formatFileSize(found_length)))
			
			try:
				(_, _, cfi) = self.CONN.CheckFlashChip(limitVoltage=False)
				if len(cfi["raw"]) > 0:
					with open(self.CONFIG_PATH + "/cfi.bin", "wb") as f: f.write(cfi["raw"])
					print("CFI data was extracted to “cfi.bin”.")
			except:
				pass

			#input("\nPress ENTER to erase the temporary files.")
			os.unlink(self.CONFIG_PATH + "/test1.bin")
			os.unlink(self.CONFIG_PATH + "/test2.bin")
			os.unlink(self.CONFIG_PATH + "/test3.bin")
