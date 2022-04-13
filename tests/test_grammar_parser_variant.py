import pytest

from parse_helper import parse_me
from pre_workbench.structinfo.exceptions import invalid, incomplete

# Test cases specific to the "variant" type

def test_first_incomplete_variant_fail():
	with pytest.raises(incomplete):
		parse_me("""
		DEFAULT variant {
			UINT32
			UINT16
		}
		""", "11 22", {})


def test_second_incomplete_variant_success():
	parse_me("""
	DEFAULT variant {
		UINT8
		UINT32
		UINT16
	}
	""", "11 22", 0x11)


def test_invalid_variant_success():
	parse_me("""
	DEFAULT variant(endianness=">") {
		UINT32(magic=1)
		UINT32(magic=2)
	}
	""", "00 00 00 02", 2)


def test_all_invalid_variant_fail():
	with pytest.raises(invalid):
		parse_me("""
		DEFAULT variant(endianness=">") {
			UINT32(magic=1)
			UINT32(magic=2)
		}
		""", "00 00 00 03", {})


test_variant_reset_offset_code = """
	capture_file variant {
		pcap_file(endianness=">")
		pcap_file(endianness="<")
	}
	pcap_file struct {
		dummy UINT32
		magic_number UINT32(description="'A1B2C3D4' means the endianness is correct", magic=2712847316)
	}
	"""
def test_variant_reset_offset_1():
	parse_me(test_variant_reset_offset_code,
	"  00000001 A1B2C3D4 ", {
		'dummy': 1,
		'magic_number': 0xA1B2C3D4
	})

def test_variant_reset_offset_2():
	parse_me(test_variant_reset_offset_code,
	 "  01000000 D4C3B2A1 ", {
		 'dummy': 1,
		 'magic_number': 0xA1B2C3D4
	 })
