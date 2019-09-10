
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
	QFileDialog, QTabWidget, QFrame, QWidget, QToolBar, QVBoxLayout, \
	QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QDialog, \
	QDialogButtonBox, QCompleter
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject, QStringListModel)

def showSettingsDlg(definition, values=None):
	if values == None: values = {}
	dlg = QDialog()
	dlg.setLayout(QVBoxLayout())
	sg = SettingsGroup(definition, values)
	dlg.layout().addWidget(sg)
	btn = QDialogButtonBox()
	btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
	btn.clicked.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)
	if dlg.exec() == QDialog.Rejected: return None
	return values


class SettingsGroup(QFrame):
	item_changed = pyqtSignal(str, str)

	def __init__(self, definition, values):
		super().__init__()
		self.layout = QFormLayout()
		self.values = values
		self.setLayout(self.layout)
		self.setFields(definition)
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
	
	def setFields(self, definition):
		for i in reversed(range(self.layout.count())): 
			self.layout.itemAt(i).widget().deleteLater()
		for fieldId, title, fieldtype, params in definition:
			empty=""
			if fieldtype == "text":
				field = QLineEdit()
				field.textChanged.connect(self.textChanged)
				if "autocomplete" in params:
					field.setCompleter(QCompleter(QStringListModel(list(params["autocomplete"]), field), field))

			elif fieldtype == "select":
				field = QComboBox()
				for value, text in params["options"]:
					field.addItem(text, value)
				field.activated.connect(self.selectChanged)
				empty = params["options"][0][0]
			elif fieldtype == "check":
				field = QCheckBox()
				field.stateChanged.connect(self.checkChanged)
				empty = "False"
			field.setObjectName(fieldId)
			self.layout.addRow(title, field)
			if fieldId in self.values:
				self.updateField(fieldId)
			elif "default" in params:
				self.values[fieldId] = params["default"]
				self.updateField(fieldId)
			else:
				self.values[fieldId] = empty

	@pyqtSlot(str)
	def textChanged(self, newText):
		self.onFieldChanged(newText)
	
	@pyqtSlot(int)
	def selectChanged(self, newIndex):
		self.onFieldChanged(self.sender().itemData(newIndex))
	
	@pyqtSlot(int)
	def checkChanged(self, newState):
		self.onFieldChanged("True" if newState == Qt.Checked else "False")

	def onFieldChanged(self, value):
		fieldId = self.sender().objectName()
		self.values[fieldId] = value
		self.item_changed.emit(fieldId, value)
	
	def updateField(self, fieldId):
		value = str(self.values[fieldId])
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
			self.values[k] = v
			self.updateField(k)

class ExpandWidget(QWidget):
	def __init__(self, title, body, collapsed=False):
		super().__init__()
		layout = QVBoxLayout()
		layout.setContentsMargins(0,0,0,0)

		self.header = QPushButton()
		self.header.setText(title)
		#self.header.setStyleSheet("border: 1px solid #000000; background: #898983");
		#self.header.setGeometry(QRect(0, 0, 330, 25))
		self.header.clicked.connect(self.onHeaderClick)
		layout.addWidget(self.header)

		self.body = body
		layout.addWidget(self.body)
		self.setSizePolicy(self.body.sizePolicy())

		self.setLayout(layout)
		self.setCollapsed(collapsed)
		#self.setStyleSheet("background-color:#ffeeaa;border: 2px solid black;")
		#pal = self.palette()
		#pal.setColor(QPalette.Window, Qt.blue)
		#self.setPalette(pal)

	def onHeaderClick(self):
		self.setCollapsed(not self.collapsed)
	def setCollapsed(self, value):
		self.collapsed = value
		if self.collapsed:
			self.body.hide()
		else:
			self.body.show()


def printsizepolicy(pol):
	print("controlType", pol.controlType())
	print("expandingDirections", pol.expandingDirections())
	print("horizontalPolicy", pol.horizontalPolicy())
	print("horizontalStretch", pol.horizontalStretch())
	print("verticalPolicy", pol.verticalPolicy())
	print("verticalStretch", pol.verticalStretch())
	