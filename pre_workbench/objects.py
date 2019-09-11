import binascii

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
	def __init__(self, buf=None, metadata=None):
		super().__init__()
		self.metadata = dict() if metadata is None else metadata
		self.setContent(buf)
		self.ranges = list()
		self.fields = dict()

	def setContent(self, buf):
		if buf is None:
			self.buffer = bytearray()
		else:
			self.buffer = bytearray(buf)
		self.length = len(self.buffer)

	def ensureCapacity(self, newLength):
		if self.length < newLength:
			self.buffer = self.buffer + (newLength - self.length) * b"\0"
			self.length = len(self.buffer)

	def setBytes(self, offset, newBytes, meta, style):
		if type(newBytes) == bytes:
			n = len(newBytes)
			self.ensureCapacity(offset + n)
			#for i in range(n):
			#	self.buffer[offset + i] = newBytes[i]
			self.buffer[offset:offset+n] = newBytes
		elif type(newBytes) == int:
			n = newBytes
			self.ensureCapacity(offset + n)
		else:
			raise TypeError("newBytes must be of type 'bytes' or 'int'")
		#print(offset,n,meta,style)
		if meta != None or style != None:
			r = Range(offset, offset+n-1)
			if meta != None: r.metadata = meta
			if style != None: r.style = style
			self.ranges.append(r)
			if "name" in meta: self.fields[meta["name"]] = r


	def getByte(self, i):
		return self.buffer[i]
	def getBytes(self,offset, length):
		return self.buffer[offset:offset+length]
	def getDecoded(self,offset, structUnpackFormat):
		return struct.unpack_from(structUnpackFormat, self.buffer, offset)


	def getAnnotationValues(self, contains=None, start=None, annotationProperty=None):
		# TODO check whether a more efficient algorithm needs to be used
		values = []
		for rr in self.ranges:
			if rr.matches(contains=contains, start=start, hasMetaKey=annotationProperty):
				values.append(rr.metadata[annotationProperty])
		return values

	def matchRanges(self, **match):
		# TODO check whether a more efficient algorithm needs to be used
		values = []
		for rr in self.ranges:
			if rr.matches(**match):
				values.append(rr)
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
	
	def toHexDump(self, offset=0, length=None):
		if length==None:
			b=self.buffer[offset:]
		else:
			b=self.buffer[offset:offset+length]
		return hexdump.hexdump(b, result='return')
	def toHex(self, offset=0, length=None, joiner="", format="%02x"):
		if length==None:
			b=self.buffer[offset:]
		else:
			b=self.buffer[offset:offset+length]
		return joiner.join(format % c for c in b)

class Range:
	def __init__(self, start, end):
		self.start = start
		self.end = end
		self.metadata = dict()
		self.style = dict()
	def length(self):
		return self.end - self.start + 1
	def contains(self, i):
		return i >= self.start and i <= self.end
	def matches(self, start=None, end=None, contains=None, hasMetaKey=None, hasStyleKey=None, overlaps=None, **kw):
		if start != None and start != self.start: return False
		if end != None and end != self.end: return False
		if contains != None and not self.contains(contains): return False
		if overlaps != None and not (self.contains(overlaps.start) or self.contains(overlaps.end) or overlaps.contains(self.start) or overlaps.contains(self.end)): return False
		if hasMetaKey != None and not hasMetaKey in self.metadata: return False
		if hasStyleKey != None and not hasStyleKey in self.style: return False
		for k,v in kw.items():
			if self.metadata.get(k) == v: continue
			if self.style.get(k) == v: continue
			return False
		return True


class ByteBufferList(QObject):
	on_new_packet = pyqtSignal(int)
	
	def __init__(self):
		super().__init__()
		self.metadata = dict()
		self.buffers = list()
		self.updating = None
	def add(self, bbuf):
		self.buffers.append(bbuf)
		if self.updating is None:
			self.on_new_packet.emit(1)
		else:
			self.updating += 1
	def beginUpdate(self):
		if self.updating is not None: raise AssertionError("endUpdate called while in update")
		self.updating = 0
	def endUpdate(self):
		if self.updating is None: raise AssertionError("endUpdate called while not in update")
		self.on_new_packet.emit(self.updating)
		self.updating = None
	def __len__(self):
		return len(self.buffers)

	def getAllKeys(self, metadataKeys=True, fieldKeys=True):
		s = set()
		for bbuf in self.buffers:
			if metadataKeys: s.update(bbuf.metadata.keys())
			if fieldKeys: s.update(bbuf.fields.keys())
		return s
	



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


