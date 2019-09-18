import json
import struct
import uuid
from collections import namedtuple

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QAbstractItemModel, QModelIndex
from PyQt5.QtWidgets import QTreeWidgetItem


import typeeditor
import xdrm
from objects import Range
from structinfo_expr import Expression
from typeregistry import TypeRegistry

class parse_exception(Exception):
	def __init__(self, context, msg):
		super().__init__(context.get_path() + ": " + msg)
		self.parse_stack = context.stack
		self.offset = context.offset()

class incomplete(parse_exception):
	def __init__(self, context, need, got):
		super().__init__(context, "incomplete: needed %d, got %d bytes" %(need,got))


class invalid(parse_exception):
	def __init__(self, context, msg="invalid"):
		super().__init__(context, msg)


class value_not_found(parse_exception):
	def __init__(self, context, msg="value_not_found"):
		super().__init__(context, msg)


#def parse_stack_tostr(stack):


class ParseContext:
	def __init__(self, buf=None):
		self.stack = list()
		self.id = ""
		self.buf_offset = 0
		self.buf_limit_end = None
		self.display_offset_delta = 0
		self.buf = bytes()
		if buf != None:
			self.feed_bytes(buf)

	def feed_bytes(self, data):
		remove_bytes = self.buf_offset if len(self.stack) == 0 else 0
		self.buf = self.buf[remove_bytes:] + data
		self.display_offset_delta += remove_bytes
		self.buf_offset -= remove_bytes
		if self.buf_limit_end != None:
			self.buf_limit_end -= remove_bytes

	def get_param(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack)-1, -1, -1):
			if id in self.stack[i][0].params:
				return self.stack[i][0].params[id]
		if raise_if_missing:
			raise Exception("Missing parameter "+id)
		else:
			return default

	def log(self, *dat):
		print("\t"*len(self.stack) + self.get_path(), end=": ")
		print(*dat)

	def push(self, desc, value, id=None):
		if id != None: self.id = id
		self.log("push",desc,value)
		self.stack.append((desc, value, self.id, self.buf_offset, self.buf_limit_end))
		self.id=""

	def restore_offset(self):
		self.buf_offset = self.stack[-1][3]

	def pop(self):
		self.log("pop")
		_, value, self.id, _, self.buf_limit_end = self.stack.pop()
		self.log("returning",value)
		return value

	def set_child_limit(self, max_length):
		self.require_bytes(max_length)
		self.buf_limit_end = self.buf_offset + max_length

	def get_path(self):
		return ".".join(x[2] for x in self.stack)

	def remaining_bytes(self):
		if self.buf_limit_end:
			return self.buf_limit_end - self.buf_offset
		else:
			return len(self.buf) - self.buf_offset

	def require_bytes(self, needed):
		if self.remaining_bytes() < needed: raise incomplete(self, needed, self.remaining_bytes())

	def peek_structformat(self, format_string):
		return struct.unpack_from(format_string, self.buf, self.buf_offset)

	def consume_bytes(self, count):
		self.require_bytes(count)
		self.buf_offset += count

	def read_bytes(self, count):
		self.require_bytes(count)
		self.buf_offset += count
		return self.buf[self.buf_offset - count:self.buf_offset]

	def offset(self):
		return self.buf_offset + self.display_offset_delta

	def top_offset(self):
		return self.stack[-1][3] + self.display_offset_delta

	def top_length(self):
		return self.buf_offset - self.stack[-1][3] + self.display_offset_delta

	def top_value(self):
		return self.stack[-1][1]

	def pack_value(self, value):
		return value

	def unpack_value(self, packed_value):
		return packed_value


class LoggingParseContext(ParseContext):
	def pack_value(self, value):
		self.log(type(self.stack[-1][0]).__name__, self.top_offset(), self.top_length(), value)
		return value

class AnnotatingParseContext(ParseContext):
	def pack_value(self, value):
		self.log(type(self.stack[-1][0]).__name__, self.top_offset(), self.top_length(), value)
		return Range(self.top_offset(), self.top_offset() + self.top_length(), value, self.stack[-1][0], self.stack[-1][2])

	def unpack_value(self, packed_value):
		while isinstance(packed_value, Range):
			packed_value = packed_value.value
		return packed_value

class BytebufferAnnotatingParseContext(AnnotatingParseContext):
	def __init__(self, bbuf):
		super().__init__(bbuf.buffer)
		self.bbuf = bbuf

	def pack_value(self, value):
		range = super().pack_value(value)
		range.metadata.update({ 'name': self.get_path(), 'pos': self.top_offset(), 'size': self.top_length(), '_sdef_ref': self.stack[-1][0], 'show': str(value) })
		fi = self.stack[-1][0]
		if isinstance(fi, AbstractFI):
			range.metadata.update(fi.extra_params())
		elif isinstance(fi, dict):
			range.metadata.update(fi)
		self.bbuf.addRange(range)
		return range



