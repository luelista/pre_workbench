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
import time
import traceback

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMenu, QFileDialog, QTreeWidget, QTreeWidgetItem, \
	QTreeWidgetItemIterator, QMessageBox, QAction
from pre_workbench.consts import SYNTAX_REFERENCE_URL

from pre_workbench import configs, guihelper
from pre_workbench.algo.range import Range
from pre_workbench.configs import SettingsField
from pre_workbench.controls.genericwidgets import showSettingsDlg
from pre_workbench.controls.scintillaedit import showScintillaDialog
from pre_workbench.guihelper import getMonospaceFont, filledColorIcon, setClipboardText, navigateBrowser, \
	isOptionPressed
from pre_workbench.interactive_fic import InteractiveFormatInfoContainer
from pre_workbench.structinfo.format_info import FormatInfo, StructFI, VariantStructFI, SwitchFI, RepeatStructFI, \
	UnionFI, BitStructFI
from pre_workbench.typeeditor import showTypeEditorDlg, showTreeEditorDlg
from pre_workbench.util import PerfTimer, truncate_str


class RangeTreeWidget(QTreeWidget):
	RangeRole = QtCore.Qt.UserRole
	BytesOffsetRole = QtCore.Qt.UserRole + 1
	BytesSizeRole = QtCore.Qt.UserRole + 2
	SourceDescRole = QtCore.Qt.UserRole + 3

	def __init__(self, parent=None):
		super().__init__(parent)
		self.itemActivated.connect(self._fiTreeItemActivated)
		self.setColumnCount(6)
		self.setColumnWidth(0, 280)
		self.headerItem().setText(0, "Grammar Tree")
		self.headerItem().setText(1, "Offset")
		self.headerItem().setText(2, "Type")
		self.setColumnWidth(3, 180)
		self.headerItem().setText(3, "Displayed Value")
		self.headerItem().setText(4, "Raw Value")
		self.headerItem().setText(5, "Print")
		self.header().moveSection(3, 1)
		self.header().moveSection(5, 3)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self._onCustomContextMenuRequested)
		self.header().setContextMenuPolicy(Qt.CustomContextMenu)
		self.header().customContextMenuRequested.connect(self._onHeaderCustomContextMenuRequested)
		self.formatInfoContainer = None
		self.optionsConfigKey = "RangeTree"
		self.setMouseTracking(True)
		self.setAcceptDrops(True)
		self.onlyPrintable = False

	def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
		super().wheelEvent(a0)
		a0.accept()

	def updateTree(self, fi_trees):
		self.clear()
		for fi_tree in fi_trees:
			if fi_tree is None: continue
			Range_addToTree(fi_tree, self, self.onlyPrintable)

	def _fiTreeItemActivated(self, item, column):
		pass

	def hilightFormatInfoTree(self, range):
		start_time = time.perf_counter()
		count = 0
		iterator = QTreeWidgetItemIterator(self)
		self.setUpdatesEnabled(False)
		while iterator.value():
			item = iterator.value()
			itemRange = item.data(0, RangeTreeWidget.RangeRole)
			bgColor = QColor("#dddddd") if itemRange is not None and itemRange.overlaps(range) else QColor("#ffffff")
			with PerfTimer("setBackground"):
				item.setBackground(0, bgColor)
			#item.setProperty("class", "highlighted" if itemRange is not None and itemRange.overlaps(range) else "")
			iterator += 1
			count += 1
		self.setUpdatesEnabled(True)
		logging.debug("hilightFormatInfoTree took %f sec for %d items", (time.perf_counter() - start_time), count)


	################################################
	#region Context Menu
	################################################

	def _onCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		if item := self.itemAt(point):
			range = item.data(0, RangeTreeWidget.RangeRole)
			source = item.data(0, RangeTreeWidget.SourceDescRole)

			parentSource = item.parent().data(0, RangeTreeWidget.SourceDescRole) if item.parent() else None
			if isinstance(source, FormatInfo):
				ctx.addAction("Edit ...", lambda: self.editField(source))
				if isinstance(source.fi, (StructFI, UnionFI)):
					ctx.addAction("Add field ...", lambda: self.addField(source, "StructField"))
					ctx.addSeparator()
				if isinstance(source.fi, VariantStructFI):
					ctx.addAction("Add variant ...", lambda: self.addField(source, "AnyFI"))
					ctx.addSeparator()
				if isinstance(source.fi, SwitchFI):
					ctx.addAction("Add case ...", lambda: self.addField(source, "SwitchItem"))
					ctx.addSeparator()
				if isOptionPressed():
					ctx.addAction("Edit tree ...", lambda: self.editField2(source))
				ctx.addAction("Visualization ...", lambda: self.editDisplayParams(source))
				ctx.addAction("Repeat ...", lambda: self.repeatField(source))
				ctx.addAction("Hide field", lambda: self.styleSelection(source, hide=1))
				if parentSource is not None and isinstance(parentSource.fi, (StructFI, UnionFI, BitStructFI)):
					ctx.addAction("Delete field", lambda: self.removeField(parentSource, range.field_name))
					ctx.addSeparator()
				ctx.addSeparator()
				for key, name, style in guihelper.getHighlightStyles():
					ctx.addAction(name+"\t"+key, lambda style=style: self.styleSelection(source, **style))
				ctx.addSeparator()
			ctx.addAction("Copy", lambda: setClipboardText("\t".join(item.text(i) for i in range(item.columnCount()))))
		ctx.addSeparator()
		self._buildGenericContextMenu(ctx)

		ctx.exec(self.mapToGlobal(point))

	def _onHeaderCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		self._buildGenericContextMenu(ctx)
		ctx.exec(self.mapToGlobal(point))

	def _buildGenericContextMenu(self, ctx):
		ctx.addAction("Expand All", lambda: self.expandAll())
		ctx.addAction("Collapse All", lambda: self.collapseAll())
		ctx.addAction(QAction(parent=ctx, text="Only printable", triggered=self._toggleOnlyPrintable, checkable=True, checked=self.onlyPrintable))


	def _toggleOnlyPrintable(self):
		self.onlyPrintable = not self.onlyPrintable

	def addField(self, parent, typeName):
		def ok(params):
			parent.updateParams(children=parent.params['children']+[params])
			self._afterUpdate()

		showTypeEditorDlg("format_info.tes", typeName, ok_callback=ok)

	def removeField(self, parent, field_name):
		ch = parent.params['children']
		del ch[next(i for i,(comment,key,el) in enumerate(ch) if key == field_name)]
		parent.updateParams(children=ch)
		self._afterUpdate()

	def editDisplayParams(self, parent):
		from pre_workbench.structinfo import ExprFunctions
		showModes = [("","")] + ExprFunctions.getSelectList('name')
		params = showSettingsDlg([
			SettingsField("color", "Background color", "color", {"color":True}),
			SettingsField("textcolor", "Text color", "color", {"color":True}),
			SettingsField("section", "Section header", "text", {}),
			SettingsField("show", "Value display style", "select", {"editable":True,"options":showModes}),
		], title="Edit display params", values=parent.params, parent=self)
		if params is None: return
		if params.get("color") == "": params["color"] = None
		if params.get("textcolor") == "": params["textcolor"] = None
		if params.get("section") == "": params["section"] = None
		if params.get("show") == "": params["show"] = None
		parent.updateParams(**params)
		self._afterUpdate()

	def styleSelection(self, parent, **styles):
		parent.updateParams(**styles)
		self._afterUpdate()

	def editField(self, element: FormatInfo):
		"""
		params = showTypeEditorDlg("format_info.tes", "AnyFI", element.serialize())
		if params is None: return
		element.deserialize(params)
		"""
		#result, ok = QInputDialog.getMultiLineText(self, "Edit field", "Edit field", element.to_text(0, None))
		#if ok:
		def ok_callback(result):
			element.from_text(result)
			self._afterUpdate()
		showScintillaDialog(self, "Edit field", element.to_text(0, None), ok_callback=ok_callback, help_callback=lambda: navigateBrowser(SYNTAX_REFERENCE_URL))

	def editField2(self, element: FormatInfo):
		def ok_callback(params):
			element.deserialize(params)
			self._afterUpdate()
		showTreeEditorDlg("format_info.tes", "AnyFI", element.serialize(), ok_callback=ok_callback)

	def repeatField(self, element: FormatInfo):
		def ok_callback(params):
			element.setContents(RepeatStructFI, params)
			self._afterUpdate()

		showTypeEditorDlg("format_info.tes", "RepeatStructFI", { "children": element.serialize() }, ok_callback=ok_callback)

	def _afterUpdate(self):
		# TODO BUG - this causes a parse of the wrong container to be shown in the Grammar Parse Result!
		self.saveFormatInfo(self.formatInfoContainer.file_name)

	#endregion

	################################################
	#region File Handling
	################################################

	def newFormatInfo(self):
		fileName, _ = QFileDialog.getSaveFileName(self, "Save Grammar File",
												  configs.getValue(self.optionsConfigKey + "_lastOpenFile", ""),
												  "Grammar Files (*.pfi *.txt)")
		if not fileName: return
		self.formatInfoContainer = InteractiveFormatInfoContainer(load_from_string="DEFAULT struct(endianness="<") {}")
		self.formatInfoContainer.file_name = fileName
		self.saveFormatInfo(self.formatInfoContainer.file_name)

	def fileOpenFormatInfo(self):
		fileName, _ = QFileDialog.getOpenFileName(self,"Load Grammar File", configs.getValue(self.optionsConfigKey+"_lastOpenFile",""),"Grammar Files (*.pfi *.txt)")
		if fileName:
			configs.setValue(self.optionsConfigKey+"_lastOpenFile", fileName)
			self.loadFormatInfo(load_from_file=fileName)

	def loadFormatInfo(self, **loadSrc):
		try:
			self.formatInfoContainer = InteractiveFormatInfoContainer(**loadSrc)
		except Exception as ex:
			traceback.print_exc()
			QMessageBox.warning(self, "Failed to parse Grammar File", str(ex))
			return

	def saveFormatInfo(self, fileName):
		self.formatInfoContainer.write_file(fileName)

	def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
		self.dragMoveEvent(e)

	def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:
		if e.mimeData().hasUrls():
			e.acceptProposedAction()

	def dropEvent(self, e: QtGui.QDropEvent) -> None:
		logging.debug("dropEvent %s %r", e, e.mimeData().formats())
		if e.mimeData().hasUrls():
			fileName = e.mimeData().urls()[0].toLocalFile()
			logging.debug("dropEvent %s %r", fileName, e.mimeData().urls())
			self.loadFormatInfo(load_from_file=fileName)
			e.setDropAction(Qt.CopyAction)
			e.accept()

	#endregion


