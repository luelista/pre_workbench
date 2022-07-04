import inspect

from pre_workbench.structinfo.parsecontext import FormatInfoContainer
from pre_workbench.structinfo.parser import parse_definition

def assert_text(d, code):
	assert d.to_text().replace("\t", " " * 8) == inspect.cleandoc(code)

def test_comment_on_root():
	definition = """
	/* foo */
	DEFAULT struct {
	}
	
	aaa struct {
	}
	
	/* bar */
	bbb struct {
	}
	
	ccc struct {
	}
	"""
	fic = FormatInfoContainer(load_from_string=definition)
	assert_text(fic, definition)

def test_comment_before_structfield():
	code = """
	struct {
		magic UINT32
		/* foo */
		header UINT32
		/* bar */
		payload UINT32
	}
	"""
	d = parse_definition(code, "anytype")
	assert_text(d, code)


def test_comment_in_union():
	code = """
	union {
		/* foo */
		signed INT32
		unsigned UINT32
	}
	"""
	d = parse_definition(code, "anytype")
	assert_text(d, code)


def test_size_syntax():
	code = """
	struct {
		/* foo */
		bytefield BYTES[8]
		len UINT8
		header struct {
			len2 UINT8
		}
		test BYTES[len]
		test2 STRING[header.len](charset="utf8")
	}
	"""
	d = parse_definition(code, "anytype")
	assert_text(d, code)


def test_complex_statement_1():
	code = """
	repeat(endianness=">", charset="utf-8") struct {
			type UINT16(base="HEX")
			length UINT8
			value STRING[length]
		}
	"""
	d = parse_definition(code, "anytype")
	assert_text(d, code)

