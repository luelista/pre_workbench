
# PRE Workbench
# Copyright (C) 2019 Max Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import struct
import traceback
import uuid

from pre_workbench.hexdump import hexdump
from pre_workbench.structinfo import display_styles
from pre_workbench.structinfo.valueenc import StructInfoValueEncoder
from pre_workbench.objects import Range, ByteBufferList, ByteBuffer
from pre_workbench.structinfo.expr import Expression, deserialize_expr
from typeregistry import TypeRegistry

FILE_MAGIC = b"\xde\xca\xf9\x30"
IFACE_UUID = uuid.UUID("cf3d3cfc-8cda-4456-be70-f5c7cc2c6d07")


class parse_exception(Exception):
	def __init__(self, context, msg):
		self.offset = context.offset()
		self.context_hexdump = context.hexdump_context(self.offset)
		super().__init__(context.get_path() + ": " + msg + "\n" + self.context_hexdump)
		self.parse_stack = context.stack


class incomplete(parse_exception):
	def __init__(self, context, need, got):
		super().__init__(context, "incomplete: needed %d, got %d bytes" %(need,got))


class invalid(parse_exception):
	def __init__(self, context, msg="invalid"):
		super().__init__(context, msg)


class value_not_found(parse_exception):
	def __init__(self, context, msg="value_not_found"):
		super().__init__(context, msg)


class spec_error(parse_exception):
	def __init__(self, context, msg):
		super().__init__(context, "spec_error: "+msg)
		self.offending_desc = context.stack[-1][0]


#def parse_stack_tostr(stack):

class FormatInfoContainer:
	def __init__(self, definitions=None, load_from_file=None):
		self.definitions = {} if definitions is None else definitions
		self.main_name = None
		self.file_name = None
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
		self.file_name = fileName

	def load_from_string(self, txt):
		from pre_workbench.structinfo.parser import parse_string, MainTrans
		ast = parse_string(txt)

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

	def get_fi_by_def_name(self, def_name):
			return self.definitions[def_name]



