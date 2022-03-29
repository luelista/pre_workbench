
from binascii import unhexlify

from pre_workbench.structinfo.parsecontext import FormatInfoContainer, LoggingParseContext, ParseContext

log = False

def parse_me(definition, hexstring, expected):
	fic = FormatInfoContainer(load_from_string=definition)
	if log:
		pc = LoggingParseContext(fic, unhexlify(hexstring.replace(" ","")))
	else:
		pc = ParseContext(fic, unhexlify(hexstring.replace(" ","")))
	result = pc.parse()
	#print(result)
	assert result == expected

