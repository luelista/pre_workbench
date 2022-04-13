import logging
import os.path

# sample files from https://wiki.wireshark.org/Development/PcapNg
# - dhcp_little_endian.pcapng (SHB, IDB, NRB, 4 * EPB; encoded in little-endian format)
# - dhcp_big_endian.pcapng (SHB, IDB, NRB, 4 * EPB; encoded in big-endian format)
from pre_workbench.structinfo.pcap_reader import read_pcap_file
from tests.parse_helper import open_fixture

def test_load_pcapng_le():
	result = read_pcap_file(open_fixture("test006_le.pcapng"))
	assert len(result) == 5   # file contains 5 EPB blocks
	assert len(result.metadata['interfaces']) == 2   # file contains 2 IDB blocks


def test_load_pcapng_be():
	result = read_pcap_file(open_fixture("test006_be.pcapng"))
	assert len(result) == 5 # file contains 5 EPB blocks
	assert len(result.metadata['interfaces']) == 2 # file contains 2 IDB blocks


def test_load_pcapng_difficult_be():
	# Description: ISBs with various options, in different SHB sections
	# Category:    difficult
	#
	# Block counts:
	#	EPB: 3
	#	IDB: 5
	#	ISB: 4
	#	SHB: 3
	#	SPB: 1
	#
	# Block sequence: SHB, IDB, IDB, EPB, ISB, SHB, IDB, EPB, ISB, SPB, SHB, IDB, IDB, ISB, EPB, ISB
	result = read_pcap_file(open_fixture("test201.pcapng"))
	print(result)
	assert len(result) == 4 # file contains 3 EPB blocks and 1 SPB block
	assert len(result.metadata['interfaces']) == 5 # file contains 5 IDB blocks


