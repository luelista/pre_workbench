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
import logging
import traceback
import os.path

from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QToolBar

from pre_workbench.configs import SettingsField, getIcon
from pre_workbench.datasource import DataSourceTypes, MacroDataSource
from pre_workbench.datawidgets import DynamicDataWidget
from pre_workbench.controls.genericwidgets import SettingsGroup
from pre_workbench.guihelper import APP
from pre_workbench.typeregistry import WindowTypes


@WindowTypes.register(icon='beaker.png')
class ObjectWindow(QWidget):
	meta_updated = pyqtSignal(str, object)

	def __init__(self, name=None, dataSourceType="", collapseSettings=False, **kw):
		super().__init__()
		kw["name"] = name if name is not None else os.path.basename(kw["fileName"]) if "fileName" in kw else "Untitled"
		kw["dataSourceType"] = dataSourceType
		kw["collapseSettings"] = collapseSettings
		self.params = {}

		self.dataSource = None
		self.dataSourceType = ""
		self._initUI(collapseSettings)
		self.setConfig(kw)

	def saveParams(self):
		self.params["collapseSettings"] = not self.sourceConfig.isVisible()
		return self.params

	def sizeHint(self):
		return QSize(600, 400)

	def _initUI(self, collapseSettings):
		layout = QVBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		self.setLayout(layout)
		#tb = QToolBox(self)
		#layout.addWidget(tb)
		#self.metaConfig = SettingsGroup([
		#	("name", "Name", "text", {}),
		#	("dataSourceType", "Data Source Type", "select", {"options":DataSourceTypes.getSelectList("DisplayName")}),
		#], self.params)
		#self.metaConfig.item_changed.connect(self.onConfigChanged)
		#tb.addItem(self.metaConfig, "Metadata")
		#layout.addWidget(ExpandWidget("Metadata", self.metaConfig, collapseSettings))

		self.sourceConfig = SettingsGroup([], self.params)
		self.sourceConfig.item_changed.connect(self.onConfigChanged)
		self.sourceConfig.setVisible(not collapseSettings)
		#tb.addItem(self.sourceConfig, "Data Source Options")
		#layout.addWidget(ExpandWidget("Data Source Options", self.sourceConfig, collapseSettings))

		toolbar = QToolBar()
		dsoVisAction = toolbar.addAction(getIcon("gear--pencil.png"), "Data Source Options")
		dsoVisAction.setCheckable(True); dsoVisAction.setChecked(not collapseSettings)
		dsoVisAction.toggled.connect(lambda val: self.sourceConfig.setVisible(val))
		metadataVisAction = toolbar.addAction(getIcon("tags-label.png"), "Metadata")
		metadataVisAction.setCheckable(True)
		toolbar.addSeparator()
		self.reloadAction = toolbar.addAction(getIcon("arrow-circle-double.png"), "Reload")
		self.reloadAction.triggered.connect(self.reload)
		self.cancelAction = toolbar.addAction(getIcon("control-stop-square.png"), "Cancel")
		self.cancelAction.triggered.connect(self.onCancelFetch)
		self.cancelAction.setEnabled(False)
		exportAction = toolbar.addAction(getIcon("document-export.png"), "Export")
		exportAction.triggered.connect(self.exportInTab)
		layout.addWidget(toolbar)
		layout.addWidget(self.sourceConfig)

		self.dataDisplay = DynamicDataWidget()
		self.dataDisplay.meta_updated.connect(self.meta_updated.emit)
		metadataVisAction.toggled.connect(self.dataDisplay.setMetadataVisible)
		#tb.addItem(self.dataDisplay, "Results")
		#layout.addWidget(ExpandWidget("Results", self.dataDisplay))
		layout.addWidget(self.dataDisplay)

	def setConfig(self, config):
		#self.metaConfig.setValues(config)
		self.sourceConfig.setValues(config)
		self.params.update(config)
		self.onDataSourceTypeSelected()

	def onConfigChanged(self, key, value):
		self.params[key] = value
		self.setWindowTitle(self.params["name"] + " - " + self.params["dataSourceType"])
		if key == "name":
			pass
		elif key == "dataSourceType":
			self.onDataSourceTypeSelected()
		else:
			pass
			#if self.dataSource != None:
			#    try:
			#        self.dataSource.updateParam(key, value)
			#    except ReloadRequired as ex:
			#        self.loadDataSource()

	def _getDatasourcesList(self):
		builtinDS = DataSourceTypes.getSelectList("DisplayName")
		macroDS = [("MACRO/" + container_id + "/" + macroname, "Macro: " + macroname)
				   for container_id, container, macroname in APP().find_macros_by_input_type("DATA_SOURCE")]
		return builtinDS + macroDS

	def _getDatasource(self, id):
		if id.startswith("MACRO/"):
			prefix, container_id, macroname = id.split("/", 3)
			return lambda params: MacroDataSource(container_id, macroname, params)
		else:
			clz, _ = DataSourceTypes.find(name=self.params["dataSourceType"])
			return clz

	def _getDatasourceConfigFields(self, id):
		if id.startswith("MACRO/"):
			prefix, container_id, macroname = id.split("/", 3)
			macro = APP().get_macro(container_id, macroname)
			return macro.options
		else:
			clz, _ = DataSourceTypes.find(name=self.params["dataSourceType"])
			return clz.getConfigFields()

	def onDataSourceTypeSelected(self):
		logging.debug("dst=" + self.params["dataSourceType"])
		confFields = []
		if self.params["dataSourceType"]:
			confFields = self._getDatasourceConfigFields(self.params["dataSourceType"])
			self.dataSourceType = self.params["dataSourceType"]
		self.sourceConfig.setFields([
										SettingsField("name", "Name", "text", {}),
										SettingsField("dataSourceType", "Data Source Type", "select",
													  {"options": self._getDatasourcesList()}),
									] + confFields)

	def onFinished(self):
		self.cancelAction.setEnabled(False)

	def onCancelFetch(self):
		self.dataSource.cancelFetch()

	def reloadFile(self):  # action Ctrl-R
		self.reload()

	def reload(self):
		try:
			self.cancelAction.setEnabled(True)
			clz = self._getDatasource(self.params["dataSourceType"])
			self.dataSource = clz(self.params)
			self.dataSource.on_finished.connect(self.onFinished)
			result = self.dataSource.startFetch()
			self.dataDisplay.setContents(result)

		except Exception as e:
			self.dataDisplay.setErrMes(traceback.format_exc(), "Error: " + str(e))
			self.cancelAction.setEnabled(False)

	def childActionProxy(self):
		return self.dataDisplay.childWidget

	def exportInTab(self):
		pass
