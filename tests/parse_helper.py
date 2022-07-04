import inspect
import os.path

from binascii import unhexlify

from pre_workbench.structinfo.parsecontext import FormatInfoContainer, ParseContext

log = False

def parse_me(definition, hexstring, expected):
	fic = FormatInfoContainer(load_from_string=definition)
	definition_roundtrip = fic.to_text().replace("\t", " " * 8)
	assert definition_roundtrip == inspect.cleandoc(definition)
	pc = ParseContext(fic, unhexlify(hexstring.replace(" ","")), logging_enabled=log)
	result = pc.parse()
	if pc.failed:
		raise pc.failed
	print(result)
	assert result == expected


def open_fixture(name, mode="rb"):
	return open(os.path.join(os.path.dirname(__file__), "fixtures/" + name), mode)

