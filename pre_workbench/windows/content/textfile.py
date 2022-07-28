
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
import traceback
import uuid

from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QMouseEvent, QColor, QKeyEvent, QTextFrameFormat, QTextFormat, QImage, QTextDocument, \
	QKeySequence, QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMessageBox, QToolBar, QAction, QComboBox

from pre_workbench.configs import getIcon
from pre_workbench.windows.mdifile import MdiFile
from pre_workbench.guihelper import getMonospaceFont
from pre_workbench.app import navigateLink
from pre_workbench.controls.scintillaedit import ScintillaEdit
from pre_workbench.typeregistry import WindowTypes

FONT_SIZES = [7, 8, 9, 10, 11, 12, 13, 14, 18, 24, 36, 48, 64, 72, 96, 144, 288]
IMAGE_EXTENSIONS = ['.jpg','.png','.bmp']
HTML_EXTENSIONS = ['.htm', '.html']

def hexuuid():
	return uuid.uuid4().hex

def splitext(p):
	return os.path.splitext(p)[1].lower()

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

	def makeCodeBlock(self):
		cur = self.textCursor()
		format = QTextFrameFormat()
		format.setBorder(2.0)
		format.setBorderBrush(QColor(255,0,255))
		format.setProperty(QTextFormat.UserProperty + 100, "code-block")
		format.setPadding(5.0)
		frame = cur.insertFrame(format)
		self.setTextCursor(frame.firstCursorPosition())
		self.setCurrentFont(getMonospaceFont())

	def keyPressEvent(self, e: QKeyEvent):
		mod = e.modifiers() & ~QtCore.Qt.KeypadModifier
		print(int(mod), e.key())
		if mod == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
			logging.debug("ctr-enter")
			code = self.getCodeBlockUnderCursor()
			run_code(self, code)
			return

		super().keyPressEvent(e)

	def canInsertFromMimeData(self, source):
		if source.hasImage():
			return True
		else:
			return super(RichEdit, self).canInsertFromMimeData(source)

	def insertFromMimeData(self, source):
		cursor = self.textCursor()
		document = self.document()

		if source.hasUrls():

			for u in source.urls():
				file_ext = splitext(str(u.toLocalFile()))
				if u.isLocalFile() and file_ext in IMAGE_EXTENSIONS:
					image = QImage(u.toLocalFile())
					document.addResource(QTextDocument.ImageResource, u, image)
					cursor.insertImage(u.toLocalFile())

				else:
					# If we hit a non-image or non-local URL break the loop and fall out
					# to the super call & let Qt handle it
					break

			else:
				# If all were valid images, finish here.
				return


		elif source.hasImage():
			image = source.imageData()
			uuid = hexuuid()
			document.addResource(QTextDocument.ImageResource, uuid, image)
			cursor.insertImage(uuid)
			return

		super(RichEdit, self).insertFromMimeData(source)


def run_code(parent, code):
	try:
		from pre_workbench.macros import macroenv
		locals = {key: getattr(macroenv, key) for key in macroenv.__all__}
		exec(code, globals(), locals)
	except Exception as ex:
		QMessageBox.warning(parent, "Exception in script", traceback.format_exc())


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

		format_toolbar = QToolBar("Format")
		format_toolbar.setIconSize(QSize(16, 16))
		self.layout().addWidget(format_toolbar)

		self.fontsize = QComboBox()
		self.fontsize.addItems([str(s) for s in FONT_SIZES])
		# Connect to the signal producing the text of the current selection. Convert the string to float
		# and set as the pointsize. We could also use the index + retrieve from FONT_SIZES.
		self.fontsize.currentIndexChanged[str].connect(lambda s: self.dataDisplay.setFontPointSize(float(s)))
		format_toolbar.addWidget(self.fontsize)

		self.bold_action = QAction(getIcon('edit-bold.png'), "Bold", self)
		self.bold_action.setStatusTip("Bold")
		self.bold_action.setShortcut(QKeySequence.Bold)
		self.bold_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
		self.bold_action.setCheckable(True)
		self.bold_action.toggled.connect(lambda x: self.dataDisplay.setFontWeight(QFont.Bold if x else QFont.Normal))
		format_toolbar.addAction(self.bold_action)
		self.addAction(self.bold_action)

		self.italic_action = QAction(getIcon('edit-italic.png'), "Italic", self)
		self.italic_action.setStatusTip("Italic")
		self.italic_action.setShortcut(QKeySequence.Italic)
		self.italic_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
		self.italic_action.setCheckable(True)
		self.italic_action.toggled.connect(self.dataDisplay.setFontItalic)
		format_toolbar.addAction(self.italic_action)
		self.addAction(self.italic_action)

		self.underline_action = QAction(getIcon('edit-underline.png'), "Underline", self)
		self.underline_action.setStatusTip("Underline")
		self.underline_action.setShortcut(QKeySequence.Underline)
		self.underline_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
		self.underline_action.setCheckable(True)
		self.underline_action.toggled.connect(self.dataDisplay.setFontUnderline)
		format_toolbar.addAction(self.underline_action)
		self.addAction(self.underline_action)

		self.add_script_action = QAction(getIcon('script--plus.png'), "Add Script", self)
		self.add_script_action.setStatusTip("Underline")
		self.add_script_action.setShortcut(QKeySequence('F4'))
		self.add_script_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
		self.add_script_action.triggered.connect(self.dataDisplay.makeCodeBlock)
		format_toolbar.addAction(self.add_script_action)
		self.addAction(self.add_script_action)

		self._format_actions = [
			self.fontsize,
			self.bold_action,
			self.italic_action,
			self.underline_action,
		]
		self.update_format()
		self.dataDisplay.setAutoFormatting(QTextEdit.AutoAll)
		self.dataDisplay.selectionChanged.connect(self.update_format)

		self.layout().addWidget(self.dataDisplay)
		self.dataDisplay.textChanged.connect(self.documentWasModified)

	def block_signals(self, objects, b):
		for o in objects:
			o.blockSignals(b)

	def update_format(self):
		# Disable signals for all format widgets, so changing values here does not trigger further formatting.
		self.block_signals(self._format_actions, True)

		self.fontsize.setCurrentText(str(int(self.dataDisplay.fontPointSize())))

		self.italic_action.setChecked(self.dataDisplay.fontItalic())
		self.underline_action.setChecked(self.dataDisplay.fontUnderline())
		self.bold_action.setChecked(self.dataDisplay.fontWeight() == QFont.Bold)

		self.block_signals(self._format_actions, False)

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
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "All Files (*.*)", "untitled%d.txt")
	def sizeHint(self):
		return QSize(600,400)
	def _initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = ScintillaEdit()
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
