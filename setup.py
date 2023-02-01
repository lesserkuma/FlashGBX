import setuptools

with open("README.md", "r", encoding="utf-8") as fh: long_description = fh.read()

setuptools.setup(
	name="FlashGBX",
	version="3.21",
	author="Lesserkuma",
	description="Reads and writes Game Boy and Game Boy Advance cartridge data. Supported hardware: GBxCart RW v1.3 and v1.4 by insideGadgets.",
	url="https://github.com/lesserkuma/FlashGBX",
	packages=setuptools.find_packages(),
	install_requires=['pyserial>=3.5', 'Pillow', 'setuptools', 'requests', 'python-dateutil'],
	extras_require={
		"qt5":["PySide2"],
		"qt6":["PySide6"]
	},
	include_package_data=True,
	classifiers=[
		"Development Status :: 5 - Production/Stable",
		"Environment :: X11 Applications :: Qt",
		"Topic :: Terminals :: Serial",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: Developers',
	],
	project_urls={
		'Source': 'https://github.com/lesserkuma/FlashGBX/',
		'Tracker': 'https://github.com/lesserkuma/FlashGBX/issues',
	},
	entry_points={
		'console_scripts': (
			'flashgbx = FlashGBX.FlashGBX:main',
		)
	},
	python_requires='>=3.7',
	long_description_content_type="text/markdown",
	long_description=long_description,
)
