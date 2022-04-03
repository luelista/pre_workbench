import datetime
import logging
import uuid
from math import ceil, floor

from bitstring import BitStream

from pre_workbench.structinfo import display_styles, FITypes
from pre_workbench.structinfo.exceptions import *
from pre_workbench.structinfo.expr import deserialize_expr, Expression
from pre_workbench.structinfo.parsecontext import ParseContext
from pre_workbench.structinfo.serialization import recursive_serialize, deserialize_fi
from pre_workbench.structinfo.valueenc import StructInfoValueEncoder


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
		elif "%" in self.params["show"]:
			self.formatter = lambda x: self.params["show"] % x
		else:
			self.formatter = lambda x: self.params["show"].format(x) if x is not None else None

	def updateParams(self, **changes):
		for k,v in changes.items():
			if v is None:
				self.params.pop(k, None)
			else:
				self.params[k] = v
		self.fi.init(**self.params)

	"""
	Serializes a FormatInfo to its parsable text representation
	"""
	def to_text(self, indent = 0, refs=None):
		return self.fi._to_text(indent, refs, self.params)

	def from_text(self, txt):
		from pre_workbench.structinfo.parser import parse_definition
		item = parse_definition(txt)
		self.fi = item.fi
		self.params = item.params

	def serialize(self):
		return [type(self.fi).type_id, recursive_serialize(self.params)]

	def extra_params(self, removewhat=['children','def_name'], context=None):
		return {i:self._eval_if_needed(self.params[i], context) for i in self.params if not i in removewhat}

	def _eval_if_needed(self, expr, context):
		if isinstance(expr, Expression) and context is not None:
			return expr.evaluate(context)
		else:
			return expr

	def read_from_buffer(self, context):
		try:
			context.push(self, None)
			if "print" in self.params and not isinstance(self.fi, FieldFI):
				logging.info("%s %s", "+ " * len(context.stack), self.params["print"])
			result = self.fi._parse(context)

			if "print" in self.params and isinstance(self.fi, FieldFI):
				logging.info("%s %s: \t%r", "+ " * len(context.stack), self.params["print"], result.value if hasattr(result, "value") else result)
			return result
		except parse_exception as ex:
			context.log("parse_exception: "+str(ex))
			context.restore_offset()
			if not context.get_param("ignore_errors", False, raise_if_missing=False):
				context.failed = ex
			return context.pack_error(ex)
		except Exception as ex:
			context.log("UNHANDLED Exception in FI parse: "+str(ex))
			context.restore_offset()
			if not context.get_param("ignore_errors", False, raise_if_missing=False):
				context.failed = ex
			return context.pack_error(parse_exception(context, "UNHANDLED Exception in FI parse: "+str(ex), cause=ex))
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
			if context.failed: break
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
			context.id = "var-%d"%i
			result = context.pack_value(variant.read_from_buffer(context))

			if context.failed and isinstance(context.failed, invalid):
				#TODO verhalten bei unterschiedlich langen varianten??? -  noch zu überlegen
				# aktuell: invalid ist es nur, wenn alle invalid sind - incomplete schon, sobald das erste incomplete ist
				print("variant %d no match: %r"%(i, context.failed))
				context.failed = None
				continue


			return result
		#
		context.log("no variant matched")
		raise invalid(context, "no variant matched")
		#return context.pack_value(None)


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
				context.id = "[%d]"%i
				o.append(self.children.read_from_buffer(context))
				if context.failed:
					if isinstance(context.failed, incomplete) or (
							isinstance(context.failed, invalid) and self.until_invalid):
						context.failed = None
						o.pop()
					break
				if pos == context.offset():
					raise parse_exception(context, "infinite loop prevented - repeat child consumed zero bytes")
				if self.until_expr.evaluate(context): break
				i += 1
		else:
			times = self.times_expr.evaluate(context)
			for i in range(times):
				context.id = "[%d/%d]"%(i,times)
				o.append(self.children.read_from_buffer(context))
				if context.failed: break
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
				context.id = "case %r" % (checkFor,)
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


def guess_timestamp_unit(num):
	if num >= 500000000000000.0:
		return 'us'
	elif num >= 500000000000.0:
		return 'ms'
	else:
		return 's'


def _parse_unsigned_int_timestamp(c, n):
	num = c.peek_int(n, signed=False)
	unit = c.get_param('unit',raise_if_missing=None)
	if unit is None:
		unit = guess_timestamp_unit(num)
	if unit == 'us':
		num /= 1000000.0
	elif unit == 'ms':
		num /= 1000.0
	elif unit != 's':
		raise spec_error(c, f'invalid time unit "{unit}" provided, use "us", "ms" or "s"')
	return datetime.datetime.fromtimestamp(num)
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
	"ABSOLUTE_TIME": (EXPR_LEN, _parse_unsigned_int_timestamp, ),   		#
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
	"EUI64": 	(8, _parse_bytes_formatted("%02x%02x:%02x%02x:%02x%02x:%02x%02x"), ),   			#
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
		self.size_expr = deserialize_expr(size) if size else None
		self.size_len_expr = deserialize_expr(size_len) if size_len else None
		self.parse_with = parse_with

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


@FITypes.register(type_id=9)
class BitStructFI:
	def init(self, children, **kw):
		self.children = [(str(name), bitlength) for (name, bitlength) in children]
		self.size = ceil(sum(bits for (name, bits) in self.children) / 8)

	def _to_text(self, indent, refs, all_params):
		x = "bits "+params_to_text(indent, refs, all_params, )+"{"+"\n"
		for (name, bits) in self.children:
			x += "\t"*(1+indent) + name + " : " + str(bits) + "\n"
		return x + "\t"*indent+"}"

	def _parse(self, context):
		o = {}
		context.set_top_value(o)
		context.require_bytes(self.size)
		raw_data = context.peek_bytes(self.size)
		le = False
		if context.get_param("endianness", raise_if_missing=False) == "<":
			raw_data = raw_data[::-1]
			le = True
		stream = BitStream(raw_data)
		pos = context.buf_offset * 8
		for key, len in self.children:
			if not le: context.buf_offset = floor(pos / 8)
			context.push(desc=context.stack[-1].desc, id=key)
			o[key] = context.pack_value(stream.read(len).uint)
			context.pop()
			pos += len
		context.buf_offset = ceil(pos / 8)
		return context.pack_value(o)


def params_to_text(indent, refs, params, ignore=['children','def_name'], before="(", after=")"):
	x=["%s=%s"%(k, StructInfoValueEncoder().encode(v)) for k,v in params.items() if k not in ignore]
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

