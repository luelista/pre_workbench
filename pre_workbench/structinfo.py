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

class FormatInfoContainer:
	def __init__(self, definitions=None, load_from_file=None):
		self.definitions = {} if definitions is None else definitions
		self.main_name = None
		if load_from_file is not None: self.load_from_file(load_from_file)

	def to_text(self, indent = 0):
		return "\n\n".join(name+" "+value.to_text(indent, None) for name, value in self.definitions.items())

	def load_from_file(self, fileName):
		if fileName.endswith(".txt"):
			with open(fileName, "r") as f:
				self.load_from_string(f.read())
		else:
			with open(fileName, "rb") as f:
				#return bin_deserialize_fi(f.read())
				#TODO
				raise NotImplemented

	def load_from_string(self, txt):
		from structinfo_parser import fi_parser, MainTrans
		ast = fi_parser.parse(txt)
		print(ast.pretty())

		trans = MainTrans(self)
		trans.load_definitions(ast)

	def write_file(self, fileName):
		if fileName.endswith(".txt"):
			txt = self.to_text()
			with open(fileName, "w") as f:
				f.write(txt)
		elif fileName.endswith(".pfi"):
			#ser = bin_serialize_fi(fi)
			#with open(fileName, "wb") as f:
			#	f.write(ser)
			raise NotImplemented
		else:
			raise Exception("unsupported file type")




class ParseContext:
	def __init__(self, format_infos: FormatInfoContainer, buf: bytes = None):
		self.format_infos = format_infos
		self.stack = list()
		self.id = ""
		self.buf_offset = 0
		self.buf_limit_end = None
		self.display_offset_delta = 0
		self.buf = bytes()
		if buf != None:
			self.feed_bytes(buf)

	def get_fi_by_def_name(self, def_name):
		try:
			return self.format_infos.definitions[def_name]
		except KeyError:
			raise parse_exception(self, "reference to undefined formatinfo name: "+def_name)

	def feed_bytes(self, data):
		remove_bytes = self.buf_offset if len(self.stack) == 0 else 0
		self.buf = self.buf[remove_bytes:] + data
		self.display_offset_delta += remove_bytes
		self.buf_offset -= remove_bytes
		if self.buf_limit_end != None:
			self.buf_limit_end -= remove_bytes

	def parse(self, by_name=None):
		if by_name is None: by_name = self.format_infos.main_name
		return self.get_fi_by_def_name(by_name).read_from_buffer(self)

	def get_param(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack)-1, -1, -1):
			if id in self.stack[i][0].params:
				return self.stack[i][0].params[id]
		if raise_if_missing:
			raise value_not_found(self, "Missing parameter "+id)
		else:
			return default

	def log(self, *dat):
		print("\t"*len(self.stack) + self.get_path(), end=": ")
		print(*dat)

	def push(self, desc, value=None, id=None):
		if id != None: self.id = id
		self.log("push",desc)
		self.stack.append([desc, value, self.id, self.buf_offset, self.buf_limit_end])
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

	def top_id(self):
		for i in reversed(range(len(self.stack))):
			id = self.stack[i][2]
			if id: return id
		return None

	def set_top_value(self, value):
		self.stack[-1][1] = value

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
		return Range(self.top_offset(), self.top_offset() + self.top_length(), value, source_desc=self.stack[-1][0], field_name=self.top_id())

	def unpack_value(self, packed_value):
		while isinstance(packed_value, Range):
			packed_value = packed_value.value
		return packed_value

class BytebufferAnnotatingParseContext(AnnotatingParseContext):
	def __init__(self, format_infos: FormatInfoContainer, bbuf):
		super().__init__(format_infos, bbuf.buffer)
		self.bbuf = bbuf

	def pack_value(self, value):
		range = super().pack_value(value)
		range.metadata.update({ 'name': self.get_path(), 'pos': self.top_offset(), 'size': self.top_length(), '_sdef_ref': self.stack[-1][0], 'show': str(value) })
		fi = self.stack[-1][0]
		if isinstance(fi, FormatInfo):
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
		return FormatInfo(data)
	else:
		return data


