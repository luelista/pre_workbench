from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QPushButton, \
	QMessageBox, QInputDialog

from pre_workbench.guihelper import qApp


def showManageAnnotationSetsDialog(parent):
	dlg = QDialog(parent)
	dlg.setMinimumWidth(400)
	dlg.setWindowTitle("Manage Annotation Sets")
	dlg.setLayout(QVBoxLayout())
	listWidget = QListWidget()
	def update():
		listWidget.clear()
		listWidget.addItems(qApp().project.getAnnotationSetNames())
		sel_changed(listWidget.currentRow())
	dlg.layout().addWidget(listWidget)

	btn = QDialogButtonBox()
	#btn.setOrientation(Qt.Vertical)
	def rename_click():
		sel = listWidget.currentItem().text()
		new_name, ok = QInputDialog.getText(dlg, "Rename", "Please enter new name:", text=sel)
		if ok:
			qApp().project.renameAnnotationSet(sel, new_name)
			update()
	def delete_click():
		sel = listWidget.currentItem().text()
		if QMessageBox.question(dlg, "Delete", "Delete Annotation Set \"" + sel + "\"?") == QMessageBox.Yes:
			qApp().project.deleteAnnotationSet(sel)
			update()

	btns = [QPushButton("Rename", clicked=rename_click),
			QPushButton("Delete", clicked=delete_click)]
	for pbtn in btns:
		btn.addButton(pbtn, QDialogButtonBox.ActionRole)
	def sel_changed(row):
		for pbtn in btns:
			pbtn.setEnabled(row != -1)
	listWidget.currentRowChanged.connect(sel_changed)
	update()
	btn.setStandardButtons(QDialogButtonBox.Close)
	btn.accepted.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)
	dlg.exec()
