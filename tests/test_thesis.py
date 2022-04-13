
from parse_helper import parse_me


def test_thesis_struct():
	parse_me("""
	pascal_string struct {
		length UINT16(endianness=">")
		value STRING(size=(length), charset="ascii")
	}
	""",
	"  0004 41414141 ", {
		'length': 4,
		'value': 'AAAA'
	})
def test_thesis_repeat():
	parse_me("""
	int32_array struct(endianness=">") {
		count UINT16
		items repeat(times=(count)) INT32
	}
	""",
	"  0004 00000001 00000002 00000003 00000004 ", {
		'count': 4,
		'items': [1,2,3,4]
	})
def test_thesis_variant():
	parse_me("""
	capture_file variant {
		pcap_file(endianness=">")
		pcap_file(endianness="<")
	}
	pcap_file struct {
		magic_number UINT32(description="'A1B2C3D4' means the endianness is correct", magic=0xA1B2C3D4)
	}
	""",
	"  A1B2C3D4 ", {
		'magic_number': 0xA1B2C3D4
	})
def test_thesis_switch():
	parse_me("""
	my_packet struct {
		header struct {
			type UINT8
		}
		payload switch (header.type) {
			case (1): payload_1
			case (2): payload_2
		}
	}
	payload_1 struct {
		aaa INT8
	}
	payload_2 struct {
		bbb UINT8
	}
	""",
	"  02 FF ", {
		'header': { 'type': 2 },
		'payload': { 'bbb': 255 }
	})
def test_thesis_union():
	parse_me("""
	u_s union {
		unsigned UINT8
		signed INT8
	}
	""",
	"  FF ", {
		'unsigned': 255,
		'signed': -1
	})


