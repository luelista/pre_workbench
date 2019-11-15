
from binascii import unhexlify


from pre_workbench.structinfo import LoggingParseContext, FormatInfo, FormatInfoContainer, ParseContext, invalid

log = False

def parse_me(definition, hexstring, expected):
	fic = FormatInfoContainer()
	fic.load_from_string(definition)
	if log:
		pc = LoggingParseContext(fic, unhexlify(hexstring.replace(" ","")))
	else:
		pc = ParseContext(fic, unhexlify(hexstring.replace(" ","")))
	result = pc.parse()
	#print(result)
	assert result == expected

