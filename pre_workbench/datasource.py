
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
import os

from PyQt5.QtCore import (pyqtSignal, QObject, QProcess)

from pre_workbench.configs import SettingsField, SettingsSection, registerOption, getValue
from pre_workbench.objects import ByteBuffer, ByteBufferList, ReloadRequired
from pre_workbench.structinfo.exceptions import invalid, incomplete
from pre_workbench.structinfo.serialization import bin_serialize_fi
from pre_workbench.typeregistry import TypeRegistry
from pre_workbench.tshark_helper import findTshark, PdmlToPacketListParser, findInterfaces

group = SettingsSection('DataSources', 'Data Sources', 'wireshark', 'Wireshark Integration')
try:
	tsharkDefault = findTshark()
except FileNotFoundError:
	tsharkDefault = ""
registerOption(group, "tsharkBinary", "tshark Binary", "text", {"fileselect":"open"}, tsharkDefault, None)

DataSourceTypes = TypeRegistry()

class DataSource(QObject):
	on_finished = pyqtSignal()
	on_log = pyqtSignal(str)
	def __init__(self, params):
		super().__init__()
		self.params = params
	def updateParam(self, key, value):
		raise ReloadRequired()
	def startFetch(self):
		pass
	def cancelFetch(self):
		pass

@DataSourceTypes.register(DisplayName = "Binary file")
class FileDataSource(DataSource):
	@staticmethod
	def getConfigFields():
		return [
			SettingsField("fileName", "File name", "text", {"fileselect":"open"}),
			SettingsField("formatInfo", "Format info", "text", {"fileselect":"open"})
		]
	def startFetch(self):
		bbuf = ByteBuffer(metadata={'fileName':self.params['fileName'],
									'fileTimestamp': os.path.getmtime(self.params['fileName'])})
		with open(self.params['fileName'], "rb") as f:
			bbuf.setContent(f.read())

		if self.params["formatInfo"] != "":
			from pre_workbench.structinfo.parsecontext import FormatInfoContainer, BytebufferAnnotatingParseContext
			bbuf.fi_container = FormatInfoContainer(load_from_file=self.params["formatInfo"])
			parse_context = BytebufferAnnotatingParseContext(bbuf.fi_container, bbuf)
			#parse_context.on_new_subflow_category = self.newSubflowCategory
			bbuf.fi_tree = parse_context.parse()

		self.on_finished.emit()
		return bbuf
		
	def cancelFetch(self):
		# cancel reading file
		pass

@DataSourceTypes.register(DisplayName = "PCAP file")
class PcapFileDataSource(DataSource):
	@staticmethod
	def getConfigFields():
		return [
			SettingsField("fileName", "File name", "text", {"fileselect":"open"})
		]
	def startFetch(self):
		with open(self.params['fileName'], "rb") as f:
			from pre_workbench.structinfo.parsecontext import LoggingParseContext
			pcapfile = PcapFile.read_from_buffer(LoggingParseContext(f.read()))
			plist = ByteBufferList()
			plist.metadata.update(pcapfile['file_header'])
			for packet in pcapfile['packets']:
				plist.add(ByteBuffer(packet['payload'], metadata=packet['header']))

		self.on_finished.emit()
		return plist
	def cancelFetch(self):
		# cancel reading file
		pass


class AbstractTsharkDataSource(DataSource):
	def startFetch(self):
		self.plist = ByteBufferList()
		self.process = QProcess()
		self.process.finished.connect(self.onProcessFinished)
		self.process.readyReadStandardError.connect(self.onReadyReadStderr)
		self.process.readyReadStandardOutput.connect(self.onReadyReadStdout)

		self.process.start(getValue("DataSources.wireshark.tsharkBinary"), self.getArgs())
		self.target=PdmlToPacketListParser(self.plist)
		return self.plist

	def onReadyReadStderr(self):
		s = "STD-ERR FROM Tshark:"+self.process.readAllStandardError().data().decode("utf-8", "replace")
		print(s)
		self.on_log.emit(s)
	def onReadyReadStdout(self):
		self.plist.beginUpdate()
		self.target.feed(self.process.readAllStandardOutput())
		self.plist.endUpdate()

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.terminate()
		self.process.waitForFinished(500)
		self.process.kill()
		pass


