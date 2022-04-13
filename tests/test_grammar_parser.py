import uuid

import pytest

from parse_helper import parse_me
from pre_workbench.structinfo.exceptions import invalid, incomplete


def test_repeated_struct():
	parse_me("""
		DEFAULT repeat(endianness=">", charset="utf-8") struct {
			type UINT16(base="HEX")
			length UINT8
			value STRING(size=(length))
		}
		""",
		"0001 05 3132333435  0002 01 42   0003 0a 41414141414141414141",
		[
			{'type': 1, 'length': 5, 'value': '12345'},
			{'type': 2, 'length': 1, 'value': 'B'},
			{'type': 3, 'length': 10, 'value': 'AAAAAAAAAA'},
		]
	)



def test_repeat_struct_union():
	parse_me("""
		DEFAULT repeat struct(endianness=">", charset="utf-8") {
			type UINT16(base="HEX")
			aaa union {
				x UINT32
				y BYTES(size=(4))
			}
		}
		""",
		"0001 12345678 0002 41424344 0003 00000001 ",
		[
			{'type': 1, 'aaa': {'x': 0x12345678, 'y': b"\x12\x34\x56\x78"}},
			{'type': 2, 'aaa': {'x': 0x41424344, 'y': b"ABCD"}},
			{'type': 3, 'aaa': {'x': 1, 'y': b"\0\0\0\x01"}},
		]
	)

def test_union():
	parse_me("""
		DEFAULT union(endianness=">") {
				x UINT32
				y BYTES(size=(4))
			}
		""",
		"41424344 ",
		{'x': 0x41424344, 'y': b"ABCD"}
	)


def1 = """
	DEFAULT struct(endianness=">") {
		magic_value UINT32(magic=0xabcd1100)
		vb varlen_bytes
		pascal_utf8 pascal_string(charset="utf-8")
		pascal_iso pascal_string(charset="iso-8859-1")
		c_utf8 c_string(charset="utf-8")
		c_iso c_string(charset="iso-8859-1")
	}
	pascal_string struct {
		length UINT16(endianness=">")
		value STRING(size=(length))
	}
	c_string STRINGZ
	varlen_bytes struct {
		len_length UINT8(endianness=">")
		length E_INT(endianness=">", size=(len_length))
		value BYTES(size=(length))
	}
	"""

def test_strings_types():
	parse_me(def1,
		"abcd1100     02 0005 0000000000    0004  f09f8c88  0009 4dfcdf696767616e67    4dc3bcc39f696767616e67 00    4dfcdf696767616e67 00",
					{
						'magic_value': 0xabcd1100,
						'vb': {'len_length': 2, 'length': 5, 'value': b'\0\0\0\0\0'},
						'pascal_utf8': {'length': 4, 'value':"🌈"},
						'pascal_iso': {'length': 9, 'value': "Müßiggang"},
						'c_utf8': "Müßiggang",
						'c_iso': "Müßiggang",
					}

	)


def test_magic_fail():
	with pytest.raises(invalid):
		parse_me(def1, "11223344     02 0005 0000000000    0004  f09f8c88  0009 4dfcdf696767616e67    4dc3bcc39f696767616e67 00    4dfcdf696767616e67 00", {})



