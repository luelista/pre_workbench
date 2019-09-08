
from PyQt5.QtCore import (Qt, pyqtSignal, QObject)
from objects import ByteBuffer, ByteBufferList, ReloadRequired


class DataSource:
	on_finished = pyqtSignal()
	def updateParam(self, key, value):
		raise ReloadRequired()
	def startFetch(self):
		pass
	def cancelFetch(self):
		pass

class FileDataSource(DataSource):
	DisplayName = "Binary file"
	ConfigFields = [
		("fileName", "File name", "text", {})
	]
	def __init__(self, fileName):
		super().__init__()
		self.fileName = fileName

	def startFetch(self):
		with open(self.fileName, "rb") as f:
			self.setContent(f.read())
		self.on_new_data.emit()
		self.on_finished.emit()
		
	def cancelFetch(self):
		# cancel reading file
		pass
	

class PcapFileDataSource(DataSource):
	DisplayName = "PCAP file"
	ConfigFields = [
		("fileName", "File name", "text", {})
	]
	def __init__(self, fileName):
		super().__init__()
		self.fileName = fileName
	def startFetch(self):
		# start reading file
		pass
	def cancelFetch(self):
		# cancel reading file
		pass
	


class LiveCaptureDataSource(DataSource):
	DisplayName = "Live capture"
	ConfigFields = [
		("interface", "Interface", "text", {})
	]
	def __init__(self, interface):
		super().__init__()
		self.interface = interface
	def startFetch(self):
		# start the capture
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
