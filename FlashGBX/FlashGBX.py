# -*- coding: utf-8 -*-
# ＵＴＦ－８
import sys, os, glob, re, json, zlib, argparse, zipfile, traceback, platform, datetime
from . import Util

def ReadConfigFiles(args):
	reset = args['argparsed'].reset
	settings = Util.IniSettings(ini_file=args["config_path"] + "/settings.ini")
	config_version = settings.value("ConfigVersion")
	if not os.path.exists(args["config_path"]): os.makedirs(args["config_path"])
	fc_files = glob.glob("{0:s}/fc_*.txt".format(args["config_path"]))
	if config_version is not None and len(fc_files) == 0:
		print("No flash cartridge type configuration files found in {:s}. Resetting configuration...".format(args["config_path"]))
		settings.clear()
		os.rename(args["config_path"] + "/settings.ini", args["config_path"] + "/settings.ini_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".bak")
		config_version = False # extracts the config.zip again
	elif reset:
		settings.clear()
		print("All configuration has been reset.")
	
	settings.setValue("ConfigVersion", Util.VERSION)
	return (config_version, fc_files)

def LoadConfig(args):
	app_path = args['app_path']
	config_path = args['config_path']
	ret = []
	flashcarts = { "DMG":{}, "AGB":{} }
	
	# Settings and Config
	(config_version, fc_files) = ReadConfigFiles(args=args)
	if config_version != Util.VERSION:
		# Rename old files that have since been replaced/renamed/merged
		deprecated_files = [ "fc_AGB_M36L0R705.txt", "fc_AGB_TEST.txt", "fc_DMG_TEST.txt", "fc_AGB_Nintendo_E201850.txt", "fc_AGB_Nintendo_E201868.txt", "config.ini", "fc_DMG_MX29LV320ABTC.txt" ]
		for file in deprecated_files:
			if os.path.exists(config_path + "/" + file):
				os.rename(config_path + "/" + file, config_path + "/" + file + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".bak")
		
		rf_list = ""
		if os.path.exists(app_path + "/res/config.zip"):
			with zipfile.ZipFile(app_path + "/res/config.zip") as zip:
				for zfile in zip.namelist():
					if os.path.exists(config_path + "/" + zfile):
						zfile_crc = zip.getinfo(zfile).CRC
						with open(config_path + "/" + zfile, "rb") as ofile: buffer = ofile.read()
						ofile_crc = zlib.crc32(buffer) & 0xFFFFFFFF
						if zfile_crc == ofile_crc: continue
						os.rename(config_path + "/" + zfile, config_path + "/" + zfile + "_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".bak")
						rf_list += zfile + "\n"
					zip.extract(zfile, config_path + "/")
			
			if rf_list != "":
				ret.append([1, "The application was recently updated and some flashcart handler files have been updated as well. You will find backup copies of them in your configuration directory.\n\nUpdated files:\n" + rf_list[:-1]])
			fc_files = glob.glob("{0:s}/fc_*.txt".format(config_path))
		else:
			ret.append([2, "{:s} not found. This is required to load new flash cartridge type configurations after updating.\n".format(app_path + "/res/config.zip")])
	
	# Read flash cart types
	for file in fc_files:
		with open(file, encoding='utf-8') as f:
			data = f.read()
			specs_int = re.sub("(0x[0-9A-F]+)", lambda m: str(int(m.group(1), 16)), data) # hex numbers to int numbers, otherwise not valid json
			try:
				specs = json.loads(specs_int)
			except:
				ret.append([2, "The flashchip handler file “{:s}” could not be parsed and needs to be fixed before it can be used.".format(os.path.basename(file))])
				continue
			for name in specs["names"]:
				if not specs["type"] in flashcarts: continue # only DMG and AGB are supported right now
				flashcarts[specs["type"]][name] = specs
	
	return { "flashcarts":flashcarts, "config_ret":ret }

class ArgParseCustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter): pass
def main(portableMode=False):
	if platform.system() == "Windows": os.system("color")
	os.environ['QT_MAC_WANTS_LAYER'] = '1'
	
	print("{:s} {:s} by Lesserkuma".format(Util.APPNAME, Util.VERSION))
	print("\nDISCLAIMER: This software is provided as-is and the developer is not responsible for any damage that is caused by the use of it. Use at your own risk!")
	print("\nFor troubleshooting please visit https://github.com/lesserkuma/FlashGBX\n")
	
	if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
		app_path = os.path.dirname(sys.executable)
	else:
		app_path = os.path.dirname(os.path.abspath(__file__))
	
	try:
		from . import FlashGBX_GUI
		from PySide2 import QtCore
		cp = { "subdir":app_path + "/config", "appdata":QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppConfigLocation) }
	except:
		cp = { "subdir":app_path + "/config" }
	
	if portableMode:
		cfgdir_default = "subdir"
	else:
		cfgdir_default = "appdata"
	
	examples = "\nexamples:\n" + \
	"  Backup the ROM of a Game Boy Advance cartridge:\n\t{:s} --mode agb --action backup-rom\n\n".format(sys.argv[0]) + \
	"  Backup Save Data from a Game Boy cartridge:\n\t{:s} --mode dmg --action backup-save\n\n".format(sys.argv[0]) + \
	"  Write a Game Boy Advance ROM relying on auto-detecting the flash cartridge:\n\t{:s} --mode agb --action flash-rom ROM.gba\n\n".format(sys.argv[0]) + \
	"  Extract Game Boy Camera pictures as .png files from a save data file:\n\t{:s} --mode dmg --action gbcamera-extract --gbcamera-outfile-format png --path GAMEBOYCAMERA.sav\n\n".format(sys.argv[0])

	parser = argparse.ArgumentParser(formatter_class=ArgParseCustomFormatter, epilog=examples)
	try:
		parser._action_groups[1].title = "general arguments"
	except:
		pass
	parser.add_argument("--cli", help="force command line interface mode", action="store_true")
	parser.add_argument("--reset", help="clears all settings such as last used directory information", action="store_true")
	parser.add_argument("--debug", help="enable debug messages used for development", action="store_true")
	
	parser.add_argument_group('')
	ap_config = parser.add_argument_group('configuration arguments')
	if "appdata" in cp: ap_config.add_argument("--cfgdir", choices=["appdata", "subdir"], type=str.lower, default=cfgdir_default, help="sets the config directory to either the OS-provided local app config directory (" + cp['appdata'] + "), or a subdirectory of this application (" + cp['subdir'].replace("\\", "/") + ")")

	ap_cli1 = parser.add_argument_group('main command line interface arguments')
	ap_cli1.add_argument("--mode", choices=["dmg", "agb"], type=str.lower, default=None, help="set cartridge mode to \"dmg\" (Game Boy) or \"agb\" (Game Boy Advance)")
	ap_cli1.add_argument("--action", choices=["info", "backup-rom", "flash-rom", "backup-save", "restore-save", "erase-save", "gbcamera-extract", "debug-probe-save"], type=str.lower, default=None, help="select program action")
	ap_cli1.add_argument("--overwrite", action="store_true", help="overwrite without asking if target file already exists")
	ap_cli1.add_argument("path", nargs="?", default="auto", help="target or source file path (optional when reading, required when writing)")
	
	ap_cli2 = parser.add_argument_group('optional command line interface arguments')
	ap_cli2.add_argument("--dmg-romsize", choices=["auto", "32kb", "64kb", "128kb", "256kb", "512kb", "1mb", "2mb", "4mb", "8mb"], type=str.lower, default="auto", help="set size of Game Boy cartridge ROM data")
	ap_cli2.add_argument("--dmg-mbc", choices=["auto", "1", "2", "3", "5", "6", "7"], type=str.lower, default="auto", help="set memory bank controller type of Game Boy cartridge")
	ap_cli2.add_argument("--dmg-savesize", choices=["auto", "4k", "16k", "64k", "256k", "512k", "1m", "eeprom2k", "eeprom4k", "tama5"], type=str.lower, default="auto", help="set size of Game Boy cartridge save data")
	ap_cli2.add_argument("--agb-romsize", choices=["auto", "4mb", "8mb", "16mb", "32mb", "64mb"], type=str.lower, default="auto", help="set size of Game Boy Advance cartridge ROM data")
	ap_cli2.add_argument("--agb-savetype", choices=["auto", "eeprom4k", "eeprom64k", "sram256k", "sram512k", "sram1m", "flash512k", "flash1m"], type=str.lower, default="auto", help="set type of Game Boy cartridge save data")
	ap_cli2.add_argument("--store-rtc", action="store_true", help="store RTC register values if supported")
	ap_cli2.add_argument("--ignore-bad-header", action="store_true", help="don’t stop if invalid data found in cartridge header data")
	ap_cli2.add_argument("--fast-read-mode", action="store_true", help="enable experimental fast read mode for GBxCart RW v1.3")
	ap_cli2.add_argument("--flashcart-handler", type=str, default="autodetect", help="name of flash cart; see txt files in config directory")
	ap_cli2.add_argument("--prefer-chip-erase", action="store_true", help="prefer full chip erase over sector erase when both available")
	ap_cli2.add_argument("--reversed-sectors", action="store_true", help="use reversed flash sectors if possible")
	ap_cli2.add_argument("--force-5v", action="store_true", help="force 5V when writing Game Boy flash cartridges")
	ap_cli2.add_argument("--no-verify-flash", action="store_true", help="do not verify written ROM data")
	ap_cli2.add_argument("--save-filename-add-datetime", action="store_true", help="adds a timestamp to the file name of save data backups")
	ap_cli2.add_argument("--gbcamera-palette", choices=["grayscale", "dmg", "sgb", "cgb1", "cgb2", "cgb3"], type=str.lower, default="grayscale", help="sets the palette of pictures extracted from Game Boy Camera saves")
	ap_cli2.add_argument("--gbcamera-outfile-format", choices=["png", "bmp", "gif", "jpg"], type=str.lower, default="png", help="sets the file format of saved pictures extracted from Game Boy Camera saves")
	args = parser.parse_args()
	
	if "appdata" in cp:
		config_path = cp[args.cfgdir]
	else:
		config_path = cp["subdir"]
	
	if args.mode is not None or args.action is not None:
		args.cli = True
	
	if args.debug == True:
		Util.DEBUG = True
	
	args = {"app_path":app_path, "config_path":config_path, "argparsed":args}
	args.update(LoadConfig(args))
	
	app = None
	exc = None
	if not args["argparsed"].cli:
		try:
			from . import FlashGBX_GUI
			app = FlashGBX_GUI.FlashGBX_GUI(args)
		except:
			exc = traceback.format_exc()
			app = None
		
		if app is None:
			from . import FlashGBX_CLI
			if args["argparsed"].action is None:
				parser.print_help()
				print("\n\n{:s}ERROR: GUI mode couldn’t be launched, but the application can be run in CLI mode.\n       Command line switches are explained above.{:s}\n".format(Util.ANSI.RED, Util.ANSI.RESET))
				if exc is not None: print("{:s}{:s}{:s}".format(Util.ANSI.YELLOW, exc, Util.ANSI.RESET))
			
			print("Now running in CLI mode.\n")
			app = FlashGBX_CLI.FlashGBX_CLI(args)
			try:
				app.run()
			except KeyboardInterrupt:
				print("\n\nProgram stopped.")
			return
		
		app.run()
	
	else:
		from . import FlashGBX_CLI
		print("Now running in CLI mode.\n")
		app = FlashGBX_CLI.FlashGBX_CLI(args)
		try:
			app.run()
		except KeyboardInterrupt:
			print("\n\nProgram stopped.")
