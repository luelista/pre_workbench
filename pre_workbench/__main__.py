print("PRE-Workbench")

import logging
import os.path
import platform
import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSplashScreen, QStyleFactory, QFileDialog, QMessageBox

import pre_workbench.app
from pre_workbench import configs, guihelper, errorhandler
from pre_workbench.app import WorkbenchApplication
from pre_workbench.configs import SettingsSection
from pre_workbench.mainwindow import WorkbenchMain
from pre_workbench.project import Project
from pre_workbench.syshelper import load_file_watch


def find_project(args):
	if not args.choose_project:
		if args.project_dir and os.path.isdir(args.project_dir):
			return sys.argv[1]

		last_prj = configs.getValue("LastProjectDir", None)
		if last_prj and os.path.isfile(os.path.join(last_prj, ".pre_workbench")):
			return last_prj

		if os.path.isfile(os.path.join(os.getcwd(), ".pre_workbench")):
			return os.getcwd()

	if not args.choose_project:
		QMessageBox.information(None, "Welcome", "Welcome to PRE Workbench!\n\n"
								"In the next dialog, you will be asked to choose a project directory. You can\n"
								"- choose an existing project\n- create a new folder\n- select an existing folder\n\n"
								"If it does not exist already, a project database file (named \".pre_workbench\") "
								"will automatically be created in this directory.")

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

	app = WorkbenchApplication(sys.argv)
	if not app.args.reset_config:
		configs.loadFromFile()
	else:
		logging.warning("Resetting configuration!")
	splash = show_splash()

	configs.registerOption(SettingsSection('View', 'View', 'Theme', 'Theme'),
						   "AppTheme", "Theme", "select", {"options": [(x, x) for x in QStyleFactory.keys()]},
						   "fusion", lambda key, value: app.setStyle(value))
	load_file_watch(app, os.path.join(os.path.dirname(__file__), "stylesheet.css"), lambda contents: app.setStyleSheet(contents))

	prj_dir = find_project(app.args)
	if not prj_dir: sys.exit(1)
	app_project = Project(prj_dir)
	configs.updateMru("ProjectMru", prj_dir, 5)
	pre_workbench.app.CurrentProject = app_project
	configs.setValue("LastProjectDir", app_project.projectFolder)

	pre_workbench.app.MainWindow = WorkbenchMain(app_project)
	pre_workbench.app.MainWindow.show()
	splash.finish(pre_workbench.app.MainWindow)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())


def show_splash():
	splashimg = configs.respath("icons/splash.jpg")
	splash = QSplashScreen(QPixmap(splashimg))
	splash.show()
	return splash


run_app()


