from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView, QFileDialog, QMenu


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
		if index.isValid():
			file = self.model.fileInfo(index)
			selectedFile = file.absoluteFilePath()
			selectedFolder = selectedFile if file.isDir() else file.absolutePath()

		ctx = QMenu("Context menu", self)
		ctx.addAction("Set root folder ...", lambda: self.selectRootFolder(preselect=selectedFolder))
		ctx.exec(self.mapToGlobal(point))

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
				self.on_open.emit(file.absoluteFilePath())

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


