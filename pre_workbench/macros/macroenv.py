from PyQt5.QtWidgets import QMessageBox, QInputDialog

from pre_workbench.app import MainWindow
from pre_workbench.controls.genericwidgets import showListSelectDialog
from pre_workbench.guihelper import navigateBrowser, getClipboardText, setClipboardText
from pre_workbench.controls.scintillaedit import showScintillaDialog

def alert(msg, title="Macro Alert"):
	QMessageBox.information(MainWindow, title, str(msg))

def confirm(msg, title="Macro Confirm"):
	return QMessageBox.question(MainWindow, title, str(msg), QMessageBox.Ok|QMessageBox.Cancel) == QMessageBox.Ok

def prompt(msg, defaultText="", title="Macro Prompt"):
	return QInputDialog.getText(MainWindow, title, str(msg), text=defaultText)


import logging

log = logging.info

__all__ = ['navigateBrowser', 'getClipboardText', 'setClipboardText', 'showScintillaDialog', 'alert', 'confirm', 'prompt', 'log', 'logging', 'showListSelectDialog', 'MainWindow']
