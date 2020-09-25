# FlashGBX

by Lesserkuma

<img src="/.github/FlashGBX_Windows.png" alt="Screenshot" width="500">
<img src="/.github/FlashGBX_Ubuntu.png" alt="Screenshot" width="500">

## Introduction

### Software features

- Backup and restore save data from Game Boy and Game Boy Advance game cartridges
- Backup ROM data from Game Boy and Game Boy Advance game cartridges
- Flash new ROMs to a wide variety of Game Boy and Game Boy Advance flash cartridges
- Many flash cartridges can be auto-detected
- A Flash ID check can be performed for unsupported flash cartridges

### Confirmed working reader/writer hardware

- [insideGadgets GBxCart RW v1.3 and v1.3 Pro](https://www.gbxcart.com/) with firmware versions from R17 up to R19 (other hardware revisions and firmware versions may also work, but are untested)

### Currently supported flash cartridges

- Game Boy

	- insideGadgets 32 KB *(thanks AlexiG)*
	- insideGadgets 512 KB *(thanks AlexiG)*
	- insideGadgets 1 MB, 128 KB SRAM *(thanks AlexiG)*
	- insideGadgets 2 MB, 128 KB SRAM/32 KB FRAM *(thanks AlexiG)*
	- insideGadgets 4 MB, 128 KB SRAM/FRAM *(thanks AlexiG)*
	- insideGadgets 4 MB, 32 KB FRAM, MBC3+RTC *(thanks AlexiG)*
	- BUNG Doctor GB Card 64M
	- GB Smart 32M

- Game Boy Advance

	- Flash2Advance 256M (non-ultra variant)
	- Nintendo AGB Cartridge 128M Flash S, E201850
	- Nintendo AGB Cartridge 256M Flash S, E201868

### Currently supported bootleg cartridges

- Game Boy

	- DIY cart with AM29F016/AM29F016B *(thanks RevZ)*
	- ES29LV160_DRV with 29DL32TF-70
	- GB-M968 with M29W160EB *(thanks RevZ)*
	- GB-M968 with MX29LV320ABTC
	- S29GL032 (no PCB text)
	- SD007_48BALL_64M with GL032M11BAIR4 *(thanks RevZ)*
	- SD007_48BALL_64M with M29W640
	- SD007_48BALL_64M_V3 with 29DL161TD-90
	- SD007_48BALL_64M_V5 with 36VF3204
	- SD007_48BALL_64M_V6 with 29DL163BD-90 *(thanks LovelyA72)*
	- SD007_BV5_V2 with HY29LV160TT *(thanks RevZ)*
	- SD007_BV5_V2 with MX29LV320BTC *(thanks RevZ)*
	- SD007_BV5_V3 with AM29LV160MB *(thanks RevZ)*

- Game Boy Advance

	- 28F256L03B-DRV with 256L30B
	- 4455_4400_4000_4350_36L0R_V3 with M36L0R705
	- AGB-E05-01 with MSP55LV128M
	- AGB-SD-E05 with MSP55LV128 *(thanks RevZ)*
	- BX2006_0106_NEW with S29GL128N10TFI01 *(thanks litlemoran)*

Many different bootleg cartridges share their command set, so even if yours is not on this list, it may still work fine or even be detected as another one. Support for more cartridges can also be added by creating external config files that include the necessary flash chip commands.

## DISCLAIMER

This software is provided as-is and the developer is not responsible for any damage that is caused by the use of it. Use at your own risk!

## System Requirements and Setup Instructions

Requires [Python 3.8+](https://www.python.org/downloads/) with [PySide2](https://pypi.org/project/PySide2/) and [pyserial](https://pypi.org/project/pyserial/) packages. If these are available for your Operating System, it should be compatible.

Developed and tested using the *insideGadgets GBxCart RW v1.3 Pro* hardware device on Windows 10. Also confirmed working on most Debian-based Linux distributions including Ubuntu.

### Windows

There are multiple options to run this application on Windows:

* You can install the app with the Setup program. This will add the app to the start menu and optionally create a desktop icon.
* Or, you can extract the Portable package and run the precompiled `FlashGBX.exe` file (created with *PyInstaller*) which includes the Python interpreter, required packages and libraries.
* Or, you can install Python and run the app directly from source code:
	1. Install [Python 3.8+](https://www.python.org/downloads/)
	2. Open a Command Prompt window and install PySide2 and pyserial like so:<br>`pip install PySide2 pyserial`
	3. Run `FlashGBX.py`

### Linux

#### Manual setup procedure tested on Ubuntu 20.04.1 LTS

1. Update the package list:<br>`sudo apt update`
2. Install Python3, pip for Python 3 and the XCB library package (required by PySide2/Qt5):<br>`sudo apt install python3 python3-pip libxcb-xinerama0`<br>If it says “Package 'python3-pip' has no installation candidate”, you may need to run this command first and then try again:<br>`sudo add-apt-repository universe`
3. Install PySide2 and pyserial using pip:<br>`sudo pip3 install PySide2 pyserial`
4. At this point you could run the app with `sudo` privileges, but to avoid that you will need access permissions for your cart reader/writer hardware. Here are some ways to do that:
	* Add yourself to the *dialout* usergroup and then reboot the system:<br>`sudo adduser $USER dialout`<br>`sudo reboot`
	* Or, add permanent user permissions to your device. (No reboot required.)
		1. Create a udev rules file:<br>`sudoedit /etc/udev/rules.d/50-ttyusb.rules`
		2. Add the following line to this file (GBxCart RW uses Vendor ID *1a86* and Product ID *7523*):<br>`KERNEL=="ttyUSB[0-9]*",ATTRS{idVendor}=="1a86",ATTRS{idProduct}=="7523",MODE="0666"`
		3. Reload your udev configuration:<br>`sudo udevadm control --reload`
		4. Connect your cart reader/writer to a USB port. (If it was already connected, unplug and reconnect it.)
6. Run the app:<br>`python3 FlashGBX.py`

#### Automated install script for Debian-based distributions

A third-party install script contributed by *RevZ* for your convenience is also available. This is not maintained by me, but this should take care of installing all the prerequisites and copy everything to a subdirectory in your home directory. It also adds a shortcut to your desktop.

After extracting all FlashGBX files into a temporary directory, get the installer [here](https://pastebin.com/fDsYh1Eb), place it into the same directory, adjust permissions (`chmod +x installer.sh`) and run it (`./installer.sh`). After the install is complete you may still have to reboot, and right click the Desktop icon to “Allow Launching”.

## Contributions

The author would like to thank the following kind people for their help and contributions:

- AlexiG (GBxCart RW hardware, bug reports, flash chip info)
- RevZ (install script for Linux, testing, bug reports, flash chip info)
- AndehX (app icon)
- LovelyA72 (flash chip info)
- litlemoran (flash chip info)

## Changes

### v0.7β

- First started tracking changes
- Added a way to launch the flash cartridge type auto-detection process from the type list
- Added support for SD007_48BALL_64M_V6 with 29DL163BD-90 *(thanks LovelyA72)*
- Confirmed support for BX2006_0106_NEW with S29GL128N10TFI01 (same as AGB-E05-01 with MSP55LV128M) *(thanks litlemoran)*
- Fixed config file for 4455_4400_4000_4350_36L0R_V3 with M36L0R705 (sector size map was incomplete)
- Renamed some labels of flash cartridge types
- Made config files UTF-8 compatible
- File open and save dialogs will now remember the last used directory for ROM files and save data files respectively (stored in config.ini in AppData/Roaming), clearable with the `--resetconfig` switch
- Added CRC32 checksum comparison for Game Boy Advance games by using a database based on header SHA1 hashes
- Fixed a bug with save data restore and improved save data backup speed
- Fixed a few status message errors
- Added a warning when changing platforms
- Made some messages suppressible (stored in config.ini)
- Added detection of ungraceful device disconnects when starting a new task, with optional automatic reconnect
- First public beta release