@DataSourceTypes.register(DisplayName = "PCAP file via Tshark")
class TsharkPcapFileDataSource(AbstractTsharkDataSource):
	@staticmethod
	def getConfigFields():
		return [
			SettingsField("fileName", "File name", "text", {"fileselect":"open"}),
			SettingsField("displayFilter", "Display filter", "text", {}),
			SettingsField("decodeAs", "Decode as", "text", {})
		]
	def getArgs(self):
		args = ["-r", self.params["fileName"], "-T", "pdml"]
		if self.params["displayFilter"] != "":
			args += ["-Y", self.params["displayFilter"]]
		if self.params["decodeAs"] != "":
			args += ["-d", self.params["decodeAs"]]
		return args

@DataSourceTypes.register(DisplayName = "Live capture via Tshark")
class TsharkLiveDataSource(AbstractTsharkDataSource):
	@staticmethod
	def getConfigFields():
		return [
			SettingsField("interface", "Interface", "select", {"options":findInterfaces()}),
			SettingsField("captureFilter", "libpcap-style capture filter", "text", {}),
			SettingsField("displayFilter", "Display filter", "text", {}),
			SettingsField("decodeAs", "Decode as", "text", {}),
		]
	def getArgs(self):
		args = ["-i", self.params["interface"], "-T", "pdml"]
		if self.params["captureFilter"] != "":
			args += ["-f", self.params["captureFilter"]]
		if self.params["displayFilter"] != "":
			args += ["-Y", self.params["displayFilter"]]
		if self.params["decodeAs"] != "":
			args += ["-d", self.params["decodeAs"]]
		return args


@DataSourceTypes.register(DisplayName = "Live capture via PCAP over stdout")
class LivePcapCaptureDataSource(DataSource):
	@staticmethod
	def getConfigFields():
		return [
			SettingsField("shell_cmd", "Shell command line", "text", {"default":"sudo tcpdump -w -"})
		]
	def startFetch(self):
		self.plist = ByteBufferList()
		self.packetFI = None
		from pre_workbench.structinfo.parsecontext import ParseContext
		self.ctx = ParseContext()
		self.process = QProcess()
		self.process.finished.connect(self.onProcessFinished)
		self.process.readyReadStandardError.connect(self.onReadyReadStderr)
		self.process.readyReadStandardOutput.connect(self.onReadyReadStdout)

		self.process.start("/bin/sh", ["-c", self.params["shell_cmd"]])

		return self.plist

	def tryParseHeader(self):
		for headerFI, packetFI in PcapVariants:
			try:
				header = headerFI.read_from_buffer(self.ctx)
				self.packetFI = packetFI
				self.plist.metadata.update(header)
				return
			except invalid as ex:
				self.on_log.emit(str(ex))
				pass
		raise invalid(self.ctx, "no PcapVariant matched")


	def onReadyReadStderr(self):
		self.on_log.emit("STD-ERR:"+self.process.readAllStandardError().data().decode("utf-8", "replace"))
	def onReadyReadStdout(self):
		self.ctx.feed_bytes(self.process.readAllStandardOutput())
		try:
			if self.packetFI == None:
				self.tryParseHeader()
			while True:
				packet = self.packetFI.read_from_buffer(self.ctx)
				self.plist.add(ByteBuffer(packet['payload'], metadata=packet['header']))
		except incomplete:
			return
		except invalid as ex:
			self.on_log.emit("Invalid packet format - killing pcap")
			self.on_log.emit (str(ex))
			self.cancelFetch()

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.terminate()
		self.process.waitForFinished(500)
		self.process.kill()
		pass
