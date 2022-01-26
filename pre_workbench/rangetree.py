import traceback

from PyQt5.QtCore import (Qt, pyqtSignal)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMenu, QFileDialog, QTreeWidget, QTreeWidgetItem, \
	QTreeWidgetItemIterator, QMessageBox

from pre_workbench.configs import SettingsField
from pre_workbench import configs
from pre_workbench.genericwidgets import showSettingsDlg
from pre_workbench.algo.rangelist import Range

from pre_workbench.structinfo.format_info import FormatInfo, StructFI, VariantStructFI, SwitchFI, RepeatStructFI
from pre_workbench.structinfo.parsecontext import FormatInfoContainer
from pre_workbench.structinfo.serialization import deserialize_fi
from pre_workbench.textfile import showScintillaDialog
from pre_workbench.typeeditor import showTypeEditorDlg, showTreeEditorDlg


class InteractiveFormatInfoContainer(FormatInfoContainer):
	def __init__(self, parent, **kw):
		super().__init__(**kw)
		self.parent = parent

	def get_fi_by_def_name(self, def_name):
		try:
			return self.definitions[def_name]
		except KeyError:
			if QMessageBox.question(self.parent, "Format Info", "Reference to undefined formatinfo '"+def_name+"'. Create it now?") == QMessageBox.Yes:
				params = showTypeEditorDlg("format_info.tes", "AnyFI", title="Create formatinfo '"+def_name+"'")
				if params is None: raise
				self.definitions[def_name] = deserialize_fi(params)
				return self.definitions[def_name]
			else:
				raise