class ParseContext:
	def __init__(self, format_infos: FormatInfoContainer, buf: bytes = None):
		self.format_infos = format_infos
		self.stack = list()
		self.id = ""
		self.buf_offset = 0
		self.buf_limit_end = None
		self.display_offset_delta = 0
		self.buf = bytes()
		self.on_new_subflow_category = None
		self.subflow_categories = dict()
		if buf != None:
			self.feed_bytes(buf)

	def hexdump_context(self, ptr, context=16):
		start = ptr - (ptr%16) - context
		end = start + 2*context
		return hexdump(self.buf[start - self.display_offset_delta : end - self.display_offset_delta], result='return', addr_offset=start, addr_ptr=ptr)

	def get_fi_by_def_name(self, def_name):
		try:
			return self.format_infos.get_fi_by_def_name(def_name)
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
		self.id = by_name
		return self.get_fi_by_def_name(by_name).read_from_buffer(self)

	def get_param(self, id, default=None, raise_if_missing=True):
		for i in range(len(self.stack)-1, -1, -1):
			if id in self.stack[i][0].params:
				return self.stack[i][0].params[id]
		if raise_if_missing:
			raise value_not_found(self, "Missing parameter "+id)
		else:
			return default

	def push(self, desc, value=None, id=None):
		if id != None: self.id = id
		self.log("push",desc)
		self.stack.append([desc, value, self.id, self.buf_offset, self.buf_limit_end])
		self.id=""

	def restore_offset(self):
		self.buf_offset = self.stack[-1][3]

	def pop(self):
		self.log("pop")
		desc, value, self.id, _, self.buf_limit_end = self.stack.pop()
		self.log("-->", value, desc)
		return value

	def set_child_limit(self, max_length):
		self.require_bytes(max_length)
		self.buf_limit_end = self.buf_offset + max_length

	def get_path(self):
		return ".".join(x[2] for x in self.stack)

	def log(self, *dat):
		pass

	def remaining_bytes(self):
		if self.buf_limit_end:
			return self.buf_limit_end - self.buf_offset
		else:
			return len(self.buf) - self.buf_offset

	def require_bytes(self, needed):
		if self.remaining_bytes() < needed: raise incomplete(self, needed, self.remaining_bytes())

	def peek_structformat(self, format_string):
		return struct.unpack_from(self.get_param('endianness') + format_string, self.buf, self.buf_offset)

	def peek_int(self, n, signed):
		return int.from_bytes(self.buf[self.buf_offset:self.buf_offset+n], signed=signed, byteorder='little' if self.get_param('endianness') == '<' else 'big')

	def peek_bytes(self, n):
		return self.buf[self.buf_offset : self.buf_offset + n]

	def consume_bytes(self, count):
		self.require_bytes(count)
		self.buf_offset += count

	def read_bytes(self, count):
		self.require_bytes(count)
		self.buf_offset += count
		return self.buf[self.buf_offset - count:self.buf_offset]

	def offset(self):
		return self.buf_offset + self.display_offset_delta

	def top_offset(self, stack_index=-1):
		return self.stack[stack_index][3] + self.display_offset_delta

	def top_length(self, stack_index=-1):
		return self.buf_offset - self.stack[stack_index][3] + self.display_offset_delta

	def top_value(self, stack_index=-1):
		return self.stack[stack_index][1]

	def top_id(self):
		for i in reversed(range(len(self.stack))):
			id = self.stack[i][2]
			if id: return id
		return None

	def set_top_value(self, value):
		self.stack[-1][1] = value

	def top_buf(self, stack_index=-1):
		return self.buf[ self.stack[stack_index][3] : self.buf_offset ]

	def pack_value(self, value):
		if self.on_new_subflow_category is not None:
			try:
				desc = self.stack[-1][0]
				if 'reassemble_into' in desc.params:
					category, meta, subflow_key = self.build_subflow_key(desc.params['reassemble_into'])
					print("reassemble:",category,subflow_key,value)
					new = False
					if category not in self.subflow_categories:
						self.subflow_categories[category] = ByteBufferList()
						new = True
					databytes = self.top_buf()
					if 'segment_meta' in desc.params:
						datameta = { k: v.evaluate(self) for k,v in desc.params['segment_meta'] }
					else:
						datameta = {}
					self.subflow_categories[category].reassemble(subflow_key, meta, databytes, datameta)
					if new: self.on_new_subflow_category(category=category, parse_context=self)

				if 'store_into' in desc.params:
					category, meta, subflow_key = self.build_subflow_key(desc.params['store_into'])
					print("store:",category,subflow_key,value)
					new = False
					if category not in self.subflow_categories:
						self.subflow_categories[category] = ByteBufferList()
						new = True
					self.subflow_categories[category].add(ByteBuffer(buf=self.top_buf(), metadata=meta))
					if new: self.on_new_subflow_category(category=category, parse_context=self)

			except Exception as ex:
				raise parse_exception(self, "while adding bytes to reassembly buffer: "+ str(ex))
		return value

	def unpack_value(self, packed_value):
		return packed_value

	def build_subflow_key(self, param):
		meta = {}
		category = param[0]
		subflow_key = list()
		for expr in param[1:]:
			if isinstance(expr, Expression):
				key, value = expr.expr_str, expr.evaluate(self)
			else:
				key, value = str(expr), str(expr)
			meta[key] = value
			subflow_key.append(value)
		return category, meta, tuple(subflow_key)

class LoggingParseContext(ParseContext):
	def log(self, *dat):
		#print("\t"*len(self.stack) + self.get_path(), end=": ")
		print( self.get_path(), end=": ")
		try:
			print(*dat)
		except Exception as ex:
			print("!!!EXCEPTION in log print!!!")
			print(str(ex))
			traceback.print_exc()

	def pack_value(self, value):
		self.log("pack(L)",type(self.stack[-1][0]).__name__, self.top_offset(), self.top_length())#, value)
		return value

class AnnotatingParseContext(ParseContext):
	def pack_value(self, value):
		source_desc = self.stack[-1][0]
		self.log("pack(A)",type(source_desc).__name__, self.top_offset(), self.top_length())#, value)
		return Range(self.top_offset(), self.top_offset() + self.top_length(), super().pack_value(value), source_desc=source_desc, field_name=self.top_id())

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

def bin_serialize_fi(self):
	return xdrm.dumps([IFACE_UUID, "FormatInfoFile", self.serialize()], magic=FILE_MAGIC)

def bin_deserialize_fi(bin):
	iid, typename, data = xdrm.loads(bin, magic=FILE_MAGIC)
	if iid != IFACE_UUID or typename != "FormatInfoFile":
		raise Exception("Invalid file format (got iid=%r typename=%r)"%(iid,typename))
	return deserialize_fi(data)