"""
class RangeTreeModel(QAbstractItemModel):
	def __init__(self, root, parent=None):
		super().__init__(parent)
		self.rootFiValue = root

	def columnCount(self, parent):
		return 5

	def data(self, index, role):
		if not index.isValid():
			return None

		if role != QtCore.Qt.DisplayRole:
			return None

		if self.listObject is None:
			return None

		item = self.listObject.buffers[index.row()]
		col_info = self.columns[index.column()]
		return col_info.extract(item)

	def flags(self, index):
		if not index.isValid():
			return QtCore.Qt.NoItemFlags

		return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

	def headerData(self, section, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			if section >= len(self.columns):
				return None
			return self.columns[section].title

		return None

	def index(self, row, column, parent):
		if not self.hasIndex(row, column, parent):
			return QModelIndex()

		return self.createIndex(row, column, parent.internalPointer())

	def rowCount(self, parent):
		if self.listObject is None: return 0
		return len(self.listObject)

	def addColumn(self, colInfo, insertBefore=None):
		if insertBefore == None: insertBefore = len(self.columns)
		self.beginInsertColumns(QModelIndex(), insertBefore, insertBefore)
		self.columns.insert(insertBefore, colInfo)
		self.endInsertColumns()
	def removeColumns(self, column: int, count: int, parent: QModelIndex = ...) -> bool:
		self.beginRemoveColumns(parent, column, column+count-1)
		self.columns = self.columns[0:column] + self.columns[column+count:]
		print(column, count, self.columns)
		self.endRemoveColumns()
		return True

	def parent(self, child: QModelIndex) -> QModelIndex:
		return QModelIndex()
"""

FITypes = TypeRegistry()

def deserialize_fi(data):
	if type(data) == list and len(data) == 2:
		tid, params = data
		t, _ = FITypes.find(type_id=tid)
		return t(**params)
	else:
		return data


