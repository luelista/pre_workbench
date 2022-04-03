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


import logging
import os
import sys
import traceback
import uuid

from PyQt5.QtCore import (Qt, pyqtSlot, QSignalMapper, QTimer, pyqtSignal)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMainWindow, QAction, QFileDialog, QWidget, QMessageBox, QToolButton, QLabel, QApplication
from PyQtAds import ads

from pre_workbench.guihelper import NavigateCommands, GlobalEvents, navigateBrowser
from pre_workbench import configs
# noinspection PyUnresolvedReferences
from pre_workbench.windows.content import textfile
# noinspection PyUnresolvedReferences
from pre_workbench import typeeditor
# noinspection PyUnresolvedReferences
from pre_workbench import windows
from pre_workbench.configs import getIcon
from pre_workbench.datawidgets import DynamicDataWidget
from pre_workbench.windows.dockwindows import FileBrowserWidget, MdiWindowListWidget, StructInfoTreeWidget, \
	StructInfoCodeWidget, DataInspectorWidget
from pre_workbench.windows.dockwindows import RangeTreeDockWidget, RangeListWidget, SelectionHeuristicsConfigWidget, LogWidget
from pre_workbench.genericwidgets import MemoryUsageWidget, showPreferencesDlg
# noinspection PyUnresolvedReferences
from pre_workbench.windows.content.objectwindow import ObjectWindow
from pre_workbench.typeeditor import JsonView
from pre_workbench.typeregistry import WindowTypes
from pre_workbench.windows.content.hexfile import HexFileWindow

