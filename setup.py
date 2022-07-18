
# PRE Workbench
# Copyright (C) 2022 Mira Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import setuptools
from Cython.Build import cythonize

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
	name='pre_workbench',
	author="Mira Weller",
	author_email="mweller@seemoo.tu-darmstadt.de",
	description="Protocol Reverse Engineering Workbench",
	long_description=long_description,
	long_description_content_type="text/markdown",
	include_package_data=True,
	url="https://github.com/pre-workbench",
	packages=setuptools.find_packages(),
	entry_points={
		'console_scripts': ['prewb_c=pre_workbench.app:run_app', 'prewb_parse=pre_workbench.structinfo.cli:run_cli', 'prewb_codegen=pre_workbench.wdgen.cli'],
		'gui_scripts': ['prewb=pre_workbench.app:run_app',],
	},
	install_requires=[
		'PyQt5>=5.11.3',
		'appdirs>=1.4.3',
		'QScintilla>=2.11.2',
		'lark-parser>=0.7.5',
		'psutil>=5.0.0',
		'bitstring>=3.1.9',
		'PyQtAds>=3.8.1',
		'darkdetect==0.6.0',
		'PyYAML>=6.0',
	],
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
		"Topic :: System :: Networking",
		"Environment :: X11 Applications :: Qt",
		"Operating System :: OS Independent",
	],
	ext_modules = cythonize("pre_workbench/algo/*.pyx"),
)
