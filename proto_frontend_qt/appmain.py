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

import sys, os
import traceback

from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
	QFileDialog, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout, \
	QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox, QLabel, QDockWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject, QSize)

from dockwindows import FileBrowserWidget
from objects import ByteBuffer, ByteBufferList, ReloadRequired
from datasource import PcapFileDataSource, FileDataSource, LiveCaptureDataSource
import configs
from genericwidgets import ExpandWidget, SettingsGroup, printsizepolicy
from datawidgets import DynamicDataWidget, PacketListWidget
from hexview import HexView2
from typeregistry import DataSourceTypes, WindowTypes

MRU_MAX = 5
class ProtoFrontendMain(QMainWindow):
	def __init__(self):
		super().__init__()
		self.initUI()
		self.restoreChildren()

	def restoreChildren(self):
		for wndInfo in configs.getValue("ChildrenInfo", []):
			clz = WindowTypes.find(name=wndInfo["clz"])
			wnd = clz(**wndInfo["par"])
			self.showChild(wnd)
			wnd.parent().restoreGeometry(wndInfo["geo"])

	def saveChildren(self):
		childrenInfo = [
			{
				"clz": type(wnd.widget()).__name__,
				"geo": bytes(wnd.saveGeometry()),
				"par": wnd.widget().saveParams(),
			}
			for wnd in self.mdiArea.subWindowList()
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
		widget.on_data_selected.connect(self.onZoom)
		widget.show()



@WindowTypes.register()
class ObjectWindow(QWidget):
	on_data_selected = pyqtSignal(QObject)
	def __init__(self, name="Untitled", dataSourceType="", collapseSettings=False, **kw):
		super().__init__()
		kw["name"] = name
		kw["dataSourceType"] = dataSourceType
		kw["collapseSettings"] = collapseSettings
		self.params = {}

		self.dataSource = None
		self.dataSourceType = ""
		self.initUI(collapseSettings)
		self.setConfig(kw)


	def saveParams(self):
		self.params["collapseSettings"] = self.sourceConfig.parent().collapsed
		return self.params

	def sizeHint(self):
		return QSize(600,400)
	def initUI(self, collapseSettings):
		layout=QVBoxLayout()
		layout.setContentsMargins(0,0,0,0)
		self.setLayout(layout)
		#tb = QToolBox(self)
		#layout.addWidget(tb)
		self.metaConfig = SettingsGroup([
			("name", "Name", "text", {}),
			("dataSourceType", "Data Source Type", "select", {"options":DataSourceTypes.getSelectList("DisplayName")}),
		], self.params)
		self.metaConfig.item_changed.connect(self.onConfigChanged)
		#tb.addItem(self.metaConfig, "Metadata")
		layout.addWidget(ExpandWidget("Metadata", self.metaConfig, collapseSettings))

		self.sourceConfig = SettingsGroup([], self.params)
		self.sourceConfig.item_changed.connect(self.onConfigChanged)
		#tb.addItem(self.sourceConfig, "Data Source Options")
		layout.addWidget(ExpandWidget("Data Source Options", self.sourceConfig, collapseSettings))

		toolbar = QToolBar()
		self.cancelAction = toolbar.addAction("Cancel")
		self.cancelAction.triggered.connect(self.onCancelFetch)
		self.cancelAction.setEnabled(False)
		self.reloadAction = toolbar.addAction("Reload")
		self.reloadAction.triggered.connect(self.reload)
		layout.addWidget(toolbar)

		self.dataDisplay = DynamicDataWidget()
		self.dataDisplay.on_data_selected.connect(self.on_data_selected.emit)
		#tb.addItem(self.dataDisplay, "Results")
		#layout.addWidget(ExpandWidget("Results", self.dataDisplay))
		layout.addWidget(self.dataDisplay)

	def setConfig(self, config):
		self.metaConfig.setValues(config)
		self.sourceConfig.setValues(config)
		self.params.update(config)
		self.loadDataSource()

	def onConfigChanged(self, key, value):
		self.params[key] = value
		if key == "name":
			self.setWindowTitle(value)
		elif key == "dataSourceType":
			self.loadDataSource()
		else:
			pass
			#if self.dataSource != None:
			#    try:
			#        self.dataSource.updateParam(key, value)
			#    except ReloadRequired as ex:
			#        self.loadDataSource()

	def loadDataSource(self):
		print("dst="+self.params["dataSourceType"])
		if not self.params["dataSourceType"]: return
		clz = DataSourceTypes.find(name=self.params["dataSourceType"])
		if self.dataSourceType != self.params["dataSourceType"]:
			print(clz, clz.ConfigFields)
			self.sourceConfig.setFields(clz.ConfigFields)
			self.dataSourceType = self.params["dataSourceType"]

	def onFinished(self):
		self.cancelAction.setEnabled(False)

	def onCancelFetch(self):
		self.dataSource.cancelFetch()

	def reload(self):
		try:
			self.cancelAction.setEnabled(True)
			clz = DataSourceTypes.find(name=self.params["dataSourceType"])
			self.dataSource = clz(self.params)
			self.dataSource.on_finished.connect(self.onFinished)
			result = self.dataSource.startFetch()
			self.dataDisplay.setContents(result)

		except Exception as e:
			self.dataDisplay.setErrMes(traceback.format_exc())
			self.cancelAction.setEnabled(False)

@WindowTypes.register()
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
	ex = ProtoFrontendMain()
	#os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

