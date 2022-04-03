
# PRE Workbench
# Copyright (C) 2022 Mira Weller
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
import logging
import uuid

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QEvent, QSize)
from PyQt5.QtGui import QKeyEvent, QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, \
	QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QHBoxLayout, QLabel, \
	QListWidget, QListWidgetItem, QFrame, QScrollArea, QDialog, QDoubleSpinBox, QSpinBox, QTableWidget, QMenu, \
	QInputDialog, QTreeWidget, QTreeWidgetItem, QMessageBox

from pre_workbench.guihelper import makeDlgButtonBox
from pre_workbench.structinfo.expr import Expression
from pre_workbench.configs import respath
from pre_workbench.structinfo import xdrm
from pre_workbench.genericwidgets import MdiFile, showWidgetDlg
from pre_workbench.typeregistry import WindowTypes, DataWidgetTypes

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
		#print(definition)
		if typeKind == Type_Named:
			return self.generateTypeEditorByName(parent, typeContent)
		elif typeKind == Type_Struct:
			return StructTypeEditor(parent, self, definition)
		elif typeKind == Type_Choice:
			return ChoiceTypeEditor(parent, self, definition)
		elif typeKind == Type_List:
			return ListTypeEditor(parent, self, definition)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_INTEGER and typeContent.get('isFlagType')==True:
			return FlagsTypeEditor(parent, self, definition)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_INTEGER:
			return IntTypeEditor(parent, self, definition)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_REAL:
			return FloatTypeEditor(parent, self, definition)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_ENUMERATED:
			return EnumTypeEditor(parent, self, definition)
		elif typeKind == Type_Primitive and typeContent['primitive'] == PrimitiveTags_BOOLEAN:
			return BooleanTypeEditor(parent, self, definition)
		else:
			return TextTypeEditor(parent, self, definition)

	def generateTypeEditorByName(self, parent, typeName):
		te = self.generateTypeEditor(parent, self.typeDefs[typeName]['def'])
		te.typeName = typeName
		return te

	def resolveTypeInfo(self, definition):
		typeKind, typeContent = definition
		if typeKind == Type_Named:
			return self.resolveTypeInfo(self.typeDefs[typeContent]['def'])
		else:
			return definition



class TypeEditorSetOptions:
	def __init__(self, raise_on_missing_key=True, raise_on_unknown_key=True, raise_on_invalid_choice=True):
		self.raise_on_missing_key = raise_on_missing_key
		self.raise_on_unknown_key = raise_on_unknown_key
		self.raise_on_invalid_choice = raise_on_invalid_choice

class BaseTypeEditor(QFrame):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema : TypeEditorSchema, rootTypeDefinition : dict):
		super().__init__(parent)
		self.schema = schema
		self.rootTypeDefinition = rootTypeDefinition
		self.rootTypeContent = rootTypeDefinition[1]
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

class FloatTypeEditor(QDoubleSpinBox):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeDefinition):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setValue(value)
	def get(self):
		return self.value()
	def clear(self):
		self.setValue(0)

class IntTypeEditor(QSpinBox):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeDefinition):
		super().__init__(parent)
	def changeEvent(self, e: QEvent) -> None:
		self.updated.emit("")
	def set(self, value, opts=None):
		self.setValue(value)
	def get(self):
		return self.value()
	def clear(self):
		self.setValue(0)

class TextTypeEditor(QLineEdit):
	updated = pyqtSignal(str)
	def __init__(self, parent, schema, rootTypeDefinition):
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
	def __init__(self, parent, schema, rootTypeDefinition):
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
	def __init__(self, parent, schema, rootTypeDefinition):
		super().__init__(parent)
		for t in rootTypeDefinition[1]["enumOptions"]:
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
	def __init__(self, parent, schema, rootTypeDefinition):
		super().__init__(parent)
		for t in rootTypeDefinition[1]["enumOptions"]:
			listItem = QListWidgetItem(t["name"], self)
			listItem.setCheckState(Qt.Unchecked)
			listItem.setData(Qt.UserRole, t["value"])
		self.itemChanged.connect(self.selectChanged)
		self.myHeight = min(200, len(rootTypeDefinition[1]["enumOptions"]) * 15)
	def sizeHint(self):
		return QSize(150, self.myHeight)
	def selectChanged(self, newIndex):
		self.updated.emit("")
	def set(self, value, opts=None):
		for i in range(self.count()):
			flag = self.item(i).data(Qt.UserRole)
			self.item(i).setCheckState(Qt.Checked if (value & flag) != 0 else Qt.Unchecked)
	def get(self):
		o = 0
		for i in range(self.count()):
			if self.item(i).checkState() == Qt.Checked:
				o |= self.item(i).data(Qt.UserRole)
		return 0
	def clear(self):
		self.set(0)


