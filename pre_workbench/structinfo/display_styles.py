
def dec(i):
	return str(i)

def hex(i):
	if isinstance(i, bytes):
		return ":".join("%02x" % a for a in i)
	else:
		return "0x%x" % i

def dotted_quad(b):
	return ".".join("%d" % i for i in b)

def ip6(b):
	return ".".join("%x" % i for i in b)


