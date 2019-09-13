import uuid

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QEvent, QSize)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, \
	QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QHBoxLayout, QLabel, \
	QSpinBox, QListWidget, QListWidgetItem, QFrame, QScrollArea, QDialog, QDialogButtonBox
import xdrm
from genericwidgets import MdiFile
from typeregistry import WindowTypes

FILE_MAGIC = b"\xde\xca\xf9\x30"

Type_Struct=0; Type_Choice=1; Type_List=2; Type_Named=3; Type_Primitive=4
PrimitiveTags_BOOLEAN = 1
PrimitiveTags_INTEGER = 2
PrimitiveTags_BIT_STRING = 3
PrimitiveTags_OCTET_STRING = 4
PrimitiveTags_OBJECT_IDENTIFIER = 6
PrimitiveTags_REAL = 9
PrimitiveTags_ENUMERATED = 10
PrimitiveTags_UTF8String = 12
Field_UiFlags_advanced = 1
Field_UiFlags_autoIncrement = 2
Type_UiFlags_flags = 1
StructSerialization_Dictionary = 0
StructSerialization_Tuple = 1

class TypeEditorSchema:
	def __init__(self, schema):
		if type(schema) == bytes:
			iid, typeName, data = xdrm.loads(schema, magic=FILE_MAGIC)
			if iid != uuid.UUID("97fc3615-349c-476e-9007-6570e5239332"):
				raise TypeError("Invalid file format, invalid interface ID (got=%r, expected=97fc3615-349c-476e-9007-6570e5239332)" % (iid,))
			if typeName != "Interface":
				raise TypeError("Invalid file format, invalid typeName (got=%r, expected=Interface)" % (iid,))
			schema = data
		self.typeDefs = dict((el['name'], el) for el in schema['typeDefs'])
		self.iid = uuid.UUID(schema['iid'])

	def generateTypeEditor(self, parent, definition):
		typeKind, typeContent = definition
		print(definition)
		if typeKind == Type_Named:
			return self.generateTypeEditorByName(parent, typeContent)
		elif typeKind == Type_Struct:
			return StructTypeEditor(parent, self, typeContent)
		elif typeKind == Type_Choice:
			return ChoiceTypeEditor(parent, self, typeContent)
		elif typeKind == Type_List:
			return ListTypeEditor(parent, self, typeContent)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_INTEGER and typeContent.get('params',{}).get('isFlagType')==True:
			return FlagsTypeEditor(parent, self, typeContent)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_INTEGER:
			return NumericTypeEditor(parent, self, typeContent)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_ENUMERATED:
			return EnumTypeEditor(parent, self, typeContent)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_BOOLEAN:
			return BooleanTypeEditor(parent, self, typeContent)
		else:
			return TextTypeEditor(parent, self, typeContent)

	def generateTypeEditorByName(self, parent, typeName):
		te = self.generateTypeEditor(parent, self.typeDefs[typeName]['def'])
		te.typeName = typeName
		return te



class TypeEditorSetOptions:
	def __init__(self, raise_on_missing_key=True, raise_on_unknown_key=True, raise_on_invalid_choice=True):
		self.raise_on_missing_key = raise_on_missing_key
		self.raise_on_unknown_key = raise_on_unknown_key
		self.raise_on_invalid_choice = raise_on_invalid_choice

class BaseTypeEditor(QFrame):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema : TypeEditorSchema, rootTypeContent : dict):
		super().__init__(parent)
		self.schema = schema
		self.rootTypeContent = rootTypeContent
		self.initUI()
		self.typeName = ""
	def serialize(self):
		return xdrm.dumps([self.schema.iid, self.typeName, self.get()], magic=FILE_MAGIC)
	def deserialize(self, buf):
		iid, typeName, data = xdrm.loads(buf, magic=FILE_MAGIC)
		if iid != self.schema.iid: raise Exception("Invalid file format, invalid interface ID (got=%r, expected=%r)" % (iid, self.schema.iid))
		# TODO check typeName ??
		self.set(data)

class PrimitiveTypeEditor(BaseTypeEditor):
	pass
