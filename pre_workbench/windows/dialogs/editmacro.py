from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QPushButton, \
	QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem
from pre_workbench.consts import MACRO_PROPERTIES_HELP_URL

from pre_workbench.configs import SettingsField
from pre_workbench.controls.genericwidgets import SettingsGroup
from pre_workbench.controls.scintillaedit import ScintillaEdit
from pre_workbench.guihelper import APP, navigateBrowser
from pre_workbench.macros.macro import Macro
from pre_workbench.typeeditor import showTypeEditorDlg


class EditMacroDialog(QDialog):
	option_types=["-","text","color","font","select","check","int"]
	def __init__(self, parent, macro):
		super().__init__(parent)
		self.macro = macro
		self.setMinimumWidth(400)
		self.resize(800,800)
		verb = "Edit" if macro.container.macrosEditable else "View"
		self.setWindowTitle(verb + " Macro")
		self.setLayout(QVBoxLayout())

		self.propsWidget = SettingsGroup([
			SettingsField("name", "Name", "text", {}),
			SettingsField("input_type", "Macro/Input Type", "select", {"options": list(zip(Macro.TYPES, Macro.TYPES))}),
			SettingsField("output_type", "Output Type", "select", {"options": list(zip(Macro.TYPES, Macro.TYPES))}),
		], {"name": macro.name, "input_type": macro.input_type, "output_type": macro.output_type})
		self.layout().addWidget(self.propsWidget)

		self.tableWidget = QTreeWidget()
		self.tableWidget.setMaximumHeight(100)
		self.tableWidget.setColumnCount(4)
		self.tableWidget.headerItem().setText(0, "Variable name")
		self.tableWidget.setColumnWidth(0, 200)
		self.tableWidget.headerItem().setText(1, "Display title")
		self.tableWidget.headerItem().setText(2, "Field type")
		self.tableWidget.headerItem().setText(3, "Parameters")
		self.tableWidget.setColumnWidth(3, 400)
		self.options = macro.options
		self.loadOptions()
		self.tableWidget.doubleClicked.connect(self.editOptions)
		self.layout().addWidget(self.tableWidget)

		from PyQt5.Qsci import QsciLexerPython
		self.editorWidget = ScintillaEdit(lexer=QsciLexerPython())
		self.editorWidget.setText(macro.code)
		self.editorWidget.setModified(False)
		self.editorWidget.setReadOnly(not self.macro.container.macrosEditable)
		self.layout().addWidget(self.editorWidget)

		btn = QDialogButtonBox()
		btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok|QDialogButtonBox.Help)
		btn.addButton(QPushButton("Edit Options...", clicked=self.editOptions), QDialogButtonBox.ActionRole)
		btn.accepted.connect(self.accept)
		btn.rejected.connect(self.reject)
		btn.helpRequested.connect(lambda: navigateBrowser(MACRO_PROPERTIES_HELP_URL))
		self.layout().addWidget(btn)

		self.editorWidget.ctrlEnterPressed.connect(btn.accepted.emit)

	def loadOptions(self):
		self.tableWidget.clear()
		for opt in self.options:
			item = QTreeWidgetItem([opt['id'], opt['title'], opt['fieldType'], repr(opt['params'])])
			self.tableWidget.addTopLevelItem(item)

	def editOptions(self):
		verb = "Edit" if self.macro.container.macrosEditable else "View"
		options = [{"id":x["id"], "title":x["title"], "field": [ EditMacroDialog.option_types.index(x["fieldType"]), x["params"] ]} for x in self.options]
		res = showTypeEditorDlg("settingsgroup.tes", "SettingsGroup", options, verb + " Options Of Macro \""+self.macro.name+"\"", parent=self)
		if res:
			if self.macro.container.macrosEditable:
				self.options = [{"id":x["id"], "title":x["title"], "fieldType": EditMacroDialog.option_types[x["field"][0]], "params": x["field"][1]} for x in res]
				self.loadOptions()

	def accept(self) -> None:
		if self.macro.container.macrosEditable:
			self.macro.name = self.propsWidget.values["name"]
			self.macro.input_type = self.propsWidget.values["input_type"]
			self.macro.output_type = self.propsWidget.values["output_type"]
			self.macro.code = self.editorWidget.text()
			self.macro.options = self.options

		super().accept()

	def reject(self) -> None:
		if self.editorWidget.isModified():
			if QMessageBox.question(self, "Discard changes?", "Discard changes?")==QMessageBox.No:
				return
		super().reject()
