
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
from PyQt5.QtCore import QObject, pyqtSignal

all_registries = []

class TypeRegistry(QObject):
	updated = pyqtSignal()

	def __init__(self, name):
		super().__init__()
		self.setObjectName("TypeReg_"+name)
		self.types = list()
		all_registries.append(self)

	def register(self, **meta):
		def wrapper(typ):
			for k,v in meta.items():
				if hasattr(typ, k) and getattr(typ, k) == v: continue
				setattr(typ, k, v)
			if not "name" in meta:
				meta["name"] = typ.__name__
			for index, (checktyp, _) in enumerate(self.types):
				if checktyp.__name__ == typ.__name__:
					del self.types[index]
					break
			self.types.append((typ, meta))
			self.updated.emit()
			return typ
		return wrapper

	def find(self, **checkForMeta):
		for typ, meta in self.types:
			match = True
			for key, value in checkForMeta.items():
				if meta.get(key) == value or (type(meta.get(key)) == list and value in meta.get(key)):
					pass  # still consider this a match
				else:
					match = False
					break
			if match:
				return typ, meta
		return None, None

	def getSelectList(self, displayMeta):
		return [("", "")] + [(typ.__name__, meta[displayMeta]) for typ, meta in self.types]


def dump_type_registries():
	out = {reg.objectName(): {typ.__name__: meta for typ, meta in reg.types} for reg in all_registries}
	return out

WindowTypes = TypeRegistry("WindowTypes")
DataWidgetTypes = TypeRegistry("DataWidgetTypes")
DockWidgetTypes = TypeRegistry("DockWidgetTypes")
