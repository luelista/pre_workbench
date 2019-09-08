import hexdump, struct
from PyQt5.QtCore import (Qt, pyqtSignal, QObject)

class ReloadRequired(Exception):
	pass

class ByteBuffer(QObject):
	"""
- dict<string,string> metadata
- byte[] buffer
- int length
- dict<string,(number,number)> ranges
- dict<string,field> fields
    field = ()
	"""
	on_new_data = pyqtSignal()
	def __init__(self, buf=None):
		super().__init__()
		self.metadata = dict()
		self.setContent(buf)
		self.ranges = list()
		self.fields = dict()

	def setContent(self, buf):
		if buf is None:
			self.buffer = bytes()
		else:
			self.buffer = buf
		self.length = len(self.buffer)

	def getByte(self, i):
		return self.buffer[i]
	def getBytes(offset, length):
		return self.buffer[i:i+length]
	def getDecoded(offset, structUnpackFormat):
		return struct.unpack_from(structUnpackFormat, self.buffer, offset)

	def getAnnotations(self, i, annotationProperty):
		if i >= self.length: return []

		# TODO check whether a more efficient algorithm needs to be used
		values = []
		for rr in self.ranges:
			if rr.contains(i) and annotationProperty in rr.metadata:
				values.append(rr.metadata[annotationProperty])
		return values

	def getStyle(self, i, styleName, defaultValue):
		for rr in self.ranges:
			if rr.contains(i) and styleName in rr.style:
				return rr.style[styleName]
		return defaultValue

	def __len__(self):
		return self.length
	
	def split_on_delimiter(self, delim):
		bufs = self.buffer.split(delim)
		lst = ByteBufferList()
		lst.metadata = self.metadata
		for buf in bufs:
			lst.add(ByteBuffer(buf))
	
	def toHexDump(self):
		return hexdump.hexdump(self.buffer, result='return')

class Range:
	def __init__(self):
		self.start = 0
		self.end = 0
		self.metadata = dict()
		self.style = dict()
	def contains(self, i):
		return i >= self.start and i <= self.end

class ByteBufferList(QObject):
	on_new_packet = pyqtSignal()
	
	def __init__(self):
		super().__init__()
		self.metadata = dict()
		self.buffers = list()
	def add(self, bbuf):
		self.buffers.append(bbuf)
		self.on_new_packet.emit()
	



class BidiByteBuffer:
	def __init__(self, up, down):
		self.up = up
		self.down = down
	def merged(self):
		buf = ByteBuffer()
		# pseudo-code:
		# for range in sorted(self.up.split_by_tag_value("timestamp") + self.down.split_by_tag_value("timestamp"))
		#   buf.append_buffer(range)
		return buf


#load_pcap_file(file) / parse_pcap(byteBuffer)
#split_on_delimiter(byteBuffer, delim)
#split_by_length_prefix(packSpec, (meta_names), )
#merge_lists_of_byteBuffer(list_of_byteBufer, ...)
#concat_lists_of_byteBuffer(list_of_byteBufer, ...)


