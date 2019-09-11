import struct
from collections import namedtuple


class parse_exception(Exception):
	def __init__(self, context, msg):
		super().__init__(context.get_path() + ": " + msg)

class incomplete(parse_exception):
	def __init__(self, context, need, got):
		super().__init__(context, "incomplete: needed %d, got %d bytes" %(need,got))


class invalid(parse_exception):
	def __init__(self, context, msg="invalid"):
		super().__init__(context, msg)


class value_not_found(parse_exception):
	def __init__(self, context, msg="value_not_found"):
		super().__init__(context, msg)



class ParseContext:
	def __init__(self):
		self.stack = list()
		self.id = ""

	def get_param(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack)-1, -1, -1):
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
		self.stack.append((desc, value, self.id))

	def pop(self):
		_, _, self.id = self.stack.pop()

	def get_path(self):
		return ".".join(x[2] for x in self.stack)

def splitdot(expr):
	try:
		i = expr.index(".")
		return expr[:i], expr[i+1:]
	except ValueError:
		return expr, ""
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

def require_bytes(context, buf, needed):
	if len(buf) < needed: raise incomplete(context, needed, len(buf))


class FixedFieldDesc(AbstractDesc):
	def init(self, format, description="", magic=None, **kw):
		self.pack_format=format
		self.description=description
		self.magic_value=magic
		self.size = struct.calcsize(format)

	def read_from_buffer(self, buf, context):
		try:
			context.push(self, None)
			require_bytes(context, buf, self.size)
			(value,), rest = struct.unpack_from(context.get_param("endianness") + self.pack_format, buf, 0), buf[self.size:]
			if self.magic_value != None and value != self.magic_value:
				raise invalid(context, "found magic_value %r doesn't match spec %r" % (value, self.magic_value))
			return value, rest
		finally:
			context.pop()


class VarByteFieldDesc(AbstractDesc):
	def init(self, size_expr="", description="", **kw):
		self.pack_format=format
		self.size_expr=size_expr
		self.description=description

	def read_from_buffer(self, buf, context):
		try:
			context.push(self, None)
			n = context.eval(self.size_expr)
			require_bytes(context, buf, n)
			return buf[:n], buf[n:]
		finally:
			context.pop()


class StructDesc(AbstractDesc):
	def init(self, children, **kw):
		self.children = children
		try:
			self.size = sum(c.size for c in self.children)
		except:
			self.size = None

	def read_from_buffer(self, buf, context):
		try:
			o = {}
			context.push(self, o)
			rest = buf
			for name, child in self.children:
				context.id = name
				o[name], rest = child.read_from_buffer(rest, context)
			return o, rest
		finally:
			context.pop()


class VariantStructDesc(AbstractDesc):
	def init(self, variants, **kw):
		self.variants = variants
		self.size = None


	def read_from_buffer(self, buf, context):
		try:
			context.push(self, None)
			for i, variant in enumerate(self.variants):
				try:
					context.id = str(i)
					return variant.read_from_buffer(buf, context)
				#except (incomplete, invalid):
				except invalid as ex:
					#TODO verhalten bei unterschiedlich langen varianten??? -  noch zu überlegen
					# aktuell: invalid ist es nur, wenn alle invalid sind - incomplete schon, sobald das erste incomplete ist
					print("variant %d no match: %r"%(i, ex))
					pass
			raise invalid(context, "no variant matched")
		finally:
			context.pop()



class RepeatStructDesc(AbstractDesc):
	def init(self, child, times=-1, **kw):
		self.child = child
		self.times = times
		self.size = None

	def read_from_buffer(self, buf, context):
		try:
			o = []
			context.push(self, o)
			rest = buf
			n = context.eval(self.times)
			if self.times == "*":
				i = 0
				while True:
					try:
						context.id = str(i)
						data, rest = self.child.read_from_buffer(rest, context)
						o.append(data)
					except incomplete:
						break
					i += 1
			else:
				for i in range(n):
					context.id = str(i)
					data, rest = self.child.read_from_buffer(rest, context)
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
