import xdrm
from PyQt5.QtCore import QByteArray

configDict = dict()
try:
	with open("config.xdr", "rb") as f:
		configDict = xdrm.loads(f.read())
except:
	pass

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
	with open("config.xdr", "wb") as f:
		f.write(xdrm.dumps(configDict))