"""
class NumericTypeEditor(QSpinBox):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setValue(value)
	def get(self):
		return self.value()
	def clear(self):
		self.setValue(0)
"""
class NumericTypeEditor(QLineEdit):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setText(str(value))
	def get(self):
		return int(self.text())
	def clear(self):
		self.setText("0")
class TextTypeEditor(QLineEdit):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setText(value)
	def get(self):
		return self.text()
	def clear(self):
		self.setValue(0)

class BooleanTypeEditor(QCheckBox):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setCheckState(Qt.Checked if value else Qt.Unchecked)
	def get(self):
		return self.checkState() == Qt.Checked
	def clear(self):
		self.setCheckState(Qt.Unchecked)

class EnumTypeEditor(QComboBox):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
		for t in rootTypeContent["enumOptions"]:
			self.addItem(t["name"], t["value"])
		self.activated.connect(self.selectChanged)
	def selectChanged(self, newIndex):
		self.updated.emit("")
	def set(self, value, opts=None):
		idx = self.findData(value)
		self.setCurrentIndex(idx)
	def get(self):
		return self.currentData()
	def clear(self):
		self.setCurrentIndex(0)

class FlagsTypeEditor(QListWidget):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeContent):
		super().__init__(parent)
		for t in rootTypeContent["enumOptions"]:
			listItem = QListWidgetItem(t["name"], self)
			listItem.setCheckState(Qt.Unchecked)
			listItem.setData(Qt.ItemDataRole, t["value"])
		self.itemChanged.connect(self.selectChanged)
	def selectChanged(self, newIndex):
		self.updated.emit("")
	def set(self, value, opts=None):
		for i in range(self.count()):
			flag = self.item(i).data(Qt.ItemDataRole)
			self.item(i).setCheckState(Qt.Checked if (value & flag) != 0 else Qt.Unchecked)
	def get(self):
		o = 0
		for i in range(self.count()):
			if self.item(i).checkState() == Qt.Checked:
				o |= self.item(i).data(Qt.ItemDataRole)
		return 0
	def clear(self):
		self.set(0)


class error_while_assigning(Exception):
	def __init__(self, key, msg=""):
		super().__init__("error while assigning "+key+": "+msg)

class StructuredTypeEditor(BaseTypeEditor):
	def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
		pass

	def keyReleaseEvent(self, e: QtGui.QKeyEvent) -> None:
		if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_V:
			self.paste()

	def paste(self):
		pass


