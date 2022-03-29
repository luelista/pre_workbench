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

from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from pre_workbench.datawidgets import PacketListWidget
from pre_workbench.genericwidgets import MdiFile
from pre_workbench.objects import ByteBufferList
from pre_workbench.typeregistry import WindowTypes


@WindowTypes.register(fileExts=['.pcapng','.pcap','.cap'], icon='document-table.png')
class PcapngFileWindow(QWidget, MdiFile):
	meta_updated = pyqtSignal(str, object)
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self._initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "PCAP files (*.pcapng, *.pcap, *.cap)", "untitled%d.pcapng")
		if "state" in self.params: self.dataDisplay.restoreState(self.params["state"])

	def saveParams(self):
		self.params["state"] = self.dataDisplay.saveState()
		return self.params

	def sizeHint(self):
		return QSize(600,400)

	def _initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = PacketListWidget()
		self.dataDisplay.meta_updated.connect(self.meta_updated.emit)
		self.layout().addWidget(self.dataDisplay)
		self.packetList = ByteBufferList()
		self.dataDisplay.setContents(self.packetList)

	def loadFile(self, fileName):
		with open(fileName, "rb") as f:
			from pre_workbench.structinfo.pcapfiles import read_pcap_file
			self.packetList = read_pcap_file(f)
			self.dataDisplay.setContents(self.packetList)

	def saveFile(self, fileName):
		return False

