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
