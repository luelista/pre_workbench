from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidgetItem

from pre_workbench.util import truncate_str


class Range:
	__slots__ = (
	'value', 'source_desc', 'field_name', 'start', 'end', 'bytes_size', 'metadata', 'buffer_idx', 'exception')
	RangeRole = QtCore.Qt.UserRole
	BytesOffsetRole = QtCore.Qt.UserRole + 1
	BytesSizeRole = QtCore.Qt.UserRole + 2
	SourceDescRole = QtCore.Qt.UserRole + 3

	def __init__(self, start, end, value=None, source_desc=None, field_name=None, meta=None, buffer_idx=0):
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

	def addToTree(self, parent):
		me = QTreeWidgetItem(parent)
		me.setData(0, Range.RangeRole, self)
		me.setData(0, Range.BytesOffsetRole, self.start)
		me.setData(0, Range.BytesSizeRole, self.bytes_size)
		me.setData(0, Range.SourceDescRole, self.source_desc)
		text0 = self.field_name
		text1 = str(self.start) + "+" + str(self.bytes_size)
		text2 = str(self.source_desc)
		x = self
		while type(x.value) == Range:
			x = x.value
			me.setData(0, Range.SourceDescRole, x.source_desc)
			text0 += " >> " + x.field_name
			text1 += " >> " + str(x.start) + "+" + str(x.bytes_size)
			text2 += " >> " + str(x.source_desc)
		me.setText(0, truncate_str(text0))
		me.setText(1, truncate_str(text1))
		me.setText(2, truncate_str(text2))
		if type(x.value) == dict:
			me.setExpanded(True)
			for key, item in x.value.items():
				item.addToTree(me)
		elif type(x.value) == list:
			me.setExpanded(True)
			for item in x.value:
				item.addToTree(me)
		else:
			try:
				me.setText(3, truncate_str(x.source_desc.formatter(x.value)))
			except:
				me.setText(3, truncate_str(x.value))

	def __str__(self):
		return "Range[%d:%d name=%s, value=%r, desc=%r]" % (
		self.start, self.end, self.field_name, self.value, self.source_desc)

	def __repr__(self):
		return "Range[%d:%d name=%s, valuetype=%r]" % (self.start, self.end, self.field_name, type(self.value))

	def length(self):
		return self.bytes_size

	def contains(self, i):
		return self.start <= i < self.end

	def overlaps(self, other):
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