
# PRE Workbench
# Copyright (C) 2019 Max Weller
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
from collections import defaultdict

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QMessageBox

MainWindow = None
NavigateCommands = dict()

class GlobalEventCls(QObject):
    on_log = pyqtSignal(str)
    on_select_bytes = pyqtSignal(object, object)

GlobalEvents = GlobalEventCls()


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
        if not "=" in args[i]:
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
    params = dict()
    for arg in args:
        key, value = arg.split("=", 2)
        params[key] = value
    fun(**params)

def navigateLink(link):
    if QMessageBox.question(None, "Open from anchor?", str(link)) == QMessageBox.Yes:
        navigate("OPEN", "FileName=" + link)

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

def setControlColors(ctrl, bg, fg=None):
    pal = ctrl.palette()
    if bg is not None: pal.setColor(ctrl.backgroundRole(), QColor(bg))
    if fg is not None: pal.setColor(QPalette.WindowText, QColor(fg))
    ctrl.setPalette(pal)

def qApp():
    return QApplication.instance()
