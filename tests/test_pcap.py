import logging
import os.path

# sample files from https://github.com/hadrielk/pcapng-test-generator

from pre_workbench.structinfo.pcap_reader import read_pcap_file
from tests.parse_helper import open_fixture

def test_load_pcapng_le():
	"""
	Description: Two IDBs different linktype
	Category:    basic

	Block counts:
		EPB: 5
		IDB: 2
		SHB: 1

	Block sequence: SHB, IDB, IDB, EPB, EPB, EPB, EPB, EPB
	"""
	result = read_pcap_file(open_fixture("test006_le.pcapng"))
	assert len(result) == 5   # file contains 5 EPB blocks
	assert len(result.metadata['interfaces']) == 2   # file contains 2 IDB blocks


def test_load_pcapng_be():
	"""
	Description: Two IDBs different linktype
	Category:    basic

	Block counts:
		EPB: 5
		IDB: 2
		SHB: 1

	Block sequence: SHB, IDB, IDB, EPB, EPB, EPB, EPB, EPB
	"""
	result = read_pcap_file(open_fixture("test006_be.pcapng"))
	assert len(result) == 5 # file contains 5 EPB blocks
	assert len(result.metadata['interfaces']) == 2 # file contains 2 IDB blocks


def test_load_pcapng_difficult_be():
	"""
	Description: ISBs with various options, in different SHB sections
	Category:    difficult

	Block counts:
		EPB: 3
		IDB: 5
		ISB: 4
		SHB: 3
		SPB: 1

	Block sequence: SHB, IDB, IDB, EPB, ISB, SHB, IDB, EPB, ISB, SPB, SHB, IDB, IDB, ISB, EPB, ISB
	"""
	result = read_pcap_file(open_fixture("test201.pcapng"))
	print(result)
	assert len(result) == 4 # file contains 3 EPB blocks and 1 SPB block
	assert len(result.metadata['interfaces']) == 5 # file contains 5 IDB blocks


