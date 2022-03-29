
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
import logging
import os

from PyQt5.QtCore import (pyqtSignal, QObject, QProcess)

from pre_workbench.configs import SettingsField, SettingsSection, registerOption, getValue
from pre_workbench.objects import ByteBuffer, ByteBufferList, ReloadRequired
from pre_workbench.structinfo.exceptions import invalid, incomplete
from pre_workbench.structinfo.pcapfiles import read_pcap_file
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
	logger = logging.getLogger("DataSource")
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
			plist = read_pcap_file(f)

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
		self.logger.warning("STD-ERR FROM Tshark: %s", self.process.readAllStandardError().data().decode("utf-8", "replace"))

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
		for headerFI, packetFI in PcapFormats:
			try:
				header = headerFI.read_from_buffer(self.ctx)
				self.packetFI = packetFI
				self.plist.metadata.update(header)
				return
			except invalid as ex:
				self.logger.debug("invalid pcap format, trying next (exception: %r)", ex)
		raise invalid(self.ctx, "no PcapVariant matched")

	def onReadyReadStderr(self):
		self.logger.warning("STD-ERR: %s", self.process.readAllStandardError().data().decode("utf-8", "replace"))

	def onReadyReadStdout(self):
		self.ctx.feed_bytes(self.process.readAllStandardOutput())
		try:
			if self.packetFI is None:
				self.tryParseHeader()
			while True:
				packet = self.packetFI.read_from_buffer(self.ctx)
				self.plist.add(ByteBuffer(packet['payload'], metadata=packet['header']))
		except incomplete:
			return
		except invalid as ex:
			self.logger.exception("Invalid packet format - killing pcap")
			self.cancelFetch()

	def onProcessFinished(self, exitCode, exitStatus):
		self.on_finished.emit()

	def cancelFetch(self):
		self.process.terminate()
		self.process.waitForFinished(500)
		self.process.kill()


