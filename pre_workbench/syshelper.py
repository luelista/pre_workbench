from PyQt5.QtCore import QFileSystemWatcher


def get_current_rss():
	import os
	import psutil
	process = psutil.Process(os.getpid())
	return process.memory_info().rss

def load_file_watch(parent, filename, callback):
	def cb(p=""):
		try:
			with open(filename, "r") as f:
				data = f.read()
		except:
			return
		callback(data)
	fsw = QFileSystemWatcher([filename], parent)
	fsw.fileChanged.connect(cb)
	cb()