MRU_MAX = 5
class WorkbenchMain(QMainWindow):
	zoom_updated = pyqtSignal(object)
	selected_bytes_updated = pyqtSignal(object)
	grammar_updated = pyqtSignal(object)
	meta_updated = pyqtSignal(str, object)

	def __init__(self, project):
		super().__init__()
		self.project = project
		self.mappedChildActions = list()
		self.curChildMeta = dict()
		self.initUI()
		self.restoreChildren()
		self.mdiArea.restoreState(self.project.getValue("DockState", b""))

		NavigateCommands["WINDOW-ID"] = self.navigateWindowId
		NavigateCommands["WINDOW"] = self.navigateWindow
		NavigateCommands["OPEN"] = self.openFile
		self.statusTimer = QTimer(self)
		self.statusTimer.timeout.connect(self.onStatusTimer)
		self.statusTimer.start(1000)

	def onStatusTimer(self):
		self.statusBar() # TODO was soll das?

	def restoreChildren(self):
		for wndInfo in self.project.getValue("ChildrenInfo", []):
			clz, _ = WindowTypes.find(name=wndInfo["clz"])
			try:
				wnd = clz(**wndInfo["par"])
				wnd.setObjectName(str(wndInfo["id"]))
				self.showChild(wnd)
			except Exception as ex:
				traceback.print_exc()
				msg = QMessageBox(QMessageBox.Critical, "Failed to restore window", "Failed to restore window of type "+wndInfo["clz"]+"\n\n"+traceback.format_exc(), QMessageBox.Ok | QMessageBox.Abort, self)
				msg.addButton("Show parameters", QMessageBox.YesRole)
				res = msg.exec()
				if res == QMessageBox.Abort:
					sys.exit(13)
				if res == 0:
					self.showChild(JsonView(jdata=wndInfo))
		for wndInfo in self.project.getValue("DockWidgetStates", []):
			try:
				self.dockWidgets[wndInfo["id"]].restoreState(wndInfo["par"])
			except:
				logging.exception("Failed to restore dock widget state for %r", wndInfo["id"])

	def updateChildWindowList(self, obj=None):
		logging.debug("updateChildWindowList")
		wndList = self.mdiArea.dockWidgetsMap().values()
		self.dockWidgets["Window List"].updateWindowList(wndList)

	def closeEvent(self, e):
		configs.setValue("MainWindowGeometry", self.saveGeometry())
		configs.setValue("MainWindowState", self.saveState(123))
		self.saveChildren()
		self.project.setValue("DockState", self.mdiArea.saveState())
		super().closeEvent(e)

	def saveChildren(self):
		self.project.setValue("ChildrenInfo", [
			{
				"id": wnd.widget().objectName(),
				"clz": type(wnd.widget()).__name__,
				"geo": [wnd.pos().x(), wnd.pos().y(), wnd.size().width(), wnd.size().height() ], #bytes(wnd.saveGeometry()),
				"par": wnd.widget().saveParams(),
			}
			for wnd in self.mdiArea.dockWidgetsMap().values()
			if hasattr(wnd.widget(), "saveParams")
		])
		self.project.setValue("DockWidgetStates", [
			{ "id": name, "par": widget.saveState() }
			for name, widget in self.dockWidgets.items()
			if hasattr(widget, "saveState")
		])


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


	def _initActions(self):
		self.exitAct = QAction('Exit', self, shortcut='Ctrl+Q', statusTip='Exit application', triggered=QApplication.closeAllWindows, menuRole=QAction.QuitRole)

		self.openAct = QAction(getIcon('folder-open-document.png'), 'Open', self, shortcut='Ctrl+O',
							   statusTip='Open file', triggered=self.onFileOpenAction)

		self.loadProjectAct = QAction(getIcon('application--plus.png'), 'Open project...', self, shortcut='Ctrl+Shift+O',
							   statusTip='Open project...', triggered=self.onProjectOpenAction)

		self.saveAct = QAction(getIcon('disk.png'), "&Save", self,
				shortcut=QKeySequence.Save,
				statusTip="Save the document to disk")
		self.mapChildAction(self.saveAct, "save")

		self.saveAsAct = QAction(getIcon('disk-rename.png'), "Save &As...", self,
				shortcut=QKeySequence.SaveAs,
				statusTip="Save the document under a new name")
		self.mapChildAction(self.saveAsAct, "saveAs")

		self.reloadFileAct = QAction("&Reload", self,
				shortcut=QKeySequence.Refresh,
				statusTip="Reload the current file from disk")
		self.mapChildAction(self.reloadFileAct, "reloadFile")

		# TODO
		"""self.closeAct = QAction("Cl&ose", self,
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
				triggered=self.mdiArea.activatePreviousSubWindow)"""

		self.reloadGrammarAct = QAction("&Reload grammar", self,
				shortcut="Ctrl+I",
				statusTip="Reload the grammar from disk")
		self.mapChildAction(self.reloadGrammarAct, "reloadGrammar")

		self.openGrammarAct = QAction("&Open grammar", self,
				shortcut="Ctrl+Shift+I",
				statusTip="Open a grammar file to parse the current buffer")
		self.mapChildAction(self.openGrammarAct, "openGrammar")

	def _initMenu(self):
		menubar = self.menuBar()
		mainToolbar = self.addToolBar('Main')
		toolWndToolbar = self.addToolBar('Tool Windows')

		##### FILE #####
		fileMenu = menubar.addMenu('&File')
		newTbAct = QToolButton(self, icon=getIcon('document--plus.png'), text='New', popupMode=QToolButton.InstantPopup)
		newTbMenu = fileMenu.addMenu("New Tab")
		newTbAct.setMenu(newTbMenu)
		for wndTyp, meta in WindowTypes.types:
			text = 'New '+meta.get('displayName', meta.get('name'))
			newAct = QAction(text, self, #shortcut='Ctrl+N',
									   statusTip=text,
									   triggered=lambda dummy, wndTyp=wndTyp: self.onFileNewWindowAction(wndTyp))
			#fileMenu.addAction(newAct)
			newTbMenu.addAction(newAct)
		mainToolbar.addWidget(newTbAct)
		#fileMenu.addAction(self.newAct)

		fileMenu.addAction(self.openAct)
		fileMenu.addAction(self.saveAct)
		fileMenu.addAction(self.saveAsAct)
		fileMenu.addAction(self.reloadFileAct)
		fileMenu.addSeparator()

		fileMenu.addAction(self.loadProjectAct)
		recentProjectMenu = fileMenu.addMenu('&Recent projects')
		for project in configs.getValue("ProjectMru", []):
			recentProjectMenu.addAction(project, lambda dir=project: self.openProjectInNewWindow(dir))
		fileMenu.addSeparator()

		self.mruActions = []
		for _ in range(MRU_MAX):
			a = fileMenu.addAction("-")
			a.triggered.connect(self.onMruClicked)
			self.mruActions.append(a)
		self.updateMruActions()
		fileMenu.addSeparator()
		fileMenu.addAction(self.exitAct)

		##### VIEW #####
		viewMenu = menubar.addMenu('&View')
		toolWndMenu = viewMenu.addMenu('&Tool Windows')
		for name in self.dockWidgets:
			#a = toolWndMenu.addAction(name, lambda name=name: self.mdiArea.findDockWidget(name).toggleView(True))
			toolWndMenu.addAction(self.mdiArea.findDockWidget(name).toggleViewAction())
			toolWndToolbar.addAction(self.mdiArea.findDockWidget(name).toggleViewAction())
		viewMenu.addSeparator()
		a = QAction("Zoom In", self, shortcut='Ctrl++')
		self.mapChildAction(a, "zoomIn")
		viewMenu.addAction(a)
		a = QAction("Zoom Out", self, shortcut='Ctrl+-')
		self.mapChildAction(a, "zoomOut")
		viewMenu.addAction(a)
		a = QAction("Reset", self, shortcut='Ctrl+0')
		self.mapChildAction(a, "zoomReset")
		viewMenu.addAction(a)

		##### PARSER #####
		parserMenu = menubar.addMenu('&Parser')
		parserMenu.addAction(self.openGrammarAct)
		parserMenu.addAction(self.reloadGrammarAct)

		##### TOOLS #####
		toolsMenu = menubar.addMenu('&Tools')
		showConfigAction = QAction("Show config", self, triggered=lambda: self.showChild(JsonView(jdata=configs.configDict)),
								   shortcut='Ctrl+Shift+,')
		toolsMenu.addAction(showConfigAction)
		editConfigAction = QAction(getIcon("wrench-screwdriver.png"), "Preferences ...", self, triggered=lambda: self.onPreferences(),
								   menuRole=QAction.PreferencesRole, shortcut='Ctrl+,')
		toolsMenu.addAction(editConfigAction)

		##### WINDOW #####
		self.windowMenu = menubar.addMenu("&Window")
		self.updateWindowMenu()
		self.windowMenu.aboutToShow.connect(self.updateWindowMenu)

		##### HELP #####
		helpMenu = menubar.addMenu("&Help")
		helpMenu.addAction(QAction("Getting started", self, triggered=lambda: navigateBrowser("https://luelista.github.io/pre_workbench/getting-started")))
		helpMenu.addAction(QAction("Syntax reference", self, triggered=lambda: navigateBrowser("https://luelista.github.io/pre_workbench/syntax-reference")))
		helpMenu.addAction(QAction("Key bindings", self, triggered=lambda: navigateBrowser("https://luelista.github.io/pre_workbench/key-bindings")))

		helpMenu.addAction(QAction("Issue tracker", self, triggered=lambda: navigateBrowser("https://github.com/luelista/pre_workbench/issues")))
		helpMenu.addAction(QAction("About PRE Workbench", self, triggered=lambda: self.showAboutBox(),
								   menuRole=QAction.AboutRole))

		mainToolbar.addAction(self.openAct)
		mainToolbar.addAction(self.saveAct)
		mainToolbar.addAction(self.saveAsAct)
		mainToolbar.addAction(editConfigAction)

	def _initDockWindows(self):
		self.dockWidgets = {}
		self.createDockWnd("Project Files", "folder-tree.png", FileBrowserWidget(self.project.projectFolder), ads.LeftDockWidgetArea, showFirstRun=True)
		self.dockWidgets["Project Files"].on_open.connect(self.openFile)
		self.createDockWnd("Window List", "applications-stack.png", MdiWindowListWidget(), ads.LeftDockWidgetArea)
		self.zoomWindow = DynamicDataWidget()
		self.zoomWindow.meta_updated.connect(self.onMetaUpdateRaw)
		self.createDockWnd("Zoom", "document-search-result.png", self.zoomWindow, ads.BottomDockWidgetArea)
		self.zoom_updated.connect(lambda content: self.zoomWindow.setContents(content))
		self.createDockWnd("Data Inspector", "user-detective-gray.png", DataInspectorWidget(), ads.BottomDockWidgetArea, showFirstRun=True)
		self.selected_bytes_updated.connect(self.dockWidgets["Data Inspector"].on_select_bytes)
		self.createDockWnd("Data Source Log", "terminal--exclamation.png", LogWidget("DataSource"), ads.TopDockWidgetArea)
		self.createDockWnd("Application Log", "terminal--exclamation.png", LogWidget(""), ads.TopDockWidgetArea)

		self.createDockWnd("Grammar Definition Tree", "tree.png", StructInfoTreeWidget())
		self.createDockWnd("Grammar Definition Code", "tree--pencil.png", StructInfoCodeWidget(), showFirstRun=True)
		self.createDockWnd("Grammar Parse Result", "tree--arrow.png", RangeTreeDockWidget(), showFirstRun=True)
		self.meta_updated.connect(self.dockWidgets["Grammar Parse Result"].on_meta_update)
		self.createDockWnd("Selected Ranges", "bookmarks.png", RangeListWidget(), showFirstRun=True)
		self.meta_updated.connect(self.dockWidgets["Selected Ranges"].on_meta_update)
		self.createDockWnd("Selection Heuristics", "clipboard-task.png", SelectionHeuristicsConfigWidget())

	def initUI(self):
		ads.CDockManager.setConfigFlag(ads.CDockManager.FocusHighlighting, True)
		ads.CDockManager.setConfigFlag(ads.CDockManager.MiddleMouseButtonClosesTab, True)
		ads.CDockManager.setConfigFlag(ads.CDockManager.AllTabsHaveCloseButton, True)
		ads.CDockManager.setConfigFlag(ads.CDockManager.DockAreaHasCloseButton, False)
		self.mdiArea = ads.CDockManager(self)

		label = QLabel(text="Welcome")
		label.setAlignment(Qt.AlignCenter)
		self.centralDockWidget = ads.CDockWidget("CentralWidget")
		self.centralDockWidget.setWidget(label)
		self.centralDockWidget.setFeature(ads.CDockWidget.NoTab, True)
		self.centralDockWidget.setFeature(ads.CDockWidget.DockWidgetClosable, False)
		self.mdiArea.setCentralWidget(self.centralDockWidget)

		self._initDockWindows()

		self.setUnifiedTitleAndToolBarOnMac(True)
		self.setAcceptDrops(True)

		self.mdiArea.focusedDockWidgetChanged.connect(self.onSubWindowActivated)
		self.mdiArea.focusedDockWidgetChanged.connect(self.dockWidgets["Window List"].onSubWindowActivated)

		# required for actions in "Window" menu
		self.windowMapper = QSignalMapper(self)
		self.windowMapper.mapped[QWidget].connect(self.setActiveSubWindow)

		self._initActions()
		self._initMenu()

		self.statusBar().addWidget(MemoryUsageWidget())

		self.setWindowIcon(getIcon("appicon.png"))
		self.setGeometry(300, 300, 850, 850)
		self.restoreGeometry(configs.getValue("MainWindowGeometry", b""))
		self.restoreState(configs.getValue("MainWindowState", b""), 123)
		self.setWindowTitle(f'PRE Workbench - {self.project.projectFolder}')
		self.setWindowFilePath(self.project.projectDbFile)
		self.show()

	def showAboutBox(self):
		QMessageBox.about(self, "PRE Workbench", "Protocol Reverse Engineering Workbench\n\n"
												 "Copyright (c) 2022 Mira Weller\n"
												 "Licensed under the GNU General Public License Version 3\n\n"
												 "https://github.com/luelista/pre_workbench")

	def onPreferences(self):
		res = showPreferencesDlg(configs.configDefinitions, configs.configDict, "Preferences", self)
		if res is not None:
			for k,v in res.items():
				configs.setValue(k,v)
		GlobalEvents.on_config_change.emit()

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
		#TODO
		return
		self.windowMenu.clear()
		self.windowMenu.addAction(self.closeAct)
		self.windowMenu.addAction(self.closeAllAct)
		self.windowMenu.addSeparator()
		self.windowMenu.addAction(self.nextAct)
		self.windowMenu.addAction(self.previousAct)

		windows = self.mdiArea.dockWidgetsMap().values()
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

	def onSubWindowActivated(self, old: ads.CDockWidget, now: ads.CDockWidget):
		logging.debug("onSubWindowActivated")
		self.updateMappedChildActions()
		if now is None or not hasattr(now.widget(), 'child_wnd_meta'): return
		new_meta = now.widget().child_wnd_meta
		# TODO what about metas only contained in new_meta?
		for ident, oldval in self.curChildMeta.items():
			newval = new_meta.get(ident)
			if newval != oldval:
				self.curChildMeta[ident] = newval
				if hasattr(self, ident+"_updated"): getattr(self, ident+"_updated").emit(newval)
				self.meta_updated.emit(ident, newval)

	def activeMdiChild(self):
		activeSubWindow = self.mdiArea.focusedDockWidget()
		if activeSubWindow:
			return activeSubWindow.widget()
		return None

	def setActiveSubWindow(self, window):
		if window:
			window.toggleView(True)
			window.raise_()
			window.setFocus()
			try:
				print(window.widget().nextInFocusChain())
				window.widget().nextInFocusChain().setFocus()
			except:
				logging.exception("nextInFocusChain")

	def onProjectOpenAction(self):
		self.openProjectInNewWindow()

	def openProjectInNewWindow(self, projectPath = "--choose-project"):
		import subprocess
		subprocess.Popen([sys.executable, sys.argv[0], projectPath], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


	def onFileNewWindowAction(self, typ):
		ow = typ()
		self.showChild(ow)

	def onFileOpenAction(self):
		fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", configs.getValue("lastOpenFile",""))
		if fileName:
			configs.setValue("lastOpenFile", fileName)
			self.openFile(fileName)

	def findWindow(self, Type=None, FileName=None, Id=None):
		for childWnd in self.mdiArea.dockWidgetsMap().values():
			logging.debug("childWnd object name: %s", childWnd.objectName())
			widget = childWnd.widget()
			if ((Type is None or type(widget).__name__ == Type) and
				(FileName is None or (hasattr(widget, "params") and widget.params.get("fileName") == FileName)) and
				(Id is None or childWnd.objectName() == Id)):
				return childWnd

		return None

	def navigateWindowId(self, Id):
		childWnd = self.findWindow(Id=Id)
		if childWnd:
			logging.debug("switching to childWnd: %s", childWnd)
			self.setActiveSubWindow(childWnd)

	@pyqtSlot(str, str)
	def navigateWindow(self, Type, FileName):
		childWnd = self.findWindow(Type=Type, FileName=FileName)
		if childWnd:
			logging.debug("switching to childWnd: %s", childWnd)
			self.setActiveSubWindow(childWnd)
			return

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
		childWnd = self.findWindow(FileName=FileName)
		if childWnd:
			logging.debug("switching to childWnd: %s", childWnd)
			self.setActiveSubWindow(childWnd)
			return

		configs.updateMru("MainFileMru", FileName, MRU_MAX)
		self.updateMruActions()

		root,ext = os.path.splitext(FileName)
		winType, _ = WindowTypes.find(fileExts=ext)
		if winType is None: winType = HexFileWindow

		try:
			wnd = winType(fileName=FileName)
			self.showChild(wnd)
		except Exception as ex:
			msg = QMessageBox(QMessageBox.Critical, "Failed to open file", "Failed to open window of type "+winType.__name__+"\n\n"+str(ex), QMessageBox.Ok, self)
			msg.setDetailedText(traceback.format_exc())
			msg.exec()

	def onMetaUpdateRaw(self, ident, newval):
		if hasattr(self, ident+"_updated"): getattr(self, ident+"_updated").emit(newval)
		self.meta_updated.emit(ident, newval)

	def onMetaUpdateChild(self, ident, newval):
		self.sender().child_wnd_meta[ident] = newval
		self.curChildMeta[ident] = newval
		if hasattr(self, ident+"_updated"): getattr(self, ident+"_updated").emit(newval)
		self.meta_updated.emit(ident, newval)

	def showChild(self, widget, floating=False):
		logging.debug("showChild %s", widget)
		subwnd = ads.CDockWidget(widget.windowTitle())
		subwnd.setWidget(widget)
		subwnd.setFeature(ads.CDockWidget.DockWidgetDeleteOnClose, True)
		subwnd.setFeature(ads.CDockWidget.DockWidgetForceCloseWithArea, True)
		subwnd.setWindowIcon(getIcon(type(widget).icon if hasattr(type(widget), 'icon') else 'document.png'))
		widget.child_wnd_meta = dict()
		try:
			widget.meta_updated.connect(self.onMetaUpdateChild)
		except: pass
		widget.destroyed.connect(self.updateChildWindowList)
		if not widget.objectName(): widget.setObjectName(str(uuid.uuid1()))
		subwnd.setObjectName(widget.objectName())
		widget.show()
		if floating:
			self.mdiArea.addDockWidgetFloating(subwnd)
		else:
			self.mdiArea.addDockWidgetTabToArea(subwnd, self.centralDockWidget.dockAreaWidget())
		self.updateChildWindowList()

	def createDockWnd(self, name, iconName, widget, area=ads.RightDockWidgetArea, showFirstRun=False):
		dw=ads.CDockWidget(name)
		dw.setObjectName(name)
		dw.setWidget(widget)
		dw.setIcon(getIcon(iconName))
		#dw.setToggleViewActionMode(ads.CDockWidget.ActionModeShow)
		dw.toggleViewAction().setIcon(dw.icon())
		self.mdiArea.addDockWidgetTab(area, dw)
		self.dockWidgets[name] = widget
		if not showFirstRun: dw.closeDockWidget()

