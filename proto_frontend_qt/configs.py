import xdrm

configDict = dict()
try:
	with open("config.xdr", "rb") as f:
		configDict = xdrm.loads(f.read())
except:
	pass


def getValue(key, defaultValue=None):
	return configDict.get(key,defaultValue)

def setValue(key, value):
	configDict[key] = value
	saveConfig()

def saveConfig():
	with open("config.xdr", "wb") as f:
		f.write(xdrm.dumps(configDict))

