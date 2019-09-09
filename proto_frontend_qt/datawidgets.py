
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, \
	QFileDialog, QTabWidget, QTableWidget, QWidget, QToolBar, QVBoxLayout,\
	QMdiArea, QFormLayout, QToolBox, QComboBox, QLineEdit, QCheckBox, QLabel, QTableWidgetItem
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QObject, QSize)

from objects import ByteBuffer, ByteBufferList, ReloadRequired
from datasource import PcapFileDataSource, FileDataSource, LiveCaptureDataSource
import configs
from genericwidgets import ExpandWidget, SettingsGroup, printsizepolicy
from hexview import HexView2
from typeregistry import DataWidgetTypes

@DataWidgetTypes.register(handles=ByteBufferList)
class PacketListWidget(QWidget):
	def __init__(self):
		super().__init__()
		
		self.initUI()
		
		
	def initUI(self):
		layout = QVBoxLayout()
		self.setLayout(layout)

		tabs = QTabWidget()
		layout.addWidget(tabs)
		
		self.packetlist = QTableWidget()
		self.packetlist.setColumnCount(10)
		tabs.addTab(self.packetlist, "Raw Frames")

		self.iplist = QTableWidget()
		tabs.addTab(self.iplist, "IP Payloads")

		self.udplist = QTableWidget()
		tabs.addTab(self.udplist, "UDP Payloads")

		self.sessionlist = QTableWidget()
		tabs.addTab(self.sessionlist, "TCP Sessions")

	def setContents(self, lstObj):
		self.listObject = lstObj
		print("setContents", lstObj, len(lstObj))
		self.setWindowTitle(str(lstObj))
		self.listObject.on_new_packet.connect(self.onNewPacket)
		for bbuf in lstObj.buffers:
			self.addPacketToList(bbuf)

	def onNewPacket(self):
		print("onNewPacket")
		for bbuf in lstObj.buffers[self.packetlist.rowCount():]:
			self.addPacketToList(bbuf)

	def run_ndis(self):
		pass

	def addPacketToList(self, bbuf):
		idx = self.packetlist.rowCount()
		self.packetlist.insertRow(idx)
		c = 0
		for k,v in bbuf.metadata.items():
			self.packetlist.setItem(idx, c, QTableWidgetItem(v))
			c += 1
			if c > 10: break


@DataWidgetTypes.register(handles=ByteBuffer)
class ByteBufferWidget(QWidget):
	def __init__(self):
		super().__init__()
		
		self.initUI()
		
		
	def initUI(self):
		toolbar = QToolBar()
		self.splitIntoPacketsAction = toolbar.addAction("Split into packets")
		self.splitIntoPacketsAction.triggered.connect(self.splitIntoPackets)

		layout = QVBoxLayout()
		layout.setContentsMargins(0,0,0,0)
		self.setLayout(layout)

		self.textbox = HexView2()
		layout.addWidget(self.textbox)
		layout.addWidget(toolbar)
		#x=QTextEdit()
		#layout.addWidget(x)
		printsizepolicy(self.textbox.sizePolicy())
		#printsizepolicy(x.sizePolicy())
		

	def setContents(self, bufObj):
		self.bufferObject = bufObj
		self.setWindowTitle(str(bufObj))
		self.textbox.setBuffer(bufObj)
		self.bufferObject.on_new_data.connect(self.onNewData)

	def onNewData(self):
		#self.textbox.showHex(bufObj.buffer)
		self.textbox.redraw()

	def splitIntoPackets(self):
		pass

	def run_ndis(self):
		pass


class DynamicDataWidget(QWidget):
	
	def __init__(self):
		super().__init__()
		self.setLayout(QVBoxLayout())
		self.layout().setContentsMargins(0,0,0,0)
		self.childWidget = None
		self.setErrMes("No data loaded")
	def setContents(self, data):
		typ = type(data)
		if data is None:
			self.setErrMes("Data is 'None'")
		else:
			widgetTyp = DataWidgetTypes.find(handles=typ)
			if widgetTyp == None:
				self.setErrMes("Unknown data type "+str(typ))
			else:
				self.loadChildType(widgetTyp)
				self.childWidget.setContents(data)

	def setErrMes(self, msg):
		self.loadChildType(QTextEdit)
		self.childWidget.setHtml("<h4>Error</h4><p>"+msg+"</p>")

	def loadChildType(self, childType):
		if self.childWidget != None:
			self.layout().removeWidget(self.childWidget)
			self.childWidget.setParent(None)
		self.childWidget = childType()
		self.layout().addWidget(self.childWidget)
