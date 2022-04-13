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

