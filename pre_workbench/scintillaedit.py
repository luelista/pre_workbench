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

from PyQt5.Qsci import QsciScintilla, QsciLexerCPP
from PyQt5.QtGui import QColor, QStatusTipEvent
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QApplication

from pre_workbench import configs, SettingsSection
from pre_workbench.guihelper import makeDlgButtonBox


class QsciLexerFormatinfo(QsciLexerCPP):
	def keywords(self, p_int):
		if p_int == 1:
			return "variant struct switch case repeat true false null bytes fixed"
		elif p_int == 2:
			return "uint8 int8 uint16 int16 uint32 int32"
		else:
			return super().keywords(p_int)



configs.registerOption(SettingsSection("View", "View", "Scintilla", "Code Editor"),
					   "FontFamily", "Font Family", "text", {}, "monospace", None)

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
		self.marginClicked.connect(self._on_margin_clicked)
		self.selectionChanged.connect(self._on_selection_changed)
		self.cursorPositionChanged.connect(self._on_cursor_position_changed)

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

		#lexer = QsciLexerPython()
		lexer = QsciLexerFormatinfo()
		#lexer.setDefaultFont(font)
		self.setLexer(lexer)
		fontFamily = configs.getValue("View.Scintilla.FontFamily").encode('utf-8')
		self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, QsciScintilla.STYLE_DEFAULT, fontFamily)
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
		#self.setMinimumSize(600, 450)

	def _on_margin_clicked(self, nmargin, nline, modifiers):
		# Toggle marker for the line the margin was clicked on
		if self.markersAtLine(nline) != 0:
			self.markerDelete(nline, self.ARROW_MARKER_NUM)
		else:
			self.markerAdd(nline, self.ARROW_MARKER_NUM)

	def _on_selection_changed(self):
		pass

	def _on_cursor_position_changed(self, line, col):
		try:
			pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
			style = self.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos)
			logging.debug("line %d, col %d, pos %d, style %d", line, col, pos,style)
			QApplication.postEvent(self, QStatusTipEvent("line %d, col %d, pos %d, style %d"%(
				line, col, pos,style)))
		except Exception as e:
			logging.exception("get style failed")



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