def recursive_serialize(obj):
	if isinstance(obj, dict):
		return {k:recursive_serialize(v) for k,v in obj.items()}
	elif isinstance(obj, list):
		return [recursive_serialize(v) for v in obj]
	elif isinstance(obj, tuple):
		return tuple(recursive_serialize(v) for v in obj)
	elif isinstance(obj, FormatInfo):
		return obj.serialize()
	else:
		return obj

def deserialize_fi(data):
	if type(data) == list and len(data) == 2:
		return FormatInfo(data)
	else:
		return data

# struct header_field_info {
#     const char      *name;
#     const char      *abbrev;
#     enum ftenum     type;
#     int             display;
#     const void      *strings;
#     guint64         bitmask;
#     const char      *blurb;
#     .....
# };

hf_info_template = """
		{ &hf_{proto_abbrev}_{field_name}, {
			"{description}", "{proto_abbrev}.{field_name}", FT_{ws_type}, BASE_{display_base},
			{enum_ref}, 0, NULL, HFILL }},"""

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
		if "show" not in self.params:
			self.formatter = str
		elif hasattr(display_styles, self.params["show"]):
			self.formatter = getattr(display_styles, self.params["show"])
		else:
			self.formatter = lambda x: self.params["show"] % x

	def updateParams(self, **changes):
		for k,v in changes.items():
			if v is None:
				self.params.pop(k, None)
			else:
				self.params[k] = v
		self.fi.init(**self.params)

	def to_text(self, indent = 0, refs=None):
		return self.fi._to_text(indent, refs, self.params)

	def from_text(self, txt):
		from pre_workbench.structinfo.parser import fi_parser, MainTrans
		ast = fi_parser.parse(txt, start="anytype")
		print(ast.pretty())

		trans = MainTrans(self)
		item = trans.transform(ast)
		self.fi = item.fi
		self.params = item.params

	def serialize(self):
		return [type(self.fi).type_id, recursive_serialize(self.params)]

	def extra_params(self, removewhat=['children','def_name']):
		return {i:self.params[i] for i in self.params if not i in removewhat}

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			return self.fi._parse(context)
		except parse_exception as ex:
			context.log("parse_exception: "+str(ex))
			context.restore_offset()
			raise
		except Exception as ex:
			context.restore_offset()
			raise parse_exception(context, "UNHANDLED Exception in FI parse: "+str(ex)) from ex
		#except Exception as ex:
		#	context.log("UNHANDLED Exception in FI parse: "+str(ex))
		#	traceback.print_exc()
		#	context.restore_offset()
		#	raise
		finally:
			context.log("calling context.pop",self.fi)
			context.pop()

	def __repr__(self):
		return type(self.fi).__name__+ params_to_text(0, None, self.params)

@FITypes.register(type_id=2)
class StructFI:
	def init(self, children, **kw):
		self.children = [(str(name), deserialize_fi(c)) for (name, c) in children]
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
		#raise invalid(context, "no variant matched")
		context.log("no variant matched")
		return context.pack_value(None)


@FITypes.register(type_id=4)
class RepeatStructFI:
	def init(self, children, times=None, until="false", until_invalid=False, **kw):
		self.children = deserialize_fi(children)
		if times is not None:
			self.times_expr = deserialize_expr(times)
			self.until_expr = None
		else:
			self.until_expr = deserialize_expr(until)
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
		self.children = [(deserialize_expr(expr), deserialize_fi(c)) for (expr, c) in children]
		self.expr = deserialize_expr(expr)
		self.size = None

	def _to_text(self, indent, refs, all_params):
		x = "switch "+self.expr.expr_str+" "+ params_to_text(indent, refs, all_params, ignore=["children","expr"])+"{"+"\n"
		for (expr, c) in self.children:
			x += "\t"*(1+indent) + "case "+expr.expr_str + ": " + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
		checkFor = self.expr.evaluate(context)
		for expr, child in self.children:
			if expr.evaluate(context) == checkFor:
				return context.pack_value(child.read_from_buffer(context))
		#raise invalid(context, "no switch case matched")
		context.log("no switch case matched, expr value = "+repr(checkFor))
		return context.pack_value(None)


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
		#print(context.id, self.ref_name)
		context.id = self.ref_name
		return context.pack_value(self.ref.read_from_buffer(context))



