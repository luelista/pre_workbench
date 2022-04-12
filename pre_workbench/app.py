import argparse
import gc
import logging
import os.path
import platform
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QSplashScreen, QStyleFactory, QFileDialog, QMessageBox

from pre_workbench import configs, errorhandler
from pre_workbench.configs import SettingsSection
from pre_workbench.guihelper import splitNavArgs
from pre_workbench.syshelper import load_file_watch
from pre_workbench.util import get_app_version

MainWindow = None
NavigateCommands = dict()


class GlobalEventCls(QObject):
	on_config_change = pyqtSignal()


GlobalEvents = GlobalEventCls()
CurrentProject = None


def navigate(*args):
	for item in splitNavArgs(args):
		navigateSingle(*item)


def navigateSingle(cmd, *args):
	fun = NavigateCommands[cmd]
	params = {}
	for arg in args:
		key, value = arg.split("=", 2)
		params[key] = value
	fun(**params)


def navigateLink(link):
	if QMessageBox.question(None, "Open from anchor?", str(link)) == QMessageBox.Yes:
		navigate("OPEN", f'FileName={link}')


class WorkbenchApplication(QApplication):
	def __init__(self, args):
		super().__init__(args)
		logging.debug("Initializing application...")

		self.args = self._parse_args()
		logging.debug("CMD args: %r", self.args)
		if self.args.gc_debug:
			gc.set_debug(gc.DEBUG_STATS)

	def event(self, e):
		"""Handle macOS FileOpen events."""
		if e.type() == QEvent.FileOpen:
			logging.info("FileOpen Event: %s", e.file())
			MainWindow.openFile(e.file())
		else:
			return super().event(e)

		return True

	def _parse_args(self):
		parser = argparse.ArgumentParser(description='Protocol Reverse Engineering Workbench')
		parser.add_argument('--reset-config', action='store_true',
							help='Reset the configuration to defaults')
		parser.add_argument('--gc-debug', action='store_true',
							help='Print debug output from garbage collector')
		parser.add_argument('--choose-project', action='store_true',
							help='Force the project directory chooser to appear, instead of opening the last project')
		parser.add_argument('project_dir', metavar='DIR', type=str, nargs='?',
							help='Project directory')

		return parser.parse_args(self.arguments()[1:])


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
	global CurrentProject, MainWindow
	from pre_workbench.project import Project
	from pre_workbench.mainwindow import WorkbenchMain

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
	CurrentProject = app_project
	configs.setValue("LastProjectDir", app_project.projectFolder)

	MainWindow = WorkbenchMain(app_project)
	MainWindow.show()
	splash.finish(MainWindow)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())


def show_splash():
	splashimg = configs.respath("icons/splash.jpg")
	splash = QSplashScreen(QPixmap(splashimg))
	splash.showMessage("Version "+get_app_version(), QtCore.Qt.AlignBottom|QtCore.Qt.AlignLeft, QtCore.Qt.white)
	splash.show()
	return splash

