
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
	QFileDialog, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout,\
	QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject)


class SettingsGroup(QWidget):
	item_changed = pyqtSignal(str, str)

	def __init__(self, definition):
		super().__init__()
		self.layout = QFormLayout()
		self.setLayout(self.layout)
		self.setFields(definition)
	
	def setFields(self, definition):
		for i in reversed(range(self.layout.count())): 
			self.layout.itemAt(i).widget().deleteLater()
		for fieldId, title, fieldtype, params in definition:
			if fieldtype == "text":
				field = QLineEdit()
				field.textChanged.connect(self.textChanged)
			elif fieldtype == "select":
				field = QComboBox()
				for value, text in params["options"]:
					field.addItem(text, value)
				field.activated.connect(self.selectChanged)
			elif fieldtype == "check":
				field = QCheckBox()
				field.stateChanged.connect(self.checkChanged)
			field.setObjectName(fieldId)
			self.layout.addRow(title, field)

	@pyqtSlot(str)
	def textChanged(self, newText):
		fieldId = self.sender().objectName()
		self.onChange(fieldId, newText)
	
	@pyqtSlot(int)
	def selectChanged(self, newIndex):
		fieldId = self.sender().objectName()
		self.onChange(fieldId, self.sender().itemData(newIndex))
	
	@pyqtSlot(int)
	def checkChanged(self, newState):
		fieldId = self.sender().objectName()
		self.onChange(fieldId, "True" if newState == Qt.Checked else "False")

	def onChange(self, fieldId, value):
		self.item_changed.emit(fieldId, value)
	
	def setValue(self, fieldId, value):
		value = str(value)
		field = self.findChild(QWidget, fieldId)
		if isinstance(field, QLineEdit):
			field.setText(value)
		elif isinstance(field, QComboBox):
			idx = field.findData(value)
			if idx == -1: raise Exception("invalid select value: "+value)
			field.setCurrentIndex(idx)
		elif isinstance(field, QCheckBox):
			if value == "True":
				field.setState(Qt.Checked)
			elif value == "False":
				field.setState(Qt.Unchecked)
			else:
				raise Exception("invalid check value: "+value)

	def setValues(self, values):
		for k, v in values.items():
			self.setValue(k, v)

class ExpandWidget(QWidget):
	def __init__(self, title, body):
		super().__init__()
		layout = QVBoxLayout()

		self.header = QPushButton()
		self.header.setText(title)
		self.header.setStyleSheet("border: 1px solid #000000; background: #898983");
		#self.header.setGeometry(QRect(0, 0, 330, 25))
		self.header.clicked.connect(self.onHeaderClick)
		layout.addWidget(self.header)

		self.body = body
		layout.addWidget(self.body)

		self.setLayout(layout)
		self.hidden = False

	def onHeaderClick(self):
		self.hidden = not self.hidden
		if self.hidden:
			self.body.hide()
		else:
			self.body.show()
