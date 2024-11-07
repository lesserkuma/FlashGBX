# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
	['run.py'],
	pathex=[],
	binaries=[('FlashGBX/res/icon.ico', 'res')],
	datas=[],
	hiddenimports=[],
	hookspath=[],
	hooksconfig={},
	runtime_hooks=[],
	excludes=[],
	noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
	pyz,
	a.scripts,
	[],
	exclude_binaries=True,
	name='FlashGBX',
	debug=False,
	bootloader_ignore_signals=False,
	strip=False,
	upx=True,
	console=True,
	icon=['FlashGBX/res/icon.ico'],
)
coll = COLLECT(
	exe,
	a.binaries,
	a.datas,
	strip=False,
	upx=True,
	upx_exclude=[],
	name='FlashGBX',
)
info_plist = {
	'CFBundleName': 'FlashGBX',
	'CFBundleDisplayName': 'FlashGBX',
	'CFBundleGetInfoString': 'Interface software for GB/GBC/GBA cart readers',
	'CFBundleShortVersionString': '<APP_VERSION>',
	'CFBundleIdentifier': 'com.lesserkuma.FlashGBX',
}
app = BUNDLE(
	coll,
	name='FlashGBX.app',
	icon='FlashGBX/res/icon.ico',
	bundle_identifier='com.lesserkuma.FlashGBX',
	info_plist=info_plist,
)
