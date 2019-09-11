import struct
from collections import namedtuple

from typeregistry import TypeRegistry


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
	def __init__(self, buf=None):
		self.stack = list()
		self.id = ""
		self.buf_offset = 0
		self.display_offset_delta = 0
		self.buf = bytes()
		if buf != None:
			self.feed_bytes(buf)

	def feed_bytes(self, data):
		self.buf = self.buf[self.buf_offset:] + data
		self.display_offset_delta += self.buf_offset
		self.buf_offset = 0

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
		self.stack.append((desc, value, self.id, self.buf_offset))

	def restore_offset(self):
		self.buf_offset = self.stack[-1][3]

	def pop(self):
		_, _, self.id, _ = self.stack.pop()

	def get_path(self):
		return ".".join(x[2] for x in self.stack)

	def remaining_bytes(self):
		return len(self.buf) - self.buf_offset

	def require_bytes(self, needed):
		if self.remaining_bytes() < needed: raise incomplete(self, needed, self.remaining_bytes())

	def peek_structformat(self, format_string):
		return struct.unpack_from(format_string, self.buf, self.buf_offset)

	def consume_bytes(self, count):
		self.buf_offset += count

	def read_bytes(self, count):
		self.buf_offset += count
		return self.buf[self.buf_offset - count:self.buf_offset]

	def top_offset(self):
		return self.stack[-1][3] + self.display_offset_delta

	def top_length(self):
		return self.buf_offset - self.stack[-1][3] + self.display_offset_delta

	def pack_value(self, value):
		return value

	def unpack_value(self, packed_value):
		return packed_value

class LoggingParseContext(ParseContext):
	def pack_value(self, value):
		print(type(self.stack[-1][0]).__name__, self.stack[-1][2], self.top_offset(), self.top_length(), value)
		return value

class BytebufferAnnotatingParseContext(ParseContext):
	def __init__(self, bbuf):
		super().__init__(bbuf.buffer)
		self.bbuf = bbuf

	def pack_value(self, value):
		print(type(self.stack[-1][0]).__name__, self.stack[-1][2], self.top_offset(), self.top_length(), value)
		meta = { 'name': self.get_path(), 'pos': self.top_offset(), 'size': self.top_length(), '_sdef_ref': self.stack[-1][0] }
		meta.update(self.stack[-1][0].params)
		self.bbuf.setBytes(self.top_offset(), self.top_length(), meta=meta, style=None)
		return value

def annotate_byte_buffer(bbuf, structDef):
	return structDef.read_from_buffer(BytebufferAnnotatingParseContext(bbuf))

class AnnotatingParseContext(ParseContext):
	def pack_value(self, value):
		print(self.get_path(), value)
		return FIValue(value, self.stack[-1][0], self.stack[-1][2], self.top_offset(), self.top_length())

	def unpack_value(self, packed_value):
		return packed_value.value


def splitdot(expr):
	try:
		i = expr.index(".")
		return expr[:i], expr[i+1:]
	except ValueError:
		return expr, ""

class FIValue:
	def __init__(self, value, source_desc, field_name, bytes_offset, bytes_size):
		self.value=value
		self.source_desc=source_desc
		self.field_name=field_name
		self.bytes_offset = bytes_offset
		self.bytes_size = bytes_size


def traverse_object(el, id):
	if id == "": return el
	myid, childid = splitdot(id)
	if type(el) == dict:
		return traverse_object(el[myid], childid)
	elif type(el) == list:
		return traverse_object(el[int(myid)], childid)
	else:
		raise KeyError("can't descend into "+str(type(el)))

FITypes = TypeRegistry()

def deserialize_fi(params):
	if type(params) == dict:
		t = FITypes.find(id=params['tid'])
		return t(**params)
	else:
		return params

class AbstractFI:
	def __init__(self, **params):
		self.params = params
		self.init(**params)
	def serialize(self):
		self.params['tid'] = type(self)._type_registry_meta['id']
		return self.params

@FITypes.register(id=0)
class FixedFieldFI(AbstractFI):
	def init(self, format, magic=None, **kw):
		self.pack_format=format
		self.magic_value=magic
		self.size = struct.calcsize(format)

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			context.require_bytes(self.size)
			(value,) = context.peek_structformat(context.get_param("endianness") + self.pack_format)
			if self.magic_value != None and value != self.magic_value:
				raise invalid(context, "found magic_value %r doesn't match spec %r" % (value, self.magic_value))
			context.consume_bytes(self.size)
			return context.pack_value(value)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(id=1)
class VarByteFieldFI(AbstractFI):
	def init(self, size_expr="", **kw):
		self.pack_format=format
		self.size_expr=size_expr

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			n = context.eval(self.size_expr)
			context.require_bytes(n)
			return context.read_bytes(n)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(id=2)
class StructFI(AbstractFI):
	def init(self, children, **kw):
		self.children = [(name, deserialize_fi(c)) for (name, c) in children]
		try:
			self.size = sum(c.size for (name, c) in self.children)
		except:
			self.size = None

	def read_from_buffer(self, context):
		try:
			o = {}
			context.push(self, o)
			for name, child in self.children:
				context.id = name
				o[name] = child.read_from_buffer(context)
			return context.pack_value(o)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(id=3)
class VariantStructFI(AbstractFI):
	def init(self, variants, **kw):
		self.variants = [deserialize_fi(c) for c in variants]
		self.size = None


	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			for i, variant in enumerate(self.variants):
				try:
					context.id = str(i)
					return context.pack_value(variant.read_from_buffer(context))
				#except (incomplete, invalid):
				except invalid as ex:
					#TODO verhalten bei unterschiedlich langen varianten??? -  noch zu überlegen
					# aktuell: invalid ist es nur, wenn alle invalid sind - incomplete schon, sobald das erste incomplete ist
					print("variant %d no match: %r"%(i, ex))
					pass
			raise invalid(context, "no variant matched")
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()



@FITypes.register(id=4)
class RepeatStructFI(AbstractFI):
	def init(self, child, times=-1, **kw):
		self.child = deserialize_fi(child)
		self.times = times
		self.size = None

	def read_from_buffer(self, context):
		try:
			o = []
			context.push(self, o)
			if self.times == "*":
				i = 0
				while True:
					try:
						context.id = str(i)
						o.append(self.child.read_from_buffer(context))
					except incomplete:
						break
					i += 1
			else:
				n = context.eval(self.times)
				for i in range(n):
					context.id = str(i)
					o.append(self.child.read_from_buffer(context))
			return context.pack_value(o)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()



"""
class FixedStructFI(AbstractFI):
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
