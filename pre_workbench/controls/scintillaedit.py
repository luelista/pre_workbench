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

import darkdetect
from PyQt5.Qsci import QsciScintilla, QsciLexerCPP, QsciAPIs, QsciLexerCustom, QsciLexer
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QStatusTipEvent, QFontInfo, QFont, QContextMenuEvent
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QApplication
from lark import Token

from pre_workbench import configs
from pre_workbench.app import GlobalEvents
from pre_workbench.configs import SettingsSection
from pre_workbench.guihelper import makeDlgButtonBox, APP
from pre_workbench.structinfo import format_info
from pre_workbench.typeregistry import DataWidgetTypes

configs.registerOption(SettingsSection("View", "View", "Scintilla", "Code Editor"),
					   "Font", "Font", "font", {}, "monospace,12,-1,7,50,0,0,0,0,0", None)

configs.registerOption(SettingsSection("View", "View", "Scintilla", "Code Editor"),
					   "UseQsciLexerFormatinfo2", "Use custom syntax highlighter", "check", {}, True, None)


@DataWidgetTypes.register(handles=[str,])
class ScintillaEdit(QsciScintilla):
	ARROW_MARKER_NUM = 8

	escapePressed = pyqtSignal()
	ctrlEnterPressed = pyqtSignal()

	def __init__(self, parent=None, lexer=None):
		super().__init__(parent)

		is_dark_mode = darkdetect.isDark()
		logging.debug("Dark Mode? %r", is_dark_mode)

		# Margin 0 is used for line numbers
		self.setMarginWidth(0, 45)
		self.setMarginLineNumbers(0, True)
		self.setMarginsBackgroundColor(QColor("#555555" if is_dark_mode else "#cccccc"))

		# Clickable margin 1 for showing markers
		self.setMarginSensitivity(1, True)
		self.marginClicked.connect(self._on_margin_clicked)
		self.selectionChanged.connect(self._on_selection_changed)
		self.cursorPositionChanged.connect(self._on_cursor_position_changed)

		self.markerDefine(QsciScintilla.RightArrow, self.ARROW_MARKER_NUM)
		self.setMarkerBackgroundColor(QColor("#ee1111"), self.ARROW_MARKER_NUM)

		# Brace matching: enable for a brace immediately before or after
		# the current position
		self.setBraceMatching(QsciScintilla.SloppyBraceMatch)

		# Current line visible with special background color
		self.setCaretLineVisible(True)
		self.setCaretLineBackgroundColor(QColor("#3f3038" if is_dark_mode else "#ffe9e9"))
		self.setCaretForegroundColor(QColor("#ffffff" if is_dark_mode else "#000000"))

		# Configure Lexer

		if isinstance(lexer, QsciLexer):
			self._lexer = lexer
		elif (not lexer) or (isinstance(lexer, str) and lexer.startswith("pgdl:")):
			lexer_start = "start"
			if lexer: lexer_start = lexer.split(":")[1]
			if configs.getValue("View.Scintilla.UseQsciLexerFormatinfo2"):
				self._lexer = QsciLexerFormatinfo2(self, lexer_start)
			else:
				self._lexer = QsciLexerCPP(self)

			autocompletions = format_info.builtinTypes.keys()
			self._api = QsciAPIs(self._lexer)
			for ac in autocompletions:
				self._api.add(ac)
			self._api.prepare()

		self.setLexer(self._lexer)

		# Set the default font
		self._init_font()
		GlobalEvents.on_config_change.connect(self._init_font)

		# Enable Multi Select
		self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, 1)
		self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_MATCHCASE)
		self.SendScintilla(QsciScintilla.SCI_TARGETWHOLEDOCUMENT, 0)
		self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, 1)
		self.SendScintilla(QsciScintilla.SCI_SETMULTIPASTE, QsciScintilla.SC_MULTIPASTE_EACH)

		"""
		Customization - AUTOCOMPLETION (Partially usable without a lexer)
		"""
		# Set the autocompletions to case INsensitive
		self.setAutoCompletionCaseSensitivity(True)
		# Set the autocompletion to not replace the word to the right of the cursor
		self.setAutoCompletionReplaceWord(False)
		# Set the autocompletion source to be the words in the
		# document
		self.setAutoCompletionSource(QsciScintilla.AcsAll)
		# Set the autocompletion dialog to appear as soon as 1 character is typed
		self.setAutoCompletionThreshold(1)


	def _init_font(self):
		is_dark_mode = darkdetect.isDark()
		font = QFont()
		font.fromString(configs.getValue("View.Scintilla.Font"))
		fontInfo = QFontInfo(font)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, QsciScintilla.STYLE_DEFAULT, fontInfo.family().encode('utf-8'))
		self.SendScintilla(QsciScintilla.SCI_STYLESETSIZE, QsciScintilla.STYLE_DEFAULT, fontInfo.pointSize())
		self.SendScintilla(QsciScintilla.SCI_STYLECLEARALL)
		self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_LINENUMBER, 0x555555 if is_dark_mode else 0xcccccc)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.CommentLine, 0x777777)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Comment, 0x666666)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Operator, 0x005555)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Number, 0x0000bb)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Keyword, 0xaa0000)
		self.SendScintilla(QsciScintilla.SCI_STYLESETWEIGHT, QsciLexerCPP.Keyword, 900)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerFormatinfo2.Name_Function, 0x5775ad)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerFormatinfo2.Name_Attribute, 0x507070)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerFormatinfo2.Keyword_Constant, 0xaa0000)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerFormatinfo2.Name_Builtin, 0xd9596e)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.SingleQuotedString, 0x4d7d1c)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.DoubleQuotedString, 0x4d7d1c)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.Identifier, 0x000000)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerCPP.GlobalClass, 0xb946a8)
		self.SendScintilla(QsciScintilla.SCI_STYLESETBOLD, QsciLexerCPP.GlobalClass, 1)
		self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_BRACELIGHT, 0x333300 if is_dark_mode else 0xdddd33)
		self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_BRACEBAD, 0x3333ff)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciScintilla.STYLE_BRACEBAD, 0xffffff)
		self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciLexerFormatinfo2.Syntax_error, 0xaafefe)
		self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciLexerFormatinfo2.Syntax_error, 0x000000)


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
			logging.log(logging.TRACE, "line %d, col %d, pos %d, style %d", line, col, pos,style)
			QApplication.postEvent(self, QStatusTipEvent("line %d, col %d, pos %d, style %d"%(
				line, col, pos,style)))
		except Exception as e:
			logging.exception("get style failed")

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			self.escapePressed.emit()
		elif ((event.modifiers() & Qt.ControlModifier) == Qt.ControlModifier and
			(event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return)):
			self.ctrlEnterPressed.emit()
		elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_G:
			self.SendScintilla(QsciScintilla.SCI_TARGETWHOLEDOCUMENT, 0)
			if self.SendScintilla(QsciScintilla.SCI_GETSELECTIONS, 0) == 1:
				if self.SendScintilla(QsciScintilla.SCI_GETSELECTIONEMPTY, 0) == 1:
					self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_MATCHCASE + QsciScintilla.SCFIND_WHOLEWORD)
					self.SendScintilla(QsciScintilla.SCI_MULTIPLESELECTADDNEXT, 0)
				else:
					self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_MATCHCASE)
			self.SendScintilla(QsciScintilla.SCI_MULTIPLESELECTADDNEXT, 0)
		elif event.modifiers() == Qt.ControlModifier | Qt.ShiftModifier and event.key() == Qt.Key_G:
			self.SendScintilla(QsciScintilla.SCI_TARGETWHOLEDOCUMENT, 0)
			if self.SendScintilla(QsciScintilla.SCI_GETSELECTIONEMPTY, 0) == 1:
				self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_MATCHCASE + QsciScintilla.SCFIND_WHOLEWORD)
			else:
				self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_MATCHCASE)
			self.SendScintilla(QsciScintilla.SCI_MULTIPLESELECTADDEACH, 0)
			self.SendScintilla(QsciScintilla.SCI_MULTIPLESELECTADDEACH, 0)
		super().keyPressEvent(event)

	def contextMenuEvent(self, e: QContextMenuEvent):
		ctx = self.createStandardContextMenu()
		if self.hasSelectedText():
			menu = ctx.addMenu("Run Macro On Selection")
			for container_id, container, macroName in APP().find_macros_by_input_types(["STRING"]):
				menu.addAction(macroName, lambda c=container, name=macroName: self._runMacroOnSelection(c, name))

		ctx.exec(e.globalPos())

	def _runMacroOnSelection(self, container, macroname):
		macro = container.getMacro(macroname)
		r = macro.execute(self.selectedText())
		if macro.output_type == 'STRING' and r is not None:
			self.replaceSelectedText(r)

	def setContents(self, content):
		self.setText(content)


