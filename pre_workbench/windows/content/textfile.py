
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

import traceback

from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QMouseEvent, QFont, QColor, QKeyEvent, QTextFrameFormat, QTextFormat
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMessageBox

from pre_workbench.genericwidgets import MdiFile
from pre_workbench.guihelper import navigateLink, getMonospaceFont
from pre_workbench.scintillaedit import SimplePythonEditor
from pre_workbench.typeregistry import WindowTypes


class RichEdit(QTextEdit):
	def __init__(self, parent=None):
		super().__init__(parent)

	def mouseReleaseEvent(self, e: QMouseEvent):
		if e.modifiers() == QtCore.Qt.ControlModifier:
			anchor = self.anchorAt(e.pos())
			if anchor:
				navigateLink(anchor)
		super().mouseReleaseEvent(e)

	def getCodeBlockUnderCursor(self):
		cur = self.textCursor()
		fr = cur.currentFrame()
		print(fr)
		it = fr.begin()
		code = ""
		while not it.atEnd():
			fragment = it.currentBlock()
			if fragment.isValid():
				code += fragment.text() + "\n"
			it += 1

		return code

	def keyPressEvent(self, e: QKeyEvent):
		mod = e.modifiers() & ~QtCore.Qt.KeypadModifier
		if e.key() == QtCore.Qt.Key_F4:
			cur = self.textCursor()
			format = QTextFrameFormat()
			format.setBorder(2.0)
			format.setBorderBrush(QColor(255,0,255))
			format.setProperty(QTextFormat.UserProperty + 100, "code-block")
			format.setPadding(5.0)
			frame = cur.insertFrame(format)
			self.setTextCursor(frame.firstCursorPosition())
			self.setCurrentFont(getMonospaceFont())
		print(int(mod), e.key())
		if mod == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
			print("ctr-enter")
			code = self.getCodeBlockUnderCursor()
			print(code)
			try:
				def alert(msg):
					QMessageBox.information(self, "Script alert", str(msg))
				exec(code)
			except Exception as ex:
				QMessageBox.warning(self, "Exception in script", traceback.format_exc())
			return

		super().keyPressEvent(e)


@WindowTypes.register(fileExts=['.pht'], icon='document-text-image.png')
class HyperTextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self._initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "PRE Workbench HyperText (*.pht)", "untitled%d.pht")
	def sizeHint(self):
		return QSize(600,400)
	def _initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = RichEdit()
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)
		self.dataDisplay.textChanged.connect(self.documentWasModified)
	def loadFile(self, fileName):
		self.dataDisplay.setHtml(open(fileName,"r").read())
		self.setCurrentFile(fileName)
	def saveFile(self, fileName):
		bin = self.dataDisplay.toHtml()
		with open(fileName, "w") as f:
			f.write(bin)
		self.setCurrentFile(fileName)
		return True


@WindowTypes.register(fileExts=['.txt','.py','.log','.md'], icon='script.png')
class TextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self._initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "Text Files (*.txt)", "untitled%d.txt")
	def sizeHint(self):
		return QSize(600,400)
	def _initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = SimplePythonEditor()
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)
		self.dataDisplay.modificationChanged.connect(self.setWindowModified)
	def loadFile(self, fileName):
		self.dataDisplay.setText(open(fileName,"r").read())
		self.setCurrentFile(fileName)
		self.dataDisplay.setModified(False)
	def saveFile(self, fileName):
		bin = self.dataDisplay.text()
		with open(fileName, "w") as f:
			f.write(bin)
		self.setCurrentFile(fileName)
		self.dataDisplay.setModified(False)
		return True
