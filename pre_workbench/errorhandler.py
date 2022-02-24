import json
import logging
import platform
import sys
import tempfile
import time
import traceback
import urllib.request

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox, QCheckBox, QInputDialog

logFile = tempfile.gettempdir()+'/pre_workbench.log'

enableReports = False

def report_error(logFile, excType, excValue, trace, desc):
	try:
		req = urllib.request.Request("https://dl.weller-it.com/pre_workbench/ping.php", data=json.dumps({
			'type': 'excepthook',
			'logFile': open(logFile, "r").read(),
			'excType': str(excType),
			'excValue': str(excValue),
			'traceback': trace,
			'platform': platform.uname(),
			'desc': desc
		}).encode("utf-8"), headers={
			"Content-Type": "application/json",
		})
		with urllib.request.urlopen(req) as response:
			logging.info("Response from ping endpoint: %s",response.read())
	except Exception as e:
		logging.exception("Error reporting failed :(")
		print(e.read())


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
		"""A log has been written to "<a href="file">%s</a>".\n\nError information:\n""" % \
		( logFile,)
	timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

	tbinfo = traceback.format_tb(tracebackobj)
	errmsg = '%s: \n%s' % (str(excType), str(excValue))
	sections = [timeString, errmsg] + tbinfo
	msg = separator.join(sections)
	logging.error(msg)

	errorbox = QMessageBox()
	errorbox.setIcon(QMessageBox.Critical)
	errorbox.setWindowTitle("Application Error")
	errorbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Abort)
	errorbox.setDefaultButton(QMessageBox.Ok)
	errorbox.setText(str(notice)+str(msg))
	cbReport = QCheckBox("Report this error including log file")
	cbReport.setChecked(enableReports)
	errorbox.setCheckBox(cbReport)
	try:
		#TODO for some reason, the exec method fails with the following exception *after* closing the dialog
		#TypeError: unable to convert a C++ 'QProcess::ExitStatus' instance to a Python object
		res = errorbox.exec()
		enableReports = cbReport.isChecked()
		if enableReports:
			desc, success = QInputDialog.getMultiLineText(None, "Error Reporting", "Please enter an optional description about this error (e.g. steps leading to this error)", "")
			if success:
				report_error(logFile, excType, excValue, tbinfo, desc)
		if res == QMessageBox.Abort:
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


def initLogging():
	logging.basicConfig(level=10, format='%(asctime)s %(module)s:%(lineno)s [%(levelname)s] %(message)s', force=True,
						handlers=[
							logging.StreamHandler(),
							logging.FileHandler(filename=logFile, mode='w'),
						])
