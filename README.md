# FlashGBX (by Lesserkuma)

for [Windows](https://github.com/lesserkuma/FlashGBX/releases), [Linux](https://github.com/lesserkuma/FlashGBX#run-using-python-linux-macos-windows), [macOS](https://github.com/lesserkuma/FlashGBX#run-using-python-linux-macos-windows)

<img src="https://raw.githubusercontent.com/lesserkuma/FlashGBX/master/.github/01.png" alt="FlashGBX on Windows" width="400"><br><img src="https://raw.githubusercontent.com/lesserkuma/FlashGBX/master/.github/02.png" alt="GB Camera Album Viewer"  width="400">

## Introduction

### Software features

- Backup, restore and erase save data from Game Boy and Game Boy Advance game cartridges including Real Time Clock registers
- Backup ROM data from Game Boy and Game Boy Advance game cartridges
- Write new ROMs to a wide variety of Game Boy and Game Boy Advance flash cartridges
- Many reproduction cartridges and flash cartridges can be auto-detected
- A flash chip query (including Common Flash Interface information) can be performed for flash cartridges
- Decode and extract Game Boy Camera photos from save data
- Update firmware of insideGadgets GBxCart RW v1.3 and v1.4 devices

### Confirmed working reader/writer hardware and firmware versions

- [insideGadgets GBxCart RW v1.3, v1.4 and Mini](https://www.gbxcart.com/)
  - Official firmware versions R30 to R33 (other hardware revisions and firmware versions may also work, but are untested)
  - Lesserkuma’s high compatibility firmware versions L1 to L4

## Installing and running

### Windows Binaries

Available in the GitHub [Releases](https://github.com/lesserkuma/FlashGBX/releases) section:

* Windows Setup: An installer that will add the application to the start menu and optionally create a desktop icon
* Windows Portable: Have everything in one place including the config files

### Run using Python (Linux, macOS, Windows)

#### Installing or upgrading from an older version

1. Download and install [Python](https://www.python.org/downloads/) (version 3.7 or higher)
2. Open a Terminal or Command Prompt window
3. If your Python version is 3.10 or newer, first run this command:<br>`pip3 install --ignore-requires-python -U PySide2`
4. Install or upgrade FlashGBX with this command:<br>`pip3 install -U FlashGBX`
* If installation fails and you see an error about a conflict involving PySide2, try these commands instead:<br>`pip3 install pyserial Pillow setuptools requests python-dateutil`<br>`pip3 install --no-deps -U FlashGBX`

* Pre-made Linux packages and instructions for select distributions are available [here](https://github.com/JJ-Fox/FlashGBX-Linux-builds/releases/latest).

*FlashGBX should work on pretty much any operating system that supports Qt-GUI applications built using [Python](https://www.python.org/downloads/) with [PySide2](https://pypi.org/project/PySide2/), [pyserial](https://pypi.org/project/pyserial/), [Pillow](https://pypi.org/project/Pillow/), [setuptools](https://pypi.org/project/setuptools/), [requests](https://pypi.org/project/requests/) and [python-dateutil](https://pypi.org/project/python-dateutil/) packages.*

#### Running
Use this command in a Terminal or Command Prompt window to launch the installed FlashGBX application:

`python3 -m FlashGBX`

*To run FlashGBX in portable mode without installing, you can also download the source code archive and call `python3 run.py` after installing the prerequisites yourself.*

## Cartridge Compatibility
### Supported official cartridge memory mappers
- Game Boy
  - All cartridges without memory mapping
  - MBC1
  - MBC2
  - MBC3
  - MBC30
  - MBC5
  - MBC6
  - MBC7
  - MBC1M
  - MMM01
  - GBD (Game Boy Camera)
  - G-MMC1 (GB Memory)
  - M161
  - HuC-1
  - HuC-3
  - TAMA5

- Game Boy Advance
  - All cartridges without memory mapping
  - 8M FLASH DACS
  - 3D Memory (GBA Video)

### Currently supported flash cartridges

- Game Boy

  - 29LV Series Flash BOY with 29LV160DB
  - BUNG Doctor GB Card 64M
  - DIY cart with AM29F016
  - DIY cart with AM29F032
  - DIY cart with AT49F040
  - DIY cart with MBC1 and AM29F080
  - DIY cart with MBC3 and MX29LV640
  - DMG-MBC5-32M-FLASH Development Cartridge, E201264
  - Ferrante Crafts cart with SST39SF010A
  - GB-CART32K-A with SST39SF020A
  - GB Smart 32M
  - HDR Game Boy Camera Flashcart
  - insideGadgets 32 KB
  - insideGadgets 512 KB
  - insideGadgets 1 MB, 128 KB SRAM
  - insideGadgets 2 MB, 128 KB SRAM/32 KB FRAM
  - insideGadgets 2 MB, 32 KB FRAM, v1.0
  - insideGadgets 4 MB, 128 KB SRAM/FRAM
  - insideGadgets 4 MB, 32 KB FRAM, MBC3+RTC
  - insideGadgets 4 MB (2× 2 MB), 32 KB FRAM, MBC5
  - Mr Flash 64M

- Game Boy Advance

  - Development AGB Cartridge 64M Flash S, E201843
  - Development AGB Cartridge 128M Flash S, E201850
  - Development AGB Cartridge 256M Flash S, E201868
  - Flash2Advance 128M (with 2× 28F640J3A120)
  - Flash2Advance 256M (with 2× 28F128J3A150)
  - Flash2Advance Ultra 64M (with 2× 28F320C3B)
  - insideGadgets 16 MB, 64K EEPROM with Solar Sensor and RTC options
  - insideGadgets 32 MB, 1M FLASH with RTC option
  - insideGadgets 32 MB, 512K FLASH
  - insideGadgets 32 MB, 4K/64K EEPROM
  - insideGadgets 32 MB, 256K FRAM with Rumble option

### Currently supported and tested reproduction cartridges

- Game Boy

  - 2006_TSOP_64BALL_QFP48 with AL016J55FFAR2
  - 36VF3204 and ALTERA CPLD (no PCB text)
  - DMG-DHCN-20 with MX29LV320ET
  - DMG-GBRW-20 with 29LV320ETMI-70G
  - ES29LV160_DRV with 29DL32TF-70
  - GB-M968 with 29LV160DB
  - GB-M968 with M29W160EB
  - GB-M968 with MX29LV320ABTC
  - S29GL032N90T and ALTERA CPLD configured for MBC1 or MBC5
  - SD007_48BALL_64M with GL032M11BAIR4
  - SD007_48BALL_64M with M29W640
  - SD007_48BALL_64M_V2 with GL032M11BAIR4
  - SD007_48BALL_64M_V2 with M29W160ET
  - SD007_48BALL_64M_V3 with 29DL161TD-90
  - SD007_48BALL_64M_V5 with 36VF3203
  - SD007_48BALL_64M_V5 with 36VF3204
  - SD007_48BALL_64M_V6 with 36VF3204
  - SD007_48BALL_64M_V6 with 29DL163BD-90
  - SD007_48BALL_64M_V8 with M29W160ET
  - SD007_BV5 with 29LV160TE-70PFTN
  - SD007_BV5_DRV with M29W320DT
  - SD007_BV5_DRV with S29GL032M90TFIR4
  - SD007_BV5_V2 with HY29LV160TT
  - SD007_BV5_V2 with MX29LV320BTC
  - SD007_BV5_V3 with 29LV160BE-90PFTN
  - SD007_BV5_V3 with HY29LV160BT-70
  - SD007_BV5_V3 with AM29LV160MB
  - SD007_K8D3216_32M with MX29LV160CT
  - SD007_T40_64BALL_TSOP28 with TC58FVB016FT-85¹
  - SD007_TSOP_29LV017D with L017D70VC
  - SD007_TSOP_29LV017D with S29GL032M90T
  - SD007_TSOP_48BALL with 36VF3204
  - SD007_TSOP_48BALL with AM29LV160DB
  - SD007_TSOP_48BALL with K8D3216UTC
  - SD007_TSOP_48BALL with M29W160ET
  - SD007_TSOP_48BALL with L160DB12VI
  - SD007_TSOP_48BALL_V9 with 29LV160CBTC-70G
  - SD007_TSOP_48BALL_V10 with 29DL164BE-70P
  - SD007_TSOP_48BALL_V10 with 29DL32TF-70
  - SD007_TSOP_48BALL_V10 with 29LV320CTXEI
  - SD007_TSOP_48BALL_V10 with GL032M10BFIR3
  - SD007_TSOP_48BALL_V10 with M29W320DT
  - SD007_TSOP_64BALL_SOJ28 with 29DL164BE-70P
  - SD007_TSOP_64BALL_SOJ28 with unlabeled flash chip
  - SD007_TSOP_64BALL_SOP28 with EN29LV160AB-70TCP
  - SD007_TSOP_64BALL_SOP28 with unlabeled flash chip
  - SD008-6810-512S with MSP55LV512
  - SD008-6810-V4 with MX29GL256EL
  - SD008-6810-V5 with MX29CL256FH

- Game Boy Advance

  - 0121 with 0121M0Y0BE
  - 100BS6600_48BALL_V4 with 6600M0U0BE
  - 2006_TSOP_64BALL_6106 with W29GL128SH9B
  - 28F256L03B-DRV with 256L30B
  - 29LV128DBT2C-90Q and ALTERA CPLD
  - 36L0R8-39VF512 with M36L0R8060B
  - 36L0R8-39VF512 with M36L0R8060T
  - 4000L0ZBQ0 DRV with 3000L0YBQ0
  - 4350Q2 with 4050V0YBQ1
  - 4350Q2 with 4350LLYBQ2
  - 4050M0Y0Q0-39VF512 with 4050M0Y0Q0
  - 4050_4400_4000_4350_36L0R_V5 with 4050L0YTQ2
  - 4050_4400_4000_4350_36L0R_V5 with M36L0R7050T
  - 4050_4400_4000_4350_36L0R_V5 with M36L0T8060T
  - 4050_4400_4000_4350_36L0R_V5 with M36L0R8060T
  - 4400 with 4400L0ZDQ0
  - 4455_4400_4000_4350_36L0R_V3 with M36L0R7050T
  - AA1030_TSOP88BALL with M36W0R603
  - AGB-E05-01 with GL128S
  - AGB-E05-01 with MSP55LV128M
  - AGB-E05-01 with MX29GL128FHT2I-90G
  - AGB-E05-02 with JS28F128
  - AGB-E05-02 with M29W128FH
  - AGB-E05-02 with M29W128GH
  - AGB-E05-06L with 29LV128DBT2C-90Q
  - AGB-E08-09 with 29LV128DTMC-90Q
  - AGB-E20-30 with M29W128GH
  - AGB-E20-30 with S29GL256N10TFI01
  - AGB-SD-E05 with MSP55LV128
  - B104 with MSP55LV128
  - B11 with 26L6420MC-90
  - BX2006_0106_NEW with S29GL128N10TFI01
  - BX2006_TSOP_64BALL with GL128S
  - BX2006_TSOP_64BALL with GL256S
  - BX2006_TSOPBGA_0106 with M29W640GB6AZA6
  - BX2006_TSOPBGA_0106 with K8D6316UTM-PI07
  - GA-07 with unlabeled flash chip
  - GE28F128W30 with 128W30B0
  - M5M29G130AN (no PCB text)
  - M6MGJ927 (no PCB text)

Many different reproduction cartridges share their flash chip command set, so even if yours is not on this list, it may still work fine or even be auto-detected as another one. Support for more cartridges can also be added by creating external config files that include the necessary flash chip commands.

*¹ = Cannot be auto-detected, select cartridge type manually*

### Troubleshooting

* If something doesn’t work as expected, first try to clean the game cartridge contacts (best with IPA 99.9%+ on a cotton swab) and reconnect the device. An unstable cartridge connection is the most common reason for read or write errors.

* Depending on your system configuration, you may have to use `pip` and `python` commands instead of `pip3` and `python3`.

* On Linux systems, you may run into a *Permission Error* problem when trying to connect to USB devices without *sudo* privileges. To grant yourself the necessary permissions temporarily, you can run `sudo chmod 0666 /dev/ttyUSB0` (replace with actual device path) before running the app. For a permanent solution, add yourself to the usergroup that has access to serial devices by default (e.g. *dialout* on Debian-based distros; `sudo adduser $USER dialout`) and then reboot the system.

* On some Linux systems, you may need the *XCB Xinerama package* if you see an error regarding failed Qt platform plugin initialization. You can install it with `sudo apt install libxcb-xinerama0` etc. It was reported that this additional command is required on MX Linux: `sudo ln -s /usr/lib/x86_64-linux-gnu/libxcb-util.so.0.0.0 /usr/lib/x86_64-linux-gnu/libxcb-util.so.1`

* On some Linux systems like Fedora, you may need to install the `python3-pillow-qt` package manually in order for the GUI mode to work.

* If you’re using macOS version 10.13 or older, there may be no driver for the *insideGadgets GBxCart RW* device installed on your system. You can either upgrade your macOS version to 10.14+ or manually install a driver which is available [here](https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver).

* If you use Python 3.10+ and see the error `Type Error: 'PySide2.QtCore.Qt.WindowType' object cannot be interpreted as an integer` or can only use CLI mode, try to install or update the PySide2 package by running `pip3 install -U PySide2 --ignore-requires-python` or try the older [Python version 3.9.9](https://www.python.org/downloads/release/python-399/).

* If your Game Boy Camera cartridge is not reading, make sure it’s connected the correct way around; screws go up.

* For save data backup/restore on Game Boy Advance reproduction cartridges, depending on how it was built, you may have to manually select the save type for it to work properly. However, the save data backup/restore feature may not work on certain reproduction cartridges with batteryless-patched ROMs. As those cartridges use the same flash chip for both ROM and save data storage, a full ROM backup will usually include the save data. Also, when flashing a new unpatched ROM to a cartridge like this, the game may not be able to save progress without soldering in a battery. See the [Flash Cart DB website](https://flashcartdb.com/index.php/Clone_and_Repo_Cart_Problems) for more information.

## Miscellaneous

* To use your own frame around extracted Game Boy Camera pictures, place a file called `pc_frame.png` (must be at least 160×144 pixels) into the configuration directory. (GUI mode only)

## Thanks

The author would like to thank the following very kind people for their help and contributions (in alphabetical order):

- 90sFlav (flash chip info)
- AcoVanConis (bug reports, flash chip info)
- AlexiG (GBxCart RW hardware, bug reports, flash chip info)
- AndehX (app icon, flash chip info)
- antPL (flash chip info)
- bbsan (flash chip info)
- BennVenn (unlicensed mapper reverse engineering)
- ClassicOldSong (bug reports)
- crizzlycruz (flash chip info)
- Davidish (flash chip info)
- djedditt (testing)
- dyf2007 (flash chip info)
- easthighNerd (feature suggestions)
- EchelonPrime (flash chip info)
- endrift (research, mGBA emulator)
- eveningmoose (flash chip info)
- Frost Clock (flash chip info)
- Grender (testing)
- Herax (flash chip info)
- hiks (flash chip info)
- howie0210 (flash chip info, bug reports)
- iamevn (flash chip info)
- Icesythe7 (feature suggestions, testing, bug reports)
- Jayro (flash chip info)
- JFox (help with properly packaging the app for pip, Linux help)
- joyrider3774 (flash chip info)
- julgr (macOS help, testing)
- litlemoran (flash chip info)
- LovelyA72 (flash chip info)
- Luca DS (flash chip info)
- LucentW (flash chip info, testing, bug reports)
- marv17 (flash chip info, testing, bug reports, feature suggestions)
- Mr_V (flash chip info, testing)
- orangeglo (GB Memory Cartridge samples)
- paarongiroux (bug reports)
- Paradoxical (flash chip info)
- Rairch (bug reports)
- Raphaël BOICHOT (feature suggestions)
- redalchemy (bug reports)
- RetroGorek (flash chip info)
- RevZ (Linux help, testing, bug reports, flash chip info)
- Satumox (bug reports)
- Sgt.DoudouMiel (flash chip info)
- Shinichi999 (bug reports)
- Sithdown (flash chip info)
- skite2001 (flash chip info)
- Smelly-Ghost (testing)
- Super Maker (flash chip info, testing)
- t5b6_de (flash chip info)
- twitnic (flash chip info)
- Veund (flash chip info)
- Voultar (bug reports, feature suggestions)
- x7l7j8cc (flash chip info)
- Zeii (flash chip info)
- Zelante (flash chip info)

## DISCLAIMER

This software is provided as-is and the developer is not responsible for any damage that is caused by the use of it. Use at your own risk!
