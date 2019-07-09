
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
	output.append({
        't':p.time,
        'f':[
            (layer.name, field.name, display, binary)
            for layer, fields in reversed(layerlist)
            for field, display, binary in fields
            ]
    })

#pf = rdpcap(pcap_file)
sniff(store=0, prn=add_packet_tree2, offline=pcap_file)


outfile.write(cbor.dumps({
    "script":script_file,
    "pcap":pcap_file,
    "packets":output
    }))
outfile.close()
