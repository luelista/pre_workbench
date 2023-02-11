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
from binascii import hexlify
from copy import deepcopy

import yaml
from PyQt5 import QtCore
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QColor, QKeySequence
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView, QMenu, \
	QAction, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit, QToolBar, QComboBox, QMessageBox, \
	QShortcut, QFileDialog, QDialog, QTextBrowser

import pre_workbench.app
from pre_workbench import configs
from pre_workbench.algo.range import Range
from pre_workbench.app import navigate
from pre_workbench.configs import getIcon, SettingsField
from pre_workbench.consts import MACRO_PROPERTIES_HELP_URL, SYNTAX_REFERENCE_URL
from pre_workbench.controls.genericwidgets import showSettingsDlg
from pre_workbench.errorhandler import ConsoleWindowLogHandler
from pre_workbench.guihelper import filledColorIcon, getMonospaceFont, runProcessWithDlg, APP, navigateBrowser, \
	setClipboardText
from pre_workbench.macros.macro import Macro
from pre_workbench.rangetree import RangeTreeWidget
from pre_workbench.structinfo.parsecontext import AnnotatingParseContext
from pre_workbench.typeeditor import JsonView
from pre_workbench.typeregistry import WindowTypes, DockWidgetTypes
from pre_workbench.util import PerfTimer, truncate_str
from pre_workbench.windows.content.textfile import ScintillaEdit
from pre_workbench.windows.dialogs.editmacro import EditMacroDialog


@DockWidgetTypes.register(title="Project Files", icon="folder-tree.png", dock="Left", showFirstRun=True)
class FileBrowserWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		rootFolder = pre_workbench.app.CurrentProject.projectFolder
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
				ctx.addAction("Open as Directory of Binary Files", lambda: navigate("WINDOW", "Type=ObjectWindow", "FileName=" + selectedFile,
																			   "dataSourceType=DirectoryOfBinFilesDataSource"))
				ctx.addSeparator()
				ctx.addAction("Open in File Manager", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(selectedFile)))
			else:
				ctx.addAction("Open as Data Source", lambda: navigate("WINDOW", "Type=ObjectWindow", "FileName=" + selectedFile,
																			   "dataSourceType=FileDataSource"))
				mnuOpenWith = ctx.addMenu('Open with ...')
				for wndTyp, meta in WindowTypes.types:
					text = meta.get('displayName', meta['name'])
					mnuOpenWith.addAction(QAction(text, self, statusTip=text, icon=getIcon(meta.get('icon', 'document.png')),
											   triggered=lambda dummy, meta=meta: navigate("WINDOW", "Type="+meta['name'], "FileName="+selectedFile)))
				ctx.addSeparator()
				ctx.addAction("Open in Default Application", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(selectedFile)))
			ctx.addAction("Copy Path", lambda: setClipboardText(self.model.rootPath()))
		else:
			ctx.addAction("Open in File Manager", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.model.rootPath())))
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
			sel = info.absoluteFilePath()
		else:
			sel = None
		return { "sel": sel, "root": self.rootFolder, "hs": self.tree.header().saveState() }

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



@DockWidgetTypes.register(title="Window List", icon="applications-stack.png", dock="Left")
class MdiWindowListWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		self.list = QListWidget()
		# TODO fix context menu
		#self.list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		#self.list.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
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

	def on_focused_dock_widget_changed(self, window):
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


@DockWidgetTypes.register(title="Grammar Definitions", icon="tree--pencil.png", showFirstRun=True)
class StructInfoCodeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.editor.ctrlEnterPressed.connect(self._applyContent)
		self.editor.modificationChanged.connect(self._modificationChanged)
		self._updateContent()
		pre_workbench.app.CurrentProject.formatInfoContainer.updated.connect(self._updateContent)

	def _updateContent(self):
		self.editor.setText(pre_workbench.app.CurrentProject.formatInfoContainer.to_text())
		self.editor.setModified(False)

	def _applyContent(self):
		pre_workbench.app.CurrentProject.formatInfoContainer.load_from_string(self.editor.text())
		pre_workbench.app.CurrentProject.formatInfoContainer.write_file(None)
		self.editor.setModified(False)

	def _modificationChanged(self, mod):
		self.toolbar.setVisible(mod)

	def _initUI(self):
		self.toolbar = QToolBar()
		self.toolbar.addAction("Apply Definitions", self._applyContent)
		self.toolbar.addAction("Syntax Reference", lambda: navigateBrowser(SYNTAX_REFERENCE_URL))
		self.editor = ScintillaEdit()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.editor)
		windowLayout.addWidget(self.toolbar)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.editor.show()


