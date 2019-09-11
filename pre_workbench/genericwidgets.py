from PyQt5 import Qt
from PyQt5.QtCore import pyqtSignal, QStringListModel, pyqtSlot
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QFrame, QWidget, QVBoxLayout, \
	QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QDialog, \
	QDialogButtonBox, QCompleter, QHeaderView, QTreeWidgetItem, QTreeWidget, QInputDialog


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
			#if idx == -1: raise Exception("invalid select value: "+value)
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
			self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Maximum)
		else:
			self.body.show()
			self.setSizePolicy(self.body.sizePolicy())



def printsizepolicy(pol):
	print("controlType", pol.controlType())
	print("expandingDirections", pol.expandingDirections())
	print("horizontalPolicy", pol.horizontalPolicy())
	print("horizontalStretch", pol.horizontalStretch())
	print("verticalPolicy", pol.verticalPolicy())
	print("verticalStretch", pol.verticalStretch())




# SOURCE: https://github.com/ashwin/json-viewer/blob/master/json_viewer.py

# GUI viewer to view JSON data as tree.
# Ubuntu packages needed:
# python3-pyqt5
class TextToTreeItem:
	def __init__(self):
		self.text_list = []
		self.titem_list = []

	def append(self, text_list, titem):
		for text in text_list:
			self.text_list.append(text)
			self.titem_list.append(titem)

	# Return model indices that match string
	def find(self, find_str):

		titem_list = []
		for i, s in enumerate(self.text_list):
			if find_str in s:
				titem_list.append(self.titem_list[i])

		return titem_list


class JsonView(QTreeWidget):
	def __init__(self, jdata=None):
		super(JsonView, self).__init__()

		self.find_box = None
		self.tree_widget = None
		self.text_to_titem = TextToTreeItem()
		self.find_str = ""
		self.found_titem_list = []
		self.found_idx = 0

		self.setHeaderLabels(["Key", "Value"])
		self.header().setSectionResizeMode(QHeaderView.Stretch)

		self.setContents(jdata)

	def setContents(self, jdata):
		self.clear()
		self.contents = jdata
		if jdata != None:
			root_item = QTreeWidgetItem(["Root"])
			self.recurse_jdata(jdata, root_item)
			self.addTopLevelItem(root_item)
			root_item.setExpanded(True)


	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == Qt.Key_F and event.modifiers() == Qt.CTRL:
			str = QInputDialog.getText(self, "Find", "Find string:", text=self.find_str)
			if str is not None:
				self.find_next(str)
		if event.key() == Qt.Key_F3:
			self.find_next(self.find_str)
		if event.key() == Qt.Key_F5:
			self.setContents(self.contents)

	def find_next(self, find_str):
		# Very common for use to click Find on empty string
		if find_str == "":
			return

		# New search string
		if find_str != self.find_str:
			self.find_str = find_str
			self.found_titem_list = self.text_to_titem.find(self.find_str)
			self.found_idx = 0
		else:
			item_num = len(self.found_titem_list)
			self.found_idx = (self.found_idx + 1) % item_num

		self.tree_widget.setCurrentItem(self.found_titem_list[self.found_idx])


	def recurse_jdata(self, jdata, tree_widget):
		if isinstance(jdata, dict):
			for key, val in jdata.items():
				self.tree_add_row(key, val, tree_widget)
		elif isinstance(jdata, list):
			for i, val in enumerate(jdata):
				key = str(i)
				self.tree_add_row(key, val, tree_widget)
		else:
			raise TypeError("jdata must be list or dict")

	def tree_add_row(self, key, val, tree_widget):
		text_list = []

		if isinstance(val, dict) or isinstance(val, list):
			text_list.append(key)
			row_item = QTreeWidgetItem([key])
			self.recurse_jdata(val, row_item)
		else:
			text_list.append(key)
			text_list.append(str(val))
			row_item = QTreeWidgetItem([key, str(val)])

		tree_widget.addChild(row_item)
		self.text_to_titem.append(text_list, row_item)

