from PyQt5.QtCore import (pyqtSignal, QObject)
from PyQt5.QtWidgets import QMessageBox

import pre_workbench.app
from pre_workbench.structinfo.parsecontext import FormatInfoContainer
from pre_workbench.structinfo.serialization import deserialize_fi


class InteractiveFormatInfoContainer(QObject, FormatInfoContainer):
	updated = pyqtSignal()

	def __init__(self, **kw):
		QObject.__init__(self)
		FormatInfoContainer.__init__(self, **kw)

	def write_file(self, fileName):
		super().write_file(fileName)
		self.updated.emit()

	def get_fi_by_def_name(self, def_name):
		try:
			return self.definitions[def_name]
		except KeyError:
			if QMessageBox.question(pre_workbench.app.MainWindow, "Parser", "Reference to undefined type '" + def_name + "'. Create it now?") == QMessageBox.Yes:
				from pre_workbench.typeeditor import showTypeEditorDlg
				params = showTypeEditorDlg("format_info.tes", "AnyFI", title="Create type '"+def_name+"'")
				if params is None: raise
				self.definitions[def_name] = deserialize_fi(params)
				self.write_file(self.file_name)
				return self.definitions[def_name]
			else:
				raise