class error_while_assigning(Exception):
	def __init__(self, key, msg=""):
		super().__init__("error while assigning '"+key+"': "+msg)

class StructuredTypeEditor(BaseTypeEditor):
	def initUI(self):
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)

	def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
		pass

	def keyReleaseEvent(self, e: QtGui.QKeyEvent) -> None:
		if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_V:
			self.paste()

	def paste(self):
		pass

	def onCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		ctx.addAction("Paste", lambda: self.paste())
		ctx.addAction("alt. editor", lambda: showWidgetDlg(JsonView(jdata=self.get(), schema=self.schema, rootTypeDefinition=self.rootTypeDefinition), "alt. editor", lambda: None))

		ctx.exec(self.mapToGlobal(point))



class StructTypeEditor(StructuredTypeEditor):

	def initUI(self):
		super().initUI()
		self.setLayout(QFormLayout())
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
		self.conditionals = list()
		self.elements = dict()
		self.advancedElements = list()

		for field in self.rootTypeContent['fields']:
			self.elements[field['name']] = child = self.schema.generateTypeEditor(self, field['type'])
			child.updated.connect(lambda childKey, fieldKey = field['name']: self.updated.emit("." + fieldKey + childKey))
			opt = ""

			label = field['label'] if 'label' in field else field['name']
			if field.get('optional') == True and "defaultValue" in field: raise Exception("can't have optional AND defaultValue attribute on field")
			if field.get('optional') == True:
				child._struct_opt = labelWidget = QCheckBox(label)
				labelWidget.stateChanged.connect(lambda value, key=field['name']: self.setOpt(key, value))
				#opt = child._struct_opt = EL("input", {type: "checkbox",value:field.name}); opt.onchange=function(){self.setOpt(this.value,this.checked)}
			else:
				labelWidget = QLabel(label)

			self.layout().addRow(labelWidget, child)
			if ("uiShowIf" in field): self.conditionals.append((Expression(expr_str=field['uiShowIf']), labelWidget, child));
			# TODO fix autoincrement fields
			if ("uiFlags" in field and (field['uiFlags'] & Field_UiFlags_autoIncrement) > 0 and hasattr(self.parent(), "get")):
				siblings = self.parent().get()
				if siblings is not None and type(siblings) == list and len(siblings) > 0:
					child.set(max(sib.get(field['name'], 0) for sib in siblings) + 1)
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
		obj = self.get()
		for uiShowIf, labelWidget, child in self.conditionals:
			#vis = eval(uiShowIf, {}, obj)
			vis = uiShowIf.evaluate_dict(obj)
			labelWidget.setVisible(vis)
			child.setVisible(vis)


class ChoiceTypeEditor(StructuredTypeEditor):
	def initUI(self):
		super().initUI()
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
		super().initUI()
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


class TypeEditorFileWindow(QScrollArea, MdiFile):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), type(self).patterns, "untitled%d" + type(self).fileExts[0])
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
		self.metaSchema = TypeEditorSchema(open(type(self).schema,'rb').read())
		#self.editor = self.metaSchema.generateTypeEditorByName(self, type(self).typeName)
		self.editor = JsonView(schema=self.metaSchema, rootTypeDefinition=[Type_Named,type(self).typeName])
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



@WindowTypes.register(fileExts=['.tes'], schema=respath('meta_schema.tes'), typeName='Interface', description='Type Editor Schema', patterns='Type Editor Schema (*.pfi)')
class TypeEditorSchemaFileWindow(TypeEditorFileWindow):
	pass

@WindowTypes.register(fileExts=['.pfi'], schema=respath('format_info.tes'), typeName='FormatInfoFile', description='Protocol Format Info Specification')
class ProtocolFormatInfoFileWindow(TypeEditorFileWindow):
	pass


