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
import os

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QFileInfo
from PyQt5.QtWidgets import QFileDialog, \
	QMessageBox

from pre_workbench.app import CurrentProject


class MdiFile:
	sequenceNumber = 1
	def initMdiFile(self, fileName=None, isUntitled=False, patterns="All Files (*.*)", defaultNamePattern="untitled%d.txt"):
		self.isUntitled = True
		self.filePatterns = patterns
		self.fileDefaultNamePattern = defaultNamePattern
		if fileName == None or isUntitled:
			self.setUntitledFile(fileName)
		else:
			self.setCurrentFile(fileName)
			self.loadFile(fileName)

	def saveParams(self):
		self.params["fileName"] = self.curFile
		self.params["isUntitled"] = self.isUntitled
		return self.params

	def setUntitledFile(self, fileName=None):
		self.isUntitled = True
		self.curFile = fileName or (self.fileDefaultNamePattern % MdiFile.sequenceNumber)
		MdiFile.sequenceNumber += 1
		self.setWindowTitle(self.curFile)# + '[*]')

		#self.document().contentsChanged.connect(self.documentWasModified)

	def setCurrentFile(self, fileName):
		self.curFile = QFileInfo(fileName).canonicalFilePath()
		self.isUntitled = False
		#self.document().setModified(False)
		self.setWindowModified(False)
		self.setWindowTitle(QFileInfo(self.curFile).fileName())

	def documentWasModified(self, dummy=None):
		self.setWindowModified(True)

	def save(self):
		if self.isUntitled:
			return self.saveAs()
		else:
			return self.saveFile(self.curFile)

	def saveAs(self):
		patterns = self.filePatterns
		if not "*.*" in patterns: patterns += ';;All Files (*.*)'
		startDir = os.path.join(CurrentProject.projectFolder, self.curFile) if self.isUntitled else self.curFile
		print("saveDialog", self.isUntitled, CurrentProject.projectFolder, startDir, patterns)
		fileName, _ = QFileDialog.getSaveFileName(self, "Save As", startDir, patterns)
		if not fileName:
			return False

		return self.saveFile(fileName)

	def maybeSave(self):
		if self.isWindowModified():
			msgBox = QMessageBox(QMessageBox.Warning, self.curFile,
					"'%s' has been modified.\nDo you want to save your "
					"changes?" % QFileInfo(self.curFile).fileName(),
					QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, self, QtCore.Qt.Sheet)
			msgBox.setWindowModality(QtCore.Qt.WindowModal)
			ret = msgBox.exec()

			if ret == QMessageBox.Save:
				return self.save()

			if ret == QMessageBox.Cancel:
				return False

		return True

	def closeEvent(self, e: QtGui.QCloseEvent) -> None:
		if self.maybeSave():
			e.accept()
		else:
			e.ignore()

	def reloadFile(self):
		self.loadFile(self.curFile)
