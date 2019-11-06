
# PRE Workbench
# Copyright (C) 2019 Max Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import binascii
import re, struct
from math import ceil, floor

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidgetItem

from pre_workbench import hexdump
from PyQt5.QtCore import (Qt, pyqtSignal, QObject)

from pre_workbench.guihelper import getClipboardText


class ReloadRequired(Exception):
	pass


class RangeList:
	def __init__(self, totalLength, ranges, chunkSize=1024):
		self.ranges = ranges
		self.chunkCount = totalLength // chunkSize + 1
		self.chunkSize = chunkSize
		self.chunks = [[] for i in range(self.chunkCount)]
		for el in ranges:
			firstChunk = el.start // chunkSize
			lastChunk = el.end // chunkSize
			for i in range(firstChunk, lastChunk+1):
				self.chunks[i].append(el)

	def findMatchingRanges(self, start=None, end=None, contains=None, overlaps=None, **kw):
		scanChunk = None
		if start is not None:
			scanChunk = start // self.chunkSize
		elif end is not None:
			scanChunk = end // self.chunkSize
		elif contains is not None:
			scanChunk = contains // self.chunkSize
		elif overlaps is not None:
			firstChunk = overlaps.start // self.chunkSize
			lastChunk = overlaps.end // self.chunkSize
			if firstChunk == lastChunk:
				scanChunk = firstChunk

		if scanChunk is not None:
			if scanChunk >= self.chunkCount: return
			for el in self.chunks[scanChunk]:
				if el.matches(start=start, end=end, contains=contains, overlaps=overlaps, **kw):
					yield el
		else:
			for el in self.ranges:
				if el.matches(start=start, end=end, contains=contains, overlaps=overlaps, **kw):
					yield el

	def __len__(self):
		return len(self.ranges)

	def append(self, el):
		firstChunk = el.start // self.chunkSize
		lastChunk = el.end // self.chunkSize
		while lastChunk >= self.chunkCount:
			self.chunks.append(list())
			self.chunkCount += 1
		for i in range(firstChunk, lastChunk+1):
			self.chunks[i].append(el)
		self.ranges.append(el)


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
		self.ranges = RangeList(len(self), list())
		self.fields = dict()
		self.fi_tree = None
		self.fi_container = None

	def setContent(self, buf):
		if buf is None:
			self.buffer = bytearray()
		else:
			if isinstance(buf, ByteBuffer):
				buf = buf.buffer
			self.buffer = bytearray(buf)
		self.length = len(self.buffer)

	def ensureCapacity(self, newLength):
		if self.length < newLength:
			self.buffer = self.buffer + (newLength - self.length) * b"\0"
			self.length = len(self.buffer)

	def reassemble(self, databytes, datameta):
		if 'offset' in datameta:
			self.setBytes(datameta['offset'], databytes)
			self.addRange(Range(datameta['offset'], datameta['offset']+len(databytes), meta=datameta))
		else:
			self.appendBytes(databytes, datameta)

	def setBytes(self, offset, newBytes):
		if isinstance(newBytes, ByteBuffer):
			newBytes = newBytes.buffer
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
			raise TypeError("newBytes must be of type 'bytes' or 'int' or 'ByteBuffer'")
	def addRange(self, r):
		self.ranges.append(r)
		if "name" in r.metadata: self.fields[r.metadata["name"]] = r
		return r
	def clearRanges(self):
		self.ranges = RangeList(len(self), list())

	def appendBytes(self, newBytes, meta=None):
		start = len(self)
		self.setBytes(len(self), newBytes)
		end = len(self)
		if meta:
			return self.addRange(Range(start, end, meta=meta))

	def getByte(self, i):
		return self.buffer[i]
	def getBytes(self,offset, length):
		return self.buffer[offset:offset+length]
	def getDecoded(self,offset, structUnpackFormat):
		return struct.unpack_from(structUnpackFormat, self.buffer, offset)
	def getInt(self, offset, end, endianness='>',signed=False):
		return int.from_bytes(self.buffer[offset:end], byteorder='big' if endianness == '>' else 'little', signed=signed)

	def getAnnotationValues(self, contains=None, start=None, annotationProperty=None):
		# TODO use a more efficient algorithm!
		values = []
		for rr in self.ranges.findMatchingRanges(contains=contains, start=start, hasMetaKey=annotationProperty):
			values.append(rr.metadata[annotationProperty])
		return values

	def matchRanges(self, **match):
		return self.ranges.findMatchingRanges(**match)

	def getStyle(self, i, styleName, defaultValue):
		for rr in self.ranges.findMatchingRanges(contains=i, hasMetaKey=styleName):
			return rr.metadata[styleName]
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


	def parse_from_hexdump(dmp):
		bbuf = ByteBuffer()
		for line in dmp.split("\n"):
			if line.strip()=="": continue
			bbuf.appendBytes(binascii.unhexlify(re.match("^\s*[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{2} {0,2})+)", line).group(1).replace(" ","")))
		return bbuf


