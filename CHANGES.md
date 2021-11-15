# Release notes
### v3.0 (released 2021-11-15)
- Added support for the GBxCart RW v1.4a hardware revision
- Bundles GBxCart RW v1.4 firmware version R32+L3 (improves ROM writing speed for Development AGB Cartridge 256M Flash S, E201868)
- Added support for 0883_DRV with ES29LV160ET *(thanks RetroGorek)*
- Confirmed support for 2006_TSOP_64BALL_QFP48 with AL016J55FFAR2 *(thanks Sithdown)*
- Added support for GB-CART32K-A with SST39SF020A *(thanks Icesythe7)*
- Added support for 29LV Series Flash BOY with 29LV160DB *(thanks Luca DS)*
- Fixed a bug with reading ROMs of HuC-1 cartridges *(thanks Satumox)*
- When writing a save data file that is smaller than the selected save type suggests, repeats of the data will now be written instead of blank data; this can be useful for games like „Pokémon Pinball“ on a flash cartridge with larger SRAM/FRAM than required
- Confirmed support for SD007_TSOP_64BALL_SOP28 with unlabeled flash chip *(thanks marv17)*
- Added support for SD007_TSOP_64BALL_SOP28 with EN29LV160AB-70TCP *(thanks marv17)*
- Added support for SD007_TSOP_48BALL_V10 with 29DL32TF-70
- Improved the auto-detection of flash cartridges
- Fixed the auto-adjustment of Real Time Clock register values as the day counter was inaccurate
- Added the detection of a cartridge’s actual save type (requires save data to be present)

### v2.8 (released 2021-09-05)
- Added an option to fix wrong header checksums when writing a ROM *(thanks Voultar for the suggestion)*
- Fixed a bug with the auto-detect feature *(thanks Voultar)*
- Fixed the save data size detection of the Classic NES Series and Famicom Mini game cartridges for Game Boy Advance

### v2.7 (released 2021-09-02)
- Added support for AGB-E20-30 with M29W128GH *(thanks hiks)*
- Added support for SD007_TSOP_48BALL_V9 with 29LV160CBTC-70G *(thanks marv17)*
- Fixed a bug with parsing an invalid settings.ini *(thanks Rairch)*
- Added the image that was last seen by the GB Camera Sensor to the GB Camera Album Viewer *(thanks Raphaël BOICHOT for the suggestion)*

### v2.6 (released 2021-08-09)
- Bundles GBxCart RW v1.4 firmware version R31+L2 (fixes a very rare bug with SRAM access on Game Boy cartridges)
- Added a firmware updater for GBxCart v1.4 devices
- Configuration path bug fix for systems that do not support PySide2 *(thanks JFox)*
- Added support for S29GL032N90T and ALTERA CPLD (configured for MBC1) *(thanks t5b6_de)*
- Flashing rumble enabled Game Boy Advance flash cartridges by insideGadgets is no longer noisy *(thanks AlexiG)*
- Confirmed support for DMG-GBRW-20 with 29LV320ETMI-70G
- Confirmed support for AGB-E20-30 with S29GL256N10TFI01
- Minor bug fixes with the firmware updater *(thanks marv17)*

### v2.5 (released 2021-07-15)
- Added support for 4350Q2 with 4050V0YBQ1 *(thanks Shinichi999)*
- Fixed Real Time Clock register access for MBC3B and MBC30 cartridges on the GBxCart RW v1.4 hardware
- Added support for SD007_BV5 with 29LV160TE-70PFTN *(thanks RetroGorek)*

### v2.4 (released 2021-06-20)
- Added support for 4050_4400_4000_4350_36L0R_6108 with M36L0R7050B *(thanks Jayro)*
- Added support for AGB-E05-02 with JS28F128 *(thanks marv17)*
- Confirmed support for SD007_TSOP_48BALL_V9 with 29LV320CBTC-70G *(thanks AcoVanConis)*
- Fixed a bug when running FlashGBX without GUI support, the command line interface mode will now launch without extra parameters again *(thanks howie0210)*

