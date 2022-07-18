
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
import subprocess

from PyQt5 import QtCore
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QColor, QPalette, QDesktopServices, QFont, QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialogButtonBox, QDialog, QVBoxLayout, QLabel

from pre_workbench.util import SimpleThread


def str_ellipsis(data: str, length: int) -> str:
	return (data[:length] + '...(%d)'%(len(data))) if len(data) > length+2 else data


def setClipboardText(txt: str):
	cb = QApplication.clipboard()
	cb.clear(mode=cb.Clipboard )
	cb.setText(txt, mode=cb.Clipboard)


def getClipboardText() -> str:
	cb = QApplication.clipboard()
	return cb.text(mode=cb.Clipboard)


def splitNavArgs(args):
	start = None
	for i in range(len(args)):
		if "=" not in args[i]:
			if start is not None:
				yield args[start:i]
			start = i
	if start is not None:
		yield args[start:]


def navigateBrowser(link):
	QDesktopServices.openUrl(QUrl(link))


def getMonospaceFont() -> QFont:
	font = QFont("monospace")
	font.setStyleHint(QFont.Monospace)
	return font


def getHighlightStyles():
	#TODO maybe make these user definable
	return [
		("R", "Red", {"color": "#aa0000"}),
		("G", "Green", {"color": "#00aa00"}),
		("Y", "Yellow", {"color": "#aaaa00"}),
		("L", "Blue", {"color": "#0000aa"}),
		("M", "Magenta", {"color": "#aa00aa"}),
		("T", "Turqoise", {"color": "#00aaaa"}),
	]


def setControlColors(ctrl, bg, fg=None):
	pal = ctrl.palette()
	if bg is not None: pal.setColor(ctrl.backgroundRole(), QColor(bg))
	if fg is not None: pal.setColor(QPalette.WindowText, QColor(fg))
	ctrl.setPalette(pal)


def qApp():
	return QApplication.instance()


def filledColorIcon(color: str, size: int) -> QIcon:
	pix = QPixmap(size, size)
	pix.fill(QColor(color))
	return QIcon(pix)


def makeDlgButtonBox(dlg, ok_callback, retval_callback):
	btn = QDialogButtonBox()
	btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
	if ok_callback is not None:
		def ok_slot():
			try:
				ok_callback(retval_callback())
				dlg.accept()
			except Exception as ex:
				QMessageBox.critical(dlg, "Error", str(ex))
		btn.accepted.connect(ok_slot)
	else:
		btn.accepted.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)
	return btn


def makeWidgetDlg(widget, title, retval_callback, parent=None, ok_callback=None, min_width=300):
	dlg = QDialog(parent)
	dlg.setMinimumWidth(min_width)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.layout().addWidget(widget)
	return dlg, makeDlgButtonBox(dlg, ok_callback, retval_callback)


def showWidgetDlg(widget, title, retval_callback, parent=None, ok_callback=None, min_width=300):
	dlg, btn = makeWidgetDlg(widget, title, retval_callback, parent, ok_callback, min_width)
	if dlg.exec() == QDialog.Rejected: return None
	if not ok_callback: return retval_callback()


def TODO():
	QMessageBox.warning(None, "TODO", "Not implemented yet")


def runProcessWithDlg(title, message, parent, **subprocess_args):
	dlg = QDialog(parent)
	dlg.setWindowFlags(QtCore.Qt.Sheet | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.layout().addWidget(QLabel(text=message))
	btns = QDialogButtonBox()
	dlg.layout().addWidget(btns)
	btns.setStandardButtons(QDialogButtonBox.Cancel)
	logging.debug("Running process interactively with args %r", subprocess_args)
	proc = subprocess.Popen(**subprocess_args)
	result = {}
	def thread_fn():
		try:
			return proc.communicate(), None
		except Exception as ex:
			return (False, False), ex
	def finish_fn(res):
		(result['stdout'], result['stderr']), result['exception'] = res
		if result['exception']:
			dlg.reject()
		else:
			dlg.accept()
	thread = SimpleThread(parent, thread_fn, finish_fn)
	btns.rejected.connect(lambda: proc.kill())
	dlg.exec()
	return result
