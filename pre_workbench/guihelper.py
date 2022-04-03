
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
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtGui import QColor, QPalette, QDesktopServices, QFont
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialogButtonBox, QDialog, QVBoxLayout

MainWindow = None
NavigateCommands = dict()

class GlobalEventCls(QObject):
    on_config_change = pyqtSignal()

GlobalEvents = GlobalEventCls()

CurrentProject = None


def str_ellipsis(data, length):
	return (data[:length] + '...(%d)'%(len(data))) if len(data) > length+2 else data

def setClipboardText(txt):
	cb = QApplication.clipboard()
	cb.clear(mode=cb.Clipboard )
	cb.setText(txt, mode=cb.Clipboard)

def getClipboardText():
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

def navigateBrowser(link):
	QDesktopServices.openUrl(QUrl(link))

"""

	private void T_LinkClicked(object sender, LinkClickedEventArgs e) {
		if (e.LinkText.StartsWith("file:")) {
			App.Mgr.openFile(e.LinkText.Substring(5));
		} else if (e.LinkText.StartsWith("\\\\@")) {
			App.Mgr.Navigate(e.LinkText.Substring(3).Split('@'));
		} else if (e.LinkText.StartsWith("http://") || e.LinkText.StartsWith("https://")) {
			System.Diagnostics.Process.Start(e.LinkText);
		}
	}
"""

def getMonospaceFont():
	font = QFont("monospace")
	font.setStyleHint(QFont.Monospace)
	return font

def setControlColors(ctrl, bg, fg=None):
	pal = ctrl.palette()
	if bg is not None: pal.setColor(ctrl.backgroundRole(), QColor(bg))
	if fg is not None: pal.setColor(QPalette.WindowText, QColor(fg))
	ctrl.setPalette(pal)

def qApp():
	return QApplication.instance()


def makeDlgButtonBox(dlg, ok_callback, retval_callback):
	btn = QDialogButtonBox()
	btn.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
	if ok_callback is not None:
		def ok_slot():
			try:
				ok_callback(retval_callback())
				dlg.accept()
			except Exception as ex:
				QMessageBox.critical(dlg, "Fehler", str(ex))
		btn.accepted.connect(ok_slot)
	else:
		btn.accepted.connect(dlg.accept)
	btn.rejected.connect(dlg.reject)
	dlg.layout().addWidget(btn)
	return btn


def showWidgetDlg(widget, title, retval_callback, parent=None, ok_callback=None):
	dlg = QDialog(parent)
	dlg.setWindowTitle(title)
	dlg.setLayout(QVBoxLayout())
	dlg.layout().addWidget(widget)
	makeDlgButtonBox(dlg, ok_callback, retval_callback)
	if dlg.exec() == QDialog.Rejected: return None
	if not ok_callback: return retval_callback()
