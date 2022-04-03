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
from pre_workbench import guihelper

from pre_workbench.genericwidgets import MdiFile
from pre_workbench.hexview import HexView2
from pre_workbench.typeregistry import WindowTypes

@WindowTypes.register(icon="document-binary.png")
class HexFileWindow(QWidget, MdiFile):
	meta_updated = pyqtSignal(str, object)
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self._initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "All files (*.*)", "untitled%d.bin")

	def sizeHint(self):
		return QSize(600,400)

	def _initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = HexView2(project=guihelper.CurrentProject, formatInfoContainer=guihelper.CurrentProject.formatInfoContainer)
		self.dataDisplay.selectionChanged.connect(self._onSelectionChanged)
		self.dataDisplay.parseResultsUpdated.connect(self._onParseResultsUpdated)
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)

	def _onSelectionChanged(self, selRange):
		selbytes = self.dataDisplay.buffers[selRange.buffer_idx].getBytes(selRange.start, selRange.length())
		self.meta_updated.emit("selected_bytes", selbytes)
		self.meta_updated.emit("hexview_range", self.dataDisplay)

	def _onParseResultsUpdated(self, fi_trees):
		self.meta_updated.emit("grammar", fi_trees)

	def loadFile(self, fileName):
		self.dataDisplay.setBytes(open(fileName,'rb').read())
		self.dataDisplay.setDefaultAnnotationSet(guihelper.CurrentProject.getRelativePath(self.params.get("fileName")))

	def saveFile(self, fileName):
		#bin = self.dataDisplay.buffers[0].buffer
		#with open(fileName, "wb") as f:
		#	f.write(bin)
		return True

	def zoomIn(self):
		self.dataDisplay.zoomIn()
	def zoomOut(self):
		self.dataDisplay.zoomOut()
	def zoomReset(self):
		self.dataDisplay.zoomReset()

