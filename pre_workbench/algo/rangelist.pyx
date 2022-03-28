from collections import defaultdict

class RangeList:
	__slots__ = ('ranges', 'chunks', 'chunkSize', 'chunkCount', 'annotationStartCache', 'annotationContainsCache')

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
			if el.metadata.get(metaKey) is not None:
				indizes[el.start].append(el.metadata[metaKey])
		self.annotationStartCache[metaKey] = indizes

	def getMetaValuesStartingAt(self, start, metaKey):
		if not metaKey in self.annotationStartCache: self.cacheMetaValuesStart(metaKey)
		return self.annotationStartCache[metaKey][start]

	def cacheMetaValuesContains(self, metaKey):
		cdef int index
		indizes = defaultdict(list)
		for el in self.ranges:
			if el.metadata.get(metaKey) is not None:
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

	def remove(self, el):
		cdef int firstChunk = el.start // self.chunkSize
		cdef int lastChunk = el.end // self.chunkSize
		cdef int i
		for i in range(firstChunk, lastChunk+1):
			self.chunks[i].remove(el)
		self.ranges.remove(el)