def resolveSchema(schemaFile):
	if isinstance(schemaFile, TypeEditorSchema): return schemaFile
	if isinstance(schemaFile, str): return TypeEditorSchema(open(respath(schemaFile),'rb').read())
	return None

def showTypeEditorDlg(schemaFile, typeName, values=None, title="Editor", ok_callback=None):
	dlg = QDialog()
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
	if isinstance(typeName, str):
		editor = resolveSchema(schemaFile).generateTypeEditorByName(dlg, typeName)
	else:
		editor = resolveSchema(schemaFile).generateTypeEditor(dlg, typeName)
	if values != None: editor.set(values)
	dlg.layout().addWidget(editor)
	makeDlgButtonBox(dlg, ok_callback, lambda: editor.get())
	if dlg.exec() == QDialog.Rejected: return None
	return editor.get()



def showTreeEditorDlg(schemaFile, typeName, values=None, title="Editor", ok_callback=None):
	dlg = QDialog()
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.setStyleSheet("StructuredTypeEditor { border: 1px solid #bbb }")
	schemaFile = resolveSchema(schemaFile)
	jv = JsonView(jdata=values, schema=schemaFile, rootTypeDefinition=schemaFile.typeDefs[typeName]['def'])
	return showWidgetDlg(jv, title, lambda: jv.get())






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

def getChoiceSubtypeById(typeDef, value):
	if typeDef is not None and typeDef[0] == Type_Choice and len(value) == 2:
		try:
			return next(x for x in typeDef[1]['types'] if x['id'] == value[0])
		except StopIteration:
			pass
	return None