def Range_addToTree(range: Range, parent: QTreeWidgetItem, printableOnly: bool = False):
	x = range
	collapse = x.field_name.startswith("_")
	text0 = x.field_name
	text1 = str(x.start) + "+" + str(x.bytes_size)
	text2 = str(x.source_desc)
	color = x.metadata.get("color")
	print = []
	if x.metadata.get("print"): print.append(x.metadata["print"])
	while type(x.value) == Range:
		x = x.value
		if x.field_name.startswith("_"): collapse = True
		text0 += " >> " + x.field_name
		text1 += " >> " + str(x.start) + "+" + str(x.bytes_size)
		text2 += " >> " + str(x.source_desc)
		if x.metadata.get("color"): color = x.metadata["color"]
		if x.metadata.get("print"): print.append(x.metadata["print"])

	if ((len(print) > 0 or not printableOnly) and not x.metadata.get("hide")) or x.exception is not None:
		me = QTreeWidgetItem(parent)
		me.setData(0, RangeTreeWidget.RangeRole, range)
		me.setData(0, RangeTreeWidget.BytesOffsetRole, range.start)
		me.setData(0, RangeTreeWidget.BytesSizeRole, range.bytes_size)
		me.setData(0, RangeTreeWidget.SourceDescRole, x.source_desc)
		me.setFont(5, getMonospaceFont())
		me.setText(0, truncate_str(text0))
		me.setText(1, truncate_str(text1))
		me.setText(2, truncate_str(text2))
		if x.exception is not None:
			me.setForeground(3, QColor("red"))
			me.setText(3, str(x.exception).split("\n", 1)[0])
		elif type(x.value) == dict:
			if not collapse: me.setExpanded(True)
			for item in x.value.values():
				Range_addToTree(item, me, printableOnly)
		elif type(x.value) == list:
			if not collapse:me.setExpanded(True)
			for item in x.value:
				Range_addToTree(item, me, printableOnly)
		else:
			try:
				me.setText(3, truncate_str(x.source_desc.formatter(x.value)))
			except:
				me.setText(3, truncate_str(x.value))
		if color:
			me.setIcon(3, filledColorIcon(color, 16))
		me.setText(5, " >> ".join(print))
	else:
		if type(x.value) == dict:
			for item in x.value.values():
				Range_addToTree(item, parent, printableOnly)
		if type(x.value) == list:
			for item in x.value:
				Range_addToTree(item, parent, printableOnly)