EXPR_LEN = -1 #dynamic length specified with size_expr
DYN_LEN = -2  #dynamic length automatically determined while parsing
PREFIX_LEN = -3  #dynamic length automatically determined while parsing from a length prefix in the data

def _parse_signed_int(c, n):
	return c.peek_int(n, signed=True)
def _parse_unsigned_int(c, n):
	return c.peek_int(n, signed=False)
def _parse_stringz(c, n):
	for i in range(c.buf_offset, c.remaining_bytes() + c.buf_offset):
		if c.buf[i] == 0:
			return c.buf[c.buf_offset:i].decode(c.get_param('charset')), i - c.buf_offset + 1
	return b"", 0
def _parse_bytes_formatted(format):
	return lambda c,n: format % tuple(c.peek_bytes(n))
def _parse_uuid(c, n):
	if c.get_param("endianness") == "<":
		return uuid.UUID(bytes_le=c.peek_bytes(n))
	else:
		return uuid.UUID(bytes=c.peek_bytes(n))

builtinTypes = {
	"NONE": 	(0, lambda c,b: None, ),   			#	/* used for text labels with no value */
	#"PROTOCOL": (NOT_IMPL, None, ),   	#
	"BOOLEAN": 	(1, lambda c,n: c.peek_structformat("?")[0], ),   			#	/* TRUE and FALSE come from <glib.h> */
	"CHAR": 	(1, lambda c,n: c.peek_structformat("B")[0], ),   			#	/* 1-octet character as 0-255 */
	"E_UINT": 	(EXPR_LEN, _parse_unsigned_int, ),
	"UINT8": 	(1, lambda c,n: c.peek_structformat("B")[0], ),   			#
	"UINT16": 	(2, lambda c,n: c.peek_structformat("H")[0], ),   			#
	"UINT24": 	(3, _parse_unsigned_int, ),   			#	/* really a UINT32,  but displayed as 6 hex-digits if FD_HEX*/
	"UINT32": 	(4, lambda c,n: c.peek_structformat("L")[0], ),   			#
	"UINT40": 	(5, _parse_unsigned_int, ),   			#	/* really a UINT64,  but displayed as 10 hex-digits if FD_HEX*/
	"UINT48": 	(6, _parse_unsigned_int, ),   			#	/* really a UINT64,  but displayed as 12 hex-digits if FD_HEX*/
	"UINT56": 	(7, _parse_unsigned_int, ),   			#	/* really a UINT64,  but displayed as 14 hex-digits if FD_HEX*/
	"UINT64": 	(8, lambda c,n: c.peek_structformat("Q")[0], ),   			#
	"E_INT": 	(EXPR_LEN, _parse_signed_int, ),
	"INT8": 	(1, lambda c,n: c.peek_structformat("b")[0], ),   			#
	"INT16": 	(2, lambda c,n: c.peek_structformat("h")[0], ),   			#
	"INT24": 	(3, _parse_signed_int, ),   			#	/* same as for UINT24 */
	"INT32": 	(4, lambda c,n: c.peek_structformat("l")[0], ),   			#
	"INT40": 	(5, _parse_signed_int, ),   			# /* same as for UINT40 */
	"INT48": 	(6, _parse_signed_int, ),   			# /* same as for UINT48 */
	"INT56": 	(7, _parse_signed_int, ),   			# /* same as for UINT56 */
	"INT64": 	(8, lambda c,n: c.peek_structformat("q")[0], ),   			#
	"IEEE_11073_SFLOAT": (2, None, ),   #
	"IEEE_11073_FLOAT": (4, None, ),   	#
	"FLOAT": 	(4, lambda c,n: c.peek_structformat("f")[0],  ), 			#
	"DOUBLE": 	(8, lambda c,n: c.peek_structformat("d")[0], ),   			#
	#"ABSOLUTE_TIME": (NOT_IMPL, None, ),   		#
	#"RELATIVE_TIME": (NOT_IMPL, None, ),   		#
	"STRING": 	(EXPR_LEN, lambda c,n: c.peek_bytes(n).decode(c.get_param('charset')), ),   	#
	"STRINGZ": 	(DYN_LEN, _parse_stringz, ),   	#	/* for use with proto_tree_add_item() */
	"UINT_STRING": (PREFIX_LEN, lambda c,n: c.peek_bytes(n).decode(c.get_param('charset')), ),   #	/* for use with proto_tree_add_item() */
	"ETHER": 	(6, _parse_bytes_formatted("%02x:%02x:%02x:%02x:%02x:%02x"), ),   			#
	"BYTES": 	(EXPR_LEN, lambda c,n: c.peek_bytes(n), ),   	#
	"UINT_BYTES": (PREFIX_LEN, lambda c,n: c.peek_bytes(n), ),   	#
	"IPv4": 	(4, _parse_bytes_formatted("%d.%d.%d.%d"), ),   			#
	"IPv6": 	(16, _parse_bytes_formatted("%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x:%02x%02x"), ),   		#
	#"IPXNET": (NOT_IMPL, None, ),   	#
	#"FRAMENUM": (NOT_IMPL, None, ),   	#	/* a UINT32,  but if selected lets you go to frame with that number */
	#"PCRE": (NOT_IMPL, None, ),   		#	/* a compiled Perl-Compatible Regular Expression object */
	"GUID": 	(16, _parse_uuid, ),   		#	/* GUID,  UUID */
	"OID": 		(EXPR_LEN, None, ),   	#		/* OBJECT IDENTIFIER */
	"EUI64": 	(8, None, ),   			#
	"AX25": 	(7, None, ),   			#
	"VINES": 	(6, None, ),   			#
	"REL_OID": 	(EXPR_LEN, None, ),   	#	/* RELATIVE-OID */
	"SYSTEM_ID":(EXPR_LEN, None, ),   	#
	#"STRINGZPAD": (NOT_IMPL, None, ),  #	/* for use with proto_tree_add_item() */
	#"FCWWN": (NOT_IMPL, None, ),   	#
}

