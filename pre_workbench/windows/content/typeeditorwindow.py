from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QScrollArea

from pre_workbench.configs import respath
from pre_workbench.typeeditor import TypeEditorSchema, JsonView, Type_Named
from pre_workbench.typeregistry import WindowTypes
from pre_workbench.windows.mdifile import MdiFile


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

@WindowTypes.register(fileExts=['.pfi'], schema=respath('format_info.tes'), typeName='FormatInfoFile', description='Grammar Definition File')
class ProtocolFormatInfoFileWindow(TypeEditorFileWindow):
	pass
