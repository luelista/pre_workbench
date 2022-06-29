import argparse
import json

import binascii
import sys

from pre_workbench.structinfo.parsecontext import ParseContext


def run_cli():
	parser = argparse.ArgumentParser(description='Protocol Reverse Engineering Workbench CLI Parser')
	parser.add_argument('-P', '--project', metavar='DIR', type=str,
						help='Grammar definitions from project directory')
	parser.add_argument('-F', '--grammar-file', metavar='FILENAME', type=str,
						help='Grammar definitions from text file')
	parser.add_argument('-e', '--grammar-string', metavar='GRAMMAR', type=str,
						help='Grammar definitions from command line argument')
	parser.add_argument('-d', '--definition', metavar='NAME', type=str,
						help='Name of start grammar definition. Uses first if unspecified')
	parser.add_argument('-i', '--input-file', metavar='FILENAME', type=str,
						help='File to parse')
	parser.add_argument('-x', '--input-hex', metavar='HEXSTRING', type=str,
						help='Hex string to parse')
	parser.add_argument('--json', action="store_true",
						help='Print json output')

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

	if r.input_file:
		with open(r.input_file, "rb") as f:
			data = f.read()
	elif r.input_hex:
		data = binascii.unhexlify(r.input_hex)
	else:
		data = sys.stdin.read()

	pc = ParseContext(fic, data)
	result = pc.parse(definition)
	print(json.dumps(result, indent=4))

if __name__ == '__main__':
	run_cli()
