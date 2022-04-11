import argparse
import gc
import logging

from PyQt5.QtCore import QObject, pyqtSignal, QEvent
from PyQt5.QtWidgets import QMessageBox, QApplication

from pre_workbench.guihelper import splitNavArgs

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