@DockWidgetTypes.register(title="Parse Result", icon="tree--arrow.png", showFirstRun=True)
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
		buf_idx = item.data(0, RangeTreeWidget.BufferIndexRole)
		hexView = self.lastHexView()
		if range is not None and hexView is not None:
			sel_range = Range(range.start, range.end, buffer_idx=buf_idx)
			hexView.selectRange(sel_range, scrollIntoView=True)

	def on_meta_updated(self, event_id, param):
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




@DockWidgetTypes.register(title="Data Inspector", icon="user-detective-gray.png", dock="Bottom", showFirstRun=True)
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
		self._loadDefinitionList()
		self.loadFormatInfo()
		self.fiTreeWidget.formatInfoContainer.updated.connect(self.parse)

	def saveState(self):
		return {"hs": self.fiTreeWidget.header().saveState()}
	def restoreState(self, data):
		if "hs" in data: self.fiTreeWidget.header().restoreState(data["hs"])

	def on_selected_bytes_updated(self, selbytes):#buffer:ByteBuffer, range:Range):
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
		self.definitionSelect = QComboBox()
		self.definitionSelect.setEditable(False)
		self.fiTreeWidget = RangeTreeWidget()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.definitionSelect)
		windowLayout.addWidget(self.fiTreeWidget)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _loadDefinitionList(self):
		self.definitionSelect.addItem("Data Inspector")

	def loadFormatInfo(self):
		#definition = configs.getValue("DataInspectorDef", DataInspectorWidget.defaultdef)
		filespec = os.path.join(configs.dirs.user_config_dir, "data_inspector.txt")
		if not os.path.isfile(filespec):
			with open(filespec,"w") as f:
				f.write(DataInspectorWidget.defaultdef)

		#self.fiTreeWidget.loadFormatInfo(load_from_string=definition)
		self.fiTreeWidget.loadFormatInfo(load_from_file=filespec)


@DockWidgetTypes.register(title="Selected Ranges", icon="bookmarks.png")
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

	def on_meta_updated(self, event_id, sender):
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


