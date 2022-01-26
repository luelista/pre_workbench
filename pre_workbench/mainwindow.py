#!/usr/bin/python3
# -*- coding: utf-8 -*-

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


import time
import os
import sys
import traceback
import uuid
import logging

from PyQt5.QtCore import (Qt, QSize, pyqtSlot, QSignalMapper, QTimer, QFileSystemWatcher, pyqtSignal)
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import QMainWindow, QAction, QApplication, \
	QFileDialog, QWidget, QVBoxLayout, \
	QMdiArea, QDockWidget, QMessageBox, QTextEdit, QMdiSubWindow, QStyleFactory, QToolButton, QMenu, QSplashScreen

from pre_workbench.dockwindows import RangeTreeDockWidget, RangeListWidget
from pre_workbench import configs, SettingsSection
from pre_workbench.datawidgets import DynamicDataWidget, PacketListWidget
from pre_workbench.dockwindows import FileBrowserWidget, MdiWindowListWidget, StructInfoTreeWidget, \
	StructInfoCodeWidget, DataInspectorWidget
from pre_workbench.genericwidgets import MdiFile, MemoryUsageWidget, showSettingsDlg, showPreferencesDlg
from pre_workbench.typeeditor import JsonView
from pre_workbench.guihelper import NavigateCommands, GlobalEvents
from pre_workbench.hexview import HexView2
from pre_workbench.objectwindow import ObjectWindow
from pre_workbench.typeregistry import WindowTypes

from pre_workbench import typeeditor
from pre_workbench import textfile

