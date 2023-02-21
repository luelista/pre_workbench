# PRE Workbench
# Copyright (C) 2022 Mira Weller
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
"""
Encoder/decoder for the XDRmap binary format

This format allows maps (dictionaries) and lists of values to be stored
in a format based on the xdrlib module. It has similar capabilities as JSON,
with added support of byte arrays and UUIDs.
The loads and dumps methods allow the specification of a magic value, which
is prefixed to / expected as prefix of the encoded data, to simplify the
creation of custom binary file formats.
"""


import sys
import xdrlib
from uuid import UUID
import logging

from pre_workbench.typeregistry import TypeRegistry

XDRM_inlong = 0b000  # rest: value
XDRM_number = 0b001  # rest: 0x0800 = hyper, 0x0802 = double, 0x0010 = null, 0x0011 = undefined, 0x0012 = true, 0x0013 = false, 0x1005 = UUID
XDRM_utf8   = 0b100  # rest: length in bytes
XDRM_bytes  = 0b101  # rest: length in bytes
XDRM_array  = 0b110  # rest: count
XDRM_map    = 0b111  # rest: pair-count

Serializable = TypeRegistry("Serializable")

def loads(data, magic=bytes()):
	if data[0:len(magic)] != magic:
		raise Exception("Invalid file format (magic number expected=%r, got=%r)" % (magic, data[0:len(magic)]))
	data = data[len(magic):]
	unpacker = xdrlib.Unpacker(data)
	return _unpack_xdrm(unpacker)


def dumps(data, magic=bytes()):
	packer = xdrlib.Packer()
	_pack_xdrm(packer, data)
	return magic + packer.get_buffer()


def _unpack_xdrm(unpacker):
	typecode = unpacker.unpack_uint()
	type, rest = typecode & 0b111, typecode >> 3
	if type == XDRM_inlong:
		return rest
	elif type == XDRM_number and rest == 0x0800:
		return unpacker.unpack_hyper()
	elif type == XDRM_number and rest == 0x0802:
		return unpacker.unpack_double()
	elif type == XDRM_number and rest in [0x0010, 0x0011]:
		return None
	elif type == XDRM_number and rest == 0x0012:
		return True
	elif type == XDRM_number and rest == 0x0013:
		return False
	elif type == XDRM_number and rest == 0x1005:
		return UUID(bytes=unpacker.unpack_fopaque(0x10))
	elif type == XDRM_number and (rest & 0x1fff) == 0x1fff:
		serialize_id = rest >> 13  #16-bit class ID
		return Serializable.find(class_id=serialize_id).__deserialize__(_unpack_xdrm(unpacker))
	elif type == XDRM_utf8:
		return unpacker.unpack_fstring(rest).decode("utf-8",'surrogateescape')
	elif type == XDRM_bytes:
		return unpacker.unpack_fopaque(rest)
	elif type == XDRM_array:
		result = [_unpack_xdrm(unpacker) for _ in range(rest)]
		return result
	elif type == XDRM_map:
		result = {}
		for _ in range(rest):
			key = _unpack_xdrm(unpacker)
			result[key] = _unpack_xdrm(unpacker)
		return result
	else:
		raise Exception("invalid typecode 0x%08x (type=%d, rest=0x%x) at offset 0x%x" % (typecode, type, rest, unpacker.get_position()))


def _pack_xdrm(packer, data):
	typ = type(data)
	if typ.__name__ == 'QByteArray': data=bytes(data); typ=bytes
	if typ is int and data  >= 0 and data < 0x1fffffff:
		packer.pack_uint(XDRM_inlong | (data << 3))
	elif typ is int:
		packer.pack_uint(XDRM_number | (0x0800 << 3))
		packer.pack_hyper(data)
	elif typ is float:
		packer.pack_uint(XDRM_number | (0x0802 << 3))
		packer.pack_double(data)
	elif typ is str:
		bin = data.encode("utf-8",'surrogateescape')
		packer.pack_uint(XDRM_utf8 | (len(bin) << 3))
		packer.pack_fopaque(len(bin), bin)
	elif isinstance(data, (list, tuple)):
		packer.pack_uint(XDRM_array | (len(data) << 3))
		for el in data:
			_pack_xdrm(packer, el)
	elif isinstance(data, dict):
		packer.pack_uint(XDRM_map | (len(data) << 3))
		for key, value in data.items():
			_pack_xdrm(packer, key)
			_pack_xdrm(packer, value)
	elif data == None:
		packer.pack_uint(XDRM_number | (0x0010 << 3))
	elif data == True:
		packer.pack_uint(XDRM_number | (0x0012 << 3))
	elif data == False:
		packer.pack_uint(XDRM_number | (0x0013 << 3))
	elif isinstance(data, (bytes, bytearray)):
		packer.pack_uint(XDRM_bytes | (len(data) << 3))
		packer.pack_fopaque(len(data), data)
	elif typ is UUID:
		packer.pack_uint(XDRM_number | (0x1005 << 3))
		packer.pack_fopaque(0x10, data.bytes)
	elif hasattr(data, "__serialize__") and hasattr(type(data), "class_id"):
		logging.warning("WARNING: calling serialize on "+str(typ)+" ")
		packer.pack_uint(XDRM_number | (0x1fff << 3) | (type(data).class_id << 16))
		_pack_xdrm(packer, data.__serialize__())
	else:
		#raise Exception("can't pack "+str(typ))
		logging.warning("WARNING: packing "+str(typ)+" as str")
		bin = str(data).encode("utf-8",'surrogateescape')
		packer.pack_uint(XDRM_utf8 | (len(bin) << 3))
		packer.pack_fopaque(len(bin), bin)


def run_cli():
	import yaml
	import argparse
	parser = argparse.ArgumentParser(description='XDRmap encoder/decoder')
	parser.add_argument('-m', '--magic', metavar='HEXSTR', type=str, default='',
						help='Magic value prefix, encoded as hex string')
	parser.add_argument('-D', '--decode', action='store_true',
						help='Decodes input from XDRmap to YAML')
	parser.add_argument('-E', '--encode', action='store_true',
						help='Encodes input from YAML to XDRmap')
	parser.add_argument('-i', '--input', type=str, default='-',
						help='Input file (default: "-" for stdin)')
	parser.add_argument('-v', '--verbose', action='store_true',
						help='Enable verbose logging to stderr')
	args = parser.parse_args()
	logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
	try:
		if args.encode and args.decode: raise Exception("Invalid arguments, can't encode and decode at the same time")

		from binascii import unhexlify
		magic = unhexlify(args.magic)
		if args.input == '-':
			data = sys.stdin.buffer.read()
		else:
			with open(args.input, 'rb') as f:
				data = f.read()
		if args.encode or (data[0:3] == b'---' and not args.decode):
			logging.debug("Encoding")
			o = yaml.unsafe_load(data.decode('utf-8'))
			sys.stdout.buffer.write(dumps(o, magic=magic))
		else:
			logging.debug("Decoding from %d bytes of data", len(data))
			o = loads(data, magic=magic)
			print(yaml.dump(o, explicit_start=True, sort_keys=False))
	except EOFError:
		logging.error("XDRmap failed: Unexpected end of file\n")
		sys.exit(2)
	except Exception as ex:
		logging.exception("XDRmap failed")
		sys.exit(1)


if __name__ == '__main__':
	run_cli()
