
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

import os.path
import sys, platform
import logging, tempfile

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen, QStyleFactory, QMessageBox, QCheckBox

from pre_workbench import configs, guihelper, errorhandler
from pre_workbench.configs import SettingsSection
from pre_workbench.mainwindow import WorkbenchMain
from pre_workbench.syshelper import load_file_watch

def run_app():
	logFile = tempfile.gettempdir()+'/pre_workbench.log'
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(module)s:%(lineno)s [%(levelname)s] %(message)s', force=True,
						handlers=[
							logging.StreamHandler(),
							logging.FileHandler(filename=logFile, mode='w'),
						])
	logging.info("pre_workbench running on %s", " ".join(platform.uname()))
	logging.info("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))
	logging.info("Writing Logfile: %s", logFile)

	errorhandler.logFile = logFile
	sys.excepthook = errorhandler.excepthook

	from PyQt5.QtWidgets import QApplication

	app = QApplication(sys.argv)
	splash = show_splash()

	configs.registerOption(SettingsSection('View', 'View', 'Theme', 'Theme'),
						   "AppTheme", "Theme", "select", {"options": [(x, x) for x in QStyleFactory.keys()]},
						   "fusion", lambda key, value: app.setStyle(value))
	load_file_watch(app, os.path.join(os.path.dirname(__file__), "stylesheet.css"), lambda contents: app.setStyleSheet(contents))
	mainWindow = WorkbenchMain()
	guihelper.MainWindow = mainWindow
	mainWindow.show()
	splash.finish(mainWindow)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

def show_splash():
	splashimg = configs.respath("icons/splash.jpg")
	splash = QSplashScreen(QPixmap(splashimg))
	splash.show()
	return splash
