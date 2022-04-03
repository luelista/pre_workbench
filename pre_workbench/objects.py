
# PRE Workbench
# Copyright (C) 2022 Mira Weller
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

from pre_workbench.structinfo import hexdump
from PyQt5.QtCore import (pyqtSignal, QObject)

from pre_workbench.guihelper import getClipboardText
from pre_workbench.algo.rangelist import RangeList
from pre_workbench.algo.range import Range


class ReloadRequired(Exception):
	pass



class ByteBuffer(QObject):
	__slots__ = ('metadata', 'buffer', 'length', 'ranges', 'fields', 'fi_tree', 'fi_root_name', 'fi_container')
	on_new_data = pyqtSignal()
	def __init__(self, buf=None, metadata=None):
		super().__init__()
		self.metadata = dict() if metadata is None else metadata
		self.setContent(buf)
		self.ranges = RangeList(len(self), list())
		self.fields = dict()
		self.fi_tree = None
		self.fi_root_name = None
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
	def removeRange(self, r):
		self.ranges.remove(r)
	def clearRanges(self):
		self.ranges = RangeList(len(self), list())
	def setRanges(self, ranges):
		self.ranges = RangeList(len(self), list(ranges))

	def appendBytes(self, newBytes, meta=None):
		start = len(self)
		self.setBytes(len(self), newBytes)
		end = len(self)
		if meta:
			return self.addRange(Range(start, end, meta=meta))

	def invalidateCaches(self):
		self.ranges.invalidateCaches()

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
		if length is None:
			b=self.buffer[offset:]
		else:
			b=self.buffer[offset:offset+length]
		return hexdump.hexdump(b, result='return')

	def toHex(self, offset=0, length=None, joiner="", format="%02x"):
		if length is None:
			b=self.buffer[offset:]
		else:
			b=self.buffer[offset:offset+length]
		return joiner.join(format % c for c in b)

	def parse_from_hexdump(dmp):
		bbuf = ByteBuffer()
		for line in dmp.split("\n"):
			if line.strip()=="": continue
			bbuf.appendBytes(binascii.unhexlify(re.match(r"^\s*[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{2} {0,2})+)", line).group(1).replace(" ","")))
		return bbuf



class ByteBufferList(QObject):
	__slots__ = ('metadata', 'buffers', 'buffers_hash', 'updating')
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
			buf += binascii.unhexlify(re.match(r"^\s*[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{2} {0,2})+)", line).group(1).replace(" ",""))

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
	if re.match(r"char \S+\[\]", txt):
		return BidiByteBuffer.parse_from_c_arrays(txt)
	elif re.search(r"^\s+[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{0,2} ?)+)", txt, re.MULTILINE):
		return BidiByteBuffer.parse_from_hexdump(txt)
	elif re.match(r"^[a-fA-F0-9]{8,}\s+((?:[a-fA-F0-9]{0,2})+)", txt):
		return ByteBuffer.parse_from_hexdump(txt)
	elif re.match(r"^[a-fA-F0-9\t\s ]+$", txt):
		return ByteBuffer(binascii.unhexlify(re.sub(r"\s","",txt)))
	else:
		return ByteBuffer(txt.encode("utf-8"))


#load_pcap_file(file) / parse_pcap(byteBuffer)
#split_on_delimiter(byteBuffer, delim)
#split_by_length_prefix(packSpec, (meta_names), )
#merge_lists_of_byteBuffer(list_of_byteBufer, ...)
#concat_lists_of_byteBuffer(list_of_byteBufer, ...)


