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

import os
import sys
import traceback
import uuid

from PyQt5.QtCore import (Qt, QSize)
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, \
	QFileDialog, QWidget, QVBoxLayout, \
	QMdiArea, QDockWidget, QMessageBox

import configs
from datawidgets import DynamicDataWidget, PacketListWidget
from dockwindows import FileBrowserWidget
from genericwidgets import JsonView
from objectwindow import ObjectWindow
from typeregistry import WindowTypes

MRU_MAX = 5
class WorkbenchMain(QMainWindow):
	def __init__(self):
		super().__init__()
		self.initUI()
		self.restoreChildren()

	def restoreChildren(self):
		for wndInfo in configs.getValue("ChildrenInfo", []):
			clz = WindowTypes.find(name=wndInfo["clz"])
			try:
				wnd = clz(**wndInfo["par"])
				self.showChild(wnd)
				wnd.parent().restoreGeometry(wndInfo["geo"])
			except Exception as ex:
				msg = QMessageBox(QMessageBox.Critical, "Failed to restore window", "Failed to restore window of type "+wndInfo["clz"]+"\n\n"+traceback.format_exc(), QMessageBox.Ok | QMessageBox.Abort, self)
				#msg.addButton(QMessageBox.Ok)
				#msg.addButton(QMessageBox.Abort)
				msg.addButton("Show parameters", QMessageBox.YesRole)
				res = msg.exec()
				print("%x"%res)
				if res == QMessageBox.Abort:
					sys.exit(13)
				if res == 0:
					self.showChild(JsonView(wndInfo))


	def saveChildren(self):
		childrenInfo = [
			{
				"id": wnd.widget().uuid,
				"clz": type(wnd.widget()).__name__,
				"geo": bytes(wnd.saveGeometry()),
				"par": wnd.widget().saveParams(),
			}
			for wnd in self.mdiArea.subWindowList()
			if hasattr(wnd.widget(), "saveParams")
		]
		configs.setValue("ChildrenInfo", childrenInfo)
		
		
	def initUI(self):
		dw=QDockWidget("File browser")
		dw.setObjectName("FileBrowser")
		dw.setWidget(FileBrowserWidget())
		self.addDockWidget(Qt.RightDockWidgetArea, dw)

		dw=QDockWidget("Zoom")
		dw.setObjectName("Zoom")
		self.zoom = DynamicDataWidget()
		dw.setWidget(self.zoom)
		self.addDockWidget(Qt.BottomDockWidgetArea, dw)

		self.mdiArea = QMdiArea()
		self.setCentralWidget(self.mdiArea)

		exitAct = QAction('Exit', self)
		exitAct.setShortcut('Ctrl+Q')
		exitAct.setStatusTip('Exit application')
		exitAct.triggered.connect(self.close)

		newAct = QAction('New window', self)
		newAct.setShortcut('Ctrl+N')
		newAct.setStatusTip('New window')
		newAct.triggered.connect(self.onFileNewWindowAction)

		openAct = QAction('Open', self)
		openAct.setShortcut('Ctrl+O')
		openAct.setStatusTip('Open file')
		openAct.triggered.connect(self.onFileOpenAction)

		self.statusBar()

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(newAct)
		fileMenu.addAction(openAct)
		fileMenu.addSeparator()
		self.mruActions = list()
		for i in range(MRU_MAX):
			a = fileMenu.addAction("-")
			a.triggered.connect(self.onMruClicked)
			self.mruActions.append(a)
		self.updateMruActions()
		fileMenu.addSeparator()
		fileMenu.addAction(exitAct)


		toolsMenu = menubar.addMenu('&Tools')
		toolsMenu.addAction("Show config", lambda: self.showChild(JsonView(configs.configDict)))

		toolbar = self.addToolBar('Main')
		toolbar.addAction(newAct)
		toolbar.addAction(openAct)
		toolbar.addAction(exitAct)
		
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


	def closeEvent(self, e):
		configs.setValue("MainWindowGeometry", self.saveGeometry())
		configs.setValue("MainWindowState", self.saveState(123))
		self.saveChildren()
		super().closeEvent(e)

	def onFileNewWindowAction(self):
		ow = ObjectWindow()
		ow.setConfig({})
		self.showChild(ow)


	def onFileOpenAction(self):
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", configs.getValue("lastOpenFile",""),"All Files (*);;Python Files (*.py)", options=options)
		if fileName:
			configs.setValue("lastOpenFile", fileName)
			self.openFile(fileName)
	
	def openFile(self, fileName):
		configs.updateMru("MainFileMru", fileName, MRU_MAX)
		self.updateMruActions()

		root,ext=os.path.splitext(fileName)
		winType = WindowTypes.find(fileExts=ext)
		if winType != None:
			wnd = winType(fileName=fileName)
			self.showChild(wnd)
			wnd.reload()
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

	def onZoom(self, data):
		self.zoom.setContents(data)

	def showChild(self, widget):
		self.mdiArea.addSubWindow(widget)
		try:
			widget.on_data_selected.connect(self.onZoom)
		except: pass
		if not hasattr(widget, "uuid"): widget.uuid = uuid.uuid1()
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





if __name__ == '__main__':
	
	app = QApplication(sys.argv)
	ex = WorkbenchMain()
	#os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