"""
PcapHeader = structinfo.StructFI(def_name="pcap_header", children=[
	("magic_number",  structinfo.FixedFieldFI(format="I", 	description="'A1B2C3D4' means the endianness is correct", magic=0xa1b2c3d4)),
	("version_major", structinfo.FixedFieldFI(format="H", 	description="major number of the file format")),
	("version_minor", structinfo.FixedFieldFI(format="H", 	description="minor number of the file format")),
	("thiszone", 	  structinfo.FixedFieldFI(format="i", 	description="correction time in seconds from UTC to local time (0)")),
	("sigfigs", 	  structinfo.FixedFieldFI(format="I", 	description="accuracy of time stamps in the capture (0)")),
	("snaplen", 	  structinfo.FixedFieldFI(format="I", 	description="max length of captured packed (65535)")),
	("network", 	  structinfo.FixedFieldFI(format="I", 	description="type of data link (1 = ethernet)")),
])
PcapPacket = structinfo.StructFI(def_name="pcap_packet", children=[
	("header", structinfo.StructFI(children=[
		("ts_sec", 		structinfo.FixedFieldFI(format="I",  description="timestamp seconds")),
		("ts_usec", 	structinfo.FixedFieldFI(format="I",  description="timestamp microseconds")),
		("incl_len", 	structinfo.FixedFieldFI(format="I",  description="number of octets of packet saved in file")),
		("orig_len", 	structinfo.FixedFieldFI(format="I",  description="actual length of packet")),
	])),
	("payload", 	structinfo.VarByteFieldFI(size_expr="header.incl_len")),
])
PcapVariants = [
	(structinfo.VariantStructFI(children=[PcapHeader], endianness="<"), structinfo.VariantStructFI(children=[PcapPacket], endianness="<")),
	(structinfo.VariantStructFI(children=[PcapHeader], endianness=">"), structinfo.VariantStructFI(children=[PcapPacket], endianness=">")),
	]
PcapFile = structinfo.VariantStructFI(def_name="pcap_file", children=[
	structinfo.StructFI(children=[
		("file_header", PcapHeader),
		("packets", structinfo.RepeatStructFI(children=PcapPacket)),
	], endianness=en)
	for en in ["<",">"]
])
"""

#PcapFormats = structinfo.FormatInfoContainer(load_from_string="""
#""")

"""

	@RpcMethod(iface="pft",name="parse_pcap_file_with_scapy")
	def parse_pcap_file_with_scapy(self, pcap_filename, script_filename):
		fd, tmpout = tempfile.mkstemp(".cbor")
		result = subprocess.run([python_exec, "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, tmpout], stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		tmpfile = os.fdopen(fd, "rb")
		out = tmpfile.read()
		tmpfile.close()
		os.unlink(tmpout)
		return [result.returncode, out, result.stdout.decode("utf8")]

	def _readerthread(self, fh, buffer):
		buffer.append(fh.read())
		fh.close()
"""
"""
	@RpcMethod(iface="pft",name="parse_pcap_file_with_scapy2")
	async def parse_pcap_file_with_scapy2(self, pcap_filename, script_filename):
		read_fd, write_fd = os.pipe()
		proc = subprocess.Popen([python_exec, "wrapper.py", "data/" + script_filename, "data/" + pcap_filename, str(write_fd)], 
			stdout=subprocess.PIPE,stderr=subprocess.PIPE, pass_fds=[write_fd])
		mypipe_buff = []
		mypipe = os.fdopen(read_fd, "rb")
		mypipe_thread = threading.Thread(target=self._readerthread, args=(mypipe, mypipe_buff), daemon=True)
		mypipe_thread.start()
		stdout, stderr = proc.communicate(timeout=5000)

		return [result.returncode, result.stdout, result.stderr.decode("utf8")]
	"""
"""
	@RpcMethod(iface="pft",name="parse_pcap_file_with_tshark")
	def parse_pcap_file_with_tshark(self, pcap_filename):
		result = subprocess.run([tshark_exec, "-r", "data/" + pcap_filename, "-T", "pdml"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		stderr = result.stderr.decode("utf8")
		try:
			convertedstdout = cbor.dumps(convertPdmlToPacketTree(result.stdout))
		except Exception as eex:
			convertedstdout = None
			stderr+="\n\nconversion failed with exception: "+str(eex)

		return [result.returncode, convertedstdout, stderr]
"""

if __name__=="__main__":
	with open("PcapFile.pfi", "wb") as f:
		f.write(bin_serialize_fi(PcapFile))
	with open("PcapFile.txt", "w") as f:
		f.write(PcapFile.to_text())