class StructTypeEditor(StructuredTypeEditor):

	def initUI(self):
		self.setLayout(QFormLayout())
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
		self.conditionals = list()
		self.elements = dict()
		self.advancedElements = list()

		for field in self.rootTypeContent['fields']:
			self.elements[field['name']] = child = self.schema.generateTypeEditor(self, field['type'])
			child.updated.connect(lambda childKey, fieldKey = field['name']: self.updated.emit("." + fieldKey + childKey))
			opt = ""

			if field.get('optional') == True and "defaultValue" in field: raise Exception("can't have optional AND defaultValue attribute on field")
			if field.get('optional') == True:
				child._struct_opt = labelWidget = QCheckBox(field['name'])
				labelWidget.stateChanged.connect(lambda value, key=field['name']: self.setOpt(key, value))
				#opt = child._struct_opt = EL("input", {type: "checkbox",value:field.name}); opt.onchange=function(){self.setOpt(this.value,this.checked)}
			else:
				labelWidget = QLabel(field['name'])

			self.layout().addRow(labelWidget, child)
			if ("uiShowIf" in field): self.conditionals.append((field['uiShowIf'], labelWidget, child));
			# TODO fix autoincrement fields
			#if ("uiFlags" in field and (field['uiFlags'] & Field_UiFlags_autoIncrement) > 0 and parent.children):
			#	child.set(parent.children.reduce(function(p,c) { return Math.max(p,c.getFieldValue(field.name))}, 0) + 1);
			if ("uiFlags" in field and (field['uiFlags'] & Field_UiFlags_advanced) > 0):
				self.advancedElements.append((labelWidget, child))

		self.checkConditions(None)
		self.updated.connect(self.checkConditions)

	def clear(self, recursive=False):
		for key, el in self.elements.items():
			if hasattr(el, "_struct_opt"): self.setOpt(key, False)
			#if ("_struct_def" in self.elements[key]) self.elements[key].set(self.elements[key]._struct_def);
			#else
			if recursive: el.clear(recursive)

	def set(self, dictionary, opts=TypeEditorSetOptions()):
		self.clear(False)
		if self.rootTypeContent.get('serialization') == StructSerialization_Tuple:
			for newValue, (key, el) in zip(dictionary, self.elements.items()):
				el.set(newValue)
		else:
			for key, el in dictionary.items():
				if not key in self.elements:
					if opts.raise_on_unknown_key:
						raise LookupError("failed to set unknown struct member "+key)
					else:
						continue
				if hasattr(self.elements[key], "_struct_opt"): self.setOpt(key, True)
				try:
					self.elements[key].set(dictionary[key], opts)
				except Exception as e:
					raise error_while_assigning(key, str(e)) from e

	def get(self):
		if self.rootTypeContent.get('serialization') == StructSerialization_Tuple:
			return [None if hasattr(el, "_struct_opt") and el._struct_opt.checkState() != Qt.Checked
					else el.get()
					for key, el in self.elements.items()]
		o = {}
		for key, el in self.elements.items():
			if hasattr(el, "_struct_opt") and el._struct_opt.checkState() != Qt.Checked:
				continue
			o[key] = el.get()
		return o

	def getFieldValue(self, fieldName):
		if hasattr(self.elements[fieldName], "_struct_opt") and self.elements[fieldName]._struct_opt.checkState() != Qt.Checked:
			return None
		return self.elements[fieldName].get()

	def setOpt(self, key, isSet):
		self.elements[key]._struct_opt.setCheckState(Qt.Checked if isSet else Qt.Unchecked)
		self.elements[key].setVisible(isSet)
		self.updated.emit("." + key)

	@pyqtSlot(str)
	def checkConditions(self, updatedKey):
		#TODO
		"""  var obj = self.get();
		self.conditionals.forEach(function(cond) {
			with(obj) {
				cond[1].className = eval(cond[0]) ? "uiShowIf-visible" : "uiShowIf-hidden";
			}
		});"""
		pass



class ChoiceTypeEditor(StructuredTypeEditor):
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.layout().setContentsMargins(0,0,0,0)
		self.child = None
		self.selectEl = QComboBox()
		self.layout().addWidget(self.selectEl)
		for t in self.rootTypeContent["types"]:
			self.selectEl.addItem(t["name"], t["id"])
		self.selectEl.activated.connect(self.selectChanged)
		self.selectChanged(0)


	def selectChanged(self, newIndex):
		#id = self.selectEl.itemData(newIndex)
		if self.child != None: self.layout().removeWidget(self.child); self.child.deleteLater()
		self.child = None
		choiceItem = self.rootTypeContent['types'][newIndex]
		self.child = self.schema.generateTypeEditor(self, choiceItem['type'])
		self.child.updated.connect(lambda childKey: self.updated.emit(childKey))
		self.layout().addWidget(self.child)
		self.updated.emit("")

	def clear(self, recursive=False):
		self.selectEl.setCurrentIndex(0)
		self.selectChanged(0)

	def set(self, choiceObj, opts=TypeEditorSetOptions()):
		choice, content = choiceObj
		idx = self.selectEl.findData(choice)
		self.selectEl.setCurrentIndex(idx)
		self.selectChanged(idx)  # TODO ist das nötig???
		self.child.set(content, opts)

	def get(self):
		return [
			self.selectEl.currentData(),
			self.child.get()
		]


