
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

import errno
import logging
import os
from collections import namedtuple, defaultdict

from PyQt5.QtGui import QIcon
from appdirs import AppDirs

from pre_workbench.structinfo import xdrm
from PyQt5.QtCore import QByteArray

class SettingsSection:
	def __init__(self, sectionId,sectionTitle,subsectionId,subsectionTitle):
		self.sectionId = sectionId
		self.sectionTitle = sectionTitle
		self.subsectionId = subsectionId
		self.subsectionTitle = subsectionTitle
	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.sectionId == other.sectionId and self.subsectionId == other.subsectionId
		else:
			return False
	def __hash__(self):
		return hash(self.sectionId + "." + self.subsectionId)

class SettingsField:
	def __init__(self, id, title, fieldType, params):
		self.id = id
		self.title = title
		self.fieldType = fieldType
		self.params = params


def getValue(key, defaultValue=None):
	return configDict.get(key, defaultValue)

def registerOption(section, fieldId, title, fieldType, params, defaultValue, callback):
	id = f"{section.sectionId}.{section.subsectionId}.{fieldId}"
	field = SettingsField(id, title, fieldType, params)
	if id not in configDict:
		configDict[id] = defaultValue
	if callback:
		callback(id, configDict[id])
		configWatchers[id] = callback
	configDefinitions[section].append(field)

def setValue(key, value):
	if isinstance(value, QByteArray): value=bytes(value)
	configDict[key] = value
	saveConfig()
	if key in configWatchers: configWatchers[key](key, value)

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

def getIcon(name):
	return QIcon(respath("icons/"+name))

def respath(filename):
	return os.path.join(os.path.dirname(__file__), filename)

dirs = AppDirs("PRE-Workbench", "Weller IT", roaming=True)
mkdir_p(dirs.user_config_dir)
configFilespec = os.path.join(dirs.user_config_dir, "config.xdr")

configWatchers = dict()
configDict = dict()
configDefinitions = defaultdict(list)

def loadFromFile():
	try:
		logging.debug("Loading configuration file: %s", configFilespec)
		with open(configFilespec, "rb") as f:
			data = xdrm.loads(f.read())
			configDict.update(data)
	except:
		logging.exception(f"Unable to load config from %s, using defaults", configFilespec)


if __name__ == "__main__":
	import sys, json, binascii

	def configSerializer(obj):
		if isinstance(obj, bytes):
			return {'_bytes': binascii.hexlify(obj).decode("ascii")}
	#print(len(sys.argv), sys.argv)
	#for x in sys.argv: print(">>>"+x+"<<<")
	if len(sys.argv) == 2:
		print("value of '"+sys.argv[1]+"' = "+json.dumps(getValue(sys.argv[1]), default=configSerializer))
	elif len(sys.argv) == 3:
		val = json.loads(sys.argv[2])
		print("setting '"+sys.argv[1]+"' to ", json.dumps(val))
		setValue(sys.argv[1], val)
	else:
		print(json.dumps(configDict, indent=2, default=configSerializer))

