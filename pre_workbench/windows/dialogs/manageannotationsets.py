from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QPushButton, \
	QMessageBox, QInputDialog

from pre_workbench.guihelper import qApp


class ManageAnnotationSetsDialog(QDialog):
	def __init__(self, parent):
		super().__init__(parent)
		self.setMinimumWidth(400)
		self.setWindowTitle("Manage Annotation Sets")
		self.setLayout(QVBoxLayout())
		self.listWidget = QListWidget()
		self.layout().addWidget(self.listWidget)

		btn = QDialogButtonBox()

		self.btns = [QPushButton("Rename", clicked=self._rename_click),
				QPushButton("Delete", clicked=self._delete_click)]
		for pbtn in self.btns:
			btn.addButton(pbtn, QDialogButtonBox.ActionRole)
		self._update()
		self.listWidget.currentRowChanged.connect(self._sel_changed)
		btn.setStandardButtons(QDialogButtonBox.Close)
		btn.accepted.connect(self.accept)
		btn.rejected.connect(self.reject)
		self.layout().addWidget(btn)

	def _sel_changed(self, row):
		for pbtn in self.btns:
			pbtn.setEnabled(row != -1)

	def _rename_click(self):
		sel = self.listWidget.currentItem().text()
		new_name, ok = QInputDialog.getText(self, "Rename", "Please enter new name:", text=sel)
		if ok:
			qApp().project.renameAnnotationSet(sel, new_name)
			self._update()

	def _delete_click(self):
		sel = self.listWidget.currentItem().text()
		if QMessageBox.question(self, "Delete", "Delete Annotation Set \"" + sel + "\"?") == QMessageBox.Yes:
			qApp().project.deleteAnnotationSet(sel)
			self._update()

	def _update(self):
		self.listWidget.clear()
		self.listWidget.addItems(qApp().project.getAnnotationSetNames())
		self._sel_changed(self.listWidget.currentRow())
