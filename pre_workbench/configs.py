
# PRE Workbench
# Copyright (C) 2019 Max Weller
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

import errno
import os

from appdirs import AppDirs

from . import xdrm
from PyQt5.QtCore import QByteArray

def getValue(key, defaultValue=None):
	return configDict.get(key,defaultValue)

def setValue(key, value):
	if isinstance(value, QByteArray): value=bytes(value)
	configDict[key] = value
	saveConfig()

def updateMru(key, value, max=5):
	mru = getValue(key, [])
	try:
		mru.remove(value)
	except ValueError:
		pass
	mru.insert(0, value)
	if len(mru) > max: mru = mru[0:max]
	setValue(key, mru)

def saveConfig():
	with open(configFilespec, "wb") as f:
		f.write(xdrm.dumps(configDict))

def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:  # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


def respath(filename):
	return os.path.join(os.path.dirname(__file__), filename)

dirs = AppDirs("PRE-Workbench", "Weller IT", roaming=True)
mkdir_p(dirs.user_config_dir)
configFilespec = os.path.join(dirs.user_config_dir, "config.xdr")

configDict = dict()
try:
	with open(configFilespec, "rb") as f:
		configDict = xdrm.loads(f.read())
except:
	pass


