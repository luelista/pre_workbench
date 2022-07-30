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

import argparse
import gc
import json
import logging
import logging.config
import os.path
import platform
import sys
import typing
from glob import glob

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

if typing.TYPE_CHECKING:
	from pre_workbench.project import Project

MainWindow = None
NavigateCommands = dict()

class GlobalEventCls(QObject):
	on_config_change = pyqtSignal()


GlobalEvents = GlobalEventCls()
CurrentProject: "typing.Optional[Project]" = None


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
		logging.getLogger().setLevel(self.args.log_level)
		if self.args.log_config:
			logging.config.dictConfig(json.load(open(self.args.log_config,"r")))
		logging.debug("CMD args: %r", self.args)
		if self.args.gc_debug:
			gc.set_debug(gc.DEBUG_STATS)

		self._show_splash()
		self.update_splash("Loading configuration...")
		from pre_workbench.project import Project
		self.user_prj = Project(configs.dirs.user_config_dir, "USER", "User-local")
		if not self.args.reset_config:
			configs.loadFromFile()
		else:
			logging.warning("Resetting configuration!")
			self.user_prj.db.execute("DELETE FROM options")
			self.user_prj.db.commit()

		configs.registerOption(SettingsSection('View', 'View', 'Theme', 'Theme'),
							   "AppTheme", "Theme", "select", {"options": [(x, x) for x in QStyleFactory.keys()]},
							   "fusion", lambda key, value: self.setStyle(value))
		load_file_watch(self, os.path.join(os.path.dirname(__file__), "stylesheet.css"),
						lambda contents: self.setStyleSheet(contents))

		prj_dir = self._find_project()
		if not prj_dir: sys.exit(1)
		self.project = Project(prj_dir, "PROJECT", "Project: "+os.path.basename(prj_dir))
		configs.updateMru("ProjectMru", prj_dir, 5)
		configs.setValue("LastProjectDir", self.project.projectFolder)

		from pre_workbench.macros.macro import SysMacroContainer
		self.macro_containers = {
			"BUILTIN": SysMacroContainer(),
			"USER": self.user_prj,
			"PROJECT": self.project
		}

		configs.registerOption(SettingsSection('General', 'General', 'Plugins', 'Plugins'),
							   "PluginsDir", "Plugin directory", "text",
							   {"fileselect": "dir", "caption": "Select folder from which all *.py files should be loaded as plugins"},
							   "", None)
		self.plugins = {}
		if self.args.plugins_dir:
			self.plugins_dir = self.args.plugins_dir
		elif dir := configs.getValue("General.Plugins.PluginsDir", ""):
			self.plugins_dir = dir
		else:
			self.plugins_dir = None

		if self.plugins_dir:
			self.update_splash("Loading plugins...")
			configs.icon_searchpaths.append(self.plugins_dir)
			for file in glob(os.path.join(self.plugins_dir, "*.py")):
				self._load_plugin(file)

	def _load_plugin(self, filespec):
		import importlib.util
		import sys
		modname = "pre_workbench.plugins." + os.path.basename(filespec)[:-3]
		enabled_plugins = configs.getValue("EnabledPlugins", [])
		if modname not in enabled_plugins:
			logging.info("Skipping plugin " + modname + " (from file " + filespec + ") - not enabled")
			return

		self.update_splash("Loading plugin " + modname)
		logging.info("Loading plugin "+modname+" from file "+filespec)
		spec = importlib.util.spec_from_file_location(modname, filespec)
		my_mod = importlib.util.module_from_spec(spec)
		sys.modules[modname] = my_mod
		self.plugins[modname] = my_mod
		spec.loader.exec_module(my_mod)

	def find_macros_by_input_types(self, types):
		return [(container_id, container, name)
					for container_id, container in self.macro_containers.items()
					for name in container.getMacroNamesByInputTypes(types)]

	def get_macro(self, container_id, name):
		return self.macro_containers[container_id].getMacro(name)

	def event(self, e):
		"""Handle macOS FileOpen events."""
		if e.type() == QEvent.FileOpen:
			logging.info("FileOpen Event: %s", e.file())
			MainWindow.openFile(e.file())
		else:
			return super().event(e)

		return True

	def _parse_args(self):
		parser = ArgumentParserWithGUI(description='Protocol Reverse Engineering Workbench')
		parser.add_argument('--reset-config', action='store_true',
							help='Reset the configuration to defaults')
		parser.add_argument('--log-level', default='DEBUG',
							help='Set the log level', choices=['TRACE','DEBUG','INFO','WARNING','ERROR'])
		parser.add_argument('--log-config', metavar='FILE',
							help='Load detailed logging config from file')
		parser.add_argument('--plugins-dir', metavar='DIR',
							help='Load all Python files from this folder as plugins')
		parser.add_argument('--gc-debug', action='store_true',
							help='Print debug output from garbage collector')
		parser.add_argument('--choose-project', action='store_true',
							help='Force the project directory chooser to appear, instead of opening the last project')
		parser.add_argument('project_dir', metavar='DIR', type=str, nargs='?',
							help='Project directory')

		return parser.parse_args(self.arguments()[1:])

	def _find_project(self):
		if not self.args.choose_project:
			if self.args.project_dir and os.path.isdir(self.args.project_dir):
				return self.args.project_dir

			if self.args.project_dir and os.path.isfile(self.args.project_dir) and os.path.basename(self.args.project_dir) == ".pre_workbench":
				return os.path.dirname(self.args.project_dir)

			last_prj = configs.getValue("LastProjectDir", None)
			if last_prj and os.path.isfile(os.path.join(last_prj, ".pre_workbench")):
				return last_prj

			if os.path.isfile(os.path.join(os.getcwd(), ".pre_workbench")):
				return os.getcwd()

		if not self.args.choose_project:
			QMessageBox.information(self.splash, "Welcome", "Welcome to PRE Workbench!\n\n"
									"In the next dialog, you will be asked to choose a project directory. You can\n"
									"- choose an existing project\n- create a new folder\n- select an existing folder\n\n"
									"If it does not exist already, a project database file (named \".pre_workbench\") "
									"will automatically be created in this directory.")

		dlg = QFileDialog(self.splash)
		dlg.setFileMode(QFileDialog.DirectoryOnly)
		dlg.setWindowTitle("Choose project directory")
		if dlg.exec() == QFileDialog.Accepted:
			return dlg.selectedFiles()[0]

		return None

	def _show_splash(self):
		splashimg = configs.respath("icons/splash.jpg")
		self.splash = QSplashScreen(QPixmap(splashimg))
		self.update_splash()
		self.splash.show()

	def update_splash(self, message=""):
		self.splash.showMessage(message + "\nVersion " + get_app_version(), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft, QtCore.Qt.white)


class ArgumentParserWithGUI(argparse.ArgumentParser):
	def _print_message(self, message: str, file = None) -> None:
		if message and file is None and sys.stderr is None:
			QMessageBox.information(None, "PRE Workbench", message)
		else:
			super()._print_message(message, file)


def run_app():
	global CurrentProject, MainWindow

	errorhandler.initLogging()
	logging.info("pre_workbench running on %s", " ".join(platform.uname()))
	logging.info("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))
	logging.info("Writing Logfile: %s", errorhandler.logFile)
	logging.info("Argv: %r", sys.argv)

	sys.excepthook = errorhandler.excepthook

	app = WorkbenchApplication(sys.argv)
	CurrentProject = app.project

	app.update_splash("Loading main window...")
	from pre_workbench.mainwindow import WorkbenchMain
	MainWindow = WorkbenchMain(app.project)
	MainWindow.show()
	app.splash.finish(MainWindow)
	# os.system("/home/mw/test/Qt-Inspector/build/qtinspector "+str(os.getpid())+" &")
	sys.exit(app.exec_())

