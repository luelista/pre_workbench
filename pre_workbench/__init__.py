
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

import gc
import logging
import os.path
import platform
import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen, QStyleFactory, QFileDialog

from pre_workbench import configs, guihelper, errorhandler
from pre_workbench.configs import SettingsSection
from pre_workbench.mainwindow import WorkbenchMain
from pre_workbench.project import Project
from pre_workbench.syshelper import load_file_watch

gc.set_debug(gc.DEBUG_STATS)

def find_project():
	preventAutoOpen = len(sys.argv) > 1 and sys.argv[1] == "--choose-project"

	if not preventAutoOpen:
		if len(sys.argv) > 1 and os.path.isfile(os.path.join(sys.argv[1], ".pre_workbench")):
			return sys.argv[1]

		if os.path.isfile(os.path.join(os.getcwd(), ".pre_workbench")):
			return os.getcwd()

		last_prj = configs.getValue("LastProjectDir", None)
		if last_prj and os.path.isfile(os.path.join(last_prj, ".pre_workbench")):
			return last_prj

	dlg = QFileDialog()
	dlg.setFileMode(QFileDialog.DirectoryOnly)
	dlg.setWindowTitle("Choose project directory")
	if dlg.exec() == QFileDialog.Accepted:
		return dlg.selectedFiles()[0]

	return None

def run_app():
	errorhandler.initLogging()
	logging.info("pre_workbench running on %s", " ".join(platform.uname()))
	logging.info("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))
	logging.info("Writing Logfile: %s", errorhandler.logFile)
	logging.info("Argv: %r", sys.argv)

	sys.excepthook = errorhandler.excepthook

	from PyQt5.QtWidgets import QApplication

	app = QApplication(sys.argv)
	splash = show_splash()

	configs.registerOption(SettingsSection('View', 'View', 'Theme', 'Theme'),
						   "AppTheme", "Theme", "select", {"options": [(x, x) for x in QStyleFactory.keys()]},
						   "fusion", lambda key, value: app.setStyle(value))
	load_file_watch(app, os.path.join(os.path.dirname(__file__), "stylesheet.css"), lambda contents: app.setStyleSheet(contents))

	prj_dir = find_project()
	if not prj_dir: sys.exit(1)
	app_project = Project(prj_dir)
	guihelper.CurrentProject = app_project
	configs.setValue("LastProjectDir", app_project.projectFolder)

	guihelper.MainWindow = WorkbenchMain(app_project)
	guihelper.MainWindow.show()
	splash.finish(guihelper.MainWindow)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

def show_splash():
	splashimg = configs.respath("icons/splash.jpg")
	splash = QSplashScreen(QPixmap(splashimg))
	splash.show()
	return splash
