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
import hashlib
import inspect
import logging
import os
import re
import subprocess
import tempfile
import weakref
import shlex
from copy import deepcopy

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices, QColor
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView, QMenu, \
	QAction, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit, QToolBar, QComboBox, QMessageBox

import pre_workbench.app
from pre_workbench import configs
from pre_workbench.algo.range import Range
from pre_workbench.configs import getIcon, SettingsField
from pre_workbench.controls.genericwidgets import showSettingsDlg
from pre_workbench.controls.scintillaedit import showScintillaDialog
from pre_workbench.errorhandler import ConsoleWindowLogHandler
from pre_workbench.guihelper import filledColorIcon, getMonospaceFont, runProcessWithDlg, qApp, TODO
from pre_workbench.app import navigate
from pre_workbench.macros.macro import Macro
from pre_workbench.rangetree import RangeTreeWidget
from pre_workbench.structinfo.parsecontext import AnnotatingParseContext
from pre_workbench.windows.content.textfile import ScintillaEdit
from pre_workbench.typeeditor import JsonView
from pre_workbench.typeregistry import WindowTypes
from pre_workbench.util import PerfTimer, truncate_str


class FileBrowserWidget(QWidget):
	on_open = pyqtSignal(str)
	def __init__(self, rootFolder):
		super().__init__()
		self._initUI()
		self.setRoot(rootFolder)

	def _initUI(self):
		self.model = QFileSystemModel()
		self.tree = QTreeView()
		self.tree.setModel(self.model)

		self.tree.setAnimated(False)
		self.tree.setIndentation(20)
		self.tree.setSortingEnabled(True)
		self.tree.sortByColumn(0, 0)
		self.tree.setColumnWidth(0, 200)
		self.tree.setDragEnabled(True)
		self.tree.setAcceptDrops(True)

		self.tree.setWindowTitle("Dir View")
		self.tree.resize(640, 480)
		self.tree.doubleClicked.connect(self.onDblClick)
		self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.tree.customContextMenuRequested.connect(self.onCustomContextMenuRequested)

		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.tree)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def onCustomContextMenuRequested(self, point):
		index = self.tree.indexAt(point)
		selectedFile = None
		selectedFolder = None
		ctx = QMenu("Context menu", self)
		if index.isValid():
			file = self.model.fileInfo(index)
			selectedFile = file.absoluteFilePath()
			selectedFolder = selectedFile if file.isDir() else file.absolutePath()
			if file.isDir():
				ctx.addAction("Open as directory of binary files", lambda: navigate("WINDOW", "Type=ObjectWindow", "FileName=" + selectedFile,
																			   "dataSourceType=DirectoryOfBinFilesDataSource"))
				ctx.addSeparator()
				ctx.addAction("Open in file manager", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(selectedFile)))
			else:
				for wndTyp, meta in WindowTypes.types:
					text = 'Open with '+meta.get('displayName', meta['name'])
					ctx.addAction(QAction(text, self, statusTip=text, icon=getIcon(meta.get('icon', 'document.png')),
											   triggered=lambda dummy, meta=meta: navigate("WINDOW", "Type="+meta['name'], "FileName="+selectedFile)))
				ctx.addSeparator()
				ctx.addAction("Open in default application", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(selectedFile)))
		else:
			ctx.addAction("Open in file manager", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.model.rootPath())))
		#ctx.addAction("Set root folder ...", lambda: self.selectRootFolder(preselect=selectedFolder))
		ctx.exec(self.tree.viewport().mapToGlobal(point))

	def setRoot(self, dir):
		self.rootFolder = dir
		self.model.setRootPath(dir)
		self.tree.setRootIndex(self.model.index(dir))

	def onDblClick(self, index):
		if index.isValid():
			file = self.model.fileInfo(index)
			if not file.isDir():
				navigate("OPEN", "FileName="+file.absoluteFilePath())

	def saveState(self):
		if self.tree.currentIndex().isValid():
			info = self.model.fileInfo(self.tree.currentIndex())
			return { "sel": info.absoluteFilePath(), "root": self.rootFolder, "hs": self.tree.header().saveState() }

	def restoreState(self, state):
		try:
			idx = self.model.index(state["sel"])
			if idx.isValid():
				self.tree.expand(idx)
				self.tree.setCurrentIndex(idx)
				self.tree.scrollTo(idx, QAbstractItemView.PositionAtCenter)
		except:
			pass
		if "hs" in state: self.tree.header().restoreState(state["hs"])


class MdiWindowListWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		self.list = QListWidget()
		#self.list.doubleClicked.connect(self.onDblClick)
		self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.list.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		self.list.itemClicked.connect(self.gotoItem)

		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.list)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def gotoItem(self, item):
		windowId = item.data(QtCore.Qt.UserRole)
		navigate("WINDOW-ID", "Id="+windowId)

	def updateWindowList(self, wndList):
		logging.debug("MdiWindowListWidget.updateWindowList (len=%d)", len(wndList))
		self.list.clear()
		for window in wndList:
			if not hasattr(window.widget(), 'child_wnd_meta'): continue
			listitem = QListWidgetItem(window.windowTitle())
			listitem.setData(QtCore.Qt.UserRole, window.widget().objectName())
			listitem.setIcon(window.windowIcon())
			self.list.addItem(listitem)

	def onCustomContextMenuRequested(self, point):
		item = self.list.itemAt(point)
		ctx = QMenu("Context menu", self)
		if item is not None:
			ctx.addAction("Close window", lambda: self.closeWindow(item))

		ctx.addAction("Close all windows", lambda: self.closeAllWindows())
		ctx.exec(self.list.viewport().mapToGlobal(point))

	def onSubWindowActivated(self, window):
		if window is None: return
		for i in range(self.list.count()):
			if self.list.item(i).data(QtCore.Qt.UserRole) == window.objectName():
				self.list.setCurrentRow(i)


class StructInfoTreeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()

		self._updateContent()
		pre_workbench.app.CurrentProject.formatInfoContainer.updated.connect(self._updateContent)

	def _updateContent(self):
		try:
			self.tree.set([(k,v.serialize()) for k,v in pre_workbench.app.CurrentProject.formatInfoContainer.definitions.items()])
		except:
			logging.exception("failed to load StructInfoTree")

	def _initUI(self):
		self.tree = JsonView(schema="format_info.tes", rootTypeDefinition="FormatInfoFile")
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.tree)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)


class StructInfoCodeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self._updateContent()
		pre_workbench.app.CurrentProject.formatInfoContainer.updated.connect(self._updateContent)
		self.editor.ctrlEnterPressed.connect(self._applyContent)

	def _updateContent(self):
		self.editor.setText(pre_workbench.app.CurrentProject.formatInfoContainer.to_text())

	def _applyContent(self):
		pre_workbench.app.CurrentProject.formatInfoContainer.load_from_string(self.editor.text())
		pre_workbench.app.CurrentProject.formatInfoContainer.write_file(None)

	def _initUI(self):
		self.editor = ScintillaEdit()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.editor)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.editor.show()


class RangeTreeDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		#self.lastBuffer = lambda : None # dead weakref
		self.lastHexView = lambda : None   # dead weakref
		self.fiTreeWidget.formatInfoContainer = pre_workbench.app.CurrentProject.formatInfoContainer

	def _initUI(self):
		self.fiTreeWidget = RangeTreeWidget()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.fiTreeWidget)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.fiTreeWidget.show()
		self.fiTreeWidget.currentItemChanged.connect(self._fiTreeItemSelected)

	def _fiTreeItemSelected(self, item, previous):
		if item is None: return
		range = item.data(0, RangeTreeWidget.RangeRole)
		hexView = self.lastHexView()
		if range is not None and hexView is not None:
			hexView.selectRange(range, scrollIntoView=True)

	def on_meta_update(self, event_id, param):
		if param is None or not self.isVisible(): return
		if event_id == "hexview_range":
			with PerfTimer("RangeTreeWidget update"):
				#buf = param.buffers[param.selBuffer]
				logging.debug("RangeTreeDockWidget %r %r", self.lastHexView(), param)
				if self.lastHexView() is not param:
					self.lastHexView = weakref.ref(param)
					self.fiTreeWidget.updateTree([buf.fi_tree for buf in param.buffers])
				self.fiTreeWidget.hilightFormatInfoTree(param.selRange())
		elif event_id == "grammar":
			self.fiTreeWidget.updateTree(param)

	def saveState(self):
		return {"hs": self.fiTreeWidget.header().saveState()}
	def restoreState(self, data):
		if "hs" in data: self.fiTreeWidget.header().restoreState(data["hs"])





