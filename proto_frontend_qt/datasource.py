import struct
from collections import namedtuple

from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QProcess)
from objects import ByteBuffer, ByteBufferList, ReloadRequired
from structinfo import StructInfo, FieldInfo
from typeregistry import TypeRegistry

DataSourceTypes = TypeRegistry()

class DataSource(QObject):
	on_finished = pyqtSignal()
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
			("fileName", "File name", "text", {})
		]
	def __init__(self, params):
		super().__init__()
		self.fileName = params["fileName"]

	def startFetch(self):
		bbuf = ByteBuffer()
		with open(self.fileName, "rb") as f:
			bbuf.setContent(f.read())
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
			("fileName", "File name", "text", {})
		]
	def __init__(self, params):
		super().__init__()
		self.fileName = params["fileName"]

	def startFetch(self):
		# start reading file
		self.on_finished.emit()
		pass
	def cancelFetch(self):
		# cancel reading file
		pass
	
import subprocess
from tshark_helper import findTshark, convertPdmlToPacketList, PdmlToPacketListParser, findInterfaces


class AbstractTsharkDataSource(DataSource):
	def startFetch(self):
		self.plist = ByteBufferList()
		self.process = QProcess()
		self.process.finished.connect(self.onProcessFinished)
		self.process.readyReadStandardError.connect(self.onReadyReadStderr)
		self.process.readyReadStandardOutput.connect(self.onReadyReadStdout)

		self.process.start(findTshark(), self.getArgs())
		self.target=PdmlToPacketListParser(self.plist)
		return self.plist

	def onReadyReadStderr(self):
		print("STD-ERR FROM Tshark:",self.process.readAllStandardError())
	def onReadyReadStdout(self):
		self.plist.beginUpdate()
		self.target.feed(self.process.readAllStandardOutput())
		self.plist.endUpdate()

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.kill()
		pass


@DataSourceTypes.register(DisplayName = "PCAP file via Tshark")
class TsharkPcapFileDataSource(AbstractTsharkDataSource):
	@staticmethod
	def getConfigFields():
		return [
			("fileName", "File name", "text", {}),
			("displayFilter", "Display filter", "text", {}),
			("decodeAs", "Decode as", "text", {})
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
			("interface", "Interface", "select", {"options":findInterfaces()}),
			("captureFilter", "libpcap-style capture filter", "text", {}),
			("displayFilter", "Display filter", "text", {}),
			("decodeAs", "Decode as", "text", {}),
			("tsharkBinary", "tshark Binary", "text", {"default":findTshark()}),
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
			("shell_cmd", "Shell command line", "text", {"default":"tcpdump -w -"})
		]
	def startFetch(self):
		self.plist = ByteBufferList()
		self.buf = bytes()
		self.endianness = None
		self.process = QProcess()
		self.process.finished.connect(self.onProcessFinished)
		self.process.readyReadStandardError.connect(self.onReadyReadStderr)
		self.process.readyReadStandardOutput.connect(self.onReadyReadStdout)

		self.process.start("/bin/sh", ["-c", self.params["shell_cmd"]])
		return self.plist

	def onReadyReadStderr(self):
		print("STD-ERR FROM Tshark:",self.process.readAllStandardError())
	def onReadyReadStdout(self):
		self.buf += self.process.readAllStandardOutput()
		while True:
			if self.endianness == None:
				header, rest = PcapHeader.read_from_buffer(self.buf, "<")
				if header == None: return
				if header["magic_number"] == 0xa1b2c3d4:
					print("File is little endian")
					self.endianness = "<"
				else:
					header, rest = PcapHeader.read_from_buffer(self.buf, ">")
					if header == None: return
					if header["magic_number"] == 0xa1b2c3d4:
						print("File is big endian")
						self.endianness = ">"
					else:
						raise Exception("invalid magic_number")
				self.buf = rest
				self.pcap_header_done = True
				self.plist.metadata.update(header)
			else:
				header, payload, self.buf = pcap_read_next_packet(self.buf, self.endianness)
				if header == None: return
				bbuf = ByteBuffer(payload)
				bbuf.metadata.update(header)
				self.plist.add(bbuf)

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.kill()
		pass

PcapHeader = StructInfo([
	FieldInfo("I", 	"magic_number",  "'A1B2C3D4' means the endianness is correct", magic),
	FieldInfo("H", 	"version_major", "major number of the file format"),
	FieldInfo("H", 	"version_minor", "minor number of the file format"),
	FieldInfo("i", 	"thiszone", 	 "correction time in seconds from UTC to local time (0)"),
	FieldInfo("I", 	"sigfigs", 		 "accuracy of time stamps in the capture (0)"),
	FieldInfo("I", 	"snaplen", 		 "max length of captured packed (65535)"),
	FieldInfo("I", 	"network", 		 "type of data link (1 = ethernet)"),
])
PcapPacketHeader = StructInfo([
	FieldInfo("I", "ts_sec", "timestamp seconds"),
	FieldInfo("I", "ts_usec", "timestamp microseconds"),
	FieldInfo("I", "incl_len", "number of octets of packet saved in file"),
	FieldInfo("I", "orig_len", "actual length of packet"),
])
print(PcapHeader.size, PcapPacketHeader.size)

def pcap_read_next_packet(pcap_buf, endianness):
	header, rest = PcapPacketHeader.read_from_buffer(pcap_buf, endianness)
	print(header, len(pcap_buf), len(rest))
	if header == None or header['incl_len'] > len(rest): return None, None, pcap_buf
	return header, rest[0:header['incl_len']], rest[header['incl_len']:]


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
