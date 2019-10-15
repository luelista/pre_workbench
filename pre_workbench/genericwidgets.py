
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

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, QStringListModel, pyqtSlot, QSize, QFileInfo, QTimer
from PyQt5.QtGui import QKeyEvent, QIcon, QDragEnterEvent, QDropEvent, QPixmap, QColor
from PyQt5.QtWidgets import QFrame, QWidget, QVBoxLayout, \
	QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QDialog, \
	QDialogButtonBox, QCompleter, QHeaderView, QTreeWidgetItem, QTreeWidget, QInputDialog, QSpinBox, QFileDialog, \
	QMessageBox, QAction, QLabel, QColorDialog

from .configs import getIcon
from .syshelper import get_current_rss
from .typeregistry import DataWidgetTypes


def showSettingsDlg(definition, values=None, title="Options", parent=None):
	if values == None: values = {}
	dlg = QDialog(parent)
	dlg.setWindowTitle(title)
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

class FileDropLineEdit(QLineEdit):
	def __init__(self, *__args):
		super().__init__(*__args)
		self.setAcceptDrops(True)

	def dragEnterEvent(self, e:QDragEnterEvent):
		if e.mimeData().hasText() or (e.mimeData().hasUrls() and e.mimeData().urls()[0].isLocalFile()):
			e.accept()
		else:
			e.ignore()
	def dropEvent(self, e:QDropEvent):
		if e.mimeData().hasUrls():
			self.setText(e.mimeData().urls()[0].toLocalFile())
			e.accept()
		elif e.mimeData().hasText():
			self.setText(e.mimeData().text())
			e.accept()

class ColorSelectLineEdit(QLineEdit):
	def __init__(self, *__args):
		super().__init__(*__args)
		self.colorSelectAction = QAction(getIcon("select.png"), "Select color", self)
		self.colorSelectAction.triggered.connect(self.selectColor)
		self.textChanged.connect(self.onTextChanged)
		self.addAction(self.colorSelectAction, QLineEdit.TrailingPosition)
	def selectColor(self):
		result, ok = QColorDialog.getColor(QColor(self.text()))
		if ok:
			self.setText(result.name())
	def onTextChanged(self, newText):
		self.colorSelectAction.setIcon(filledColorIcon(newText, 16))



def filledColorIcon(color, size):
	pix = QPixmap(size, size)
	pix.fill(QColor(color))
	return QIcon(pix)

class SettingsGroup(QFrame):
	item_changed = pyqtSignal(str, str)

	def __init__(self, definition, values):
		super().__init__()
		self.layout = QFormLayout()
		self.values = values
		self.setLayout(self.layout)
		self.setFields(definition)
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
		self.setStyleSheet("SettingsGroup{background:#ffeeaa}")
		self.layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

	def setFields(self, definition):
		for i in reversed(range(self.layout.count())):
			self.layout.itemAt(i).widget().deleteLater()
		for fieldId, title, fieldtype, params in definition:
			empty=""
			if fieldtype == "-":
				self.layout.addRow("  ",None)
				continue
			if fieldtype == "text":
				field = FileDropLineEdit()
				field.textChanged.connect(self.textChanged)
				if "autocomplete" in params:
					field.setCompleter(QCompleter(QStringListModel(list(params["autocomplete"]), field), field))
				if "fileselect" in params:
					act = QAction(getIcon("select.png"), "Select file", field)
					act.triggered.connect(lambda c,params=params, field=field:
										  self.selectFile(field, params["fileselect"],
														  params.get("caption","Select file"),
														  params.get("filter","All files (*.*)")))
					field.addAction(act, QLineEdit.TrailingPosition)
			elif fieldtype == "color":
				field = ColorSelectLineEdit()
				field.textChanged.connect(self.textChanged)
			elif fieldtype == "select":
				field = QComboBox()
				for value, text in params["options"]:
					field.addItem(text, value)
				field.activated.connect(self.selectChanged)
				empty = params["options"][0][0]
			elif fieldtype == "check":
				field = QCheckBox()
				field.stateChanged.connect(self.checkChanged)
				empty = False
			elif fieldtype == "number":
				field = QSpinBox()
				field.valueChanged.connect(self.spinChanged)
				if 'min' in params: field.setMinimum(params['min'])
				if 'max' in params: field.setMaximum(params['max'])
				empty = 0
			field.setObjectName(fieldId)
			self.layout.addRow(title, field)
			if fieldId in self.values:
				self.updateField(fieldId)
			elif "default" in params:
				self.values[fieldId] = params["default"]
				self.updateField(fieldId)
			else:
				self.values[fieldId] = empty

	def selectFile(self, field, mode, caption, filter):
		if mode == "open":
			r, _ = QFileDialog.getOpenFileName(self, caption, field.text(), filter)
		elif mode == "save":
			r, _ = QFileDialog.getSaveFileName(self, caption, field.text(), filter)
		elif mode == "dir":
			r, _ = QFileDialog.getExistingDirectory(self, caption, field.text())
		else:
			raise Exception("Invalid fileselect mode "+mode)
		if r:
			field.setText(r)

	@pyqtSlot(str)
	def textChanged(self, newText):
		self.onFieldChanged(newText)

	@pyqtSlot(int)
	def spinChanged(self, newValue):
		self.onFieldChanged(newValue)

	@pyqtSlot(int)
	def selectChanged(self, newIndex):
		self.onFieldChanged(self.sender().itemData(newIndex))

	@pyqtSlot(int)
	def checkChanged(self, newState):
		self.onFieldChanged(True if newState == QtCore.Qt.Checked else False)

	def onFieldChanged(self, value):
		fieldId = self.sender().objectName()
		self.values[fieldId] = value
		self.item_changed.emit(fieldId, str(value))

	def updateField(self, fieldId):
		value = self.values[fieldId]
		field = self.findChild(QWidget, fieldId)
		if isinstance(field, QLineEdit):
			field.setText(value)
		elif isinstance(field, QSpinBox):
			field.setValue(value)
		elif isinstance(field, QComboBox):
			idx = field.findData(value)
			#if idx == -1: raise Exception("invalid select value: "+value)
			field.setCurrentIndex(idx)
		elif isinstance(field, QCheckBox):
			if value == True:
				field.setCheckState(QtCore.Qt.Checked)
			elif value == False:
				field.setCheckState(QtCore.Qt.Unchecked)
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

	def append(self, text, titem):
		self.text_list.append(text)
		self.titem_list.append(titem)

	# Return model indices that match string
	def find(self, find_str):

		titem_list = []
		for i, s in enumerate(self.text_list):
			if find_str in s:
				titem_list.append(self.titem_list[i])

		return titem_list


