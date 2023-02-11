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

from PyQt5.QtCore import (pyqtSignal, QObject)

import pre_workbench.app
from pre_workbench.structinfo.parsecontext import FormatInfoContainer


class InteractiveFormatInfoContainer(QObject, FormatInfoContainer):
	updated = pyqtSignal()

	def __init__(self, **kw):
		QObject.__init__(self)
		FormatInfoContainer.__init__(self, **kw)

	def write_file(self, fileName):
		super().write_file(fileName)
		self.updated.emit()

	def get_fi_by_def_name(self, def_name):
		def_name = str(def_name)
		try:
			return self.definitions[def_name]
		except KeyError:
			from pre_workbench.controls.scintillaedit import showScintillaDialog
			code = showScintillaDialog(pre_workbench.app.MainWindow, "Reference to undefined type '" + def_name + "'. Create it now?", "", lexer="pgdl:anytype")
			if code:
				from pre_workbench.structinfo.parser import parse_definition
				self.definitions[def_name] = parse_definition(code)
				self.write_file(self.file_name)
				return self.definitions[def_name]
			else:
				raise

