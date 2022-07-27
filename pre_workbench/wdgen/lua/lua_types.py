
from io import StringIO

from pre_workbench.structinfo.format_info import DYN_LEN, EXPR_LEN, PREFIX_LEN
from pre_workbench.wdgen.lua.lua_expr import to_lua_expr


class WDGenVisitor:
	def __init__(self, context, proto_name):
		self.context = context
		self.ws_field_defs = list()
		self.proto_name = proto_name
		self.output = StringIO()

	def out(self, s):
		self.output.write(s + '\n')

	def get_result(self):
		return self.output.getvalue()

	def structfi(self, desc):
		self.out("  -- struct " + self.context.get_path("_"))
		for name, child, comment in desc.fi.children:
			self.context.id = name
			child.visit(self.context, self)

	def variantstructfi(self, desc):
		self.out("  -- variant " + self.context.get_path("_"))
		raise NotImplementedError("Type 'variant' not implemented yet for code generation")

	def repeatstructfi(self, desc):
		self.out("  -- repeat " + self.context.get_path("_"))
		if desc.fi.times_expr:
			self.out("  for i_" + self.context.get_path("_") + " = 1," + to_lua_expr(desc.fi.times_expr) + " do")
			desc.fi.children.visit(self.context, self)
			self.out("  end")
		else:
			self.out("  while offset < buffer:len() do")
			desc.fi.children.visit(self.context, self)
			self.out("  if " + to_lua_expr(desc.fi.until_expr) + " then break end")
			self.out("  end")

	def switchfi(self, desc):
		self.out("  -- switch " + self.context.get_path("_"))
		raise NotImplementedError("Type 'switch' not implemented yet for code generation")

	def namedfi(self, desc):
		self.out("  -- named " + self.context.get_path("_"))
		self.out("  offset = offset + parse_"+desc.fi.ref_name+"(buffer(offset), pinfo, subtree, '" + self.context.top_id() + ": ', fval)")

	def fieldfi(self, desc):
		self.out("  -- field " + self.context.get_path("_")+" "+desc.fi.format_type)
		id = self.context.get_path("_")
		method = "add_le" if self.context.get_param("endianness") == "<" else "add"
		le_prefix = "le_" if self.context.get_param("endianness") == "<" else ""
		if desc.fi.size == DYN_LEN:
			raise NotImplementedError('DYN_LEN not implemented')
		elif desc.fi.size == PREFIX_LEN:
			raise NotImplementedError('PREFIX_LEN not implemented')
		elif desc.fi.size == EXPR_LEN:
			self.out("  len = " + to_lua_expr(desc.fi.size_expr) + "  -- expression-based length")
		else:
			self.out("  len = " + str(desc.fi.size) + "  -- static length")
		self.out(f"  subtree:{method}(" + "f_" + id + ", buffer(offset, len))")
		if desc.fi.format_type in ('INT8', 'INT16', 'INT24', 'INT32'):
			self.out(f"  fval['{self.context.top_id()}'] = buffer(offset, len):{le_prefix}int()")
		elif desc.fi.format_type in ('CHAR', 'UINT8', 'UINT16', 'UINT24', 'UINT32'):
			self.out(f"  fval['{self.context.top_id()}'] = buffer(offset, len):{le_prefix}uint()")
		self.out("  offset = offset + len")
		show = desc.params.get("show", "")
		self.ws_field_defs.append((self.context.get_path("."), self.context.top_id(), desc.fi.format_type, self.context.get_param('show',raise_if_missing=False), self.context.get_param('charset',raise_if_missing=False)))
		self.out("")


	def unionfi(self, desc):
		self.out("  -- union " + self.context.get_path("_"))
		raise NotImplementedError("Type 'union' not implemented yet for code generation")

	def bitstructfi(self, desc):
		self.out("  -- bits " + self.context.get_path("_"))
		raise NotImplementedError("Type 'bits' not implemented yet for code generation")
		for key, len in desc.fi.children:
			self.out("  -- "+key+" "+str(len))
			self.ws_field_defs.append((self.context.get_path("."), "UINT32"))
