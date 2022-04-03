
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

import re
import subprocess
from xml.etree.ElementTree import XMLParser
import binascii, os, shutil

from pre_workbench.configs import getValue
from pre_workbench.objects import ByteBuffer
from pre_workbench.structinfo.parsecontext import ParseContext, BytebufferAnnotatingParseContext


class PdmlToPacketListParser:
	def __init__(self, destPacketList, parse_context_type=ParseContext):
		#self.interface = interface
		self.destination = destPacketList
		self.cur_proto = None
		self.parse_context_type = parse_context_type
		self.parse_context = None
		self.parser=XMLParser(target=self)


	def feed(self, data):
		self.parser.feed(data)
		
	def start(self,tag,attrib):
		if self.parse_context: self.parse_context.log("<%s>"%tag,attrib)
		if tag == "pdml":
			self.destination.metadata.update(attrib)
			return

		if tag == "packet":
			self.next_packet = ByteBuffer()
			self.cur_proto = None
			self.parse_context = BytebufferAnnotatingParseContext(None, self.next_packet)
			self.parse_context.push(None, None, id="root")
			self.parse_context.push(attrib, list(), id="packet")
			return

		if tag == "proto":
			self.cur_proto = attrib["name"]
			#self.next_packet.setBytes(int(attrib['pos']), int(attrib["size"]), {"section":}, None)
			#print(attrib)
			if "showname" in attrib: attrib["section"] = attrib["showname"]

		if self.cur_proto == "geninfo": # ignore all geninfo fields, they contain mostly bullshit
			return

		if self.cur_proto == "frame": # put frame metadata in the metadata dict
			if tag == "field":
				self.next_packet.metadata[attrib["name"]] = attrib["show"]
			return

		if 'pos' in attrib and "size" in attrib:
			pos = int(attrib['pos'])
			size = int(attrib['size'])
			self.parse_context.buf_offset = pos
			self.parse_context.id = attrib["name"].split(".")[-1]
			#del attrib['pos']
			#del attrib['size']
			v = list(  )
			if "value" in attrib and len(attrib["value"]) == size * 2:
				#try:
					self.next_packet.setBytes(pos, binascii.unhexlify(attrib["value"]))

					self.parse_context.push(attrib, v)
					self.parse_context.buf_offset += size
					v.append( self.parse_context.pack_value(attrib["value"]) )

				#except:
				#	pass
			else:
				self.parse_context.push(attrib, v)
		else:
			if "name" in attrib:
				self.parse_context.id = attrib["name"].split(".")[-1]
			else:
				self.parse_context.id = ""
			v = list(  )
			self.parse_context.push(attrib, v)
			#self.next_packet.setBytes(pos, size, attrib, None)




	def end(self,tag):
		self.parse_context.log("</%s>"%tag,self.cur_proto)
		if tag == "pdml":
			self.parse_context.log("done")
		elif tag == "packet":
			self.next_packet.fi_tree = self.parse_context.pack_value(self.parse_context.pop())
			assert(self.parse_context.pop() == None)
			self.destination.add(self.next_packet)
			self.next_packet = None
		elif self.cur_proto == "geninfo" or self.cur_proto == "frame":
			pass
		else:
			val = self.parse_context.top_value()
			if len(val) == 1:
				packed_val = val[0]
			else:
				packed_val = self.parse_context.pack_value(val)
			self.parse_context.pop()
			self.parse_context.top_value().append(packed_val)
		

	def data(self, data):
		pass            # We do not need to do anything with data.
	def close(self):
		#return self.stack[0].value
		pass


def convertPdmlToPacketList(pdmlString, destPacketList):
	target=PdmlToPacketListParser(destPacketList)
	parser=XMLParser(target=target)
	parser.feed(pdmlString)
	return parser.close()

def findTshark():
	if os.path.isfile("C:\\Program Files\\Wireshark\\tshark.exe"):
		return "C:\\Program Files\\Wireshark\\tshark.exe"
	else:
		path=shutil.which("tshark")
		if path == None:
			raise FileNotFoundError("tshark executable not found. please install wireshark and place tshark in path")
		return path
def parseInterfaceLine(s):
	match = re.match(r"\d+\. ((\w+)( \(.*\))?)", s)
	return (match.group(2) ,match.group(1))
def findInterfaces():
	tsharkBinary = getValue("DataSources.wireshark.tsharkBinary")
	try:
		return [parseInterfaceLine(s) for s in subprocess.check_output([tsharkBinary, "-D"]).decode("utf-8").split("\n") if ". " in s]
	except Exception as e:
		print(e)
		return [("ERROR","ERROR")]

if __name__=="__main__":
	print(findInterfaces())