def test_tagged_type_strings_endianness():
	parse_me("""
		DEFAULT repeat tagged_type
		tagged_type struct {
			type_id UINT16(endianness=">")
			value switch (type_id) {
				case (3): UINT32(endianness="<")
				case (4): UINT32(endianness=">")
				case (5): UINT64(endianness="<")
				case (6): UINT64(endianness=">")
				case (7): DOUBLE
				case (8): ETHER
				case (9): IPv4
				case (10): varlen_bytes
				case (16): pascal_string(charset="utf-8")
				case (17): pascal_string(charset="iso-8859-1")
				case (32): c_string(charset="utf-8")
				case (33): c_string(charset="iso-8859-1")
			}
		}
		pascal_string struct {
			length UINT16(endianness=">")
			value STRING(size=(length))
		}
		c_string STRINGZ
		varlen_bytes struct {
			len_length UINT8(endianness=">")
			length E_INT(endianness=">", size=(len_length))
			value BYTES(size=(length))
		}
		""",
		"0010 0005 4142434445    0020 4141414100    0004 00000001    0003 01000000    0006 0000000000000001    0008 aabbccddeeff  0009 0a010164    000a 01 01 01    000a 02 0001 01    000a 02 0005 0000000000 ",
		[{'type_id': 16, 'value': {'length': 5, 'value': 'ABCDE'}}, {'type_id': 32, 'value': 'AAAA'}, {'type_id': 4, 'value': 1}, {'type_id': 3, 'value': 1}, {'type_id': 6, 'value': 1}, {'type_id': 8, 'value': 'aa:bb:cc:dd:ee:ff'}, {'type_id': 9, 'value': '10.1.1.100'},
		 {'type_id': 10, 'value': {'len_length': 1, 'length': 1, 'value': b'\x01'}}, {'type_id': 10, 'value': {'len_length': 2, 'length': 1, 'value': b'\x01'}}, {'type_id': 10, 'value': {'len_length': 2, 'length': 5, 'value': b'\x00\x00\x00\x00\x00'}}
		 ]
	)

def test_ws_numbers():
	parse_me("""
	DEFAULT struct(endianness=">", charset="ascii") {
		none NONE
		bool BOOLEAN
		char CHAR
		euint E_UINT(size=(9))
		uint8 UINT8
		uint16 UINT16
		uint24 UINT24
		uint32 UINT32
		uint40 UINT40
		uint48 UINT48
		uint56 UINT56
		uint64 UINT64
		eint E_INT(size=(9))
		int8 INT8
		int16 INT16
		int24 INT24
		int32 INT32
		int40 INT40
		int48 INT48
		int56 INT56
		int64 INT64
		float FLOAT
		double DOUBLE
	}
	""",
	"  01  41  000000000000000001  01  0001  0000 01   0000 0001  0000 0000 01  0000 0000 0001  0000 0000 0000 01  0000 0000 0000 0001"
	"000000000000000001  01  0001  0000 01   0000 0001  0000 0000 01  0000 0000 0001  0000 0000 0000 01  0000 0000 0000 0001"
	"00000000  0000000000000000    ", {
				 'none': None,
				 'bool': True,
				 'char': 65,
				 'euint': 1,
				 'uint8': 1,
				 'uint16': 1,
				 'uint24': 1,
				 'uint32': 1,
				 'uint40': 1,
				 'uint48': 1,
				 'uint56': 1,
				 'uint64': 1,
				 'eint': 1,
				 'int16': 1,
				 'int24': 1,
				 'int32': 1,
				 'int40': 1,
				 'int48': 1,
				 'int56': 1,
				 'int64': 1,
				 'int8': 1,
				 'float': 0.0,
				 'double': 0.0,
			 })


def test_ws_bytes():
	parse_me("""
	DEFAULT struct(endianness=">", charset="ascii") {
		string STRING(size=(3))
		stringz STRINGZ
		uint_string UINT_STRING(size_len=(3))
		ether ETHER
		bytes BYTES(size=(3))
		uint_bytes UINT_BYTES(size_len=(3))
		ipv4 IPv4
		ipv6 IPv6
		idocument GUID
		idispatch GUID
	}
	""",
	"   414243     414243444500   000005 4142434445   aabbccddeeff     010203  000005 0102030405     0a010164"
	"     fe80 0000 0000 0000 14df 5963 6159 0eac"
	"bf1b29c2987341b79b45f22c50432bb1  0004020000000000c000000000000046", {
				 'bytes': b'\x01\x02\x03',
				 'ether': 'aa:bb:cc:dd:ee:ff',
				 'idispatch': uuid.UUID('00040200-0000-0000-c000-000000000046'),
				 'idocument': uuid.UUID('bf1b29c2-9873-41b7-9b45-f22c50432bb1'),
				 'ipv4': '10.1.1.100',
				 'ipv6': 'fe80:0000:0000:0000:14df:5963:6159:0eac',
				 'string': 'ABC',
				 'stringz': 'ABCDE',
				 'uint_bytes': b'\x01\x02\x03\x04\x05',
				 'uint_string': 'ABCDE'
	})

