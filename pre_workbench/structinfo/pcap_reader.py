import logging
from datetime import datetime

from pre_workbench.objects import ByteBufferList, ByteBuffer
from pre_workbench.structinfo.parsecontext import FormatInfoContainer

PcapFormats = FormatInfoContainer(load_from_string="""

pcap_file variant {
	struct (endianness="<", section="pcap file, little endian"){
		header pcap_header
		packets repeat pcap_packet
	}
	struct (endianness=">", section="pcap file, big endian"){
		header pcap_header
		packets repeat pcap_packet
	}
	repeat(endianness="<", section="pcapNG file, little endian") pcapng_block
	repeat(endianness=">", section="pcapNG file, big endian") pcapng_block
}

pcap_header struct (section="pcap file header"){
	magic_number UINT32(description="'A1B2C3D4' means the endianness is correct", magic=2712847316)
	version_major UINT16(description="major number of the file format")
	version_minor UINT16(description="minor number of the file format")
	thiszone INT32(description="correction time in seconds from UTC to local time (0)")
	sigfigs UINT32(description="accuracy of time stamps in the capture (0)")
	snaplen UINT32(description="max length of captured packed (65535)")
	encap_proto UINT32(description="type of data link (1 = ethernet)")
}

pcap_packet struct {
	pheader struct (section="pcap packet header"){
		ts_sec UINT32(description="timestamp seconds")
		ts_usec UINT32(description="timestamp microseconds")
		incl_len UINT32(description="number of octets of packet saved in file")
		orig_len UINT32(description="actual length of packet")
	}
	payload BYTES(size=(pheader.incl_len))
}

pcapng_block struct (section="pcapNG block"){
	block_type UINT32(color="#999900", show="0x%08X")
	block_length UINT32(color="#666600")
	block_payload BYTES(size=(block_length - 12), parse_with=pcapng_block_payload)
	block_length2 UINT32(color="#666600")
}

pcapng_block_payload switch block_type {
	case 0x0A0D0D0A: pcapng_SHB
	case 1: pcapng_IDB
	case 6: pcapng_EPB
	case 5: BYTES
}

pcapng_SHB struct {
	byte_order_magic UINT32(magic=439041101, color="green", show="0x%08X")
	version_major UINT16
	version_minor UINT16
	section_length INT64
	options pcapng_options
}

pcapng_IDB struct {
	linktype UINT16
	reserved UINT16
	snaplen UINT32
	options pcapng_options
}

pcapng_EPB struct {
	interface_id UINT32
	timestamp_hi UINT32
	timestamp_lo UINT32
	cap_length UINT32
	orig_length UINT32
	payload BYTES(size="cap_length")
	payload_padding BYTES(size="3-((cap_length-1)&3)", textcolor="#888888")
}

pcapng_options repeat struct {
		code UINT16(color="#660666")
		length UINT16
		value BYTES(size=(length), textcolor="#d3ebff")
		padding BYTES(size=(pad(4)), textcolor="#666")
	}
""")


def read_pcap_file(f):
	from pre_workbench.structinfo.parsecontext import ParseContext
	ctx = ParseContext(PcapFormats, f.read())
	pcapfile = ctx.parse()
	plist = ByteBufferList()
	if 'header' in pcapfile:
		# pcap classic
		plist.metadata.update(pcapfile['header'])
		for packet in pcapfile['packets']:
			plist.add(ByteBuffer(packet['payload'], metadata=packet['pheader']))
	else:
		# pcapNG
		plist.metadata['interfaces'] = []
		for block_wrapper in pcapfile:
			block = block_wrapper['block_payload']
			if isinstance(block, dict) and 'payload' in block:
				meta = {'interface_id': block['interface_id'],
						'timestamp': datetime.fromtimestamp(
							(block['timestamp_hi'] << 32 | block['timestamp_lo']) / 1000000.0),
						'cap_length': block['cap_length'],
						'orig_length': block['orig_length'],
						}
				plist.add(ByteBuffer(block['payload'], metadata=meta))
			elif block_wrapper['block_type'] == 0x0A0D0D0A:  # SHB
				plist.metadata['pcap_version'] = "%d.%d" % (block['version_major'], block['version_minor'])
				for opt in block['options']:
					update_option(plist.metadata, "SHB", opt["code"], opt["value"])
			elif block_wrapper['block_type'] == 1:  # IDB
				interface = {'linktype': block['linktype'], 'snaplen': block['snaplen']}
				for opt in block['options']:
					update_option(interface, "IDB", opt["code"], opt["value"])
				plist.metadata['interfaces'].append(interface)
			else:
				logging.info("PCAPng - unhandled header block: %r", block_wrapper)
	return plist


opt_names = {
	"*": {
		1: ("opt_comment", True),  # yes
	},
	"SHB": {
		2: ("shb_hardware", False),  # no
		3: ("shb_os", False),  # no
		4: ("shb_userappl", False),  # no
	},
	"IDB": {
		2: ("if_name", False),  # variable	no
		3: ("if_description", False),  # variable	no
		4: ("if_IPv4addr", True),  # 8	yes
		5: ("if_IPv6addr", True),  # 17	yes
		6: ("if_MACaddr", False),  # 6	no
		7: ("if_EUIaddr", False),  # 8	no
		8: ("if_speed", False),  # 8	no
		9: ("if_tsresol", False),  # 1	no
		10: ("if_tzone", False),  # 4	no
		11: ("if_filter", False),  # variable, minimum 1	no
		12: ("if_os", False),  # variable	no
		13: ("if_fcslen", False),  # 1	no
		14: ("if_tsoffset", False),  # 8	no
		15: ("if_hardware", False),  # variable	no
		16: ("if_txspeed", False),  # 8	no
		17: ("if_rxspeed", False),  # 8	no
	}
}


def get_option_info(block_type, code):
	if code in opt_names["*"]:
		return opt_names["*"][code]
	elif block_type in opt_names and code in opt_names[block_type]:
		return opt_names[block_type][code]
	else:
		return "code_%d" % code, True


def update_option(target, block_type, code, value):
	if code == 0: return
	name, multiple = get_option_info(block_type, code)
	if multiple:
		if not name in target:
			target[name] = [value]
		else:
			target[name].append(value)
	else:
		target[name] = value