@DockWidgetTypes.register(title="Macros", icon="scripts.png", dock="Right", showFirstRun=False)
class MacroListDockWidget(QWidget):
	CONTAINER_ROLE = QtCore.Qt.UserRole + 100
	MACRO_NAME_ROLE = QtCore.Qt.UserRole + 101
	MACRO_ICONS = {
		'NONE': 'script.png',
		'BYTE_ARRAY': 'script-attribute.png',
		'BYTE_BUFFER': 'script-attribute-b.png',
		'BYTE_BUFFER_LIST': 'script-attribute-l.png',
		'DATA_SOURCE': 'script-attribute-d.png',
		'STRING': 'script-attribute-s.png',
		'SELECTION_HEURISTIC': 'script-attribute-h.png',
	}
	def __init__(self):
		super().__init__()
		self._initUI()
		self._loadList()

	def _initUI(self):
		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(1)
		self.treeView.setColumnWidth(1, 300)
		self.treeView.headerItem().setText(0, "Name")
		self.treeView.customContextMenuRequested.connect(self._customContextMenuRequested)
		self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.treeView.itemDoubleClicked.connect(self._onDblClick)
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.treeView)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _loadList(self):
		self.treeView.clear()
		for container_id, container in APP().macro_containers.items():
			root = QTreeWidgetItem(self.treeView, [container.containerTitle])
			root.setExpanded(True)
			root.setIcon(0, getIcon("box.png"))
			root.setData(0, MacroListDockWidget.CONTAINER_ROLE, container)
			self._loadMacros(root, container)

	def _loadMacros(self, root, container):
		macroList = container.getMacros()
		for macroItem in macroList:
			item = QTreeWidgetItem(root, [macroItem.name])
			item.setIcon(0, getIcon(MacroListDockWidget.MACRO_ICONS.get(macroItem.input_type, "script.png")))
			item.setData(0, MacroListDockWidget.CONTAINER_ROLE, container)
			item.setData(0, MacroListDockWidget.MACRO_NAME_ROLE, macroItem.name)

	def _customContextMenuRequested(self, point):
		item = self.treeView.itemAt(point)
		ctx = QMenu("Context menu", self)
		if item:
			container = item.data(0, MacroListDockWidget.CONTAINER_ROLE)
			macroname = item.data(0, MacroListDockWidget.MACRO_NAME_ROLE)
			if macroname:
				ctx.addAction("Execute", lambda: self.executeMacro(container.getMacro(macroname)))
				if container.macrosEditable:
					ctx.addAction("Edit", lambda: self.editMacro(container.getMacro(macroname)))
					ctx.addAction("Delete", lambda: self.deleteMacro(container, macroname))
				else:
					ctx.addAction("View code", lambda: self.editMacro(container.getMacro(macroname)))
				ctx.addSeparator()
				for target_container_id, target_container in APP().macro_containers.items():
					if target_container.macrosEditable and target_container != container:
						ctx.addAction("Copy to " + target_container.containerTitle, lambda trg=target_container: self.copyMacro(container.getMacro(macroname), trg))
				ctx.addAction("Export ...", lambda: self.exportMacro(container.getMacro(macroname)))
			else:
				if container.macrosEditable:
					ctx.addAction("Create macro ...", lambda: self.createMacro(container))
					ctx.addAction("Import ...", lambda: self.importMacro(container))
			ctx.exec(self.treeView.viewport().mapToGlobal(point))

	def deleteMacro(self, container, macroname):
		if QMessageBox.question(self, "Delete Macro", "Delete Macro \"" + macroname + "\"?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
			container.deleteMacro(macroname)
			self._loadList()

	def _onDblClick(self, item: QTreeWidgetItem, columnIdx: int):
		container = item.data(0, MacroListDockWidget.CONTAINER_ROLE)
		macroname = item.data(0, MacroListDockWidget.MACRO_NAME_ROLE)
		if macroname:
			self.executeMacro(container.getMacro(macroname))

	def executeMacro(self, macro):
		if macro.input_type == Macro.TYPE_NONE:
			macro.execute(None)
		else:
			QMessageBox.warning(self, "Not implemented", "Please call with input data of type: " + macro.input_type)

	def exportMacro(self, macro):
		fileName, _ = QFileDialog.getSaveFileName(self, "Export Macro", os.path.join(APP().project.projectFolder, macro.name + ".macro.yml"), "Macro (*.macro.yml)")
		if not fileName: return
		with open(fileName, "w") as f:
			yaml.dump({"name": macro.name, "input_type": macro.input_type, "output_type": macro.output_type, "options": macro.options, "metadata": macro.metadata, "code": macro.code},
						   f, explicit_start=True, sort_keys=False)

	def importMacro(self, container):
		fileName, _ = QFileDialog.getOpenFileName(self, "Import Macro",
												  APP().project.projectFolder,
												  "Macro (*.macro.yml);;All files (*.*)")
		if not fileName: return
		with open(fileName, "r") as f:
			x = yaml.safe_load(f)
			macro = Macro(container, x["name"], x["input_type"], x["output_type"], x["code"], x["options"], x["metadata"], None)
			self.editMacro(macro)

	MacroPreferencesDef = [
			SettingsField("name", "Name", "text", {}),
			SettingsField("input_type", "Macro/Input Type", "select", {"options": list(zip(Macro.TYPES, Macro.TYPES))}),
			SettingsField("output_type", "Output Type", "select", {"options": list(zip(Macro.TYPES, Macro.TYPES))}),
		]

	def editMacro(self, macro):
		dlg = EditMacroDialog(self, macro)
		if dlg.exec() == QDialog.Rejected: return
		if macro.container.macrosEditable:
			macro.container.storeMacro(macro)
		hash = hashlib.sha256(macro.code.encode('utf-8')).digest()
		configs.updateMru("TrustedMacroHashes", hash, 255)
		self._loadList()

	def createMacro(self, container):
		result = showSettingsDlg(MacroListDockWidget.MacroPreferencesDef, title="Create Macro ...", parent=self,
								  help_callback=lambda: navigateBrowser(MACRO_PROPERTIES_HELP_URL))
		if not result: return
		macro = Macro(container, result["name"], result["input_type"], result["output_type"], "", [], {}, None)
		container.storeMacro(macro)
		self.editMacro(macro)
		self._loadList()

	def copyMacro(self, macro, target_container):
		result = showSettingsDlg(MacroListDockWidget.MacroPreferencesDef,
								 {"name": macro.name, "input_type": macro.input_type, "output_type": macro.output_type},
								 title="Copy Macro ...", parent=self,
								  help_callback=lambda: navigateBrowser(MACRO_PROPERTIES_HELP_URL))
		if not result: return
		new_macro = Macro(target_container, result["name"], result["input_type"], result["output_type"], macro.code, deepcopy(macro.options), deepcopy(macro.metadata), None)
		target_container.storeMacro(new_macro)
		self._loadList()


@DockWidgetTypes.register(title="Selection Heuristics", icon="table-select-cells.png")
class SelectionHeuristicsConfigWidget(QWidget):
	HELPER_ROLE = QtCore.Qt.UserRole + 100

	def __init__(self):
		super().__init__()
		self._initUI()

	def _initUI(self):
		self.listView = QListWidget()
		self.infoBox = QTextBrowser()
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
		self.infoBox.setPlainText(inspect.cleandoc(current.data(self.HELPER_ROLE).__doc__) if current is not None else "")

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


@DockWidgetTypes.register(title="External Tools", icon="toolbox--arrow.png", dock="Bottom", showFirstRun=False)
class ExtToolDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.selBytes = None

	def _initUI(self):
		toolbar = QToolBar()
		toolbar.addAction("Run", self._runTool)
		self.cmdLineEdit = QComboBox(editable=True, minimumWidth=200)
		QShortcut(QKeySequence(QtCore.Qt.Key_Return), self.cmdLineEdit, activated=self._runTool, context=QtCore.Qt.WidgetWithChildrenShortcut)
		self._updateMru()
		toolbar.addWidget(self.cmdLineEdit)
		self.textBox = QTextEdit()
		self.textBox.setFont(getMonospaceFont())
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(toolbar)
		windowLayout.addWidget(self.textBox)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)

	def _updateMru(self):
		self.cmdLineEdit.clear()
		self.cmdLineEdit.addItems(configs.getValue("ExtToolMru", []))

	def on_selected_bytes_updated(self, selBytes):
		self.selBytes = selBytes

	def _runTool(self):
		commandLine = self.cmdLineEdit.currentText()
		configs.updateMru("ExtToolMru", commandLine, 10)
		self._updateMru()
		self.textBox.clear()
		if not self.selBytes: return
		f = tempfile.NamedTemporaryFile(delete=False)
		try:
			f.write(self.selBytes)
			f.close()
			args = commandLine.format('"' + f.name + '"')
			result = runProcessWithDlg("External command", "Running external command: " + args[0], self,
									   args=args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
			self.textBox.setText(result['stdout'].decode('latin1'))
			#for line in result['stdout'].decode('latin1').split('\n'):
			#	root = QTreeWidgetItem(self.treeView)
			#	root.setText(0, line)
		finally:
			os.remove(f.name)



@DockWidgetTypes.register(title="Search", icon="magnifier-left.png", dock="Bottom", showFirstRun=False)
class SearchDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self._initUI()
		self.hexview = None

	def _initUI(self):
		toolbar = QToolBar()
		self.cmdLineEdit = QComboBox(editable=True, minimumWidth=200)
		QShortcut(QKeySequence(QtCore.Qt.Key_Return), self.cmdLineEdit, activated=self._runTool, context=QtCore.Qt.WidgetWithChildrenShortcut)
		self._updateMru()
		toolbar.addWidget(self.cmdLineEdit)
		toolbar.addAction(getIcon("magnifier-left.png"), "Find", self._runTool)
		self.displayAsHexAction = QAction(getIcon("document-binary.png"), "Display Results as Hex String", self, triggered=self._runTool)
		self.displayAsHexAction.setCheckable(True)
		toolbar.addAction(self.displayAsHexAction)

		self.treeView = QTreeWidget()
		self.treeView.setColumnCount(2)
		self.treeView.setColumnWidth(0, 300)
		self.treeView.headerItem().setText(0, "Result")
		self.treeView.headerItem().setText(1, "Offset")
		self.treeView.currentItemChanged.connect(self._currentItemChanged)
		self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
				if self.displayAsHexAction.isChecked():
					x.setText(0, hexlify(match.group(0), b':').decode('latin1'))
				else:
					x.setText(0, match.group(0).decode('latin1'))
				x.setText(1, str(match.start()))
				x.setData(0, QtCore.Qt.UserRole, Range(match.start(), match.end(), buffer_idx=i))

	def _currentItemChanged(self, item, prevItem):
		if not item: return
		range = item.data(0, QtCore.Qt.UserRole)
		if not range: return
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