MRU_MAX = 5
class WorkbenchMain(QMainWindow):
	on_zoom_update = pyqtSignal(object)
	on_selected_bytes_update = pyqtSignal(object)
	on_grammar_update = pyqtSignal(object)
	on_meta_update = pyqtSignal(str, object)

	def __init__(self):
		super().__init__()
		self.mappedChildActions = list()
		self.curChildMeta = dict()
		self.initUI()
		self.restoreChildren()

		NavigateCommands["WINDOW-ID"] = self.navigateWindowId
		NavigateCommands["WINDOW"] = self.navigateWindow
		NavigateCommands["OPEN"] = self.openFile
		self.statusTimer = QTimer(self)
		self.statusTimer.timeout.connect(self.onStatusTimer)
		self.statusTimer.start(1000)

	def onStatusTimer(self):
		self.statusBar()

	def restoreChildren(self):
		for wndInfo in configs.getValue("ChildrenInfo", []):
			clz, _ = WindowTypes.find(name=wndInfo["clz"])
			try:
				wnd = clz(**wndInfo["par"])
				wnd.setObjectName(str(wndInfo["id"]))
				self.showChild(wnd)
				if self.mdiArea.viewMode() == QMdiArea.SubWindowView:
					#wnd.parent().restoreGeometry(wndInfo["geo"])
					x,y,w,h = wndInfo["geo"]
					wnd.parent().move(x,y)
					wnd.parent().resize(w,h)
			except Exception as ex:
				traceback.print_exc()
				msg = QMessageBox(QMessageBox.Critical, "Failed to restore window", "Failed to restore window of type "+wndInfo["clz"]+"\n\n"+traceback.format_exc(), QMessageBox.Ok | QMessageBox.Abort, self)
				msg.addButton("Show parameters", QMessageBox.YesRole)
				res = msg.exec()
				if res == QMessageBox.Abort:
					sys.exit(13)
				if res == 0:
					self.showChild(JsonView(jdata=wndInfo))
		for wndInfo in configs.getValue("DockWidgetStates", []):
			self.dockWidgets[wndInfo["id"]].restoreState(wndInfo["par"])

	def updateChildWindowList(self, obj=None):
		logging.debug("updateChildWindowList")
		wndList = self.mdiArea.subWindowList()
		self.dockWidgets["Window List"].updateWindowList(wndList)

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
				"geo": [wnd.pos().x(), wnd.pos().y(), wnd.size().width(), wnd.size().height() ], #bytes(wnd.saveGeometry()),
				"par": wnd.widget().saveParams(),
			}
			for wnd in self.mdiArea.subWindowList(QMdiArea.StackingOrder)
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

	def mapChildAction(self, action, funcName):
		action.setProperty("childFuncName", funcName)
		self.mappedChildActions.append(action)
		action.triggered.connect(self.mappedChildActionTriggered)

	def mappedChildActionTriggered(self):
		funcName = self.sender().property("childFuncName")
		child = self.activeMdiChild()
		if child is not None and hasattr(child, funcName):
			getattr(child, funcName)()
		elif child is not None and hasattr(child, "childActionProxy") and hasattr(child.childActionProxy(), funcName):
			getattr(child.childActionProxy(), funcName)()

	def updateMappedChildActions(self):
		child = self.activeMdiChild()
		if child is None:
			for action in self.mappedChildActions:
				action.setEnabled(False)
		else:
			for action in self.mappedChildActions:
				funcName = action.property("childFuncName")
				action.setEnabled(hasattr(child, funcName) or hasattr(child, "childActionProxy") and hasattr(child.childActionProxy(), funcName))


	def createActions(self):
		self.exitAct = QAction('Exit', self, shortcut='Ctrl+Q', statusTip='Exit application', triggered=self.close)
		self.openAct = QAction('Open', self, shortcut='Ctrl+O', statusTip='Open file', triggered=self.onFileOpenAction)
		self.saveAct = QAction("&Save", self,
				shortcut=QKeySequence.Save,
				statusTip="Save the document to disk")
		self.mapChildAction(self.saveAct, "save")

		self.saveAsAct = QAction("Save &As...", self,
				shortcut=QKeySequence.SaveAs,
				statusTip="Save the document under a new name")
		self.mapChildAction(self.saveAsAct, "saveAs")

		self.reloadFileAct = QAction("&Reload", self,
				shortcut=QKeySequence.Refresh,
				statusTip="Reload the current file from disk")
		self.mapChildAction(self.reloadFileAct, "reloadFile")

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

		self.reloadGrammarAct = QAction("&Reload grammar", self,
				shortcut="Ctrl+I",
				statusTip="Reload the grammar from disk")
		self.mapChildAction(self.reloadGrammarAct, "reloadGrammar")

		self.openGrammarAct = QAction("&Open grammar", self,
				shortcut="Ctrl+Shift+I",
				statusTip="Open a grammar file to parse the current buffer")
		self.mapChildAction(self.openGrammarAct, "openGrammar")



	def initUI(self):
		self.setUnifiedTitleAndToolBarOnMac(True)
		self.setDocumentMode(True)
		self.dockWidgets = dict()
		self.createDockWnd("File Browser", FileBrowserWidget())
		self.dockWidgets["File Browser"].on_open.connect(self.openFile)
		self.createDockWnd("Zoom", DynamicDataWidget())
		dsLog = QTextEdit()
		self.createDockWnd("Data Source Log", dsLog)
		GlobalEvents.on_log.connect(lambda txt: dsLog.append(self.sender().objectName() + ": " + txt + "\n"))

		self.createDockWnd("Window List", MdiWindowListWidget())
		self.createDockWnd("Grammar Definition Tree", StructInfoTreeWidget())
		self.createDockWnd("Grammar Definition Code", StructInfoCodeWidget())
		self.createDockWnd("Grammar Parse Result", RangeTreeDockWidget())
		self.createDockWnd("Data Inspector", DataInspectorWidget())
		self.createDockWnd("Selected Ranges", RangeListWidget())

		self.mdiArea = QMdiArea()
		configs.registerOption(SettingsSection("View", "View", "General", "General"),
							   "TabbedView", "Tabbed View", "check", {}, False, lambda k, v:
			self.mdiArea.setViewMode(QMdiArea.TabbedView if v else QMdiArea.SubWindowView))
		self.mdiArea.setDocumentMode(True)
		self.mdiArea.setTabsClosable(True)
		self.setCentralWidget(self.mdiArea)

		self.mdiArea.subWindowActivated.connect(self.onSubWindowActivated)
		self.windowMapper = QSignalMapper(self)
		self.windowMapper.mapped[QWidget].connect(self.setActiveSubWindow)

		self.createActions()

		menubar = self.menuBar()
		toolbar = self.addToolBar('Main')
		newTbAct = QToolButton(self, text='New', popupMode=QToolButton.InstantPopup)
		newTbMenu = QMenu(newTbAct)
		newTbAct.setMenu(newTbMenu)
		fileMenu = menubar.addMenu('&File')
		for wndTyp, meta in WindowTypes.types:
			text = 'New '+meta.get('displayName', meta.get('name'))
			newAct = QAction(text, self, #shortcut='Ctrl+N',
									   statusTip=text,
									   triggered=lambda dummy, wndTyp=wndTyp: self.onFileNewWindowAction(wndTyp))
			fileMenu.addAction(newAct)
			newTbMenu.addAction(newAct)
		toolbar.addWidget(newTbAct)
		fileMenu.addSeparator()
		#fileMenu.addAction(self.newAct)
		fileMenu.addAction(self.openAct)
		fileMenu.addAction(self.saveAct)
		fileMenu.addAction(self.saveAsAct)
		fileMenu.addAction(self.reloadFileAct)
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
		a = QAction("Zoom In", self, shortcut='Ctrl++'); self.mapChildAction(a, "zoomIn"); viewMenu.addAction(a)
		a = QAction("Zoom Out", self, shortcut='Ctrl+-'); self.mapChildAction(a, "zoomOut"); viewMenu.addAction(a)
		a = QAction("Reset", self, shortcut='Ctrl+0'); self.mapChildAction(a, "zoomReset"); viewMenu.addAction(a)
		viewMenu.addSeparator()
		for name in self.dockWidgets.keys():
			viewMenu.addAction(name, lambda name=name: self.dockWidgets[name].parent().show())

		parserMenu = menubar.addMenu('&Parser')
		parserMenu.addAction(self.openGrammarAct)
		parserMenu.addAction(self.reloadGrammarAct)

		toolsMenu = menubar.addMenu('&Tools')
		showConfigAction = QAction("Show config", self, triggered=lambda: self.showChild(JsonView(jdata=configs.configDict)),
								   shortcut='Ctrl+Shift+,')
		toolsMenu.addAction(showConfigAction)
		editConfigAction = QAction("Preferences ...", self, triggered=lambda: self.onPreferences(),
								   menuRole=QAction.PreferencesRole, shortcut='Ctrl+,')
		toolsMenu.addAction(editConfigAction)

		self.windowMenu = menubar.addMenu("&Window")
		self.updateWindowMenu()
		self.windowMenu.aboutToShow.connect(self.updateWindowMenu)

		#toolbar.addAction(self.newAct)
		toolbar.addAction(self.openAct)
		toolbar.addAction(self.exitAct)

		self.statusBar().addWidget(MemoryUsageWidget())

		self.setGeometry(300, 300, 850, 850)
		self.restoreGeometry(configs.getValue("MainWindowGeometry", b""))
		self.restoreState(configs.getValue("MainWindowState", b""), 123)
		self.setWindowTitle('PRE Workbench')
		self.show()

	def onPreferences(self):
		res = showPreferencesDlg(configs.configDefinitions, configs.configDict, "Preferences", self)
		if res is not None:
			for k,v in res.items():
				configs.setValue(k,v)

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
		self.updateMappedChildActions()
		new_meta = self.activeMdiChild().child_wnd_meta if self.activeMdiChild() is not None else {}
		# TODO what about metas only contained in new_meta?
		for ident, oldval in self.curChildMeta.items():
			newval = new_meta.get(ident)
			if newval != oldval:
				self.curChildMeta[ident] = newval
				if hasattr(self, "on_"+ident+"_update"): getattr(self, "on_"+ident+"_update").emit(newval)
				self.on_meta_update.emit(ident, newval)

	def activeMdiChild(self):
		activeSubWindow = self.mdiArea.activeSubWindow()
		if activeSubWindow:
			return activeSubWindow.widget()
		return None

	def setActiveSubWindow(self, window):
		if window:
			self.mdiArea.setActiveSubWindow(window)


	def onFileNewWindowAction(self, typ):
		ow = typ()
		self.showChild(ow)


	def onFileOpenAction(self):
		options = QFileDialog.Options()
		#options |= QFileDialog.DontUseNativeDialog
		fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", configs.getValue("lastOpenFile",""),"All Files (*);;Python Files (*.py)", options=options)
		if fileName:
			configs.setValue("lastOpenFile", fileName)
			self.openFile(fileName)

	def navigateWindowId(self, Id):
		#childWnd = self.mdiArea.findChild(QMdiSubWindow, Id)
		for childWnd in self.mdiArea.subWindowList():
			logging.debug("childWnd object name: %s", childWnd.objectName())
			if childWnd.objectName() == Id:
				logging.debug("childWnd", childWnd)
				self.setActiveSubWindow(childWnd)
				childWnd.show()
				return True

		return False

	@pyqtSlot(str, str)
	def navigateWindow(self, Type, FileName):
		winType, _ = WindowTypes.find(name=Type)
		if winType is None:
			QMessageBox.critical(self, "Failed to open window", "Failed to open window of unknown type "+Type)
			return
		try:
			wnd = winType(fileName=FileName)
			self.showChild(wnd)
		except Exception as ex:
			msg = QMessageBox(QMessageBox.Critical, "Failed to open file", "Failed to open window of type "+winType.__name__+"\n\n"+str(ex), QMessageBox.Ok, self)
			msg.setDetailedText(traceback.format_exc())
			msg.exec()


	@pyqtSlot(str)
	def openFile(self, FileName):
		configs.updateMru("MainFileMru", FileName, MRU_MAX)
		self.updateMruActions()

		root,ext=os.path.splitext(FileName)
		winType, _ = WindowTypes.find(fileExts=ext)
		if winType != None:
			try:
				wnd = winType(fileName=FileName)
				self.showChild(wnd)
			except Exception as ex:
				msg = QMessageBox(QMessageBox.Critical, "Failed to open file", "Failed to open window of type "+winType.__name__+"\n\n"+str(ex), QMessageBox.Ok, self)
				msg.setDetailedText(traceback.format_exc())
				msg.exec()
			return

		if FileName.endswith(".pcap") or FileName.endswith(".pcapng"):
			meta = {
				"name": FileName,
				"dataSourceType": "PcapFileDataSource",
				"fileName": FileName
			}
		else:
			meta = {
				"name": FileName,
				"dataSourceType": "FileDataSource",
				"fileName": FileName
			}
		ow = ObjectWindow(collapseSettings=True)
		ow.setConfig(meta)
		self.showChild(ow)
		ow.reload()

	def onMetaUpdate(self, ident, newval):
		self.sender().child_wnd_meta[ident] = newval
		self.curChildMeta[ident] = newval
		if hasattr(self, "on_"+ident+"_update"): getattr(self, "on_"+ident+"_update").emit(newval)
		self.on_meta_update.emit(ident, newval)

	def showChild(self, widget):
		logging.debug("showChild %s", widget)
		subwnd = self.mdiArea.addSubWindow(widget)
		widget.child_wnd_meta = dict()
		try:
			widget.on_meta_update.connect(self.onMetaUpdate)
		except: pass
		try:
			widget.on_log.connect(self.onLog)
		except: pass
		widget.destroyed.connect(self.updateChildWindowList)
		if not widget.objectName(): widget.setObjectName(str(uuid.uuid1()))
		subwnd.setObjectName(widget.objectName())
		widget.show()
		self.updateChildWindowList()



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


