
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

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QStringListModel, pyqtSlot, QFileInfo, QTimer
from PyQt5.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPixmap, QColor
from PyQt5.QtWidgets import QFrame, QWidget, QVBoxLayout, \
	QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QDialog, \
	QDialogButtonBox, QCompleter, QSpinBox, QFileDialog, \
	QMessageBox, QAction, QLabel, QColorDialog

from pre_workbench.configs import getIcon
from pre_workbench.syshelper import get_current_rss


def makeDlgButtonBox(dlg, ok_callback, retval_callback):
	btn = QDialogButtonBox()
	btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
	if ok_callback is not None:
		def ok_slot():
			try:
				ok_callback(retval_callback())
				dlg.accept()
			except Exception as ex:
				QMessageBox.critical(dlg, "Fehler", str(ex))
		btn.accepted.connect(ok_slot)
	else:
		btn.accepted.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)


def showWidgetDlg(widget, title, retval_callback, parent=None, ok_callback=None):
	dlg = QDialog(parent)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.layout().addWidget(widget)
	makeDlgButtonBox(dlg, ok_callback, retval_callback)
	if dlg.exec() == QDialog.Rejected: return None
	return retval_callback()


def showSettingsDlg(definition, values=None, title="Options", parent=None, ok_callback=None):
	if values == None: values = {}
	sg = SettingsGroup(definition, values)
	return showWidgetDlg(sg, title, lambda: values, parent, ok_callback)


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
		result = QColorDialog.getColor(QColor(self.text()))
		print(result)
		if result:
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
				self.layout.addRow(title+"  ",None)
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





class MdiFile:
	sequenceNumber = 1
	def initMdiFile(self, fileName=None, isUntitled=False, patterns="All Files (*.*)", defaultNamePattern="untitled%d.txt"):
		#self.setAttribute(QtWidgets.Qt.WA_DeleteOnClose)
		self.isUntitled = True
		self.filePatterns = patterns
		self.fileDefaultNamePattern = defaultNamePattern
		if fileName == None or isUntitled:
			self.setUntitledFile(fileName)
		else:
			self.setCurrentFile(fileName)
			self.loadFile(fileName)

	def setUntitledFile(self, fileName=None):
		self.isUntitled = True
		self.curFile = fileName or (self.fileDefaultNamePattern % MdiFile.sequenceNumber)
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
			self.setCurrentFile(self.curFile)
			return self.saveAs()
		else:
			self.setCurrentFile(self.curFile)
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

	def reloadFile(self):
		self.loadFile(self.curFile)


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


