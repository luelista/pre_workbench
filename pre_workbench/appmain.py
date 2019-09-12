#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
ZetCode PyQt5 tutorial 

This program creates a skeleton of
a classic GUI application with a menubar,
toolbar, statusbar, and a central widget. 

Author: Jan Bodnar
Website: zetcode.com 
Last edited: August 2017
"""
import time
import os
import sys
import traceback
import uuid

from PyQt5.QtCore import (Qt, QSize, pyqtSlot, QSignalMapper)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, \
	QFileDialog, QWidget, QVBoxLayout, \
	QMdiArea, QDockWidget, QMessageBox, QTextEdit

import configs
from datawidgets import DynamicDataWidget, PacketListWidget
from dockwindows import FileBrowserWidget
from genericwidgets import JsonView
from objectwindow import ObjectWindow
from typeregistry import WindowTypes
import typeeditor

MRU_MAX = 5
class WorkbenchMain(QMainWindow):
	def __init__(self):
		super().__init__()
		self.initUI()
		self.restoreChildren()

	def restoreChildren(self):
		for wndInfo in configs.getValue("ChildrenInfo", []):
			clz, _ = WindowTypes.find(name=wndInfo["clz"])
			try:
				wnd = clz(**wndInfo["par"])
				self.showChild(wnd)
				wnd.parent().restoreGeometry(wndInfo["geo"])
				wnd.setObjectName(str(wndInfo["id"]))
			except Exception as ex:
				msg = QMessageBox(QMessageBox.Critical, "Failed to restore window", "Failed to restore window of type "+wndInfo["clz"]+"\n\n"+traceback.format_exc(), QMessageBox.Ok | QMessageBox.Abort, self)
				msg.addButton("Show parameters", QMessageBox.YesRole)
				res = msg.exec()
				if res == QMessageBox.Abort:
					sys.exit(13)
				if res == 0:
					self.showChild(JsonView(wndInfo))
		for wndInfo in configs.getValue("DockWidgetStates", []):
			self.dockWidgets[wndInfo["id"]].restoreState(wndInfo["par"])


	def closeEvent(self, e):
		configs.setValue("MainWindowGeometry", self.saveGeometry())
		configs.setValue("MainWindowState", self.saveState(123))
		self.saveChildren()
		super().closeEvent(e)

	def saveChildren(self):
		configs.setValue("ChildrenInfo", [
			{
				"id": wnd.widget().objectName(),
				"clz": type(wnd.widget()).__name__,
				"geo": bytes(wnd.saveGeometry()),
				"par": wnd.widget().saveParams(),
			}
			for wnd in self.mdiArea.subWindowList()
			if hasattr(wnd.widget(), "saveParams")
		])
		configs.setValue("DockWidgetStates", [
			{ "id": name, "par": widget.saveState() }
			for name, widget in self.dockWidgets.items()
			if hasattr(widget, "saveState")
		])


	def createDockWnd(self, name, widget):
		dw=QDockWidget(name)
		dw.setObjectName(name)
		dw.setWidget(widget)
		self.addDockWidget(Qt.RightDockWidgetArea, dw)
		self.dockWidgets[name] = widget

	def createActions(self):
		self.exitAct = QAction('Exit', self, shortcut='Ctrl+Q', statusTip='Exit application', triggered=self.close)
		self.newAct = QAction('New window', self, shortcut='Ctrl+N', statusTip='New window', triggered=self.onFileNewWindowAction)
		self.openAct = QAction('Open', self, shortcut='Ctrl+O', statusTip='Open file', triggered=self.onFileOpenAction)
		self.saveAct = QAction("&Save", self,
				shortcut=QKeySequence.Save,
				statusTip="Save the document to disk", triggered=self.onFileSaveAction)

		self.saveAsAct = QAction("Save &As...", self,
				shortcut=QKeySequence.SaveAs,
				statusTip="Save the document under a new name",
				triggered=self.onFileSaveAsAction)

		self.closeAct = QAction("Cl&ose", self,
				statusTip="Close the active window",
				triggered=self.mdiArea.closeActiveSubWindow)

		self.closeAllAct = QAction("Close &All", self,
				statusTip="Close all the windows",
				triggered=self.mdiArea.closeAllSubWindows)

		self.nextAct = QAction("Ne&xt", self, shortcut=QKeySequence.NextChild,
				statusTip="Move the focus to the next window",
				triggered=self.mdiArea.activateNextSubWindow)

		self.previousAct = QAction("Pre&vious", self,
				shortcut=QKeySequence.PreviousChild,
				statusTip="Move the focus to the previous window",
				triggered=self.mdiArea.activatePreviousSubWindow)


	def initUI(self):
		self.dockWidgets = dict()
		self.createDockWnd("File Browser", FileBrowserWidget())
		self.dockWidgets["File Browser"].on_open.connect(self.openFile)
		self.createDockWnd("Zoom", DynamicDataWidget())
		self.createDockWnd("Data Source Log", QTextEdit())

		self.mdiArea = QMdiArea()
		self.setCentralWidget(self.mdiArea)

		self.mdiArea.subWindowActivated.connect(self.onSubWindowActivated)
		self.windowMapper = QSignalMapper(self)
		self.windowMapper.mapped[QWidget].connect(self.setActiveSubWindow)

		self.createActions()

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(self.newAct)
		fileMenu.addAction(self.openAct)
		fileMenu.addAction(self.saveAct)
		fileMenu.addAction(self.saveAsAct)
		fileMenu.addSeparator()
		self.mruActions = list()
		for i in range(MRU_MAX):
			a = fileMenu.addAction("-")
			a.triggered.connect(self.onMruClicked)
			self.mruActions.append(a)
		self.updateMruActions()
		fileMenu.addSeparator()
		fileMenu.addAction(self.exitAct)


		viewMenu = menubar.addMenu('&View')
		for name in self.dockWidgets.keys():
			viewMenu.addAction(name, lambda name=name: self.dockWidgets[name].parent().show())

		toolsMenu = menubar.addMenu('&Tools')
		toolsMenu.addAction("Show config", lambda: self.showChild(JsonView(configs.configDict)))

		self.windowMenu = menubar.addMenu("&Window")
		self.updateWindowMenu()
		self.windowMenu.aboutToShow.connect(self.updateWindowMenu)

		toolbar = self.addToolBar('Main')
		toolbar.addAction(self.newAct)
		toolbar.addAction(self.openAct)
		toolbar.addAction(self.exitAct)
		
		self.setGeometry(300, 300, 850, 850)
		self.restoreGeometry(configs.getValue("MainWindowGeometry", b""))
		self.restoreState(configs.getValue("MainWindowState", b""), 123)
		self.setWindowTitle('PRE Workbench')
		self.show()

	def onMruClicked(self):
		self.openFile(self.sender().data())

	def updateMruActions(self):
		mru = configs.getValue("MainFileMru", [])
		for i in range(MRU_MAX):
			self.mruActions[i].setVisible(i < len(mru))
			if i < len(mru):
				self.mruActions[i].setText(os.path.basename(mru[i]))
				self.mruActions[i].setData(mru[i])

	def updateWindowMenu(self):
		self.windowMenu.clear()
		self.windowMenu.addAction(self.closeAct)
		self.windowMenu.addAction(self.closeAllAct)
		self.windowMenu.addSeparator()
		self.windowMenu.addAction(self.nextAct)
		self.windowMenu.addAction(self.previousAct)

		windows = self.mdiArea.subWindowList()
		if len(windows) != 0: self.windowMenu.addSeparator()

		for i, window in enumerate(windows):
			child = window.widget()

			text = "%d %s" % (i + 1, child.windowTitle())
			if i < 9:
				text = '&' + text

			action = self.windowMenu.addAction(text)
			action.setCheckable(True)
			action.setChecked(child is self.activeMdiChild())
			action.triggered.connect(self.windowMapper.map)
			self.windowMapper.setMapping(action, window)

	def onSubWindowActivated(self):
		pass

	def activeMdiChild(self):
		activeSubWindow = self.mdiArea.activeSubWindow()
		if activeSubWindow:
			return activeSubWindow.widget()
		return None
	def setActiveSubWindow(self, window):
		if window:
			self.mdiArea.setActiveSubWindow(window)


	def onFileSaveAction(self):
		if self.activeMdiChild() and self.activeMdiChild().save():
			self.statusBar().showMessage("File saved", 2000)

	def onFileSaveAsAction(self):
		if self.activeMdiChild() and self.activeMdiChild().saveAs():
			self.statusBar().showMessage("File saved", 2000)


	def onFileNewWindowAction(self):
		ow = ObjectWindow()
		ow.setConfig({})
		self.showChild(ow)


	def onFileOpenAction(self):
		options = QFileDialog.Options()
		#options |= QFileDialog.DontUseNativeDialog
		fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", configs.getValue("lastOpenFile",""),"All Files (*);;Python Files (*.py)", options=options)
		if fileName:
			configs.setValue("lastOpenFile", fileName)
			self.openFile(fileName)

	@pyqtSlot(str)
	def openFile(self, fileName):
		configs.updateMru("MainFileMru", fileName, MRU_MAX)
		self.updateMruActions()

		root,ext=os.path.splitext(fileName)
		winType, _ = WindowTypes.find(fileExts=ext)
		if winType != None:
			try:
				wnd = winType(fileName=fileName)
				self.showChild(wnd)
			except Exception as ex:
				msg = QMessageBox(QMessageBox.Critical, "Failed to open file", "Failed to open window of type "+winType.__name__+"\n\n"+str(ex), QMessageBox.Ok, self)
				msg.setDetailedText(traceback.format_exc())
				msg.exec()
			return

		if fileName.endswith(".pcap") or fileName.endswith(".pcapng"):
			meta = {
				"name": fileName,
				"dataSourceType": "PcapFileDataSource",
				"fileName": fileName
			}
		else:
			meta = {
				"name": fileName,
				"dataSourceType": "FileDataSource",
				"fileName": fileName
			}
		ow = ObjectWindow(collapseSettings=True)
		ow.setConfig(meta)
		self.showChild(ow)
		ow.reload()

	def onLog(self, txt):
		self.dockWidgets["Data Source Log"].append(self.sender().objectName() + ": " + txt + "\n")

	def onZoom(self, cont):
		self.dockWidgets["Zoom"].setContents(cont)

	def showChild(self, widget):
		self.mdiArea.addSubWindow(widget)
		try:
			widget.on_data_selected.connect(self.onZoom)
		except: pass
		try:
			widget.on_log.connect(self.onLog)
		except: pass
		if not widget.objectName(): widget.setObjectName(str(uuid.uuid1()))
		widget.show()



@WindowTypes.register() #fileExts=['.pcapng','.pcap','.cap'])
class PcapngFileWindow(QWidget):
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
	def saveParams(self):
		return self.params
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = PacketListWidget()
		self.layout().addWidget(self.dataDisplay)



def excepthook(excType, excValue, tracebackobj):
	"""
	Global function to catch unhandled exceptions.

	@param excType exception type
	@param excValue exception value
	@param tracebackobj traceback object
	"""
	separator = '-' * 80
	logFile = "pyappcrash.log"
	notice = \
		"""An unhandled exception occurred. Please report the problem\n"""\
		"""using the error reporting dialog.\n"""\
		"""A log has been written to "%s".\n\nError information:\n""" % \
		( logFile,)
	versionInfo="0.0.1"
	timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

	traceback.print_tb(tracebackobj)

	tbinfo = traceback.format_tb(tracebackobj)
	errmsg = '%s: \n%s' % (str(excType), str(excValue))
	sections = [separator, timeString, separator, errmsg, separator]+ tbinfo
	msg = '\n'.join(sections)
	try:
		f = open(logFile, "w")
		f.write(msg)
		f.write(versionInfo)
		f.close()
	except IOError:
		pass
	errorbox = QMessageBox()
	errorbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Abort)
	errorbox.setText(str(notice)+str(msg)+str(versionInfo))
	if errorbox.exec_() == QMessageBox.Abort:
		sys.exit(2)

sys.excepthook = excepthook


if __name__ == '__main__':
	
	app = QApplication(sys.argv)
	ex = WorkbenchMain()
	#os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