def bin_serialize_fi(self):
	return xdrm.dumps([uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07"), "FormatInfoFile", self.serialize()], magic=typeeditor.FILE_MAGIC)

def bin_deserialize_fi(bin):
	iid, typename, data = xdrm.loads(bin, magic=typeeditor.FILE_MAGIC)
	if iid != uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07") or typename != "FormatInfoFile":
		raise Exception("Invalid file format (got iid=%r typename=%r)"%(iid,typename))
	return deserialize_fi(data)

class AbstractFI:
	def __init__(self, **params):
		self.params = params
		self.init(**params)
	def updateParams(self, **params):
		self.params.update(params)
		self.init(**params)
	def to_text(self, indent = 0, refs=None):
		if refs == None:
			refs = dict()
			name = self.params.get("def_name","DEFAULT")
			refs[name] = ""
			refs[name] = self._to_text(indent, refs)
			return "\n\n".join(name+" "+value for name,value in refs.items())
		else:
			return self._to_text(indent, refs)
	def serialize(self):
		return [type(self).type_id, self.params]
	def extra_params(self, removewhat=['children','def_name']):
		return {i:self.params[i] for i in self.params if not i in removewhat}
	def __repr__(self):
		return self.params.get("def_name","")+" "+type(self).__name__+ "("+repr(self.params)+")"

@FITypes.register(type_id=0)
class FixedFieldFI(AbstractFI):

	struct_format_alias={
		"c": "char",
		"b": "int8",
		"B": "uint8",
		"?": "bool",
		"h": "int16",
		"H": "uint16",
		"i": "int32",
		"I": "uint32",
		#"l": "int32",
		#"L": "uint32",
		"q": "int64",
		"Q": "uint64",
		"f": "float",
		"d": "double",
		"s": "char[]",
	}

	def init(self, format, magic=None, **kw):
		self.pack_format=format
		self.magic_value=magic
		self.size = struct.calcsize(format)

	def _to_text(self, indent, refs):
		if self.pack_format in FixedFieldFI.struct_format_alias:
			return FixedFieldFI.struct_format_alias[self.pack_format]+params_to_text(indent, refs, self.extra_params(["format"]))
		else:
			return "pack("+repr(self.pack_format)+params_to_text(indent, refs, self.extra_params(["format"]),",","")+")"

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
	def init(self, size_expr="", parse_with=None, **kw):
		if size_expr:
			self.size_expr = Expression(size_expr)
		else:
			self.size_expr = None
		self.parse_with=parse_with

	def _to_text(self, indent, refs):
		return  "bytes"+params_to_text(indent, refs, self.extra_params())

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			if self.size_expr:
				n = self.size_expr.evaluate(context)
			else:
				n = context.remaining_bytes()
			if self.parse_with == None:
				return context.pack_value(context.read_bytes(n))
			else:
				context.set_child_limit(n)
				val = self.parse_with.read_from_buffer(context)
				context.consume_bytes(context.remaining_bytes())
				return context.pack_value(val)
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

	def _to_text(self, indent, refs):
		x = "struct "+params_to_text(indent, refs, self.extra_params())+"{"+"\n"
		for (name, c) in self.children:
			x += "\t"*(1+indent) + name + " " + c.to_text(indent+1, refs) + "\n"
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
	def _to_text(self, indent, refs):
		if len(self.children) == 1:
			return params_to_text(indent, refs, self.extra_params()) + self.children[0].to_text(indent, refs)
		x = "variant "+params_to_text(indent, refs, self.extra_params())+"{\n"
		for c in self.children:
			x += "\t"*(1+indent) + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			for i, variant in enumerate(self.children):
				try:
					context.id = "var-%d"%i
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
	def init(self, children, times=None, until="false", **kw):
		self.children = deserialize_fi(children)
		if times is not None:
			self.times_expr = Expression(times)
			self.until_expr = None
		else:
			self.until_expr = Expression(until)
			self.times_expr = None
		self.size = None

	def _to_text(self, indent, refs):
		return "repeat"+params_to_text(indent, refs, self.extra_params()) +" "+ self.children.to_text(indent+1, refs)

	def read_from_buffer(self, context : ParseContext):
		try:
			o = []
			context.push(self, o)
			if self.times_expr is None:
				i = 0
				while True:
					pos = context.offset()
					try:
						context.id = "[%d]"%i
						o.append(self.children.read_from_buffer(context))
					except incomplete:
						break
					except invalid:
						if self.params.get("until_invalid"):
							break
						else:
							raise
					if pos == context.offset():
						raise parse_exception(context, "infinite loop prevented - repeat child consumed zero bytes")
					if self.until_expr.evaluate(context): break
					i += 1
			else:
				for i in range(self.times_expr.evaluate(context)):
					context.id = "[%d]"%i
					o.append(self.children.read_from_buffer(context))
			return context.pack_value(o)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(type_id=5)
class SwitchFI(AbstractFI):
	def init(self, expr, children, **kw):
		self.children = [(Expression(expr), deserialize_fi(c)) for (expr, c) in children]
		self.expr = Expression(expr)
		self.size = None

	def _to_text(self, indent, refs):
		x = "switch "+json.dumps(self.expr.expr_str)+" "+ params_to_text(indent, refs, self.extra_params(["children","expr"]))+"{"+"\n"
		for (expr, c) in self.children:
			x += "\t"*(1+indent) + "case "+json.dumps(expr.expr_str) + ": " + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			checkFor = self.expr.evaluate(context)
			for expr, child in self.children:
				if expr.evaluate(context) == checkFor:
					return context.pack_value(child.read_from_buffer(context))
			raise invalid(context, "no switch case matched")
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()


@FITypes.register(type_id=6)
class NamedFI(AbstractFI):
	def init(self, def_name, **kw):
		self.ref = None
		self.def_name = def_name   ##TODO eigentlich ist das hier kein def_name, sondern ein REF_name...
		self.size = None

	def _to_text(self, indent, refs):
		if self.def_name not in refs:
			refs[self.def_name] = ""
			refs[self.def_name] = self.ref._to_text(0, refs)
		return "&" + self.def_name

	def read_from_buffer(self, context):
		return self.ref.read_from_buffer(context)


def params_to_text(indent, refs, params, before="(", after=")"):
	x=["%s=%s"%(k,v.to_text(indent,refs) if hasattr(v, "to_text") else json.dumps(v)) for k,v in params.items()]
	if len(x) == 0: return ""
	return before+", ".join(x)+after

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


def load_file(fileName:str):
	import structinfo_parser
	if fileName.endswith(".txt"):
		with open(fileName, "r") as f:
			return structinfo_parser.parse_fi(f.read())
	else:
		with open(fileName, "rb") as f:
			return bin_deserialize_fi(f.read())

def write_file(fileName, fi):
	if fileName.endswith(".txt"):
		txt = fi.to_text()
		with open(fileName, "w") as f:
			f.write(txt)
	elif fileName.endswith(".pfi"):
		ser = bin_serialize_fi(fi)
		with open(fileName, "wb") as f:
			f.write(ser)
	else:
		raise Exception("unsupported file type")
