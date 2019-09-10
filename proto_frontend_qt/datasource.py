
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QProcess)
from objects import ByteBuffer, ByteBufferList, ReloadRequired

from typeregistry import DataSourceTypes

class DataSource(QObject):
	on_finished = pyqtSignal()
	def updateParam(self, key, value):
		raise ReloadRequired()
	def startFetch(self):
		pass
	def cancelFetch(self):
		pass

@DataSourceTypes.register(DisplayName = "Binary file")
class FileDataSource(DataSource):
	
	ConfigFields = [
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
	
	ConfigFields = [
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
from pdml_helper import findTshark, convertPdmlToPacketList, PdmlToPacketListParser

class AbstractTsharkDataSource(DataSource):
	def __init__(self, params):
		super().__init__()
		self.params = params

	def startFetch(self):
		plist = ByteBufferList()
		self.process = QProcess()
		self.process.finished.connect(self.onProcessFinished)
		self.process.readyReadStandardError.connect(self.onReadyReadStderr)
		self.process.readyReadStandardOutput.connect(self.onReadyReadStdout)

		self.process.start(findTshark(), self.getArgs())
		self.target=PdmlToPacketListParser(plist)
		return plist

	def onReadyReadStderr(self):
		print("STD-ERR FROM Tshark:",self.process.readAllStandardError())
	def onReadyReadStdout(self):
		self.target.feed(self.process.readAllStandardOutput())

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.kill()
		pass


@DataSourceTypes.register(DisplayName = "PCAP file via Tshark")
class TsharkPcapFileDataSource(AbstractTsharkDataSource):
	
	ConfigFields = [
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

	ConfigFields = [
		("interface", "Interface", "text", {}),
		("displayFilter", "Display filter", "text", {}),
		("decodeAs", "Decode as", "text", {}),
		("tsharkBinary", "tshark Binary", "text", {"default":findTshark()}),
	]
	def getArgs(self):
		args = ["-i", self.params["interface"], "-T", "pdml"]
		if self.params["displayFilter"] != "":
			args += ["-Y", self.params["displayFilter"]]
		if self.params["decodeAs"] != "":
			args += ["-d", self.params["decodeAs"]]
		return args

	

@DataSourceTypes.register(DisplayName = "Live capture")
class LiveCaptureDataSource(DataSource):
	
	ConfigFields = [
		("interface", "Interface", "text", {})
	]
	def __init__(self, params):
		super().__init__()
		self.interface = params["interface"]

	def startFetch(self):
		# start the capture
		self.on_finished.emit()
		pass
	def cancelFetch(self):
		# cancel the capture
		pass
	
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
