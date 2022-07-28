import inspect
import os.path
import tempfile
import struct

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


def make_pcap(pcap_data_link_type, lst):
	# Global Header Values
	PCAP_GLOBAL_HEADER_FMT = "@ I H H i I I I "
	PCAP_MAGICAL_NUMBER = 2712847316
	PCAP_MJ_VERN_NUMBER = 2
	PCAP_MI_VERN_NUMBER = 4
	PCAP_LOCAL_CORECTIN = 0
	PCAP_ACCUR_TIMSTAMP = 0
	PCAP_MAX_LENGTH_CAP = 65535
	PCAP_DATA_LINK_TYPE = pcap_data_link_type

	pcap_header = struct.pack(
		PCAP_GLOBAL_HEADER_FMT,
		PCAP_MAGICAL_NUMBER,
		PCAP_MJ_VERN_NUMBER,
		PCAP_MI_VERN_NUMBER,
		PCAP_LOCAL_CORECTIN,
		PCAP_ACCUR_TIMSTAMP,
		PCAP_MAX_LENGTH_CAP,
		PCAP_DATA_LINK_TYPE,
	)

	with tempfile.NamedTemporaryFile(delete=False) as ofile:
		ofile.write(pcap_header)

		for bbuf in lst.buffers:
			length = len(bbuf.buffer)
			ts_sec = 0
			ts_usec = 0
			pcap_packet = (
				struct.pack("@ I I I I", ts_sec, ts_usec, length, length) + bbuf.buffer
			)
			ofile.write(pcap_packet)

	return ofile.name

