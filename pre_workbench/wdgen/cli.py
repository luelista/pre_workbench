import argparse
import sys

from pre_workbench.wdgen.lua import generate_lua_dissector

def run_cli():
	parser = argparse.ArgumentParser(description='PRE Workbench - Wireshark Dissector Generator')
	parser.add_argument('-P', '--project', metavar='DIR', type=str,
						help='Grammar definitions from project directory')
	parser.add_argument('-F', '--grammar-file', metavar='FILENAME', type=str,
						help='Grammar definitions from text file')
	parser.add_argument('-e', '--grammar-string', metavar='GRAMMAR', type=str,
						help='Grammar definitions from command line argument')
	parser.add_argument('-t', '--only-types', metavar='TYPENAMES', type=str,
						help='Generate code only for specified types (comma-separated list)')
	parser.add_argument('-d', '--definition', metavar='NAME', type=str,
						help='Name of start grammar definition. Uses first if unspecified')
	parser.add_argument('-l', '--language', metavar='LANG', type=str,
						help='Programming language to generate (supported: lua)', default="lua")
	parser.add_argument('--dissector-table', metavar='NAME:KEY', type=str, action='append',
						help='Register the protocol in the given dissector table, under the given key')
	parser.add_argument('-o', '--output-file', metavar='FILENAME', type=str,
						help='Output filename for generated code (default: "-" for stdout)', default="-")

	r = parser.parse_args()
	if r.project:
		from pre_workbench.project import Project
		project = Project(r.project, 'PROJECT', '')
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

	if r.output_file == '-':
		def out(s):
			print(s)
	else:
		f = open(r.output_file, "w")
		def out(s):
			f.write(s + '\n')

	if r.language == 'lua':
		generate_lua_dissector(r, fic, out)
	else:
		raise NotImplemented

if __name__ == '__main__':
	run_cli()

