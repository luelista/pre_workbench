import sys

from PyQt5.QtWidgets import QApplication

from qtcolorpicker import QtColorPicker

app = QApplication(sys.argv)
ex = QtColorPicker()
ex.show()
sys.exit(app.exec_())

