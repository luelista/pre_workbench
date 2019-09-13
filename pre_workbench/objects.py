import binascii

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidgetItem

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
		self.fi_tree = None

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

	def setBytes(self, offset, newBytes):
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
	def addRange(self, r):
		self.ranges.append(r)
		if "name" in r.metadata: self.fields[r.metadata["name"]] = r


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
	RangeRole = QtCore.Qt.UserRole
	BytesOffsetRole = QtCore.Qt.UserRole+1
	BytesSizeRole = QtCore.Qt.UserRole+2
	SourceDescRole = QtCore.Qt.UserRole+3
	def __init__(self, start, end, value=None, source_desc=None, field_name=None):
		self.value=value
		self.source_desc=source_desc
		self.field_name=field_name
		self.start = start
		self.end = end
		self.bytes_size = end - start
		self.metadata = dict()
		self.style = dict()

	def addToTree(self, parent):
		me = QTreeWidgetItem(parent)
		me.setData(0, Range.RangeRole, self)
		me.setData(0, Range.BytesOffsetRole, self.start)
		me.setData(0, Range.BytesSizeRole, self.bytes_size)
		me.setData(0, Range.SourceDescRole, self.source_desc)
		me.setText(0, self.field_name)
		me.setText(1, str(self.start) + "+" + str(self.bytes_size))
		me.setText(2, str(self.source_desc))
		if type(self.value) == dict:
			me.setExpanded(True)
			for key,item in self.value.items():
				item.addToTree(me)
		elif type(self.value) == list:
			me.setExpanded(True)
			for item in self.value:
				item.addToTree(me)
		elif type(self.value) == Range:
			me.setExpanded(True)
			self.value.addToTree(me)
		else:
			me.setText(3, str(self.value))
	def __str__(self):
		return "Range[%d:%d name=%s, value=%r, desc=%r]"%(self.start,self.end,self.field_name,self.value,self.source_desc)
	def __repr__(self):
		return "Range[%d:%d name=%s, value=%r, desc=%r]"%(self.start,self.end,self.field_name,self.value,self.source_desc)
	def length(self):
		return self.bytes_size

	def contains(self, i):
		return self.start <= i < self.end

	def overlaps(self, other):
		return self.contains(other.start) or self.contains(other.end-1) or other.contains(self.start) or other.contains(self.end-1)

	def matches(self, start=None, end=None, contains=None, hasMetaKey=None, hasStyleKey=None, overlaps=None, **kw):
		if start != None and start != self.start: return False
		if end != None and end != self.end: return False
		if contains != None and not self.contains(contains): return False
		if overlaps != None and not self.overlaps(overlaps): return False
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


