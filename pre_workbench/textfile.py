
# PRE Workbench
# Copyright (C) 2019 Max Weller
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

from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMessageBox

from .genericwidgets import MdiFile
from .guihelper import navigateLink
from .typeregistry import WindowTypes

class RichEdit(QTextEdit):
	def __init__(self, parent=None):
		super().__init__(parent)

	def mouseReleaseEvent(self, e: QMouseEvent):
		if e.modifiers() == QtCore.Qt.ControlModifier:
			anchor = self.anchorAt(e.pos())
			if anchor:
				navigateLink(anchor)




@WindowTypes.register(fileExts=['.pht'])
class HyperTextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), "PRE Workbench HyperText (*.pht)", "untitled%d.pht")
	def saveParams(self):
		self.params["fileName"] = self.curFile
		return self.params
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = RichEdit()
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)
	def loadFile(self, fileName):
		self.dataDisplay.setHtml(open(fileName,"r").read())
		self.setCurrentFile(fileName)
	def saveFile(self, fileName):
		bin = self.dataDisplay.toHtml()
		with open(fileName, "w") as f:
			f.write(bin)
		self.setCurrentFile(fileName)
		return True

@WindowTypes.register(fileExts=['.txt','.py','.log'])
class TextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), "Text Files (*.txt)", "untitled%d.txt")
	def saveParams(self):
		self.params["fileName"] = self.curFile
		return self.params
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = QTextEdit()
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)
	def loadFile(self, fileName):
		self.dataDisplay.setText(open(fileName,"r").read())
		self.setCurrentFile(fileName)
	def saveFile(self, fileName):
		bin = self.dataDisplay.toPlainText()
		with open(fileName, "w") as f:
			f.write(bin)
		self.setCurrentFile(fileName)
		return True