class Range:
	RangeRole = QtCore.Qt.UserRole
	BytesOffsetRole = QtCore.Qt.UserRole+1
	BytesSizeRole = QtCore.Qt.UserRole+2
	SourceDescRole = QtCore.Qt.UserRole+3
	def __init__(self, start, end, value=None, source_desc=None, field_name=None, meta=None, buffer_idx=0):
		self.value=value
		self.source_desc=source_desc
		self.field_name=field_name
		self.start = start
		self.end = end
		self.bytes_size = end - start
		self.metadata = dict()
		self.buffer_idx = buffer_idx
		if meta: self.metadata.update(meta)
		self.style = dict()

	def addToTree(self, parent):
		me = QTreeWidgetItem(parent)
		theRange = self
		me.setData(0, Range.RangeRole, theRange)
		me.setData(0, Range.BytesOffsetRole, theRange.start)
		me.setData(0, Range.BytesSizeRole, theRange.bytes_size)
		me.setData(0, Range.SourceDescRole, theRange.source_desc)
		text0 = theRange.field_name
		text1 = str(theRange.start) + "+" + str(theRange.bytes_size)
		text2 = str(theRange.source_desc)
		while type(theRange.value) == Range:
			theRange = theRange.value
			me.setData(0, Range.SourceDescRole, theRange.source_desc)
			text0 += " >> "+theRange.field_name
			text1 += " >> "+str(theRange.start) + "+" + str(theRange.bytes_size)
			text2 += " >> "+str(theRange.source_desc)
		me.setText(0, text0)
		me.setText(1, text1)
		me.setText(2, text2)
		if type(theRange.value) == dict:
			me.setExpanded(True)
			for key,item in theRange.value.items():
				item.addToTree(me)
		elif type(theRange.value) == list:
			me.setExpanded(True)
			for item in theRange.value:
				item.addToTree(me)
		else:
			formatter = theRange.source_desc.formatter if theRange.source_desc is not None else str
			me.setText(3, formatter(theRange.value))
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
		self.buffers_hash = dict()
		self.updating = None
	def add(self, bbuf):
		self.buffers.append(bbuf)
		if self.updating is None:
			self.on_new_packet.emit(1)
		else:
			self.updating += 1

	def reassemble(self, subflow_key, bufmeta, databytes, datameta):
		if subflow_key not in self.buffers_hash:
			print("Starting new buffer for key",subflow_key)
			bbuf = ByteBuffer(metadata=bufmeta)
			self.buffers_hash[subflow_key] = bbuf
			self.add(bbuf)
		self.buffers_hash[subflow_key].reassemble(databytes, datameta)

	def beginUpdate(self):
		if self.updating is not None: raise AssertionError("beginUpdate called while in update")
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
	UP = 0
	DOWN = 1
	def __init__(self, up=None, down=None):
		self.up = ByteBuffer() if up is None else up
		self.down = ByteBuffer() if down is None else down
		self.buffers = (self.up, self.down)
		self.merge_ranges = list()

	def merged(self):
		buf = ByteBuffer()
		# pseudo-code:
		# for range in sorted(self.up.split_by_tag_value("timestamp") + self.down.split_by_tag_value("timestamp"))
		#   buf.append_buffer(range)
		return buf

	def parse_from_hexdump(dmp):
		out = BidiByteBuffer()
		buf = bytes(); bufdir = None; buflinum = None
		for linum, line in enumerate(dmp.split("\n")):
			if line.strip()=="": continue
			dir = BidiByteBuffer.DOWN if line.startswith(" ") or line.startswith("\t") else BidiByteBuffer.UP
			if bufdir != dir:
				if bufdir != None:
					out.appendBytes(buf, bufdir, {"linum":buflinum})
				bufdir = dir
				buflinum = linum
				buf = bytes()
			buf += binascii.unhexlify(re.match("^\s*[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{2} {0,2})+)", line).group(1).replace(" ",""))

		if bufdir != None:
				out.appendBytes(buf, bufdir, {"linum":buflinum})

		return out

	def parse_from_c_arrays(dmp):
		out = BidiByteBuffer()
		buf = bytes(); bufheader = None
		for linum, line in enumerate(dmp.split("\n")):
			if line.strip()=="": continue
			header = re.match(r"char peer(\d+)_(\d+)\[\] = { /\* Packet (\d+) \*/", line)
			if header:
				if bufheader != None:
					out.appendBytes(buf, int(bufheader.group(1)), {"pktnum":int(bufheader.group(3))})
				bufheader = header
				buf = bytes()
			else:
				cleaned_line = line.replace("0x","").replace(", ","").replace(" };","")
				print(cleaned_line)
				buf += binascii.unhexlify(cleaned_line)

		if bufheader != None:
			out.appendBytes(buf, int(bufheader.group(1)), {"pktnum":int(bufheader.group(3))})

		return out

	def appendBytes(self, newBytes, direction, meta):
		bbuf = self.buffers[direction]

		meta["direction"] = "up" if direction == BidiByteBuffer.UP else "down"
		meta["section"] = str(meta)
		bbuf.appendBytes(newBytes, meta)

def parseHexFromClipboard():
	txt = getClipboardText()
	if re.match("char \S+\[\]", txt):
		return BidiByteBuffer.parse_from_c_arrays(txt)
	elif re.search("^\s+[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{0,2} ?)+)", txt, re.MULTILINE):
		return BidiByteBuffer.parse_from_hexdump(txt)
	elif re.match("^[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{0,2})+)", txt):
		return ByteBuffer.parse_from_hexdump(txt)
	elif re.match("^[a-fA-F0-9\t\s ]+$", txt):
		return ByteBuffer(binascii.unhexlify(re.sub("\s","",txt)))
	else:
		return ByteBuffer(txt.encode("utf-8"))


#load_pcap_file(file) / parse_pcap(byteBuffer)
#split_on_delimiter(byteBuffer, delim)
#split_by_length_prefix(packSpec, (meta_names), )
#merge_lists_of_byteBuffer(list_of_byteBufer, ...)
#concat_lists_of_byteBuffer(list_of_byteBufer, ...)