@DataWidgetTypes.register(handles=[dict,])
class JsonView(QTreeWidget):
	updated = pyqtSignal(str)
	def __init__(self, parent=None, schema : "TypeEditorSchema"=None, rootTypeDefinition =None, jdata=None):
		super(JsonView, self).__init__(parent)
		self.schema = resolveSchema(schema)
		self.rootTypeDefinition = [Type_Named, rootTypeDefinition] if isinstance(rootTypeDefinition, str) else rootTypeDefinition
		self.typeName = ""

		self.find_box = None
		self.text_to_titem = TextToTreeItem()
		self.find_str = ""
		self.found_titem_list = []
		self.found_idx = 0

		self.setDragEnabled(True)
		self.viewport().setAcceptDrops(True)
		self.setDropIndicatorShown(True)
		self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		self.setHeaderLabels(["Key", "Type", "Value"])
		self.setColumnWidth(0, 200)
		self.setColumnWidth(1, 100)
		self.setColumnWidth(2, 400)

		self.setContents(jdata)

	def onCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		item = self.itemAt(point)
		if item != None:
			typ = item.data(1, QtCore.Qt.UserRole)
			ctx.addAction("Edit ...", lambda: self.editField(item))
			if self.schema is not None:
				ctx.addAction("Change type ...", lambda: self.changeType(item))
			parentTyp = None
			if item.parent() is not None:
				parentTyp = item.parent().data(1, QtCore.Qt.UserRole)
			if typ is dict:
				ctx.addSeparator()
				childTypeDefs = item.data(1, QtCore.Qt.UserRole + 2)
				for name, typedef in childTypeDefs.items():
					ctx.addAction("Set "+name, lambda: self.addField(item, name, typedef)).setEnabled(False)
				ctx.addAction("Add custom field ...", lambda: self.addField(item, "StructField")).setEnabled(False)

			if typ is list:
				ctx.addSeparator()
				childTypeDef = item.data(1, QtCore.Qt.UserRole + 2)
				if childTypeDef:
					ctx.addAction("Add item ...", lambda: self.addField(item, None, childTypeDef))
				ctx.addAction("Clear list", lambda: self.clearList(item)).setEnabled(False)
			if parentTyp is dict:
				ctx.addSeparator()
				ctx.addAction("Rename ...", lambda: self.renameField(item, item.parent())).setEnabled(False)
				ctx.addAction("Remove this field", lambda: self.removeField(item))
			if parentTyp is list:
				ctx.addSeparator()
				ctx.addAction("Remove this item", lambda: self.removeField(item))

		ctx.exec(self.mapToGlobal(point))

	def sizeHint(self):
		return QSize(620,600)

	def serialize(self):
		return xdrm.dumps([self.schema.iid, self.typeName, self.get()], magic=FILE_MAGIC)
	def deserialize(self, buf):
		iid, typeName, data = xdrm.loads(buf, magic=FILE_MAGIC)
		if iid != self.schema.iid: raise Exception("Invalid file format, invalid interface ID (got=%r, expected=%r)" % (iid, self.schema.iid))
		# TODO check typeName ??
		self.rootTypeDefinition = [Type_Named, typeName]
		self.typeName = typeName
		self.set(data)
	def setContents(self, jdata):
		self.set(jdata)
	def set(self, jdata):
		self.clear()
		self.contents = jdata
		if jdata != None:
			self.tree_add_row("Root", jdata, self, self.rootTypeDefinition ).setExpanded(True)
			#self.addTopLevelItem(root_item)
			#root_item.setExpanded(True)

	def editField(self, item):
		typeDef = item.data(1, QtCore.Qt.UserRole + 1)
		logging.debug("editField: typeDef %r",typeDef)
		data = self.tree_fetch(item)
		if typeDef is not None:
			showTypeEditorDlg(self.schema, typeDef, data, "Edit item", ok_callback=lambda res: self.tree_set_row(item, res, typeDef))
		elif isinstance(data, str):
			res, ok = QInputDialog.getText(self, "Edit", "Edit string value", text=data)
			if ok: self.tree_set_row(item, res, typeDef)
		elif isinstance(data, int):
			res, ok = QInputDialog.getInt(self, "Edit", "Edit int value", value=data)
			if ok: self.tree_set_row(item, res, typeDef)
		elif isinstance(data, float):
			res, ok = QInputDialog.getDouble(self, "Edit", "Edit float value", value=data)
			if ok: self.tree_set_row(item, res, typeDef)
		elif isinstance(data, (bytes, bytearray)):
			from pre_workbench.hexview import showHexView2Dialog
			showHexView2Dialog(self, "Edit bytes value", data, lambda newVal: self.tree_set_row(item, newVal, typeDef))
		else:
			QMessageBox.information(self, "Note", "Editor for data type "+str(type(data))+" not implemented")

	def addField(self, parentItem, name, typeDef):
		parentTypeDef = parentItem.data(1, QtCore.Qt.UserRole + 1)
		parentData = self.tree_fetch(parentItem)
		def ok(res):
			if name is None:
				parentData.append(res)
			else:
				parentData[name] = res
			self.tree_set_row(parentItem, parentData, parentTypeDef)
		showTypeEditorDlg(self.schema, typeDef, None, "Add field", ok_callback=ok)

	def removeField(self, item):
		item.parent().removeChild(item)

	def changeType(self, item):
		typeDef = item.data(1, QtCore.Qt.UserRole + 1)
		newTypedef = showTypeEditorDlg("meta_schema.tes", "Type", typeDef, "Set type")
		if newTypedef is not None:
			res2 = showTypeEditorDlg(self.schema, newTypedef, None, "Set new value")
			if res2 is not None:
				self.tree_set_row(item, res2, newTypedef)

	def get(self):
		return self.tree_fetch(self.topLevelItem(0))

	def tree_fetch(self, item):
		typ = item.data(1, QtCore.Qt.UserRole)
		typeDef = item.data(1, QtCore.Qt.UserRole + 1)
		if typeDef is not None and self.schema is not None:
			typeDef = self.schema.resolveTypeInfo(typeDef)
			if typeDef[0] == Type_Choice and (typ is list or typ is tuple):
				choiceId = item.data(1, QtCore.Qt.UserRole + 2)
				return [choiceId, self.tree_fetch(item.child(0))]
			elif typeDef[0] == Type_Struct and typeDef[1].get('serialization')==StructSerialization_Tuple and (typ is list or typ is tuple):
				return tuple([self.tree_fetch(item.child(i)) for i in range(item.childCount())])

		if typ is dict:
			return {item.child(i).data(0, QtCore.Qt.UserRole) : self.tree_fetch(item.child(i)) for i in range(item.childCount())}
		elif typ is list:
			return [self.tree_fetch(item.child(i)) for i in range(item.childCount())]
		else:
			return item.data(2, QtCore.Qt.UserRole)

	def tree_add_row(self, key, val, parent, typeDef=None):
		me = QTreeWidgetItem(parent)
		me.setData(0, QtCore.Qt.UserRole, key)
		me.setText(0, key)
		self.tree_set_row(me, val, typeDef)
		self.text_to_titem.append(key, me)
		return me

	def tree_set_row(self, me, val, origtypeDef):
		logging.debug("tree_set_row: origTypeDef = %r", origtypeDef)
		me.setData(1, QtCore.Qt.UserRole, type(val))
		me.setData(1, QtCore.Qt.UserRole + 1, origtypeDef)
		if self.schema is not None and origtypeDef is not None:
			typeDef = self.schema.resolveTypeInfo(origtypeDef)
			typeKind = typeDef[0]
		else:
			typeDef = None
			typeKind = -1
		if origtypeDef is not None and origtypeDef[0] == Type_Named:
			me.setText(1, origtypeDef[1])
			me.setFont(1, QFont("sans-serif",	 weight=QFont.Bold))
		else:
			me.setText(1, type(val).__name__)
		me.setData(2, QtCore.Qt.UserRole, val)

		#remove pre-existing child nodes
		for i in reversed(range(me.childCount())):
			me.removeChild(me.child(i))

		logging.debug("tree_set_row: typeDef = %r",typeDef)
		if isinstance(val, dict):
			if typeDef is None:
				childTypeDefs = {}
			else:
				childTypeDefs = {field['name'] : field['type'] for field in typeDef[1]['fields']}
			logging.debug("tree_set_row: defs = %r",childTypeDefs)
			for key, cc in val.items():
				self.tree_add_row(key, cc, me, childTypeDefs.pop(key, None))
			me.setData(1, QtCore.Qt.UserRole + 2, childTypeDefs)
		elif (isinstance(val, list) or isinstance(val, tuple)) and typeKind == Type_Struct and typeDef[1].get("serialization")==StructSerialization_Tuple:
			childTypeDefs = {field['name']: field['type'] for field in typeDef[1]['fields']}
			for field, cc in zip(typeDef[1]['fields'], val):
				self.tree_add_row(field['name'], cc, me, childTypeDefs.pop(field['name'], None))
			me.setData(1, QtCore.Qt.UserRole + 2, childTypeDefs)

		elif isinstance(val, list) or isinstance(val, tuple):
			choiceItem = getChoiceSubtypeById(typeDef, val)
			if choiceItem is not None:
				me.setData(1, QtCore.Qt.UserRole + 2, val[0])
				logging.debug("tree_set_row: choiceItem = %r",choiceItem)
				self.tree_add_row(choiceItem['name'], val[1], me, choiceItem['type'])
			else:
				if typeKind == Type_List:
					me.setData(1, QtCore.Qt.UserRole + 2, typeDef[1]['itemType'])
				for i, cc in enumerate(val):
					key = str(i)
					self.tree_add_row(key, cc, me, typeDef[1]['itemType'] if typeKind == Type_List else None)
		else:
			me.setText(2, str(val))
			self.text_to_titem.append(str(val), me)

		if me.childCount() == 1: me.setExpanded(True)


	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == QtCore.Qt.Key_F and event.modifiers() == QtCore.Qt.ControlModifier:
			str, ok = QInputDialog.getText(self, "Find", "Find string:", text=self.find_str)
			if ok:
				self.find_next(str)
		elif event.key() == QtCore.Qt.Key_F3 or (event.key() == QtCore.Qt.Key_G and event.modifiers() == QtCore.Qt.ControlModifier):
			self.find_next(self.find_str)
		elif event.key() == QtCore.Qt.Key_F5:
			self.setContents(self.contents)
		elif event.key() == QtCore.Qt.Key_Enter:
			self.editField()
		else:
			super().keyPressEvent(event)

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

		self.setCurrentItem(self.found_titem_list[self.found_idx])




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
	editor.set(xdrm.loads(open(sys.argv[3], 'rb').read()))
	with open(sys.argv[4],"wb") as f:
		f.write(editor.serialize())
	sys.exit(app.exec_())


