
from binascii import unhexlify

from pre_workbench.structinfo.parsecontext import FormatInfoContainer, ParseContext

log = False

def parse_me(definition, hexstring, expected):
	fic = FormatInfoContainer(load_from_string=definition)
	pc = ParseContext(fic, unhexlify(hexstring.replace(" ","")), logging_enabled=log)
	result = pc.parse()
	#print(result)
	assert result == expected

