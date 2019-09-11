from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout, QAbstractItemView


class FileBrowserWidget(QWidget):
    on_open = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.model = QFileSystemModel()
        self.model.setRootPath('')
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

        windowLayout = QVBoxLayout()
        windowLayout.addWidget(self.tree)
        windowLayout.setContentsMargins(0,0,0,0)
        self.setLayout(windowLayout)

    def onDblClick(self, index):
        if index.isValid():
            file = self.model.fileInfo(index)
            self.on_open.emit(file.absoluteFilePath())

    def saveState(self):
        if self.tree.currentIndex().isValid():
            info = self.model.fileInfo(self.tree.currentIndex())
            return { "sel": info.absoluteFilePath() }

    def restoreState(self, state):
        try:
            idx = self.model.index(state["sel"])
            if idx.isValid():
                self.tree.expand(idx)
                self.tree.setCurrentIndex(idx)
                self.tree.scrollTo(idx, QAbstractItemView.PositionAtCenter)
        except:
            pass


