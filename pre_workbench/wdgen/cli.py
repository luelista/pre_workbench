import argparse
import json

import binascii
import sys

from lark import Transformer

from pre_workbench.structinfo.expr import Expression
from pre_workbench.structinfo.parsecontext import ParseContext, stack_frame


class WDGenVisitor:
	def __init__(self, context):
		self.context = context
		self.ws_field_defs = list()

	def structfi(self, desc):
		print("  -- struct " + self.context.get_path("_"))
		for name, child, comment in desc.fi.children:
			self.context.id = name
			child.visit(self.context, self)

	def variantstructfi(self, desc):
		print("  -- variant " + self.context.get_path("_"))

	def repeatstructfi(self, desc):
		print("  -- variant " + self.context.get_path("_"))

	def switchfi(self, desc):
		print("  -- switch " + self.context.get_path("_"))

	def namedfi(self, desc):
		print("  -- named " + self.context.get_path("_"))

	def fieldfi(self, desc):
		print("  -- field " + self.context.get_path("_")+" "+desc.fi.format_type)
		id = self.context.get_path("_")
		method = "add_le" if self.context.get_param("endianness") == "<" else "add"
		print("  len = " + str(desc.fi.size))
		print("  subtree:" + method + "(" + "pf_" + id + ", buffer(offset, len))")
		print("  offset = offset + len")
		show = desc.params.get("show", "")
		self.ws_field_defs.append((self.context.get_path("_"),self.context.top_id(),desc.fi.format_type))


	def unionfi(self, desc):
		print("  -- union " + self.context.get_path("_"))

	def bitstructfi(self, desc):
		print("  -- bits " + self.context.get_path("_"))
		for key, len in desc.fi.children:
			print("  -- "+key+" "+str(len))
			self.ws_field_defs.append((self.context.get_path("_"), "UINT32"))



def run_cli():
	parser = argparse.ArgumentParser(description='PRE Workbench - Wireshark Dissector Generator')
	parser.add_argument('-P', '--project', metavar='DIR', type=str,
						help='Grammar definitions from project directory')
	parser.add_argument('-F', '--grammar-file', metavar='FILENAME', type=str,
						help='Grammar definitions from text file')
	parser.add_argument('-e', '--grammar-string', metavar='GRAMMAR', type=str,
						help='Grammar definitions from command line argument')
	parser.add_argument('-d', '--definition', metavar='NAME', type=str,
						help='Name of start grammar definition. Uses first if unspecified')
	parser.add_argument('-l', '--language', metavar='LANG', type=str,
						help='Programming language to generate (supported: lua, c, ')

	r = parser.parse_args()
	if r.project:
		from pre_workbench.project import Project
		project = Project(r.project)
		fic = project.formatInfoContainer
	elif r.grammar_file:
		from pre_workbench.structinfo.parsecontext import FormatInfoContainer
		fic = FormatInfoContainer(load_from_file=r.grammar_file)
	elif r.grammar_string:
		from pre_workbench.structinfo.parsecontext import FormatInfoContainer
		fic = FormatInfoContainer(load_from_string=r.grammar_string)
	else:
		print("Missing grammar")
		parser.print_help()
		sys.exit(1)

	definition = r.definition if r.definition else fic.main_name
	proto_name = fic.main_name
	print(f'{proto_name}_proto = Proto("{proto_name}", "{proto_name} Protocol")')
	print(f'function {proto_name}_proto.dissector(buffer, pinfo, tree)')
	print(f'  local subtree = tree:add({proto_name}_proto, buffer(), "Protocol Data {definition}")')
	print(f'  parse_{definition}(buffer, pinfo, subtree)')
	print(f'end')
	context = ParseContext(fic)
	generator = WDGenVisitor(context)
	for key, value in fic.definitions.items():
		print("-- definition "+key)
		print("function parse_"+key+"(buffer, pinfo, subtree)")
		context.id = key
		value.visit(context, generator)
		print("end")
		print("")



if __name__ == '__main__':
	run_cli()
