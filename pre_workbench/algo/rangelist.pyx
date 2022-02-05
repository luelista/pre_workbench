from collections import defaultdict

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidgetItem

from pre_workbench.util import truncate_str


class RangeList:
	def __init__(self, totalLength, ranges, chunkSize=128):
		cdef int firstChunk, lastChunk, i
		self.ranges = ranges
		self.annotationStartCache = dict()
		self.annotationContainsCache = dict()
		self.chunkCount = totalLength // chunkSize + 1
		self.chunkSize = chunkSize
		self.chunks = [[] for i in range(self.chunkCount)]
		for el in ranges:
			firstChunk = el.start // chunkSize
			lastChunk = el.end // chunkSize
			for i in range(firstChunk, lastChunk+1):
				self.chunks[i].append(el)

	def invalidateCaches(self):
		self.annotationStartCache = dict()
		self.annotationContainsCache = dict()

	def cacheMetaValuesStart(self, metaKey):
		indizes = defaultdict(list)
		for el in self.ranges:
			if metaKey in el.metadata:
				indizes[el.start].append(el.metadata[metaKey])
		self.annotationStartCache[metaKey] = indizes

	def getMetaValuesStartingAt(self, start, metaKey):
		if not metaKey in self.annotationStartCache: self.cacheMetaValuesStart(metaKey)
		return self.annotationStartCache[metaKey][start]

	def cacheMetaValuesContains(self, metaKey):
		cdef int index
		indizes = defaultdict(list)
		for el in self.ranges:
			if metaKey in el.metadata:
				for index in range(el.start, el.end):
					indizes[index].append(el.metadata[metaKey])
		self.annotationContainsCache[metaKey] = indizes

	def getMetaValuesContaining(self, start, metaKey):
		if not metaKey in self.annotationContainsCache: self.cacheMetaValuesContains(metaKey)
		return self.annotationContainsCache[metaKey][start]

	def findMatchingRanges(self, start=None, end=None, contains=None, overlaps=None, **kw):
		cdef int scanChunk = -1
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

		if scanChunk != -1:
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
		cdef int firstChunk = el.start // self.chunkSize
		cdef int lastChunk = el.end // self.chunkSize
		cdef int i
		while lastChunk >= self.chunkCount:
			self.chunks.append(list())
			self.chunkCount += 1
		for i in range(firstChunk, lastChunk+1):
			self.chunks[i].append(el)
		self.ranges.append(el)


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
		self.exception = None
		if meta: self.metadata.update(meta)
		#self.style = dict()

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
		me.setText(0, truncate_str(text0))
		me.setText(1, truncate_str(text1))
		me.setText(2, truncate_str(text2))
		if type(theRange.value) == dict:
			me.setExpanded(True)
			for key,item in theRange.value.items():
				item.addToTree(me)
		elif type(theRange.value) == list:
			me.setExpanded(True)
			for item in theRange.value:
				item.addToTree(me)
		else:
			try:
				me.setText(3, truncate_str(theRange.source_desc.formatter(theRange.value)))
			except:
				me.setText(3, truncate_str(theRange.value))
	def __str__(self):
		return "Range[%d:%d name=%s, value=%r, desc=%r]"%(self.start,self.end,self.field_name,self.value,self.source_desc)
	def __repr__(self):
		#return "Range[%d:%d name=%s, value=%r, desc=%r]"%(self.start,self.end,self.field_name,self.value,self.source_desc)
		return "Range[%d:%d name=%s, valuetype=%r]" % (self.start, self.end, self.field_name, type(self.value))
	def length(self):
		return self.bytes_size

	def contains(self, i):
		return self.start <= i < self.end

	def overlaps(self, other):
		return self.contains(other.start) or self.contains(other.end-1) or other.contains(self.start) or other.contains(self.end-1)

	def matches(self, start=None, end=None, contains=None, hasMetaKey=None,
				#hasStyleKey=None,
				overlaps=None, **kw):
		if start != None and start != self.start: return False
		if end != None and end != self.end: return False
		if contains != None and not self.contains(contains): return False
		if overlaps != None and not self.overlaps(overlaps): return False
		if hasMetaKey != None and not hasMetaKey in self.metadata: return False
		#if hasStyleKey != None and not hasStyleKey in self.style: return False
		for k,v in kw.items():
			if self.metadata.get(k) == v: continue
			#if self.style.get(k) == v: continue
			return False
		return True


