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

import json
import logging
import logging.config
import platform
import sys
import tempfile
import time
import traceback
import urllib.request

from PyQt5.QtCore import pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QMessageBox, QCheckBox, QInputDialog

from pre_workbench import consts
from pre_workbench.util import get_app_version

logFile = tempfile.gettempdir()+'/'+consts.LOGFILE_NAME

enableReports = False

def report_error(logFile, excType, excValue, trace, desc):
	try:
		req = urllib.request.Request(consts.ERROR_REPORT_URL, data=json.dumps({
			'type': 'excepthook',
			'logFile': open(logFile, "r").read(),
			'excType': str(excType),
			'excValue': str(excValue),
			'traceback': trace,
			'platform': platform.uname(),
			'desc': desc,
			'version': get_app_version(),
		}).encode("utf-8"), headers={
			"Content-Type": "application/json",
		})
		with urllib.request.urlopen(req) as response:
			logging.info("Response from ping endpoint: %s",response.read())
	except Exception as e:
		logging.exception("Error reporting failed :(")
		print(e.read())

def check_for_updates():
	try:
		req = urllib.request.Request(consts.UPDATE_CHECK_URL)
		with urllib.request.urlopen(req) as response:
			content = json.loads(response.read())
			version = content["info"]["version"]
			return version
	except Exception as e:
		logging.exception("Update check failed :(")
		try:
			logging.warning("Update check result: "+str(e.read()))
		except:
			logging.warning("Unable to read update check result")

def excepthook(excType, excValue, tracebackobj):
	global enableReports
	"""
	Global function to catch unhandled exceptions.

	@param excType exception type
	@param excValue exception value
	@param tracebackobj traceback object
	"""
	separator = "\n" + ('-' * 80) + "\n"
	notice = \
		"""An unhandled exception occurred. Please report the problem\n"""\
		"""using the error reporting dialog.\n"""\
		"""\nError information:\n"""
	timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

	tbinfo = traceback.format_tb(tracebackobj)
	errmsg = '%s: \n%s' % (str(excType), str(excValue))
	sections = [timeString, errmsg] + tbinfo
	msg = separator.join(sections)
	logging.error(msg)

	errorbox = QMessageBox()
	errorbox.setIcon(QMessageBox.Critical)
	errorbox.setWindowTitle("Application Error")
	errorbox.setStandardButtons(QMessageBox.Ok)
	errorbox.addButton("Terminate Application", QMessageBox.DestructiveRole)
	logbtn = errorbox.addButton("Show Log", QMessageBox.ActionRole)
	logbtn.clicked.disconnect()
	logbtn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(logFile)))
	errorbox.setDefaultButton(QMessageBox.Ok)
	errorbox.setText(str(notice)+str(timeString + "\n" + errmsg))
	errorbox.setDetailedText(str(msg))
	cbReport = QCheckBox("Report this error including log file")
	cbReport.setChecked(enableReports)
	errorbox.setCheckBox(cbReport)
	try:
		#TODO for some reason, the exec method fails with the following exception *after* closing the dialog
		#TypeError: unable to convert a C++ 'QProcess::ExitStatus' instance to a Python object
		res = errorbox.exec()
		print(res)
		enableReports = cbReport.isChecked()
		if enableReports:
			desc, success = QInputDialog.getMultiLineText(None, "Error Reporting", "Please enter an optional description about this error (e.g. steps leading to this error, contact details in case more details are needed)", "")
			if success:
				report_error(logFile, excType, excValue, tbinfo, desc)
		if res != QMessageBox.Ok:
			sys.exit(2)
	except Exception as e:
		traceback.print_exc()
		print(str(e))


class ConsoleWindowLogHandler(logging.Handler, QObject):
	sigLog = pyqtSignal(str, str)
	def __init__(self):
		logging.Handler.__init__(self)
		QObject.__init__(self)
		self.formatter = logging.Formatter('%(asctime)s %(module)18s:%(lineno)-4s [%(levelname)s] %(message)s')

	def emit(self, log_record):
		message = self.formatter.format(log_record)
		self.sigLog.emit(log_record.levelname, message)

from copy import copy
from logging import Formatter

MAPPING = {
	'TRACE'   : 37, # white
	'DEBUG'   : 37, # white
	'INFO'    : 36, # cyan
	'WARNING' : 33, # yellow
	'ERROR'   : 31, # red
	'CRITICAL': 41, # white on red bg
}

PREFIX = '\033[{}m'
SUFFIX = '\033[0m'

class ColoredFormatter(Formatter):
	def __init__(self, pattern=None):
		Formatter.__init__(self, pattern)

	def format(self, record):
		seq = MAPPING.get(record.levelname, 37) # default white
		return PREFIX.format(seq) + Formatter.format(self, record) + SUFFIX

def initLogging():
	streamHandler = logging.StreamHandler()
	#if sys.stderr.isatty():
	streamHandler.setFormatter(ColoredFormatter('%(asctime)s %(name)s - %(module)s:%(lineno)s [%(levelname)s] %(message)s'))
	logging.basicConfig(level=10, format='%(asctime)s %(name)s - %(module)s:%(lineno)s [%(levelname)s] %(message)s',
						handlers=[
							streamHandler,
							logging.FileHandler(filename=logFile, mode='w'),
						])
