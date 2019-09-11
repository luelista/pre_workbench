import struct
from collections import namedtuple


class incomplete(Exception):
	pass


class invalid(Exception):
	pass


class value_not_found(Exception):
	pass


class ParseContext:
	def __init__(self, parent, params):
		self.stack = list()
		self.params = params

	def get_param(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack), 0, -1):
			if id in self.stack[i][0].params:
				return self.stack[i][0].params[id]
		if raise_if_missing:
			raise Exception("Missing parameter "+id)
		else:
			return default

	def get_value(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack), 0, -1):
			try:
				return traverse_object(self.stack[i][1], id)
			except (KeyError, IndexError) as ex:
				print("get_value "+id+"/"+str(i)+" err: "+str(ex))
				pass
		if raise_if_missing:
			raise Exception("Value not found for "+id)
		else:
			return default

	def eval(self, id):
		try:
			return int(id)
		except ValueError:
			pass
		if id.startswith("$"):
			return self.get_param(id[1:])
		else:
			return self.get_value(id)

	def push(self, desc, value):
		self.stack.append((desc, value))

	def pop(self):
		self.stack.pop()

def splitdot(str):
	if str.contains("."):
		return str.split(".", 2)
	else:
		return str, ""
"""
class DescValue:
	def __init__(self, value, sourcedesc):
		self.value=value
		self.sourcedesc=sourcedesc
	def get_value(self, id):
		if id == "": return self.value
		myid, childid = splitdot(id)
		if type(self.value) == dict:
			return self.value[myid].get_value(childid)
"""

def traverse_object(el, id):
	if id == "": return el
	myid, childid = splitdot(id)
	if type(el) == dict:
		return traverse_object(el[myid], childid)
	elif type(el) == list:
		return traverse_object(el[int(myid)], childid)
	else:
		raise KeyError("can't descend into "+str(type(el)))

class AbstractDesc:
	def __init__(self, **params):
		self.params = params
		self.init(**params)


class FixedFieldDesc(AbstractDesc):
	def init(self, format, name="", description="", magic=None, **kw):
		self.pack_format=format
		self.name=name
		self.description=description
		self.magic_value=magic
		self.size = struct.calcsize(format)

	def read_from_buffer(self, buf, context):
		try:
			context.push(self, None)
			if len(buf) < self.size: raise incomplete()
			value, rest = struct.unpack_from(context.get_param("endianness") + self.pack_format, buf, 0), buf[self.size:]
			if self.magic_value != None and value != self.magic_value:
				raise invalid("found magic_value %r doesn't match spec %r" % (value, self.magic_value))
		finally:
			context.pop()


class StructDesc(AbstractDesc):
	def init(self, children, **kw):
		self.children = children

	def read_from_buffer(self, buf, context):
		try:
			o = {}
			context.push(self, o)
			for name, child in self.children:
				o[name], rest = child.read_from_buffer(rest)
			return o
		finally:
			context.pop()


class TryStructDesc(AbstractDesc):
	def init(self, variants, **kw):
		self.variants = variants

	def read_from_buffer(self, buf, context):
		for variant in self.variants:
			data, rest = variant.read_from_buffer(buf)
			if data != None:
				return data, rest
		raise invalid()


class RepeatStructDesc(AbstractDesc):
	def init(self, child, times=-1, **kw):
		self.child = child
		self.times = times

	def read_from_buffer(self, buf, context):
		try:
			o = []
			context.push(self, o)
			rest = buf
			n = context.eval(self.times)
			if self.times == "*":
				while True:
					try:
						data, rest = self.child.read_from_buffer(rest)
						o.append(data)
					except incomplete:
						break
			else:
				for i in range(n):
					data, rest = self.child.read_from_buffer(rest)
					o.append(data)
			return o
		finally:
			context.pop()



"""
class FixedStructDesc(AbstractDesc):
	def init(self, fields, default_endianness="!", **kw):
		self.fields = fields
		self.default_endianness = default_endianness
		self.pack_format = ""
		self.field_names = []
		for field in fields:
			self.pack_format += field.format
			self.field_names.append(field.name)
		self.size = struct.calcsize(self.pack_format)

	def read_from_buffer(self, buf, context):
		if endianness == None: endianness = self.default_endianness
		if len(buf) < self.size: raise incomplete
		return dict(zip(self.field_names, struct.unpack_from(endianness + self.pack_format, buf, 0))), buf[self.size:]
"""
