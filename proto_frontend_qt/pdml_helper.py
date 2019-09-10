from xml.etree.ElementTree import XMLParser
import binascii, os, shutil
from objects import ByteBuffer

class PdmlToPacketListParser:
	def __init__(self, destPacketList):
		#self.interface = interface
		self.destination = destPacketList
		self.cur_proto = None
		self.parser=XMLParser(target=self)

	def feed(self, data):
		self.parser.feed(data)
		
	def start(self,tag,attrib):
		#print("start",tag,attrib)
		if tag == "pdml":
			self.destination.metadata.update(attrib)
			return

		if tag == "packet":
			self.next_packet = ByteBuffer()
			self.cur_proto = None

		if tag == "proto":
			self.cur_proto = attrib["name"]
			#self.next_packet.setBytes(int(attrib['pos']), int(attrib["size"]), {"section":}, None)
			#print(attrib)
			if "showname" in attrib: attrib["section"] = attrib["showname"]

		if self.cur_proto == "geninfo": # ignore all geninfo fields, they contain mostly bullshit
			return

		if self.cur_proto == "frame": # put frame metadata in the metadata dict
			if tag == "field":
				self.next_packet.metadata[attrib["name"]] = attrib["show"]
			return

		if 'pos' in attrib and "size" in attrib:
			pos = int(attrib['pos'])
			size = int(attrib['size'])
			del attrib['pos']
			del attrib['size']
			if "value" in attrib and len(attrib["value"]) == size * 2:
				#try:
					self.next_packet.setBytes(pos, binascii.unhexlify(attrib["value"]), None, None)
					del attrib['value']
				#except:
				#	pass
			self.next_packet.setBytes(pos, size, attrib, None)




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
