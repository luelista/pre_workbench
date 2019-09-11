import errno
import os

from appdirs import AppDirs

import xdrm
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


dirs = AppDirs("PRE-Workbench", "Weller IT", roaming=True)
mkdir_p(dirs.user_config_dir)
configFilespec = os.path.join(dirs.user_config_dir, "config.xdr")

configDict = dict()
try:
	with open(configFilespec, "rb") as f:
		configDict = xdrm.loads(f.read())
except:
	pass


