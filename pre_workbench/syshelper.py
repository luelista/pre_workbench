from pathlib import Path
from resource import getpagesize

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel

PAGESIZE = getpagesize()
PATH = Path('/proc/self/statm')

def get_resident_set_size() -> int:
	"""Return the current resident set size in bytes."""
	# statm columns are: size resident shared text lib data dt
	statm = PATH.read_text()
	fields = statm.split()
	return int(fields[1]) * PAGESIZE

class MemoryUsageWidget(QLabel):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		try:
			self.onStatusUpdate()
			self.timer = QTimer(self)
			self.timer.timeout.connect(self.onStatusUpdate)
			self.timer.start(5000)
		except:
			self.setText("---")

	def onStatusUpdate(self):
		self.setText("%0.1f MB"%(get_resident_set_size()/1024/1024))

