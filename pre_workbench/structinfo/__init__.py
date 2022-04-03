
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

from pre_workbench.typeregistry import TypeRegistry

FITypes = TypeRegistry()


"""
class RangeTreeModel(QAbstractItemModel):
	def __init__(self, root, parent=None):
		super().__init__(parent)
		self.rootFiValue = root

	def columnCount(self, parent):
		return 5

	def data(self, index, role):
		if not index.isValid():
			return None

		if role != QtCore.Qt.DisplayRole:
			return None

		if self.listObject is None:
			return None

		item = self.listObject.buffers[index.row()]
		col_info = self.columns[index.column()]
		return col_info.extract(item)

	def flags(self, index):
		if not index.isValid():
			return QtCore.Qt.NoItemFlags

		return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

	def headerData(self, section, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			if section >= len(self.columns):
				return None
			return self.columns[section].title

		return None

	def index(self, row, column, parent):
		if not self.hasIndex(row, column, parent):
			return QModelIndex()

		return self.createIndex(row, column, parent.internalPointer())

	def rowCount(self, parent):
		if self.listObject is None: return 0
		return len(self.listObject)

	def addColumn(self, colInfo, insertBefore=None):
		if insertBefore == None: insertBefore = len(self.columns)
		self.beginInsertColumns(QModelIndex(), insertBefore, insertBefore)
		self.columns.insert(insertBefore, colInfo)
		self.endInsertColumns()
	def removeColumns(self, column: int, count: int, parent: QModelIndex = ...) -> bool:
		self.beginRemoveColumns(parent, column, column+count-1)
		self.columns = self.columns[0:column] + self.columns[column+count:]
		print(column, count, self.columns)
		self.endRemoveColumns()
		return True

	def parent(self, child: QModelIndex) -> QModelIndex:
		return QModelIndex()
"""


# struct header_field_info {
#     const char      *name;
#     const char      *abbrev;
#     enum ftenum     type;
#     int             display;
#     const void      *strings;
#     guint64         bitmask;
#     const char      *blurb;
#     .....
# };

hf_info_template = """
		{ &hf_{proto_abbrev}_{field_name}, {
			"{description}", "{proto_abbrev}.{field_name}", FT_{ws_type}, BASE_{display_base},
			{enum_ref}, 0, NULL, HFILL }},"""