@FITypes.register(type_id=7)
class FieldFI:
	def init(self, format_type, base="DEC", bitmask=0, size=None, size_len=None, parse_with=None, **kw):
		self.format_type = format_type
		self.base = base
		self.bitmask = bitmask
		self.size, self._parse_fn = builtinTypes[format_type]
		if size:
			self.size_expr = deserialize_expr(size)
		else:
			self.size_expr = None
		if size_len:
			self.size_len_expr = deserialize_expr(size_len)
		else:
			self.size_len_expr = None
		self.parse_with=parse_with

	def _to_text(self, indent, refs, all_params):
		return  self.format_type+""+params_to_text(indent, refs, all_params, ignore=['children', 'def_name', 'format_type'])

	def _parse(self, context):
		if self.size == DYN_LEN:
			value, n = self._parse_fn(context, 0)
		else:
			if self.size >= 0:
				n = self.size
			elif self.size == PREFIX_LEN:
				nn = self.size_len_expr.evaluate(context)
				n = context.peek_int(nn, signed=False)
				context.consume_bytes(nn)
			elif self.size == EXPR_LEN:
				if self.size_expr:
					n = self.size_expr.evaluate(context)
				else:
					n = context.remaining_bytes()
			else:
				raise spec_error("invalid builtin-type size %d" % (self.size,))

			if self.parse_with is not None:
				context.set_child_limit(n)
				val = self.parse_with.read_from_buffer(context)
				context.consume_bytes(context.remaining_bytes())
				return context.pack_value(val)

			context.require_bytes(n)
			value = self._parse_fn(context, n)

		magic = context.get_param("magic", raise_if_missing=False)
		if magic is not None and value != magic:
			raise invalid(context, "found magic value %r doesn't match spec %r" % (value, magic))

		context.consume_bytes(n)
		return context.pack_value(value)


@FITypes.register(type_id=8)
class UnionFI:
	def init(self, children, **kw):
		self.children = [(str(name), deserialize_fi(c)) for (name, c) in children]
		try:
			self.size = sum(c.size for (name, c) in self.children)
		except:
			self.size = None

	def _to_text(self, indent, refs, all_params):
		x = "union "+params_to_text(indent, refs, all_params, )+"{"+"\n"
		for (name, c) in self.children:
			x += "\t"*(1+indent) + name + " " + c.to_text(indent+1, refs) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
		o = {}
		context.set_top_value(o)
		start, end = context.buf_offset, context.buf_offset
		for name, child in self.children:
			context.buf_offset = start
			context.id = name
			o[name] = child.read_from_buffer(context)
			end = max(end, context.buf_offset)
		context.buf_offset = end
		return context.pack_value(o)



def params_to_text(indent, refs, params, ignore=['children','def_name'], before="(", after=")"):
	x=["%s=%s"%(k,StructInfoValueEncoder().encode(v)) for k,v in params.items() if k not in ignore]
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

