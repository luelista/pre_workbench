import argparse
import json
import os

import binascii
import sys

from pre_workbench.structinfo.parsecontext import ParseContext
from pre_workbench.util import PerfTimer


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
	parser.add_argument( '--input-pcap-file', metavar='FILENAME', type=str,
						help='PCAP File to parse')
	parser.add_argument('-i', '--input-file', metavar='FILENAME', type=str,
						help='Raw binary file to parse')
	parser.add_argument('-x', '--input-hex', metavar='HEXSTRING', type=str,
						help='Hex string to parse')
	parser.add_argument('--json', action="store_true",
						help='Print json output')
	parser.add_argument('--print', action="store_true",
						help='Print with Python print function')

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

	definition = r.definition if r.definition else fic.main_name

	if r.input_pcap_file:
		with PerfTimer('Load PCAP'):
			with open(r.input_pcap_file, "rb") as f:
				if os.environ.get('PCAP','')=='dpkt':
					import dpkt
					plist = [buf for ts,buf in dpkt.pcap.Reader(f)]
				else:
					from pre_workbench.structinfo.pcap_reader import read_pcap_file
					plist = [bbuf.buffer for bbuf in read_pcap_file(f).buffers]
		with PerfTimer('Parse Data'):
			for buf in plist:
				parse_data(fic, buf, definition, r)
	else:
		if r.input_file:
			with open(r.input_file, "rb") as f:
				data = f.read()
		elif r.input_hex:
			data = binascii.unhexlify(r.input_hex)
		else:
			data = sys.stdin.read()
		parse_data(fic, data, definition, r)

def parse_data(fic, data, definition, r):
	pc = ParseContext(fic, data)
	result = pc.parse(definition)
	if r.json:
		print(json.dumps(result, indent=4, default=str_helper))
	else:
		print(result)

def str_helper(obj):
	if isinstance(obj, (bytes, bytearray)):
		return binascii.hexlify(obj).decode('ascii').upper()
	else:
		return str(obj)

if __name__ == '__main__':
	run_cli()