class DataInspectorWidget(QWidget):
	defaultdef = """
	DataInspector union (ignore_errors=true, endianness=">"){
		uint8 UINT8
		int8 INT8
		uint8_bin UINT8(show="{0:08b}")
		uint16_BE UINT16(endianness=">")
		uint32_BE UINT32(endianness=">")
		int16_BE INT16(endianness=">")
		int32_BE INT32(endianness=">")
		float_BE FLOAT(endianness=">")
		double_BE DOUBLE(endianness=">")
		uint16_LE UINT16(endianness="<")
		uint32_LE UINT32(endianness="<")
		int16_LE INT16(endianness="<")
		int32_LE INT32(endianness="<")
		float_LE FLOAT(endianness="<")
		double_LE DOUBLE(endianness="<")
		ipv4 IPv4
		ether ETHER
	}
	"""
	def __init__(self):
		super().__init__()
		self.selbytes = None
		self._initUI()
		self.loadFormatInfo()
		self.fiTreeWidget.formatInfoContainer.updated.connect(self.parse)

	def saveState(self):
		return {"hs": self.fiTreeWidget.header().saveState()}
	def restoreState(self, data):
		if "hs" in data: self.fiTreeWidget.header().restoreState(data["hs"])

	def on_select_bytes(self, selbytes):#buffer:ByteBuffer, range:Range):
		if not self.isVisible(): return
		self.selbytes = selbytes
		self.parse()

	def parse(self):
		with PerfTimer("DataInspector parsing"):
			if not self.selbytes: return
			parse_context = AnnotatingParseContext(self.fiTreeWidget.formatInfoContainer, self.selbytes) #buffer.getBytes(range.start, range.length()))
			fi_tree = parse_context.parse()
			self.fiTreeWidget.updateTree([fi_tree])

	def _initUI(self):
		self.fiTreeWidget = RangeTreeWidget()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.fiTreeWidget)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def loadFormatInfo(self):
		#definition = configs.getValue("DataInspectorDef", DataInspectorWidget.defaultdef)
		filespec = os.path.join(configs.dirs.user_config_dir, "data_inspector.txt")
		if not os.path.isfile(filespec):
			with open(filespec,"w") as f:
				f.write(DataInspectorWidget.defaultdef)

		#self.fiTreeWidget.loadFormatInfo(load_from_string=definition)
		self.fiTreeWidget.loadFormatInfo(load_from_file=filespec)


class RangeListWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(4)
		self.treeView.setColumnWidth(1, 300)
		self.treeView.headerItem().setText(0, "Range")
		self.treeView.headerItem().setText(1, "Name")
		self.treeView.headerItem().setText(2, "ShowName")
		self.treeView.headerItem().setText(2, "Show")
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def on_meta_update(self, event_id, sender):
		with PerfTimer("RangeListWidget update"):
			if event_id != "hexview_range" or sender is None or not self.isVisible(): return
			self.treeView.clear()
			for d in sender.buffers[sender.selBuffer].matchRanges(overlaps=sender.selRange()):
				root = QTreeWidgetItem(self.treeView)
				if "color" in d.metadata:
					root.setIcon(1, filledColorIcon(QColor(d.metadata["color"]), 16))
				root.setText(0, "Range %d-%d" % (d.start, d.end))
				root.setText(1, truncate_str(d.metadata.get("name")))
				root.setText(2, truncate_str(d.metadata.get("showname")))
				root.setText(3, truncate_str(d.metadata.get("show")))
				for k,v in d.metadata.items():
					if k != "name" and k != "showname" and k != "show":
						x = QTreeWidgetItem(root)
						x.setText(0, truncate_str(k))
						x.setText(1, truncate_str(v))
				# TODO ...on click: self.selectRange(d)


