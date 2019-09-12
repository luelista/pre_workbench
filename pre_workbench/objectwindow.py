import traceback

from PyQt5.QtCore import pyqtSignal, QObject, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QToolBar

from datasource import DataSourceTypes
from datawidgets import DynamicDataWidget
from genericwidgets import SettingsGroup, ExpandWidget
from typeregistry import WindowTypes


@WindowTypes.register()
class ObjectWindow(QWidget):
	on_data_selected = pyqtSignal(QObject)
	on_log = pyqtSignal(str)

	def __init__(self, name="Untitled", dataSourceType="", collapseSettings=False, **kw):
		super().__init__()
		kw["name"] = name
		kw["dataSourceType"] = dataSourceType
		kw["collapseSettings"] = collapseSettings
		self.params = {}

		self.dataSource = None
		self.dataSourceType = ""
		self.initUI(collapseSettings)
		self.setConfig(kw)


	def saveParams(self):
		self.params["collapseSettings"] = self.sourceConfig.parent().collapsed
		return self.params

	def sizeHint(self):
		return QSize(600,400)
	def initUI(self, collapseSettings):
		layout=QVBoxLayout()
		layout.setContentsMargins(0,0,0,0)
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
		#tb.addItem(self.sourceConfig, "Data Source Options")
		layout.addWidget(ExpandWidget("Data Source Options", self.sourceConfig, collapseSettings))

		toolbar = QToolBar()
		self.cancelAction = toolbar.addAction("Cancel")
		self.cancelAction.triggered.connect(self.onCancelFetch)
		self.cancelAction.setEnabled(False)
		self.reloadAction = toolbar.addAction("Reload")
		self.reloadAction.triggered.connect(self.reload)
		layout.addWidget(toolbar)

		self.dataDisplay = DynamicDataWidget()
		self.dataDisplay.on_data_selected.connect(self.on_data_selected.emit)
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

	def onDataSourceTypeSelected(self):
		print("dst="+self.params["dataSourceType"])
		confFields = []
		if self.params["dataSourceType"]:
			clz, _ = DataSourceTypes.find(name=self.params["dataSourceType"])
			if self.dataSourceType != self.params["dataSourceType"]:
				confFields = clz.getConfigFields()
				self.dataSourceType = self.params["dataSourceType"]
		self.sourceConfig.setFields([
			("name", "Name", "text", {}),
			("dataSourceType", "Data Source Type", "select", {"options":DataSourceTypes.getSelectList("DisplayName")}),
		] + confFields)

	def onFinished(self):
		self.cancelAction.setEnabled(False)

	def onCancelFetch(self):
		self.dataSource.cancelFetch()

	def reload(self):
		try:
			self.cancelAction.setEnabled(True)
			clz, _ = DataSourceTypes.find(name=self.params["dataSourceType"])
			self.dataSource = clz(self.params)
			self.dataSource.on_finished.connect(self.onFinished)
			self.dataSource.on_log.connect(self.on_log.emit)
			result = self.dataSource.startFetch()
			self.dataDisplay.setContents(result)

		except Exception as e:
			self.dataDisplay.setErrMes(traceback.format_exc())
			self.cancelAction.setEnabled(False)
