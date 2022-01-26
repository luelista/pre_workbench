
# PRE Workbench
# Copyright (C) 2022 Mira Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from scapy.all import *
import sys
from collections import defaultdict
import cbor

script_file = sys.argv[1]
pcap_file = sys.argv[2]
outfile = open(sys.argv[3], "wb")

with open(script_file) as f:
    code = compile(f.read(), script_file, 'exec')
    exec(code) #, global_vars, local_vars)


output = list()
def add_packet_tree2(p):
	wholebinary, layerlist = p.build_ps()
	offset = 0
	out_protos = []
	for layer, fields in reversed(layerlist):
		out_fields = []
		#print(dir(layer))
		#['__all_slots__', '__bool__', '__bytes__', '__class__', '__contains__', '__deepcopy__', '__delattr__', '__delitem__', '__dict__', '__dir__', '__div__', '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__getitem__', '__getstate__', '__gt__', '__hash__', '__init__', '__iter__', '__iterlen__', '__le__', '__len__', '__lt__', '__module__', '__mul__', '__ne__', '__new__', '__nonzero__', '__rdiv__', '__reduce__', '__reduce_ex__', '__repr__', '__rmul__', '__rtruediv__', '__setattr__', '__setitem__', '__setstate__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__truediv__', '__weakref__', '_answered', '_do_summary', '_name', '_overload_fields', '_pkt', '_show_or_dump', '_superdir', '_tmp_dissect_pos', '_unpickle', 'add_payload', 'add_underlayer', 'aliastypes', 'answers', 'build', 'build_done', 'build_padding', 'build_ps', 'canvas_dump', 'class_default_fields', 'class_default_fields_ref', 'class_dont_cache', 'class_fieldtype', 'class_packetfields', 'clear_cache', 'clone_with', 'command', 'copy', 'copy_field_value', 'copy_fields_dict', 'decode_payload_as', 'default_fields', 'default_payload_class', 'delfieldval', 'direction', 'display', 'dissect', 'dissection_done', 'do_build', 'do_build_payload', 'do_build_ps', 'do_dissect', 'do_dissect_payload', 'do_init_cached_fields', 'do_init_fields', 'explicit', 'extract_padding', 'fields', 'fields_desc', 'fieldtype', 'firstlayer', 'fragment', 'from_hexcap', 'get_field', 'getfield_and_val', 'getfieldval', 'getlayer', 'guess_payload_class', 'hashret', 'haslayer', 'hide_defaults', 'init_fields', 'lastlayer', 'layers', 'load', 'lower_bonds', 'match_subclass', 'mysummary', 'name', 'original', 'overload_fields', 'overloaded_fields', 'packetfields', 'payload', 'payload_guess', 'pdfdump', 'post_build', 'post_dissect', 'post_dissection', 'post_transforms', 'pre_dissect', 'prepare_cached_fields', 'psdump', 'raw_packet_cache', 'raw_packet_cache_fields', 'remove_payload', 'remove_underlayer', 'route', 'self_build', 'sent_time', 'setfieldval', 'show', 'show2', 'show_indent', 'show_summary', 'sniffed_on', 'sprintf', 'summary', 'svgdump', 'time', 'underlayer', 'upper_bonds', 'wirelen']
		info = {'name':layer.name,'pos':offset,'show':layer.mysummary()}
		for field, display, binary in fields:
			out_fields.append( ({'name':layer.name+'.'+field.name, 'show':display, 'value':binary,'pos':offset, 'size':len(binary)}, []) )
			offset += len(binary)
		info['size'] = offset - info['pos']
		out_protos.append( (info, out_fields) )
		print(info, out_fields)

	output.append((
		{'frame.time_epoch':p.time},
		out_protos
	))

#pf = rdpcap(pcap_file)
sniff(store=0, prn=add_packet_tree2, offline=pcap_file)


outfile.write(cbor.dumps({
    "script":script_file,
    "pcap":pcap_file,
    "packets":output
    }))
outfile.close()