class QsciLexerFormatinfo(QsciLexerCPP):
	def keywords(self, p_int):
		if p_int == 1:
			return "variant struct bits union switch case repeat true false null"
		elif p_int == 2:
			return " ".join(format_info.builtinTypes.keys())
		else:
			return super().keywords(p_int)

class QsciLexerFormatinfo2(QsciLexerCustom):
	Punctuation = 27
	Number = 4
	Operator = 10
	String_Double = 6
	Comment_Multiline = 1
	Name = 11           			# IDENTIFIER
	Name_Class = 19     			# GLOBAL_IDENTIFIER
	Name_Property = 25  			# FIELD_NAME_IDENTIFIER
	Name_Variable_Instance = 11		# VAR_REF_IDENTIFIER
	Name_Builtin = 9					# TYPE_REF_IDENTIFIER
	Name_Function = 14				# FUN_NAME_IDENTIFIER
	Name_Attribute = 16				# KEY_IDENTIFIER
	Keyword = 5
	Keyword_Constant = 17
	Syntax_error = 2

	def __init__(self, parent, lexer_start):
		super().__init__(parent)
		self.lexer_start = lexer_start
		self.create_parser()
		self.create_styles()

	def create_styles(self):
		self.token_styles = {
			"LBRACE": QsciLexerFormatinfo2.Punctuation,
			"RBRACE": QsciLexerFormatinfo2.Punctuation,
			"ESCAPED_STRING": QsciLexerFormatinfo2.String_Double,
			"NUMBER": QsciLexerFormatinfo2.Number,
			"LPAR": QsciLexerFormatinfo2.Punctuation,
			"RPAR": QsciLexerFormatinfo2.Punctuation,
			"COMMA": QsciLexerFormatinfo2.Punctuation,
			"LSQB": QsciLexerFormatinfo2.Punctuation,
			"RSQB": QsciLexerFormatinfo2.Punctuation,
			"EQUAL": QsciLexerFormatinfo2.Operator,
			"COLON": QsciLexerFormatinfo2.Operator,
			"DOT": QsciLexerFormatinfo2.Operator,
			"DOTS": QsciLexerFormatinfo2.Operator,
			"TERM_OP": QsciLexerFormatinfo2.Operator,
			"FACTOR_OP": QsciLexerFormatinfo2.Operator,
			"CONJ_OP": QsciLexerFormatinfo2.Operator,
			"EQ_OP": QsciLexerFormatinfo2.Operator,
			"COMP_OP": QsciLexerFormatinfo2.Operator,
			"DOLLAR": QsciLexerFormatinfo2.Operator,

			"IDENTIFIER": QsciLexerFormatinfo2.Name,
			"GLOBAL_IDENTIFIER": QsciLexerFormatinfo2.Name_Class,
			"FIELD_NAME_IDENTIFIER": QsciLexerFormatinfo2.Name_Property,
			"VAR_REF_IDENTIFIER": QsciLexerFormatinfo2.Name_Variable_Instance,
			"TYPE_REF_IDENTIFIER": QsciLexerFormatinfo2.Name_Builtin,
			"FUN_NAME_IDENTIFIER": QsciLexerFormatinfo2.Name_Function,
			"KEY_IDENTIFIER": QsciLexerFormatinfo2.Name_Attribute,

			"VARIANT": QsciLexerFormatinfo2.Keyword,
			"STRUCT": QsciLexerFormatinfo2.Keyword,
			"BITS": QsciLexerFormatinfo2.Keyword,
			"UNION": QsciLexerFormatinfo2.Keyword,
			"SWITCH": QsciLexerFormatinfo2.Keyword,
			"CASE": QsciLexerFormatinfo2.Keyword,
			"REPEAT": QsciLexerFormatinfo2.Keyword,

			"TRUE": QsciLexerFormatinfo2.Keyword_Constant,
			"FALSE": QsciLexerFormatinfo2.Keyword_Constant,
			"NULL": QsciLexerFormatinfo2.Keyword_Constant,

			"MULTILINE_COMMENT": QsciLexerFormatinfo2.Comment_Multiline,
		}

	def create_parser(self):
		from pre_workbench.structinfo.expr import fi_parser_hilight
		self.lark = fi_parser_hilight

	def language(self):
		return "FormatInfo"

	def description(self, style):
		return {v: k for k, v in self.token_styles.items()}.get(style, "")

	def styleText(self, start, end):
		text = self.parent().text()
		last_pos = 0

		try:
			tree = self.lark.parse(text, self.lexer_start, )
		except Exception as e:
			self.startStyling(start)
			self.setStyling(end-start, QsciLexerFormatinfo2.Syntax_error)
			print(e)
			return
		self.startStyling(0)
		try:
			for token in tree.scan_values(lambda x:True):
				#print("token: ",token, isinstance(token, lark.Token))
				if not isinstance(token, Token): continue
				ws_len = token.start_pos - last_pos
				if ws_len:
					self.setStyling(ws_len, 0)    # whitespace

				token_len = len(bytearray(token, "utf-8"))
				typ = token.type
				if typ == "IDENTIFIER" and token.column == 1: typ = "DEF_IDENTIFIER"
				self.setStyling(token_len, self.token_styles.get(typ, 0))
				if not typ in self.token_styles: print(typ)

				last_pos = token.start_pos + token_len
		except Exception as e:
			print(e)

def showScintillaDialog(parent, title, content, ok_callback, readonly=False, lexer=None, help_callback=None):
	dlg = QDialog(parent)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.resize(800,600)
	sg = ScintillaEdit(lexer=lexer)
	sg.setText(content)
	sg.setReadOnly(readonly)
	dlg.layout().addWidget(sg)
	box = makeDlgButtonBox(dlg, ok_callback, lambda: sg.text(), help_callback)
	sg.escapePressed.connect(box.rejected.emit)
	sg.ctrlEnterPressed.connect(box.accepted.emit)
	if dlg.exec() == QDialog.Rejected: return None
	return sg.text()
