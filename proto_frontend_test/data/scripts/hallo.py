
import sys
from collections import defaultdict
from scapy.all import sr1,IP,ICMP,rdpcap,sniff
import cbor

def expand(x):
    yield x
    while x.payload:
        x = x.payload
        yield x
def show_packet_tree(pkg):
	results = list()

	for layer in expand(pkg):
		# Get layer name
		#layer_tmp_name = str(layer.__dict__["aliastypes"][0])
		#layer_start_pos = layer_tmp_name.rfind(".") + 1
		#layer_name = layer_tmp_name[layer_start_pos:-2].lower()
		layer_name = layer.name

		# Get the layer info
		tmp_t = {}
		for x, y in layer.__dict__["default_fields"].items():
			if y and not isinstance(y, (str, int, long, float, list, dict)):
				tmp_t[x].update(pkg_to_json(y))
			else:
				tmp_t[x] = y

		try:
			tmp_t = {}
			for x, y in layer.__dict__["fields"].items():
				if y and not isinstance(y, (str, int, long, float, list, dict)):
					tmp_t[x].update(pkg_to_json(y))
				else:
					tmp_t[x] = y

		except KeyError:
			# No custom fields
			pass

		results.append(tmp_t)

	return results


#pf = rdpcap(sys.argv[1])
sniff(store=0, prn=show_packet_tree, offline=sys.argv[1])