@DataWidgetTypes.register(handles=[dict,list])
class JsonView(QTreeWidget):
	def __init__(self, jdata=None):
		super(JsonView, self).__init__()

		self.find_box = None
		self.tree_widget = None
		self.text_to_titem = TextToTreeItem()
		self.find_str = ""
		self.found_titem_list = []
		self.found_idx = 0

		self.setHeaderLabels(["Key", "Type", "Value"])
		self.setColumnWidth(0, 200)
		self.setColumnWidth(1, 100)
		self.setColumnWidth(2, 400)

		self.setContents(jdata)

	def sizeHint(self):
		return QSize(620,600)

	def setContents(self, jdata):
		self.clear()
		self.contents = jdata
		if jdata != None:
			self.tree_add_row("Root", jdata, self).setExpanded(True)
			#self.addTopLevelItem(root_item)
			#root_item.setExpanded(True)

	def tree_add_row(self, key, val, parent):
		me = QTreeWidgetItem(parent)
		me.setData(0, QtCore.Qt.UserRole, key)
		me.setText(0, key)
		me.setData(1, QtCore.Qt.UserRole, type(val))
		me.setText(1, type(val).__name__)
		me.setData(2, QtCore.Qt.UserRole, val)

		if isinstance(val, dict):
			for key, cc in val.items():
				self.tree_add_row(key, cc, me)
		elif isinstance(val, list):
			for i, cc in enumerate(val):
				key = str(i)
				self.tree_add_row(key, cc, me)
		else:
			me.setText(2, str(val))
			self.text_to_titem.append(str(val), me)

		self.text_to_titem.append(key, me)
		return me

	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == QtCore.Qt.Key_F and event.modifiers() == QtCore.Qt.ControlModifier:
			str = QInputDialog.getText(self, "Find", "Find string:", text=self.find_str)
			if str is not None:
				self.find_next(str)
		if event.key() == QtCore.Qt.Key_F3:
			self.find_next(self.find_str)
		if event.key() == QtCore.Qt.Key_F5:
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




class MdiFile:
	sequenceNumber = 1
	def initMdiFile(self, fileName=None, patterns="All Files (*.*)", defaultNamePattern="untitled%d.txt"):
		#self.setAttribute(QtWidgets.Qt.WA_DeleteOnClose)
		self.isUntitled = True
		self.filePatterns = patterns
		self.fileDefaultNamePattern = defaultNamePattern
		if fileName == None:
			self.newFile()
		else:
			self.loadFile(fileName)

	def newFile(self):
		self.isUntitled = True
		self.curFile = self.fileDefaultNamePattern % MdiFile.sequenceNumber
		MdiFile.sequenceNumber += 1
		self.setWindowTitle(self.curFile + '[*]')

		#self.document().contentsChanged.connect(self.documentWasModified)

	def setCurrentFile(self, fileName):
		self.curFile = QFileInfo(fileName).canonicalFilePath()
		self.isUntitled = False
		#self.document().setModified(False)
		self.setWindowModified(False)
		self.setWindowTitle(QFileInfo(self.curFile).fileName() + "[*]")


	def documentWasModified(self, dummy=None):
		self.setWindowModified(True)

	def save(self):
		if self.isUntitled:
			return self.saveAs()
		else:
			return self.saveFile(self.curFile)

	def saveAs(self):
		fileName, _ = QFileDialog.getSaveFileName(self, "Save As", self.curFile, self.filePatterns)
		if not fileName:
			return False

		return self.saveFile(fileName)

	def maybeSave(self):
		if self.isWindowModified():
			ret = QMessageBox.warning(self, self.curFile,
					"'%s' has been modified.\nDo you want to save your "
					"changes?" % QFileInfo(self.curFile).fileName(),
					QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

			if ret == QMessageBox.Save:
				return self.save()

			if ret == QMessageBox.Cancel:
				return False

		return True


class MemoryUsageWidget(QLabel):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		try:
			self.onStatusUpdate()
			self.timer = QTimer(self)
			self.timer.timeout.connect(self.onStatusUpdate)
			self.timer.start(5000)
		except:
			self.setText("---")

	def onStatusUpdate(self):
		self.setText("%0.1f MB"%(get_current_rss()/1024/1024))


