
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
import inspect
import logging
import os
import weakref

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices, QColor, QFont
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView, QMenu, \
	QAction, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit

from pre_workbench import configs, guihelper
from pre_workbench.algo.range import Range
from pre_workbench.configs import getIcon
from pre_workbench.errorhandler import ConsoleWindowLogHandler
from pre_workbench.genericwidgets import filledColorIcon
from pre_workbench.guihelper import navigate, getMonospaceFont
from pre_workbench.rangetree import RangeTreeWidget
from pre_workbench.structinfo.exceptions import parse_exception
from pre_workbench.structinfo.parsecontext import AnnotatingParseContext
from pre_workbench.windows.content.textfile import SimplePythonEditor
from pre_workbench.typeeditor import JsonView
from pre_workbench.typeregistry import WindowTypes
from pre_workbench.util import PerfTimer, truncate_str


class FileBrowserWidget(QWidget):
	on_open = pyqtSignal(str)
	def __init__(self, rootFolder):
		super().__init__()
		self.initUI()
		self.setRoot(rootFolder)

	def initUI(self):
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
				ctx.addAction("Open in file manager", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(selectedFile)))
			else:
				for wndTyp, meta in WindowTypes.types:
					text = 'Open with '+meta.get('displayName', meta['name'])
					ctx.addAction(QAction(text, self, statusTip=text, icon=getIcon(meta.get('icon', 'document.png')),
											   triggered=lambda dummy, meta=meta: navigate("WINDOW", "Type="+meta['name'], "FileName="+selectedFile)))
				ctx.addSeparator()
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
		self.initUI()

	def initUI(self):
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
		self.initUI()

		self._updateContent()
		guihelper.CurrentProject.formatInfoContainer.updated.connect(self._updateContent)

	def _updateContent(self):
		try:
			self.tree.set([(k,v.serialize()) for k,v in guihelper.CurrentProject.formatInfoContainer.definitions.items()])
		except:
			logging.exception("failed to load StructInfoTree")

	def initUI(self):
		self.tree = JsonView(schema="format_info.tes", rootTypeDefinition="FormatInfoFile")
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.tree)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)


class StructInfoCodeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()
		self._updateContent()
		guihelper.CurrentProject.formatInfoContainer.updated.connect(self._updateContent)
		self.editor.ctrlEnterPressed.connect(self._applyContent)

	def _updateContent(self):
		self.editor.setText(guihelper.CurrentProject.formatInfoContainer.to_text())

	def _applyContent(self):
		guihelper.CurrentProject.formatInfoContainer.load_from_string(self.editor.text())
		guihelper.CurrentProject.formatInfoContainer.write_file(None)

	def initUI(self):
		self.editor = SimplePythonEditor()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.editor)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.editor.show()


class RangeTreeDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()
		#self.lastBuffer = lambda : None # dead weakref
		self.lastHexView = lambda : None   # dead weakref
		self.fiTreeWidget.formatInfoContainer = guihelper.CurrentProject.formatInfoContainer

	def initUI(self):
		self.fiTreeWidget = RangeTreeWidget()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.fiTreeWidget)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.fiTreeWidget.show()
		self.fiTreeWidget.currentItemChanged.connect(self._fiTreeItemSelected)

	def _fiTreeItemSelected(self, item, previous):
		if item is None: return
		range = item.data(0, Range.RangeRole)
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




class DataInspectorWidget(QWidget):
	defaultdef = """
	DEFAULT union (ignore_errors=true, endianness=">"){
		uint8 UINT8
		int8 INT8
		uint8_bin UINT8(show="{0:08b}")
		BE union (endianness=">"){
			uint16 UINT16
			uint32 UINT32
			int16_be INT16
			int32_be INT32
			float FLOAT
			double DOUBLE
		}
		LE union (endianness="<"){
			uint16 UINT16
			uint32 UINT32
			int16 INT16
			int32 INT32
			float FLOAT
			double DOUBLE
		}
		ipv4 IPv4
		ether ETHER
	}
	"""
	def __init__(self):
		super().__init__()
		self.selbytes = None
		self.initUI()
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
			try:
				fi_tree = parse_context.parse()
			except parse_exception as ex:
				logging.exception("Failed to apply format info")
				logging.getLogger("DataSource").error("Failed to apply format info: "+str(ex))
			self.fiTreeWidget.updateTree([fi_tree])

	def initUI(self):
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
		self.initUI()

	def initUI(self):
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
			for d in sender.buffers[0].matchRanges(overlaps=sender.selRange()):
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


class SelectionHeuristicsConfigWidget(QWidget):
	HELPER_ROLE = QtCore.Qt.UserRole + 100

	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		self.listView = QListWidget()
		self.infoBox = QTextEdit()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.listView)
		windowLayout.addWidget(self.infoBox)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.listView.itemChanged.connect(self.itemChanged)
		self.listView.currentItemChanged.connect(self.currentItemChanged)

		from pre_workbench.hexview_selheur import SelectionHelpers
		for helper, meta in SelectionHelpers.types:
			item = QListWidgetItem(helper.__name__ )
			item.setData(self.HELPER_ROLE, helper)
			item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
			item.setCheckState(QtCore.Qt.Checked if configs.getValue("SelHeur."+helper.__name__+".enabled", meta.get("defaultEnabled",False)) else QtCore.Qt.Unchecked)
			item.setIcon(filledColorIcon(configs.getValue("SelHeur."+helper.__name__+".color", meta.get("color","#000000")), 16))
			self.listView.addItem(item)

	def currentItemChanged(self, current, previous):
		self.infoBox.setText(inspect.cleandoc(current.data(self.HELPER_ROLE).__doc__) if current is not None else "")

	def itemChanged(self, item):
		configs.setValue("SelHeur." + item.data(self.HELPER_ROLE).__name__ + ".enabled", item.checkState() == QtCore.Qt.Checked)


class RpcDockWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		pass


class LogWidget(QWidget):
	def __init__(self, logger_name = ""):
		super().__init__()
		self.initUI()
		self.logger = logging.getLogger(logger_name)
		self.handler = ConsoleWindowLogHandler()
		self.handler.sigLog.connect(self.logEvent)

	def initUI(self):
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

