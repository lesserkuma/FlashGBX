import setuptools

with open("README.md", "r", encoding="utf-8") as fh: long_description = fh.read()

setuptools.setup(
	name="FlashGBX",
	version="0.8b0",
	author="Lesserkuma",
	description="A GUI application that can read and write Game Boy and Game Boy Advance cartridge data. Currently supports the GBxCart RW hardware device by insideGadgets.",
	url="https://github.com/lesserkuma/FlashGBX",
	packages=setuptools.find_packages(),
	install_requires=['PySide2', 'pyserial'],
	include_package_data=True,
	classifiers=[
		"Development Status :: 4 - Beta",
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
