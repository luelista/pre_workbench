from pre_workbench.structinfo.parsecontext import ParseContext
from pre_workbench.wdgen.lua.lua_types import WDGenVisitor


entry_func_template = '''
function {proto_name}_proto.dissector(buffer, pinfo, tree)
  local subtree = tree:add({proto_name}_proto, buffer(), "Protocol Data {definition}")
  local fieldValues = {}
  end_offset = parse_{definition}(buffer, pinfo, subtree, "", fieldValues)
  subtree:set_len(end_offset)
end

'''

definition_header_template = '''
-- definition {key}
function parse_{key}(buffer, pinfo, treenode, title_prefix, fval)
  local subtree = treenode:add({proto_name}_proto, buffer(), title_prefix .. "{key}")
  local offset = 0
  local field_item
'''
definition_footer_template = '''
  subtree:set_len(offset)
  return offset
end

'''


def generate_lua_dissector(definition, only_types, dissector_table, fic, out):
	if only_types:
		only_types = only_types.split(",")
	else:
		only_types = None
	proto_name = only_types[0] if only_types else fic.main_name
	if not definition: definition = proto_name

	context = ParseContext(fic)
	generator = WDGenVisitor(context, proto_name)
	generator.out(entry_func_template.replace('{proto_name}', proto_name).replace('{definition}', definition))

	for key, value in fic.definitions.items():
		if only_types and key not in only_types: continue

		generator.out(definition_header_template.replace('{proto_name}', proto_name).replace('{key}', key))
		context.id = key
		value.visit(context, generator)
		generator.out(definition_footer_template)

	out.write("\n--------------------------------------------\n-- init" + '\n')
	out.write(f'{proto_name}_proto = Proto("{proto_name}", "{proto_name} Protocol")' + '\n')

	out.write("\n--------------------------------------------\n-- ws_field_defs" + '\n')
	for d in generator.ws_field_defs:
		display = _get_display(d)
		out.write(f'local f_{d.long_id.replace(".","_")} = ProtoField.new("{d.short_id}", "{d.long_id}", ftypes.{d.format_type}, nil, {display})' + '\n')

	fields = ','.join('f_' + d.long_id.replace(".","_") for d in generator.ws_field_defs)
	out.write(proto_name + '_proto.fields = {' + fields + '}' + '\n')

	out.write("\n--------------------------------------------\n-- parser functions" + '\n')
	out.write(generator.get_result() + '\n')

	if dissector_table:
		out.write("\n--------------------------------------------\n-- registration" + '\n')
		for entry in dissector_table:
			name, key = entry.split(":")
			out.write(f'local dissector_table = DissectorTable.get("{name}")' + '\n')
			out.write(f'dissector_table:add({key}, {proto_name}_proto)' + '\n')


def _get_display(d):
	if 'STRING' in d.format_type:
		return 'base.UNICODE' if d.charset and 'utf' in d.charset else 'base.ASCII'
	elif d.format_type == 'BYTES':
		return 'base.NONE'
	else:
		return 'base.HEX' if d.show and 'hex' in d.show else 'base.DEC'

