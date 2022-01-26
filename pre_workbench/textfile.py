
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
from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciLexerCPP
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QMouseEvent, QFont, QFontMetrics, QColor, QKeyEvent, QTextFrameFormat, QTextFormat
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMessageBox, QDialog, QDialogButtonBox

from pre_workbench.genericwidgets import MdiFile
from pre_workbench.guihelper import navigateLink, makeDlgButtonBox
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

	def keyPressEvent(self, e: QKeyEvent):
		mod = e.modifiers() & ~QtCore.Qt.KeypadModifier
		if e.key() == QtCore.Qt.Key_F4:
			cur = self.textCursor()
			format = QTextFrameFormat()
			format.setBorder(2.0)
			format.setBorderBrush(QColor(255,0,255))
			format.setProperty(QTextFormat.UserProperty + 100, "code-block")
			frame = cur.insertFrame(format)
			self.setTextCursor(frame.firstCursorPosition())
		print(int(mod), e.key())
		if mod == QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_Return:
			print("ctr-enter")
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
			print(code)
			try:
				exec(code)
			except Exception as ex:
				QMessageBox.warning(self, "Exception in script", traceback.format_exc())
			return

		super().keyPressEvent(e)




@WindowTypes.register(fileExts=['.pht'])
class HyperTextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "PRE Workbench HyperText (*.pht)", "untitled%d.pht")
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


class QsciLexerFormatinfo(QsciLexerCPP):
	def keywords(self, p_int):
		if p_int == 1:
			return "variant struct switch case repeat true false null bytes fixed"
		elif p_int == 2:
			return "uint8 int8 uint16 int16 uint32 int32"
		else:
			return super().keywords(p_int)




class SimplePythonEditor(QsciScintilla):
	ARROW_MARKER_NUM = 8

	def __init__(self, parent=None):
		super().__init__(parent)

		# Set the default font
		#font = QFont()
		#font.setFamilies(['Monaco', 'Courier New'])
		#font.setFixedPitch(True)
		#font.setPointSize(11)
		#self.setFont(font)
		#self.setMarginsFont(font)

		# Margin 0 is used for line numbers
		#fontmetrics = QFontMetrics(font)
		#self.setMarginsFont(font)
		#self.setMarginWidth(0, fontmetrics.width("00000") + 6)
		self.setMarginWidth(0, 45)
		self.setMarginLineNumbers(0, True)
		self.setMarginsBackgroundColor(QColor("#cccccc"))

		# Clickable margin 1 for showing markers
		self.setMarginSensitivity(1, True)
		self.marginClicked.connect(self.on_margin_clicked)
		self.selectionChanged.connect(self.on_selection_changed)
		self.cursorPositionChanged.connect(self.on_cursor_position_changed)
		self.markerDefine(QsciScintilla.RightArrow,
			self.ARROW_MARKER_NUM)
		self.setMarkerBackgroundColor(QColor("#ee1111"),
			self.ARROW_MARKER_NUM)

		# Brace matching: enable for a brace immediately before or after
		# the current position
		#
		self.setBraceMatching(QsciScintilla.SloppyBraceMatch)

		# Current line visible with special background color
		self.setCaretLineVisible(True)
		self.setCaretLineBackgroundColor(QColor("#ffe4e4"))

		# Set Python lexer
		# Set style for Python comments (style number 1) to a fixed-width
		# courier.
		#

		#lexer = QsciLexerPython()
		lexer = QsciLexerFormatinfo()
		#lexer.setDefaultFont(font)
		self.setLexer(lexer)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, QsciScintilla.STYLE_DEFAULT, b'Courier New')
		self.SendScintilla(QsciScintilla.SCI_STYLESETSIZE, QsciScintilla.STYLE_DEFAULT, 11)
		self.SendScintilla(QsciScintilla.SCI_STYLECLEARALL)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.CommentLine, 0x777777)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Comment, 0x666666)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Keyword, 0x0000aa)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.KeywordSet2, 0x000055)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.SingleQuotedString, 0x00aa00)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.DoubleQuotedString, 0x00aa00)

		# Don't want to see the horizontal scrollbar at all
		# Use raw message to Scintilla here (all messages are documented
		# here: http://www.scintilla.org/ScintillaDoc.html)
		self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)

		# not too small
		self.setMinimumSize(600, 450)

	def on_margin_clicked(self, nmargin, nline, modifiers):
		# Toggle marker for the line the margin was clicked on
		if self.markersAtLine(nline) != 0:
			self.markerDelete(nline, self.ARROW_MARKER_NUM)
		else:
			self.markerAdd(nline, self.ARROW_MARKER_NUM)

	def on_selection_changed(self):
		pass

	def on_cursor_position_changed(self, a, b):
		try:
			pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
			print(a,b,pos)
			style = self.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos)
			print(a,b,pos,style)
		except Exception as e:
			print(e)


@WindowTypes.register(fileExts=['.txt','.py','.log','.md'])
class TextFileWindow(QWidget, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "Text Files (*.txt)", "untitled%d.txt")
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = SimplePythonEditor()
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)
	def loadFile(self, fileName):
		self.dataDisplay.setText(open(fileName,"r").read())
		self.setCurrentFile(fileName)
	def saveFile(self, fileName):
		bin = self.dataDisplay.text()
		with open(fileName, "w") as f:
			f.write(bin)
		self.setCurrentFile(fileName)
		return True


def showScintillaDialog(parent, title, content, ok_callback):
	dlg = QDialog(parent)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	sg = SimplePythonEditor()
	sg.setText(content)
	dlg.layout().addWidget(sg)
	makeDlgButtonBox(dlg, ok_callback, lambda: sg.text())
	if dlg.exec() == QDialog.Rejected: return None
	return sg.text()