class RangeTreeWidget(QTreeWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.itemActivated.connect(self.fiTreeItemActivated)
		self.setColumnCount(5)
		self.setColumnWidth(0, 400)
		self.headerItem().setText(0, "Grammar Tree")
		self.headerItem().setText(1, "Offset")
		self.headerItem().setText(2, "Type")
		self.setColumnWidth(3, 200)
		self.headerItem().setText(3, "Displayed Value")
		self.headerItem().setText(4, "Raw Value")
		self.header().moveSection(3, 1)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		self.formatInfoContainer = None
		self.optionsConfigKey = "RangeTree"
		self.setMouseTracking(True)

	formatInfoUpdated = pyqtSignal()

	def updateTree(self, fi_tree):
		self.clear()
		if fi_tree is not None:
			root = QTreeWidgetItem(self)
			root.setExpanded(True)
			if self.formatInfoContainer:
				root.setText(0, self.formatInfoContainer.file_name)
			fi_tree.addToTree(root)

	def fiTreeItemActivated(self, item, column):
		pass

	def hilightFormatInfoTree(self, range):
		iterator = QTreeWidgetItemIterator(self)
		while iterator.value():
			item = iterator.value()
			itemRange = item.data(0, Range.RangeRole)
			item.setBackground(0, QColor("#dddddd") if itemRange is not None and itemRange.overlaps(range) else QColor("#ffffff"))
			#item.setProperty("class", "highlighted" if itemRange is not None and itemRange.overlaps(range) else "")
			iterator += 1

	def onCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		item = self.itemAt(point)
		if item != None:
			range = item.data(0, Range.RangeRole)
			source = item.data(0, Range.SourceDescRole)

			if item.parent() != None:
				parentSource = item.parent().data(0, Range.SourceDescRole)
			if isinstance(source, FormatInfo):
				if isinstance(source.fi, StructFI):
					ctx.addAction("Add field ...", lambda: self.addField(source, "StructField"))
					ctx.addSeparator()
				if isinstance(source.fi, VariantStructFI):
					ctx.addAction("Add variant ...", lambda: self.addField(source, "AnyFI"))
					ctx.addSeparator()
				if isinstance(source.fi, SwitchFI):
					ctx.addAction("Add case ...", lambda: self.addField(source, "SwitchItem"))
					ctx.addSeparator()
				if parentSource is not None and isinstance(parentSource, StructFI):
					ctx.addAction("Remove this field", lambda: self.removeField(parentSource, range.field_name))
					ctx.addSeparator()
				ctx.addAction("Edit ...", lambda: self.editField(source))
				ctx.addAction("Edit tree ...", lambda: self.editField2(source))
				ctx.addAction("Visualization ...", lambda: self.editDisplayParams(source))
				ctx.addAction("Repeat ...", lambda: self.repeatField(source))
				ctx.addSeparator()
		else:
			ctx.addAction("Edit ...", lambda: self.editField(self.formatInfoContainer.definitions[self.formatInfoContainer.main_name]))

		ctx.addAction("New format info ...", self.newFormatInfo)
		ctx.addAction("Load format info ...", self.fileOpenFormatInfo)
		if self.formatInfoContainer and self.formatInfoContainer.file_name:
			ctx.addAction("Save format info", lambda: self.saveFormatInfo(self.formatInfoContainer.file_name))
		ctx.exec(self.mapToGlobal(point))

	def addField(self, parent, typeName):
		def ok(params):
			parent.updateParams(children=parent.params['children']+[params])
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)

		params = showTypeEditorDlg("format_info.tes", typeName, ok_callback=ok)


	def removeField(self, parent, field_name):
		ch = parent.params['children']
		del ch[field_name]
		parent.updateParams(children=ch)
		self.formatInfoUpdated.emit()


	def editDisplayParams(self, parent):
		params = showSettingsDlg([
			SettingsField("color", "Background color", "color", {"color":True}),
			SettingsField("textcolor", "Text color", "color", {"color":True}),
			SettingsField("section", "Section header", "text", {}),
		], title="Edit display params", values=parent.params, parent=self)
		if params is None: return
		if params.get("color") == "": params["color"] = None
		if params.get("textcolor") == "": params["textcolor"] = None
		if params.get("section") == "": params["section"] = None
		parent.updateParams(**params)
		self.formatInfoUpdated.emit()
		self.saveFormatInfo(self.formatInfoContainer.file_name)

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
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showScintillaDialog(self, "Edit field", element.to_text(0, None), ok_callback=ok_callback)


	def editField2(self, element: FormatInfo):
		def ok_callback(params):
			element.deserialize(params)
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showTreeEditorDlg("format_info.tes", "AnyFI", element.serialize(), ok_callback=ok_callback)


	def repeatField(self, element: FormatInfo):
		def ok_callback(params):
			element.setContents(RepeatStructFI, params)
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)

		showTypeEditorDlg("format_info.tes", "RepeatStructFI", { "children": element.serialize() }, ok_callback=ok_callback)

	def newFormatInfo(self):
		def ok_callback(params):
			fileName, _ = QFileDialog.getSaveFileName(self, "Save format info",
													  configs.getValue(self.optionsConfigKey + "_lastOpenFile", ""),
													  "Format Info files (*.pfi *.txt)")
			if not fileName: return
			self.formatInfoContainer = InteractiveFormatInfoContainer(self, )
			self.formatInfoContainer.main_name = "DEFAULT"
			self.formatInfoContainer.definitions["DEFAULT"] = deserialize_fi(params)
			self.formatInfoContainer.file_name = fileName
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showTypeEditorDlg("format_info.tes", "AnyFI", ok_callback=ok_callback)

	def fileOpenFormatInfo(self):
		fileName, _ = QFileDialog.getOpenFileName(self,"Load format info", configs.getValue(self.optionsConfigKey+"_lastOpenFile",""),"Format Info files (*.pfi *.txt)")
		if fileName:
			configs.setValue(self.optionsConfigKey+"_lastOpenFile", fileName)
			self.loadFormatInfo(load_from_file=fileName)

	def loadFormatInfo(self, **loadSrc):
		try:
			self.formatInfoContainer = InteractiveFormatInfoContainer(self, **loadSrc)
		except Exception as ex:
			traceback.print_exc()
			QMessageBox.warning(self, "Failed to parse format info description", str(ex))
			return
		self.formatInfoUpdated.emit()

	def saveFormatInfo(self, fileName):
		self.formatInfoContainer.write_file(fileName)
