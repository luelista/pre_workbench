from xml.etree.ElementTree import XMLParser
import binascii, os, shutil
from objects import ByteBuffer

class PdmlToPacketListParser:
	def __init__(self, destPacketList):
		#self.interface = interface
		self.destination = destPacketList
		
		
	def start(self,tag,attrib):
		#print("start",tag,attrib)
		if tag == "pdml":
			self.destination.metadata.update(attrib)
			return

		if tag == "packet":
			self.next_packet = ByteBuffer()

		for numattr in ('pos','size'):
			if numattr in attrib: attrib[numattr] = int(attrib[numattr])
		if "value" in attrib and "size" in attrib and len(attrib["value"]) == attrib["size"] * 2:
			try:
				attrib["value"] = binascii.unhexlify(attrib["value"])
				self.next_packet.setBytes(attrib['pos'], attrib["value"], None, None)
			except:
				pass
		if 'pos' in attrib:
			self.next_packet.setBytes(attrib['pos'], attrib["size"], attrib, None)

	def end(self,tag):
		if tag == "packet":
			self.destination.add(self.next_packet)
			self.next_packet = None
		

	def data(self, data):
		pass            # We do not need to do anything with data.
	def close(self):
		#return self.stack[0][1]
		pass


def convertPdmlToPacketList(pdmlString, destPacketList):
	target=PdmlToPacketListParser(destPacketList)
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
