import sys
from PyQt5.QtWidgets import QApplication, QFileSystemModel, QTreeView, QWidget, QVBoxLayout
from PyQt5.QtGui import QIcon

class FileBrowserWidget(QWidget):

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

        self.tree.setWindowTitle("Dir View")
        self.tree.resize(640, 480)

        windowLayout = QVBoxLayout()
        windowLayout.addWidget(self.tree)
        windowLayout.setContentsMargins(0,0,0,0)
        self.setLayout(windowLayout)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileBrowserWidget()
    ex.show()
    sys.exit(app.exec_())
