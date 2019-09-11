import struct
from collections import namedtuple

FieldInfo = namedtuple("FieldInfo", ["format", "name", "description"])
class StructInfo:
	def __init__(self, fields, default_endianness="!"):
		self.fields = fields
		self.default_endianness = default_endianness
		self.pack_format = ""
		self.field_names = []
		for field in fields:
			self.pack_format += field.format
			self.field_names.append(field.name)
		self.size = struct.calcsize(self.pack_format)
	def read_from_buffer(self, buf, endianness=None):
		if endianness == None: endianness = self.default_endianness
		if len(buf) < self.size: return None, buf
		return dict(zip(self.field_names, struct.unpack_from(endianness + self.pack_format, buf, 0))), buf[self.size:]