class ListTypeEditor(StructuredTypeEditor):
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.addButton = QPushButton("Add")
		self.addButton.clicked.connect(lambda: self.add())
		self.layout().addWidget(self.addButton)

	def add(self, object=None):
		child = self.schema.generateTypeEditor(self, self.rootTypeContent['itemType'])
		child.updated.connect(lambda childKey: self.updated.emit("[x]"+childKey))
		wrapper = ListTypeEditorItem(child)
		if object != None: child.set(object)
		self.layout().insertWidget(self.layout().count() - 1, wrapper)
		self.updated.emit("")

	def clear(self):
		while True:
			el = self.findChild(ListTypeEditorItem)
			if el == None: break
			self.layout().removeWidget(el)
			el.setParent(None)
		self.updated.emit("")

	def delete(self, index):
		widget = self.layout().takeAt(index)
		self.updated.emit("")
		widget.deleteLater()

	def get(self):
		return [child.body.get() for child in self.findChildren(ListTypeEditorItem, options=QtCore.Qt.FindDirectChildrenOnly)]

	def set(self, lst, opts=TypeEditorSetOptions()):
		self.clear()
		for item in lst:
			self.add(item)



class ListTypeEditorItem(QWidget):
	def __init__(self, body):
		super().__init__()
		self.body = body
		self.setLayout(QHBoxLayout())
		leftCol =  QFrame()
		leftCol.setLayout(QVBoxLayout())
		leftCol.layout().setAlignment(Qt.AlignTop)
		leftCol.setStyleSheet("QFrame{background:#ddd;}")
		delBtn = QPushButton("X")
		delBtn.clicked.connect(self.deleteMe)
		leftCol.layout().addWidget(delBtn)
		self.layout().addWidget(leftCol)

		self.layout().addWidget(body)
	def deleteMe(self):
		self.parent().layout().removeWidget(self)
		self.parent().updated.emit("")
		self.deleteLater()


class TypeEditorSchemaFileWindow(QScrollArea, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params["fileName"], type(self).patterns, "untitled%d" + type(self).fileExts[0])
	def saveParams(self):
		return self.params
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
		self.metaSchema = TypeEditorSchema(open(type(self).schema,'rb').read())
		self.editor = self.metaSchema.generateTypeEditorByName(self, type(self).typeName)
		self.setWidget(self.editor)
		self.setWidgetResizable(True)
	def loadFile(self, fileName):
		self.editor.deserialize(open(fileName,'rb').read())
		self.setCurrentFile(fileName)
		self.editor.updated.connect(self.documentWasModified)
	def saveFile(self, fileName):
		with open(fileName, "wb") as f:
			f.write(self.editor.serialize())
		self.setCurrentFile(fileName)
		return True



@WindowTypes.register(fileExts=['.tes'], schema='meta_schema.tes', typeName='Interface', description='Type Editor Schema', patterns='Type Editor Schema (*.pfi)')
class TypeEditorSchemaFileWindow(TypeEditorSchemaFileWindow):
	pass

@WindowTypes.register(fileExts=['.pfi'], schema='format_info.tes', typeName='FormatInfoFile', description='Protocol Format Info Specification')
class ProtocolFormatInfoFileWindow(TypeEditorSchemaFileWindow):
	pass




def showTypeEditorDlg(schemaFile, typeName, values=None, title="Options"):
	if values == None: values = {}
	dlg = QDialog()
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
	metaSchema = TypeEditorSchema(open(schemaFile,'rb').read())
	editor = metaSchema.generateTypeEditorByName(dlg, typeName)
	if values != None: editor.set(values)
	dlg.layout().addWidget(editor)
	btn = QDialogButtonBox()
	btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
	btn.clicked.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)
	if dlg.exec() == QDialog.Rejected: return None
	return editor.get()



if __name__ == '__main__':
	import sys
	from PyQt5.QtWidgets import QMainWindow, QApplication, QScrollArea
	app = QApplication(sys.argv)
	schema = TypeEditorSchema(open(sys.argv[1],'rb').read())
	wnd = QMainWindow()
	scroll = QScrollArea(wnd)
	scroll.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
	editor = schema.generateTypeEditorByName(scroll, sys.argv[2])
	scroll.setWidget(editor)
	scroll.setWidgetResizable(True)
	wnd.setCentralWidget(scroll)
	wnd.show()
	editor.set(xdrm.loads(open(sys.argv[3],'rb').read()))
	with open(sys.argv[4],"wb") as f:
		f.write(editor.serialize())
	sys.exit(app.exec_())


