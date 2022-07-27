from pre_workbench.structinfo.parsecontext import ParseContext
from pre_workbench.wdgen.lua.lua_types import WDGenVisitor


def generate_lua_dissector(r, fic, out):
	definition = r.definition if r.definition else fic.main_name
	proto_name = fic.main_name

	context = ParseContext(fic)
	generator = WDGenVisitor(context, proto_name)
	generator.out(f'function {proto_name}_proto.dissector(buffer, pinfo, tree)')
	generator.out(f'  local subtree = tree:add({proto_name}_proto, buffer(), "Protocol Data {definition}")')
	generator.out('  local fieldValues = {}')
	generator.out(f'  end_offset = parse_{definition}(buffer, pinfo, subtree, "", fieldValues)')
	generator.out(f'  subtree:set_len(end_offset)')
	generator.out(f'end')
	generator.out("")
	for key, value in fic.definitions.items():
		generator.out("-- definition "+key)
		generator.out("function parse_"+key+"(buffer, pinfo, treenode, title_prefix, fval)")
		generator.out(f'  local subtree = treenode:add({proto_name}_proto, buffer(), title_prefix .. "{key}")')
		generator.out("  local offset = 0")
		generator.out("  local field_item")
		context.id = key
		value.visit(context, generator)
		generator.out(f'  subtree:set_len(offset)')
		generator.out("  return offset")
		generator.out("end")
		generator.out("")

	out("\n--------------------------------------------\n-- init")
	out(f'{proto_name}_proto = Proto("{proto_name}", "{proto_name} Protocol")')

	out("\n--------------------------------------------\n-- ws_field_defs")
	for (key, id, format_type, show, charset) in generator.ws_field_defs:
		if 'STRING' in format_type:
			display = 'base.UNICODE' if charset and 'utf' in charset else 'base.ASCII'
		elif format_type == 'BYTES':
			display = 'base.NONE'
		else:
			display = 'base.HEX' if show and 'hex' in show else 'base.DEC'
		out(f'local f_{key.replace(".","_")} = ProtoField.{format_type.lower()}("{key}", "{id}", {display})')
	fields = ','.join('f_' + key.replace(".","_") for (key, id, format_type, show, charset) in generator.ws_field_defs)
	out(proto_name + '_proto.fields = {' + fields + '}')

	out("\n--------------------------------------------\n-- parser functions")
	out(generator.get_result())

	if r.dissector_table:
		name, key = r.dissector_table.split(":")
		out("\n--------------------------------------------\n-- registration")
		out(f'local dissector_table = DissectorTable.get("{name}")')
		out(f'dissector_table:add({key}, {proto_name}_proto)')