### v2.3 (released 2021-06-08)
- Added support for AGB-E05-06L with 29LV128DBT2C-90Q *(thanks marv17)*
- Nintendo Power GB Memory Cartridges will now be unlocked properly even if they’re stuck in erase mode *(thanks Grender for testing)*
- Confirmed support for SD007_TSOP_48BALL_V10 with GL032M10BFIR3 *(thanks Mr_V)*
- Added support for 2006_TSOP_64BALL_6106 with W29GL128SH9B *(thanks marv17)*
- Fixed support for insideGadgets 1 MB, 128 KB SRAM *(thanks AlexiG)*
- The [setup package](https://github.com/lesserkuma/FlashGBX/releases) now includes the CH341 USB serial driver for insideGadgets GBxCart RW devices

### v2.2 (released 2021-06-03)
- Added support for insideGadgets 2 MB, 32 KB FRAM, v1.0 *(thanks t5b6_de)*
- Added support for SD007_TSOP_29LV017D with M29W320DT *(thanks marv17)*
- Added support for SD007_TSOP_29LV017D with S29GL032M90T *(thanks marv17)*
- Fixed detection of Classic NES Series and Famicom Mini game cartridges for Game Boy Advance *(thanks LucentW)*
- Added support for 29LV128DBT2C-90Q and ALTERA CPLD (configured for MBC5) *(thanks Sgt.DoudouMiel)*
- Added support for 0121 with 0121M0Y0BE *(thanks RetroGorek)*
- Fixed detection of Pocket Monsters Ruby v1.1 (AGB-AXVJ-JPN) and Pocket Monsters Sapphire v1.1 (AGB-AXPJ-JPN) genuine game cartridges *(thanks Icesythe7)*
- Fixed flash chip query for flash cartridges that have no CFI data but swapped pins *(thanks marv17)*
- Added support for M5M29G130AN (no PCB text) *(thanks Mr_V)*
- Added support for GA-07 with unlabeled flash chip *(thanks Mr_V)*
- Added support for SD007_TSOP_48BALL_V10 with M29W320DT *(thanks Jayro)*
- Fixed a problem of reading from a certain type of cartridge that uses the GL256S flash chip *(thanks marv17)*
- Added support for B11 with 26L6420MC-90 *(thanks dyf2007)*
- Added support for a DIY cart with MBC3 and MX29LV640 *(thanks eveningmoose)*

### v2.1 (released 2021-05-05)
- Fixed support for SD007_TSOP_29LV017D with L017D70VC *(thanks marv17 and 90sFlav)*
- Added support for a DIY cart with MBC1 and AM29F080 *(thanks skite2001)*
- Added support for SD007_TSOP_48BALL_V8 with 29LV320CTTC *(thanks Jayro)*
- Added the MBC5+SRAM mapper type which is officially unused, but is actually used by GB Studio *(thanks Jayro)*
- The GBxCart RW v1.3 firmware updater should now also work if the device is below firmware version R19
- Adjusted the baudrate used for updating the firmware which fixes a problem on some macOS systems
- Added support for Flash2Advance Ultra 64M with 2× 28F320C3B
- Confirmed support for 4350Q2 with 4350LLYBQ2

### v2.0 (released 2021-05-01)
- Added an integrated firmware updater for GBxCart v1.3 devices which includes the latest official firmware version at time of FlashGBX release; also supports external firmware files
- Added support for the new GBxCart RW v1.4 hardware
- Created a custom high compatibility firmware for GBxCart v1.3 and v1.4 devices, completely written from scratch
  - Version L1 for GBxCart RW v1.3
    - Works with all officially released Game Boy and Game Boy Advance cartridges including those with rare mappers, except cartridges that use memory cards and other external peripherals
    - Supported mappers: MBC1, MBC2, MBC3, MBC30, MBC5, MBC6, MBC7, MBC1M, MMM01, GBD (Game Boy Camera), G-MMC1 (GB Memory), M161, HuC-1, HuC-3, TAMA5, DACS, 3D Memory (GBA Video)
    - Enables support for a few more reproduction and flash cartridges including:
      - 4050M0Y0Q0-39VF512 with 4050M0Y0Q0
      - Development AGB Cartridge 128M Flash S, E201850
      - Development AGB Cartridge 256M Flash S, E201868
      - Flash2Advance 256M (non-Ultra)
    - Faster transfer rates for most operations
    - Currently only supported by FlashGBX, not supported by official interface software
    - Available through the integrated Firmware Updater
    - It’s possible to return to the official firmware at any time using FlashGBX or the official firmware updater
  - Version L1 for GBxCart v1.4
    - Same as above but already integrated into the official firmware of GBxCart RW v1.4
- Added support for official cartridges with the MBC6 memory bank controller including its flash memory; tested with “Net de Get: Minigame @ 100” (CGB-BMVJ-JPN) *(thanks to endrift’s research at [gbdev](https://gbdev.gg8.se/forums/viewtopic.php?id=544))* (requires GBxCart RW firmware version L1+)
- Previously preliminarily added mapper support including for MBC7 and GBA Video cartridges is now working (requires GBxCart RW firmware version L1+)
- Added support for writing compilation ROMs to Nintendo Power GB Memory Cartridges (DMG-MMSA-JPN); requires a .map file in the same directory as the ROM file; all this can be generated using orangeglo’s [GBNP ROM builder website](https://orangeglo.github.io/gbnp/index.html)
- Confirmed support for GB-M968 with 29LV160DB *(thanks bbsan)*
- Added support for ROM backup as well as save data backup and restore for 8M FLASH DACS cartridges; tested with “Hikaru no Go 3 – Joy Carry Cartridge” (AGB-GHTJ-JPN)
- Confirmed support for SD007_TSOP_29LV017D with L017D70VC *(thanks marv17)*
- Added support for 100BS6600_48BALL_V4 with 6600M0U0BE (the “369IN1” cartridge) *(thanks to BennVenn’s research on Discord)*
- Removed broken support for saving and restoring RTC registers of official TAMA5 cartridges inside the save file as it became clear that the year value was not correctly written; more research needed
- Support for optionally saving RTC registers of official Game Boy Advance cartridges inside the save file was added, however currently no emulator has support for synchronizing the clock
- Added an option for updating the RTC values (like the clock was running in the background) when restoring a save data file that has these values stored inside

### v1.4.2 (released 2021-03-17)
- Confirmed support for SD007_48BALL_64M_V8 with M29W160ET *(thanks marv17)*
- Fixed minor bugs

### v1.4.1 (released 2021-03-15)
- Added ROM and map backup support for official Nintendo Power GB Memory cartridges (DMG-MMSA-JPN); save data handling and ROM writing is not supported yet
- Added preliminary support for 4050M0Y0Q0-39VF512 with 4050M0Y0Q0 (requires a future firmware update of GBxCart RW)
- Added preliminary support for official cartridges with the MBC7 memory bank controller; tested with “Korokoro Kirby” (CGB-KKKJ-JPN) (requires a future firmware update of GBxCart RW)
- Added support for official cartridges with the M161 memory bank controller; tested with “Mani 4 in 1: Tetris + Alleyway + Yakuman + Tennis” (DMG-601CHN) (requires GBxCart RW firmware R26 or newer)
- Added support for B104 with MSP55LV128 *(thanks Zelante)*
- Added save data backup and restore support for official cartridges with ATMEL AT29LV512 flash chips; tested with a copy of “Mario Kart: Super Circuit” (AGB-AMKP-EUR)

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

### v1.3 (released 2021-01-21)
- Fixed a bug introduced in v1.1 that broke support for AGB-E08-09 with 29LV128DTMC-90Q *(thanks LucentW for reporting)*
- Will now show the application’s version number in message boxes

### v1.2.1 (released 2021-01-16)
- Fixed a bug introduced in v1.1 that broke MBC3 handling *(thanks marv17 for reporting)*
- Will now default back to 5V for Game Boy cartridges after unsuccessful flash chip auto-detection
- Added support for DIY carts with the AT49F040 flash chip *(thanks howie0210)*
- Minor bug fixes

### v1.1 (released 2021-01-11)
- Added support for GE28F128W30 with 128W30B0 *(thanks bbsan)*
- Added support for BX2006_TSOP_64BALL with GL256S *(thanks Paradoxical)*
- Confirmed support for SD007_48BALL_64M_V2 with M29W160ET *(thanks Paradoxical)*
- Added support for M6MGJ927 (no PCB text) *(thanks Super Maker)*
- Added a warning for very old reproduction cartridges with DRM that show “YJencrypted” as their game title *(thanks Super Maker)*
- Added a firmware check when writing to cartridges with flash chips manufactured by Sharp (unsupported by GBxCart RW firmware R25)
- Added optional verification of written data after ROM flashing *(thanks marv17 for the suggestion)*

### v1.0 (released 2021-01-01)
- Added a firmware check when writing to insideGadgets Game Boy Advance flash cartridges (requires GBxCart RW firmware R20 or newer)
- Confirmed support for Mr Flash 64M (rebranded BUNG Doctor GB Card 64M)
- Fixed a problem with writing to the insideGadgets 512 KB Game Boy flash cartridge

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
- Added support for SD007_BV5_DRV with M29W320DT *(thanks Frost Clock)*
- Added experimental *Fast Read Mode* support for GBxCart RW with firmware R19+; can be up to 20% faster, but the functioning currently heavily relies on system performance and drivers
- Bumped the required minimum firmware version of GBxCart RW to R19
- Confirmed support for 4050_4400_4000_4350_36L0R_V5 with M36L0R7050T
- Added the option to enable the preference of sector erase over chip erase when flashing a ROM; this can improve flashing speed for ROMs smaller than the flash chip capacity
- Some flash chips may have reversed sectors despite shared flash ID; if you think your cartridge is affected, you can add `"sector_reversal":true,` to its config file for a prompt upon flashing
- Renamed config.ini to settings.ini to avoid confusion with the term “config file”

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