class MacroListDockWidget(QWidget):
	CONTAINER_ROLE = QtCore.Qt.UserRole + 100
	MACRO_NAME_ROLE = QtCore.Qt.UserRole + 101
	def __init__(self):
		super().__init__()
		self._initUI()
		self._loadList()

	def _initUI(self):
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(1)
		self.treeView.setColumnWidth(1, 300)
		self.treeView.headerItem().setText(0, "Name")
		self.treeView.customContextMenuRequested.connect(self.customContextMenuRequested)
		self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _loadList(self):
		self.treeView.clear()
		for title, container in qApp().macro_containers.items():
			root = QTreeWidgetItem(self.treeView, [title])
			root.setExpanded(True)
			root.setData(0, MacroListDockWidget.CONTAINER_ROLE, container)
			self._loadMacros(root, container)

	def _loadMacros(self, root, container):
		names = container.getMacroNames()
		for name in names:
			item = QTreeWidgetItem(root, [name])
			item.setData(0, MacroListDockWidget.CONTAINER_ROLE, container)
			item.setData(0, MacroListDockWidget.MACRO_NAME_ROLE, name)

	def customContextMenuRequested(self, point):
		item = self.treeView.itemAt(point)
		ctx = QMenu("Context menu", self)
		if item:
			container = item.data(0, MacroListDockWidget.CONTAINER_ROLE)
			macroname = item.data(0, MacroListDockWidget.MACRO_NAME_ROLE)
			if macroname:
				ctx.addAction("Execute", lambda: self.executeMacro(container.getMacro(macroname)))
				if container.macrosEditable:
					ctx.addAction("Edit code", lambda: self.editCode(container.getMacro(macroname)))
					ctx.addAction("Preferences", lambda: self.editPreferences(container.getMacro(macroname)))
					ctx.addAction("Delete macro", lambda: self.deleteMacro(container, macroname))
				else:
					ctx.addAction("View code", lambda: self.editCode(container.getMacro(macroname)))
				ctx.addSeparator()
				for title, target_container in qApp().macro_containers.items():
					if target_container.macrosEditable and target_container != container:
						ctx.addAction("Copy to " + title, lambda trg=target_container: self.copyMacro(container.getMacro(macroname), trg))
			else:
				if container.macrosEditable:
					ctx.addAction("Create macro ...", lambda: self.createMacro(container))
			ctx.exec(self.treeView.viewport().mapToGlobal(point))

	def deleteMacro(self, container, macroname):
		if QMessageBox.question(self, "Delete Macro", "Delete Macro \"" + macroname + "\"?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
			container.deleteMacro(macroname)
			self._loadList()

	def executeMacro(self, macro):
		if macro.input_type == Macro.TYPE_NONE:
			macro.execute(None)
		else:
			TODO()

	def editPreferences(self, macro):
		result = showSettingsDlg([
			SettingsField("name", "Name", "text", {}),
			SettingsField("input_type", "Input Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
			SettingsField("output_type", "Output Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
		], {"name": macro.name, "input_type": macro.input_type, "output_type": macro.output_type}, title="Edit Preferences Of Macro \"" + macro.name + "\"", parent=self)
		if not result: return
		macro.name = result["name"]
		macro.input_type = result["input_type"]
		macro.output_type = result["output_type"]
		macro.container.storeMacro(macro)
		self._loadList()

	def createMacro(self, container):
		result = showSettingsDlg([
			SettingsField("name", "Name", "text", {}),
			SettingsField("input_type", "Input Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
			SettingsField("output_type", "Output Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
		], title="Create Macro ...", parent=self)
		if not result: return
		macro = Macro(container, result["name"], result["input_type"], result["output_type"], "", [], {}, None)
		container.storeMacro(macro)
		self.editCode(macro)
		self._loadList()

	def copyMacro(self, macro, target_container):
		result = showSettingsDlg([
			SettingsField("name", "Name", "text", {}),
			SettingsField("input_type", "Input Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
			SettingsField("output_type", "Output Type", "select", {"options": zip(Macro.TYPES, Macro.TYPES)}),
		], {"name": macro.name, "input_type": macro.input_type, "output_type": macro.output_type}, title="Copy Macro ...", parent=self)
		if not result: return
		new_macro = Macro(target_container, result["name"], result["input_type"], result["output_type"], macro.code, deepcopy(macro.options), deepcopy(macro.metadata), None)
		target_container.storeMacro(new_macro)
		self._loadList()

	def editCode(self, macro):
		verb = "Edit" if macro.container.macrosEditable else "View"
		from PyQt5.Qsci import QsciLexerPython
		res = showScintillaDialog(self, verb + " Code Of Macro \""+macro.name+"\"", macro.code, None,
								  readonly=not macro.container.macrosEditable, lexer=QsciLexerPython())
		if res:
			if macro.container.macrosEditable:
				macro.code = res
				macro.container.storeMacro(macro)
			hash = hashlib.sha256(res.encode('utf-8')).digest()
			configs.updateMru("TrustedMacroHashes", hash, 255)



class SelectionHeuristicsConfigWidget(QWidget):
	HELPER_ROLE = QtCore.Qt.UserRole + 100

	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		self.listView = QListWidget()
		self.infoBox = QTextEdit()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.listView)
		windowLayout.addWidget(self.infoBox)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.listView.itemChanged.connect(self.itemChanged)
		self.listView.currentItemChanged.connect(self.currentItemChanged)
		self.listView.itemDoubleClicked.connect(self.itemDoubleClicked)
		self.listView.customContextMenuRequested.connect(self.customContextMenuRequested)
		self.listView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

		from pre_workbench.controls.hexview_selheur import SelectionHelpers
		self._updateList()
		SelectionHelpers.updated.connect(self._updateList)

	def _updateList(self):
		from pre_workbench.controls.hexview_selheur import SelectionHelpers
		self.listView.clear()
		for helper, meta in SelectionHelpers.types:
			item = QListWidgetItem(helper.__name__ )
			item.setData(self.HELPER_ROLE, helper)
			item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
			item.setCheckState(QtCore.Qt.Checked if configs.getValue(f'SelHeur.{helper.__name__}.enabled', meta.get("defaultEnabled", False)) else QtCore.Qt.Unchecked)
			item.setIcon(filledColorIcon(configs.getValue(f'SelHeur.{helper.__name__}.color', meta.get("color", "#000000")), 16))
			self.listView.addItem(item)

	def currentItemChanged(self, current, previous):
		self.infoBox.setText(inspect.cleandoc(current.data(self.HELPER_ROLE).__doc__) if current is not None else "")

	def itemChanged(self, item):
		configs.setValue(f'SelHeur.{item.data(self.HELPER_ROLE).__name__}.enabled', item.checkState() == QtCore.Qt.Checked)

	def itemDoubleClicked(self, item):
		helper = item.data(self.HELPER_ROLE)
		if not hasattr(helper, "options"): return
		def ok(values):
			configs.setValue(f"SelHeur.{helper.__name__}.options", values)
		showSettingsDlg(helper.options, configs.getValue(f"SelHeur.{helper.__name__}.options", {}), f"Preferences for {helper.__name__}", self, ok)

	def customContextMenuRequested(self, point):
		item = self.listView.itemAt(point)
		ctx = QMenu("Context menu", self)
		if item:
			if hasattr(item.data(self.HELPER_ROLE), "options"):
				ctx.addAction("Preferences", lambda: self.itemDoubleClicked(item))
			else:
				ctx.addAction("Preferences").setEnabled(False)
			ctx.addSeparator()
		ctx.addAction("Enable All", lambda: self.setAllChecked(True))
		ctx.addAction("Disable All", lambda: self.setAllChecked(False))
		ctx.exec(self.listView.viewport().mapToGlobal(point))

	def setAllChecked(self, checked):
		for i in range(self.listView.count()):
			self.listView.item(i).setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)


class RpcDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		pass


class BinwalkDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.selBytes = None

	def _initUI(self):
		toolbar = QToolBar()
		toolbar.addAction("Run", self._runBinwalk)
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(3)
		self.treeView.setColumnWidth(1, 300)
		self.treeView.headerItem().setText(0, "Name")
		self.treeView.headerItem().setText(1, "Offset")
		self.treeView.headerItem().setText(2, "Description")
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(toolbar)
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def on_select_bytes(self, selBytes):
		self.selBytes = selBytes

	def _runBinwalk(self):
		self.treeView.clear()
		if not self.selBytes: return
		import binwalk
		result = binwalk.scan(self.selBytes.decode('latin1'), string=True, signature=True)
		for module in result:
			root = QTreeWidgetItem(self.treeView)
			root.setText(0, module.name)
			for result in module.results:
				x = QTreeWidgetItem(root)
				x.setText(0, result.file.name)
				x.setText(1, "0x%.8X"%result.offset)
				x.setText(2, result.description)


class ExtToolDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.selBytes = None

	def _initUI(self):
		toolbar = QToolBar()
		toolbar.addAction("Run", self._runTool)
		self.cmdLineEdit = QComboBox(editable=True, minimumWidth=200)
		self._updateMru()
		toolbar.addWidget(self.cmdLineEdit)
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(1)
		self.treeView.setColumnWidth(1, 300)
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(toolbar)
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _updateMru(self):
		self.cmdLineEdit.clear()
		self.cmdLineEdit.addItems(configs.getValue("ExtToolMru", []))

	def on_select_bytes(self, selBytes):
		self.selBytes = selBytes

	def _runTool(self):
		commandLine = self.cmdLineEdit.currentText()
		configs.updateMru("ExtToolMru", commandLine, 10)
		self._updateMru()
		self.treeView.clear()
		if not self.selBytes: return
		with tempfile.NamedTemporaryFile() as f:
			f.write(self.selBytes)
			f.flush()
			args = shlex.split(commandLine)
			args = [arg.format(f.name) for arg in args]
			result = runProcessWithDlg("External command", "Running external command: " + args[0], self,
									   args=args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
			for line in result['stdout'].decode('latin1').split('\n'):
				root = QTreeWidgetItem(self.treeView)
				root.setText(0, line)



class SearchDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.hexview = None

	def _initUI(self):
		toolbar = QToolBar()
		toolbar.addAction("Find", self._runTool)
		self.cmdLineEdit = QComboBox(editable=True, minimumWidth=200)
		self._updateMru()
		toolbar.addWidget(self.cmdLineEdit)
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(2)
		self.treeView.setColumnWidth(0, 300)
		self.treeView.headerItem().setText(0, "Result")
		self.treeView.headerItem().setText(1, "Offset")
		self.treeView.itemClicked.connect(self._itemClicked)
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(toolbar)
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _updateMru(self):
		self.cmdLineEdit.clear()
		self.cmdLineEdit.addItems(configs.getValue("FindMru", []))

	def on_meta_updated(self, event_id, sender):
		if event_id != "hexview_range" or sender is None: return
		self.hexview = sender

	def _runTool(self):
		findStr = self.cmdLineEdit.currentText()
		configs.updateMru("FindMru", findStr, 10)
		self._updateMru()
		self.treeView.clear()
		if not self.hexview: return
		pattern = re.compile(findStr.encode('latin1'))
		for i,buf in enumerate(self.hexview.buffers):
			root = None
			for match in pattern.finditer(buf.buffer):
				if not root:
					root = QTreeWidgetItem(self.treeView)
					root.setText(0, "Buffer %d: %r" % (i, buf.metadata))
					root.setExpanded(True)
				x = QTreeWidgetItem(root)
				x.setText(0, match.group(0).decode('latin1'))
				x.setText(1, str(match.start()))
				x.setData(0, QtCore.Qt.UserRole, Range(match.start(), match.end(), buffer_idx=i))

	def _itemClicked(self, item):
		range = item.data(0, QtCore.Qt.UserRole)
		if range:
			self.hexview.selectRange(range, True)




class LogWidget(QWidget):
	def __init__(self, logger_name = ""):
		super().__init__()
		self._initUI()
		self.logger = logging.getLogger(logger_name)
		self.handler = ConsoleWindowLogHandler()
		self.handler.sigLog.connect(self.logEvent)

	def _initUI(self):
		self.textBox = QTextEdit()
		self.textBox.setFont(getMonospaceFont())
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.textBox)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def showEvent(self, QShowEvent):
		self.logger.addHandler(self.handler)

	def hideEvent(self, QHideEvent):
		try:
			self.logger.removeHandler(self.handler)
		except:
			pass #sometimes it is not connected, probably hideEvent is called multiple times

	def logEvent(self, level, message):
		if level in ["ERROR", "WARNING"]:
			self.textBox.setTextColor(QColor("red"))
		elif level == "INFO":
			self.textBox.setTextColor(QColor("blue"))
		else:
			self.textBox.setTextColor(QColor("black"))

		self.textBox.append(message)

