# FlashGBX

by Lesserkuma

<img src="https://raw.githubusercontent.com/lesserkuma/FlashGBX/master/.github/FlashGBX_Windows.png" alt="FlashGBX on Windows" width="500">

<img src="https://raw.githubusercontent.com/lesserkuma/FlashGBX/master/.github/FlashGBX_Ubuntu.png" alt="FlashGBX on Ubuntu" width="500">

<img src="https://raw.githubusercontent.com/lesserkuma/FlashGBX/master/.github/FlashGBX_macOS.png" alt="FlashGBX on macOS" width="500">

## Introduction

### Software features

- Backup, restore and erase save data from Game Boy and Game Boy Advance game cartridges
- Backup ROM data from Game Boy and Game Boy Advance game cartridges
- Write new ROMs to a wide variety of Game Boy and Game Boy Advance flash cartridges
- Many reproduction cartridges and flash cartridges can be auto-detected
- A flash chip query can be performed for unsupported flash cartridges
- Decode and extract Game Boy Camera photos from save data

### Confirmed working reader/writer hardware

- [insideGadgets GBxCart RW v1.3 and v1.3 Pro](https://www.gbxcart.com/) with firmware versions from R19 up to R26 (other hardware revisions and firmware versions may also work, but are untested)

### Currently supported official cartridge memory mappers

- Game Boy
  - All cartridges without memory mapping
  - MBC1
  - MBC2
  - MBC3/MBC30
  - MBC5
  - MBC7
  - MBC1M
  - MMM01
  - Game Boy Camera
  - G-MMC1 (ROM and map backup only)
  - M161
  - HuC-1
  - HuC-3
  - TAMA5

- Game Boy Advance
  - All cartridges without memory mapping
  - 3D Memory (GBA Video)

### Currently supported flash cartridges

- Game Boy

  - BUNG Doctor GB Card 64M
  - DIY cart with AM29F016/AM29F016B
  - DIY cart with AM29F032/AM29F032B
  - DIY cart with AT49F040
  - GB Smart 32M
  - insideGadgets 32 KB
  - insideGadgets 512 KB
  - insideGadgets 1 MB, 128 KB SRAM
  - insideGadgets 2 MB, 128 KB SRAM/32 KB FRAM
  - insideGadgets 4 MB, 128 KB SRAM/FRAM
  - insideGadgets 4 MB, 32 KB FRAM, MBC3+RTC
  - Mr Flash 64M

- Game Boy Advance

  - Development AGB Cartridge 128M Flash S, E201850
  - Development AGB Cartridge 256M Flash S, E201868
  - Flash2Advance 256M (non-ultra variant, with 2× 28F128J3A150)
  - insideGadgets 16 MB, 64K EEPROM with Solar Sensor and RTC options
  - insideGadgets 32 MB, 1M FLASH with RTC option
  - insideGadgets 32 MB, 512K FLASH
  - insideGadgets 32 MB, 4K/64K EEPROM
  - insideGadgets 32 MB, 256K FRAM with Rumble option

### Currently supported and tested reproduction cartridges

- Game Boy

  - DMG-DHCN-20 with MX29LV320ET
  - ES29LV160_DRV with 29DL32TF-70
  - GB-M968 with M29W160EB
  - GB-M968 with MX29LV320ABTC
  - ALTERA CPLD and S29GL032N90T (no PCB text)
  - SD007_48BALL_64M with GL032M11BAIR4
  - SD007_48BALL_64M with M29W640
  - SD007_48BALL_64M_V2 with GL032M11BAIR4
  - SD007_48BALL_64M_V2 with M29W160ET
  - SD007_48BALL_64M_V3 with 29DL161TD-90
  - SD007_48BALL_64M_V5 with 36VF3203
  - SD007_48BALL_64M_V5 with 36VF3204
  - SD007_48BALL_64M_V6 with 36VF3204
  - SD007_48BALL_64M_V6 with 29DL163BD-90
  - SD007_BV5_DRV with M29W320DT
  - SD007_BV5_DRV with S29GL032M90TFIR4
  - SD007_BV5_V2 with HY29LV160TT
  - SD007_BV5_V2 with MX29LV320BTC
  - SD007_BV5_V3 with 29LV160BE-90PFTN
  - SD007_BV5_V3 with HY29LV160BT-70
  - SD007_BV5_V3 with AM29LV160MB
  - SD007_K8D3216_32M with MX29LV160CT
  - SD007_TSOP_48BALL with 36VF3204
  - SD007_TSOP_48BALL with AM29LV160DB
  - SD007_TSOP_48BALL with AM29LV160DT
  - SD007_TSOP_48BALL with K8D3216UTC
  - SD007_TSOP_48BALL with M29W160ET
  - SD007_TSOP_48BALL with L160DB12VI

- Game Boy Advance

  - 28F256L03B-DRV with 256L30B
  - 36L0R8-39VF512 with M36L0R8060B
  - 36L0R8-39VF512 with M36L0R8060T
  - 4050M0Y0Q0-39VF512 with 4050M0Y0Q0
  - 4050_4400_4000_4350_36L0R_V5 with 4050L0YTQ2
  - 4050_4400_4000_4350_36L0R_V5 with M36L0R7050T
  - 4050_4400_4000_4350_36L0R_V5 with M36L0T8060T
  - 4050_4400_4000_4350_36L0R_V5 with M36L0R8060T
  - 4400 with 4400L0ZDQ0
  - 4455_4400_4000_4350_36L0R_V3 with M36L0R7050T
  - AGB-E05-01 with GL128S
  - AGB-E05-01 with MSP55LV128M
  - AGB-E05-01 with MX29GL128FHT2I-90G
  - AGB-E05-02 with M29W128FH
  - AGB-E05-02 with M29W128GH
  - AGB-E08-09 with 29LV128DTMC-90Q
  - AGB-SD-E05 with MSP55LV128
  - B104 with MSP55LV128
  - BX2006_0106_NEW with S29GL128N10TFI01
  - BX2006_TSOP_64BALL with GL128S
  - BX2006_TSOP_64BALL with GL256S
  - BX2006_TSOPBGA_0106 with M29W640GB6AZA6
  - BX2006_TSOPBGA_0106 with K8D6316UTM-PI07
  - GE28F128W30 with 128W30B0
  - M6MGJ927 (no PCB text)

Many different reproduction cartridges share their flash chip command set, so even if yours is not on this list, it may still work fine or even be auto-detected as another one. Support for more cartridges can also be added by creating external config files that include the necessary flash chip commands.

## Installing and running

If you have Python and pip installed, you can use `pip install FlashGBX` to download and install the application, or use `pip install --upgrade FlashGBX` to upgrade from an older version. Then use `python -m FlashGBX` or `python -m FlashGBX --cli` to run it.

To run FlashGBX in portable mode, you can also download the source code archive and call `python run.py` after installing the prerequisites yourself.

The application should work on pretty much every operating system that supports Qt-GUI applications built using [Python 3.7+](https://www.python.org/downloads/) with [PySide2](https://pypi.org/project/PySide2/), [pyserial](https://pypi.org/project/pyserial/), [Pillow](https://pypi.org/project/Pillow/), [setuptools](https://pypi.org/project/setuptools/) and [requests](https://pypi.org/project/requests/) packages.

*On some platforms you may have to use `pip3`/`python3` instead of `pip`/`python`.*

### Windows binaries

Available in the GitHub [Releases](https://github.com/lesserkuma/FlashGBX/releases) section:

* Windows Setup: An installer that will add the application to the start menu and optionally create a desktop icon
* Windows Portable: Have everything in one place including the config files

These executables have been created using *PyInstaller* and *Inno Setup*.

### Troubleshooting

* If something doesn’t work as expected, first try to clean the game cartridge contacts (best with IPA 99.9%+ on a cotton swab) and reconnect the device.

* On Linux systems, you may run into a *Permission Error* problem when trying to connect to USB devices without *sudo* privileges. To grant yourself the necessary permissions temporarily, you can run `sudo chmod 0666 /dev/ttyUSB0` (replace with actual device path) before running the app. For a permanent solution, add yourself to the usergroup that has access to serial devices by default (e.g. *dialout* on Debian-based distros; `sudo adduser $USER dialout`) and then reboot the system.

* On some Linux systems, you may need the *XCB Xinerama package* if you see an error regarding failed Qt platform plugin initialization. You can install it with `sudo apt install libxcb-xinerama0` etc.

* If the `PySide2` package is not available for your system, you can install FlashGBX like so instead: `pip install pyserial Pillow setuptools requests` followed by `pip install --no-deps FlashGBX`.

* On older systems such as MacOS X El Capitan 10.11, you may run into an error that says `TypeError: 'Shiboken.ObjectType' object is not iterable`. Installing [Python 3.7.9](https://www.python.org/downloads/release/python-379/) instead of the latest available version may resolve this issue. If that still doesn’t work, you can try to uninstall PySide2 (`pip uninstall PySide2`) and then run FlashGBX again in command line interface mode.

* For save data backup/restore on Game Boy Advance reproduction cartridges, depending on how it was built, you may have to manually select the save type for it to work properly. However, the save data backup/restore feature may not work on certain reproduction cartridges with batteryless-patched ROMs. As those cartridges use the same flash chip for both ROM and save data storage, a full ROM backup will usually include the save data. Also, when flashing a new unpatched ROM to a cartridge like this, the game may not be able to save progress without soldering in a battery. See the [Flash Cart DB website](https://flashcartdb.com/index.php/Clone_and_Repo_Cart_Problems) for more information.

## DISCLAIMER

This software is provided as-is and the developer is not responsible for any damage that is caused by the use of it. Use at your own risk!

## Contributions

The author would like to thank the following very kind people for their help and contributions (in alphabetical order):

- AlexiG (GBxCart RW hardware, bug reports, flash chip info)
- AndehX (app icon, flash chip info)
- antPL (flash chip info)
- bbsan (flash chip info)
- ClassicOldSong (bug reports)
- djedditt (testing)
- easthighNerd (feature suggestions)
- Frost Clock (flash chip info)
- howie0210 (flash chip info)
- Icesythe7 (feature suggestions)
- JFox (help with properly packaging the app for pip)
- julgr (macOS help, testing)
- litlemoran (flash chip info)
- LovelyA72 (flash chip info)
- LucentW (flash chip info, testing, bug reports)
- marv17 (flash chip info, testing, bug reports, feature suggestions)
- paarongiroux (bug reports)
- Paradoxical (flash chip info)
- RevZ (Linux help, testing, bug reports, flash chip info)
- Super Maker (flash chip info, testing)
- Veund (flash chip info)
- Zeii (flash chip info)
- Zelante (flash chip info)

## Changes

### v0.7β (released 2020-09-25)
- First started tracking changes
- Added a way to launch the flash cartridge type auto-detection process from the type list
- Added support for SD007_48BALL_64M_V6 with 29DL163BD-90 *(thanks LovelyA72)*
- Confirmed support for BX2006_0106_NEW with S29GL128N10TFI01 (same as AGB-E05-01 with MSP55LV128M) *(thanks litlemoran)*
- Fixed config file for 4455_4400_4000_4350_36L0R_V3 with M36L0R705 (sector size map was incomplete)
- Renamed some labels of flash cartridge types
- Made config files UTF-8 compatible
- File open and save dialogs will now remember the last used directory for ROM files and save data files respectively (stored in settings.ini in AppData/Roaming), clearable with the `--reset` switch or by editing/deleting settings.ini
- Added CRC32 checksum comparison for Game Boy Advance games by using a database based on header SHA1 hashes
- Fixed a bug with save data restore and improved save data backup speed
- Fixed a few status message errors
- Added a warning when changing platforms
- Made some messages suppressible (stored in settings.ini)
- Added detection of ungraceful device disconnects when starting a new task, with optional automatic reconnect
- First public beta release

### v0.8β (released 2020-10-03)
- Added support for the DIY cart with AM29F016/AM29F016B with AUDIO as WE *(thanks AndehX)*
- Renamed `VIN` to `AUDIO` in config files and the command line switch `--resetconfig` to `--reset`
- Added experimental support for GBxCart RW revisions other than v1.3 and fixed a crash when connecting to unknown revisions of the GBxCart RW
- The app is now available as a package and can be installed directly through *pip* *(thanks JFox)*
- Changed the way configuration files are stored (for details call with `--help` command line switch)
- Added a button that opens a file browser to the currently used config directory for easy access
- Added the option to erase/wipe the save data on a cartridge
- Rearranged some buttons on the main window so that the newly added button popup menus don’t block anything
- Improved the database for Game Boy Advance titles (now detects SRAM_F_V### save types properly)
- Rewrote some of the save data handling for Game Boy Advance cartridges to speed transfers up a bit
- Fixed a couple of instability issues that used to caused timeouts on macOS *(thanks julgr)*
- Confirmed support for SD007_48BALL_64M_V5 with 29DL163BD-90 *(thanks julgr)*
- Added an option for flashing at 5V for a few flash cartridge types that sometimes require this; if you think your cartridge is affected, you can add `"voltage_variants":true,` to the config file for it
- Fixed support for Windows 7 when using pre-compiled exe file packages
- Reduced size and decompression time of the pre-compiled exe file packages by excluding unnecessary DLL files
- Fixed a timing issue that could sometimes cause a loss of save data when hot-swapping Game Boy cartridges
- Added some warnings that may help with troubleshooting
- Added taskbar progress visualization on Windows systems

### v0.9β (released 2020-12-17)
- Confirmed support for BX2006_TSOP_64BALL with GL128S
- Confirmed support for SD007_48BALL_64M_V2 with GL032M11BAIR4
- Added support for 4050_4400_4000_4350_36L0R_V5 with M36L0R8060T/M36L0T8060T
- Rewrote parts of the GBxCart RW interface code
- When flashing ROM files, empty chunks of data will now be skipped
- Fixed config files for MSP55LV128 and MSP55LV128M flash chips
- Confirmed support for SD007_48BALL_64M_V6 with 36VF3204
- Confirmed support for SD007_TSOP_48BALL with 36VF3204
- Added the option to add date and time to suggested filenames for save data backups *(thanks easthighNerd for the suggestion)*
- Added a check and warning for unstable ROM readings
- Added Common Flash Interface query for both unknown and known flash cartridge types
- Added support for 36L0R8-39VF512 with M36L0R8060B *(thanks LucentW)*
- Added support for another version of 36L0R8-39VF512 with M36L0R8060B/M36L0R8060T *(thanks AndehX)*
- Added support for AGB-E05-02 with M29W128GH *(thanks marv17)*
- Added backup and restore of 1M SRAM save data in GBA mode
- Confirmed support for BX2006_TSOPBGA_0106 with M29W640GB6AZA6 *(thanks LucentW)*
- Confirmed support for AGB-E05-01 with GL128S
- Improved writing speed for MSP55LV128M, S29GL128 and similar flash chips (requires GBxCart RW firmware R23 or newer)
- Before flashing a ROM it will now be checked if its logo data and header checksum are valid and a warning will be shown if not
- Added support for SD007_BV5_V3 with 29LV160BE-90PFTN *(thanks LucentW)*
- Added support for SD007_BV5_V3 with HY29LV160BT *(thanks LucentW)*
- Added support for SD007_48BALL_64M_V5 with 36VF3203 *(thanks LucentW)*
- Added support for SD007_TSOP_48BALL with M29W160ET *(thanks LucentW)*
- Added support for AGB-E08-09 with 29LV128DTMC-90Q *(thanks LucentW)*
- Confirmed support for SD007_TSOP_48BALL with L160DB12VI *(thanks marv17)*
- Added support for SD007_TSOP_48BALL with AM29LV160DT *(thanks marv17)*
- Added support for SD007_BV5_DRV with M29W320DT *(thanks Frost Clock)*
- Added experimental *Fast Read Mode* support for GBxCart RW with firmware R19+; can be up to 20% faster, but the functioning currently heavily relies on system performance and drivers
- Bumped the required minimum firmware version of GBxCart RW to R19
- Confirmed support for 4050_4400_4000_4350_36L0R_V5 with M36L0R7050T
- Added the option to enable the preference of sector erase over chip erase when flashing a ROM; this can improve flashing speed for ROMs smaller than the flash chip capacity
- Some flash chips may have reversed sectors despite shared flash ID; if you think your cartridge is affected, you can add `"sector_reversal":true,` to its config file for a prompt upon flashing
- Renamed config.ini to settings.ini to avoid confusion with the term “config file”

### v0.10 (released 2020-12-27)
- Fixed an issue with Raspberry Pi compatibility *(thanks ClassicOldSong)*
- Confirmed support for SD007_TSOP_48BALL with AM29LV160DB *(thanks marv17)*
- Fixed timeout errors with ROMs that have non-standard file sizes (e.g. trimmed files)
- Improved writing speed for most Game Boy reproduction cartridges by up to 40% (requires GBxCart RW firmware R24 or newer)
- Improved writing speed for M36L0R and similar flash chips by up to 80% (requires GBxCart RW firmware R24 or newer)
- Confirmed support for 4400 with 4400L0ZDQ0 *(thanks Zeii)*
- Backup and restore save data of flash chips manufactured by SANYO requires GBxCart RW firmware R24 or newer; a warning message for this will now be displayed in necessary cases
- Added the option to check for updates at application start *(thanks Icesythe7 and JFox for the suggestion and help)*
- Added support for BX2006_TSOPBGA_0106 with K8D6316UTM-PI07 *(thanks LucentW)*
- Added support for the currently available insideGadgets Game Boy Advance flash cartridges *(thanks AlexiG)*
- Added a Game Boy Camera album viewer and picture extractor

### v1.0 (released 2021-01-01)
- Added a firmware check when writing to insideGadgets Game Boy Advance flash cartridges (requires GBxCart RW firmware R20 or newer)
- Confirmed support for Mr Flash 64M (rebranded BUNG Doctor GB Card 64M)
- Fixed a problem with writing to the insideGadgets 512 KB Game Boy flash cartridge

### v1.1 (released 2021-01-11)
- Added support for GE28F128W30 with 128W30B0 *(thanks bbsan)*
- Added support for BX2006_TSOP_64BALL with GL256S *(thanks Paradoxical)*
- Confirmed support for SD007_48BALL_64M_V2 with M29W160ET *(thanks Paradoxical)*
- Added support for M6MGJ927 (no PCB text) *(thanks Super Maker)*
- Added a warning for very old reproduction cartridges with DRM that show “YJencrypted” as their game title *(thanks Super Maker)*
- Added a firmware check when writing to cartridges with flash chips manufactured by Sharp (unsupported by GBxCart RW firmware R25)
- Added optional verification of written data after ROM flashing *(thanks marv17 for the suggestion)*

### v1.2.1 (released 2021-01-16)
- Fixed a bug introduced in v1.1 that broke MBC3 handling *(thanks marv17 for reporting)*
- Will now default back to 5V for Game Boy cartridges after unsuccessful flash chip auto-detection
- Added support for DIY carts with the AT49F040 flash chip *(thanks howie0210)*
- Minor bug fixes

### v1.3 (released 2021-01-21)
- Fixed a bug introduced in v1.1 that broke support for AGB-E08-09 with 29LV128DTMC-90Q *(thanks LucentW for reporting)*
- Will now show the application’s version number in message boxes

### v1.4 (released 2021-02-28)
- Added a command line interface (CLI) as an alternative to the GUI interface; see `--help` command line switch for details or run interactive mode with `--cli`
- Fixed some minor compatibility issues for older systems that only have access to slightly outdated versions of the PySide2 package
- Added support for DMG-DHCN-20 with MX29LV320ET *(thanks Veund)*
- Added the option to export Game Boy Camera pictures in more file formats
- Added support for SD007_BV5_DRV with S29GL032M90TFIR4
- Confirmed support for SD007_BV5_DRV with MX29LV320BTC
- Added support for SD007_K8D3216_32M with MX29LV160CT *(thanks marv17)*
- Added support for AGB-E05-02 with M29W128FH
- Reading the sector map from CFI is experimental and can be enabled by adding `"sector_size_from_cfi":true,` to a flash cartridge config file
- Several flash cartridge types can now be written via full chip erase mode
- For specifying a specific MBC for writing to a DIY flash cartridge, it is now possible to add `"mbc":3,` or the like to its config file
- Removed officially unused Game Boy MBC types and ROM sizes from the drop down lists
- Added support for AGB-E05-01 with MX29GL128FHT2I-90G *(thanks antPL)*
- Added support for official cartridges with the HuC-1 memory bank controller; tested with “Pokémon Card GB” (DMG-ACXJ-JPN)
- Added support for official cartridges with the HuC-3 memory bank controller; tested with “Robot Poncots Sun Version” (DMG-HREJ-JPN)
- Added support for official cartridges with the TAMA5 memory bank controller; tested with “Game de Hakken!! Tamagotchi Osutchi to Mesutchi” (DMG-AOMJ-JPN) (requires GBxCart RW firmware R26 or newer)
- Added preliminary support for official GBA Video cartridges with 3D Memory; tested with “Shrek 2” (AGB-M2SE-USA) *(thanks to endrift’s article [“Dumping the Undumped”](https://mgba.io/2015/10/20/dumping-the-undumped/))* (requires a future firmware update of GBxCart RW)
- Added support for optionally saving and restoring RTC registers of official TAMA5 cartridges inside the save file
- Experimental support for optionally saving RTC registers of official MBC3+RTC+SRAM+BATTERY cartridges inside the save file using the 48 bytes save format explained on the [BGB website](https://bgb.bircd.org/rtcsave.html) was added. Latching the RTC register and restoring RTC register values to the cartridge is not supported at this time as it requires a new GBxCart RW hardware device revision.
- Added support for 4050_4400_4000_4350_36L0R_V5 with 4050L0YTQ2 *(thanks Shinichi999)*
- Fixed GUI support on macOS Big Sur *(thanks paarongiroux)*
- Added support for official cartridges with the MBC1M memory bank controller; tested with “Bomberman Collection” (DMG-ABCJ-JPN); save data backup is untested but should work
- Added support for official cartridges with the MMM01 memory bank controller; tested with “Momotarou Collection 2” (DMG-AM3J-JPN) (requires GBxCart RW firmware R26 or newer)
- Support for optionally saving and restoring RTC registers of official HuC-3+RTC+SRAM+BATTERY cartridges inside the save file using the 12 bytes save format used by the [hhugboy emulator](https://github.com/tzlion/hhugboy) was added.
- Added support for SD007_TSOP_48BALL with K8D3216UTC *(thanks marv17)*

### v1.4.1 (released 2021-03-15)
- Added ROM and map backup support for official Nintendo Power GB Memory cartridges (DMG-MMSA-JPN); save data handling and ROM writing is not supported yet
- Fixed a minor bug with save data backup and restore (the bug did not cause damage)
- Added preliminary support for 4050M0Y0Q0-39VF512 with 4050M0Y0Q0 (requires a future firmware update of GBxCart RW)
- Added preliminary support for official cartridges with the MBC7 memory bank controller; tested with “Korokoro Kirby” (CGB-KKKJ-JPN) (requires a future firmware update of GBxCart RW)
- Added support for official cartridges with the M161 memory bank controller; tested with “Mani 4 in 1: Tetris + Alleyway + Yakuman + Tennis” (DMG-601CHN) (requires GBxCart RW firmware R26 or newer)
- Added support for B104 with MSP55LV128 *(thanks Zelante)*
- Added save data backup and restore support for official cartridges with ATMEL AT29LV512 flash chips; tested with a copy of “Mario Kart: Super Circuit” (AGB-AMKP-EUR)
