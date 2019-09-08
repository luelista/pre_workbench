from xml.etree.ElementTree import XMLParser
import binascii, os, shutil

class PdmlConvertParser:
	def __init__(self):
		self.stack=[({}, [])]
	def start(self,tag,attrib):
		if "value" in attrib and "size" in attrib and len(attrib["value"]) == int(attrib["size"]) * 2:
			try:
				attrib["value"] = binascii.unhexlify(attrib["value"])
			except:
				pass
		for numattr in ('pos','size'):
			if numattr in attrib: attrib[numattr] = int(attrib[numattr])
		item=(attrib, [])
		self.stack.append(item)
	def end(self,tag):
		item=self.stack.pop()
		self.stack[-1][1].append(item)
	def data(self, data):
		pass            # We do not need to do anything with data.
	def close(self):
		return self.stack[0][1]


def convertPdmlToPacketTree(pdmlString):
	target=PdmlConvertParser()
	parser=XMLParser(target=target)
	parser.feed(pdmlString)
	return parser.close()

def findTshark():
	if os.path.isfile("C:\\Program Files\\Wireshark\\tshark.exe"):
		return "C:\\Program Files\\Wireshark\\tshark.exe"
	else:
		path=shutil.which("tshark")
		if path == None:
			raise FileNotFoundError("tshark executable not found. please install wireshark and place tshark in path")
		return path
