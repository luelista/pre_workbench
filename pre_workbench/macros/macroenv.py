from PyQt5.QtWidgets import QMessageBox, QInputDialog

from pre_workbench.app import MainWindow
from pre_workbench.controls.genericwidgets import showListSelectDialog
from pre_workbench.guihelper import navigateBrowser, getClipboardText, setClipboardText
from pre_workbench.controls.scintillaedit import showScintillaDialog
from pre_workbench.objects import ByteBufferList, ByteBuffer


def alert(msg, title="Macro Alert"):
	QMessageBox.information(MainWindow, title, str(msg))


def confirm(msg, title="Macro Confirm") -> bool:
	return QMessageBox.question(MainWindow, title, str(msg), QMessageBox.Ok|QMessageBox.Cancel) == QMessageBox.Ok


def prompt(msg, defaultText="", title="Macro Prompt") -> (str, bool):
	return QInputDialog.getText(MainWindow, title, str(msg), text=defaultText)


def zoom(obj):
	MainWindow.zoomWindow.setContents(obj)


def openAsUntitled(obj):
	if isinstance(obj, bytes) or isinstance(obj, bytearray):
		obj = ByteBuffer(obj)

	if isinstance(obj, ByteBuffer):
		from pre_workbench.windows.content.hexfile import HexFileWindow
		wnd = HexFileWindow()
		wnd.dataDisplay.setBytes(obj)
		MainWindow.showChild(wnd)
	elif isinstance(obj, str):
		from pre_workbench.windows.content.textfile import TextFileWindow
		wnd = TextFileWindow()
		wnd.dataDisplay.setText(obj)
		MainWindow.showChild(wnd)
	elif isinstance(obj, ByteBufferList):
		from pre_workbench.windows.content.pcapfile import PcapngFileWindow
		wnd = PcapngFileWindow()
		wnd.dataDisplay.setContents(obj)
		MainWindow.showChild(wnd)


import logging

log = logging.info

__all__ = ['navigateBrowser', 'getClipboardText', 'setClipboardText', 'showScintillaDialog', 'alert', 'confirm', 'prompt', 'log', 'logging', 'showListSelectDialog', 'MainWindow', 'zoom',
		   'ByteBuffer', 'ByteBufferList', 'openAsUntitled']
