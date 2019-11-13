
class RangeList:
	def __init__(self, totalLength, ranges, chunkSize=1024):
		self.ranges = ranges
		self.chunkCount = totalLength // chunkSize + 1
		self.chunkSize = chunkSize
		self.chunks = [[] for i in range(self.chunkCount)]
		cdef int firstChunk, lastChunk, i
		for el in ranges:
			firstChunk = el.start // chunkSize
			lastChunk = el.end // chunkSize
			for i in range(firstChunk, lastChunk+1):
				self.chunks[i].append(el)

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
