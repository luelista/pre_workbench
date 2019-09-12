import json
import struct
import uuid
from collections import namedtuple

import typeeditor
import xdrm
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
		meta.update(self.stack[-1][0].extra_params())
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

def deserialize_fi(data):
	if type(data) == list and len(data) == 2:
		tid, params = data
		t, _ = FITypes.find(type_id=params['tid'])
		return t(**params)
	else:
		return data


def bin_serialize_fi(self):
	return typeeditor.FILE_MAGIC + xdrm.dumps([uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07"), "FormatInfoFile", self.serialize()])

def bin_deserialize_fi(self):
	return typeeditor.FILE_MAGIC + xdrm.dumps([uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07"), "FormatInfoFile", self.serialize()])

class AbstractFI:
	def __init__(self, **params):
		self.params = params
		self.init(**params)
	def to_text(self, indent = 0):
		pass
	def serialize(self):
		return [type(self).type_id, self.params]
	def extra_params(self, removewhat=['children']):
		return {i:self.params[i] for i in self.params if not i in removewhat}

struct_format_alias={
	"c": "char",
	"b": "int8",
	"B": "uint8",
	"?": "bool",
	"h": "int16",
	"H": "uint16",
	"i": "int32",
	"I": "uint32",
	"l": "int32",
	"L": "uint32",
	"q": "int64",
	"Q": "uint64",
	"f": "float",
	"d": "double",
	"s": "char[]",
}

@FITypes.register(type_id=0)
class FixedFieldFI(AbstractFI):
	def init(self, format, magic=None, **kw):
		self.pack_format=format
		self.magic_value=magic
		self.size = struct.calcsize(format)

	def to_text(self, indent = 0):
		if self.pack_format in struct_format_alias:
			return params_to_text(self.extra_params(["pack_format"])) + struct_format_alias[self.pack_format]
		else:
			return params_to_text(self.extra_params(["pack_format"])) + "(pack "+repr(self.pack_format)+")"

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


@FITypes.register(type_id=1)
class VarByteFieldFI(AbstractFI):
	def init(self, size_expr="", **kw):
		self.size_expr=size_expr

	def to_text(self, indent = 0):
		return params_to_text(self.extra_params()) + "bytes"

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			n = context.eval(self.size_expr)
			context.require_bytes(n)
			return context.pack_value(context.read_bytes(n))
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(type_id=2)
class StructFI(AbstractFI):
	def init(self, children, **kw):
		self.children = [(name, deserialize_fi(c)) for (name, c) in children]
		try:
			self.size = sum(c.size for (name, c) in self.children)
		except:
			self.size = None

	def to_text(self, indent = 0):
		x = params_to_text(self.extra_params())+"struct {"+"\n"
		for (name, c) in self.children:
			x += "\t"*(1+indent) + name + " " + c.to_text(indent+1) + "\n"
		return x + "\t"*indent+"}"

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


@FITypes.register(type_id=3)
class VariantStructFI(AbstractFI):
	def init(self, children, **kw):
		self.children = [deserialize_fi(c) for c in children]
		self.size = None
	def to_text(self, indent = 0):
		if len(self.children) == 1:
			return params_to_text(self.extra_params()) + self.children[0].to_text(indent)
		x = params_to_text(self.extra_params())+"variant {\n"
		for c in self.children:
			x += "\t"*(1+indent) + c.to_text(indent+1) + "\n"
		return x + "\t"*indent+"}"

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			for i, variant in enumerate(self.children):
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



@FITypes.register(type_id=4)
class RepeatStructFI(AbstractFI):
	def init(self, children, times=-1, **kw):
		self.children = deserialize_fi(children)
		self.times = times
		self.size = None

	def to_text(self, indent = 0):
		return params_to_text(self.extra_params(["children","times"]))+"repeat("+json.dumps(self.times)+"){"+"\n"+ "\t"*(1+indent) + self.children.to_text(indent+1) + "\n}"


	def read_from_buffer(self, context):
		try:
			o = []
			context.push(self, o)
			if self.times == "*":
				i = 0
				while True:
					try:
						context.id = str(i)
						o.append(self.children.read_from_buffer(context))
					except incomplete:
						break
					i += 1
			else:
				n = context.eval(self.times)
				for i in range(n):
					context.id = str(i)
					o.append(self.children.read_from_buffer(context))
			return context.pack_value(o)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()

def params_to_text(params):
	x=["%s=%s"%(k,json.dumps(v)) for k,v in params.items()]
	if len(x) == 0: return ""
	return "["+", ".join(x)+"] "

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
