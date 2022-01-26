import struct
import traceback

from pre_workbench.objects import ByteBufferList, ByteBuffer
from pre_workbench.algo.rangelist import Range

from pre_workbench.structinfo.hexdump import hexdump
from pre_workbench.structinfo.exceptions import *
from pre_workbench.structinfo.expr import Expression


class FormatInfoContainer:
	def __init__(self, definitions=None, load_from_file=None, load_from_string=None):
		self.definitions = {} if definitions is None else definitions
		self.main_name = None
		self.file_name = None
		if load_from_file is not None: self.load_from_file(load_from_file)
		if load_from_string is not None: self.load_from_string(load_from_string)

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

	def pack_error(self, ex):
		return None

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

	def pack_error(self, ex):
		range = self.pack_value(None)
		range.exception = ex
		return range

	def unpack_value(self, packed_value):
		while isinstance(packed_value, Range):
			packed_value = packed_value.value
		return packed_value

class BytebufferAnnotatingParseContext(AnnotatingParseContext):
	def __init__(self, format_infos: FormatInfoContainer, bbuf):
		super().__init__(format_infos, bbuf.buffer)
		self.bbuf = bbuf

	def pack_value(self, value):
		from pre_workbench.structinfo.format_info import FormatInfo
		range = super().pack_value(value)
		range.metadata.update({ 'name': self.get_path(), 'pos': self.top_offset(), 'size': self.top_length(), '_sdef_ref': self.stack[-1][0], 'show': str(value) })
		fi = self.stack[-1][0]
		if isinstance(fi, FormatInfo):
			range.metadata.update(fi.extra_params())
		elif isinstance(fi, dict):
			range.metadata.update(fi)
		self.bbuf.addRange(range)
		return range