@WindowTypes.register() #fileExts=['.pcapng','.pcap','.cap'])
class HexFileWindow(QWidget, MdiFile):
	on_meta_update = pyqtSignal(str, object)
	def __init__(self, **params):
		super().__init__()
		self.params = params
		self.initUI()
		self.initMdiFile(params.get("fileName"), params.get("isUntitled", False), "All files (*.*)", "untitled%d.bin")
	def sizeHint(self):
		return QSize(600,400)
	def initUI(self):
		self.setLayout(QVBoxLayout())
		self.dataDisplay = HexView2()
		self.dataDisplay.selectionChanged.connect(self.onSelectionChanged)
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().addWidget(self.dataDisplay)

	def onSelectionChanged(self, selRange):
		selbytes = self.dataDisplay.buffers[selRange.buffer_idx].getBytes(selRange.start, selRange.length())
		self.on_meta_update.emit("selected_bytes", selbytes)

	def loadFile(self, fileName):
		self.dataDisplay.setBytes(open(fileName,'rb').read())

	def saveFile(self, fileName):
		bin = self.dataDisplay.buffers[0].buffer
		with open(fileName, "wb") as f:
			f.write(bin)
		return True


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


	tbinfo = traceback.format_tb(tracebackobj)
	errmsg = '%s: \n%s' % (str(excType), str(excValue))
	sections = [separator, timeString, separator, errmsg, separator]+ tbinfo
	msg = '\n'.join(sections)
	print(msg)
	try:
		f = open(logFile, "w")
		f.write(msg)
		f.write(versionInfo)
		f.close()
	except IOError:
		pass
	errorbox = QMessageBox()
	errorbox.setIcon(QMessageBox.Critical)
	errorbox.setWindowTitle("Application Error")
	errorbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Abort)
	errorbox.setDefaultButton(QMessageBox.Ok)
	errorbox.setText(str(notice)+str(msg)+str(versionInfo))
	try:
		#TODO for some reason, the exec method fails with the following exception *after* closing the dialog
		#TypeError: unable to convert a C++ 'QProcess::ExitStatus' instance to a Python object
		res = errorbox.exec()
		print("msgbox result",res)
		if res == QMessageBox.Abort:
			sys.exit(2)
	except Exception as e:
		traceback.print_exc()
		print(str(e))

sys.excepthook = excepthook
