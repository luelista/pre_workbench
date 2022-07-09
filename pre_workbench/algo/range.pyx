

cdef class Range:
	cdef readonly object value
	cdef readonly object source_desc
	cdef readonly str field_name
	cdef readonly int start
	cdef readonly int end
	cdef readonly int bytes_size
	cdef readonly dict metadata
	cdef readonly int buffer_idx
	cdef public object exception

	def __init__(self, int start, int end, value=None, source_desc=None, str field_name=None, dict meta=None, int buffer_idx=0):
		self.value = value
		self.source_desc = source_desc
		self.field_name = field_name
		self.start = start
		self.end = end
		self.bytes_size = end - start
		self.metadata = {}
		self.buffer_idx = buffer_idx
		self.exception = None
		if meta: self.metadata.update(meta)

	def __str__(self):
		return "Range[%d:%d name=%s, value=%r, desc=%r]" % (
		self.start, self.end, self.field_name, self.value, self.source_desc)

	def __repr__(self):
		return "Range[%d:%d name=%s, valuetype=%r]" % (self.start, self.end, self.field_name, type(self.value))

	def length(self):
		return self.bytes_size

	cpdef bint contains(self, int i):
		return self.start <= i < self.end

	cpdef bint overlaps(self, Range other):
		return self.contains(other.start) or self.contains(other.end - 1) or other.contains(
			self.start) or other.contains(self.end - 1)

	def matches(self, start=None, end=None, contains=None, hasMetaKey=None, doesntHaveMetaKey=None,
				overlaps=None, **kw):
		if start is not None and start != self.start: return False
		if end is not None and end != self.end: return False
		if contains is not None and not self.contains(contains): return False
		if overlaps is not None and not self.overlaps(overlaps): return False
		if hasMetaKey is not None and hasMetaKey not in self.metadata: return False
		if doesntHaveMetaKey is not None and doesntHaveMetaKey in self.metadata: return False
		for k, v in kw.items():
			if self.metadata.get(k) == v: continue
			return False
		return True