def bin_serialize_fi(self):
	return xdrm.dumps([uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07"), "FormatInfoFile", self.serialize()], magic=typeeditor.FILE_MAGIC)

def bin_deserialize_fi(bin):
	iid, typename, data = xdrm.loads(bin, magic=typeeditor.FILE_MAGIC)
	if iid != uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07") or typename != "FormatInfoFile":
		raise Exception("Invalid file format (got iid=%r typename=%r)"%(iid,typename))
	return deserialize_fi(data)



class FormatInfo:
	def __init__(self, info=None, typeRef=None, params=None):
		if info is not None: self.deserialize(info)
		if typeRef is not None: self.setContents(typeRef, params)
	def deserialize(self, info):
		type_id, params = info
		t, _ = FITypes.find(type_id=type_id)
		self.setContents(t, params)

	def setContents(self, typeRef, params):
		self.fi = typeRef()
		self.fi.init(**params)
		self.params = params

	def to_text(self, indent = 0, refs=None):
		return self.fi._to_text(indent, refs, self.params)

	def serialize(self):
		return [type(self.fi).type_id, self.params]

	def extra_params(self, removewhat=['children','def_name']):
		return {i:self.params[i] for i in self.params if not i in removewhat}

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			return self.fi._parse(context)
		except:
			context.restore_offset()
			raise
		finally:
			context.pop()

	def __repr__(self):
		return type(self.fi).__name__+ params_to_text(0, None, self.params)

@FITypes.register(type_id=0)
class FixedFieldFI:

	def init(self, format, magic=None, **kw):
		self.pack_format=format
		#self.magic_value=magic
		self.size = struct.calcsize(format)

	def _to_text(self, indent, refs, all_params):
		return  "fixed"+params_to_text(indent, refs, all_params, )

	def _parse(self, context):
		context.require_bytes(self.size)
		(value,) = context.peek_structformat(context.get_param("endianness") + self.pack_format)
		magic = context.get_param("magic", raise_if_missing=False)
		if magic != None and value != magic:
			raise invalid(context, "found magic value %r doesn't match spec %r" % (value, magic))
		context.consume_bytes(self.size)
		return context.pack_value(value)


@FITypes.register(type_id=1)
class VarByteFieldFI:
	def init(self, size_expr="", parse_with=None, **kw):
		if size_expr:
			self.size_expr = Expression(size_expr)
		else:
			self.size_expr = None
		self.parse_with=parse_with

	def _to_text(self, indent, refs, all_params):
		return  "bytes"+params_to_text(indent, refs, all_params, )

	def _parse(self, context):
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


@FITypes.register(type_id=2)
class StructFI:
	def init(self, children, **kw):
		self.children = [(name, deserialize_fi(c)) for (name, c) in children]
		try:
			self.size = sum(c.size for (name, c) in self.children)
		except:
			self.size = None

	def _to_text(self, indent, refs, all_params):
		x = "struct "+params_to_text(indent, refs, all_params, )+"{"+"\n"
		for (name, c) in self.children:
			x += "\t"*(1+indent) + name + " " + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
		o = {}
		context.set_top_value(o)
		for name, child in self.children:
			context.id = name
			o[name] = child.read_from_buffer(context)
		return context.pack_value(o)


@FITypes.register(type_id=3)
class VariantStructFI:
	def init(self, children, **kw):
		self.children = [deserialize_fi(c) for c in children]
		self.size = None
	def _to_text(self, indent, refs, all_params):
		if len(self.children) == 1:
			return params_to_text(indent, refs, all_params, ) + self.children[0].to_text(indent, refs)
		x = "variant "+params_to_text(indent, refs, all_params, )+"{\n"
		for c in self.children:
			x += "\t"*(1+indent) + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
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



@FITypes.register(type_id=4)
class RepeatStructFI:
	def init(self, children, times=None, until="false", until_invalid=False, **kw):
		self.children = deserialize_fi(children)
		if times is not None:
			self.times_expr = Expression(times)
			self.until_expr = None
		else:
			self.until_expr = Expression(until)
			self.times_expr = None
		self.until_invalid = until_invalid
		self.size = None

	def _to_text(self, indent, refs, all_params):
		return "repeat"+params_to_text(indent, refs, all_params, ) +" "+ self.children.to_text(indent+1, refs)

	def _parse(self, context : ParseContext):
		o = []
		context.set_top_value(o)
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
					if self.until_invalid:
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


@FITypes.register(type_id=5)
class SwitchFI:
	def init(self, expr, children, **kw):
		self.children = [(Expression(expr), deserialize_fi(c)) for (expr, c) in children]
		self.expr = Expression(expr)
		self.size = None

	def _to_text(self, indent, refs, all_params):
		x = "switch "+json.dumps(self.expr.expr_str)+" "+ params_to_text(indent, refs, all_params, ignore=["children","expr"])+"{"+"\n"
		for (expr, c) in self.children:
			x += "\t"*(1+indent) + "case "+json.dumps(expr.expr_str) + ": " + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
		checkFor = self.expr.evaluate(context)
		for expr, child in self.children:
			if expr.evaluate(context) == checkFor:
				return context.pack_value(child.read_from_buffer(context))
		raise invalid(context, "no switch case matched")


@FITypes.register(type_id=6)
class NamedFI:
	def init(self, ref_name, **kw):
		self.ref_name = ref_name
		self.ref = None

	def _to_text(self, indent, refs, all_params):
		return self.ref_name + params_to_text(indent, refs, all_params, ignore=["ref_name"])

	def _parse(self, context):
		if self.ref is None:
			self.ref = context.get_fi_by_def_name(self.ref_name)
		print(context.id, self.ref_name)
		context.id = self.ref_name
		return context.pack_value(self.ref.read_from_buffer(context))



def params_to_text(indent, refs, params, ignore=['children','def_name'], before="(", after=")"):
	x=["%s=%s"%(k,v.to_text(indent,refs) if hasattr(v, "to_text") else json.dumps(v)) for k,v in params.items() if k not in ignore]
	if len(x) == 0: return ""
	return before+", ".join(x)+after

"""
class FixedStructFI:
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

