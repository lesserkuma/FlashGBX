# -*- coding: utf-8 -*-
# ＵＴＦ－８
import math, time, datetime, copy

# Utility functions
def bitswap(n, s):
	p, q = s
	if (((n & (1 << p)) >> p) ^ ((n & (1 << q)) >> q)) == 1:
		n ^= (1 << p)
		n ^= (1 << q)
	return n

def ParseCFI(buffer):
	buffer = copy.copy(buffer)
	info = {}
	magic = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
	if magic != "QRY": # nothing swapped
		return False
	
	try:
		info["flash_id"] = buffer[0:8]
		info["magic"] = "{:s}{:s}{:s}".format(chr(buffer[0x20]), chr(buffer[0x22]), chr(buffer[0x24]))
		
		if buffer[0x36] == 0xFF and buffer[0x48] == 0xFF:
			print("FAIL: No information about the voltage range found in CFI data.")
			try:
				with open("./cfi_debug.bin", "wb") as f: f.write(buffer)
			except:
				pass
			return False
		
		info["vdd_min"] = (buffer[0x36] >> 4) + ((buffer[0x36] & 0x0F) / 10)
		info["vdd_max"] = (buffer[0x38] >> 4) + ((buffer[0x38] & 0x0F) / 10)
		
		if buffer[0x3E] > 0 and buffer[0x3E] < 0xFF:
			info["single_write"] = True
			info["single_write_time_avg"] = int(math.pow(2, buffer[0x3E]))
			info["single_write_time_max"] = int(math.pow(2, buffer[0x46]) * info["single_write_time_avg"])
		else:
			info["single_write"] = False

		if buffer[0x40] > 0 and buffer[0x40] < 0xFF:
			info["buffer_write"] = True
			info["buffer_write_time_avg"] = int(math.pow(2, buffer[0x40]))
			info["buffer_write_time_max"] = int(math.pow(2, buffer[0x48]) * info["buffer_write_time_avg"])
		else:
			info["buffer_write"] = False

		if buffer[0x42] > 0 and buffer[0x42] < 0xFF:
			info["sector_erase"] = True
			info["sector_erase_time_avg"] = int(math.pow(2, buffer[0x42]))
			info["sector_erase_time_max"] = int(math.pow(2, buffer[0x4A]) * info["sector_erase_time_avg"])
		else:
			info["sector_erase"] = False

		if buffer[0x44] > 0 and buffer[0x44] < 0xFF:
			info["chip_erase"] = True
			info["chip_erase_time_avg"] = int(math.pow(2, buffer[0x44]))
			info["chip_erase_time_max"] = int(math.pow(2, buffer[0x4C]) * info["chip_erase_time_avg"])
		else:
			info["chip_erase"] = False

		info["tb_boot_sector"] = False
		if "{:s}{:s}{:s}".format(chr(buffer[0x80]), chr(buffer[0x82]), chr(buffer[0x84])) == "PRI":
			if buffer[0x9E] != 0 and buffer[0x9E] != 0xFF:
				temp = { 0x02: 'Bottom Boot Device', 0x03: 'Top Boot Device' }
				try:
					info["tb_boot_sector"] = "{:s} (0x{:02X})".format(temp[buffer[0x9E]], buffer[0x9E])
				except:
					info["tb_boot_sector"] = "0x{:02X}".format(buffer[0x9E])
		elif "{:s}{:s}{:s}".format(chr(buffer[0x214]), chr(buffer[0x216]), chr(buffer[0x218])) == "PRI":
			pass # todo
		
		info["device_size"] = int(math.pow(2, buffer[0x4E]))
		info["buffer_size"] = buffer[0x56] << 8 | buffer[0x54]
		if info["buffer_size"] > 1:
			info["buffer_write"] = True
			info["buffer_size"] = int(math.pow(2, info["buffer_size"]))
		else:
			del(info["buffer_size"])
			info["buffer_write"] = False
		info["erase_sector_regions"] = buffer[0x58]
		info["erase_sector_blocks"] = []
		total_blocks = 0
		pos = 0
		for i in range(0, min(4, info["erase_sector_regions"])):
			b = (buffer[0x5C+(i*8)] << 8 | buffer[0x5A+(i*8)]) + 1
			t = (buffer[0x60+(i*8)] << 8 | buffer[0x5E+(i*8)]) * 256
			total_blocks += b
			size = b * t
			pos += size
			info["erase_sector_blocks"].append([ t, b, size ])
	
	except:
		print("ERROR: Trying to parse CFI data resulted in an error.")
		try:
			with open("./cfi_debug.bin", "wb") as f: f.write(buffer)
		except:
			pass
		return False
	
	return info

def dprint(*args, **kwargs):
	# uncomment for some debug prints
	#print(" ".join(map(str, args)), **kwargs)
	pass
