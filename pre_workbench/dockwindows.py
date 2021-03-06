
# PRE Workbench
# Copyright (C) 2019 Max Weller
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
import os
import traceback

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView, QFileDialog, QMenu, \
	QAction, QListWidget, QListWidgetItem, QTableWidget, QTreeWidget, QMessageBox

import configs
import structinfo
from pre_workbench.objects import ByteBuffer, Range
from pre_workbench.guihelper import navigate, GlobalEvents
from pre_workbench.typeregistry import WindowTypes
from pre_workbench.rangetree import RangeTreeWidget


class FileBrowserWidget(QWidget):
	on_open = pyqtSignal(str)
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		self.model = QFileSystemModel()
		self.rootFolder = ''
		self.model.setRootPath(self.rootFolder)
		self.tree = QTreeView()
		self.tree.setModel(self.model)

		self.tree.setAnimated(False)
		self.tree.setIndentation(20)
		self.tree.setSortingEnabled(True)
		self.tree.sortByColumn(0, 0)
		self.tree.setColumnWidth(0, 200)
		self.tree.setDragEnabled(True)

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
			if not file.isDir():
				for wndTyp, meta in WindowTypes.types:
					text = 'Open with '+meta.get('displayName', meta['name'])
					print(wndTyp, meta)
					ctx.addAction(QAction(text, self, statusTip=text,
											   triggered=lambda dummy, meta=meta: navigate("WINDOW", "Type="+meta['name'], "FileName="+selectedFile)))
				ctx.addSeparator()

		ctx.addAction("Set root folder ...", lambda: self.selectRootFolder(preselect=selectedFolder))
		ctx.exec(self.tree.viewport().mapToGlobal(point))

	def selectRootFolder(self, preselect=None):
		if preselect == None: preselect = self.rootFolder
		dir = QFileDialog.getExistingDirectory(self,"Set root folder", preselect)
		if dir != None:
			self.setRoot(dir)

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
			return { "sel": info.absoluteFilePath(), "root": self.rootFolder }

	def restoreState(self, state):
		try:
			self.setRoot(state["root"])
		except:
			pass
		try:
			idx = self.model.index(state["sel"])
			if idx.isValid():
				self.tree.expand(idx)
				self.tree.setCurrentIndex(idx)
				self.tree.scrollTo(idx, QAbstractItemView.PositionAtCenter)
		except:
			pass


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
		navigate("WINDOW-ID","Id="+windowId)


	def updateWindowList(self, wndList):
		print("MdiWindowListWidget.updateWindowList", len(wndList))
		self.list.clear()
		for wnd in wndList:
			wid = wnd.widget()
			text = wnd.windowTitle() + "|" + type(wid).__name__ + "|" + wid.objectName()
			listitem = QListWidgetItem(text)
			listitem.setData(QtCore.Qt.UserRole, wid.objectName())
			self.list.addItem(listitem)


	def onCustomContextMenuRequested(self, point):
		item = self.list.itemAt(point)
		ctx = QMenu("Context menu", self)
		if item is not None:
			ctx.addAction("Close window", lambda: self.closeWindow(item))

		ctx.addAction("New window", lambda: self.newWindow())
		ctx.exec(self.list.viewport().mapToGlobal(point))


class StructInfoTreeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		pass

class StructInfoCodeWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		pass

class DataInspectorWidget(QWidget):
	defaultdef = """
	DEFAULT union {
		uint8_be UINT8(endianness=">")
		uint16_be UINT16(endianness=">")
		uint32_be UINT32(endianness=">")
		int8_be INT8(endianness=">")
		int16_be INT16(endianness=">")
		int32_be INT32(endianness=">")
		ipv4 IPv4
		ether ETHER
		float FLOAT
		double DOUBLE
	}
	"""
	def __init__(self):
		super().__init__()
		self.initUI()

	def showEvent(self, QShowEvent):
		GlobalEvents.on_select_bytes.connect(self.on_select_bytes)

	def hideEvent(self, QHideEvent):
		GlobalEvents.on_select_bytes.disconnect(self.on_select_bytes)

	def on_select_bytes(self, buffer:ByteBuffer, range:Range):
		parse_context = structinfo.AnnotatingParseContext(self.fiTreeWidget.formatInfoContainer, buffer.getBytes(range.start, range.length()))
		try:
			fi_tree = parse_context.parse()
		except structinfo.parse_exception as ex:
			QMessageBox.warning(self, "Parse error", str(ex))
			traceback.print_exc()
			fi_tree = ex.partial_result
		self.fiTreeWidget.updateTree(fi_tree)

	def initUI(self):
		self.fiTreeWidget = RangeTreeWidget()
		windowLayout = QVBoxLayout()
		windowLayout.addWidget(self.fiTreeWidget)
		windowLayout.setContentsMargins(0,0,0,0)
		self.setLayout(windowLayout)
		self.loadFormatInfo()

	def loadFormatInfo(self):
		#definition = configs.getValue("DataInspectorDef", DataInspectorWidget.defaultdef)
		filespec = os.path.join(configs.dirs.user_config_dir, "data_inspector.txt")
		if not os.path.isfile(filespec):
			with open(filespec,"w") as f:
				f.write(DataInspectorWidget.defaultdef)

		#self.fiTreeWidget.loadFormatInfo(load_from_string=definition)
		self.fiTreeWidget.loadFormatInfo(load_from_file=filespec)

