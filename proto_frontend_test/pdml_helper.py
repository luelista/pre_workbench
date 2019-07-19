from xml.etree.ElementTree import XMLParser

class PdmlConvertParser:
	def __init__(self):
		self.stack=[({}, [])]
	def start(self,tag,attrib):
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


